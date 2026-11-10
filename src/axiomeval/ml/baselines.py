"""S9 baselines on prefix features: majority, rule, logistic regression, gradient boosting.

All model choices are made on training groups only (grouped cross-validation);
test groups are scored once. Uncertainty is a bootstrap over test groups, the
independent unit (AXM 04-C05). AXM references for the models: 05-C01, 05-C03,
05-C04 (log loss), 06-C01 (Brier).
"""
import hashlib
import json
import math
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sklearn
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold

from axiomeval.ml.features import FEATURE_VERSION, Example


@dataclass
class Featurizer:
    """Fit on training examples only; the same object transforms every other split."""
    use_text: bool = True
    use_structure: bool = True
    use_release: bool = False  # shortcut ablation only

    def fit(self, examples: list[Example]) -> "Featurizer":
        self.text = TfidfVectorizer(min_df=2 if len(examples) > 2 else 1, ngram_range=(1, 2), sublinear_tf=True)
        self.dict = DictVectorizer()
        if self.use_text:
            self.text.fit([e.text for e in examples])
        self.dict.fit([self._struct(e) for e in examples])
        return self

    def _struct(self, e: Example) -> dict:
        features = dict(e.structure) if self.use_structure else {}
        if self.use_release:
            features[f"release:{e.release_id}"] = 1.0
        return features or {"bias": 1.0}

    def transform(self, examples: list[Example]):
        parts = [self.dict.transform([self._struct(e) for e in examples])]
        if self.use_text:
            parts.append(self.text.transform([e.text for e in examples]))
        return csr_matrix(hstack(parts))


def labels(examples):
    return np.array([e.label for e in examples])


def groups(examples):
    return np.array([e.group_id for e in examples])


class Majority:
    name = "majority"

    def fit(self, x, y, g):
        self.p = float(np.clip(y.mean(), 1e-6, 1 - 1e-6))
        return self

    def predict_proba(self, x):
        return np.full(x.shape[0], self.p)


class FirstStepRule:
    """P(review | does the first step answer without any tool?) estimated on train, Laplace-smoothed."""
    name = "rule_first_step"

    def __init__(self, column: int):
        self.column = column

    def fit(self, x, y, g):
        flag = np.asarray(x[:, self.column].todense()).ravel() > 0
        self.p = {v: (y[flag == v].sum() + 1) / ((flag == v).sum() + 2) for v in (False, True)}
        return self

    def predict_proba(self, x):
        flag = np.asarray(x[:, self.column].todense()).ravel() > 0
        return np.where(flag, self.p[True], self.p[False])


class Logistic:
    name = "logistic_regression"

    def __init__(self, seed: int):
        self.seed = seed

    def fit(self, x, y, g):
        self.c = select_c(x, y, g, self.seed)
        self.model = LogisticRegression(C=self.c, max_iter=2000, random_state=self.seed).fit(x, y)
        return self

    def predict_proba(self, x):
        return self.model.predict_proba(x)[:, 1]


class Boosting:
    name = "gradient_boosting"

    def __init__(self, seed: int):
        self.seed = seed

    def fit(self, x, y, g):
        self.model = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.1, max_iter=150,
                                                    l2_regularization=1.0, random_state=self.seed)
        self.model.fit(x.toarray(), y)
        return self

    def predict_proba(self, x):
        return self.model.predict_proba(x.toarray())[:, 1]


def select_c(x, y, g, seed, grid=(0.01, 0.1, 1.0, 10.0)) -> float:
    """Choose C by grouped cross-validated log loss on training groups only."""
    folds = GroupKFold(n_splits=min(5, len(set(g))))
    best, best_loss = grid[0], math.inf
    for c in grid:
        losses = []
        for tr, va in folds.split(x, y, g):
            if len(set(y[tr])) < 2:
                continue
            model = LogisticRegression(C=c, max_iter=2000, random_state=seed).fit(x[tr], y[tr])
            losses.append(log_loss(y[va], model.predict_proba(x[va])[:, 1], labels=[0, 1]))
        if losses and np.mean(losses) < best_loss:
            best, best_loss = c, float(np.mean(losses))
    return best


def metrics(y, p) -> dict:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    out = {"n": int(len(y)), "prevalence": float(y.mean()), "brier": float(brier_score_loss(y, p)),
           "log_loss": float(log_loss(y, p, labels=[0, 1]))}
    if len(set(y)) == 2:
        out["pr_auc"] = float(average_precision_score(y, p))
        out["roc_auc"] = float(roc_auc_score(y, p))
    return out


def group_bootstrap(y, p, g, metric: str, draws: int = 1000, seed: int = 0, alpha: float = 0.05):
    """Percentile interval of a metric when test groups (not runs) are resampled."""
    rng = np.random.default_rng(seed)
    unique = np.unique(g)
    index = {u: np.flatnonzero(g == u) for u in unique}
    values = []
    for _ in range(draws):
        rows = np.concatenate([index[u] for u in rng.choice(unique, size=len(unique), replace=True)])
        if metric in ("pr_auc", "roc_auc") and len(set(y[rows])) < 2:
            continue
        values.append(metrics(y[rows], p[rows])[metric])
    if len(values) < draws // 2:
        return None
    return [float(np.quantile(values, alpha / 2)), float(np.quantile(values, 1 - alpha / 2))]


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def files_digest(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in sorted(paths):
        h.update(Path(path).name.encode())
        h.update(Path(path).read_bytes())
    return h.hexdigest()


def run_protocol(train: list[Example], test: list[Example], seed: int, featurizer: Featurizer,
                 bootstrap_draws: int = 1000) -> dict:
    feat = featurizer.fit(train)
    x_tr, x_te = feat.transform(train), feat.transform(test)
    y_tr, y_te, g_tr, g_te = labels(train), labels(test), groups(train), groups(test)
    names = feat.dict.get_feature_names_out().tolist()
    models = [Majority(), Logistic(seed), Boosting(seed)]
    if "first_step_answers_directly" in names:
        models.insert(1, FirstStepRule(names.index("first_step_answers_directly")))
    results = {}
    for model in models:
        start = time.perf_counter()
        model.fit(x_tr, y_tr, g_tr)
        p = model.predict_proba(x_te)
        entry = metrics(y_te, p)
        entry["fit_and_predict_seconds"] = round(time.perf_counter() - start, 3)
        for m in ("pr_auc", "brier"):
            entry[f"{m}_ci95_groups"] = group_bootstrap(y_te, p, g_te, m, draws=bootstrap_draws, seed=seed)
        if isinstance(model, Logistic):
            entry["chosen_C"] = model.c
        results[model.name] = entry
    return {"n_train_runs": len(train), "n_train_groups": len(set(g_tr)), "n_test_runs": len(test),
            "n_test_groups": len(set(g_te)), "models": results}


def experiment(examples: list[Example], run_files: list[Path], seeds=(0, 1, 2)) -> dict:
    by_part = {p: [e for e in examples if e.partition == p] for p in ("train", "validation", "calibration", "test")}
    fit_pool = by_part["train"] + by_part["validation"]
    releases = sorted({e.release_id for e in examples})
    report = {
        "manifest": {"hypothesis": "H-S09: prefix features predict runs that need review better than majority",
                     "feature_version": FEATURE_VERSION, "label": "business != SUCCESS",
                     "horizon": "after first model call", "dataset_digest": files_digest(run_files),
                     "run_files": [Path(p).name for p in run_files], "seeds": list(seeds),
                     "git_commit": git_commit(), "python": platform.python_version(),
                     "sklearn": sklearn.__version__, "machine": platform.machine(),
                     "selection": "grouped CV on train+validation groups only; test scored once per seed"},
        "frozen_split": {}, "ablations": {}, "leave_one_release_out": {},
    }
    for seed in seeds:
        report["frozen_split"][str(seed)] = run_protocol(fit_pool, by_part["test"], seed, Featurizer())
    for name, feat in (("structure_only", Featurizer(use_text=False)), ("text_only", Featurizer(use_structure=False)),
                       ("with_release_shortcut", Featurizer(use_release=True))):
        report["ablations"][name] = run_protocol(fit_pool, by_part["test"], seeds[0], feat)
    for held in releases:
        train = [e for e in fit_pool if e.release_id != held]
        test = [e for e in by_part["test"] if e.release_id == held]
        if train and test:
            report["leave_one_release_out"][held] = run_protocol(train, test, seeds[0], Featurizer())
    return report


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
