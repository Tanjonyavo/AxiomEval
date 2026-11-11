# S9 sur le corpus v2 — baselines sur préfixes de trajectoires

Rapport brut : `reports/s09/v2_baselines.json`. Manifeste : données `7da7d3df…`, commit `dcda87b`, graines 0, 1, 2. Même protocole, mêmes caractéristiques (`prefix-features-v1`) et même horizon que la première expérience S9 (`S09_BASELINES.md`). Seuls les données et l'évaluation par famille sont nouvelles.

## Données

| Élément | Valeur |
|---|---|
| Exécutions | 4 320 réelles : 4 releases × 540 scénarios × 2 tirages (`data/MANIFEST_V2.json`) |
| Corpus | v2, 180 groupes, 63 familles (`docs/data/DATA_CARD_V2.md`) |
| Entraînement + validation | 126 groupes, 3 024 exécutions |
| Test (partition gelée) | 28 groupes, 672 exécutions, prévalence 0,499 |
| Étiquette | résultat métier ≠ SUCCESS (« demande une revue ») |

## Résultats, partition gelée (28 groupes de test)

| Modèle | PR-AUC [IC 95 % groupes] | ROC-AUC | Brier [IC 95 % groupes] |
|---|---|---|---|
| Majorité | 0,499 [0,38 ; 0,62] | 0,500 | 0,251 [0,24 ; 0,26] |
| Règle « premier pas sans outil » | 0,582 [0,43 ; 0,74] | 0,637 | 0,232 [0,21 ; 0,25] |
| Régression logistique (C = 1) | **0,897 [0,82 ; 0,95]** | 0,871 | **0,141 [0,11 ; 0,17]** |
| Boosting (HistGradientBoosting) | 0,851 [0,75 ; 0,92] | 0,818 | 0,168 [0,13 ; 0,21] |

Les graines 0, 1 et 2 donnent les mêmes points : les modèles sont déterministes à données fixées et les graines ne changent que le bootstrap.

## Ablations (graine 0)

| Variante | Logistique PR-AUC | Boosting PR-AUC |
|---|---|---|
| Complète | 0,897 | 0,851 |
| Structure seule (sans texte) | 0,804 [0,68 ; 0,89] | 0,859 [0,76 ; 0,93] |
| Texte seul | 0,841 [0,73 ; 0,91] | 0,750 [0,62 ; 0,86] |
| Avec l'identifiant de release (raccourci interdit) | 0,906 | 0,853 |

## Généralisation

**Release tenue à l'écart** (entraînement sur 3 releases, test sur les 28 groupes de la 4e) : logistique 0,86 (r3) à 0,93 (r1) ; boosting 0,76 (r3) à 0,86 (r1). r3, le modèle 0,5B, est la plus difficile à prévoir à partir des autres.

**Familles tenues à l'écart** (14 familles sur 63 jamais vues à l'entraînement ; 41 groupes, 984 exécutions, prévalence 0,645) :

| Modèle | PR-AUC [IC 95 %] | ROC-AUC | Brier [IC 95 %] |
|---|---|---|---|
| Majorité | 0,645 [0,54 ; 0,74] | 0,500 | 0,288 [0,27 ; 0,31] |
| Règle | 0,675 [0,57 ; 0,79] | 0,561 | 0,290 [0,26 ; 0,32] |
| Régression logistique (C = 10) | 0,811 [0,73 ; 0,89] | 0,715 | 0,311 [0,26 ; 0,37] |
| Boosting | **0,868 [0,81 ; 0,92]** | 0,765 | **0,208 [0,18 ; 0,24]** |

## Interprétation

1. **H-S09 est soutenue sur la partition gelée.** La régression logistique dépasse la majorité et la règle : les intervalles groupés sont disjoints (0,82 > 0,62 et 0,82 > 0,74). Avec 4 groupes de test (v1), ce n'était pas démontrable.
2. **Logistique et boosting ne sont pas départagés** sur la partition gelée : leurs intervalles se chevauchent.
3. **Le texte de la question mène à un raccourci de famille.** Sur des familles jamais vues, la logistique (surtout textuelle) perd 0,09 de PR-AUC. Son Brier (0,311) devient **pire que celui de la majorité** (0,288) : ses probabilités sont mal calibrées hors des familles connues. Le boosting, qui s'appuie davantage sur la structure du premier pas, garde un Brier meilleur que la majorité (intervalles disjoints).
4. Le raccourci « release » apporte +0,009 de PR-AUC : négligeable. Les caractéristiques n'encodent donc pas déjà l'identité du modèle de façon décisive.

## Limites

- La comparaison des modèles repose sur des **intervalles marginaux** : un bootstrap apparié de la différence serait plus juste. Les prédictions ne sont pas encore conservées dans le rapport.
- Un seul agent, un seul domaine, des labels écrits par règles. La généralisation à un autre agent (transfert, §9) n'est pas testée.
- Les 63 familles restent peu nombreuses : 14 familles de test, c'est encore une petite base pour juger la généralisation.
- La calibration (S15) n'est pas faite. Le résultat 3 montre qu'elle est nécessaire avant d'utiliser ces probabilités pour décider d'une revue.
- Pas de DVC ni de MLflow : le suivi passe par le manifeste JSON.

## Statut

**S9 : IMPLÉMENTÉ ET TESTÉ au périmètre du laboratoire.** La conclusion H-S09 est soutenue sur 28 groupes de test, avec la limite de généralisation du point 3.
