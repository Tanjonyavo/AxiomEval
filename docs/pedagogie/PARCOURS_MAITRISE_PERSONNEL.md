# Parcours de maîtrise personnel

Objectif : niveau 5 (défense technique) sur ce qui est implémenté. Niveaux : 1 lecture, 2 compréhension, 3 application, 4 autonomie, 5 défense. Une semaine n'est validée que si son « évaluation finale » est réussie **sans aide**.

| Semaine | Prérequis | Lecture théorique | Lecture du code | Lecture AXM | Exercices | Commandes | Modification à réaliser | Évaluation finale |
|---|---|---|---|---|---|---|---|---|
| S01 | Python, dataclasses | Manuel §S01 | `models/`, `config.py`, `policies/gate.py` | — | Guide S6 (local) | `axiomeval demo --case violation` | Ajouter un cas de démo `stale` | Expliquer les 4 verdicts et leur ordre |
| S02 | S01 | Manuel §S02 | `collect/agent.py`, `adapters.py` | — | Guide S6 | `axiomeval run-agent` | Passer k de recherche à 3 et mesurer | Dessiner la boucle de l'agent |
| S03 | S02 | Manuel §S03, maths §1 | `collect/trace.py`, `redaction.py` | — | Guide S6 | tests P02 | Ajouter un motif de caviardage | Montrer qu'un réordonnancement est détecté |
| S04 | S03 | Manuel §S04 | `corpus/*.py` (`splits.py` expliqué) | 04-C01, 03-C04 | 1–12 | `axiomeval corpus` | Exercice 9 | Recalculer la partition à la main pour 4 groupes |
| S05 | S04, probabilités | Maths §2–5 | `stats/paired.py` (expliqué) | 03-C04, 03-C06, 04-C03, 04-C04, 04-C05 | 13–24 | `axiomeval compare` | Exercice 22 | Dériver le rayon de Hoeffding et le calculer pour n = 27 |
| S06 | S01 | Manuel §S06 | `policy/authz.py` (expliqué), `secure_tools.py` | 06-C08 | 25–36 | tests S06 | Exercice 33 | Réécrire `authorize` de mémoire, tests verts |
| S07 | S06 | Manuel §S07, `FINDINGS.md` | `security/egress.py` (expliqué), `corpus/evaluate.py` | 06-C07, 06-C08 | 37–48 | `axiomeval security-report` | Exercice 45 | Raconter F-001 de l'observation au test de régression |
| S08 | S05 | Manuel §S08 | `api/store.py`, `api/app.py` | — | 49–60 | `axiomeval serve` + curl | Exercice 58 | Expliquer l'idempotence et la reprise après erreur |
| S09 | S05, régression logistique | Maths §6–7 | `ml/features.py`, `ml/baselines.py` | 05-C01, 05-C03, 05-C04, 06-C01 | 61–72 | `axiomeval ml-baselines` | Exercice 69 | Expliquer pourquoi aucune supériorité n'est démontrée |
| S10–S24 | S09 | Manuel, tableau S10–S24 ; maths §8–12 | — (non implémenté) | voir tableau | à venir | — | — | Préparer l'objectif et le piège principal de chaque semaine |
| S25–S26 | tout | Manuel §S25–S26 | — | 04-C09, 06-C09 | — | — | Plan du rapport scientifique | Plan validé par un pair |

Rythme suggéré : une semaine du parcours par semaine réelle, 3 à 5 h, en commençant toujours par l'exercice de lecture de code avant de lire l'explication.
