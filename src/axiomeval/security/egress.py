"""Egress guard: the last control before an answer reaches the user (S7, spec §31.8).

The guard looks for planted canaries in plain and transformed forms (base64,
hexadecimal, reversed, separated letters, upper/lower case) and for common
secret patterns. When it finds one it replaces the whole answer by a refusal:
partial masking could still leak the surrounding context.
"""
from dataclasses import dataclass

from axiomeval.collect.redaction import PATTERNS, decoded_views as _decoded_views, squash as _squash

REFUSAL = "Je ne peux pas communiquer cette information."


@dataclass(frozen=True)
class GuardResult:
    answer: str
    findings: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.findings)


@dataclass(frozen=True)
class OutputGuard:
    canaries: tuple[str, ...]

    def check(self, answer: str) -> GuardResult:
        findings = []
        squashed = _squash(answer)
        for canary in self.canaries:
            key = _squash(canary)
            if canary in answer:
                findings.append("canary:plain")
            elif key in squashed:
                findings.append("canary:spaced-or-case")
            elif key[::-1] in squashed:
                findings.append("canary:reversed")
            elif any(key in _squash(view) for view in _decoded_views(answer)):
                findings.append("canary:encoded")
        for kind, pattern in PATTERNS:
            if kind != "email" and pattern.search(answer):
                findings.append(f"secret-pattern:{kind}")
        findings = tuple(dict.fromkeys(findings))
        return GuardResult(REFUSAL if findings else answer, findings)
