"""CLI commands for the grouped corpus, real collection and release comparison."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

from axiomeval.errors import AxiomEvalError, ValidationError

CORPUS_DIR = Path("fixtures/corpus")
COMPARISON_CONFIG = Path("configs/comparison.yaml")
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
    collect.add_argument("--comparison-plan", type=Path)
    collect.add_argument("--comparison-config", type=Path, default=COMPARISON_CONFIG)
    freeze = commands.add_parser("freeze-comparison", help="Record a comparison plan before collecting runs")
    freeze.add_argument("--corpus-dir", type=Path, default=CORPUS_DIR)
    freeze.add_argument("--config", type=Path, default=COMPARISON_CONFIG)
    freeze.add_argument("--baseline-release", type=Path, required=True)
    freeze.add_argument("--candidate-release", type=Path, required=True)
    freeze.add_argument("--baseline-model-digest", required=True, help="SHA-256 of the installed reference model")
    freeze.add_argument("--candidate-model-digest", required=True, help="SHA-256 of the installed candidate model")
    freeze.add_argument("--out", type=Path, required=True)
    freeze.add_argument("--draws", type=int, default=1)
    freeze.add_argument("--partitions", nargs="+")
    compare = commands.add_parser("compare", help="Paired release verdict (business + security)")
    compare.add_argument("--baseline", type=Path, required=True)
    compare.add_argument("--candidate", type=Path, required=True)
    compare.add_argument("--margin", type=float)
    compare.add_argument("--alpha", type=float)
    compare.add_argument("--min-groups", type=int)
    compare.add_argument("--partitions", nargs="*", default=None)
    compare.add_argument("--comparison-plan", type=Path)
    compare.add_argument("--comparison-config", type=Path, default=COMPARISON_CONFIG)
    size = commands.add_parser("plan-size", help="Size a fixed paired non-inferiority study")
    size.add_argument("--margin", type=float, required=True)
    size.add_argument("--alpha", type=float, default=0.05)
    size.add_argument("--power", type=float, default=0.80)
    size.add_argument("--target-cost-difference", type=float, default=0.0,
                      help="Expected candidate-minus-baseline failure-rate difference")
    sec = commands.add_parser("security-report", help="Security report by attack family across releases")
    sec.add_argument("--runs", type=Path, nargs="+", required=True)
    sec.add_argument("--out", type=Path, required=True)
    ml = commands.add_parser("ml-baselines", help="S9 baselines on trajectory prefixes (task B)")
    ml.add_argument("--runs", type=Path, nargs="+", required=True)
    ml.add_argument("--out", type=Path, required=True)
    seq = commands.add_parser("ml-sequence", help="S10 event-sequence models at horizon k (needs the seq extra)")
    seq.add_argument("--runs", type=Path, nargs="+", required=True)
    seq.add_argument("--out", type=Path, required=True)
    seq.add_argument("--horizons", type=int, nargs="+", default=[1, 2, 3])
    serve = commands.add_parser("serve", help="Local REST API (token in AXIOMEVAL_API_TOKEN)")
    serve.add_argument("--db", type=Path, default=Path("data/axiomeval.db"))
    serve.add_argument("--port", type=int, default=8765)


def dispatch(args, exit_codes) -> int | None:
    handlers = {"corpus": _corpus, "collect": _collect, "compare": _compare, "freeze-comparison": _freeze_comparison,
                "security-report": _security, "plan-size": _plan_size,
                "serve": _serve, "ml-baselines": _ml, "ml-sequence": _seq}
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
    docs = None
    if (args.corpus_dir / "kb").is_dir():
        from axiomeval.collect.knowledge import load_documents
        docs = load_documents(args.corpus_dir / "kb")
    args.card.write_text(data_card(corpus, partitions, docs), encoding="utf-8")
    print(json.dumps({"corpus": corpus.corpus_id, "digest": corpus.digest, "groups": len(corpus.groups),
                      "scenarios": len(corpus.scenarios), "split": status}))
    return 0


def _load_design(base):
    from axiomeval.corpus.scenarios import load_corpus
    from axiomeval.corpus.splits import load_frozen
    corpus = load_corpus(base / "templates.json")
    return corpus, load_frozen(corpus, base / "split.json")


def _freeze_comparison(args, _codes) -> int:
    from axiomeval.collect.knowledge import load_documents
    from axiomeval.collection import EVALUATOR_VERSION, environment_digest
    from axiomeval.corpus.release import load_release
    from axiomeval.policy.authz import load_policy
    from axiomeval.stats.plan import BoundRelease, ComparisonEvidence, expected_runs, freeze_comparison, load_protocol

    base = args.corpus_dir
    corpus, partitions = _load_design(base)
    if args.partitions and not set(args.partitions) <= set(partitions.values()):
        raise ValidationError("comparison plan contains an unknown or empty partition")
    scenarios = [s for s in corpus.scenarios if not args.partitions or partitions[s.group_id] in args.partitions]
    selected_partitions = {s.group_id: partitions[s.group_id] for s in scenarios}
    environment = environment_digest(load_documents(base / "kb"), _load_orders(base),
                                     load_policy(base / "policy.json"), canaries=CANARIES)
    evidence = ComparisonEvidence(
        BoundRelease(load_release(args.baseline_release).digest, args.baseline_model_digest),
        BoundRelease(load_release(args.candidate_release).digest, args.candidate_model_digest),
        environment, EVALUATOR_VERSION,
    )
    fingerprint = freeze_comparison(args.out, load_protocol(args.config), corpus.digest,
                                    expected_runs(scenarios, args.draws), selected_partitions, evidence)
    print(json.dumps({"file": str(args.out), "sha256": fingerprint}))
    return 0


def _load_orders(base: Path) -> dict:
    try:
        return json.loads((base / "orders.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError("invalid corpus orders JSON") from exc


def _collect(args, _codes) -> int:
    from axiomeval.collection import collect
    from axiomeval.corpus.release import load_release
    from axiomeval.policy.authz import load_policy
    from axiomeval.stats.plan import load_comparison, load_protocol
    base = args.corpus_dir
    corpus, partitions = _load_design(base)
    plan = load_comparison(args.comparison_plan, load_protocol(args.comparison_config)) if args.comparison_plan else None
    result = collect(load_release(args.release), corpus, partitions, load_policy(base / "policy.json"),
                     base / "kb", _load_orders(base), CANARIES, args.out, args.draws,
                     tuple(args.partitions) if args.partitions else None, limit=args.limit, comparison_plan=plan)
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


def _seq(args, _codes) -> int:
    from axiomeval.collection import load_records
    from axiomeval.ml.baselines import files_digest, write_report
    from axiomeval.ml.sequence import experiment
    records = [r for path in args.runs for r in load_records(path)]
    report = experiment(records, tuple(args.horizons))
    report["manifest"]["dataset_digest"] = files_digest(list(args.runs))
    report["manifest"]["run_files"] = [str(p) for p in args.runs]
    write_report(report, args.out)
    summary = {k: {"population_runs": h["population_runs"], "test_groups": h["test_groups"],
                   **({m: {x: round(v[x], 3) for x in ("pr_auc", "brier") if x in v}
                       for m, v in h["seeds"]["0"].items() if m != "gru_minus_pooled"} if "seeds" in h
                      else {"skipped": h.get("skipped")})}
               for k, h in report["horizons"].items()}
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


def _plan_size(args, _codes) -> int:
    from axiomeval.stats.paired import hoeffding_sample_size

    n = hoeffding_sample_size(args.margin, args.alpha, args.power, args.target_cost_difference)
    print(json.dumps({"sufficient_independent_units": n, "alpha": args.alpha, "power": args.power,
                      "margin": args.margin, "target_cost_difference": args.target_cost_difference,
                      "assumptions": "fixed sample, independent equally weighted paired units, "
                                     "differences in [-1, 1], business test only"}, indent=2))
    return 0


def _compare(args, codes) -> int:
    from axiomeval.collection import load_records
    from axiomeval.stats.paired import Protocol, release_verdict
    from axiomeval.stats.plan import load_comparison, load_protocol
    overrides = {name: getattr(args, name) for name in ("alpha", "margin", "min_groups")
                 if getattr(args, name) is not None}
    if args.comparison_plan and (overrides or args.partitions is not None):
        raise ValidationError("margin, alpha, group count and partitions are frozen by the comparison plan")
    plan = load_comparison(args.comparison_plan, load_protocol(args.comparison_config)) if args.comparison_plan else None
    base, cand = load_records(args.baseline), load_records(args.candidate)
    if args.partitions:
        base = [r for r in base if r["partition"] in args.partitions]
        cand = [r for r in cand if r["partition"] in args.partitions]
    protocol = plan.protocol if plan else Protocol(**overrides)
    result = plan.verdict(base, cand) if plan else release_verdict(base, cand, protocol)
    print(json.dumps({"verdict": result.verdict, "reasons": result.reasons,
                      "paired": asdict(result.paired) if result.paired else None,
                      "security": result.security,
                      "protocol": asdict(protocol),
                      "comparison_plan_sha256": plan.sha256 if plan else None,
                      "methods": {"decision_bound": "conservative Hoeffding bound on independent groups",
                                  "bootstrap_interval": "approximate diagnostic by group",
                                  "security_bound": "weighted Hoeffding conditional on independent template families and fixed run weights",
                                  "simulation": "none used for the decision"}}, ensure_ascii=False, indent=2))
    return codes[result.verdict]
