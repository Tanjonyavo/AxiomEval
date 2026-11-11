"""Tabular reference for S10: the S9 logistic regression (prefix-features-v2) on the S10 test groups, horizon 1.

Horizon 1 of S10 and the S9 prefix are the same events (up to the first model call). The S9 model keeps
its own selection protocol (C chosen by grouped cross-validation on train + validation), so this is a
reference row, not a paired comparison.

Usage: python tools/ml/s10_tabular_reference.py data/runs/v3/r1-baseline.jsonl data/runs/v3/r6-bound.jsonl \
           --out reports/s10/v3_tabular_h1.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

from axiomeval.collection import load_records
from axiomeval.ml.baselines import Featurizer, Logistic, files_digest, group_bootstrap, metrics
from axiomeval.ml.features import FEATURE_VERSION, to_example


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    records = [r for path in args.runs for r in load_records(path)
               if any(e["kind"] == "model_call" for e in r["trace"])]  # same population as S10 horizon 1
    examples = [(r["partition"], to_example(r)) for r in records]
    fit = [e for p, e in examples if p in ("train", "validation")]
    test = [e for p, e in examples if p == "test"]
    out = {"feature_version": FEATURE_VERSION, "dataset_digest": files_digest(list(args.runs)),
           "population_runs": len(examples), "test_runs": len(test), "seeds": {}}
    for seed in (0, 1, 2):
        feat = Featurizer().fit(fit)
        x_fit, x_te = feat.transform(fit), feat.transform(test)
        y_fit, y_te = np.array([e.label for e in fit]), np.array([e.label for e in test])
        g_fit, g_te = np.array([e.group_id for e in fit]), np.array([e.group_id for e in test])
        model = Logistic(seed).fit(x_fit, y_fit, g_fit)
        p = model.predict_proba(x_te)
        entry = metrics(y_te, p)
        entry["chosen_C"] = model.c
        for m in ("pr_auc", "brier"):
            entry[f"{m}_ci95_groups"] = group_bootstrap(y_te, p, g_te, m, draws=1000, seed=seed)
        out["seeds"][str(seed)] = entry
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({s: {k: v[k] for k in ("pr_auc", "pr_auc_ci95_groups", "brier", "brier_ci95_groups", "chosen_C")}
                      for s, v in out["seeds"].items()}, indent=1))


if __name__ == "__main__":
    main()
