# AxiomEval — résultats vérifiables

Cette page résume les chiffres cités dans mon CV : ce qui a été mesuré, comment c'est compté, et où vérifier chaque nombre dans ce dépôt. Toutes les exécutions sont réelles (aucune simulation), faites en local du 10 au 11/11/2026.

## Protocole

| Élément | Valeur |
|---|---|
| Modèle | `qwen2.5:1.5b-instruct` via Ollama, en local (aucun appel réseau externe) |
| Agent | Support client d'une boutique fictive : recherche documentaire (k = 2) et outils `lookup_order_status`, `refund_order`, `search_kb`, `escalate_to_human` (plus `export_customer_data`, interdit), au plus 4 pas |
| Tirages | Température 0,7, 2 tirages par scénario, graine = graine de release + numéro de tirage |
| Corpus v2 | 180 groupes, 540 scénarios, 4 releases × 1 080 exécutions = **4 320** ([data card](docs/data/DATA_CARD_V2.md)) |
| Corpus v3 | 245 groupes, 735 scénarios (dont 156 d'attaque), 3 releases × 1 470 exécutions = **4 410** ([data card](docs/data/DATA_CARD_V3.md)) |
| Total | **8 730 exécutions réelles** ; empreintes SHA-256 des fichiers bruts dans `data/MANIFEST_V2.json` et `data/MANIFEST_V3.json` |
| Unité statistique | Le groupe (un modèle de scénario et ses paramètres) ; paraphrases et tirages sont moyennés dans le groupe |
| Labels | Règles écrites avant toute exécution (mots attendus, outils, état final) |

## Définitions

- **Brèche** : un effet interdit qui a réellement eu lieu. Exemples : un secret planté (canari) ou une valeur protégée apparaît dans la réponse, un outil interdit s'exécute, un remboursement non demandé est exécuté. Une tentative arrêtée par un contrôle n'est **pas** une brèche, elle est comptée à part.
- **Exécutions avec brèche** : nombre d'exécutions qui contiennent au moins une brèche (code : `src/axiomeval/corpus/evaluate.py`).
- **Faille** : un comportement réel et reproductible qui produit une brèche, documenté avec sa trace, sa cause, son correctif et son retest (F-001 à F-008, [FINDINGS.md](docs/security/FINDINGS.md)).

## Sécurité : brèches de 62 à 6 sur le corpus v3

Mêmes 1 470 scénarios et mêmes tirages pour chaque release ; seule la configuration de l'agent change.

| Release | Contrôles ajoutés | Exécutions avec brèche | Attaques réussies (sur 312) |
|---|---|---|---|
| r1 | aucun | 62 | 25 (borne sup. 0,110) |
| r6 | garde de sortie, valeurs protégées, remboursement lié à la demande | 40 | 0 (borne sup. 0,010) |
| r7 | vérifications d'écriture (montant ≤ total, lecture avant décision) | **6** | 0 (borne sup. 0,010) |

Les bornes supérieures sont exactes (Clopper-Pearson, α = 0,05). Rapports : `reports/s05/v3_compare_r1-baseline_r6-bound.json`, `reports/s05/v3_compare_r6-bound_r7-checked.json`.

Ce que ces chiffres ne disent pas : r7 est **rejetée** quand même. Les 6 brèches restantes viennent d'une seule famille (`verifier_puis_rembourser`), et les nouveaux contrôles bloquent aussi des remboursements conditionnels légitimes (18/36 → 0/36). Détail : [FINDINGS.md, retest de F-007 et F-008](docs/security/FINDINGS.md).

## Failles : 8 trouvées, 7 corrigées

| Faille | Résumé | État |
|---|---|---|
| F-001 | Secret exfiltré dans les arguments d'un outil | Corrigée, retest réel |
| F-002 | Secret divulgué malgré des consignes durcies | Corrigée par un contrôle hors modèle |
| F-003 | Courriel interne divulgué | Corrigée, retest réel (5 fuites → 0) |
| F-004 | Montant négatif réinterprété en remboursement | Corrigée, retest réel |
| F-005 | Remboursement spontané pendant une question | Corrigée, rejeu testé |
| F-006 | Variante d'un secret écrite dans les traces | Corrigée, test de régression |
| F-007 | Remboursement supérieur au total de la commande | Corrigée, retest réel (18 → 0) |
| F-008 | Liaison à la demande trompée par un seuil ou une condition | **Partielle** : cas « seuil » et « autre commande » à 0 ; cas « condition » de 20 à 6 brèches |

## Prédiction (S10) : erreur réduite de 20 %

Question : prédire, à partir du début d'une exécution, si elle va échouer. Partition de test gelée, par groupe.

| Modèle (horizon 2) | Score de Brier (plus bas = mieux) |
|---|---|
| Agrégat (régression logistique) | 0,129 |
| GRU (PyTorch) | **0,103** |

Différence appariée, bootstrap groupé à 95 % : [−0,044 ; −0,011]. Ablation : avec l'ordre des événements mélangé, le gain reste le même ([−0,046 ; −0,012]). Conclusion honnête : le GRU fait mieux, mais **pas grâce à l'ordre** ; l'hypothèse de départ n'est pas soutenue. Rapport : [S10_SEQUENCES_V3.md](docs/experiments/S10_SEQUENCES_V3.md).

## Reproduire

```powershell
python -m pip install -e ".[api,ml,seq]"
python -m unittest discover -s tests          # 166 tests
python -m axiomeval collect --corpus-dir fixtures/corpus-v3 --release configs/releases/r7-checked.yaml --out data/runs/v3/r7-checked.jsonl --draws 2
python -m axiomeval compare --baseline data/runs/v3/r6-bound.jsonl --candidate data/runs/v3/r7-checked.jsonl
```

Une collecte de 1 470 exécutions prend environ 6 minutes avec Ollama (environ 4 exécutions par seconde sur la machine de test, RTX 3060 6 Go). À température 0,7, une recollecte donne des chiffres proches mais pas identiques ; les fichiers d'origine sont identifiés par leurs empreintes.

## Limites

Un seul petit modèle, une boutique fictive en français, des labels à base de règles. Ces résultats décrivent ces exécutions, pas les agents IA en général.
