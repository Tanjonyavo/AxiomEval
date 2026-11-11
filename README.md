# AxiomEval

AxiomEval decides whether a new version of an AI agent may replace the current one. It runs a real local model on a grouped scenario corpus, records every step in a redacted, hash-chained trace, blocks unauthorized tool calls outside the model, and compares two releases group by group with a statistical bound. The verdict is one of `PROMOTE`, `HOLD`, `INCOMPLETE` or `REJECT`.

Everything below was measured on real runs of `qwen2.5:1.5b-instruct` through a local Ollama server. Nothing leaves the machine. The software is a research prototype, not a production system.

## What works today

| Area | Status | Where |
|---|---|---|
| Domain models, configuration, verdict policy | Implemented and tested | `src/axiomeval/models`, `policies` |
| Real local agent with RAG, tools, redacted hash-chained traces | Implemented and tested | `src/axiomeval/collect` |
| Grouped corpora with frozen splits and versioned releases (v1: 27 groups, v2: 180, v3: 245) | Implemented and tested | `fixtures/`, `configs/releases/` |
| Paired release comparison per group (Hoeffding bound, Clopper-Pearson for zero events) | Implemented and tested | `src/axiomeval/stats` |
| Authorization outside the model (roles, tenants, ownership, refunds bound to what the user asked) | Implemented and tested | `src/axiomeval/policy`, `collect/secure_tools.py` |
| Egress guard, security regression corpus, findings F-001 to F-008 with real retests | Implemented and tested | `src/axiomeval/security`, [findings](docs/security/FINDINGS.md) |
| Local REST API with SQLite persistence and migrations | Implemented and tested | `src/axiomeval/api` |
| Baselines that predict failing runs from trajectory prefixes | Implemented and tested | `src/axiomeval/ml`, [report](docs/experiments/S09_BASELINES_V2.md) |
| Event-sequence models (pooled logistic vs GRU) at horizon k | Implemented and tested; hypothesis not supported | [report](docs/experiments/S10_SEQUENCES_V3.md) |
| Releases r8a and r8b (read before write, guided refusals) | Code and replay tests only; real collection not finished | [mission state](docs/progression/ETAT_MISSION.md) |
| Weeks S11 to S24 of the plan (transformer, calibration, transfer, …) | Not started | [audit](docs/audit/AUDIT_INITIAL_S24.md) |

## Main real results

- **Corpus v2, r5 to r6:** `HOLD`, the first non-rejected verdict, with 0 breaches in 1,080 runs. A human review of the blocked attempts is still required.
- **Corpus v3, 1,470 runs per release:** breaches fell from 62 (r1) to 40 (r6), then to 6 (r7).
- **Verdict r6 to r7: `REJECT`.** The new write checks stopped the refund breaches, but they also blocked legitimate conditional refunds (18/36 to 0/36).
- **Sequence models (S10):** the GRU beats the pooled baseline at horizon 2 (Brier 0.103 vs 0.129). It keeps the same gain when event order is shuffled, so order is not what helps.

Protocol, definitions and where to check each number: [RESULTATS.md](RESULTATS.md) (in French). The raw runs (`data/runs/`) stay local. Their SHA-256 digests are in `data/MANIFEST*.json`, and the comparison reports are in `reports/`.

## Installation

Requirements: Python 3.12 or newer, and Git. PyYAML is the only required dependency. The extras add the API (`api`), the baselines (`ml`) and the sequence models (`seq`, which needs PyTorch).

```powershell
git clone https://github.com/Tanjonyavo/AxiomEval.git
Set-Location AxiomEval
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[api,ml,seq]"
.\.venv\Scripts\python.exe -m axiomeval --help
```

On Linux or macOS, use `python3` to create the environment and `.venv/bin/python` afterwards.

To run against a real model, install [Ollama](https://ollama.com), start `ollama serve`, then run `ollama pull qwen2.5:1.5b-instruct`. The adapter refuses any address other than `localhost`.

## Commands

| Command | Purpose |
|---|---|
| `check-config`, `demo --case safe\|violation\|missing\|uncertain` | Validate the configuration; run the four synthetic verdict cases |
| `run-agent --config configs/agent.yaml` | Run the real agent on the frozen support tasks |
| `corpus` | Validate a corpus, freeze its split, write its data card |
| `collect --corpus-dir fixtures/corpus-v3 --release configs/releases/r7-checked.yaml --out data/runs/v3/r7.jsonl` | Run a release on a corpus. The command resumes and skips runs already recorded. |
| `compare --baseline A.jsonl --candidate B.jsonl` | Give a paired release verdict, on business success and on security |
| `security-report` | Report results by attack family across releases |
| `ml-baselines`, `ml-sequence` | Train and evaluate the predictors (S09, S10) |
| `serve` | Start the local REST API (token in `AXIOMEVAL_API_TOKEN`) |

Run `python -m axiomeval <command> --help` for every option. Exit codes 10, 11 and 12 mean `REJECT`, `INCOMPLETE` and `HOLD`, and 2 means an error.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

166 tests pass. One live test is skipped unless `AXIOMEVAL_LIVE=1` is set. The tests replay scripted model answers to check the harness, including real traces that once caused breaches. Scientific conclusions come only from real collections. CI runs the suite on Python 3.12 and 3.13.

## Documentation

- **Start here:** [`docs/pedagogie/PDF/AxiomEval_Tout_En_Un.pdf`](docs/pedagogie/PDF/AxiomEval_Tout_En_Un.pdf). It gathers the complete guide, the manuals and the code explained line by line, in French.
- Security: [threat model](docs/security/THREAT_MODEL.md), [findings F-001 to F-008](docs/security/FINDINGS.md).
- Data cards: [v1](docs/data/DATA_CARD.md), [v2](docs/data/DATA_CARD_V2.md), [v3](docs/data/DATA_CARD_V3.md), [security corpus](docs/data/DATA_CARD_SECURITY.md).
- Design: [architecture](docs/architecture.md), [decisions](docs/decisions.md).
- Progress: [final report](docs/progression/RAPPORT_FINAL_S24.md), [exact resume point](docs/progression/ETAT_MISSION.md).

## Limitations

- One small local model, French support scenarios and synthetic orders: the results describe these runs only.
- Fingerprints prove that local content is consistent. They do not authenticate who wrote it.
- Redaction covers the planted canaries and common patterns (email, API key, bearer token, card number), not every kind of personal data.
- A `PROMOTE` is a recommendation for the tested scope only. It never deploys anything.
