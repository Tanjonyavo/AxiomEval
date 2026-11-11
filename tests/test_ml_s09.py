"""S9: prefix feature contract, leakage audit, baselines and grouped uncertainty."""
import unittest

import numpy as np

from axiomeval.ml.baselines import (Featurizer, Majority, family_of, family_split, group_bootstrap, metrics,
                                    run_protocol)
from axiomeval.ml.features import Example, leaked_keys, prefix, to_example


def event(kind, **data):
    return {"kind": kind, "data": data}


def record(group, business, first_tool=None, release="r1", partition="train", question="Où est ma commande ?"):
    calls = [[first_tool, {}]] if first_tool else []
    trace = [event("input", question=question), event("retrieval", documents=["commandes"]),
             event("model_call", step=0, tool_calls=calls, prompt_tokens=400, content="" if calls else "réponse"),
             event("tool_call", tool=first_tool or "x"), event("authz", allowed=True),
             event("output", answer="FINAL ANSWER TEXT")]
    return {"draw_key": f"{group}-{business}-{release}-{first_tool}", "group_id": group, "release_id": release,
            "partition": partition, "kind": "account", "business": business, "trace": trace}


class FeatureContractTests(unittest.TestCase):
    def test_prefix_stops_at_first_model_call(self):
        r = record("g1", "SUCCESS", "lookup_order_status")
        self.assertEqual([e["kind"] for e in prefix(r["trace"])], ["input", "retrieval", "model_call"])
        self.assertEqual(leaked_keys(r), ["authz", "output", "tool_call"])

    def test_no_future_information_in_features(self):
        example = to_example(record("g1", "FAILURE"))
        serialized = repr(example.structure) + example.text
        for forbidden in ("FINAL ANSWER", "authz", "release", "latency", "SUCCESS", "FAILURE"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(example.label, 1)
        self.assertEqual(example.structure["first_step_answers_directly"], 1.0)

    def test_label_is_business_not_success(self):
        self.assertEqual(to_example(record("g", "MISSING")).label, 1)
        self.assertEqual(to_example(record("g", "SUCCESS")).label, 0)

    def test_featurizer_learns_vocabulary_from_train_only(self):
        train = [to_example(record("g1", "SUCCESS", question="retour colis retour colis"))] * 3
        test = [to_example(record("g2", "SUCCESS", question="mot inédit inédit"))]
        feat = Featurizer().fit(train)
        self.assertNotIn("inédit", feat.text.vocabulary_)
        self.assertEqual(feat.transform(test).shape[1], feat.transform(train).shape[1])

    def test_release_shortcut_only_in_ablation(self):
        ex = [to_example(record("g1", "SUCCESS"))]
        self.assertFalse(any("release" in n for n in Featurizer().fit(ex).dict.get_feature_names_out()))
        self.assertTrue(any("release" in n for n in Featurizer(use_release=True).fit(ex).dict.get_feature_names_out()))


class MetricTests(unittest.TestCase):
    def test_metrics_on_known_values(self):
        y, p = np.array([0, 0, 1, 1]), np.array([0.1, 0.4, 0.35, 0.8])
        m = metrics(y, p)
        self.assertAlmostEqual(m["brier"], np.mean((p - y) ** 2))
        self.assertAlmostEqual(m["roc_auc"], 0.75)
        self.assertAlmostEqual(m["pr_auc"], (1 / 1 + 2 / 3) / 2)

    def test_group_bootstrap_resamples_groups(self):
        y = np.array([0, 1] * 20)
        p = np.where(y == 1, 0.9, 0.1)
        g = np.repeat(np.arange(10), 4)
        ci = group_bootstrap(y, p, g, "brier", draws=200)
        self.assertLessEqual(ci[0], metrics(y, p)["brier"] + 1e-12)
        self.assertGreaterEqual(ci[1], metrics(y, p)["brier"] - 1e-12)

    def test_majority_predicts_train_prevalence(self):
        self.assertAlmostEqual(Majority().fit(None, np.array([0, 0, 0, 1]), None).p, 0.25)


class ProtocolTests(unittest.TestCase):
    def test_learnable_signal_beats_majority(self):
        train, test = [], []
        for i in range(30):
            fails = i % 2 == 0
            tool = None if fails else "lookup_order_status"
            target = test if i >= 22 else train
            for d in range(2):
                r = record(f"g{i}", "FAILURE" if fails else "SUCCESS", tool,
                           partition="test" if i >= 22 else "train")
                r["draw_key"] += str(d)
                target.append(to_example(r))
        result = run_protocol(train, test, 0, Featurizer(use_text=False), bootstrap_draws=100)
        models = result["models"]
        self.assertEqual(result["n_test_groups"], 8)
        self.assertGreater(models["logistic_regression"]["pr_auc"], models["majority"]["pr_auc"])
        self.assertLess(models["rule_first_step"]["brier"], models["majority"]["brier"])

    def test_document_features_come_from_training_data(self):
        """prefix-features-v2: any retrieved document becomes a feature; names unseen in train are dropped."""
        def with_docs(group, docs):
            r = record(group, "SUCCESS")
            r["trace"][1]["data"]["documents"] = docs
            return to_example(r)
        feat = Featurizer(use_text=False).fit([with_docs("g1", ["garanties"]), with_docs("g2", ["magasins"])])
        names = feat.dict.get_feature_names_out().tolist()
        self.assertIn("doc:garanties", names)
        self.assertNotIn("doc:inconnu", names)
        self.assertEqual(feat.transform([with_docs("g3", ["inconnu"])]).shape[1], len(feat.dict.get_feature_names_out()))

    def test_family_split_holds_out_whole_families(self):
        examples = [to_example(record(f"fam{f}-{g:02d}", "SUCCESS", partition=p))
                    for f in range(8) for g in range(3) for p in ("train", "test", "calibration")]
        train, test = family_split(examples)
        families = lambda xs: {family_of(e.group_id) for e in xs}  # noqa: E731
        self.assertEqual(len(families(test)), 2)
        self.assertFalse(families(train) & families(test))
        self.assertTrue(all(e.partition != "calibration" for e in train + test))
        self.assertEqual(family_split(examples), (train, test))  # deterministic


if __name__ == "__main__":
    unittest.main()
