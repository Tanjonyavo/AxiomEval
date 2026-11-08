# Audit de la semaine 1 - 2 novembre 2026

## Conclusion de périmètre

Le socle technique est implémenté et testé en laboratoire après deux corrections ciblées. **La semaine 1 complète n'est pas déclarée entièrement acquise** : éligibilité individuelle, appropriation du code et validations extérieures restent ouvertes. Aucun modèle IA réel évalué, aucun entraînement, aucun client ou directeur contacté.

Références lues : spécification V2 (notamment §0, §9, §38, §55, §60 et critères associés), roadmap 32 semaines, README principal, manuel intégral, architecture/décisions, documents S1 de cadrage/recherche/admission/commercial/validation, 21 fichiers Python du paquet, tests, YAML et métadonnées. Aucun `AGENTS.md` applicable trouvé dans le dépôt et ses ancêtres contrôlés.

## Prévu, implémenté, vérifié, restant

| Prévu | Implémenté / présent | Vérifié dans cet audit | Restant à faire |
|---|---|---|---|
| S1 : cadrage | Objectif, identité, budget 32 semaines / 640 h et périmètre rédigés | Cohérence du périmètre | Temps réel et vélocité personnelle à mesurer |
| S1 : architecture, une implémentation | Paquet local, modèles, configuration, démo et rapports | Tests, CLI, séparation des imports métier | Robustesse de production aux jalons prévus |
| S1 : question et littérature | Question falsifiable, horizon futur, baselines, huit notices et protocole exploratoire | Préparation distinguée des expériences | Lectures approfondies, originalité, oracles/données et expériences |
| S1 : notes/prérequis/deadlines | Matrice d'admission datée du 5 octobre | Inconnues personnelles et distinction ouverture/clôture visibles | Relevé/cours/statut, programmes et encadrement ; sources à réactualiser |
| S1 : ICP et offre préparée | Problème hypothétique, offre, grille et indicateurs | Préparation distinguée de vente et pilote | Demande et coûts réels à observer ; aucun contact ici |
| S1 : comprendre et défendre | Manuels et exercices, deux PDF après correction | Copies de sources et commandes contrôlées | Restitution et modifications pratiques par l'étudiant |
| S2 : agent local + RAG + outil sûr | **Non implémenté** | Aucun appel de modèle ou d'outil dans le chemin S1 | Matériel/licences et trajectoires réelles |
| S3-S6 et suite | Plans documentés | Aucune capacité future déclarée livrée | Trace/privacy/oracles, manifest/splits/uv/CI, statistique, authz, puis modèles |

Les notices externes de littérature, admission et marché restent des documents datés : cet audit du code ne réatteste pas leurs pages web au 2 novembre. Leur présence ne prouve ni admissibilité, ni performance, ni vente.

## Problèmes confirmés et corrections

| Problème et effet | Correction | Vérification | Limite |
|---|---|---|---|
| YAML de 1 500 niveaux, inférieur à la taille maximale : `RecursionError`, traceback, code 1 | `load_config` traduit aussi `RecursionError` du parseur en `ConfigurationError` | Régression avant/après ; `check-config`/`demo` : code 2, sans rapport ni traceback | Pas de profondeur maximale contractuelle ni d'isolation générale |
| Échappement `\uD800` : substitut isolé accepté ; erreur au hash pour le nom, validation à tort ou erreur d'écriture pour l'environnement | `models.validation.text` exige un texte encodable UTF-8 ; erreur métier traduite en erreur de configuration | Champs texte et outils, domaine et CLI ; accents conservés | Encodage seulement, pas de redaction ni d'authentification |
| Le test de cohérence JSON/HTML vérifiait surtout la présence du verdict | Test renforcé avec extraction du `<pre>` par `HTMLParser` puis égalité JSON complète, accents compris | Test et quatre paires de rapports | HTML local simple |
| Priorité `INCOMPLETE` sur `HOLD` sans test dédié | Cas incertain avec deux preuves requises testé | `INCOMPLETE` dans la suite et la CLI | Aucune incertitude statistique calculée |
| Copies de code et résultats historiques à réviser | Manuel synchronisé, explications, 26 tests et date actualisés ; audit/PDF liés | 25 blocs source comparés et liens locaux contrôlés | À réviser après chaque changement de code |

## Architecture, objets et confiance

CLI : arguments et erreurs ; chargeur : YAML vers `Config` ; `run_demo` : `Run` et `Evidence`, puis `evaluate` et `decide` ; rapports : décision déjà calculée vers JSON/HTML. Les modèles n'ont pas de dépendance d'entrées/sorties. `logging.py` prépare un format, sans journal d'audit complet.

`Target` identifie nom/release/règles ; `Scenario` nom/entrée ; `Run` une occurrence avec UUID et heure ; `Evidence` contient ses trois liens, observation et empreinte ; `Finding` référence sa preuve contrôlée ; `Evaluation` rassemble constats/problèmes ; `Decision` porte verdict/raisons. Les définitions ont une identité stable pour la représentation canonique retenue ; UUID, heure et identifiants de preuve changent entre runs.

Une preuve est contrôlée avant de soutenir un constat. Une observation valide partielle peut déjà confirmer un outil interdit : `REJECT` prime ; sinon les problèmes de complétude priment sur l'incertitude. `PROMOTE` ne déploie rien. Les outils sont triés, sans ordre temporel ni répétitions : aucune trajectoire séquentielle complète.

Les sorties internes ne sont pas une entrée tierce authentifiée. Le gel évite les modifications accidentelles, sans résister à du code du même processus. Un hash recalculable ne prouve pas son auteur. Le scénario brut figure dans le rapport : données synthétiques exclusivement à ce stade.

## Vérifications exécutées

21 tests existants passants avant travail ; nouveaux tests reproduisant les défauts avant correction ; **26 tests passants après**. Quatre démos, variantes à deux preuves, aides, version, commande installée, erreurs, relations et égalité JSON/HTML vérifiées. `pip check` passe. Wheel construit, 21 fichiers Python identiques aux sources corrigées. Installation neuve complète et nouvelle exécution Python 3.12 **non vérifiées** : téléchargement indisponible. Détails et commandes dans [validation.md](validation.md).

## Passage à S2

Commencer par agent local, RAG et outil sûr, avec CPU/RAM/latence/temps et droits du modèle documentés. Définir la provenance des observations réelles ; désactiver le drapeau synthétique seul ne suffit pas. Garder les fixtures comme tests de contrats. Ne pas déclarer achevés les traces S3, manifest/uv/CI S4 ou statistiques S5.

Supports : [01 - Résumé](pdf/01-resume-semaine-1.pdf) et [02 - Guide technique](pdf/02-comprendre-maitriser-semaine-1.pdf). Leur lecture ne démontre pas à elle seule la maîtrise : exécuter, prévoir et modifier le code en expliquant les résultats.
