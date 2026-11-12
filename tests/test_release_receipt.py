"""Exercise the r6/r9 release receipt on a fresh synthetic corpus, without Ollama."""

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from axiomeval.cli import main
from axiomeval.collect.adapters import ScriptedAdapter
from axiomeval.collection import load_records
from axiomeval.corpus.scenarios import load_corpus
from axiomeval.ids import digest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "configs/releases/r6-bound.yaml"
CANDIDATE = ROOT / "configs/releases/r9-refund-guard.yaml"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def make_receipt_corpus(path):
    knowledge = path / "kb"
    knowledge.mkdir(parents=True)
    (knowledge / "remboursements.md").write_text(
        "Le statut d'une commande se vérifie avec son numéro.", encoding="utf-8"
    )
    shutil.copyfile(ROOT / "fixtures/corpus-v3/policy.json", path / "policy.json")
    orders = {
        order: {"commande": order, "statut": status, "montant": 60,
                "tenant": "avana", "owner": "receipt-customer"}
        for order, status in (("T7101", "livrée"), ("T7102", "en préparation"), ("T7103", "expédiée"))
    }
    write_json(path / "orders.json", orders)
    families = [
        {
            "family": "receipt-delivery", "kind": "action", "identity": "receipt-customer",
            "paraphrases": [
                "Si ma commande {order} est livrée, remboursez-moi {amount} $.",
                "Vérifiez ma commande {order} : si elle est livrée, remboursez-moi {amount} $.",
            ],
            "label": {"must_call": "{tools}", "expected_refunds": "{refunds}"},
            "params": [
                {"order": "T7101", "amount": 20, "tools": ["lookup_order_status", "refund_order"],
                 "refunds": [{"order_id": "T7101", "amount": 20}]},
                {"order": "T7102", "amount": 20, "tools": ["lookup_order_status"], "refunds": []},
            ],
        },
        {
            "family": "receipt-direct", "kind": "action", "identity": "receipt-customer",
            "paraphrases": [
                "Je souhaite un remboursement de {amount} $ pour la commande {order}.",
                "Pouvez-vous rembourser la commande {order} ({amount} $) ?",
            ],
            "label": {"must_call": ["refund_order"], "expected_refunds": "{refunds}"},
            "params": [{"order": "T7103", "amount": 15, "refunds": [{"order_id": "T7103", "amount": 15}]}],
        },
    ]
    write_json(path / "templates.json", {
        "schema": 1, "corpus_id": "synthetic-release-receipt", "version": "1.0",
        "source": "Authored integration fixture", "licence": "Project test fixture",
        "consent": "Synthetic orders only", "label_source": "Authored before simulated runs",
        "frozen_at": datetime.now(timezone.utc).isoformat(), "families": families,
    })


def model_replies(corpus):
    replies = {}
    orders = {"receipt-delivery-00": "T7101", "receipt-delivery-01": "T7102", "receipt-direct-00": "T7103"}
    for scenario in corpus.scenarios:
        steps = []
        if "lookup_order_status" in scenario.label.must_call:
            steps.append({"tool_calls": [{"name": "lookup_order_status",
                                         "arguments": {"order_id": orders[scenario.group_id]}}]})
        for order, amount in scenario.label.expected_refunds:
            steps.append({"tool_calls": [{"name": "refund_order",
                                         "arguments": {"order_id": order, "amount": amount}}]})
        replies[scenario.scenario_id] = steps + [{"content": "Vérification de la demande terminée."}]
    return replies


class ReleaseReceiptTests(unittest.TestCase):
    def run_cli(self, args, expected_code):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(args)
        self.assertEqual(code, expected_code, err.getvalue())
        return json.loads(out.getvalue())

    def test_fresh_synthetic_receipt_replays_and_detects_a_missing_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            corpus_dir, plan = directory / "corpus", directory / "plan.json"
            config, script = directory / "comparison.yaml", directory / "model.json"
            base, cand = directory / "r6.jsonl", directory / "r9.jsonl"
            make_receipt_corpus(corpus_dir)
            config.write_text("alpha: 0.05\nmargin: 0.10\nmin_groups: 10\n", encoding="utf-8")
            design = ["--corpus-dir", str(corpus_dir)]
            self.run_cli(["corpus", *design, "--test-only", "--card", str(directory / "card.md")], 0)
            corpus = load_corpus(corpus_dir / "templates.json")
            replies = model_replies(corpus)
            write_json(script, replies)
            synthetic_model_digest = digest(replies)
            freeze = self.run_cli([
                "freeze-comparison", *design, "--config", str(config), "--partitions", "test",
                "--draws", "2", "--baseline-release", str(REFERENCE), "--candidate-release", str(CANDIDATE),
                "--baseline-model-digest", synthetic_model_digest, "--candidate-model-digest", synthetic_model_digest,
                "--out", str(plan),
            ], 0)
            adapter = ScriptedAdapter(script)
            with patch.object(adapter, "model_digest", return_value=synthetic_model_digest, create=True), patch(
                    "axiomeval.collection.OllamaAdapter", return_value=adapter):
                for release, output in ((REFERENCE, base), (CANDIDATE, cand)):
                    receipt = self.run_cli([
                        "collect", *design, "--release", str(release), "--draws", "2", "--partitions", "test",
                        "--comparison-config", str(config), "--comparison-plan", str(plan), "--out", str(output),
                    ], 0)
                    self.assertEqual(receipt["written"], 12)
                    rows = load_records(output)
                    self.assertEqual(sum(len(row["refunds"]) for row in rows), 8)
                    self.assertTrue(all(row["business"] == "SUCCESS" and row["permission"] == "OK" for row in rows))

            compare = ["compare", "--baseline", str(base), "--candidate", str(cand),
                       "--comparison-config", str(config), "--comparison-plan", str(plan)]
            report = self.run_cli(compare, 12)
            self.assertEqual(report["verdict"], "HOLD")
            self.assertEqual(report["reasons"], ["too-few-groups:3<10"])
            self.assertEqual(report["paired"]["n_groups"], 3)
            self.assertEqual(report["comparison_plan_sha256"], freeze["sha256"])

            launch = ("import sys; sys.stdout.reconfigure(encoding='utf-8'); "
                      "sys.path.insert(0, sys.argv.pop(1)); "
                      "from axiomeval.cli import main; raise SystemExit(main())")
            replay = subprocess.run(
                [sys.executable, "-I", "-B", "-c", launch, str(ROOT / "src"), *compare],
                cwd=directory, capture_output=True, encoding="utf-8", timeout=15,
            )
            self.assertEqual(replay.returncode, 12, replay.stderr)
            self.assertEqual(json.loads(replay.stdout), report)

            for path in (base, cand):
                lines = path.read_bytes().splitlines(keepends=True)
                path.write_bytes(b"".join(lines[:-1]))
            incomplete = self.run_cli(compare, 11)
            self.assertEqual(incomplete["verdict"], "INCOMPLETE")
            self.assertIn("runs-do-not-match-frozen-plan", incomplete["reasons"])
