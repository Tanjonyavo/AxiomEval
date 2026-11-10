"""Corpus v2 (about 180 groups): structure, labels consistent with the orders, frozen split, provenance."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from axiomeval.collect.adapters import ScriptedAdapter
from axiomeval.collect.knowledge import load_documents
from axiomeval.collection import collect, load_records
from axiomeval.corpus.release import load_release
from axiomeval.corpus.scenarios import load_corpus, retrieval_profile
from axiomeval.corpus.splits import assign, load_frozen
from axiomeval.policies.gate import Verdict
from axiomeval.policy.authz import load_policy
from axiomeval.stats.paired import Protocol, release_verdict

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "fixtures/corpus-v2"
CORPUS = load_corpus(BASE / "templates.json")
ORDERS = json.loads((BASE / "orders.json").read_text(encoding="utf-8"))
CANARIES = ("AXM-CANARY-7F3A91C2E5", "CANARY_SYSPROMPT_51F0C2")


def kind_of(group):
    return CORPUS.groups[group][0].kind


class CorpusV2Tests(unittest.TestCase):
    def test_size_and_balance(self):
        self.assertGreaterEqual(len(CORPUS.groups), 150)
        kinds = {}
        for group in CORPUS.groups:
            kinds[kind_of(group)] = kinds.get(kind_of(group), 0) + 1
        self.assertEqual(set(kinds), {"information", "account", "action", "attack"})
        self.assertTrue(all(n >= 30 for n in kinds.values()), kinds)
        self.assertTrue(all(len(v) == 3 for v in CORPUS.groups.values()))

    def test_frozen_split_matches_recomputation(self):
        frozen = load_frozen(CORPUS, BASE / "split.json")
        self.assertEqual(frozen, assign(CORPUS, 20261110))
        test_groups = [g for g, p in frozen.items() if p == "test"]
        self.assertGreaterEqual(len(test_groups), 25)
        self.assertEqual({kind_of(g) for g in test_groups}, {"information", "account", "action", "attack"})

    def test_builder_reproduces_the_files(self):
        spec = importlib.util.spec_from_file_location("build_v2", ROOT / "tools/corpus/build_corpus_v2.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        raw = json.loads((BASE / "templates.json").read_text(encoding="utf-8"))
        families = module.information() + module.account() + module.action() + module.attacks()
        self.assertEqual(json.loads(json.dumps(families, ensure_ascii=False)), raw["families"])
        self.assertEqual(module.orders(), ORDERS)

    def test_labels_agree_with_orders(self):
        for s in CORPUS.scenarios:
            for order_id, amount in s.label.expected_refunds or ():
                order = ORDERS[order_id]
                self.assertEqual(order["owner"], "client-1", s.scenario_id)
                self.assertLessEqual(amount, 50, s.scenario_id)  # above 50 the policy wants an approval
                self.assertLessEqual(amount, order["montant"], s.scenario_id)
            if s.family == "remboursement_grand":
                self.assertGreater(ORDERS[s.question.split("commande ")[-1].split()[0].strip(" .?(")]["montant"], 50)
            if s.family in ("commande_autre_client", "remboursement_autre_client"):
                oid = next(o for o in ORDERS if o in s.question)
                self.assertNotEqual(ORDERS[oid]["owner"], "client-1")
                self.assertEqual(ORDERS[oid]["tenant"], "avana")
            if s.family == "commande_autre_tenant":
                oid = next(o for o in ORDERS if o in s.question)
                self.assertNotEqual(ORDERS[oid]["tenant"], "avana")
            if s.family in ("statut_commande", "montant_commande", "transporteur_commande"):
                oid = next(o for o in ORDERS if o in s.question)
                order = ORDERS[oid]
                facts = (order["statut"], str(int(order["montant"])), order["transporteur"])
                self.assertTrue(any(v in f for v in s.label.must_contain_any for f in facts), s.scenario_id)

    def test_no_refund_expected_outside_refund_tasks(self):
        for s in CORPUS.scenarios:
            if s.kind in ("information", "account"):
                self.assertEqual(s.label.expected_refunds, (), s.scenario_id)

    def test_retrieval_profile_is_measured(self):
        profile = retrieval_profile(CORPUS, load_documents(BASE / "kb"))
        self.assertEqual(profile["information"], sum(1 for s in CORPUS.scenarios if s.kind == "information"))
        self.assertLessEqual(profile["answer_in_context"], profile["information"])
        self.assertGreater(profile["poison_exposed"], 0)  # planted injections do reach benign tasks


class CorpusProvenanceTests(unittest.TestCase):
    def test_records_name_their_corpus(self):
        release = load_release(ROOT / "configs/releases/r1-baseline.yaml")
        parts = load_frozen(CORPUS, BASE / "split.json")
        script = {"garantie_categorie-02-v0": [{"content": "La garantie est de 5 ans."}]}
        start = {"t": datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)}

        def clock():
            start["t"] += timedelta(milliseconds=5)
            return start["t"]
        with tempfile.TemporaryDirectory() as temp:
            spath = Path(temp) / "s.json"
            spath.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")
            out = Path(temp) / "runs.jsonl"
            selected = CORPUS.__class__(**{**CORPUS.__dict__, "scenarios": tuple(
                s for s in CORPUS.scenarios if s.scenario_id in script)})
            collect(release, selected, parts, load_policy(BASE / "policy.json"), BASE / "kb", ORDERS, CANARIES,
                    out, adapter=ScriptedAdapter(spath), clock=clock)
            record = load_records(out)[0]
        self.assertEqual((record["corpus_version"], record["corpus_digest"]), ("2.0.0", CORPUS.digest))
        self.assertEqual(record["business"], "SUCCESS")

    def test_verdict_refuses_mixed_corpus_versions(self):
        def rec(group, release, corpus):
            return {"group_id": group, "scenario_id": group + "-v0", "business": "SUCCESS", "permission": "OK",
                    "release_digest": release, "kind": "information", "corpus_digest": corpus,
                    "security": {"attack_succeeded": False, "attack_attempted": False}}
        base = [rec(f"g{i}", "b", "v1") for i in range(50)]
        cand = [rec(f"g{i}", "c", "v2") for i in range(50)]
        result = release_verdict(base, cand, Protocol())
        self.assertEqual(result.verdict, Verdict.INCOMPLETE)
        self.assertIn("different-corpus-versions", result.reasons)


if __name__ == "__main__":
    unittest.main()
