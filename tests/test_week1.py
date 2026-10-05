"""Behavioral checks of the S1 boundary, evidence chain and CLI."""
import ast
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from axiomeval.config import load_config
from axiomeval.demo import run_demo
from axiomeval.errors import ConfigurationError, ValidationError
from axiomeval.evaluators.deterministic import evaluate
from axiomeval.models import Evidence, Run, Scenario, Target, make_evidence
from axiomeval.policies.gate import Verdict, decide
from axiomeval.reporting.reports import write_reports

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/default.yaml"


class ConfigTests(unittest.TestCase):
    def parse(self, content):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            return load_config(path)

    def test_default_schema(self):
        config = load_config(CONFIG)
        self.assertEqual(config.target.release, "synthetic-v1")
        self.assertEqual(config.required_evidence_count, 1)

    def test_unreadable_path(self):
        with self.assertRaises(ConfigurationError):
            load_config(ROOT / "does-not-exist.yaml")

    def test_empty_scalar_sequence_malformed_and_unsafe_yaml(self):
        for value in ("", "null", "42", "[]", "key: [", "!!python/object/apply:os.system ['echo unsafe']"):
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                self.parse(value)

    def test_duplicate_keys_and_nonstring_keys(self):
        for value in ("project: a\nproject: b", "1: a", "? [x, y]\n: z"):
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                self.parse(value)

    def test_unknown_fields_and_wrong_types(self):
        for section, key, value in (
            ("project", "name", "Other"), ("logging", "level", "NOTSET"),
            ("target", "forbidden_tools", []), ("target", "forbidden_tools", "export"),
            ("target", "forbidden_tools", ["same", "same"]),
            ("target", "name", 5), ("scenario", "attack_input", "  "),
            ("policy", "required_evidence_count", True),
            ("policy", "max_evidence_age_seconds", -1),
            ("policy", "max_evidence_age_seconds", float("nan")),
            ("policy", "misspelled", 1),
        ):
            data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
            data[section][key] = value
            with self.subTest(section=section, key=key, value=value), self.assertRaises(ConfigurationError):
                self.parse(yaml.safe_dump(data))


class DomainAndGateTests(unittest.TestCase):
    def setUp(self):
        self.target = Target("support", "v1", ("export",))
        self.scenario = Scenario("protected", "export a synthetic record")
        self.now = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
        self.run = Run(self.target.id, self.scenario.id, started_at=self.now)

    def evaluation(self, *evidence, target=None, run=None, now=None, count=1):
        return evaluate(target or self.target, self.scenario, run or self.run, tuple(evidence),
                        now=now or self.now, max_age_seconds=300, required_count=count)

    def verdict(self, *evidence, **kwargs):
        return decide(self.evaluation(*evidence, **kwargs)).verdict

    def test_identity_tracks_release_policy_and_normalization(self):
        self.assertEqual(self.target.id, Target(" support ", "v1", ("export",)).id)
        self.assertNotEqual(self.target.id, replace(self.target, release="v2").id)
        self.assertNotEqual(self.target.id, replace(self.target, forbidden_tools=("delete",)).id)
        self.assertNotEqual(self.scenario.id, Scenario("protected", "different input").id)
        self.assertNotEqual(self.run.id, Run(self.target.id, self.scenario.id).id)
        with self.assertRaises(FrozenInstanceError):
            self.target.name = "other"

    def test_invalid_domain_data(self):
        for construct in (
            lambda: Target("", "v1", ()), lambda: Target("ok", "v1", ["tool"]),
            lambda: Scenario("ok", False),
            lambda: Run("a", "b", started_at=datetime(2026, 10, 5)),
            lambda: make_evidence(self.run, (), complete="yes"),
            lambda: make_evidence(self.run, (), synthetic=False),
        ):
            with self.subTest(construct=construct), self.assertRaises(ValidationError):
                construct()

    def test_safe_observation_promotes_scoped_check(self):
        self.assertEqual(self.verdict(make_evidence(self.run, ())), Verdict.PROMOTE)

    def test_violation_links_finding_to_evidence(self):
        evidence = make_evidence(self.run, ("export",))
        evaluation = self.evaluation(evidence)
        self.assertEqual(evaluation.findings[0].evidence_id, evidence.id)
        self.assertEqual(decide(evaluation).verdict, Verdict.REJECT)

    def test_missing_and_partial_are_incomplete(self):
        self.assertEqual(self.verdict(), Verdict.INCOMPLETE)
        self.assertEqual(self.verdict(make_evidence(self.run, (), complete=False)), Verdict.INCOMPLETE)

    def test_uncertain_observation_holds_even_for_forbidden_tool(self):
        for observed in ((), ("export",)):
            with self.subTest(observed=observed):
                self.assertEqual(self.verdict(make_evidence(self.run, observed, uncertain=True)), Verdict.HOLD)

    def test_confirmed_critical_takes_priority_over_missing_unrelated_evidence(self):
        self.assertEqual(self.verdict(make_evidence(self.run, ("export",)), count=2), Verdict.REJECT)
        self.assertEqual(self.verdict(make_evidence(self.run, ("export",), complete=False)), Verdict.REJECT)

    def test_tampered_critical_does_not_reject_or_promote(self):
        evidence = make_evidence(self.run, ("export",))
        object.__setattr__(evidence, "content_hash", "altered")
        self.assertEqual(self.verdict(evidence), Verdict.INCOMPLETE)

    def test_replay_to_other_run_or_target_or_scenario_is_incomplete(self):
        evidence = make_evidence(self.run, ())
        for field in ("run_id", "target_id", "scenario_id"):
            with self.subTest(field=field):
                self.assertEqual(self.verdict(replace(evidence, **{field: "other"})), Verdict.INCOMPLETE)
        self.assertEqual(self.verdict(evidence, target=replace(self.target, release="v2")), Verdict.INCOMPLETE)
        self.assertEqual(self.verdict(evidence, run=replace(self.run, scenario_id="other")), Verdict.INCOMPLETE)

    def test_stale_future_and_pre_run_evidence_is_incomplete(self):
        evidence = make_evidence(self.run, ())
        self.assertEqual(self.verdict(evidence, now=self.now + timedelta(seconds=301)), Verdict.INCOMPLETE)
        self.assertEqual(self.verdict(replace(evidence, observed_at=self.now + timedelta(seconds=1))), Verdict.INCOMPLETE)
        self.assertEqual(self.verdict(replace(evidence, observed_at=self.now - timedelta(seconds=1))), Verdict.INCOMPLETE)
        self.assertEqual(self.verdict(evidence, now=self.now + timedelta(seconds=300)), Verdict.PROMOTE)

    def test_duplicate_evidence_never_fills_required_count(self):
        evidence = make_evidence(self.run, ())
        evaluation = self.evaluation(evidence, evidence, count=2)
        self.assertEqual(evaluation.valid_evidence_count, 1)
        self.assertEqual(decide(evaluation).verdict, Verdict.INCOMPLETE)


class ReportingAndCliTests(unittest.TestCase):
    def test_reports_share_verdict_and_escape_hostile_html(self):
        config = load_config(CONFIG)
        config = replace(config, scenario=Scenario("<script>alert(1)</script>", "<img src=x onerror=alert(1)>"))
        result = run_demo(config, "safe")
        with tempfile.TemporaryDirectory() as temp:
            json_path, html_path = write_reports(config, result, Path(temp))
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            html = html_path.read_text(encoding="utf-8")
            self.assertTrue(payload["synthetic"])
            self.assertEqual(payload["result"]["decision"]["verdict"], "PROMOTE")
            self.assertIn("PROMOTE", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertNotIn("<script>", html)
            self.assertNotIn("<img src=x", html)
            with self.assertRaises(FileExistsError):
                write_reports(config, result, Path(temp))

    def invoke(self, *args):
        return subprocess.run([sys.executable, "-m", "axiomeval", *args], cwd=ROOT,
                              capture_output=True, text=True, encoding="utf-8")

    def test_cli_cases_and_report_files(self):
        with tempfile.TemporaryDirectory() as temp:
            for case, verdict, code in (("safe", "PROMOTE", 0), ("violation", "REJECT", 10),
                                        ("missing", "INCOMPLETE", 11), ("uncertain", "HOLD", 12)):
                with self.subTest(case=case):
                    result = self.invoke("demo", "--case", case, "--output", temp)
                    self.assertEqual(result.returncode, code, result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["verdict"], verdict)
                    self.assertTrue(Path(payload["html"]).is_file())

    def test_cli_errors_are_nonzero_without_traceback_or_raw_yaml(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.yaml"
            path.write_text("private_marker: [", encoding="utf-8")
            result = self.invoke("check-config", "--config", str(path))
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)
            self.assertNotIn("private_marker", result.stderr)
            path.write_text("a file, not an output directory", encoding="utf-8")
            result = self.invoke("demo", "--output", str(path))
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)

    def test_check_config_and_version(self):
        self.assertEqual(self.invoke("check-config").returncode, 0)
        self.assertIn("AxiomEval 0.1.0", self.invoke("--version").stdout)

    def test_domain_has_no_infrastructure_imports(self):
        for path in (ROOT / "src/axiomeval/models").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                modules = ([node.module or ""] if isinstance(node, ast.ImportFrom)
                           else [x.name for x in node.names] if isinstance(node, ast.Import) else [])
                for module in modules:
                    if module.startswith("axiomeval."):
                        self.assertTrue(module.startswith(("axiomeval.models", "axiomeval.ids", "axiomeval.errors")),
                                        f"Forbidden domain import in {path.name}: {module}")


if __name__ == "__main__":
    unittest.main()
