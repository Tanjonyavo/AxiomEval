# TX-01 — Comparaison appariée à temps fixé

Depuis la racine d’AxiomEval, exécuter avec l’environnement du dépôt.

~~~powershell
.\.venv\Scripts\python.exe -m labs.comparaison_axm --plan labs/fixtures_axm/plan.json --executions labs/fixtures_axm/executions.csv
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_comparaison_axm.py -v
~~~

La commande émet du JSON. Ajouter `--sortie chemin.json` pour créer un nouveau fichier. Le laboratoire utilise le code d’empreinte et la validation textuelle d’AxiomEval.

## Contrat de l’expérience

- Le plan fixe les deux versions, l’oracle, le nombre de répétitions, les tâches attendues, leurs groupes et leurs familles, les partitions, les poids cibles, la marge, le risque alpha et la graine. Le CSV a une ligne par exécution et l’en-tête `execution,tache,version,repetition,issue,permission,cout_unites`.
- Chaque tâche prévue doit avoir ses deux versions à chaque répétition. Une tâche totalement absente, un doublon ou un groupe présent dans les deux partitions font échouer le contrôle. Les groupes sont imbriqués dans une seule famille. Chaque famille possède au moins deux groupes dans chaque partition.
- L’issue `SUCCES` vaut 1. `ECHEC` et `TIMEOUT` valent 0 selon ce protocole. Une ligne absente reste une erreur de collecte. La permission déclarée `OK`, `VIOLATION` ou `INCERTAINE` est rapportée séparément. Les coûts sont des unités synthétiques entières.
- Le contraste est candidate moins référence. Agréger les répétitions par tâche, puis donner un poids égal aux tâches d’un groupe et aux groupes d’une famille. Agréger ensuite les moyennes des familles avec les poids cibles gelés. Le pilote fournit les variances de planification. Seule la partition d’évaluation fournit le contraste principal.
- Le JSON contient les exécutions normalisées avec groupe, famille et partition, ainsi que les empreintes du plan et des lignes normalisées. L’empreinte permet de comparer les entrées entre relances. Pour attester que le plan a précédé la collecte, il faut conserver le plan dans un registre daté distinct.

## Interpréter la sortie

La borne unilatérale de Hoeffding suppose un horizon fixé et des groupes indépendants dans et entre familles. Pour inférer sur une population, vérifier aussi le mécanisme d’échantillonnage et la portée des poids. Un intervalle percentile bootstrap est fourni comme diagnostic approximatif. La non-infériorité à marge donnée exige que la borne inférieure dépasse strictement l’opposé de la marge.

Le plan d’allocation compare, au même nombre de groupes, la répartition équilibrée et la répartition entière qui minimise la variance prévue à partir du pilote, avec coûts égaux par groupe et au moins deux groupes par famille. Le budget de planification est distinct du coût observé des exécutions. La variance du pilote est une estimation et son gain n’est pas une économie mesurée.

Sur la fixture, l’évaluation contient 52 exécutions, 13 tâches et 12 groupes. L’écart pondéré est de **+12,5 points**, la borne inférieure à 95 % vaut **−59,6 points** et le résultat est **inconclusif** à marge de 5 points. Une violation déclarée reste visible séparément. Au budget de 24 groupes, le plan donne 19 groupes de routines et 5 cas limites, contre 12 et 12 pour la référence équilibrée.

Le laboratoire constitue une preuve synthétique hors ligne. Le passage à une collecte réelle et aux modèles mixtes est prévu dans les lots suivants.
