"""Sensitive values are removed before any trace reaches a log or a report."""
import re
from dataclasses import dataclass

from axiomeval.errors import ValidationError
from axiomeval.models.validation import text

PATTERNS = (
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("api-key", re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}\b")),
    ("bearer", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{12,}")),
    ("card", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
)


@dataclass(frozen=True)
class Redactor:
    """Canaries are planted secrets: finding one means a leak, never a normal answer."""
    canaries: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.canaries, tuple) or not self.canaries:
            raise ValidationError("at least one canary secret is required")
        values = tuple(text(item, "canary") for item in self.canaries)
        if any(len(item) < 12 for item in values):
            raise ValidationError("canary secrets must contain at least 12 characters")
        object.__setattr__(self, "canaries", values)

    def leaked(self, value: str) -> bool:
        return any(canary in value for canary in self.canaries)

    def redact(self, value: str) -> str:
        for canary in self.canaries:
            value = value.replace(canary, "[REDACTED:canary]")
        for kind, pattern in PATTERNS:
            value = pattern.sub(f"[REDACTED:{kind}]", value)
        return value

    def redact_obj(self, value: object) -> object:
        """Recursively redact every string of a JSON-compatible value."""
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, list | tuple):
            return [self.redact_obj(item) for item in value]
        if isinstance(value, dict):
            return {key: self.redact_obj(item) for key, item in value.items()}
        return value

    def assert_clean(self, serialized: str) -> None:
        """Last barrier before writing: a canary in an artefact is a bug, not data."""
        if self.leaked(serialized):
            raise ValidationError("a canary secret would be written to disk")
