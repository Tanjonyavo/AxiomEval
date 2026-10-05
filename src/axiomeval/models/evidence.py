"""Synthetic observations with integrity checks; a hash is not a signature."""
from dataclasses import dataclass, field
from datetime import datetime

from axiomeval.errors import ValidationError
from axiomeval.ids import digest, stable_id
from axiomeval.models.run import Run
from axiomeval.models.validation import text, tools


@dataclass(frozen=True)
class Evidence:
    run_id: str
    target_id: str
    scenario_id: str
    observed_at: datetime
    observed_tools: tuple[str, ...]
    complete: bool = True
    uncertain: bool = False
    synthetic: bool = True
    content_hash: str = field(init=False)
    id: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("run_id", "target_id", "scenario_id"):
            object.__setattr__(self, name, text(getattr(self, name), name))
        object.__setattr__(self, "observed_tools", tools(self.observed_tools))
        if not isinstance(self.observed_at, datetime) or self.observed_at.utcoffset() is None:
            raise ValidationError("observed_at must be a timezone-aware datetime")
        if any(type(getattr(self, name)) is not bool for name in ("complete", "uncertain", "synthetic")):
            raise ValidationError("evidence flags must be booleans")
        if not self.synthetic:
            raise ValidationError("week 1 only accepts synthetic evidence")
        object.__setattr__(self, "content_hash", digest(self.payload()))
        object.__setattr__(self, "id", stable_id("EVD", self.payload()))

    def payload(self) -> dict:
        return {
            "run_id": self.run_id, "target_id": self.target_id, "scenario_id": self.scenario_id,
            "observed_at": self.observed_at.isoformat(), "observed_tools": self.observed_tools,
            "complete": self.complete, "uncertain": self.uncertain, "synthetic": self.synthetic,
        }

    def valid_for(self, run: Run, now: datetime, max_age_seconds: int) -> bool:
        age = (now - self.observed_at).total_seconds()
        return (
            self.run_id == run.id and self.target_id == run.target_id
            and self.scenario_id == run.scenario_id and self.synthetic is True
            and self.observed_at >= run.started_at and 0 <= age <= max_age_seconds
            and self.content_hash == digest(self.payload())
            and self.id == stable_id("EVD", self.payload())
        )


def make_evidence(run: Run, observed_tools: tuple[str, ...], **flags: bool) -> Evidence:
    return Evidence(run.id, run.target_id, run.scenario_id, run.started_at, observed_tools, **flags)
