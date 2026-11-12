import unittest

from axiomeval.policies.gate import Verdict
from axiomeval.stats.paired import Protocol, release_verdict


def run(group, draw, release, business="SUCCESS", scenario=None, permission="OK"):
    return {"group_id": group, "scenario_id": scenario or f"{group}-v0", "draw": draw,
            "release_digest": release, "kind": "information", "business": business,
            "permission": permission}


class ReleasePairingTests(unittest.TestCase):
    def test_missing_draws_in_all_700_groups_cannot_promote(self):
        groups = [f"g{i}" for i in range(700)]
        baseline = [run(group, draw, "base") for group in groups for draw in (0, 1)]
        complete = [run(group, draw, "candidate", "FAILURE" if draw else "SUCCESS")
                    for group in groups for draw in (0, 1)]
        partial = [row for row in complete if row["draw"] == 0]

        self.assertEqual(release_verdict(baseline, complete, Protocol()).verdict, Verdict.HOLD)
        result = release_verdict(baseline, partial, Protocol())
        self.assertEqual(result.verdict, Verdict.INCOMPLETE)
        self.assertIn("unpaired-runs", result.reasons)

    def test_missing_baseline_draw_and_extra_candidate_scenario(self):
        base = [run("g", 0, "base"), run("g", 1, "base")]
        cand = [run("g", 0, "candidate"), run("g", 1, "candidate")]
        for left, right in ((base[:1], cand), (base, cand + [run("g", 0, "candidate", scenario="g-v1")])):
            with self.subTest(left=len(left), right=len(right)):
                result = release_verdict(left, right, Protocol())
                self.assertEqual(result.verdict, Verdict.INCOMPLETE)
                self.assertIn("unpaired-runs", result.reasons)

    def test_duplicates_on_either_side_are_incomplete(self):
        base, cand = [run("g", 0, "base")], [run("g", 0, "candidate")]
        for left, right in ((base * 2, cand), (base, cand * 2), (base * 2, cand * 2)):
            with self.subTest(left=len(left), right=len(right)):
                result = release_verdict(left, right, Protocol())
                self.assertEqual(result.verdict, Verdict.INCOMPLETE)
                self.assertIn("duplicate-runs", result.reasons)

    def test_critical_finding_precedes_unpaired_runs(self):
        base = [run("g", 0, "base"), run("g", 1, "base")]
        cand = [run("g", 0, "candidate", permission="VIOLATION")]
        self.assertEqual(release_verdict(base, cand, Protocol()).verdict, Verdict.REJECT)
