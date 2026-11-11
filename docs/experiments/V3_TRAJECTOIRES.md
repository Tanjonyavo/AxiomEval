# Corpus v3 : longueur réelle des trajectoires

Mesuré le 2026-11-11 sur 2 × 1 470 exécutions réelles (r1-baseline et r6-bound, Qwen2.5 1,5B, 2 tirages par scénario), corpus v3 (`9a0cbda9…`). Données : `data/runs/v3/`, empreintes dans `data/MANIFEST_V3.json`. Mesure : `tools/data/trajectories.py`, rapport `reports/s10/v3_lengths.json`.

## Question

Le corpus v3 ajoute 9 familles multi-étapes (65 groupes) pour que les trajectoires soient assez longues pour un modèle de séquence (S10). L'ont-elles allongées ?

## Résultat

| Sous-ensemble | Exécutions | Appels au modèle (moyenne) | ≥ 2 appels | ≥ 3 appels |
|---|---|---|---|---|
| r1, familles v2 | 1 080 | 1,26 | 25,8 % | 0 % |
| r1, familles multi-étapes | 390 | 1,62 | 62,3 % | 0 % |
| r6, familles v2 | 1 080 | 1,30 | 29,5 % | 0 % |
| r6, familles multi-étapes | 390 | 1,75 | 74,6 % | 0 % |

Les tâches multi-étapes doublent à peu près la part des trajectoires à deux appels. **Aucune des 2 940 exécutions ne fait trois appels**, alors que la release en autorise quatre (`max_steps: 4`).

La cause se voit dans les traces : le modèle demande plusieurs outils **dans le même appel** (par exemple `lookup_order_status` et `refund_order` ensemble), puis répond au pas suivant. Le nombre d'étapes logiques de la tâche ne devient donc pas un nombre d'appels. Cela a une conséquence de sécurité (finding F-008 : le remboursement est décidé avant que le statut soit lu).

## Succès par famille multi-étapes

| Famille | r1 | r6 |
|---|---|---|
| statut_double | 9/48 | 14/48 |
| verifier_puis_rembourser | 24/60 | 22/60 |
| montant_puis_decision | 0/60 | 0/60 |
| rembourser_et_delai | 1/36 | 0/36 |
| garantie_puis_escalade | 0/30 | 0/30 |
| transporteur_et_delai | 12/48 | 12/48 |
| rembourser_deux | 23/36 | 30/36 |
| montant_mixte_autre_client | 0/36 | 7/36 |
| injection_resultat_outil | 23/36 | 35/36 |

Les labels des familles à 0 succès ont été vérifiés contre la base documentaire (garanties, délais, seuil de 50 $) : les échecs viennent du modèle (refus, pas d'escalade, liste passée comme numéro de commande, remboursement de 50 $ au lieu du total), pas d'une erreur d'étiquetage visible. Pour `montant_puis_decision`, r6 bloque aussi la bonne action, car le total n'est pas écrit dans la demande (coût mesuré de la liaison, voir F-008).

## Conséquence pour S10

- Horizon 1 (jusqu'au premier appel au modèle) : toutes les exécutions.
- Horizon 2 : 35,5 % des exécutions de r1 et 41,5 % de r6, avec plus de familles qu'en v2.
- Horizon 3 : population vide. Il n'est pas mesurable avec ce modèle.

Les séquences restent courtes (au plus deux appels, une dizaine d'événements). Un modèle de séquence ne peut donc exploiter que l'ordre de quelques événements. Le rapport S10 doit le dire, quel que soit son résultat.

## Limites

- Un seul modèle (1,5B) ; un modèle plus grand ferait peut-être des appels séquentiels.
- Deux tirages par scénario : les proportions par famille ont de larges intervalles.
- La génération sur GPU n'est pas parfaitement reproductible à graine égale (mesuré en v2).
