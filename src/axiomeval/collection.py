"""Collect real trajectories of one release over the grouped corpus (S3-S4, lot P03).

Each record is one draw of one scenario: it keeps the release and corpus
digests, the group, the frozen partition, the draw seed, the redacted
hash-chained trace and the three separate scores. Replaying an existing
(release, scenario, draw) key is refused, so a cached object never inflates n.
"""
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from axiomeval.collect.adapters import OllamaAdapter
from axiomeval.collect.agent import run_agent
from axiomeval.collect.knowledge import load_documents
from axiomeval.collect.oracle import Task
from axiomeval.collect.redaction import Redactor
from axiomeval.collect.secure_tools import SECURE_TOOL_SPECS, SecureToolbox
from axiomeval.collect.trace import TraceRecorder, trace_digest, validate_trace
from axiomeval.corpus.evaluate import evaluate_scenario
from axiomeval.corpus.release import Release
from axiomeval.corpus.scenarios import Corpus
from axiomeval.errors import ValidationError
from axiomeval.ids import digest
from axiomeval.models import Run
from axiomeval.policy.authz import Identity, Policy

EVALUATOR_VERSION = "corpus-evaluator-v1"


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def draw_key(release: Release, scenario_id: str, draw: int) -> str:
    return digest({"release": release.digest, "scenario": scenario_id, "draw": draw,
                   "evaluator": EVALUATOR_VERSION})


def existing_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {json.loads(line)["draw_key"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def collect(release: Release, corpus: Corpus, partitions: dict[str, str], policy: Policy, kb_dir: Path,
            orders: dict, canaries: tuple[str, ...], out: Path, draws: int = 1,
            only_partitions: tuple[str, ...] | None = None, adapter=None, clock=_clock,
            base_url: str = "http://127.0.0.1:11434", limit: int | None = None) -> dict:
    """Run every selected scenario `draws` times; append one JSON line per run."""
    docs = load_documents(kb_dir)
    redactor = Redactor(canaries)
    adapter = adapter or OllamaAdapter(base_url, release.model, release.temperature, release.seed, 180)
    seen = existing_keys(out)
    written, skipped = 0, 0
    selected = [s for s in corpus.scenarios
                if only_partitions is None or partitions[s.group_id] in only_partitions]
    if limit is not None:
        selected = selected[:limit]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as stream:
        for scenario in selected:
            for draw in range(draws):
                key = draw_key(release, scenario.scenario_id, draw)
                if key in seen:
                    skipped += 1
                    continue
                record = _one(release, scenario, partitions[scenario.group_id], draw, key, policy, docs,
                              orders, redactor, canaries, adapter, clock)
                line = json.dumps(record, ensure_ascii=False, default=str)
                redactor.assert_clean(line)
                stream.write(line + "\n")
                seen.add(key)
                written += 1
    return {"written": written, "skipped_existing": skipped, "file": str(out)}


def _one(release, scenario, partition, draw, key, policy, docs, orders, redactor, canaries, adapter, clock):
    if hasattr(adapter, "seed"):
        adapter.seed = release.seed + draw  # a new draw is a new seed, never a replay
    if hasattr(adapter, "start_task"):
        adapter.start_task(scenario.scenario_id)
    started = clock()
    if scenario.label_frozen_at > started:
        raise ValidationError(f"label of {scenario.scenario_id} frozen after the run started")
    run = Run(release.digest, scenario.scenario_id, started_at=started)
    identity = Identity(scenario.identity, "customer", "avana", started + timedelta(minutes=30))
    toolbox = SecureToolbox(docs, orders, policy, identity, clock)
    recorder = TraceRecorder(run, clock, redactor)
    task = Task(scenario.scenario_id, scenario.question, (), (), scenario.label_frozen_at)
    answer, _ = run_agent(adapter, toolbox, docs, task, recorder, release.max_steps,
                          system=release.system_prompt, tool_specs=SECURE_TOOL_SPECS,
                          retrieval_k=release.retrieval_k)
    events = tuple(recorder.events)
    validate_trace(events, run, clock())
    authz = [e.data for e in events if e.kind == "authz"]
    score = evaluate_scenario(scenario, answer, authz, toolbox.raw_calls, toolbox.ledger.refunds, canaries)
    calls = [e.data for e in events if e.kind == "model_call"]
    return {
        "draw_key": key, "evaluator": EVALUATOR_VERSION, "release_id": release.release_id,
        "release_digest": release.digest, "scenario_id": scenario.scenario_id, "group_id": scenario.group_id,
        "family": scenario.family, "kind": scenario.kind, "attack_family": scenario.attack_family,
        "partition": partition, "draw": draw, "seed": release.seed + draw, "run_id": run.id,
        "started_at": started.isoformat(), "label_source": scenario.label_source,
        "business": score.business.value, "permission": score.permission.value, "reasons": list(score.reasons),
        "security": asdict(score.security), "refunds": toolbox.ledger.refunds,
        "escalations": len(toolbox.ledger.escalations),
        "latency_seconds": round(sum(c.get("latency_seconds", 0) for c in calls), 4),
        "prompt_tokens": sum(c.get("prompt_tokens", 0) for c in calls),
        "output_tokens": sum(c.get("output_tokens", 0) for c in calls),
        "trace_digest": trace_digest(events), "trace": [asdict(e) for e in events],
    }


def load_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
