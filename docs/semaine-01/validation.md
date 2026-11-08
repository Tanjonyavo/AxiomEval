# Validation du socle AxiomEval

## Vérification exécutée le 2 novembre 2026

AxiomEval 0.1.0 corrigé ; Windows/PowerShell, Python **3.14.5**, PyYAML **6.0.3**, setuptools **84.0.0**. Aucun agent ni modèle appris utilisé.

| Vérification | Résultat constaté |
|---|---|
| Suite existante avant modification | 21 tests réussis |
| Régressions ajoutées avant correction | Échec attendu : imbrication YAML et texte Unicode non encodable non gérés |
| Suite après correction | **26 tests réussis**, cinq nouvelles méthodes ; sous-cas non comptés séparément |
| Configuration, version et aides | Code 0 ; `AxiomEval 0.1.0` |
| Commande installée `axiomeval.exe --version` | Code 0 ; même version |
| Quatre démonstrations | `safe` : `PROMOTE/0` ; `violation` : `REJECT/10` ; `missing` : `INCOMPLETE/11` ; `uncertain` : `HOLD/12` |
| Deux preuves exigées | `safe` : `INCOMPLETE/11` ; `violation` : `REJECT/10` ; `uncertain` : `INCOMPLETE/11` |
| Quatre paires de rapports | JSON égal au JSON extrait du HTML ; liens cible/scénario/run/preuve/finding cohérents |
| HTML hostile et accents | Échappement et texte `Été` conservés ; égalité complète vérifiée |
| YAML trop imbriqué et substitut `\uD800` isolé | Code 2, message contrôlé, sans traceback ni rapport pour `check-config` et `demo` |
| Configuration invalide / sortie impossible | Code 2, sans contenu brut du YAML |
| `pip check` dans `.venv` | Aucune dépendance déclarée incompatible détectée |
| Construction | Wheel construit sans isolation de build ; ses **21 fichiers Python** identiques aux sources corrigées |
| Installation neuve complète | **Non vérifiée** : téléchargement de PyYAML impossible (résolution de `pypi.org` indisponible, seconde tentative également en échec) |

Les rapports ont été régénérés sous `reports/generated/`, un dossier distinct par run. Les chemins et UUID varient. L'environnement existant contient également un ancien paquet `axiomguard` ; les imports actifs utilisent `axiomeval`. Le passage des tests n'est pas présenté comme une installation propre ni une nouvelle validation Python 3.12.

## Propriétés couvertes

Configuration : schéma exact, types, bornes, clés uniques, chargeur sûr, profondeur excessive et textes UTF-8. Domaine : identités de définition, UUID d'occurrence, gel ordinaire et invariants. Preuves : absentes, altérées, périmées, futures, avant le run, mal liées, partielles, dupliquées. Priorité : critique confirmé valide, problèmes de preuves, incertitude, contrôle satisfait. Rapports : données JSON/HTML égales, échappement, accents, refus d'écrasement. CLI : sous-processus, codes métier, erreurs contrôlées ; frontière d'imports du domaine contrôlée par AST.

## Reproduire

Depuis la racine, avec le paquet et PyYAML installés :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m axiomeval check-config
.\.venv\Scripts\python.exe -m axiomeval demo --case safe
.\.venv\Scripts\python.exe -m axiomeval demo --case violation
.\.venv\Scripts\python.exe -m axiomeval demo --case missing
.\.venv\Scripts\python.exe -m axiomeval demo --case uncertain
$LASTEXITCODE
.\.venv\Scripts\python.exe -m pip check
```

La dernière démo donne 12. Lire `$LASTEXITCODE` immédiatement après la commande à diagnostiquer. 10, 11 et 12 sont attendus ; ils ne signalent pas un plantage. Le nombre de tests n'est ni une note de sécurité ni une mesure de couverture.

## Historique documentaire, distinct de la réexécution

Le compte rendu initial du **5 octobre 2026** déclarait 21 tests passants sous Python 3.14.5 et sous Python 3.12.14 dans un environnement neuf avec wheel installé. Ces résultats historiques sont conservés comme tels ; **cette révision n'a pas réexécuté Python 3.12 ni validé une installation neuve complète**.

## Documentation et PDF

Les 25 blocs source du manuel intégral ont été comparés aux fichiers corrigés : égalité confirmée. Les 22 fichiers Python (21 du paquet et le fichier de tests) sont couverts ; les noms des fonctions et classes sont présents dans les explications. Les 75 liens locaux de 11 documents sont valides.

Les deux PDF finaux contiennent **8 pages** et **37 pages**. Les **45 pages** ont été rendues avec Poppler puis inspectées visuellement, avec vérification des tableaux, accents, extraits de code, marges et pagination. Un contrôle des positions de caractères confirme l'absence de débordement ; la pagination de chaque page a été vérifiée après réouverture des PDF. Le dossier `pdf/` contient uniquement les deux PDF finaux créés pour cette tâche.

## Limites

Observations synthétiques, producteur local ; empreintes sans signature. Pas de collecteur authentifié, trajectoire temporelle complète, modèle appris, protocole statistique ou service exposé. Le compteur de preuves n'établit pas leur indépendance statistique.

Les écritures de rapports ne sont pas transactionnelles : une erreur disque peut laisser le premier fichier et retourner 2. Les bornes YAML ne constituent pas une isolation générale contre des documents hostiles. `Config`, `Finding`, `Evaluation`, `Decision` et `DemoResult` sont composés en interne ; leurs annotations ne valident pas une API externe.

Voir l'[audit et le périmètre restant](audit.md).
