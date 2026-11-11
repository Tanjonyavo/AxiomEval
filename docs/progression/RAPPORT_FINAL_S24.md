# Rapport final de la mission S24

Date : 2026-11-10. Branche locale `feat/mission-s24` (partie de `459c357`). Aucun push. Ce rapport ne décrit que ce qui a été exécuté ; tout le reste est marqué comme tel.

**Résumé honnête : S24 n'est pas atteinte.** Les semaines S04 à S08 de la spécification 32 semaines sont implémentées et testées, S09 est partielle, S10 à S24 ne sont pas commencées. Le blocage principal est scientifique, pas logiciel : le corpus compte 27 groupes indépendants alors que S10–S12 en demandent 200 à 600.

## A. État initial

Détail : `docs/audit/AUDIT_INITIAL_S24.md` (commit `f9b3e44`).

- 11 commits, 53 tests verts, lots P01 et P02 publiés sous le nom « S6 ».
- Correspondance établie : le « S6 » publié correspond aux semaines S02–S03 de la spécification 32 semaines. Les semaines S04 (corpus groupé), S05 (comparaison appariée) et S06 (autorisation hors modèle) manquaient et bloquaient S07.
- Décision : faire S06, S04, S05 avant S07 (ordre des dépendances, pas de l'ordre des numéros).

## B. Travail réalisé, semaine par semaine

| Semaine | Statut | Commits | Contenu vérifiable |
|---|---|---|---|
| S04 (P03) | IMPLÉMENTÉ ET TESTÉ | `7b9e6aa` | 18 familles, 27 groupes, 81 scénarios ; partitions gelées par groupe (train 14, validation 5, calibration 4, test 4) ; manifestes de release ; clés de tirage ; data card ; workflow CI écrit |
| S05 (P04) | IMPLÉMENTÉ ET TESTÉ | `c269957`, `0ec1fca` | Différences appariées par groupe, rayon de Hoeffding unilatéral, bootstrap groupé (diagnostic), bornes de Clopper-Pearson, verdict §38 |
| S06 | IMPLÉMENTÉ ET TESTÉ | `15dcf35` | Autorisation fail-closed hors modèle : identité, rôle, tenant, propriétaire, plafonds, approbations à usage unique liées aux arguments |
| S07 | IMPLÉMENTÉ ET TESTÉ | `eed1a1b`, `f7e3ecf`, `1e4fbd6` | Garde de sortie et d'arguments d'outil (egress-v2), corpus de régression sécurité (7 groupes), modèle de menace, findings F-001 et F-002 |
| S08 | IMPLÉMENTÉ ET TESTÉ | `d741b34` | API FastAPI locale, SQLite, migrations vérifiées par empreinte, imports atomiques et idempotents, jeton, limite de taille |
| S09 | PARTIEL | `3846051` | Contrat de caractéristiques de préfixe, 4 baselines, sélection groupée, intervalles groupés, ablations ; conclusion impossible (4 groupes de test) |
| S10–S24 | NON COMMENCÉ | — | — |
| Pédagogie | PARTIEL | `9ac6dbd` | Manuel, mathématiques, exercices, entrevues, 3 volumes de code ; couverture ligne par ligne 9,1 % |

Journal complet : `docs/progression/COMMITS_S07_S24.md`.

## C. Tableau final des gates

| Gate | Statut | Preuve |
|---|---|---|
| G8 (API + base + verdict reproductible) | ATTEINT au périmètre laboratoire | Démo réelle : `/health`, `/ready` (schéma `0002_verdicts`), import 162 + 162, ré-import 0 inséré, verdict HTTP identique au CLI, 401 sans jeton |
| G12 (modèles séquentiels vs baselines) | NON ÉVALUÉ | S10–S12 non implémentés ; corpus trop petit |
| G16 | NON ÉVALUÉ | — |
| G20 | NON ÉVALUÉ | — |
| G24 | NON ÉVALUÉ | — |

## D. Expériences réelles

Toutes les exécutions viennent de `qwen2.5:1.5b-instruct` (r3 : `qwen2.5:0.5b-instruct`) via Ollama local, température 0,7, 2 tirages. Empreintes des fichiers dans `data/MANIFEST.json` (les fichiers eux-mêmes restent locaux).

**Comparaisons de releases (P04, 648 exécutions, 27 groupes)** — `reports/s05/` :

| Comparaison | Verdict | Raison |
|---|---|---|
| r1 → r2 (prompt durci) | REJECT | fuite de `jeton_admin` |
| r1 → r3 (modèle 0,5b) | REJECT | brèches |
| r1 → r4 (garde) | HOLD | tentatives bloquées ; différence −0,012, bootstrap [−0,117 ; 0,093], rayon de Hoeffding 0,471, ~780 groupes nécessaires |
| r2 → r4 | HOLD | différence +0,080, bootstrap [0,019 ; 0,148], ~185 groupes nécessaires |

**Baselines S09** — `reports/s09/baselines.json`, `docs/experiments/S09_BASELINES.md` (test : 96 exécutions, 4 groupes, prévalence 0,54) :

| Modèle | PR-AUC [IC groupé 95 %] |
|---|---|
| Majorité | 0,542 |
| Règle | 0,533 |
| Logistique | 0,771 [0,47 ; 0,97], Brier 0,162 |
| Boosting | 0,879 [0,62 ; 0,98] |

Aucune supériorité n'est démontrée : les intervalles se chevauchent et 4 groupes ne suffisent pas.

## E. Sécurité

Rapports : `docs/security/RAPPORT_SECURITE_CORPUS_REGRESSION.md`, `RAPPORT_SECURITE_CORPUS_PRINCIPAL.md`, `FINDINGS.md`, `THREAT_MODEL.md`. Attaques uniquement contre l'agent local du laboratoire.

- Exfiltration (corpus de régression, 27 exécutions par release) : brèches r1 19/27, r2 15/27, r3 9/27, r4 0/27 (borne supérieure exacte ≤ 11 %).
- Injection directe : 3/9 → 0/9 avec la garde.
- Contournement d'approbation, mandataire confus, injection indirecte par RAG : 0 brèche observée (l'autorisation hors modèle bloque).
- **F-001** : le modèle a passé le canari comme `order_id` à un outil ; corrigé par la garde des arguments (egress-v2) et prouvé par un test de rejeu.
- **F-002** : un prompt durci ne suffit pas (r2 fuit toujours).
- Limite : ces résultats valent pour ce corpus, ce modèle et ces gardes. Ils ne prouvent pas une sécurité générale. La garde de sortie détecte des encodages connus ; un encodage nouveau peut passer.

## F. Couverture pédagogique

Mesure : `docs/pedagogie/INDEX_CODE_EXPLIQUE.md`, générée par `tools/pedagogie/build.py`. Le dossier `docs/pedagogie/` (manuels, guide, code expliqué, PDF) est personnel : il reste en local et n'est pas publié.

- 77 fichiers, 4 371 lignes significatives, **399 expliquées (9,1 %)**.
- Fichiers expliqués à 100 % : `policy/authz.py`, `stats/paired.py`, `security/egress.py`, `corpus/splits.py`.
- PDF produits et inspectés (rendu des formules KaTeX, aucune ligne de code tronquée) dans `docs/pedagogie/PDF/` : manuel intégral, mathématiques, exercices corrigés (72, S04–S09), préparation aux entrevues (55 questions), code expliqué volumes 01 à 03.
- Les semaines S10–S24 sont décrites dans le manuel comme PRÉVU, NON IMPLÉMENTÉ, sans code ni résultat.

## G. Commandes de démonstration testées

Testées pendant la mission sur Windows, PowerShell, `.venv` Python 3.14 :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests          # 121 OK, 1 ignoré
.\.venv\Scripts\python.exe -m axiomeval corpus --card docs/data/DATA_CARD.md
.\.venv\Scripts\python.exe -m axiomeval compare --baseline data/runs/r1-baseline.jsonl --candidate data/runs/r4-guarded.jsonl
.\.venv\Scripts\python.exe -m axiomeval security-report --runs data/runs/security-r1-baseline.jsonl data/runs/security-r4-guarded.jsonl --out docs/security/RAPPORT_SECURITE_CORPUS_REGRESSION.md
.\.venv\Scripts\python.exe -m axiomeval ml-baselines --runs data/runs/r1-baseline.jsonl data/runs/r2-hardened.jsonl data/runs/r3-degraded.jsonl data/runs/r4-guarded.jsonl --out reports/s09/baselines.json
$env:AXIOMEVAL_API_TOKEN = "<jeton local>"; .\.venv\Scripts\python.exe -m axiomeval serve --db data/axiomeval.db --port 8765
.\.venv\Scripts\python.exe tools/pedagogie/build.py
node tools/pedagogie/print.mjs <chemin vers playwright/index.mjs>
```

La collecte (`axiomeval collect`) demande `ollama serve` actif. Les arguments exacts des commandes sont donnés par `--help` ; les fichiers `data/runs/` ne sont pas versionnés et doivent être recollectés sur une autre machine.

## Ce qui reste

1. Agrandir le corpus à 150–300 groupes (familles nouvelles, second domaine), puis recollecter.
2. Refaire S9, puis S10 (GRU), S11–S12 (Transformer compact, ablations) et évaluer G12.
3. S13–S24 selon l'audit initial.
4. Exécuter la CI sur GitHub après un push décidé par le propriétaire du dépôt.
5. Ajouter DVC/MLflow (absents) et compléter les explications ligne par ligne.

Point de reprise exact : `docs/progression/ETAT_MISSION.md`.

## Mise à jour du 2026-11-11 : corpus v2 et S9 refaite

- **Corpus v2** (`fixtures/corpus-v2/`, `docs/data/DATA_CARD_V2.md`) : 180 groupes, 63 familles, 540 scénarios. Le corpus v1 est inchangé.
- **Collecte réelle** : 4 320 exécutions (4 releases × 540 × 2 tirages), `data/MANIFEST_V2.json`.
- **Verdicts** : les 4 comparaisons sont REJECT. Toutes les releases ont au moins une brèche ; r4 (garde) bloque toutes les fuites de canari mais divulgue un courriel interne (F-003). En diagnostic, la différence métier r1 → r4 vaut +0,046, bootstrap [0,007 ; 0,085] ; le rayon de Hoeffding (0,182) exige encore environ 280 groupes pour la marge de 0,10.
- **Sécurité** : findings F-003 à F-006 (`docs/security/FINDINGS.md`), correctif F-006 testé. F-003, F-004 et F-005 sont documentés sans correctif.
- **S9** : IMPLÉMENTÉ ET TESTÉ (`docs/experiments/S09_BASELINES_V2.md`, `prefix-features-v2`). Sur 28 groupes de test, la logistique atteint une PR-AUC de 0,892 [0,81 ; 0,95] contre 0,499 [0,38 ; 0,62] pour la majorité. Sur 14 familles jamais vues, son Brier n'est pas meilleur que celui de la majorité ; le boosting généralise mieux.
- **Toujours non faits** : S10 à S24, gates G12 à G24, transfert vers un second agent, CI distante, DVC/MLflow.
- **Correctifs retestés en réel** (2026-11-11) : F-003 (valeurs protégées, r5 : 0/6 fuite contre 5/6) ; F-004/F-005 (liaison à la demande, r6 : 0 brèche sur 1 080). Le verdict r5 → r6 est **HOLD**, premier verdict non-REJECT sur v2 ; la non-infériorité n'est pas démontrée.
- **S10 bloquée, avec mesure** : 74 % des trajectoires réelles font 4 événements, les autres 8. Il faut des tâches à plusieurs étapes avant un modèle séquentiel.

## Mise à jour du 2026-11-11 (après-midi) : corpus v3, S10, F-007 et F-008

- **Corpus v3** (`0f8a098`) : v2 + 9 familles multi-étapes, 245 groupes. 3 × 1 470 exécutions réelles (r1, r6, r7), `data/MANIFEST_V3.json`.
- **Trajectoires** (`docs/experiments/V3_TRAJECTOIRES.md`) : les tâches multi-étapes doublent la part des exécutions à deux appels (62 à 75 %), mais **aucune** des 4 410 exécutions ne fait trois appels : le modèle demande plusieurs outils dans le même pas.
- **S10 : IMPLÉMENTÉ ET TESTÉ, hypothèse non soutenue** (`docs/experiments/S10_SEQUENCES_V3.md`). Horizon 1 : agrégat, GRU et référence tabulaire S9 équivalents (PR-AUC 0,92 à 0,94). Horizon 2 : le GRU a un meilleur Brier que l'agrégat (0,103 contre 0,129, intervalle apparié [−0,044 ; −0,011], trois graines), mais le GRU sur événements mélangés garde le même gain. L'ordre n'apporte rien de mesurable ; résultat négatif valide au sens du §20.
- **Gate G12** : NON ÉVALUÉ. S10 est fait ; le Transformer compact (S11) et les ablations S12 ne le sont pas.
- **Findings F-007 et F-008** (`docs/security/FINDINGS.md`) : remboursement supérieur au total de la commande ; liaison à la demande trompée par un seuil, par le montant d'une autre commande et par une condition décidée avant la lecture du statut. r1 → r6 : REJECT (40 brèches).
- **Correctif `write-checks-v1`, release r7** (`a6910c0`) : brèches 40 → 6, mais les remboursements conditionnels légitimes passent de 18/36 à 0/36. r6 → r7 : REJECT. F-008 est **partiellement corrigé** et le correctif a un coût réel ; r7 n'est pas à promouvoir.
- **Toujours non faits** : S11 à S24, gates G12 à G24, revue humaine des tentatives bloquées, transfert, CI distante.
