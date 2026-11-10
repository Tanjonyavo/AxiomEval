"""Release manifests: what exactly is being evaluated (model, prompt, retrieval, policy)."""
from dataclasses import dataclass
from pathlib import Path

import yaml

from axiomeval.config import UniqueKeyLoader
from axiomeval.errors import ConfigurationError
from axiomeval.ids import digest
from axiomeval.models.validation import text

FIELDS = {"release_id", "description", "model", "temperature", "seed", "retrieval_k", "max_steps", "system_prompt"}
OPTIONAL = {"output_guard"}
# egress-v2: the guard also checks tool arguments before execution (fix for finding F-001).
GUARD_VERSION = "egress-v2"


@dataclass(frozen=True)
class Release:
    release_id: str
    description: str
    model: str
    temperature: float
    seed: int
    retrieval_k: int
    max_steps: int
    system_prompt: str
    digest: str
    output_guard: bool = False

    def identity(self) -> dict:
        """Everything that changes behaviour; the digest of this dict names the release."""
        identity = {"release_id": self.release_id, "model": self.model, "temperature": self.temperature,
                    "seed": self.seed, "retrieval_k": self.retrieval_k, "max_steps": self.max_steps,
                    "system_prompt_sha256": digest(self.system_prompt)}
        if self.output_guard:
            identity["output_guard"] = True
            identity["guard_version"] = GUARD_VERSION
        return identity


def load_release(path: Path) -> Release:
    try:
        raw = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError("release manifest cannot be read") from exc
    if not isinstance(raw, dict) or not FIELDS <= set(raw) <= FIELDS | OPTIONAL:
        raise ConfigurationError("release manifest needs exactly: " + ", ".join(sorted(FIELDS))
                                 + " (optional: " + ", ".join(sorted(OPTIONAL)) + ")")
    if type(raw.get("output_guard", False)) is not bool:
        raise ConfigurationError("output_guard must be true or false")
    if "{context}" not in raw["system_prompt"]:
        raise ConfigurationError("system_prompt must contain the {context} placeholder")
    if type(raw["temperature"]) not in (int, float) or not 0 <= raw["temperature"] <= 2:
        raise ConfigurationError("temperature must be between 0 and 2")
    for name, upper in (("seed", 2**31 - 1), ("retrieval_k", 5), ("max_steps", 8)):
        if type(raw[name]) is not int or not 0 <= raw[name] <= upper:
            raise ConfigurationError(f"{name} out of range")
    release = Release(text(raw["release_id"], "release_id"), text(raw["description"], "description"),
                      text(raw["model"], "model"), float(raw["temperature"]), raw["seed"], raw["retrieval_k"],
                      raw["max_steps"], raw["system_prompt"], "", raw.get("output_guard", False))
    return Release(**{**release.__dict__, "digest": digest(release.identity())})
