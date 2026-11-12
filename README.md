# AxiomEval

AxiomEval decides whether a new version of an AI agent may replace the current one. It runs a real local model on a grouped scenario corpus, records every step in a redacted, hash-chained trace, blocks unauthorized tool calls outside the model, and compares two releases group by group with a statistical bound. The verdict is one of `PROMOTE`, `HOLD`, `INCOMPLETE` or `REJECT`.

The recorded experiments ran locally with `qwen2.5:1.5b-instruct` through Ollama and used fictional orders. AxiomEval is a local research prototype.

## What works today

| Area | Status | Where |
|---|---|---|
| Domain models, configuration, verdict policy | Implemented and tested | `src/axiomeval/models`, `policies` |
| Real local agent with RAG, tools, redacted hash-chained traces | Implemented and tested | `src/axiomeval/collect` |
| Grouped corpora with frozen splits and versioned releases (v1: 27 groups, v2: 180, v3: 245) | Implemented and tested | `fixtures/`, `configs/releases/` |
| Paired release comparison under a frozen plan (group-level Hoeffding bound) | Implemented and tested | `src/axiomeval/stats` |
| Authorization outside the model (roles, tenants, ownership, refunds bound to what the user asked) | Implemented and tested | `src/axiomeval/policy`, `collect/secure_tools.py` |
| Egress guard, security regression corpus, findings F-001 to F-008 with real retests | Implemented and tested | `src/axiomeval/security`, [findings](docs/security/FINDINGS.md) |
| Local REST API with SQLite persistence and migrations | Implemented and tested | `src/axiomeval/api` |
| Baselines that predict failing runs from trajectory prefixes | Implemented and tested | `src/axiomeval/ml`, [report](docs/experiments/S09_BASELINES_V2.md) |
| Event-sequence models (pooled logistic vs GRU) at horizon k | Implemented and tested; hypothesis not supported | [report](docs/experiments/S10_SEQUENCES_V3.md) |
| Releases r8a and r8b (read before write, guided refusals) | Code and replay tests only; real collection not finished | [mission state](docs/progression/ETAT_MISSION.md) |
| Conditional refunds and authorized review handoffs (r10 and r11) | Local behavioral validation | [results](RESULTATS.md#validation-du-parcours-de-remboursement) |
| Weeks S11 to S24 of the 32-week research plan (transformer, calibration, transfer, …) | Not started | [audit](docs/audit/AUDIT_INITIAL_S24.md) |

## Main real results

- **Corpus v2, r5 to r6:** `HOLD`, the first non-rejected verdict, with 0 breaches in 1,080 runs. A human review of the blocked attempts is still required.
- **Corpus v3, 1,470 runs per release:** breaches fell from 62 (r1) to 40 (r6), then to 6 (r7).
- **Verdict r6 to r7: `REJECT`.** The write checks stopped refunds above the order total. Six breaches remained. Conditional-refund business successes fell from 18/36 to 0/36, and exact ledger effects from 28/36 to 10/36.
- **Refund review, r10 to r11:** all six planned behavioral checks passed on 24 new scenarios, with 12/12 review handoffs and 44/48 business successes for r11. The frozen release verdict remains `HOLD`.
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
| `freeze-comparison` | Bind the two releases, installed model digests, environment, protocol and expected runs before collection. |
| `plan-size --margin 0.10` | Compute a conservative business-test sample size in independent paired units. |
| `compare --baseline A.jsonl --candidate B.jsonl` | Give a paired release verdict, on business success and on security |
| `security-report` | Report results by attack family across releases |
| `ml-baselines`, `ml-sequence` | Train and evaluate the predictors (S09, S10) |
| `serve` | Start the local REST API (token in `AXIOMEVAL_API_TOKEN`) |

Run `python -m axiomeval <command> --help` for every option. Exit codes 10, 11 and 12 mean `REJECT`, `INCOMPLETE` and `HOLD`, and 2 means an error.

For a new comparison, set the margin in [configs/comparison.yaml](configs/comparison.yaml). Run `freeze-comparison` with the planned corpus, draws and partitions, `--baseline-release` and `--candidate-release`, and `--baseline-model-digest` and `--candidate-model-digest` for the installed models. Pass the resulting file as `--comparison-plan` and the same protocol file as `--comparison-config` to both collections and to `compare`. Each run records the plan's SHA-256. Changes to the protocol invalidate the plan. Treat new collections without a plan as exploratory. Historical reports can be replayed with the original `compare` command.

The cost is the failure rate. Positive candidate-minus-baseline cost means the candidate fails more often. Non-inferiority requires the one-sided Hoeffding upper bound to fall strictly below the margin. The bound is conservative for independent groups. The bootstrap interval is an approximate diagnostic. For attack-labeled runs, the security report uses a separate Hoeffding upper bound with fixed run weights and independent template families. Simulated cases verify the software and are labeled separately from recorded results.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

The tests replay scripted model answers and check the collector, frozen plan, comparison, authorization and API. The live test requires a running local model server and `AXIOMEVAL_LIVE=1`. The sequence-model test requires the `seq` extra. CI runs the suite on Python 3.12 and 3.13.

## Documentation

- **Start here:** [RESULTATS.md](RESULTATS.md), the protocol and the verifiable numbers.
- Security: [threat model](docs/security/THREAT_MODEL.md), [findings F-001 to F-008](docs/security/FINDINGS.md).
- Data cards: [v1](docs/data/DATA_CARD.md), [v2](docs/data/DATA_CARD_V2.md), [v3](docs/data/DATA_CARD_V3.md), [security corpus](docs/data/DATA_CARD_SECURITY.md).
- Design: [architecture](docs/architecture.md), [decisions](docs/decisions.md).
- Progress: [final report](docs/progression/RAPPORT_FINAL_S24.md), [exact resume point](docs/progression/ETAT_MISSION.md).

## Limitations

- One small local model, French support scenarios and synthetic orders: the results describe these runs only.
- Fingerprints prove that local content is consistent. They do not authenticate who wrote it.
- Redaction covers the planted canaries and common patterns (email, API key, bearer token, card number), not every kind of personal data.
- A `PROMOTE` is a recommendation for the tested scope only. It never deploys anything.
