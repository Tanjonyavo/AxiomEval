import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from axiomeval.cli import main
from axiomeval.collect.adapters import OllamaAdapter, ScriptedAdapter
from axiomeval.collection import load_records
from axiomeval.corpus.scenarios import load_corpus
from axiomeval.errors import ValidationError
from axiomeval.policies.gate import Verdict
from axiomeval.stats.paired import Protocol, non_inferior, paired_comparison, release_verdict
from axiomeval.stats.plan import BoundRelease, ComparisonEvidence, freeze_comparison, load_comparison
from test_release_pairing import run

MODEL_DIGEST = "a" * 64
ENVIRONMENT_DIGEST = "b" * 64
BASE_DIGEST = "c" * 64
CANDIDATE_DIGEST = "d" * 64


class CostDecisionTests(unittest.TestCase):
    def test_analytic_cost_sign_and_upper_bound(self):
        # Candidate incurs one additional failure among two independent groups.
        # At alpha = exp(-1), the radius is 2 sqrt(1 / (2 * 2)) = 1.
        baseline = [run("a", 0, "base"), run("b", 0, "base")]
        candidate = [run("a", 0, "cand", "FAILURE"), run("b", 0, "cand")]
        protocol = Protocol(alpha=math.exp(-1.0), margin=0.5, min_groups=2)
        result = paired_comparison(baseline, candidate, protocol)
        self.assertEqual(result.cost_difference, 0.5)
        self.assertEqual(result.hoeffding_radius, 1.0)
        self.assertEqual(result.cost_upper, 1.0)  # Clipped to the possible cost difference.
        reversed_result = paired_comparison(candidate, baseline, protocol)
        self.assertEqual((reversed_result.cost_difference, reversed_result.cost_upper), (-0.5, 0.5))
        verdict = release_verdict(candidate, baseline, protocol)
        self.assertEqual((verdict.verdict, verdict.reasons), (Verdict.HOLD, ("non-inferiority-not-shown",)))

    def test_strict_boundary_and_inconclusive_result(self):
        self.assertTrue(non_inferior(0.099, 0.10))
        self.assertFalse(non_inferior(0.10, 0.10))
        self.assertFalse(non_inferior(0.101, 0.10))
        self.assertFalse(non_inferior(float("nan"), 0.10))

    def test_degenerate_and_missing_scores_are_never_favorable(self):
        base = [run(str(i), 0, "base") for i in range(30)]
        cand = [dict(row, release_digest="cand") for row in base]
        cases = (
            (base, cand, Verdict.HOLD, "zero-variance"),
            (base[:1], cand[:1], Verdict.HOLD, "too-few-groups:1<2"),
            (base, [dict(cand[0], business=float("nan")), *cand[1:]], Verdict.INCOMPLETE, "invalid-business-score"),
            ([dict(base[0], business="MISSING"), *base[1:]], cand, Verdict.INCOMPLETE, "baseline-missing-answers"),
        )
        for left, right, verdict, reason in cases:
            with self.subTest(reason=reason):
                result = release_verdict(left, right, Protocol(margin=1, min_groups=2))
                self.assertEqual(result.verdict, verdict)
                self.assertIn(reason, result.reasons)


class FrozenComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "plan.json"
        self.protocol = Protocol(min_groups=2)
        pairs = frozenset({("a", "a-v0", 0), ("b", "b-v0", 0)})
        self.partitions = {"a": "test", "b": "test"}
        self.binding = ComparisonEvidence(
            BoundRelease(BASE_DIGEST, MODEL_DIGEST), BoundRelease(CANDIDATE_DIGEST, MODEL_DIGEST),
            ENVIRONMENT_DIGEST, "test-evaluator",
        )
        self.sha = freeze_comparison(self.path, self.protocol, "test-corpus", pairs,
                                     self.partitions, self.binding)
        self.plan = load_comparison(self.path, self.protocol)

    def evidence(self, release):
        return [dict(run(group, 0, release), corpus_digest=self.plan.corpus_digest,
                     started_at=self.plan.frozen_at.isoformat(), comparison_plan_sha256=self.sha,
                     partition="test", model_digest=MODEL_DIGEST, environment_digest=ENVIRONMENT_DIGEST,
                     evaluator="test-evaluator")
                for group in ("a", "b")]

    def test_margin_change_and_overwrite_are_refused(self):
        with self.assertRaisesRegex(ValidationError, "configuration changed.*margin"):
            load_comparison(self.path, Protocol(margin=0.20, min_groups=2))
        with self.assertRaisesRegex(ValidationError, "cannot be overwritten"):
            freeze_comparison(self.path, self.protocol, "test-corpus", self.plan.pairs,
                              self.partitions, self.binding)

    def test_modified_plan_is_refused(self):
        contents = json.loads(self.path.read_text())
        contents["runs"].pop()
        self.path.write_text(json.dumps(contents))
        with self.assertRaisesRegex(ValidationError, "SHA-256 does not match"):
            load_comparison(self.path, self.protocol)

    def test_incomplete_even_when_both_sides_miss_same_draw(self):
        base, cand = self.evidence(BASE_DIGEST), self.evidence(CANDIDATE_DIGEST)
        result = self.plan.verdict(base[:1], cand[:1])
        self.assertEqual(result.verdict, Verdict.INCOMPLETE)
        self.assertIn("runs-do-not-match-frozen-plan", result.reasons)

    def test_runs_from_before_freeze_or_another_plan_are_refused(self):
        base, cand = self.evidence(BASE_DIGEST), self.evidence(CANDIDATE_DIGEST)
        self.assertEqual(self.plan.verdict(base, cand).verdict, Verdict.HOLD)
        older = (self.plan.frozen_at - timedelta(seconds=1)).isoformat()
        for changed in (dict(cand[0], started_at=older), dict(cand[0], comparison_plan_sha256="other")):
            with self.subTest(changed=changed):
                result = self.plan.verdict(base, [changed, cand[1]])
                self.assertEqual(result.verdict, Verdict.INCOMPLETE)
                self.assertIn("runs-not-collected-under-frozen-plan", result.reasons)
        self.assertIn("frozen-comparison-plan-required", release_verdict(base, cand, self.protocol).reasons)

    def test_critical_finding_precedes_plan_and_pairing_errors(self):
        base, cand = self.evidence(BASE_DIGEST), self.evidence(CANDIDATE_DIGEST)
        cand[0]["permission"] = "VIOLATION"
        self.assertEqual(self.plan.verdict(base, cand[:1]).verdict, Verdict.REJECT)
        cand[0]["comparison_plan_sha256"] = "other"
        self.assertEqual(self.plan.verdict(base, cand[:1]).verdict, Verdict.INCOMPLETE)

    def test_role_substitution_and_shared_context_change_are_refused(self):
        base, cand = self.evidence(BASE_DIGEST), self.evidence(CANDIDATE_DIGEST)
        cases = {
            "swapped": (cand, base),
            "candidate substituted": (base, [dict(r, release_digest="e" * 64) for r in cand]),
            "shared environment": ([dict(r, environment_digest="e" * 64) for r in base],
                                   [dict(r, environment_digest="e" * 64) for r in cand]),
            "shared evaluator": ([dict(r, evaluator="new") for r in base],
                                 [dict(r, evaluator="new") for r in cand]),
            "wrong model": (base, [dict(r, model_digest="e" * 64) for r in cand]),
            "wrong partition": (base, [dict(r, partition="train") for r in cand]),
        }
        for name, (left, right) in cases.items():
            with self.subTest(name=name):
                result = self.plan.verdict(left, right)
                self.assertEqual(result.verdict, Verdict.INCOMPLETE)
                self.assertIn("runs-not-collected-under-frozen-plan", result.reasons)

    def test_cli_freezes_collects_resumes_and_compares(self):
        output = self.root / "comparison.json"
        base, cand = self.root / "base.jsonl", self.root / "candidate.jsonl"
        source = Path("fixtures/corpus")
        corpus = load_corpus(source / "templates.json")
        script = self.root / "script.json"
        script.write_text(json.dumps({s.scenario_id: [{"content": "Fixture."}]
                                      for s in corpus.scenarios}), encoding="utf-8")
        adapter = ScriptedAdapter(script)
        log, err = io.StringIO(), io.StringIO()
        with redirect_stdout(log), redirect_stderr(err), patch.object(
                adapter, "model_digest", return_value=MODEL_DIGEST, create=True) as model_digest:
            self.assertEqual(main(["freeze-comparison", "--out", str(output),
                                   "--baseline-release", "configs/releases/r1-baseline.yaml",
                                   "--candidate-release", "configs/releases/r2-hardened.yaml",
                                   "--baseline-model-digest", MODEL_DIGEST,
                                   "--candidate-model-digest", MODEL_DIGEST]), 0)
            for release, path in (("r1-baseline", base), ("r2-hardened", cand)):
                args = ["collect", "--release", f"configs/releases/{release}.yaml", "--out", str(path),
                        "--comparison-plan", str(output), "--limit", "1"]
                with patch("axiomeval.collection.OllamaAdapter", return_value=adapter):
                    self.assertEqual(main(args), 0, err.getvalue())
                    self.assertEqual(main(args), 0, err.getvalue())
                self.assertEqual(len(load_records(path)), 1)
            args = ["compare", "--baseline", str(base), "--candidate", str(cand), "--comparison-plan", str(output)]
            self.assertEqual(main(args), 11, err.getvalue())
            self.assertIn("runs-do-not-match-frozen-plan", log.getvalue())
            self.assertEqual(main([*args, "--margin", "0.2"]), 2)
            self.assertIn("frozen by the comparison plan", err.getvalue())

            collect_args = ["collect", "--release", "configs/releases/r2-hardened.yaml",
                            "--comparison-plan", str(output)]
            third_release = self.root / "third.jsonl"
            third_args = ["collect", "--release", "configs/releases/r3-degraded.yaml",
                          "--comparison-plan", str(output), "--out", str(third_release)]
            with patch("axiomeval.collection.OllamaAdapter", return_value=adapter) as factory:
                self.assertEqual(main(third_args), 2)
                factory.assert_not_called()
                self.assertFalse(third_release.exists())

                self.assertEqual(main([*collect_args, "--out", str(base)]), 2)
                self.assertEqual(len(load_records(base)), 1)

                model_digest.return_value = "e" * 64
                wrong_model = self.root / "wrong-model.jsonl"
                self.assertEqual(main([*collect_args, "--out", str(wrong_model)]), 2)
                self.assertFalse(wrong_model.exists())
                model_digest.return_value = MODEL_DIGEST

                drifting_model = self.root / "drifting-model.jsonl"
                model_digest.side_effect = [MODEL_DIGEST, "e" * 64]
                self.assertEqual(main([*collect_args, "--out", str(drifting_model), "--limit", "1"]), 2)
                self.assertEqual(load_records(drifting_model), [])
                model_digest.side_effect = None

                for release, path in (("r1-baseline", base), ("r2-hardened", cand)):
                    self.assertEqual(main(["collect", "--release", f"configs/releases/{release}.yaml",
                                           "--comparison-plan", str(output), "--out", str(path)]), 0, err.getvalue())

            self.assertEqual(main(args), 12)
            self.assertIn("zero-variance", log.getvalue())
            self.assertEqual(main(["compare", "--baseline", str(cand), "--candidate", str(base),
                                   "--comparison-plan", str(output)]), 11)
            self.assertIn("runs-not-collected-under-frozen-plan", log.getvalue())

            exploratory = self.root / "exploratory.jsonl"
            with patch("axiomeval.collection.OllamaAdapter", return_value=adapter):
                args = ["collect", "--release", "configs/releases/r2-hardened.yaml",
                        "--out", str(exploratory), "--limit", "1"]
                self.assertEqual(main(args), 0)
                self.assertEqual(main(args), 0)
            self.assertIsNone(load_records(exploratory)[0]["comparison_plan_sha256"])
            self.assertEqual(main(["compare", "--baseline", str(base), "--candidate", str(exploratory)]), 11)
            self.assertIn("frozen-comparison-plan-required", log.getvalue())


class ModelIdentityTests(unittest.TestCase):
    def test_ollama_resolves_the_configured_tag(self):
        adapter = OllamaAdapter("http://127.0.0.1:11434", "example", 0.0, 0, 1)
        payload = {"models": [{"name": "another:latest", "digest": "e" * 64},
                              {"name": "example:latest", "digest": MODEL_DIGEST}]}
        with patch.object(adapter, "_get", return_value=payload) as get:
            self.assertEqual(adapter.model_digest(), MODEL_DIGEST)
            get.assert_called_once_with("/api/tags")
        with patch.object(adapter, "_get", return_value={"models": []}):
            with self.assertRaisesRegex(ValidationError, "installed model digest is unavailable"):
                adapter.model_digest()
