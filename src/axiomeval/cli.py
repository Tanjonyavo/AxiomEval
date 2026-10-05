"""Parse arguments, compose modules, and report expected errors."""
import argparse
import json
import sys
from pathlib import Path

from axiomeval import __version__
from axiomeval.config import load_config
from axiomeval.demo import CASES, run_demo
from axiomeval.errors import AxiomEvalError
from axiomeval.logging import configure_logging
from axiomeval.policies.gate import Verdict
from axiomeval.reporting.reports import write_reports

EXIT_CODES = {Verdict.PROMOTE: 0, Verdict.REJECT: 10, Verdict.INCOMPLETE: 11, Verdict.HOLD: 12}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="axiomeval", description="AxiomEval — synthetic week-1 lab")
    parser.add_argument("--version", action="version", version=f"AxiomEval {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check-config", help="Validate the local YAML configuration")
    check.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    demo = commands.add_parser("demo", help="Run a synthetic fixture; no real agent or tool")
    demo.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    demo.add_argument("--case", choices=CASES, default="safe")
    demo.add_argument("--output", type=Path, default=Path("reports/generated"))
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        configure_logging(config.log_level)
        if args.command == "check-config":
            print(json.dumps({"project": "AxiomEval", "configuration": "valid", "synthetic_only": True}))
            return 0
        result = run_demo(config, args.case)
        json_path, html_path = write_reports(config, result, args.output)
        print(json.dumps({"case": result.case, "verdict": result.decision.verdict,
                          "synthetic": True, "json": str(json_path), "html": str(html_path)}))
        return EXIT_CODES[result.decision.verdict]
    except AxiomEvalError as exc:
        print(f"AxiomEval: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("AxiomEval: unable to write report files", file=sys.stderr)
        return 2
