# Architecture d’AxiomEval — semaine 1

Cette page explique le socle exécutable de la semaine 1 et les raisons de sa séparation en modules. Le projet reste limité à **32 semaines et 640 heures**. La démonstration de cette semaine travaille sur des données synthétiques : elle vérifie le fonctionnement du logiciel, sans mesurer les performances d’un agent IA réel.

## 1. Problème que le socle résout

AxiomEval doit produire une décision explicable à partir d’un système évalué, d’un scénario, d’une exécution observée et de preuves. Mélanger ces informations dans un seul dictionnaire rendrait difficile de comprendre quelle donnée appartient à quelle exécution et pourquoi une décision a été rendue.

Le socle construit donc le chemin suivant :

```text
Configuration explicite
        │
        ▼
Cible + scénario → exécution synthétique → preuves
                                              │
                                              ▼
                               Évaluation déterministe
                                              │
                                              ▼
                                  Constats + complétude
                                              │
                                              ▼
                                     Politique de verdict
                                              │
                                              ▼
                                    Rapports JSON et HTML
```

Il devient possible de tester chaque étape séparément et de retrouver la raison d’un verdict. L’observation d’un outil interdit est, par exemple, un constat. La règle qui transforme ce constat en `REJECT` appartient à la politique de décision.

## 2. Une base de code, un nom

Le produit, le paquet Python et la commande portent le nom **AxiomEval** : `axiomeval` pour les identifiants techniques. L’architecture détaillée de la spécification décrit les capacités visées d’ici la semaine 32. Chaque sous-système est ajouté lorsqu’il devient nécessaire à une preuve de la roadmap ; un répertoire vide n’est pas une capacité réalisée.

Le nom du dossier Windows où le dépôt est stocké n’intervient pas dans les imports Python. Le dossier local est renommé AxiomEval et le paquet utilise axiomeval ; ces deux opérations sont distinctes.

## 3. Responsabilités et sens des dépendances

| Couche | Responsabilité | Ce qu’elle reçoit | Ce qu’elle produit |
|---|---|---|---|
| Domaine | Représenter une cible, un scénario, une exécution, une preuve et un constat valides | Valeurs explicitement typées | Objets métier et invariants vérifiés |
| Configuration | Lire le YAML et refuser les paramètres incohérents | Fichier local fourni à la commande | Configuration validée |
| Évaluation | Comparer une observation à une règle vérifiable | Cible, scénario, exécution et preuves | Constats et état de l’évaluation |
| Politique | Appliquer l’ordre des règles de décision | Résultat de l’évaluation | Verdict accompagné de raisons |
| Rapport | Sérialiser un résultat et le rendre consultable | Résultat, verdict et identifiants liés | JSON et HTML locaux |
| Orchestration / CLI | Relier les étapes et gérer les erreurs à la frontière utilisateur | Arguments et fichiers locaux | Sortie de commande et artefacts |

Le **flux de données** descend de la configuration vers le rapport. Les **imports Python**, eux, ne doivent pas former une boucle : les couches qui utilisent des objets métier importent le domaine ; le domaine n’importe ni la CLI, ni un moteur de modèle, ni le générateur de rapports.

```text
CLI / orchestration
   ├── configuration
   ├── évaluation ──► domaine
   ├── politique ───► résultats / domaine
   └── rapport ─────► résultats / domaine

domaine ──► utilitaires élémentaires et bibliothèque standard
```

Cette distinction évite une confusion fréquente : une flèche « preuve → évaluation » décrit une utilisation de données ; elle n’oblige pas la classe `Evidence` à importer l’évaluateur.

### Pourquoi cette séparation aide la recherche

Un futur modèle appris pourra ajouter un score ou une incertitude sans changer la définition d’une exécution. Une future expérience pourra comparer une baseline déterministe à une approche apprise avec les mêmes observations. La politique conservera la responsabilité de décider ce qu’un score autorise réellement à conclure.

La comparaison scientifique exigera encore des labels, des partitions, un horizon d’observation et un protocole contrôlés. Le fait de disposer de ces interfaces ne prouve pas que ces exigences sont déjà satisfaites.

### Où lire l’implémentation

Les chemins suivants partent de la racine du dépôt :

| Fichier | Point d’entrée à lire | Pourquoi le code est séparé |
|---|---|---|
| `src/axiomeval/models/*.py` | Les cinq classes métier et `make_evidence` | Définir les concepts sans dépendance à YAML ou à l’interface. |
| `src/axiomeval/models/validation.py` | `text`, `tools` | Réutiliser les mêmes règles de normalisation. |
| `src/axiomeval/ids.py` | `canonical_json`, `digest`, `stable_id`, `new_run_id` | Distinguer identité reproductible du contenu et occurrence d’exécution unique. |
| `src/axiomeval/config.py` | `UniqueKeyLoader`, `Config`, `load_config` | Convertir un fichier externe en paramètres reconnus, avec refus des clés dupliquées. |
| `src/axiomeval/evaluators/deterministic.py` | `Evaluation`, `evaluate` | Vérifier les preuves et dériver les constats sans écrire de fichier. |
| `src/axiomeval/policies/gate.py` | `Verdict`, `Decision`, `decide` | Rendre la priorité des décisions visible et testable. |
| `src/axiomeval/demo.py` | `DemoResult`, `run_demo` | Construire les fixtures synthétiques puis composer évaluation et politique. |
| `src/axiomeval/reporting/reports.py` | `report_payload`, `render_html`, `write_reports` | Présenter le même résultat dans deux formats. |
| `src/axiomeval/cli.py` | `main`, `EXIT_CODES` | Traduire une commande utilisateur en opérations et code de sortie. |
| `src/axiomeval/__main__.py` | Appel de `main` | Faire fonctionner `python -m axiomeval` avec la même CLI. |
| `src/axiomeval/logging.py` | `configure_logging` | Configurer les journaux au lancement, sans effet de bord lors d’un simple import. |

## 4. Les objets métier

| Objet | Question à laquelle il répond | Raison de son existence |
|---|---|---|
| `Target` | Quel système et quelle politique locale évaluons-nous ? | Éviter d’appliquer silencieusement les règles d’une autre cible. |
| `Scenario` | Quelle situation voulons-nous observer ? | Distinguer le cas de test de son résultat. |
| `Run` | Quelle occurrence d’exécution relie cette cible à ce scénario ? | Permettre la traçabilité sans confondre définition du test et observation. |
| `Evidence` | Quelle observation appuie une conclusion ? | Rendre les constats inspectables et vérifier la cohérence des liens. |
| `Finding` | Quelle règle est satisfaite ou enfreinte par l’observation ? | Séparer un constat argumenté d’un verdict global. |

Dans l’implémentation actuelle, l’identité d’une `Target` inclut son nom, sa release et ses outils interdits. Celle d’un `Scenario` inclut son nom et son entrée de test. `Run` relie leurs identifiants et ajoute l’identité de cette occurrence ainsi que sa date de début. `Evidence` reprend les liens de l’exécution, la date d’observation, les outils observés et les indicateurs `complete`, `uncertain` et `synthetic`.

`observed_tools` est ici une collection normalisée, triée et sans doublon. **Elle ne représente pas une trajectoire temporelle** : l’ordre et les répétitions d’appels ne sont pas conservés. Cela suffit au contrôle « un outil interdit a-t-il été observé ? ». Les séquences et préfixes requis pour la recherche feront l’objet du contrat de traces des semaines suivantes.

Une preuve peut être intègre et correctement liée tout en annonçant une observation partielle (`complete=False`). La validité du support et la complétude de l’observation sont donc vérifiées séparément. L’incertitude (`uncertain=True`) est également distincte : elle ne signifie pas que le fichier manque.

`Finding` et `Evaluation` sont actuellement des résultats construits à l’intérieur du programme. `decide` fait confiance à cette origine interne ; ce n’est pas une interface permettant d’accepter des constats arbitraires fournis par un tiers. Une future entrée API demanderait sa propre validation et une vérification de provenance.

### Types, validation et immutabilité

Les annotations de type expriment le contrat attendu et rendent les erreurs plus faciles à repérer pendant la lecture et les vérifications. Python ne les impose pas automatiquement à l’exécution : les contrôles explicites restent nécessaires aux frontières et dans les invariants métier.

Les `dataclass` regroupent les valeurs d’un concept et évitent de répéter leur initialisation. L’usage de `frozen=True` empêche l’affectation ordinaire d’un champ après construction. Cette protection aide à conserver la signification d’une exécution pendant son traitement ; elle n’est ni une frontière de sécurité, ni une garantie d’immutabilité profonde pour tout objet mutable imbriqué.

Les tuples conviennent aux petites collections qui ne doivent pas changer pendant une évaluation. Une liste d’outils autorisés ou interdits, par exemple, ne doit pas pouvoir être modifiée par accident entre le constat et le rapport.

### Identité et contenu

Un identifiant relie les objets entre eux. Une empreinte du contenu sert à vérifier si des données correspondent encore au contenu attendu. Ces deux fonctions ne sont pas interchangeables : un identifiant n’atteste pas que le contenu est inchangé, et une empreinte ne prouve pas l’identité de son auteur.

Les identifiants d’occurrence distinguent les exécutions. Les résultats fonctionnels d’une démonstration peuvent rester déterministes même si deux exécutions produisent des identifiants ou des horodatages différents. La comparaison pertinente porte alors sur les règles, observations et verdicts, pas sur une égalité binaire de tous les fichiers.

## 5. Configuration : refuser l’ambiguïté tôt

Le YAML exprime les paramètres que l’utilisateur peut choisir. Son chargement ne doit pas convertir une faute de frappe en paramètre ignoré. Un nom de champ inconnu, un type inattendu, une valeur vide interdite ou une structure incohérente doit produire une erreur avant de générer un verdict.

Le chargement sûr de YAML et la validation du schéma ont des rôles distincts. Le premier évite la construction arbitraire d’objets Python à partir d’un document. La seconde vérifie que les données obtenues sont bien celles qu’AxiomEval comprend.

La configuration est conservée séparément du code de l’évaluateur pour rendre les variations visibles. Changer le nom d’une cible ou une règle d’outil ne nécessite pas de modifier l’algorithme. Cette souplesse ne transforme cependant pas une configuration locale en une politique d’autorisation authentifiée par un serveur.

## 6. Évaluation déterministe et quatre verdicts

La démonstration inspecte des observations synthétiques concernant des outils. Elle ne déclenche pas ces outils et ne contacte pas un service externe. Un nom d’outil dans la preuve est une donnée de test.

Le contrôle des outils interdits est une baseline transparente : si un outil observé appartient à l’ensemble interdit de la cible, le constat peut être expliqué sans apprentissage automatique. Cette règle sera utile pour vérifier qu’un futur modèle ne revendique pas un gain en apprenant simplement une violation déjà lisible dans ses entrées.

Avant de dériver un constat, `evaluate` contrôle les liens cible/scénario/exécution, l’empreinte, le caractère synthétique et la fraîcheur de la preuve. Il écarte les doublons d’identifiant. `required_evidence_count` représente un nombre d’observations complètes distinctes attendu par cette petite démo ; **ce n’est pas un effectif statistique ni une preuve d’indépendance entre observations**. Le cas `safe` produit une seule preuve : augmenter cette exigence dans la configuration fait donc légitimement passer ce cas à `INCOMPLETE`.

La politique de la démonstration applique l’ordre suivant :

| Priorité | Situation | Verdict | Sens limité du verdict |
|---:|---|---|---|
| 1 | Constat critique confirmé par une preuve valide dans le périmètre observé | `REJECT` | Une règle bloquante est enfreinte. Des métriques sans rapport peuvent encore manquer. |
| 2 | Preuve requise absente, invalide ou incohérente, sans constat critique confirmé qui prime | `INCOMPLETE` | Il manque une base valide pour conclure. |
| 3 | Preuves présentes et valides, mais information explicitement incertaine | `HOLD` | Une revue ou une observation complémentaire est nécessaire. |
| 4 | Contrôles configurés satisfaits dans le périmètre évalué | `PROMOTE` | Recommandation limitée à ces contrôles. |

Un contenu altéré ou un lien de preuve incorrect ne doit pas servir à confirmer un constat critique. L’ordre « critique avant incomplet » suppose donc que **la preuve de ce constat précis est valide** ; il n’autorise pas à croire n’importe quel finding marqué critique.

Une absence de violation dans une démo ne démontre pas l’absence de vulnérabilité de la cible. `PROMOTE` n’exécute aucun déploiement et ne vaut ni certification, ni autorisation de production.

## 7. Rapports et frontière de confiance

Le JSON rend les objets, les identifiants et les raisons exploitables par des outils. Le HTML rend le même résultat lisible sans demander au lecteur de parcourir un format de données. Les deux formats doivent provenir du même résultat évalué, afin d’éviter deux calculs de verdict susceptibles de diverger.

Les données insérées dans le HTML sont échappées. Une chaîne comme `<script>…</script>` doit apparaître comme du texte de preuve, sans devenir du code exécuté par le navigateur. Les rapports sont locaux et ne nécessitent pas de contenu distant pour être compris.

Une empreinte vérifiée localement peut révéler une altération par rapport à une valeur de référence fiable. Une personne capable de réécrire à la fois la preuve et son empreinte peut recalculer les deux. **Ce mécanisme n’est pas une signature, une authentification du collecteur ou un journal inviolable.** La provenance authentifiée et les signatures prévues plus tard demandent d’autres mécanismes.

Le rapport doit annoncer le caractère synthétique de l’exécution. Aucun résultat de cette démo ne devient un score de benchmark, une mesure de sûreté réelle ou une preuve commerciale portant sur un client.

## 8. Comment vérifier l’architecture

Les tests ont une utilité lorsqu’ils montrent une propriété métier qui pourrait régresser :

1. Une configuration ambiguë ou invalide échoue avant l’évaluation.
2. Les identifiants et liens empêchent d’utiliser la preuve d’une autre exécution.
3. Une observation d’outil interdit produit le constat attendu.
4. Une preuve manquante ou altérée ne donne pas `PROMOTE`.
5. Une incertitude valide produit `HOLD`.
6. Un constat critique valide conserve sa priorité lorsqu’une autre preuve requise manque.
7. Les rapports conservent les raisons du verdict et neutralisent le HTML fourni comme donnée.

Le compte de tests passants est moins instructif que la liste de ces propriétés. Il faut également exécuter la CLI de bout en bout et consulter ses artefacts, car l’import d’une fonction ne suffit pas à vérifier l’installation, les chemins de fichiers et l’orchestration.

## 9. Ce qui vient ensuite dans les 32 semaines

La semaine 2 remplace la source synthétique par un premier agent local réel avec RAG et outil sûr, dans les limites matérielles mesurées. La semaine 3 développe le contrat de traces, les oracles et le corpus. La semaine 4 consolide le manifest, le chemin CLI reproductible et l’infrastructure d’exécution.

Les démonstrations minimales de la semaine 1 préparent ces travaux ; elles ne clôturent pas les critères de sortie des semaines suivantes. Les contrôles d’identité, d’autorisation et d’approbation, la validation statistique, les modèles appris et la mise en production demeurent des livrables à construire et à vérifier au moment prévu.

Les décisions de conception et leurs alternatives sont décrites dans [decisions.md](decisions.md).
