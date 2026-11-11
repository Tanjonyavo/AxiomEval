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
| P03 (corpus v2) | `5ec1646`, `2aac570` | Corpus v2 : 63 familles, 180 groupes, 540 scénarios, 46 commandes, 10 nouveaux documents dont un piégé ; provenance du corpus dans chaque enregistrement ; verdict INCOMPLETE si corpus différents | `tests/test_corpus_v2.py` (8) | Partitions : train 98, validation 28, calibration 26, test 28 groupes | `2aac570` corrige une date de gel des labels placée dans le futur (la collecte refusait tout, comme prévu) |
| S09 | `979d1a0`, `60f8d37` | Évaluation par familles tenues à l'écart ; outil de manifeste des données ; baselines refaites sur v2 | `tests/test_ml_s09.py` (10) | PR-AUC logistique 0,897 [0,82 ; 0,95] contre majorité 0,499 sur 28 groupes de test | Calibration dégradée sur familles inconnues |
| S07 | `d96dac9` | Correctif F-006 : caviardage des variantes de canari (espacées, casse, inversées, base64, hexadécimal) | test de régression F-006 | 1 enregistrement sur 4 320 touché avant correctif | L'enregistrement existant n'est pas réécrit (chaîne de hachage) |
| S05/S07 | `dcda87b` | 4 320 exécutions réelles sur v2, comparaisons, rapport de sécurité, findings F-003 à F-006 | — | 4 comparaisons REJECT ; r4 bloque tous les canaris mais divulgue un courriel interne | Comparaisons appariées en diagnostic seulement |
| S04 | `079852d` | Empreinte de l'environnement (documents, commandes, politique) dans chaque enregistrement ; verdict INCOMPLETE si environnements différents | `tests/test_corpus_v2.py` | — | Les exécutions v2 précèdent ce champ |
| S07 | `88cf85c`, `50f432d` | Correctif F-003 : valeurs protégées par la garde (egress-v3), release r5 ; retest réel | rejeu F-003 | r4 : 5/6 fuites ; r5 : 0/6 | r5 REJECT à cause de F-004 |
| S09 | `d709067` | Caractéristiques `prefix-features-v2` (documents appris sur l'entraînement) ; S9 refaite | `tests/test_ml_s09.py` (11) | Logistique 0,892 [0,81 ; 0,95] | — |
| S06 | `9923985` | Correctif F-004/F-005 : remboursement lié à la commande et au montant signé énoncés, release r6 ; retest réel | rejeux F-004 et F-005, 138 OK | r6 : 0 brèche / 1 080 ; r5 → r6 HOLD | Non-infériorité non démontrée (~520 groupes) |
| P03 (corpus v3) | `0f8a098` | Corpus v3 : v2 + 9 familles multi-étapes (65 groupes, 6 commandes à note de transporteur injectée), 245 groupes, 735 scénarios | `tests/test_corpus_v3.py` (5) | Partitions : train 135, validation 36, calibration 37, test 37 groupes | — |
| S05/S07 | `dba72c5` | 2 × 1 470 exécutions réelles v3 (r1, r6), longueurs de trajectoire, findings F-007 et F-008 | — | Aucune exécution à 3 appels ; r1 → r6 REJECT (40 remboursements non attendus) | Le modèle demande plusieurs outils dans le même pas |
| S10 | `9f3aa96`, `fcb2b49` | Séquences d'événements à horizon k, agrégat contre GRU, ablations ordre et structure, référence tabulaire | `tests/test_ml_s10.py` (7), 150 OK | Horizon 2 : Brier GRU 0,103 contre agrégat 0,129 (apparié [−0,044 ; −0,011]) ; ordre mélangé : même gain | H-S10 (l'ordre compte) non soutenue ; horizon 3 vide |
| S06/S07 | `a6910c0`, `9f0d0bc` | Correctif F-007/F-008 (`write-checks-v1`, release r7) ; retest réel | `tests/test_write_checks.py` (10), 160 OK | Brèches 40 → 6 ; remboursements conditionnels légitimes 18/36 → 0/36 | r6 → r7 REJECT ; F-008 partiellement corrigé |

Rapport de fin de mission : `docs/progression/RAPPORT_FINAL_S24.md`.

S11 à S24 : aucun commit. Voir `docs/progression/ETAT_MISSION.md`.
