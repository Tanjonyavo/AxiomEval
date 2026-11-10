# Journal des commits de la mission S07–S24

Branche locale `feat/mission-s24`, partie de `459c357`. Aucun push. Aucun message ne contient de signature d'assistant (vérifié par `git log --format=%B | grep -ci claude` = 0).

Les semaines S04–S06 de la spécification 32 semaines n'étaient pas réalisées (voir `docs/audit/AUDIT_INITIAL_S24.md`) ; elles bloquaient S07 et ont été faites d'abord.

| Semaine | Commit | Fonctionnalités | Tests exécutés | Résultats | Limites |
|---|---|---|---|---|---|
| Audit | `f9b3e44` | État initial, correspondance 32S / roadmap 18 / AXM | — | 11 commits de départ, 53 tests | — |
| S06 | `15dcf35` | Moteur d'autorisation hors modèle : identité de session, rôle, tenant, propriétaire, plafonds, approbations à usage unique, fail-closed | `tests/test_policy_s06.py` (14) + suite complète : 67 OK | Tous les cas §31.7 refusés avec la bonne raison | Pas d'OIDC/JWT/OPA réels (identité simulée dans le laboratoire) |
| S04 | `7b9e6aa` | Corpus groupé (27 groupes, 81 scénarios), partitions gelées par groupe, manifestes de release, collecte réelle avec clés de tirage, data card, workflow CI | Suite complète : 85 OK | Partitions train 14, validation 5, calibration 4, test 4 groupes | CI écrite mais non exécutée sur GitHub (pas de push) ; pas d'`uv` ni de lockfile |
| S05 | `c269957` | Comparaison appariée par groupe, borne de Hoeffding, bootstrap groupé, verdict §38 incluant le succès métier, bornes binomiales exactes | `tests/test_corpus_p03_p04.py` (18) | Priorité REJECT > INCOMPLETE > HOLD > PROMOTE vérifiée | Hoeffding très conservateur à 27 groupes |
| S07 | `eed1a1b` | Garde de sortie (clair, espacé, inversé, base64, hex), corpus de régression sécurité (7 groupes), release gardée, modèle de menace, rapport par famille | `tests/test_security_s07.py` (8) : 93 OK au total | — | Mémoire/contexte multi-session hors périmètre (agent sans mémoire) |
| S08 | `d741b34` | API FastAPI locale, SQLite, migrations vérifiées par empreinte, imports atomiques et idempotents, sauvegarde, jeton, limite de taille | `tests/test_api_s08.py` (18) : 111 OK | Démo réelle : import 2 × 162, ré-import 0, verdict HTTP = CLI, 401 sans jeton | Pas de test de charge ni de concurrence (S23) |
| S07 | `f7e3ecf` | Correctif F-001 : garde des arguments d'outil ; findings F-001, F-002 ; rapports de sécurité réels | 121 OK dont le rejeu du comportement réel | r4 : 0 brèche / 63 + 162 exécutions | Correctif prouvé par rejeu ; r4 n'a pas reproduit le comportement |
| S05 | `0ec1fca` | Comparaisons réelles de releases, empreintes des données | — | r2, r3 : REJECT ; r4 : HOLD (27 groupes insuffisants) | — |
| S09 | `3846051` | Contrat de caractéristiques de préfixe, baselines (majorité, règle, logistique, boosting), sélection groupée, intervalles groupés, ablations, release tenue à l'écart | `tests/test_ml_s09.py` (9) : 121 OK | PR-AUC logistique 0,77 [0,47 ; 0,97], boosting 0,88 [0,62 ; 0,98], majorité 0,54 | 4 groupes de test : aucune supériorité démontrée ; pas de DVC/MLflow |

| S07 | `1e4fbd6` | Data card du corpus de régression sécurité | — | 7 groupes, 21 scénarios | — |
| Pédagogie | `9ac6dbd` | Générateur de manuels, volumes de code expliqué, manuel, maths, exercices, entrevues (PDF inspectés) | 121 OK | Couverture ligne par ligne 399 / 4 371 lignes significatives (9,1 %) | 4 fichiers expliqués à 100 % seulement |

Rapport de fin de mission : `docs/progression/RAPPORT_FINAL_S24.md`.

S10 à S24 : aucun commit. Voir `docs/progression/ETAT_MISSION.md`.
