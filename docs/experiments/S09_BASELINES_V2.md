# S9 sur le corpus v2 — baselines sur préfixes de trajectoires

Rapport de référence : `reports/s09/v2_baselines_features_v2.json`, caractéristiques `prefix-features-v2`, commit `50f432d`, données `7da7d3df…`, graines 0, 1, 2. Même horizon et même protocole que la première expérience S9 (`S09_BASELINES.md`). Les nouveautés sont les données et l'évaluation par famille.

Historique : un premier passage (`reports/s09/v2_baselines.json`, commit `dcda87b`) utilisait `prefix-features-v1`, qui ne connaissait que les 6 documents du corpus v1. Les 10 documents ajoutés en v2 étaient donc invisibles. Le correctif `d709067` apprend les indicateurs de documents sur l'entraînement. Les écarts entre les deux passages sont donnés plus bas ; ils ne changent pas les conclusions principales.

## Données

| Élément | Valeur |
|---|---|
| Exécutions | 4 320 réelles : 4 releases (r1 à r4) × 540 scénarios × 2 tirages (`data/MANIFEST_V2.json`) |
| Corpus | v2, 180 groupes, 63 familles (`docs/data/DATA_CARD_V2.md`) |
| Entraînement + validation | 126 groupes, 3 024 exécutions |
| Test (partition gelée) | 28 groupes, 672 exécutions, prévalence 0,499 |
| Étiquette | résultat métier ≠ SUCCESS (« demande une revue ») |

## Résultats, partition gelée (28 groupes de test)

| Modèle | PR-AUC [IC 95 % groupes] | ROC-AUC | Brier [IC 95 % groupes] |
|---|---|---|---|
| Majorité | 0,499 [0,38 ; 0,62] | 0,500 | 0,251 [0,24 ; 0,26] |
| Règle « premier pas sans outil » | 0,582 [0,43 ; 0,74] | 0,637 | 0,232 [0,21 ; 0,25] |
| Régression logistique (C = 1) | **0,892 [0,81 ; 0,95]** | 0,868 | **0,145 [0,11 ; 0,18]** |
| Boosting (HistGradientBoosting) | 0,852 [0,76 ; 0,92] | 0,817 | 0,168 [0,13 ; 0,21] |

Les graines 0, 1 et 2 donnent les mêmes points : les modèles sont déterministes à données fixées et les graines ne changent que le bootstrap.

## Ablations (graine 0, PR-AUC)

| Variante | Logistique | Boosting |
|---|---|---|
| Complète | 0,892 | 0,852 |
| Structure seule (sans texte) | 0,810 [0,68 ; 0,90] | 0,866 [0,77 ; 0,94] |
| Texte seul | 0,841 [0,73 ; 0,91] | 0,750 [0,62 ; 0,86] |
| Avec l'identifiant de release (raccourci interdit) | 0,902 | 0,860 |

## Généralisation

**Release tenue à l'écart** (entraînement sur 3 releases, test sur les 28 groupes de la 4e) : logistique de 0,85 (r3) à 0,92 (r1) ; boosting de 0,77 (r3) à 0,86 (r1). r3, le modèle 0,5B, reste la plus difficile à prévoir à partir des autres.

**Familles tenues à l'écart** (14 familles sur 63 jamais vues à l'entraînement ; 41 groupes, 984 exécutions, prévalence 0,645) :

| Modèle | PR-AUC [IC 95 %] | ROC-AUC | Brier [IC 95 %] |
|---|---|---|---|
| Majorité | 0,645 [0,54 ; 0,74] | 0,500 | 0,288 [0,27 ; 0,31] |
| Règle | 0,675 [0,57 ; 0,79] | 0,561 | 0,290 [0,26 ; 0,32] |
| Régression logistique (C = 1) | 0,813 [0,73 ; 0,89] | 0,698 | 0,282 [0,24 ; 0,33] |
| Boosting | **0,870 [0,81 ; 0,92]** | 0,764 | **0,206 [0,17 ; 0,24]** |

## Interprétation

1. **H-S09 est soutenue sur la partition gelée.** La régression logistique dépasse la majorité et la règle : les intervalles groupés sont disjoints (0,81 > 0,62 et 0,81 > 0,74). Avec 4 groupes de test (v1), ce n'était pas démontrable.
2. **Logistique et boosting ne sont pas départagés** sur la partition gelée : leurs intervalles se chevauchent.
3. **Le texte de la question mène à un raccourci de famille.** Sur des familles jamais vues, la logistique, surtout textuelle, perd 0,08 de PR-AUC (sur un autre ensemble de test). Son Brier (0,282) n'est **pas meilleur que celui de la majorité** (0,288) : ses probabilités ne valent rien hors des familles connues. Le boosting s'appuie davantage sur la structure du premier pas et garde un Brier meilleur que la majorité (intervalles disjoints).
4. Le raccourci « release » apporte +0,010 de PR-AUC : négligeable.
5. Écarts avec le passage `prefix-features-v1` : la logistique gelée passe de 0,897 à 0,892. Sur les familles inconnues, son Brier passe de 0,311 (pire que la majorité, avec C = 10) à 0,282 (C = 1). La conclusion 3 est donc nuancée : le Brier était pire que la majorité avec v1, il est à égalité avec v2.

## Limites

- La comparaison des modèles repose sur des **intervalles marginaux** : un bootstrap apparié de la différence serait plus juste. Les prédictions ne sont pas encore conservées dans le rapport.
- Un seul agent, un seul domaine, des labels écrits par règles. La généralisation à un autre agent (transfert, §9) n'est pas testée.
- Avec 63 familles, dont 14 en test, la base reste petite pour juger la généralisation.
- La calibration (S15) n'est pas faite. Le résultat 3 montre qu'elle est nécessaire avant d'utiliser ces probabilités pour décider d'une revue.
- Pas de DVC ni de MLflow : le suivi passe par le manifeste JSON.

## Statut

**S9 : IMPLÉMENTÉ ET TESTÉ au périmètre du laboratoire.** H-S09 est soutenue sur 28 groupes de test, avec la limite de généralisation du point 3.
