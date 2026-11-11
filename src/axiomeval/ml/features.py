"""Feature contract for task B: predict, at an early instant, whether a run will need review.

Prediction instant (horizon): right after the first model call, before any tool
is executed and before any final answer exists. Only the events `input`,
`retrieval` and the first `model_call` are visible. The label is
"business outcome is not SUCCESS". Spec §12.2 and §18.

Excluded on purpose (shortcuts or future information): release id, model name,
latency (it reveals the model size), authorization results, tool results,
guard events, the final answer and any score.
"""
from dataclasses import dataclass

from axiomeval.collect.secure_tools import SECURE_TOOL_SPECS

# v2: one indicator per retrieved document name, learned on train (v1 knew only the six corpus-v1 documents).
FEATURE_VERSION = "prefix-features-v2"
VISIBLE_KINDS = ("input", "retrieval", "model_call")
TOOLS = tuple(spec["function"]["name"] for spec in SECURE_TOOL_SPECS)


@dataclass(frozen=True)
class Example:
    run_key: str
    group_id: str
    release_id: str
    partition: str
    kind: str
    text: str
    structure: dict
    label: int


def prefix(trace: list[dict]) -> list[dict]:
    """Events visible at the horizon: everything up to and including the first model call."""
    out = []
    for event in trace:
        if event["kind"] not in VISIBLE_KINDS:
            break
        out.append(event)
        if event["kind"] == "model_call":
            break
    return out


def structure_features(events: list[dict]) -> dict:
    docs = next((e["data"]["documents"] for e in events if e["kind"] == "retrieval"), [])
    call = next((e["data"] for e in events if e["kind"] == "model_call"), None)
    requested = [name for name, _ in call["tool_calls"]] if call else []
    features = {f"doc:{d}": 1.0 for d in docs}  # unseen names are dropped by the vectorizer fit on train
    features.update({f"first_tool:{t}": float(t in requested) for t in TOOLS})
    features["first_step_answers_directly"] = float(call is not None and not requested)
    features["first_step_missing"] = float(call is None)
    features["n_tools_requested"] = float(len(requested))
    features["prompt_tokens_100"] = (call or {}).get("prompt_tokens", 0) / 100.0
    features["first_text_chars_100"] = len((call or {}).get("content", "")) / 100.0
    return features


def to_example(record: dict) -> Example:
    events = prefix(record["trace"])
    question = next((e["data"]["question"] for e in events if e["kind"] == "input"), "")
    return Example(record["draw_key"], record["group_id"], record["release_id"], record["partition"],
                   record["kind"], question, structure_features(events),
                   int(record["business"] != "SUCCESS"))


def leaked_keys(record: dict) -> list[str]:
    """Kinds after the horizon that the features must never read (audit helper for tests)."""
    seen = {e["kind"] for e in prefix(record["trace"])}
    return sorted({e["kind"] for e in record["trace"]} - seen)
