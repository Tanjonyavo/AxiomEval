"""One documented connector (Ollama, local only) and a scripted stand-in for tests."""
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from axiomeval.errors import ConfigurationError, ValidationError

LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class AdapterError(ValidationError):
    """The model could not answer; the run is incomplete, never successful."""


@dataclass(frozen=True)
class ModelReply:
    content: str
    tool_calls: tuple[tuple[str, dict], ...]
    prompt_tokens: int
    output_tokens: int
    latency_seconds: float


def local_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_HOSTS:
        raise ConfigurationError("adapter.base_url must be http on localhost: data stays on this machine")
    return value.rstrip("/")


def _tool_calls(message: dict) -> tuple[tuple[str, dict], ...]:
    calls = []
    for call in message.get("tool_calls") or ():
        function = call.get("function", {})
        args = function.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {"raw": args}
        calls.append((str(function.get("name", "")), args if isinstance(args, dict) else {}))
    return tuple(calls)


@dataclass
class OllamaAdapter:
    base_url: str
    model: str
    temperature: float
    seed: int
    timeout_seconds: int
    kind: str = field(default="ollama", init=False)

    def __post_init__(self) -> None:
        self.base_url = local_url(self.base_url)

    def _post(self, path: str, body: dict) -> dict:
        request = urllib.request.Request(
            self.base_url + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeError) as exc:
            raise AdapterError(f"local model unavailable: {type(exc).__name__}") from exc

    def _get(self, path: str) -> dict:
        try:
            with urllib.request.urlopen(self.base_url + path, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeError) as exc:
            raise AdapterError(f"local model unavailable: {type(exc).__name__}") from exc

    def chat(self, messages: list[dict], tools: tuple[dict, ...]) -> ModelReply:
        start = time.perf_counter()
        body = {"model": self.model, "messages": messages, "tools": list(tools), "stream": False,
                "options": {"temperature": self.temperature, "seed": self.seed}}
        data = self._post("/api/chat", body)
        message = data.get("message") or {}
        return ModelReply(str(message.get("content", "")), _tool_calls(message),
                          int(data.get("prompt_eval_count", 0)), int(data.get("eval_count", 0)),
                          round(time.perf_counter() - start, 4))

    def model_digest(self) -> str:
        """Resolve the configured local model tag to its installed artifact."""
        tags = {m.get("name"): m for m in self._get("/api/tags").get("models", [])}
        entry = tags.get(self.model) or tags.get(f"{self.model}:latest", {})
        fingerprint = entry.get("digest")
        if not isinstance(fingerprint, str) or not fingerprint:
            raise AdapterError("installed model digest is unavailable")
        return fingerprint

    def describe(self) -> dict:
        """Provenance and resources: model digest, licence, memory used by the loaded model."""
        show = self._post("/api/show", {"model": self.model})
        tags = {m.get("name"): m for m in self._get("/api/tags").get("models", [])}
        loaded = {m.get("name"): m for m in self._get("/api/ps").get("models", [])}
        licence = str(show.get("license", "")).strip().splitlines()
        details = show.get("details", {})
        running = loaded.get(self.model, {})
        version = self._get("/api/version").get("version", "inconnue")
        return {
            "adapter": "ollama", "ollama_version": version, "model": self.model,
            "model_digest": tags.get(self.model, {}).get("digest", "inconnu"),
            "parameter_size": details.get("parameter_size"), "quantization": details.get("quantization_level"),
            "licence_first_line": licence[0] if licence else "non déclarée",
            "model_memory_bytes": running.get("size"), "model_vram_bytes": running.get("size_vram"),
            "monetary_cost": "0 (exécution locale ; énergie non mesurée)",
        }


@dataclass
class ScriptedAdapter:
    """Replays prewritten model replies. Synthetic: it tests the harness, not a model."""
    script_path: Path
    kind: str = field(default="scripted", init=False)
    replies: dict = field(default_factory=dict, init=False)
    task_id: str = field(default="", init=False)
    _cursor: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        try:
            self.replies = json.loads(Path(self.script_path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConfigurationError("scripted adapter file cannot be read") from exc

    def start_task(self, task_id: str) -> None:
        self.task_id, self._cursor = task_id, 0

    def chat(self, messages: list[dict], tools: tuple[dict, ...]) -> ModelReply:
        steps = self.replies.get(self.task_id, [])
        if self._cursor >= len(steps):
            raise AdapterError("scripted model has no reply for this step")
        step = steps[self._cursor]
        self._cursor += 1
        calls = tuple((c["name"], c.get("arguments", {})) for c in step.get("tool_calls", []))
        return ModelReply(step.get("content", ""), calls, 0, 0, 0.0)

    def describe(self) -> dict:
        return {"adapter": "scripted", "model": "scripted-replies", "synthetic": True,
                "monetary_cost": "0"}
