"""A scenario describes an input; week 1 does not execute that input."""
from dataclasses import dataclass, field

from axiomeval.ids import stable_id
from axiomeval.models.validation import text


@dataclass(frozen=True)
class Scenario:
    name: str
    attack_input: str
    id: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", text(self.name, "scenario.name"))
        object.__setattr__(self, "attack_input", text(self.attack_input, "scenario.attack_input"))
        object.__setattr__(self, "id", stable_id("SCN", [self.name, self.attack_input]))
