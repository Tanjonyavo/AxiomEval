"""CLI commands for the grouped corpus, real collection and release comparison."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

from axiomeval.errors import AxiomEvalError

CORPUS_DIR = Path("fixtures/corpus")
CANARIES = ("AXM-CANARY-7F3A91C2E5", "CANARY_SYSPROMPT_51F0C2")


def register(commands) -> None:
    corpus = commands.add_parser("corpus", help="Validate the grouped corpus, freeze its split, write the data card")
    corpus.add_argument("--corpus-dir", type=Path, default=CORPUS_DIR)
    corpus.add_argument("--card", type=Path, default=Path("docs/data/DATA_CARD.md"))
    corpus.add_argument("--seed", type=int, default=20261110)
    corpus.add_argument("--test-only", action="store_true", help="Put every group in the test partition")
    collect = commands.add_parser("collect", help="Run a release on the corpus and append real trajectories")
    collect.add_argument("--corpus-dir", type=Path, default=CORPUS_DIR)
    collect.add_argument("--release", type=Path, required=True)
    collect.add_argument("--out", type=Path, required=True)
    collect.add_argument("--draws", type=int, default=1)
    collect.add_argument("--partitions", nargs="*", default=None)
    collect.add_argument("--limit", type=int, default=None)
    compare = commands.add_parser("compare", help="Paired release verdict (business + security)")
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--candidate", type=Path, required=True)
    compare.add_argument("--margin", type=float, default=0.10)
    compare.add_argument("--alpha", type=float, default=0.05)
    compare.add_argument("--min-groups", type=int, default=10)
    compare.add_argument("--partitions", nargs="*", default=None)
    sec = commands.add_parser("security-report", help="Security report by attack family across releases")
    sec.add_argument("--runs", type=Path, nargs="+", required=True)
    sec.add_argument("--out", type=Path, required=True)
    ml = commands.add_parser("ml-baselines", help="S9 baselines on trajectory prefixes (task B)")
    ml.add_argument("--runs", type=Path, nargs="+", required=True)
    ml.add_argument("--out", type=Path, required=True)
    serve = commands.add_parser("serve", help="Local REST API (token in AXIOMEVAL_API_TOKEN)")
    serve.add_argument("--db", type=Path, default=Path("data/axiomeval.db"))
    serve.add_argument("--port", type=int, default=8765)


def dispatch(args, exit_codes) -> int | None:
    handlers = {"corpus": _corpus, "collect": _collect, "compare": _compare, "security-report": _security,
                "serve": _serve, "ml-baselines": _ml}
    if args.command not in handlers:
        return None
    try:
        return handlers[args.command](args, exit_codes)
    except AxiomEvalError as exc:
        print(f"AxiomEval: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"AxiomEval: file error ({type(exc).__name__})", file=sys.stderr)
        return 2


def _corpus(args, _codes) -> int:
    from axiomeval.corpus.scenarios import data_card, load_corpus
    from axiomeval.corpus.splits import assign, freeze, load_frozen
    corpus = load_corpus(args.corpus_dir / "templates.json")
    split = args.corpus_dir / "split.json"
    if split.exists():
        partitions = load_frozen(corpus, split)
        status = "verified"
    else:
        ratios = {"train": 0.0, "validation": 0.0, "calibration": 0.0, "test": 1.0} if args.test_only else None
        partitions = assign(corpus, args.seed, ratios)
        freeze(corpus, partitions, args.seed, split)
        status = "frozen"
    args.card.parent.mkdir(parents=True, exist_ok=True)
    args.card.write_text(data_card(corpus, partitions), encoding="utf-8")
    print(json.dumps({"corpus": corpus.corpus_id, "digest": corpus.digest, "groups": len(corpus.groups),
                      "scenarios": len(corpus.scenarios), "split": status}))
    return 0


def _collect(args, _codes) -> int:
    from axiomeval.collection import collect
    from axiomeval.corpus.release import load_release
    from axiomeval.corpus.scenarios import load_corpus
    from axiomeval.corpus.splits import load_frozen
    from axiomeval.policy.authz import load_policy
    base = args.corpus_dir
    corpus = load_corpus(base / "templates.json")
    partitions = load_frozen(corpus, base / "split.json")
    orders = json.loads((base / "orders.json").read_text(encoding="utf-8"))
    result = collect(load_release(args.release), corpus, partitions, load_policy(base / "policy.json"),
                     base / "kb", orders, CANARIES, args.out, args.draws,
                     tuple(args.partitions) if args.partitions else None, limit=args.limit)
    print(json.dumps(result))
    return 0


def _ml(args, _codes) -> int:
    from axiomeval.collection import load_records
    from axiomeval.ml.baselines import experiment, write_report
    from axiomeval.ml.features import to_example
    examples = [to_example(r) for path in args.runs for r in load_records(path)]
    report = experiment(examples, list(args.runs))
    write_report(report, args.out)
    summary = {seed: {m: {k: v.get(k) for k in ("pr_auc", "brier")} for m, v in res["models"].items()}
               for seed, res in report["frozen_split"].items()}
    print(json.dumps(summary, indent=1))
    return 0


def _serve(args, _codes) -> int:
    import os

    import uvicorn

    from axiomeval.api.app import create_app
    from axiomeval.api.store import Store
    if not os.environ.get("AXIOMEVAL_API_TOKEN"):
        print("AxiomEval: set AXIOMEVAL_API_TOKEN before starting the API", file=sys.stderr)
        return 2
    args.db.parent.mkdir(parents=True, exist_ok=True)
    store = Store(args.db, CANARIES)
    store.migrate()
    uvicorn.run(create_app(store), host="127.0.0.1", port=args.port, log_level="info")  # localhost only
    return 0


def _security(args, _codes) -> int:
    from axiomeval.collection import load_records
    from axiomeval.security.report import family_table, markdown
    reports = {}
    for path in args.runs:
        records = load_records(path)
        reports[records[0]["release_id"] if records else path.stem] = records
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown(reports), encoding="utf-8")
    print(json.dumps({name: family_table(recs) for name, recs in reports.items()}, ensure_ascii=False))
    return 0


def _compare(args, codes) -> int:
    from axiomeval.collection import load_records
    from axiomeval.stats.paired import Protocol, release_verdict
    base, cand = load_records(args.baseline), load_records(args.candidate)
    if args.partitions:
        base = [r for r in base if r["partition"] in args.partitions]
        cand = [r for r in cand if r["partition"] in args.partitions]
    result = release_verdict(base, cand, Protocol(args.alpha, args.margin, args.min_groups))
    print(json.dumps({"verdict": result.verdict, "reasons": result.reasons,
                      "paired": asdict(result.paired) if result.paired else None,
                      "security": result.security}, ensure_ascii=False, indent=2))
    return codes[result.verdict]
