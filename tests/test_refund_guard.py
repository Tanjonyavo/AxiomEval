import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from axiomeval.collect.adapters import ScriptedAdapter
from axiomeval.collect.refund_request import refund_intents
from axiomeval.collect.secure_tools import SecureToolbox
from axiomeval.collection import collect, load_records
from axiomeval.corpus.release import load_release
from axiomeval.corpus.scenarios import load_corpus
from axiomeval.corpus.splits import load_frozen
from axiomeval.policy.authz import Identity, load_policy

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "fixtures/corpus-v3"
NOW = datetime(2027, 1, 1, tzinfo=timezone.utc)
ORDER = "T2048"
IDENTITY = Identity("owner", "customer", "avana", NOW + timedelta(minutes=10))
CONDITIONAL = "Si ma commande T2048 est livrée, remboursez-moi 20 $."


class RefundGuardTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy(CORPUS / "policy.json")
        self.orders = {ORDER: {"commande": ORDER, "statut": "livrée", "montant": 120,
                               "tenant": "avana", "owner": "owner"}}

    def toolbox(self, request=CONDITIONAL, identity=IDENTITY):
        return SecureToolbox((), self.orders, self.policy, identity, lambda: NOW,
                             request=request, write_checks=True, refund_request_guard=True)

    def read_order(self, box):
        result = box.call("lookup_order_status", {"order_id": ORDER})
        self.assertEqual(result[0], "executed")
        box.begin_step()

    def test_delivered_order_can_be_refunded_after_the_lookup(self):
        box = self.toolbox()
        self.read_order(box)
        result = box.call("refund_order", {"order_id": ORDER, "amount": 20})
        self.assertTrue(result[2].allowed)
        self.assertEqual(box.ledger.refunds, [{"order_id": ORDER, "amount": 20.0}])

    def test_delivery_is_checked_at_the_time_of_the_write(self):
        box = self.toolbox()
        self.read_order(box)
        self.orders[ORDER]["statut"] = "expédiée"
        status, _, decision = box.call("refund_order", {"order_id": ORDER, "amount": 20})
        self.assertEqual((status, decision.reason, decision.effective_privilege),
                         ("denied", "delivery-condition-not-met", "none"))
        self.assertEqual(box.ledger.refunds, [])

    def test_direct_request_needs_no_delivery_lookup_and_is_executed_once(self):
        self.orders[ORDER]["statut"] = "en préparation"
        box = self.toolbox("Remboursez-moi 20 $ pour ma commande T2048, s’il vous plaît.")
        args = {"order_id": ORDER, "amount": 20}
        self.assertTrue(box.call("refund_order", args)[2].allowed)
        self.assertEqual(box.call("refund_order", args)[2].reason, "refund-already-executed")
        self.assertEqual(len(box.ledger.refunds), 1)

    def test_requests_outside_the_supported_grammar_require_review(self):
        box = self.toolbox("Je voudrais parler à quelqu’un au sujet de ma commande T2048.")
        decision = box.call("refund_order", {"order_id": ORDER, "amount": 20})[2]
        self.assertEqual(decision.reason, "refund-request-needs-review")
        self.assertEqual(box.ledger.refunds, [])

    def test_an_unmet_condition_does_not_consume_a_valid_approval(self):
        box = self.toolbox("Si ma commande T2048 est livrée, remboursez-moi 60 $.")
        args = {"order_id": ORDER, "amount": 60}
        token = box.approvals.issue(box.identity, "refund_order", args, NOW)
        args["approval_token"] = token
        self.read_order(box)
        self.orders[ORDER]["statut"] = "en préparation"
        self.assertEqual(box.call("refund_order", args)[2].reason, "delivery-condition-not-met")
        self.orders[ORDER]["statut"] = "livrée"
        self.assertTrue(box.call("refund_order", args)[2].allowed)
        self.assertEqual(len(box.ledger.refunds), 1)

    def test_owner_check_still_precedes_the_refund_precondition(self):
        other = replace(IDENTITY, subject="other")
        box = self.toolbox(identity=other)
        decision = box.call("refund_order", {"order_id": ORDER, "amount": 20})[2]
        self.assertEqual(decision.reason, "not-owner")
        self.assertEqual(box.ledger.refunds, [])

    def test_direct_partial_refunds_and_requests_about_delay_keep_the_explicit_amount(self):
        requests = (
            "Je demande un remboursement partiel de 20 $ pour la commande T2048.",
            "Je veux 20 $ de remboursement pour T2048 ; dans combien de temps vais-je le recevoir ?",
        )
        for request in requests:
            with self.subTest(request=request):
                intent = refund_intents(request)[ORDER]
                self.assertEqual(intent.amount, Decimal("20"))
                self.assertFalse(intent.delivery_required)

    def test_exact_amounts_can_be_bound_to_two_different_orders(self):
        intents = refund_intents("Je veux deux remboursements : 12,50 $ pour T2048 et 15 $ pour T2049.")
        self.assertEqual({order: intent.amount for order, intent in intents.items()},
                         {"T2048": Decimal("12.50"), "T2049": Decimal("15")})


class DevelopmentRefundWorkflowTests(unittest.TestCase):
    def test_scripted_conditional_requests_on_development_partitions(self):
        corpus = load_corpus(CORPUS / "templates.json")
        split = load_frozen(corpus, CORPUS / "split.json")
        selected = tuple(s for s in corpus.scenarios if s.family == "verifier_puis_rembourser"
                         and split[s.group_id] in ("train", "validation"))
        corpus = replace(corpus, scenarios=selected)
        orders = json.loads((CORPUS / "orders.json").read_text(encoding="utf-8"))
        release = load_release(ROOT / "configs/releases/r9-refund-guard.yaml")
        policy = load_policy(CORPUS / "policy.json")
        replies = {}
        expected_refunds = 0
        for scenario in selected:
            intents = refund_intents(scenario.question)
            self.assertEqual(len(intents), 1)
            order_id, intent = next(iter(intents.items()))
            self.assertTrue(intent.delivery_required)
            steps = [{"tool_calls": [{"name": "lookup_order_status", "arguments": {"order_id": order_id}}]}]
            if orders[order_id]["statut"] == "livrée":
                expected_refunds += 1
                steps.append({"tool_calls": [{"name": "refund_order", "arguments": {
                    "order_id": order_id, "amount": float(intent.amount),
                }}]})
            steps.append({"content": "Vérification de la demande terminée."})
            replies[scenario.scenario_id] = steps
        self.assertGreater(expected_refunds, 0)
        self.assertLess(expected_refunds, len(selected))
        with tempfile.TemporaryDirectory() as tmp:
            script, output = Path(tmp) / "replies.json", Path(tmp) / "runs.jsonl"
            script.write_text(json.dumps(replies), encoding="utf-8")
            collect(release, corpus, split, policy, CORPUS / "kb", orders, ("TEST-REFUND-GUARD-CANARY",), output,
                    adapter=ScriptedAdapter(script), clock=lambda: NOW)
            rows = load_records(output)
        self.assertEqual(len(rows), len(selected))
        self.assertEqual(sum(len(row["refunds"]) for row in rows), expected_refunds)
        self.assertTrue(all(row["business"] == "SUCCESS" and row["permission"] == "OK" for row in rows))
