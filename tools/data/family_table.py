"""Per-family table for several releases on the same corpus: success, breaches, executed refunds.

A global success rate can hide a family that collapses (r7: legitimate conditional refunds 18/36 -> 0/36
while the global rate barely moved). Publish this table with every verdict.

Usage: python tools/data/family_table.py data/runs/v3/r6-bound.jsonl data/runs/v3/r7-checked.jsonl \
           [--families a,b,...] [--out reports/s05/v3_families.md] [--json reports/s05/v3_families.json]
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def table(runs: dict[str, list[dict]], families: list[str] | None = None) -> dict:
    out: dict = {}
    for release, records in runs.items():
        per = defaultdict(lambda: {"runs": 0, "success": 0, "breach_runs": 0, "refunds": 0})
        for r in records:
            row = per[r["family"]]
            row["runs"] += 1
            row["success"] += r["business"] == "SUCCESS"
            row["breach_runs"] += bool(r["security"]["breaches"])
            row["refunds"] += len(r["refunds"])
        out[release] = dict(per)
    names = families or sorted({f for per in out.values() for f in per})
    return {"releases": list(runs), "families": names, "rows": out}


def markdown(result: dict) -> str:
    releases = result["releases"]
    head = "| Famille | " + " | ".join(f"{r} succès | {r} brèches" for r in releases) + " |"
    lines = [head, "|---|" + "---|---|" * len(releases)]
    for family in result["families"]:
        cells = []
        for release in releases:
            row = result["rows"][release].get(family)
            cells += [f"{row['success']}/{row['runs']}", str(row["breach_runs"])] if row else ["—", "—"]
        lines.append(f"| {family} | " + " | ".join(cells) + " |")
    totals = []
    for release in releases:
        rows = result["rows"][release].values()
        runs = sum(r["runs"] for r in rows)
        totals += [f"{sum(r['success'] for r in rows)}/{runs}", str(sum(r["breach_runs"] for r in rows))]
    lines.append("| **Total, toutes familles** | " + " | ".join(totals) + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--families", default="", help="comma-separated subset, in this order")
    parser.add_argument("--out", type=Path, help="Markdown table")
    parser.add_argument("--json", type=Path, help="JSON counts")
    args = parser.parse_args()
    runs = {p.stem: load(p) for p in args.runs}
    corpora = {r.get("corpus_digest") for records in runs.values() for r in records}
    if len(corpora) > 1:
        raise SystemExit("run files come from different corpora; a family table would compare different scenarios")
    result = table(runs, [f for f in args.families.split(",") if f] or None)
    text = markdown(result)
    for path, content in ((args.out, text), (args.json, json.dumps(result, ensure_ascii=False, indent=1) + "\n")):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
