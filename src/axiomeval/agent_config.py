"""Configuration of a real, bounded agent run (lot P02); stricter than the S1 schema."""
from dataclasses import dataclass
from pathlib import Path

import yaml

from axiomeval.config import LOG_LEVELS, UniqueKeyLoader, bounded_int, mapping
from axiomeval.errors import ConfigurationError, ValidationError
from axiomeval.models import Target
from axiomeval.models.validation import text

ADAPTERS = ("ollama", "scripted")


@dataclass(frozen=True)
class AgentConfig:
    target: Target
    log_level: str
    adapter: dict
    knowledge_base: Path
    orders: Path
    tasks: Path
    canaries: tuple[str, ...]
    max_evidence_age_seconds: int
    required_evidence_count: int
    repetitions: int


def load_agent_config(path: str | Path) -> AgentConfig:
    """Paths are resolved relative to the configuration file."""
    path = Path(path)
    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > 65_536:
            raise ConfigurationError("Configuration exceeds the 65536 character limit")
        data = yaml.load(content, Loader=UniqueKeyLoader)
    except (OSError, UnicodeError) as exc:
        raise ConfigurationError("Configuration file cannot be read as UTF-8") from exc
    except (yaml.YAMLError, RecursionError) as exc:
        raise ConfigurationError("Invalid YAML configuration") from exc
    root = mapping(data, {"project", "logging", "target", "adapter", "corpus", "policy"}, "root")
    project = mapping(root["project"], {"name", "environment"}, "project")
    log = mapping(root["logging"], {"level"}, "logging")
    target = mapping(root["target"], {"name", "release", "forbidden_tools"}, "target")
    adapter = root["adapter"]
    corpus = mapping(root["corpus"], {"knowledge_base", "orders", "tasks", "canaries"}, "corpus")
    policy = mapping(root["policy"], {"max_evidence_age_seconds", "required_evidence_count",
                                      "repetitions"}, "policy")
    if project["name"] != "AxiomEval":
        raise ConfigurationError("project.name must be AxiomEval")
    if log["level"] not in LOG_LEVELS:
        raise ConfigurationError("logging.level is invalid")
    if not isinstance(adapter, dict) or adapter.get("kind") not in ADAPTERS:
        raise ConfigurationError("adapter.kind must be ollama or scripted")
    expected = ({"kind", "base_url", "model", "temperature", "seed", "timeout_seconds", "max_steps"}
                if adapter["kind"] == "ollama" else {"kind", "script", "max_steps"})
    mapping(adapter, expected, "adapter")
    bounded_int(adapter["max_steps"], "adapter.max_steps", 8)
    if adapter["kind"] == "ollama":
        if type(adapter["temperature"]) not in (int, float) or not 0 <= adapter["temperature"] <= 2:
            raise ConfigurationError("adapter.temperature must be between 0 and 2")
        bounded_int(adapter["timeout_seconds"], "adapter.timeout_seconds", 600)
        if type(adapter["seed"]) is not int:
            raise ConfigurationError("adapter.seed must be an integer")
    if not isinstance(target["forbidden_tools"], list) or "disclose_protected_secret" not in target["forbidden_tools"]:
        raise ConfigurationError("target.forbidden_tools must include disclose_protected_secret")
    if not isinstance(corpus["canaries"], list) or not corpus["canaries"]:
        raise ConfigurationError("corpus.canaries must be a nonempty list")
    base = path.resolve().parent
    resolve = lambda value, name: (base / text(value, name)).resolve()
    if adapter["kind"] == "scripted":
        adapter = dict(adapter, script=resolve(adapter["script"], "adapter.script"))
    try:
        return AgentConfig(
            target=Target(target["name"], target["release"], tuple(target["forbidden_tools"])),
            log_level=log["level"], adapter=adapter,
            knowledge_base=resolve(corpus["knowledge_base"], "corpus.knowledge_base"),
            orders=resolve(corpus["orders"], "corpus.orders"),
            tasks=resolve(corpus["tasks"], "corpus.tasks"),
            canaries=tuple(text(c, "canary") for c in corpus["canaries"]),
            max_evidence_age_seconds=bounded_int(policy["max_evidence_age_seconds"],
                                                 "max_evidence_age_seconds", 86_400),
            required_evidence_count=bounded_int(policy["required_evidence_count"],
                                                "required_evidence_count", 10),
            repetitions=bounded_int(policy["repetitions"], "repetitions", 20),
        )
    except (ValidationError, TypeError) as exc:
        raise ConfigurationError(str(exc)) from exc
