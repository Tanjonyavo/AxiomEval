"""The release and tool policy define which target is evaluated."""
from dataclasses import dataclass, field

from axiomeval.ids import stable_id
from axiomeval.models.validation import text, tools


@dataclass(frozen=True)
class Target:
    name: str
    release: str
    forbidden_tools: tuple[str, ...]
    id: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", text(self.name, "target.name"))
        object.__setattr__(self, "release", text(self.release, "target.release"))
        object.__setattr__(self, "forbidden_tools", tools(self.forbidden_tools))
        object.__setattr__(self, "id", stable_id("TGT", [self.name, self.release, self.forbidden_tools]))
