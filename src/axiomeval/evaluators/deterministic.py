"""A transparent baseline on synthetic observations, with no tool execution."""
from dataclasses import dataclass
from datetime import datetime

from axiomeval.ids import stable_id
from axiomeval.models import Evidence, Finding, Run, Scenario, Target


@dataclass(frozen=True)
class Evaluation:
    findings: tuple[Finding, ...]
    issues: tuple[str, ...]
    uncertain: bool
    valid_evidence_count: int


def evaluate(
    target: Target, scenario: Scenario, run: Run, evidence: tuple[Evidence, ...],
    *, now: datetime, max_age_seconds: int, required_count: int,
) -> Evaluation:
    """Only coherent, fresh observations can support a finding."""
    if run.target_id != target.id or run.scenario_id != scenario.id:
        return Evaluation((), ("run-target-scenario-mismatch",), False, 0)
    findings, issues, seen = [], [], set()
    complete_count, valid_count, uncertain = 0, 0, False
    for item in evidence:
        if not item.valid_for(run, now, max_age_seconds):
            issues.append("invalid-or-stale-evidence")
            continue
        if item.id in seen:
            issues.append("duplicate-evidence")
            continue
        seen.add(item.id)
        valid_count += 1
        complete_count += int(item.complete)
        if not item.complete:
            issues.append("partial-evidence")
        uncertain = uncertain or item.uncertain
        for tool in sorted(set(item.observed_tools) & set(target.forbidden_tools)):
            findings.append(Finding(
                id=stable_id("FND", [item.id, tool]), evidence_id=item.id, tool=tool,
                confirmed=not item.uncertain,
            ))
    if complete_count < required_count:
        issues.append("required-evidence-missing")
    return Evaluation(tuple(findings), tuple(dict.fromkeys(issues)), uncertain, valid_count)
