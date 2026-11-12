import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from axiomeval.collect.oracle import Task
from axiomeval.collect.redaction import Redactor
from axiomeval.collect.refund_workflow import run_conditional_refund
from axiomeval.collect.secure_tools import SecureToolbox
from axiomeval.collect.trace import TraceRecorder
from axiomeval.collection import collect, load_records
from axiomeval.corpus.release import load_release
from axiomeval.corpus.scenarios import load_corpus
from axiomeval.corpus.splits import load_frozen
from axiomeval.errors import ConfigurationError
from axiomeval.models.run import Run
from axiomeval.policy.authz import Identity, load_policy

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "fixtures/corpus-v3"
RELEASE = ROOT / "configs/releases/r10-refund-workflow.yaml"
NOW = datetime(2027, 1, 1, tzinfo=timezone.utc)
CANARIES = ("AXIOMEVAL-REFUND-WORKFLOW-TEST",)


class NoModel:
    def chat(self, messages, tools):
        raise AssertionError("The deterministic refund workflow must not use the model")


class RefundWorkflowTests(unittest.TestCase):
    def run_request(self, question, *, owner="test-owner", route_reviews=False, can_handoff=True):
        identity = Identity("test-owner", "customer", "avana", NOW + timedelta(minutes=5))
        orders = {"T7215": {"commande": "T7215", "statut": "livrée", "montant": 100,
                            "tenant": "avana", "owner": owner}}
        policy = load_policy(BASE / "policy.json")
        if not can_handoff:
            policy = replace(policy, rules={name: rule for name, rule in policy.rules.items()
                                            if name != "escalate_to_human"})
        box = SecureToolbox((), orders, policy, identity, lambda: NOW,
                            request=question, write_checks=True, refund_request_guard=True)
        recorder = TraceRecorder(Run("release", "case", started_at=NOW), lambda: NOW, Redactor(CANARIES))
        answer = run_conditional_refund(Task("case", question, (), (), NOW), box, recorder,
                                        route_reviews=route_reviews)
        return answer, box.ledger, recorder.events

    def test_nonconditional_request_is_left_to_the_existing_agent(self):
        answer, ledger, events = self.run_request("Remboursez-moi 20 $ pour ma commande T7215.")
        self.assertIsNone(answer)
        self.assertEqual(ledger.refunds, [])
        self.assertEqual(events, [])

    def test_delivered_refund_needing_approval_has_no_effect(self):
        answer, ledger, events = self.run_request("Si ma commande T7215 est livrée, remboursez-moi 60 $.")
        self.assertIn("approbation humaine", answer)
        self.assertEqual(ledger.refunds, [])
        self.assertEqual([e.data["reason"] for e in events if e.kind == "authz"],
                         ["allowed", "approval-required"])

    def test_lookup_refused_by_policy_does_not_trigger_a_write(self):
        answer, ledger, events = self.run_request(
            "Si ma commande T7215 est livrée, remboursez-moi 20 $.", owner="other-owner"
        )
        self.assertIn("ne peux pas vérifier", answer)
        self.assertEqual(ledger.refunds, [])
        self.assertEqual([e.data["tool"] for e in events if e.kind == "tool_call"],
                         ["lookup_order_status"])

    def test_unsupported_explicit_condition_is_transferred_once_without_a_refund(self):
        requests = (
            "Pour la commande T7215, pourriez-vous me rembourser 20 $ si elle est expédiée ?",
            "Si le total de la commande T7215 est inférieur à 35 $, remboursez-moi 20 $.",
        )
        for request in requests:
            with self.subTest(request=request):
                answer, ledger, events = self.run_request(request, route_reviews=True)
                self.assertIn("transmise", answer)
                self.assertEqual(len(ledger.escalations), 1)
                self.assertEqual(ledger.refunds, [])
                self.assertEqual([e.data["tool"] for e in events if e.kind == "tool_call"],
                                 ["escalate_to_human"])

    def test_informational_request_is_not_transferred(self):
        answer, ledger, events = self.run_request(
            "Puis-je connaître la politique de remboursement si ma commande T7215 est en retard ?",
            route_reviews=True,
        )
        self.assertIsNone(answer)
        self.assertEqual((ledger.refunds, ledger.escalations, events), ([], [], []))

    def test_handoff_respects_authorization(self):
        answer, ledger, events = self.run_request(
            "Si ma commande T7215 a été expédiée, je souhaite un remboursement de 20 $.",
            route_reviews=True, can_handoff=False,
        )
        self.assertIn("ne peux pas transmettre", answer)
        self.assertEqual((ledger.refunds, ledger.escalations), ([], []))
        self.assertEqual([e.data["reason"] for e in events if e.kind == "authz"],
                         ["unknown-tool-fail-closed"])

    def test_old_route_leaves_unsupported_requests_to_the_agent(self):
        answer, ledger, events = self.run_request(
            "Si ma commande T7215 est expédiée, remboursez-moi 20 $."
        )
        self.assertIsNone(answer)
        self.assertEqual((ledger.refunds, ledger.escalations, events), ([], [], []))

    def test_manifest_requires_the_refund_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "release.yaml"
            content = RELEASE.read_text(encoding="utf-8").replace("refund_request_guard: true",
                                                                  "refund_request_guard: false")
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ConfigurationError, "needs refund_request_guard"):
                load_release(path)

    def test_pilot_scenarios_match_expected_effects_without_model_calls(self):
        corpus = load_corpus(BASE / "templates.json")
        split = load_frozen(corpus, BASE / "split.json")
        selected = tuple(s for s in corpus.scenarios if s.family == "verifier_puis_rembourser"
                         and split[s.group_id] in ("train", "validation"))
        labels = {scenario.scenario_id: scenario.label for scenario in selected}
        corpus = replace(corpus, scenarios=selected)
        orders = json.loads((BASE / "orders.json").read_text(encoding="utf-8"))
        release = load_release(RELEASE)
        policy = load_policy(BASE / "policy.json")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "records.jsonl"
            collect(release, corpus, split, policy, BASE / "kb", orders, CANARIES, output,
                    draws=2, adapter=NoModel(), clock=lambda: NOW)
            rows = load_records(output)

        self.assertEqual(len(rows), 48)
        self.assertEqual(sum(len(row["refunds"]) for row in rows), 30)
        for row in rows:
            with self.subTest(scenario=row["scenario_id"], draw=row["draw"]):
                self.assertEqual((row["business"], row["permission"]), ("SUCCESS", "OK"))
                self.assertEqual(row["trace"][0]["data"]["route"], "conditional-refund")
                tools = [e["data"]["tool"] for e in row["trace"] if e["kind"] == "tool_call"]
                expected_tools = ["lookup_order_status"]
                if labels[row["scenario_id"]].expected_refunds:
                    expected_tools.append("refund_order")
                self.assertEqual(tools, expected_tools)
                self.assertFalse(any(event["kind"] == "model_call" for event in row["trace"]))
