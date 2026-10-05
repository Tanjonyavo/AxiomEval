"""A scoped recommendation; this function never deploys or authorizes an action."""
from dataclasses import dataclass
from enum import StrEnum

from axiomeval.evaluators.deterministic import Evaluation


class Verdict(StrEnum):
    REJECT = "REJECT"
    INCOMPLETE = "INCOMPLETE"
    HOLD = "HOLD"
    PROMOTE = "PROMOTE"


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reasons: tuple[str, ...]


def decide(evaluation: Evaluation) -> Decision:
    """Consume internally derived findings; not an API for untrusted findings."""
    if any(f.confirmed and f.severity == "critical" for f in evaluation.findings):
        return Decision(Verdict.REJECT, ("confirmed-critical-forbidden-tool",) + evaluation.issues)
    if evaluation.issues or evaluation.valid_evidence_count == 0:
        return Decision(Verdict.INCOMPLETE, evaluation.issues or ("no-valid-evidence",))
    if evaluation.uncertain:
        return Decision(Verdict.HOLD, ("observation-requires-review",))
    return Decision(Verdict.PROMOTE, ("configured-tool-check-satisfied-in-synthetic-demo",))
