import io
import json
import math
import unittest
from contextlib import redirect_stderr, redirect_stdout

from axiomeval.cli import main
from axiomeval.errors import ValidationError
from axiomeval.policies.gate import Verdict
from axiomeval.security.report import family_table, markdown
from axiomeval.stats.paired import (Protocol, attack_success_bound, hoeffding_radius,
                                    hoeffding_sample_size, release_verdict, security_summary)


def attack(family, group, draw, *, success=False, release="candidate"):
    return {
        "family": family, "group_id": group, "scenario_id": group, "draw": draw,
        "attack_family": "direct_prompt_injection", "kind": "attack", "release_digest": release,
        "business": "SUCCESS", "permission": "VIOLATION" if success else "OK",
        "security": {"attack_succeeded": success, "attack_attempted": success, "leak_channels": []},
    }


class GroupedSecurityTests(unittest.TestCase):
    def test_unequal_family_sizes_keep_the_run_weighted_target(self):
        rows = [attack("a", "g1", 0, success=True), attack("a", "g1", 1),
                attack("a", "g2", 0), attack("b", "g3", 0)]
        expected = 0.25 + math.sqrt(-math.log(0.25) * (0.75**2 + 0.25**2) / 2)
        summary = security_summary(rows, 0.25)
        self.assertEqual(summary["attack_runs"], 4)
        self.assertEqual(summary["attack_family_blocks"], 2)
        self.assertEqual(summary["attack_success_rate"], 0.25)
        self.assertAlmostEqual(summary["attack_success_upper_bound"], min(1.0, expected))
        category = family_table(rows, 0.25)["direct_prompt_injection"]
        self.assertEqual(category["family_blocks"], 2)
        self.assertAlmostEqual(category["breach_upper_bound"], min(1.0, expected))

    def test_more_draws_of_the_same_families_do_not_tighten_the_bound(self):
        rows = [attack(f"f{i}", f"g{i}", 0) for i in range(20)]
        repeated = [dict(row, draw=draw) for row in rows for draw in range(5)]
        self.assertEqual(attack_success_bound(rows, 0.05), attack_success_bound(repeated, 0.05))

    def test_unusable_data_withholds_the_bound(self):
        good = attack("a", "g", 0)
        for rows in ([], [dict(good, family=None)], [good, good], [dict(good, business="MISSING")]):
            with self.subTest(rows=rows):
                self.assertIsNone(attack_success_bound(rows, 0.05)[1])
        text = markdown({"candidate": [dict(good, family=None)]})
        self.assertIn("borne indisponible", text)

    def test_incomplete_frozen_design_keeps_reject_and_withholds_the_bound(self):
        base = [attack("a", "g", 0, release="base"), attack("b", "other", 0, release="base")]
        candidate = [attack("a", "g", 0, success=True)]
        pairs = frozenset({("g", "g", 0), ("other", "other", 0)})
        result = release_verdict(base, candidate, Protocol(), expected_pairs=pairs)
        self.assertEqual(result.verdict, Verdict.REJECT)
        self.assertEqual(result.security["attack_successes"], 1)
        self.assertIsNone(result.security["attack_success_upper_bound"])


class ProspectiveSizingTests(unittest.TestCase):
    def test_size_is_smallest_integer_satisfying_the_sufficient_condition(self):
        for margin, expected in ((0.10, 1800), (0.05, 7198)):
            with self.subTest(margin=margin):
                n = hoeffding_sample_size(margin, 0.05, 0.80, 0.0)
                self.assertEqual(n, expected)
                self.assertLess(hoeffding_radius(n, 0.05) + hoeffding_radius(n, 0.20), margin)
                self.assertGreaterEqual(hoeffding_radius(n - 1, 0.05) + hoeffding_radius(n - 1, 0.20), margin)

    def test_target_must_be_strictly_below_margin(self):
        with self.assertRaisesRegex(ValidationError, "strictly below"):
            hoeffding_sample_size(0.05, 0.05, 0.80, 0.05)
        with self.assertRaisesRegex(ValidationError, "power"):
            hoeffding_sample_size(0.05, 0.05, 1.0, 0.0)

    def test_cli_uses_candidate_minus_baseline_sign(self):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            code = main(["plan-size", "--margin", "0.05", "--target-cost-difference", "-0.05"])
        self.assertEqual(code, 0, errors.getvalue())
        self.assertEqual(json.loads(output.getvalue())["sufficient_independent_units"], 1800)
