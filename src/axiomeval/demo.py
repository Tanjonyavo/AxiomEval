"""Handwritten fixtures exercise architecture, not an AI agent's capabilities."""
from dataclasses import dataclass
from datetime import datetime, timezone

from axiomeval.config import Config
from axiomeval.errors import ValidationError
from axiomeval.evaluators.deterministic import Evaluation, evaluate
from axiomeval.models import Evidence, Run, make_evidence
from axiomeval.policies.gate import Decision, decide

CASES = ("safe", "violation", "missing", "uncertain")


@dataclass(frozen=True)
class DemoResult:
    case: str
    run: Run
    evidence: tuple[Evidence, ...]
    evaluation: Evaluation
    decision: Decision


def run_demo(config: Config, case: str) -> DemoResult:
    if case not in CASES:
        raise ValidationError("Unknown synthetic demo case")
    run = Run(config.target.id, config.scenario.id)
    # These strings are observations only. No tool is called.
    observed = (config.target.forbidden_tools[0],) if case == "violation" else ()
    evidence = () if case == "missing" else (
        make_evidence(run, observed, uncertain=case == "uncertain"),
    )
    evaluation = evaluate(
        config.target, config.scenario, run, evidence, now=datetime.now(timezone.utc),
        max_age_seconds=config.max_evidence_age_seconds,
        required_count=config.required_evidence_count,
    )
    return DemoResult(case, run, evidence, evaluation, decide(evaluation))
