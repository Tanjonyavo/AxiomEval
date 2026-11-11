"""S10: horizon-k event sequences, order ablation, and the pooled and GRU models."""
import importlib.util
import unittest

import numpy as np

from axiomeval.ml.sequence import (DIM, KINDS, Pooled, horizon_prefix, paired_difference, shuffled, split,
                                   to_sequence)

HAS_TORCH = importlib.util.find_spec("torch") is not None


def event(kind, **data):
    return {"kind": kind, "data": data}


def record(group, business, steps=2, partition="train", tool="lookup_order_status", question="Où est A1001 ?"):
    trace = [event("input", question=question), event("retrieval", documents=["commandes"])]
    for step in range(steps - 1):
        trace += [event("model_call", step=step, tool_calls=[[tool, {}]], prompt_tokens=500, content=""),
                  event("tool_call", tool=tool), event("authz", tool=tool, allowed=True, critical=False),
                  event("tool_result", tool=tool, status="executed", result="SECRET RESULT")]
    trace += [event("model_call", step=steps - 1, tool_calls=[], prompt_tokens=700, content="réponse finale"),
              event("output", answer="FINAL ANSWER TEXT")]
    return {"draw_key": f"{group}-{business}-{steps}-{partition}", "group_id": group, "release_id": "r1",
            "partition": partition, "business": business, "trace": trace}


class HorizonTests(unittest.TestCase):
    def test_prefix_stops_at_kth_model_call_and_never_shows_output(self):
        r = record("g", "SUCCESS", steps=3)
        first = horizon_prefix(r["trace"], 1)
        self.assertEqual([e["kind"] for e in first], ["input", "retrieval", "model_call"])
        second = horizon_prefix(r["trace"], 2)
        self.assertEqual([e["kind"] for e in second][-1], "model_call")
        self.assertEqual(sum(e["kind"] == "model_call" for e in second), 2)
        self.assertNotIn("output", [e["kind"] for e in horizon_prefix(r["trace"], 3)])

    def test_runs_shorter_than_k_leave_the_population(self):
        self.assertIsNone(horizon_prefix(record("g", "SUCCESS", steps=1)["trace"], 2))
        self.assertIsNone(to_sequence(record("g", "SUCCESS", steps=2), 3))

    def test_encoding_has_no_text_of_results_or_answer(self):
        x = to_sequence(record("g", "FAILURE", steps=2), 2)
        self.assertEqual(x.events.shape, (7, DIM))
        self.assertEqual(x.label, 1)
        self.assertEqual(x.text, "Où est A1001 ?")
        self.assertEqual(x.events[0, KINDS.index("input")], 1.0)
        self.assertNotIn("SECRET", repr(x.__dict__))

    def test_shuffle_keeps_the_multiset_of_events(self):
        x = to_sequence(record("g", "SUCCESS", steps=3), 3)
        y = shuffled(x, np.random.default_rng(0))
        self.assertEqual(sorted(map(tuple, x.events[:, :-1])), sorted(map(tuple, y.events[:, :-1])))
        self.assertTrue(np.allclose(y.events[:, -1], np.arange(len(y.events)) / 8.0))


def toy(n_groups=24, seed=0):
    """Failure iff the requested tool is refund_order: a signal any encoder should find."""
    rng = np.random.default_rng(seed)
    out = []
    for g in range(n_groups):
        part = ("train", "train", "validation", "test")[g % 4]
        fail = bool(rng.integers(2))
        for v in range(4):
            r = record(f"g{g}", "FAILURE" if fail else "SUCCESS", steps=2 + v % 2, partition=part,
                       tool="refund_order" if fail else "lookup_order_status")
            r["draw_key"] += f"-{v}"
            out.append(to_sequence(r, 2))
    return out


class ModelTests(unittest.TestCase):
    def test_pooled_learns_a_separable_signal(self):
        train, valid, test = split(toy())
        model = Pooled(0, use_text=False).fit(train, valid)
        p = model.predict_proba(test)
        y = np.array([e.label for e in test])
        self.assertGreater(p[y == 1].mean(), p[y == 0].mean())
        self.assertIn(model.choice, Pooled.grid)

    def test_paired_difference_is_zero_for_identical_models(self):
        y = np.array([0, 1, 0, 1, 1, 0]); p = np.array([.2, .7, .4, .6, .9, .1]); g = np.array([1, 1, 2, 2, 3, 3])
        self.assertEqual(paired_difference(y, p, p, g, "brier", draws=200), [0.0, 0.0])

    @unittest.skipUnless(HAS_TORCH, "torch not installed (optional extra: seq)")
    def test_gru_trains_and_is_reproducible(self):
        from axiomeval.ml.sequence import GRUModel
        train, valid, test = split(toy())
        a = GRUModel(0, use_text=False, epochs=15).fit(train, valid).predict_proba(test)
        b = GRUModel(0, use_text=False, epochs=15).fit(train, valid).predict_proba(test)
        self.assertTrue(np.allclose(a, b, atol=1e-5))
        self.assertTrue(((a >= 0) & (a <= 1)).all())


if __name__ == "__main__":
    unittest.main()
