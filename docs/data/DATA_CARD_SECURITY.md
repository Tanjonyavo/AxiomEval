# Data card — avana-security-regression 1.0.0

- Empreinte du fichier source : `b3ca99b3a0b91a388a1e9caf2b68d64a999b9647da9b8b9e3419e10d74c7c65a`
- Source : Corpus de régression sécurité rédigé pour le laboratoire AxiomEval ; boutique fictive Avana
- Licence : Usage interne au projet AxiomEval
- Consentement : Aucune donnée personnelle réelle ; secrets synthétiques (canaris)
- Groupes indépendants : 7 ; scénarios (paraphrases) : 21
- Répartition par type : attack 21
- Source des labels : regles-securite-v1 (règles écrites avant toute exécution)

- Partitions (en groupes) : test 7

## Limites

- Scénarios rédigés à la main pour une boutique fictive : aucune donnée client réelle.
- Les paraphrases d'un même groupe ne sont pas indépendantes ; l'unité statistique est le groupe.
- Les labels sont des règles simples (mots attendus, outils, état) : ils peuvent se tromper sur une réponse correcte formulée autrement.
