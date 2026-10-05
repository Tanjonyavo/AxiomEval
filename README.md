# AxiomEval

Python prototype for building reproducible evaluations of AI systems: structured observations, deterministic controls, explainable decisions, and JSON/HTML reports.

## Current Status

The Week 1 foundation is executable locally. It validates a configuration, links a target and a scenario to a run, verifies evidence, detects a forbidden tool, and produces a verdict.

**All four demonstrations use synthetic observations.** No AI model or business tool is actually executed. This version is intended to validate the architecture and control rules; it is not production-ready.

## Installation

Requirements: **Python 3.12 or newer** and Git. PyYAML is the only runtime dependency. No GPU or API key is required.

From PowerShell:

```powershell
git clone https://github.com/Tanjonyavo/AxiomEval.git
Set-Location AxiomEval
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m axiomeval --version
```

On Linux or macOS, use `python3` to create the environment and `.venv/bin/python` for the following commands. Run the examples from the repository root.

## Demonstrations

```powershell
.\.venv\Scripts\python.exe -m axiomeval check-config
.\.venv\Scripts\python.exe -m axiomeval demo --case safe
.\.venv\Scripts\python.exe -m axiomeval demo --case violation
.\.venv\Scripts\python.exe -m axiomeval demo --case missing
.\.venv\Scripts\python.exe -m axiomeval demo --case uncertain
```

With the default configuration:

| Case | Verdict | Exit Code | Meaning |
|---|---|---:|---|
| `safe` | `PROMOTE` | 0 | The configured control is satisfied. |
| `violation` | `REJECT` | 10 | A forbidden tool was observed unambiguously. |
| `missing` | `INCOMPLETE` | 11 | Required evidence is missing. |
| `uncertain` | `HOLD` | 12 | The observation requires review. |
| Configuration or write error | Error | 2 | The command cannot complete the requested work. |

Exit codes 10, 11, and 12 are expected control outcomes. `PROMOTE` remains a recommendation limited to the tested scope and does not trigger any deployment.

Each run writes `report.json` and `report.html` to a separate directory under `reports/generated/`. The paths are displayed in the terminal. Open the HTML file in a browser to review the result.

Available options include `--config configs/default.yaml`, `--output reports/generated`, and `--help`. The installed `axiomeval` command uses the same entry point as `python -m axiomeval`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The 21 tests cover configuration, identifiers, verdicts, missing/tampered/stale/mislinked evidence, duplicates, HTML rendering, and the CLI. See the [validation results and limitations](docs/semaine-01/validation.md).

## Architecture

```text
Configuration → Target + Scenario → Run + Evidence
                                      ↓
                           Deterministic Evaluation
                                      ↓
                           Decision and Reasons
                                      ↓
                               JSON + HTML
```

The `src/axiomeval/` package separates domain models, evaluation logic, decision policy, reporting, and the CLI. Domain models remain independent of input/output concerns.

- [Architecture and Contracts](docs/architecture.md)
- [Design Decisions and Alternatives](docs/decisions.md)

## Limitations

Fingerprints verify local content consistency; they do not authenticate the author of the content. Tool observations in this version do not yet represent temporal trajectories. Learned models, statistical measurements, and production-grade access controls still need to be developed.

Use synthetic data: reports include scenario parameters, and this version does not yet perform sensitive-data removal.
