# Audit initial avant la mission S07–S24

Date : 2026-11-10. Dépôt local `C:\Users\ramia\OneDrive\Bureau\AxiomEval` (aussi accessible par `Math IA\AxiomEval`, lien symbolique).

## 1. État Git de départ

| Élément | Valeur |
|---|---|
| Branche | `feat/s6-agent-reel` (suit `origin/feat/s6-agent-reel`) |
| Commit de départ | `459c357` chore: keep only project files in the repository |
| `main` local et distant | `459c357` |
| Identité Git | `tanjonyavo <ramiandrisoatanjonyavo@gmail.com>` |
| Modifications non commitées | aucune sur les fichiers suivis ; documents personnels ignorés (`docs/16`–`docs/18`, spécification, notes S1, guide S6) |
| Branches locales de sauvegarde | `backup/avant-reecriture`, `backup/avant-nettoyage`, `roadmap-18-et-tx01` |
| CI | aucun workflow (`.github/` absent) |

## 2. Référentiels comparés

- **Référence technique de cette mission** : spécification 32 semaines (`AxiomEval_Final_Specification_32S_Revenue_Max_Demand_Anchored(1).md`, 3 119 lignes) et sa roadmap hebdomadaire (`AxiomEval_Roadmap_32S_…md`, §4). Matrice d'exigences AE01–AE27 (§60), contrat de verdict (§38), DoD logiciel (§61) et ML (§62).
- **Roadmap pédagogique plus récente** (`docs/18 - Refonte AXM - Produit et recherche`, 132 semaines relatives, lots P01–P08, F01–F03, R1–R6). Non modifiée.
- **Constat important** : le « S6 » publié le 10 novembre correspond aux lots P01–P02 de la roadmap 18 (agent réel, traces, caviardage). Dans la spécification 32 semaines, ce travail correspond à **S2–S3**. Les semaines 32S **S4, S5 et S6** (manifest/CI/splits, verdict statistique, autorisation) ne sont pas réalisées et bloquent S7 et la suite.

## 3. Correspondance entre parcours

| Spéc. 32S | Contenu 32S | Roadmap 18 | Cours AXM principal |
|---|---|---|---|
| S1 | Cadrage, architecture | P01 (S1–S2) | — |
| S2 | Agent local + RAG + tool sûr | P02 (S3–S4) | — |
| S3 | Trace, oracles, dataset, caviardage | P02 (S5–S6) | 03-C01, 03-C02 |
| S4 | Manifest, CLI, uv/CI, splits | P03 (S7–S9) | 04-C01, 03-C04 |
| S5 | Statistique appariée et verdict | P04 (S20–S24) | 04-C03, 04-C04, 04-C05, 03-C06 |
| S6 | Identité, policy, authz, approval | P03 (S17–S19, volet permissions) | 06-C08 |
| S7 | Attaques, privacy, correction | — (sécurité 56D) | 06-C07, 06-C08 |
| S8 | API/DB/conformance, G8 | — | — |
| S9 | ML classique + tracking | F02 partiel | 05-C01, 05-C03, 05-C04 |
| S10 | GRU/TCN | F02 | 05-C05, 05-C06, 05-C07, 02-C02, 02-C06 |
| S11 | Transformer compact | F02 | 05-C08 |
| S12 | Ablations, G12 | F02 | 05-C10, 04-C07 |
| S13 | Contrastif | F02 | 05-C09 |
| S14 | SSL | F02 | 05-C09 |
| S15 | Calibration | F03 | 06-C01, 06-C02 |
| S16 | Conformal, G16 | F03 | 06-C04 |
| S17 | Abstention/coût | F03 | 06-C03, 03-C07 |
| S18 | OOD/robustesse/optimisation | F03 | 06-C05, 06-C07, 01-C08, 02-C09 |
| S19 | Multi-task, math pack | F01/F02 | 01-C06, 01-C08, 04-C06 |
| S20 | Test final/transfert, G20 | R2–R3 | 04-C09, 06-C09 |
| S21 | MCP et sécurité approfondie | — | 06-C08 |
| S22 | Registry/ONNX/serving | — | — |
| S23 | CI/perf/concurrence/pannes | — | — |
| S24 | Interop/bundle, G24 | — | — |
| S25–S26 | Rapport scientifique, pilote borné | P05–P08 | 04-C09, 06-C09 |

## 4. Exigences et état, semaine par semaine

États : `IMPLEMENTE_ET_TESTE`, `PARTIEL`, `ABSENT`, `NON_VERIFIABLE`.

| Semaine | Exigence (32S) | Fichiers existants | Tests | État | Travail restant |
|---|---|---|---|---|---|
| S1 | Cadrage, architecture, CLI de démonstration | `src/axiomeval/{models,config,cli,demo}`, `docs/architecture.md`, `docs/decisions.md` | `tests/test_week1.py` (26) | IMPLEMENTE_ET_TESTE | — |
| S2 | Agent local réel, RAG, tool sûr, RAM/latence/temps | `collect/{agent,adapters,tools,knowledge}.py`, `configs/agent.yaml`, `fixtures/support` | `tests/test_agent_p02.py` (21, dont 1 réel) | IMPLEMENTE_ET_TESTE | Disque/cold start formalisés, taux de succès des outils |
| S3 | Trace, oracles, provenance, caviardage avant logs, `label_source`, préfixes | `collect/{trace,redaction,oracle}.py` | idem | PARTIEL | `label_source`, droits/licence par donnée, préfixes à un horizon, data card |
| S4 | Manifest de release, CLI, CI, splits gelés, cache, draw/seed | CLI `run-agent` ; splits uniquement synthétiques dans TX-01 | — | PARTIEL | Manifest versionné, corpus de scénarios groupés, partitions gelées, workflow CI, cache déterministe |
| S5 | Statistique appariée intégrée au verdict ; missing/NaN → INCOMPLETE | `labs/comparaison_axm.py` (synthétique) | `tests/test_comparaison_axm.py` (6) | PARTIEL | Comparaison baseline/candidate sur traces réelles, métrique métier dans le verdict (cas T3), marges et IC (lot P04) |
| S6 | Identité serveur, scope/args/expiry, approbation, fail-closed, replay refusé | liste d'outils interdits seulement | — | ABSENT | Moteur d'autorisation hors modèle |
| S7 | Injections directe/indirecte/RAG/tool, exfiltration, canaris, correction → régression | détection d'un canari et d'un outil interdit | 2 cas | PARTIEL | Corpus versionné par famille, exécutions réelles, correctifs, tests de régression |
| S8 | API REST, contrats, DB, migrations, reprise, G8 | — | — | ABSENT | Tout |
| S9–S24 | ML, DL, Reliable AI, MCP, MLOps, interop | `labs/comparaison_axm.py` couvre bootstrap/Hoeffding/allocation sur données synthétiques | — | ABSENT (S19 partiel pour la puissance) | Tout ; dépend d'un corpus réel suffisant (S3–S5) |

## 5. Dépendances bloquantes

1. **Corpus réel** (S3–S5) : toutes les expériences ML/DL (S9–S20) exigent des trajectoires réelles, des labels avec `label_source`, des groupes indépendants et des partitions gelées. Aujourd'hui : 5 tâches × 3 répétitions = 15 trajectoires. Insuffisant pour toute conclusion ML.
2. **Verdict statistique** (S5, P04) : S12, S17 et S20 réutilisent la comparaison appariée et la règle de décision.
3. **Autorisation hors modèle** (S6) : S7 et S21 testent son contournement.
4. **API/DB** (S8) : S22 (serving) et S23 (concurrence, reprise) s'appuient dessus.
5. **Matériel** : RTX 3060 6 Go, 15,7 Go de RAM, 15 Go de disque libre (10 nov.). Suffisant pour un petit LLM local et des modèles compacts ; pas pour de gros benchmarks externes.
6. **Benchmark externe** (S20, AE14) : AgentDojo, ATBench ou τ-bench demandent un téléchargement et une adaptation ; à vérifier (licence, taille) avant tout engagement.

## 6. Plan d'exécution réaliste

La spécification prévoit 72 h de travail par bloc de 4 semaines, soit environ 430 h pour S7–S24. **Ce travail ne peut pas être réalisé avec rigueur en une seule session.** Les numéros de semaine sont des lots de référence, pas une promesse de durée. Ordre retenu, sans sauter de dépendance :

1. Lot A (S3–S6 manquants) : corpus de scénarios groupés + manifest + partitions gelées ; verdict statistique intégré (P04) ; moteur d'autorisation ; CI locale.
2. Lot B (S7–S8) : corpus d'attaques réel, correctifs et régressions ; API + SQLite + migrations ; gate G8.
3. Lot C (S9) : génération d'un corpus réel suffisant avec deux releases, labels déterministes, baselines ML.
4. Lots suivants (S10–S24) : uniquement après réception des précédents, chacun avec tests, commit et note de limites.

Chaque lot se termine par : tests exécutés, commit local (pas de push), mise à jour de `docs/progression/COMMITS_S07_S24.md` et `docs/progression/ETAT_MISSION.md` pour une reprise exacte.

## 7. Manuels AXM disponibles (sources consultables)

Sources LaTeX dans `Math IA\AXM\16 - Refonte mathématique et visuelle\AXM-0x\Sources\cNN.tex` et PDF `A - Manuel integral.pdf`. Titres vérifiés :

- AXM-01 : C01 espaces vectoriels … C06 SVD, pseudo-inverse … C08 covariance, blanchiment, distances régularisées.
- AXM-02 : C02 chaîne, Jacobienne, différentiation automatique ; C05 descente ; C06 gradients stochastiques et Adam ; C09 multiobjectif.
- AXM-03 : C04 échantillonnage, groupes, différences appariées ; C06 concentration et martingales ; C07 décision bayésienne et coûts asymétriques ; C08 Monte-Carlo.
- AXM-04 : C01 estimande, unités, plan ; C03 intervalles et comparaisons appariées ; C04 tests, marges, non-infériorité ; C05 bootstrap ; C06 puissance ; C07 multiplicité ; C09 protocole confirmatoire.
- AXM-05 : C03 régression logistique ; C04 entropie ; C05 rétropropagation ; C07 séquences ; C08 attention et Transformers ; C09 contrastif.
- AXM-06 : C01 scores propres et calibration ; C03 abstention ; C04 prédiction conforme ; C05 hors distribution ; C07 robustesse ; C08 politiques de sécurité.
- AXM-07 : régression, modèles mixtes, GEE (évaluation d'agents à temps fixé).
