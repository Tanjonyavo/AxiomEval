"""Run real tasks, verify each trace, score three separate dimensions, then decide.

No statistical claim is made here: counts describe the runs, nothing more (lot P02).
"""
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timezone

from axiomeval.agent_config import AgentConfig
from axiomeval.collect.adapters import OllamaAdapter, ScriptedAdapter
from axiomeval.collect.agent import run_agent
from axiomeval.collect.knowledge import load_documents, load_orders
from axiomeval.collect.oracle import Business, Permission, Score, check_label_frozen, load_tasks, score
from axiomeval.collect.redaction import Redactor
from axiomeval.collect.trace import TraceEvent, TraceRecorder, trace_digest, validate_trace
from axiomeval.evaluators.deterministic import evaluate
from axiomeval.models import Evidence, Run, Scenario
from axiomeval.policies.gate import Decision, Verdict, decide

DISCLOSURE = "disclose_protected_secret"  # a leaked canary is treated as a forbidden action
SEVERITY = (Verdict.REJECT, Verdict.INCOMPLETE, Verdict.HOLD, Verdict.PROMOTE)


@dataclass(frozen=True)
class RunRecord:
    task_id: str
    repetition: int
    run: Run
    events: tuple[TraceEvent, ...]
    score: Score
    evidence: tuple[Evidence, ...]
    decision: Decision
    wall_seconds: float
    prompt_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class AgentResult:
    provenance: dict
    records: tuple[RunRecord, ...]
    harness_peak_memory_bytes: int

    @property
    def overall(self) -> Verdict:
        verdicts = {r.decision.verdict for r in self.records}
        return next(v for v in SEVERITY if v in verdicts)


def build_adapter(config: AgentConfig):
    a = config.adapter
    if a["kind"] == "scripted":
        return ScriptedAdapter(a["script"])
    return OllamaAdapter(a["base_url"], a["model"], float(a["temperature"]), a["seed"], a["timeout_seconds"])


def _clock() -> datetime:
    return datetime.now(timezone.utc)


def run_tasks(config: AgentConfig, adapter=None, clock=_clock) -> AgentResult:
    from axiomeval.collect.tools import Toolbox

    adapter = adapter or build_adapter(config)
    redactor = Redactor(config.canaries)
    docs, orders = load_documents(config.knowledge_base), load_orders(config.orders)
    tasks = load_tasks(config.tasks)
    toolbox = Toolbox(docs, orders, config.target.forbidden_tools)
    tracemalloc.start()
    records = []
    try:
        for task in tasks:
            scenario = Scenario(task.id, task.question)
            for repetition in range(1, config.repetitions + 1):
                run = Run(config.target.id, scenario.id, started_at=clock())
                check_label_frozen(task, run.started_at)
                if hasattr(adapter, "start_task"):
                    adapter.start_task(task.id)
                recorder = TraceRecorder(run, clock, redactor)
                answer, calls = run_agent(adapter, toolbox, docs, task, recorder,
                                          config.adapter["max_steps"])
                events = tuple(recorder.events)
                now = clock()
                validate_trace(events, run, now)
                records.append(_decide(config, task, repetition, run, scenario, events,
                                       answer, calls, redactor, now))
    finally:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return AgentResult(adapter.describe(), tuple(records), peak)


def _decide(config, task, repetition, run, scenario, events, answer, calls, redactor, now) -> RunRecord:
    called = tuple(n for n, s in calls if s == "executed")
    blocked = tuple(n for n, s in calls if s == "blocked")
    unknown = tuple(n for n, s in calls if s == "unknown")
    leaked = answer is not None and redactor.leaked(answer)
    result = score(task, answer, called, blocked, unknown, leaked)
    observed = tuple(sorted({n for n, _ in calls} | ({DISCLOSURE} if leaked else set())))
    evidence = (Evidence(run.id, run.target_id, run.scenario_id, events[-1].at, observed,
                         complete=result.business is not Business.MISSING,
                         uncertain=result.permission is Permission.UNCERTAIN,
                         synthetic=False, trace_digest=trace_digest(events)),) if events else ()
    evaluation = evaluate(config.target, scenario, run, evidence, now=now,
                          max_age_seconds=config.max_evidence_age_seconds,
                          required_count=config.required_evidence_count)
    calls_meta = [e.data for e in events if e.kind == "model_call"]
    wall = (events[-1].at - run.started_at).total_seconds() if events else 0.0
    return RunRecord(task.id, repetition, run, events, result, evidence, decide(evaluation), round(wall, 3),
                     sum(c.get("prompt_tokens", 0) for c in calls_meta),
                     sum(c.get("output_tokens", 0) for c in calls_meta))
