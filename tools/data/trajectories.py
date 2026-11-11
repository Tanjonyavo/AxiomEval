"""Measure trajectory lengths in run files: events and model calls per run, by family.

Usage: python tools/data/trajectories.py data/runs/v3/*.jsonl --multi statut_double,... --out reports/s10/lengths.json
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def summarize(records, multi):
    by_family = defaultdict(list)
    for r in records:
        calls = sum(e["kind"] == "model_call" for e in r["trace"])
        by_family[r["family"]].append((len(r["trace"]), calls))

    def stats(rows):
        calls = Counter(c for _, c in rows)
        return {"runs": len(rows), "mean_events": round(sum(e for e, _ in rows) / len(rows), 2),
                "mean_model_calls": round(sum(c for _, c in rows) / len(rows), 2),
                "model_calls": {str(k): v for k, v in sorted(calls.items())},
                "share_two_or_more_calls": round(sum(v for k, v in calls.items() if k >= 2) / len(rows), 3),
                "share_three_or_more_calls": round(sum(v for k, v in calls.items() if k >= 3) / len(rows), 3)}

    multi_rows = [x for f, rows in by_family.items() if f in multi for x in rows]
    other_rows = [x for f, rows in by_family.items() if f not in multi for x in rows]
    return {"all": stats(multi_rows + other_rows), "multi_step": stats(multi_rows) if multi_rows else None,
            "other": stats(other_rows) if other_rows else None,
            "by_family": {f: stats(rows) for f, rows in sorted(by_family.items())}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--multi", default="", help="comma-separated multi-step families")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    multi = set(filter(None, args.multi.split(",")))
    report = {}
    for path in args.runs:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        report[path.name] = summarize(records, multi)
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({k: {p: v[p] and {x: v[p][x] for x in ("runs", "mean_model_calls", "share_two_or_more_calls",
                                                            "share_three_or_more_calls")}
                          for p in ("all", "multi_step", "other")} for k, v in report.items()}, indent=1))


if __name__ == "__main__":
    main()
