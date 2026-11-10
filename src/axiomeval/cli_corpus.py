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
    corpus.add_argument("--templates", type=Path, default=CORPUS_DIR / "templates.json")
    corpus.add_argument("--split", type=Path, default=CORPUS_DIR / "split.json")
    corpus.add_argument("--card", type=Path, default=Path("docs/data/DATA_CARD.md"))
    corpus.add_argument("--seed", type=int, default=20261110)
    collect = commands.add_parser("collect", help="Run a release on the corpus and append real trajectories")
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


def dispatch(args, exit_codes) -> int | None:
    handlers = {"corpus": _corpus, "collect": _collect, "compare": _compare}
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
    corpus = load_corpus(args.templates)
    if args.split.exists():
        partitions = load_frozen(corpus, args.split)
        status = "verified"
    else:
        partitions = assign(corpus, args.seed)
        freeze(corpus, partitions, args.seed, args.split)
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
    corpus = load_corpus(CORPUS_DIR / "templates.json")
    partitions = load_frozen(corpus, CORPUS_DIR / "split.json")
    orders = json.loads((CORPUS_DIR / "orders.json").read_text(encoding="utf-8"))
    result = collect(load_release(args.release), corpus, partitions, load_policy(CORPUS_DIR / "policy.json"),
                     CORPUS_DIR / "kb", orders, CANARIES, args.out, args.draws,
                     tuple(args.partitions) if args.partitions else None, limit=args.limit)
    print(json.dumps(result))
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
