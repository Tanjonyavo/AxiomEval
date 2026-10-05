# Décisions de conception — semaine 1

Ces décisions concernent le socle actuel d’AxiomEval. Elles ne déclarent pas achevées les capacités futures de la spécification. Elles sont prises pour un projet de **32 semaines / 640 heures**, avec une implémentation cohérente et des preuves contrôlables.

## D01 — Un nom et un paquet : AxiomEval

**Contexte.** Le produit était décrit sous le nom AxiomEval, tandis que du code et certains documents utilisaient un ancien nom. Cette divergence compliquait les imports, l’installation et la lecture du périmètre.

**Décision.** Employer `AxiomEval` dans le texte et `axiomeval` dans le paquet Python, la commande et les métadonnées du projet. Corriger les références actives ensemble.

**Alternatives examinées.** Conserver deux noms aurait imposé d’expliquer une séparation qui n’existe pas dans le produit. Maintenir un paquet de compatibilité serait justifié par de vrais consommateurs de l’ancienne interface, mais ajoute aujourd’hui une deuxième surface à maintenir sans besoin démontré.

**Conséquences.** Les anciens exemples d’import doivent être mis à jour. Le dossier local est également renommé AxiomEval ; les imports restent indépendants du chemin Windows. Les sauvegardes historiques conservent leur rôle de trace et ne sont pas des instructions actives.

**Réexamen.** Si un consommateur réel dépend d’une ancienne version publiée, définir une migration explicite et limitée dans le temps avant de réintroduire une compatibilité.

## D02 — Un programme modulaire dans un seul processus

**Contexte.** Le périmètre final comprend recherche, évaluation, sécurité, rapports et interface logicielle. Construire immédiatement tous ces sous-systèmes multiplierait les dépendances et le travail sans produire de meilleure preuve en semaine 1.

**Décision.** Conserver un paquet local et séparer les responsabilités : domaine, configuration, évaluation, politique, rapports et CLI. Le domaine reste indépendant des entrées/sorties. L’orchestration compose les fonctions.

**Alternatives examinées.** Un script unique serait plus court au départ, mais mélangerait rapidement lecture YAML, règles métier et rendu. Des microservices ajouteraient réseau, déploiement et gestion de pannes avant qu’une séparation de processus soit nécessaire.

**Conséquences.** Les règles peuvent être testées sans service externe. Une future source de traces ou un modèle appris pourra évoluer à sa frontière, sans transformer le rendu HTML en moteur de décision. La séparation logique n’apporte aucune isolation de sécurité entre processus puisqu’il n’y en a qu’un.

**Réexamen.** Introduire une séparation de processus seulement si une contrainte mesurée de charge, d’isolation ou de déploiement la justifie dans le budget du projet.

## D03 — Contrats explicites et configuration stricte

**Contexte.** Une évaluation perd sa valeur si les données d’une autre exécution sont associées au résultat, si une faute de configuration est ignorée ou si une observation change pendant la décision.

**Décision.** Utiliser de petites `dataclass` typées pour `Target`, `Scenario`, `Run`, `Evidence` et `Finding`, vérifier les invariants et privilégier des valeurs stables pendant le traitement. Charger le YAML avec un chargeur sûr, puis valider le contenu reconnu par AxiomEval. Distinguer identité des objets et intégrité du contenu.

**Alternatives examinées.** Des dictionnaires libres reporteraient la détection des erreurs jusqu’aux consommateurs. Un framework complet de validation pourrait devenir utile avec une API et des schémas plus complexes, mais n’est pas requis pour ces contrats locaux limités.

**Conséquences.** L’ajout d’un paramètre demande un changement explicite de son contrat et de sa validation. Les annotations ne remplacent pas les contrôles à l’exécution. `frozen=True` ne protège pas un objet d’un processus hostile. Une empreinte de contenu détecte certains écarts, mais ne prouve ni l’auteur ni l’authenticité d’une preuve.

**Réexamen.** Revoir le choix de bibliothèque lorsque l’API versionnée et la persistance demanderont génération de schémas, migration ou validation plus riche. Préserver les invariants métier lors de cette évolution.

## D04 — Une baseline déterministe et une démo explicitement synthétique

**Contexte.** Le projet vise des travaux IA avancés, mais la recherche a besoin d’un chemin logiciel fiable et d’une baseline interprétable. Un score appris ne doit pas être présenté comme une contribution s’il recopie simplement une règle observable.

**Décision.** Commencer par un contrôle des outils interdits et quatre cas synthétiques illustrant `PROMOTE`, `REJECT`, `INCOMPLETE` et `HOLD`. Calculer le verdict une seule fois, avec des raisons, puis le représenter en JSON et HTML. Une preuve critique valide prime ; un manque de preuve ne devient pas une réussite. Les données insérées dans le HTML sont échappées.

**Alternatives examinées.** Une intégration immédiate de modèle ajouterait matériel, variabilité et dépendances à un problème d’abord logiciel. Un verdict binaire réussite/échec confondrait violation, absence d’information et incertitude. Une démo présentée comme un test réel donnerait une force injustifiée à des observations fabriquées.

**Conséquences.** La semaine 1 vérifie des contrats et une logique de décision ; elle ne mesure aucune compétence d’un modèle. La semaine 2 introduit le vrai agent local. Les semaines de recherche compareront les modèles à cette catégorie de baseline sur des données et horizons contrôlés. Aucun verdict ne déclenche un déploiement ni un outil externe.

**Réexamen.** Faire évoluer le contrat d’évaluation lorsqu’apparaîtront des traces réelles, des contrôles statistiques et des scores calibrés. Conserver la distinction entre observation, constat, décision et présentation.
