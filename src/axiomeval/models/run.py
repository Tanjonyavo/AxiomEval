"""Each observation belongs to one execution, even for repeated inputs."""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from axiomeval.errors import ValidationError
from axiomeval.ids import new_run_id
from axiomeval.models.validation import text


@dataclass(frozen=True)
class Run:
    target_id: str
    scenario_id: str
    id: str = field(default_factory=new_run_id)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for name in ("target_id", "scenario_id", "id"):
            object.__setattr__(self, name, text(getattr(self, name), name))
        if not isinstance(self.started_at, datetime) or self.started_at.utcoffset() is None:
            raise ValidationError("started_at must be a timezone-aware datetime")
