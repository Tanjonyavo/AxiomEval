"""Canonical identities are reproducible; run identifiers remain unique."""
import hashlib
import json
from uuid import uuid4


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(prefix: str, value: object) -> str:
    return f"{prefix}-{digest(value)}"


def new_run_id() -> str:
    return f"RUN-{uuid4()}"
