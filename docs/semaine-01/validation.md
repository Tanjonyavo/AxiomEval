# Validation du socle AxiomEval

Validation du 5 octobre 2026 — AxiomEval 0.1.0, démonstration synthétique de semaine 1.

## Résultats

| Vérification | Résultat |
|---|---|
| Python 3.14.5, PyYAML 6.0.3, code source | 21 tests réussis |
| Python 3.12.14, PyYAML 6.0.3, environnement neuf et wheel installé | 21 tests réussis |
| Construction du paquet | Wheel construit avec setuptools 84.0.0 |
| Commande installée | `axiomeval --version` affiche `AxiomEval 0.1.0` |
| Cohérence des dépendances | `pip check` sans erreur |

Les tests portent sur les contrats et le comportement du programme. Ils ne mesurent pas un modèle IA réel et ne constituent pas une validation de sécurité en production.

## Propriétés couvertes

- Configuration YAML : types, bornes, champs, clés uniques et chargeur sûr.
- Identifiants dépendant du contenu ; nouvelle identité d’exécution à chaque run.
- Quatre verdicts avec leurs codes de sortie : `PROMOTE/0`, `REJECT/10`, `INCOMPLETE/11`, `HOLD/12`.
- Priorité d’un constat critique confirmé par une preuve valide sur une autre preuve manquante.
- Preuves altérées, périmées, futures, mal liées, partielles ou dupliquées.
- Cohérence JSON/HTML, échappement des données HTML et refus d’écraser un rapport existant.
- Erreurs de configuration ou d’écriture signalées sans afficher le contenu brut du YAML.
- Dépendances des modèles indépendantes de la CLI et du rendu des rapports.

## Reproduire

Depuis la racine du dépôt après installation :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m axiomeval check-config
.\.venv\Scripts\python.exe -m axiomeval demo --case safe
.\.venv\Scripts\python.exe -m axiomeval demo --case violation
.\.venv\Scripts\python.exe -m axiomeval demo --case missing
.\.venv\Scripts\python.exe -m axiomeval demo --case uncertain
```

Les trois dernières démonstrations produisent volontairement des codes non nuls. Les UUID et horodatages changent entre les exécutions.

## Limites

Les preuves sont synthétiques et leur producteur est local. Il n’existe pas encore de collecteur authentifié, de modèle appris, de protocole statistique ni de service exposé. Le nombre de preuves exigées est un critère de complétude, pas un effectif statistique.

L’écriture des deux rapports n’est pas transactionnelle : une erreur disque peut laisser un premier fichier et provoquer une sortie avec le code 2.
