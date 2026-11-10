"""An ordered, hash-chained trace of one execution; order and repetitions are kept."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from axiomeval.errors import ValidationError
from axiomeval.ids import digest
from axiomeval.models.run import Run

EVENT_KINDS = ("input", "retrieval", "model_call", "tool_call", "tool_result", "output", "error")
GENESIS = "0" * 64
CLOCK_SKEW = timedelta(seconds=5)


class TraceError(ValidationError):
    """A trace cannot be trusted: wrong link, order, time or integrity."""


@dataclass(frozen=True)
class TraceEvent:
    run_id: str
    seq: int
    kind: str
    at: datetime
    data: dict
    prev_hash: str
    hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.kind not in EVENT_KINDS:
            raise TraceError(f"unknown event kind: {self.kind}")
        if type(self.seq) is not int or self.seq < 0:
            raise TraceError("event sequence must be a nonnegative integer")
        if not isinstance(self.at, datetime) or self.at.utcoffset() is None:
            raise TraceError("event time must be timezone-aware")
        object.__setattr__(self, "hash", digest(self.payload()))

    def payload(self) -> dict:
        return {"run_id": self.run_id, "seq": self.seq, "kind": self.kind,
                "at": self.at.isoformat(), "data": self.data, "prev_hash": self.prev_hash}


class TraceRecorder:
    """Appends events in call order; each event commits to the previous one.

    Data are redacted *before* hashing and storing, so the saved trace can be
    re-verified and never contains a planted secret.
    """

    def __init__(self, run: Run, clock, redactor) -> None:
        self.run, self.clock, self.redactor, self.events = run, clock, redactor, []

    def add(self, kind: str, **data) -> TraceEvent:
        prev = self.events[-1].hash if self.events else GENESIS
        clean = self.redactor.redact_obj(data)
        event = TraceEvent(self.run.id, len(self.events), kind, self.clock(), clean, prev)
        self.events.append(event)
        return event


def validate_trace(events: tuple[TraceEvent, ...], run: Run, now: datetime) -> None:
    """Reject false links, reordering, tampering and impossible timestamps."""
    prev_hash, prev_at = GENESIS, run.started_at
    for expected_seq, event in enumerate(events):
        if event.run_id != run.id:
            raise TraceError("event linked to another run")
        if event.seq != expected_seq:
            raise TraceError("event sequence is not contiguous")
        if event.prev_hash != prev_hash or event.hash != digest(event.payload()):
            raise TraceError("hash chain broken: event altered, removed or reordered")
        if event.at < prev_at:
            raise TraceError("event time goes backwards or precedes the run")
        if event.at > now + CLOCK_SKEW:
            raise TraceError("event time is in the future")
        prev_hash, prev_at = event.hash, event.at


def trace_digest(events: tuple[TraceEvent, ...]) -> str:
    return events[-1].hash if events else GENESIS
