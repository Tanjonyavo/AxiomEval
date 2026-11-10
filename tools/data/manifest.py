"""Write the digests of local run files (the runs stay local; their fingerprints are versioned).

Usage: python tools/data/manifest.py data/runs/v2 data/MANIFEST_V2.json
"""
import hashlib
import json
import sys
from pathlib import Path


def describe(path: Path) -> dict:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    first = records[0] if records else {}
    return {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "runs": len(records),
            "release_id": first.get("release_id"), "release_digest": first.get("release_digest"),
            "evaluator": first.get("evaluator"), "corpus_version": first.get("corpus_version"),
            "corpus_digest": first.get("corpus_digest"), "groups": len({r["group_id"] for r in records}),
            "started_first": min((r["started_at"] for r in records), default=None),
            "started_last": max((r["started_at"] for r in records), default=None)}


def main(directory: str, out: str) -> None:
    files = [describe(p) for p in sorted(Path(directory).glob("*.jsonl"))]
    payload = {"description": "Empreintes des collectes réelles (fichiers locaux, non publiés)", "files": files}
    Path(out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({f["file"]: f["runs"] for f in files}))


if __name__ == "__main__":
    main(*sys.argv[1:3])
