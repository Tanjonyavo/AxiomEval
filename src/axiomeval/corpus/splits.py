"""Deterministic, frozen partitions by group (spec §12.4).

Groups are ordered by a salted SHA-256 hash inside each kind, then cut by
cumulative proportions. The result depends only on the group ids, the seed and
the ratios, so it can be recomputed and checked; it never looks at outcomes.
"""
import hashlib
import json
from pathlib import Path

from axiomeval.corpus.scenarios import Corpus
from axiomeval.errors import ValidationError
from axiomeval.ids import digest

PARTITIONS = ("train", "validation", "calibration", "test")
DEFAULT_RATIOS = {"train": 0.55, "validation": 0.15, "calibration": 0.15, "test": 0.15}


def _rank(group_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{group_id}".encode("utf-8")).hexdigest()


def assign(corpus: Corpus, seed: int = 20261110, ratios: dict | None = None) -> dict[str, str]:
    ratios = ratios or DEFAULT_RATIOS
    if set(ratios) != set(PARTITIONS) or abs(sum(ratios.values()) - 1) > 1e-9 or min(ratios.values()) < 0:
        raise ValidationError("ratios must cover the four partitions and sum to 1")
    by_kind: dict[str, list[str]] = {}
    for s in corpus.scenarios:
        groups = by_kind.setdefault(s.kind, [])
        if s.group_id not in groups:
            groups.append(s.group_id)
    result = {}
    for kind in sorted(by_kind):
        groups = sorted(by_kind[kind], key=lambda g: _rank(g, seed))
        n, start = len(groups), 0
        cumulative = 0.0
        for name in PARTITIONS:
            cumulative += ratios[name]
            end = n if name == PARTITIONS[-1] else round(cumulative * n)
            for g in groups[start:end]:
                result[g] = name
            start = end
    return result


def freeze(corpus: Corpus, partitions: dict[str, str], seed: int, path: Path) -> dict:
    payload = {"corpus_id": corpus.corpus_id, "corpus_digest": corpus.digest, "seed": seed,
               "partitions": dict(sorted(partitions.items()))}
    payload["digest"] = digest(payload)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def load_frozen(corpus: Corpus, path: Path) -> dict[str, str]:
    """Refuse a split made for another corpus version, altered, or leaking groups."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    claimed = data.pop("digest", None)
    if claimed != digest(data):
        raise ValidationError("frozen split was modified after freezing")
    if data["corpus_digest"] != corpus.digest:
        raise ValidationError("frozen split belongs to another corpus version")
    partitions = data["partitions"]
    if set(partitions) != set(corpus.groups) or not set(partitions.values()) <= set(PARTITIONS):
        raise ValidationError("frozen split does not cover exactly the corpus groups")
    return partitions
