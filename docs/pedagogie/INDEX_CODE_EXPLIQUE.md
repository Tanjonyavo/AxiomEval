# Index du code expliqué

Mesuré automatiquement par `tools/pedagogie/build.py` au commit `c7f5ad7`. Une ligne significative est une ligne non vide qui n'est pas un commentaire seul. Une ligne est « expliquée » si elle appartient à une plage commentée dans `docs/pedagogie/explications/`.

**Total : 77 fichiers, 5138 lignes, 4371 lignes significatives, 399 expliquées (9.1 %).**

| Fichier | Lignes | Significatives | Expliquées | Semaine | Volume PDF | Commit | Couverture |
|---|---:|---:|---:|---|---|---|---|
| `.github/workflows/ci.yml` | 27 | 24 | 0 | S04 | 02 | `c7f5ad7` | 0 % |
| `configs/agent.yaml` | 31 | 29 | 0 | S02 | 01 | `c7f5ad7` | 0 % |
| `configs/default.yaml` | 18 | 16 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `configs/releases/r1-baseline.yaml` | 13 | 11 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `configs/releases/r2-hardened.yaml` | 20 | 18 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `configs/releases/r3-degraded.yaml` | 13 | 11 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `configs/releases/r4-guarded.yaml` | 21 | 19 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `fixtures/corpus/orders.json` | 9 | 9 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `fixtures/corpus/policy.json` | 9 | 9 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `fixtures/corpus/split.json` | 35 | 35 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `fixtures/corpus/templates.json` | 74 | 74 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `fixtures/security/templates.json` | 33 | 33 | 0 | S07 | 03 | `c7f5ad7` | 0 % |
| `labs/comparaison_axm.py` | 261 | 227 | 0 | S05 | 02 | `c7f5ad7` | 0 % |
| `pyproject.toml` | 35 | 29 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/__init__.py` | 2 | 2 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/__main__.py` | 4 | 3 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/agent_config.py` | 88 | 81 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/agent_run.py` | 111 | 94 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/api/__init__.py` | 1 | 1 | 0 | S08 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/api/app.py` | 119 | 96 | 0 | S08 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/api/migrations/0001_init.sql` | 20 | 19 | 0 | S08 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/api/migrations/0002_verdicts.sql` | 12 | 11 | 0 | S08 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/api/store.py` | 157 | 132 | 0 | S08 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/cli.py` | 76 | 70 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/cli_corpus.py` | 150 | 130 | 0 | S04-S09 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/__init__.py` | 1 | 1 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/adapters.py` | 136 | 113 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/agent.py` | 73 | 68 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/knowledge.py` | 50 | 38 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/oracle.py` | 97 | 82 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/redaction.py` | 52 | 43 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/secure_tools.py` | 80 | 72 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/tools.py` | 43 | 37 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collect/trace.py` | 78 | 61 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/collection.py` | 120 | 105 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `src/axiomeval/config.py` | 83 | 69 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/corpus/__init__.py` | 1 | 1 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `src/axiomeval/corpus/evaluate.py` | 109 | 98 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `src/axiomeval/corpus/release.py` | 62 | 53 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `src/axiomeval/corpus/scenarios.py` | 148 | 130 | 0 | S03-S04 | 02 | `c7f5ad7` | 0 % |
| `src/axiomeval/corpus/splits.py` | 65 | 54 | 54 | S03-S04 | 02 | `c7f5ad7` | 100 % |
| `src/axiomeval/demo.py` | 37 | 30 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/errors.py` | 13 | 7 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/evaluators/__init__.py` | 0 | 0 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/evaluators/deterministic.py` | 46 | 41 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/ids.py` | 20 | 12 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/logging.py` | 16 | 12 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/ml/__init__.py` | 1 | 1 | 0 | S09 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/ml/baselines.py` | 236 | 189 | 0 | S09 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/ml/features.py` | 71 | 57 | 0 | S09 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/models/__init__.py` | 8 | 7 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/models/evidence.py` | 67 | 57 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/models/finding.py` | 12 | 10 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/models/run.py` | 21 | 17 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/models/scenario.py` | 17 | 13 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/models/target.py` | 19 | 15 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/models/validation.py` | 21 | 17 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/policies/__init__.py` | 0 | 0 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/policies/gate.py` | 29 | 22 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/policy/__init__.py` | 1 | 1 | 0 | S06 | 02 | `c7f5ad7` | 0 % |
| `src/axiomeval/policy/authz.py` | 191 | 162 | 162 | S06 | 02 | `c7f5ad7` | 100 % |
| `src/axiomeval/reporting/__init__.py` | 0 | 0 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/reporting/agent_reports.py` | 92 | 83 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/reporting/reports.py` | 51 | 42 | 0 | S01 | 01 | `c7f5ad7` | 0 % |
| `src/axiomeval/security/__init__.py` | 1 | 1 | 0 | S07 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/security/egress.py` | 70 | 57 | 57 | S07 | 03 | `c7f5ad7` | 100 % |
| `src/axiomeval/security/report.py` | 70 | 63 | 0 | S07 | 03 | `c7f5ad7` | 0 % |
| `src/axiomeval/stats/__init__.py` | 1 | 1 | 0 | S05 | 02 | `c7f5ad7` | 0 % |
| `src/axiomeval/stats/paired.py` | 150 | 126 | 126 | S05 | 02 | `c7f5ad7` | 100 % |
| `tests/test_agent_p02.py` | 219 | 185 | 0 | S02-S03 | 01 | `c7f5ad7` | 0 % |
| `tests/test_api_s08.py` | 190 | 158 | 0 | S08 | 03 | `c7f5ad7` | 0 % |
| `tests/test_comparaison_axm.py` | 77 | 67 | 0 | S05 | 02 | `c7f5ad7` | 0 % |
| `tests/test_corpus_p03_p04.py` | 216 | 180 | 0 | S04-S05 | 02 | `c7f5ad7` | 0 % |
| `tests/test_ml_s09.py` | 95 | 75 | 0 | S09 | 03 | `c7f5ad7` | 0 % |
| `tests/test_policy_s06.py` | 116 | 92 | 0 | S06 | 02 | `c7f5ad7` | 0 % |
| `tests/test_security_s07.py` | 140 | 119 | 0 | S07 | 03 | `c7f5ad7` | 0 % |
| `tests/test_week1.py` | 287 | 244 | 0 | S01 | 01 | `c7f5ad7` | 0 % |

## Fichiers incomplets (70)

- `.github/workflows/ci.yml`
- `configs/agent.yaml`
- `configs/default.yaml`
- `configs/releases/r1-baseline.yaml`
- `configs/releases/r2-hardened.yaml`
- `configs/releases/r3-degraded.yaml`
- `configs/releases/r4-guarded.yaml`
- `fixtures/corpus/orders.json`
- `fixtures/corpus/policy.json`
- `fixtures/corpus/split.json`
- `fixtures/corpus/templates.json`
- `fixtures/security/templates.json`
- `labs/comparaison_axm.py`
- `pyproject.toml`
- `src/axiomeval/__init__.py`
- `src/axiomeval/__main__.py`
- `src/axiomeval/agent_config.py`
- `src/axiomeval/agent_run.py`
- `src/axiomeval/api/__init__.py`
- `src/axiomeval/api/app.py`
- `src/axiomeval/api/migrations/0001_init.sql`
- `src/axiomeval/api/migrations/0002_verdicts.sql`
- `src/axiomeval/api/store.py`
- `src/axiomeval/cli.py`
- `src/axiomeval/cli_corpus.py`
- `src/axiomeval/collect/__init__.py`
- `src/axiomeval/collect/adapters.py`
- `src/axiomeval/collect/agent.py`
- `src/axiomeval/collect/knowledge.py`
- `src/axiomeval/collect/oracle.py`
- `src/axiomeval/collect/redaction.py`
- `src/axiomeval/collect/secure_tools.py`
- `src/axiomeval/collect/tools.py`
- `src/axiomeval/collect/trace.py`
- `src/axiomeval/collection.py`
- `src/axiomeval/config.py`
- `src/axiomeval/corpus/__init__.py`
- `src/axiomeval/corpus/evaluate.py`
- `src/axiomeval/corpus/release.py`
- `src/axiomeval/corpus/scenarios.py`
- `src/axiomeval/demo.py`
- `src/axiomeval/errors.py`
- `src/axiomeval/evaluators/deterministic.py`
- `src/axiomeval/ids.py`
- `src/axiomeval/logging.py`
- `src/axiomeval/ml/__init__.py`
- `src/axiomeval/ml/baselines.py`
- `src/axiomeval/ml/features.py`
- `src/axiomeval/models/__init__.py`
- `src/axiomeval/models/evidence.py`
- `src/axiomeval/models/finding.py`
- `src/axiomeval/models/run.py`
- `src/axiomeval/models/scenario.py`
- `src/axiomeval/models/target.py`
- `src/axiomeval/models/validation.py`
- `src/axiomeval/policies/gate.py`
- `src/axiomeval/policy/__init__.py`
- `src/axiomeval/reporting/agent_reports.py`
- `src/axiomeval/reporting/reports.py`
- `src/axiomeval/security/__init__.py`
- `src/axiomeval/security/report.py`
- `src/axiomeval/stats/__init__.py`
- `tests/test_agent_p02.py`
- `tests/test_api_s08.py`
- `tests/test_comparaison_axm.py`
- `tests/test_corpus_p03_p04.py`
- `tests/test_ml_s09.py`
- `tests/test_policy_s06.py`
- `tests/test_security_s07.py`
- `tests/test_week1.py`
