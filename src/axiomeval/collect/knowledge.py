"""A small local documentation base and a transparent keyword retrieval."""
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from axiomeval.errors import ConfigurationError

MAX_DOC_CHARS = 20_000


def _words(value: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode()
    return {word for word in re.findall(r"[a-z0-9]+", plain) if len(word) > 2}


@dataclass(frozen=True)
class Document:
    name: str
    content: str


def load_documents(directory: Path) -> tuple[Document, ...]:
    try:
        paths = sorted(directory.glob("*.md"))
        docs = tuple(Document(p.stem, p.read_text(encoding="utf-8")) for p in paths)
    except (OSError, UnicodeError) as exc:
        raise ConfigurationError("knowledge base cannot be read") from exc
    if not docs or any(len(d.content) > MAX_DOC_CHARS for d in docs):
        raise ConfigurationError("knowledge base must contain 1+ markdown files under 20000 characters")
    return docs


def retrieve(docs: tuple[Document, ...], question: str, k: int = 2) -> tuple[Document, ...]:
    """Rank by shared words; ties keep file order so results are reproducible."""
    query = _words(question)
    scored = [(len(query & _words(d.content)), -i, d) for i, d in enumerate(docs)]
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return tuple(d for score, _, d in scored[:k] if score > 0)


def load_orders(path: Path) -> dict[str, dict]:
    try:
        orders = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError("orders file cannot be read") from exc
    if not isinstance(orders, dict):
        raise ConfigurationError("orders file must map order ids to records")
    return orders
