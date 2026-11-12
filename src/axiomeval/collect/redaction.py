"""Sensitive values are removed before any trace reaches a log or a report.

Canaries are removed in their plain form and in the transformed forms the
egress guard detects (separated letters, other case, reversed, base64,
hexadecimal): finding F-006 showed a spaced canary written to a run file.
"""
import base64
import binascii
import functools
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
_B64 = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
_HEX = re.compile(r"\b[0-9a-fA-F]{24,}\b")


def squash(value: str) -> str:
    """Letters and digits only, upper case: the form in which variants are compared."""
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def decode_token(token: str) -> list[str]:
    """Readings of one base64-like or hexadecimal token (empty when it decodes to nothing)."""
    views = []
    if _B64.fullmatch(token):
        try:
            views.append(base64.b64decode(token + "=" * (-len(token) % 4), validate=False).decode("utf-8", "ignore"))
        except (binascii.Error, ValueError):
            pass
    if _HEX.fullmatch(token):
        try:
            views.append(bytes.fromhex(token if len(token) % 2 == 0 else token[:-1]).decode("utf-8", "ignore"))
        except ValueError:
            pass
    return views


def decoded_views(value: str) -> list[str]:
    return [view for regex in (_B64, _HEX) for token in regex.findall(value) for view in decode_token(token)]


@functools.lru_cache(maxsize=64)
def _spread(key: str) -> re.Pattern:
    """The key with up to three separators between characters, any case."""
    return re.compile(r"[^A-Za-z0-9]{0,3}".join(re.escape(c) for c in key), re.IGNORECASE)


def _mask_squashed(value: str, key: str, mark: str) -> str:
    """Mask `key` wherever it appears in the squashed form of `value`, whatever separates its characters.

    This is the definition `leaked` uses, so anything it would detect is masked here
    (separators beyond the three `_spread` allows reached a run file otherwise).
    """
    positions = [i for i, ch in enumerate(value) if ch.isascii() and ch.isalnum()]
    skeleton = "".join(value[i] for i in positions).upper()
    spans, start = [], skeleton.find(key)
    while start != -1:
        spans.append((positions[start], positions[start + len(key) - 1] + 1))
        start = skeleton.find(key, start + len(key))
    for begin, end in reversed(spans):
        value = value[:begin] + mark + value[end:]
    return value


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
        squashed = squash(value)
        views = [squash(v) for v in decoded_views(value)]
        return any(squash(c) in squashed or squash(c)[::-1] in squashed or any(squash(c) in v for v in views)
                   for c in self.canaries)

    def redact(self, value: str) -> str:
        for canary in self.canaries:
            value = value.replace(canary, "[REDACTED:canary]")
            key = squash(canary)
            value = _spread(key).sub("[REDACTED:canary]", value)
            value = _spread(key[::-1]).sub("[REDACTED:canary]", value)
            value = _mask_squashed(value, key, "[REDACTED:canary]")
            value = _mask_squashed(value, key[::-1], "[REDACTED:canary]")
        if not any(regex.search(value) for regex in (_B64, _HEX)):
            return self._patterns(value)
        for regex in (_B64, _HEX):
            value = regex.sub(lambda m: "[REDACTED:canary]" if any(
                squash(c) in squash(v) for c in self.canaries for v in decode_token(m.group(0))) else m.group(0), value)
        return self._patterns(value)

    @staticmethod
    def _patterns(value: str) -> str:
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
