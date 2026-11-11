"""S10: event-sequence models on trajectory prefixes (spec §19-§20).

Horizon k: every event up to and including the k-th model call. When that call
asks for tools, the prediction is made before they run; the final answer, the
output event and any later event are never visible. Only runs that reach the
k-th model call belong to the population of horizon k, and every model is
scored on that same population.

Models, from simple to sequential, with the same split and the same selection
budget (two values chosen on the validation groups):
- pooled: mean and max of the event vectors, logistic regression (no order);
- GRU: a recurrent encoder over the events, trained with early stopping on the
  validation groups.
Both can also read the question (TF-IDF fitted on train only).
"""
import time
from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

from axiomeval.collect.secure_tools import SECURE_TOOL_SPECS
from axiomeval.ml.baselines import group_bootstrap, metrics

SEQ_VERSION = "event-sequence-v1"
KINDS = ("input", "retrieval", "model_call", "tool_call", "authz", "tool_result", "guard", "error")
TOOLS = tuple(spec["function"]["name"] for spec in SECURE_TOOL_SPECS)
STATUSES = ("executed", "denied", "guarded")
DIM = len(KINDS) + len(TOOLS) + len(STATUSES) + 8


@dataclass(frozen=True)
class SeqExample:
    run_key: str
    group_id: str
    release_id: str
    partition: str
    text: str
    events: np.ndarray  # (length, DIM)
    label: int


def horizon_prefix(trace: list[dict], k: int) -> list[dict] | None:
    """Events up to the k-th model call, or None when the run ends before it."""
    out, calls = [], 0
    for event in trace:
        if event["kind"] == "output":
            return None
        out.append(event)
        if event["kind"] == "model_call":
            calls += 1
            if calls == k:
                return out
    return None


def event_vector(event: dict, position: int) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    data, kind = event["data"], event["kind"]
    v[KINDS.index(kind)] = 1.0
    base = len(KINDS)
    tools = []
    if kind in ("tool_call", "authz", "tool_result"):
        tools = [data.get("tool")]
    elif kind == "model_call":
        tools = [name for name, _ in data.get("tool_calls", [])]
    for tool in tools:
        if tool in TOOLS:
            v[base + TOOLS.index(tool)] = 1.0
    base += len(TOOLS)
    if kind == "tool_result" and data.get("status") in STATUSES:
        v[base + STATUSES.index(data["status"])] = 1.0
    base += len(STATUSES)
    extra = [
        float(kind == "authz" and bool(data.get("allowed"))),
        float(kind == "authz" and bool(data.get("critical"))),
        len(data.get("documents", [])) / 2.0 if kind == "retrieval" else 0.0,
        len(data.get("tool_calls", [])) if kind == "model_call" else 0.0,
        len(data.get("content") or "") / 100.0 if kind == "model_call" else 0.0,
        data.get("prompt_tokens", 0) / 1000.0 if kind == "model_call" else 0.0,
        float(data.get("step", 0)) if kind == "model_call" else 0.0,
        position / 8.0,
    ]
    v[base:base + len(extra)] = extra
    return v


def to_sequence(record: dict, k: int) -> SeqExample | None:
    events = horizon_prefix(record["trace"], k)
    if events is None:
        return None
    question = next((e["data"]["question"] for e in events if e["kind"] == "input"), "")
    matrix = np.stack([event_vector(e, i) for i, e in enumerate(events)])
    return SeqExample(record["draw_key"], record["group_id"], record["release_id"], record["partition"], question,
                      matrix, int(record["business"] != "SUCCESS"))


def shuffled(example: SeqExample, rng: np.random.Generator) -> SeqExample:
    """Order ablation: same events, random order, positions recomputed."""
    order = rng.permutation(len(example.events))
    events = example.events[order].copy()
    events[:, -1] = np.arange(len(events)) / 8.0
    return SeqExample(**{**example.__dict__, "events": events})


class Text:
    def fit(self, examples):
        self.vec = TfidfVectorizer(min_df=2 if len(examples) > 2 else 1, ngram_range=(1, 2), sublinear_tf=True)
        self.vec.fit([e.text for e in examples])
        return self

    def transform(self, examples):
        return self.vec.transform([e.text for e in examples])


def pooled_matrix(examples: list[SeqExample]) -> np.ndarray:
    return np.stack([np.concatenate([e.events.mean(0), e.events.max(0), [len(e.events) / 8.0]]) for e in examples])


class Pooled:
    """Order-free baseline: mean and max of event vectors (+ question), logistic regression."""
    name = "pooled_logistic"
    grid = (0.1, 1.0)

    def __init__(self, seed: int, use_text: bool):
        self.seed, self.use_text = seed, use_text

    def _x(self, examples):
        x = csr_matrix(pooled_matrix(examples))
        return csr_matrix(hstack([x, self.text.transform(examples)])) if self.use_text else x

    def fit(self, train, valid):
        self.text = Text().fit(train) if self.use_text else None
        x_tr, y_tr = self._x(train), np.array([e.label for e in train])
        x_va, y_va = self._x(valid), np.array([e.label for e in valid])
        best = None
        for c in self.grid:
            model = LogisticRegression(C=c, max_iter=3000, random_state=self.seed).fit(x_tr, y_tr)
            loss = log_loss(y_va, model.predict_proba(x_va)[:, 1], labels=[0, 1])
            if best is None or loss < best[0]:
                best = (loss, c, model)
        self.valid_loss, self.choice, self.model = best
        self.parameters = int(self.model.coef_.size + 1)
        return self

    def predict_proba(self, examples):
        return self.model.predict_proba(self._x(examples))[:, 1]


class GRUModel:
    """GRU over events; the question enters through a small learned projection of its TF-IDF vector."""
    name = "gru"
    grid = (16, 32)

    def __init__(self, seed: int, use_text: bool, epochs: int = 60, patience: int = 8, batch: int = 64):
        self.seed, self.use_text, self.epochs, self.patience, self.batch = seed, use_text, epochs, patience, batch

    def _tensors(self, examples):
        import torch
        lengths = torch.tensor([len(e.events) for e in examples])
        padded = torch.zeros(len(examples), int(lengths.max()), DIM)
        for i, e in enumerate(examples):
            padded[i, :len(e.events)] = torch.from_numpy(e.events)
        text = None
        if self.use_text:
            text = torch.from_numpy(self.text.transform(examples).toarray().astype(np.float32))
        return padded, lengths, text

    def _net(self, hidden, text_dim):
        import torch
        from torch import nn

        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.gru = nn.GRU(DIM, hidden, batch_first=True)
                self.text = nn.Linear(text_dim, 16) if text_dim else None
                self.head = nn.Linear(hidden + (16 if text_dim else 0), 1)

            def forward(self, x, lengths, text):
                packed = nn.utils.rnn.pack_padded_sequence(x, lengths, batch_first=True, enforce_sorted=False)
                _, h = self.gru(packed)
                z = h[-1]
                if self.text is not None:
                    z = torch.cat([z, torch.relu(self.text(text))], dim=1)
                return self.head(z).squeeze(1)
        return Net()

    def _train(self, hidden, train, valid):
        import torch
        torch.manual_seed(self.seed)
        x, lengths, text = self._tensors(train)
        y = torch.tensor([e.label for e in train], dtype=torch.float32)
        xv, lv, tv = self._tensors(valid)
        yv = np.array([e.label for e in valid])
        net = self._net(hidden, text.shape[1] if text is not None else 0)
        opt = torch.optim.Adam(net.parameters(), lr=3e-3, weight_decay=1e-4)
        loss_fn = torch.nn.BCEWithLogitsLoss()
        generator = torch.Generator().manual_seed(self.seed)
        best, best_state, waited, epochs = np.inf, None, 0, 0
        for _ in range(self.epochs):
            epochs += 1
            net.train()
            for idx in torch.randperm(len(y), generator=generator).split(self.batch):
                opt.zero_grad()
                loss = loss_fn(net(x[idx], lengths[idx], text[idx] if text is not None else None), y[idx])
                loss.backward()
                opt.step()
            net.eval()
            with torch.no_grad():
                pv = torch.sigmoid(net(xv, lv, tv)).numpy()
            loss_v = log_loss(yv, np.clip(pv, 1e-6, 1 - 1e-6), labels=[0, 1])
            if loss_v < best - 1e-4:
                best, waited = loss_v, 0
                best_state = {k: v.clone() for k, v in net.state_dict().items()}
            else:
                waited += 1
                if waited >= self.patience:
                    break
        net.load_state_dict(best_state)
        return best, net, epochs

    def fit(self, train, valid):
        self.text = Text().fit(train) if self.use_text else None
        best = None
        for hidden in self.grid:
            loss, net, epochs = self._train(hidden, train, valid)
            if best is None or loss < best[0]:
                best = (loss, hidden, net, epochs)
        self.valid_loss, self.choice, self.net, self.epochs_run = best
        self.parameters = int(sum(p.numel() for p in self.net.parameters()))
        return self

    def predict_proba(self, examples):
        import torch
        x, lengths, text = self._tensors(examples)
        with torch.no_grad():
            return torch.sigmoid(self.net(x, lengths, text)).numpy().astype(float)


def paired_difference(y, p_a, p_b, g, metric: str, draws: int = 1000, seed: int = 0, alpha: float = 0.05):
    """Percentile interval of metric(b) - metric(a) when test groups are resampled jointly."""
    rng = np.random.default_rng(seed)
    unique = np.unique(g)
    index = {u: np.flatnonzero(g == u) for u in unique}
    values = []
    for _ in range(draws):
        rows = np.concatenate([index[u] for u in rng.choice(unique, size=len(unique), replace=True)])
        if metric in ("pr_auc", "roc_auc") and len(set(y[rows])) < 2:
            continue
        values.append(metrics(y[rows], p_b[rows])[metric] - metrics(y[rows], p_a[rows])[metric])
    if len(values) < draws // 2:
        return None
    return [float(np.quantile(values, alpha / 2)), float(np.quantile(values, 1 - alpha / 2))]


def evaluate(train, valid, test, seed: int, use_text: bool, draws: int = 1000) -> dict:
    y, g = np.array([e.label for e in test]), np.array([e.group_id for e in test])
    out, predictions = {}, {}
    majority = float(np.clip(np.mean([e.label for e in train]), 1e-6, 1 - 1e-6))
    predictions["majority"] = np.full(len(test), majority)
    for model in (Pooled(seed, use_text), GRUModel(seed, use_text)):
        start = time.perf_counter()
        model.fit(train, valid)
        predictions[model.name] = model.predict_proba(test)
        out[model.name] = {"choice": model.choice, "valid_log_loss": round(float(model.valid_loss), 4),
                           "parameters": model.parameters, "seconds": round(time.perf_counter() - start, 2)}
        if isinstance(model, GRUModel):
            out[model.name]["epochs_run"] = model.epochs_run
    out.setdefault("majority", {})
    for name, p in predictions.items():
        out[name].update(metrics(y, p))
        for m in ("pr_auc", "brier"):
            out[name][f"{m}_ci95_groups"] = group_bootstrap(y, p, g, m, draws=draws, seed=seed)
    out["gru_minus_pooled"] = {m: paired_difference(y, predictions["pooled_logistic"], predictions["gru"], g, m,
                                                    draws=draws, seed=seed) for m in ("pr_auc", "brier")}
    return out


def split(examples):
    return ([e for e in examples if e.partition == "train"], [e for e in examples if e.partition == "validation"],
            [e for e in examples if e.partition == "test"])


def experiment(records: list[dict], horizons=(1, 2, 3), seeds=(0, 1, 2), draws: int = 1000) -> dict:
    import platform

    import sklearn
    import torch
    report = {"manifest": {"hypothesis": "H-S10: an ordered event encoder (GRU) predicts runs that need review "
                                         "better than an order-free pooled encoder at the same horizon",
                           "sequence_version": SEQ_VERSION, "label": "business != SUCCESS",
                           "horizon": "events up to and including the k-th model call; output never visible",
                           "selection": "two values per model, chosen on validation groups; test scored once",
                           "seeds": list(seeds), "torch": torch.__version__, "sklearn": sklearn.__version__,
                           "python": platform.python_version()},
              "horizons": {}}
    for k in horizons:
        examples = [x for x in (to_sequence(r, k) for r in records) if x is not None]
        train, valid, test = split(examples)
        entry = {"population_runs": len(examples), "test_runs": len(test),
                 "test_groups": len({e.group_id for e in test}),
                 "mean_events": round(float(np.mean([len(e.events) for e in examples])), 2) if examples else 0,
                 "prevalence_test": round(float(np.mean([e.label for e in test])), 3) if test else None}
        if len({e.label for e in test}) < 2 or len({e.label for e in valid}) < 2 or len(test) < 20:
            entry["skipped"] = "too few runs or a single class in validation or test"
            report["horizons"][str(k)] = entry
            continue
        entry["seeds"] = {str(s): evaluate(train, valid, test, s, True, draws) for s in seeds}
        entry["structure_only"] = evaluate(train, valid, test, seeds[0], False, draws)
        rng = np.random.default_rng(seeds[0])
        entry["order_shuffled"] = evaluate([shuffled(e, rng) for e in train], [shuffled(e, rng) for e in valid],
                                           [shuffled(e, rng) for e in test], seeds[0], True, draws)
        report["horizons"][str(k)] = entry
    return report
