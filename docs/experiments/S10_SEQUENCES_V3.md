# S10 — Modèles de séquence d'événements (corpus v3)

Rapports : `reports/s10/v3_sequence.json` (agrégat et GRU), `reports/s10/v3_tabular_h1.json` (référence tabulaire S9). Code : `src/axiomeval/ml/sequence.py` (`event-sequence-v1`, commit `9f3aa96`), commande `ml-sequence`. Données : r1-baseline et r6-bound sur le corpus v3, 2 × 1 470 exécutions réelles, empreinte `fb1e2f3b…` (`data/MANIFEST_V3.json`). Graines 0, 1, 2 ; PyTorch 2.14.1 sur CPU, scikit-learn 1.9.1, Python 3.14.5.

## Question et hypothèse

H-S10 : à horizon égal, un encodeur qui lit les événements **dans l'ordre** (GRU) prédit mieux les exécutions à revoir (`business != SUCCESS`) qu'un encodeur qui les agrège **sans ordre** (moyenne et maximum des vecteurs d'événements, régression logistique).

## Protocole

- **Horizon k** : tous les événements jusqu'au k-ième appel au modèle inclus. Si cet appel demande des outils, la prédiction est faite avant leur exécution. La réponse finale et l'événement `output` ne sont jamais visibles.
- **Population** : seules les exécutions qui atteignent le k-ième appel. Tous les modèles d'un horizon sont évalués sur la même population et le même test.
- **Événement** : type, outil demandé ou appelé, statut du résultat, autorisation et criticité, nombre de documents récupérés, nombre d'appels d'outils, longueur du texte du modèle, jetons de prompt, numéro de pas, position. Aucun texte de résultat d'outil ni de réponse.
- **Question** : TF-IDF appris sur l'entraînement seul ; projeté en 16 dimensions pour le GRU, concaténé pour l'agrégat.
- **Partitions figées** du corpus v3, par groupe. Sélection : deux valeurs par modèle (C ∈ {0,1 ; 1} ; taille cachée ∈ {16 ; 32}), choisies sur la perte logistique des groupes de validation. GRU : Adam, arrêt précoce sur la validation (patience 8). Le test est évalué une seule fois.
- **Incertitude** : bootstrap par groupe de test (1 000 tirages). La différence GRU − agrégat est un bootstrap **apparié** (mêmes groupes tirés pour les deux modèles).
- **Ablations** : structure seule (sans la question) ; ordre mélangé (mêmes événements, ordre aléatoire, positions recalculées).

## Ce que l'horizon permet

| Horizon | Exécutions | Groupes de test | Événements (moyenne) | Prévalence test |
|---|---|---|---|---|
| 1 | 2 939 | 37 | 3,0 | 0,586 |
| 2 | 1 132 | 24 | 7,6 | 0,597 |
| 3 | 0 | — | — | — |

Aucune exécution n'atteint un troisième appel (voir `V3_TRAJECTOIRES.md`). À l'horizon 1, la séquence est toujours `input → retrieval → model_call` : l'ordre y est constant, un GRU ne peut rien en tirer.

## Résultats (graine 0 ; les graines 1 et 2 donnent les mêmes conclusions)

| Horizon | Modèle | Paramètres | PR-AUC [IC 95 %] | Brier [IC 95 %] |
|---|---|---|---|---|
| 1 | Majorité | — | 0,586 [0,47 ; 0,70] | 0,254 [0,25 ; 0,26] |
| 1 | Tabulaire S9 (logistique, `prefix-features-v2`) | — | 0,922 [0,83 ; 0,97] | 0,128 [0,08 ; 0,18] |
| 1 | Agrégat (logistique) | 1 574 | 0,932 [0,87 ; 0,97] | 0,138 [0,11 ; 0,17] |
| 1 | GRU | 30 017 | 0,941 [0,88 ; 0,98] | 0,127 [0,09 ; 0,17] |
| 2 | Majorité | — | 0,597 [0,42 ; 0,76] | 0,302 [0,25 ; 0,35] |
| 2 | Agrégat (logistique) | 752 | 0,955 [0,87 ; 0,99] | 0,129 [0,08 ; 0,19] |
| 2 | GRU | 13 297 | 0,963 [0,89 ; 0,99] | 0,103 [0,06 ; 0,16] |

Différence appariée GRU − agrégat :

| Horizon | Variante | PR-AUC | Brier |
|---|---|---|---|
| 1 | complète, graines 0 / 1 / 2 | [−0,004 ; 0,024] / [−0,009 ; 0,021] / [−0,008 ; 0,024] | [−0,029 ; 0,009] / [−0,028 ; 0,006] / [−0,029 ; 0,008] |
| 2 | complète, graines 0 / 1 / 2 | [−0,003 ; 0,034] / [−0,004 ; 0,038] / [−0,007 ; 0,036] | **[−0,044 ; −0,011] / [−0,053 ; −0,011] / [−0,047 ; −0,011]** |
| 2 | ordre mélangé | [−0,005 ; 0,027] | **[−0,046 ; −0,012]** |
| 2 | structure seule | [−0,180 ; −0,011] | [0,003 ; 0,044] |

## Lecture

1. **Tous les modèles appris dépassent nettement la majorité**, aux deux horizons, avec des intervalles disjoints.
2. **À l'horizon 2, le GRU a un meilleur Brier que l'agrégat** (environ −0,026, intervalle apparié qui exclut 0 pour les trois graines). En PR-AUC, la différence n'est pas démontrée.
3. **Ce gain ne vient pas de l'ordre.** Avec les événements mélangés, le GRU garde le même avantage (Brier 0,101, intervalle [−0,046 ; −0,012]). H-S10 n'est donc **pas soutenue** : sur ces trajectoires, l'ordre des événements n'apporte rien de mesurable. L'avantage du GRU vient plus probablement de sa capacité (environ 18 fois plus de paramètres) et de sa projection non linéaire de la question.
4. **La question porte l'essentiel du signal.** Sans elle, tous les modèles chutent (PR-AUC 0,69 à 0,79 à l'horizon 2) ; et en structure seule, le GRU fait **moins bien** que l'agrégat (Brier +0,003 à +0,044).
5. **À l'horizon 1, l'agrégat, le GRU et la référence tabulaire S9 sont équivalents** compte tenu des intervalles.

Conclusion : résultat négatif valide pour l'ordre (spec §20). Avec un agent qui fait au plus deux appels, un modèle de séquence n'apporte pas plus qu'un bon agrégat. Un GRU n'est pas justifié ici, sauf comme modèle plus flexible de la question, ce qu'un modèle non linéaire tabulaire peut aussi faire.

## Limites

- **Population sélectionnée** : l'horizon 2 ne garde que les exécutions où le modèle a demandé un outil au premier appel. Ce n'est pas un échantillon des exécutions en général.
- **24 groupes de test à l'horizon 2** : les intervalles sont larges ; une différence plus petite que 0,01 de Brier ne serait pas détectable.
- **Deux releases mélangées** (r1 et r6) : un même groupe apparaît dans les deux. La release n'est pas une variable, mais certains événements (refus `not-requested-by-user`) n'existent qu'en r6.
- **Capacité non égalisée** entre l'agrégat et le GRU. L'ablation d'ordre compare un GRU à lui-même, ce qui contrôle la capacité pour la question de l'ordre, mais pas pour la comparaison GRU contre agrégat.
- **La référence tabulaire** utilise entraînement + validation (plus de labels) et sa propre sélection de C par validation croisée groupée : c'est une ligne de référence, pas une comparaison appariée.
- **Pas encore fait** : courbes d'apprentissage, Transformer compact (S11), généralisation par famille et transfert pour les modèles de séquence, effet sur le coût de revue.
- **Temps de calcul** : mesuré pendant qu'une collecte Ollama tournait en parallèle (non comparable entre modèles).
