"""A rule finding links back to one checked synthetic observation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    id: str
    evidence_id: str
    tool: str
    severity: str = "critical"
    confirmed: bool = True
    rule: str = "forbidden-tool-observed"
