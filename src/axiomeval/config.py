"""Safe YAML parsing followed by explicit week-1 schema validation."""
from dataclasses import dataclass
from pathlib import Path

import yaml

from axiomeval.errors import ConfigurationError, ValidationError
from axiomeval.models import Scenario, Target
from axiomeval.models.validation import text

LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class UniqueKeyLoader(yaml.SafeLoader):
    """A duplicate key is an error, never a silently replaced policy."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ConfigurationError("YAML keys must be unique strings")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


@dataclass(frozen=True)
class Config:
    target: Target
    scenario: Scenario
    environment: str
    log_level: str
    max_evidence_age_seconds: int
    required_evidence_count: int


def mapping(value: object, expected: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise ConfigurationError(f"{name} must contain exactly: {', '.join(sorted(expected))}")
    return value


def bounded_int(value: object, name: str, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise ConfigurationError(f"{name} must be an integer from 1 to {maximum}")
    return value


def load_config(path: str | Path) -> Config:
    """Reject unreadable, ambiguous or unsupported configuration before a run."""
    try:
        content = Path(path).read_text(encoding="utf-8")
        if len(content) > 65_536:
            raise ConfigurationError("Configuration exceeds the 65536 character limit")
        data = yaml.load(content, Loader=UniqueKeyLoader)
    except (OSError, UnicodeError) as exc:
        raise ConfigurationError("Configuration file cannot be read as UTF-8") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError("Invalid YAML configuration") from exc
    root = mapping(data, {"project", "logging", "target", "scenario", "policy"}, "root")
    project = mapping(root["project"], {"name", "environment"}, "project")
    log = mapping(root["logging"], {"level"}, "logging")
    target = mapping(root["target"], {"name", "release", "forbidden_tools"}, "target")
    scenario = mapping(root["scenario"], {"name", "attack_input"}, "scenario")
    policy = mapping(root["policy"], {"max_evidence_age_seconds", "required_evidence_count"}, "policy")
    if project["name"] != "AxiomEval":
        raise ConfigurationError("project.name must be AxiomEval")
    if not isinstance(log["level"], str) or log["level"] not in LOG_LEVELS:
        raise ConfigurationError("logging.level must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
    if not isinstance(target["forbidden_tools"], list) or not target["forbidden_tools"]:
        raise ConfigurationError("target.forbidden_tools must be a nonempty list")
    try:
        return Config(
            target=Target(target["name"], target["release"], tuple(target["forbidden_tools"])),
            scenario=Scenario(scenario["name"], scenario["attack_input"]),
            environment=text(project["environment"], "project.environment"),
            log_level=log["level"],
            max_evidence_age_seconds=bounded_int(policy["max_evidence_age_seconds"], "max_evidence_age_seconds", 86_400),
            required_evidence_count=bounded_int(policy["required_evidence_count"], "required_evidence_count", 10),
        )
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc
