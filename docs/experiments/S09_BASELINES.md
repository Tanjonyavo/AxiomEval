# S9 — Baselines ML sur préfixes de trajectoires (tâche B)

Rapport brut : `reports/s09/baselines.json` (manifest inclus : empreinte des données `edcf44f5…`, commit, versions, graines).

## Protocole

| Élément | Valeur |
|---|---|
| Question | Les caractéristiques visibles juste après le premier appel au modèle prédisent-elles qu'une exécution aura besoin de revue (résultat métier ≠ SUCCESS) mieux qu'une baseline majoritaire ? |
| Données | 648 exécutions réelles, 4 releases × 81 scénarios × 2 tirages, 27 groupes indépendants (`data/MANIFEST.json`) |
| Horizon | Après le premier `model_call` ; aucun outil exécuté, aucune réponse finale, aucun résultat d'autorisation visible |
| Caractéristiques | Documents récupérés, outils demandés au premier pas, réponse directe ou non, nombre d'outils, jetons d'entrée, longueur du premier texte ; TF-IDF de la question (vocabulaire appris sur l'entraînement seulement) |
| Exclus | Identifiant de release, modèle, latence (révèle la taille du modèle), autorisations, résultats d'outils, garde, réponse finale |
| Partitions | Groupes gelés : entraînement + validation = 19 groupes (456 exécutions) ; test = 4 groupes (96 exécutions), ouvert une fois par graine |
| Sélection | C de la régression logistique par validation croisée groupée (GroupKFold) sur l'entraînement uniquement |
| Incertitude | Bootstrap percentile à 95 % sur les **groupes de test** (unité indépendante), 1 000 tirages |
| Graines | 0, 1, 2 : résultats identiques (modèles déterministes à données fixées) ; la variabilité vient des données, pas des graines |

## Résultats (partition de test, 96 exécutions, 4 groupes, prévalence 0,54)

| Modèle | PR-AUC [IC 95 % groupes] | Brier [IC 95 % groupes] |
|---|---|---|
| Majorité | 0,542 [0,17 ; 0,83] | 0,256 [0,22 ; 0,28] |
| Règle « premier pas sans outil » | 0,533 [0,17 ; 0,90] | 0,266 [0,20 ; 0,33] |
| Régression logistique (C = 1) | 0,771 [0,47 ; 0,97] | 0,162 [0,04 ; 0,29] |
| Boosting (HistGradientBoosting) | 0,879 [0,62 ; 0,98] | 0,213 [0,03 ; 0,40] |

Ablations (régression logistique / boosting, PR-AUC) : structure seule 0,665 / 0,716 ; texte seul 0,884 / 0,733 ; avec identifiant de release 0,729 / 0,868 (pas de gain : le raccourci « release » n'aide pas ici).

Release tenue à l'écart (entraînement sur les 3 autres, test sur ses 4 groupes de test) : PR-AUC du boosting entre 0,75 (r3) et 0,92 (r4) ; même ordre de grandeur qu'en partition gelée.

## Interprétation

- En point, les deux modèles appris dépassent la majorité et la règle. **Les intervalles se chevauchent** : avec 4 groupes de test, aucune supériorité n'est démontrée.
- Le texte de la question porte l'essentiel du signal : le modèle apprend surtout quels **types de demande** échouent souvent (actions, comptes) plutôt que la dynamique de la trajectoire. C'est un raccourci de famille de scénario, pas une compréhension du comportement de l'agent.
- La règle simple ne bat pas la majorité : « répondre sans outil » n'est pas un bon signal global, car les questions d'information se résolvent justement sans outil.

## Statut et limites

**PARTIEL.** Pipeline, contrat de caractéristiques, audit de fuite (tests), sélection groupée, intervalles groupés et ablations : réalisés et testés. Conclusion scientifique : **impossible avec 27 groupes**. La spécification (§12.3) vise 200 à 600 groupes. Les modèles séquentiels (S10), le Transformer (S11) et les ablations (S12) n'ont pas de sens sur ce corpus : agrandir et diversifier le corpus est la prochaine étape bloquante.

Non réalisé : DVC et MLflow (suivi par manifest JSON maison à la place), calibration (S15), analyse d'erreurs détaillée.
