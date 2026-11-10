# src/axiomeval/corpus/splits.py

**Rôle.** Répartir les **groupes** de scénarios entre entraînement, validation, calibration et test, de façon déterministe, puis geler cette répartition (S4, lot P03, spec §12.4). Entrée : le corpus. Sortie : dictionnaire `groupe → partition`, et le fichier `fixtures/corpus/split.json`. Utilisé par `cli_corpus` (commande `corpus`) et par la collecte. Testé par `tests/test_corpus_p03_p04.py::SplitTests`. Lien AXM : 04-C01 (« chaque groupe dans une seule partition »).

## L1-L6
**Quoi.** Docstring. Point clé : la répartition ne dépend que des identifiants de groupe, de la graine et des proportions, **jamais des résultats**. Choisir le test après avoir vu les performances serait une fuite de sélection.

## L7-L13
**Quoi.** Imports : `hashlib` (ordre pseudo-aléatoire reproductible), `json`, `Path`, le type `Corpus`, l'erreur de validation et `digest` (SHA-256 du JSON canonique, `ids.py`).

## L15-L16
**Quoi.** Les quatre partitions dans l'ordre et les proportions par défaut (55/15/15/15 %). La calibration est séparée de la validation car la calibration de probabilités (S15) et la prédiction conforme (S16) exigent des données jamais utilisées pour choisir le modèle.

## L19-L20
**Quoi.** `_rank` : empreinte de « graine:groupe ». Trier par cette empreinte revient à mélanger les groupes de façon pseudo-aléatoire mais **reproductible** sur n'importe quelle machine (contrairement à `random.shuffle` dont l'algorithme peut changer entre versions de Python).

## L23-L26
**Quoi.** Vérifie que les proportions couvrent exactement les quatre partitions, somment à 1 (à 10⁻⁹ près, tolérance de l'arithmétique flottante) et ne sont pas négatives. L'option `--test-only` (corpus sécurité) passe `test = 1`, le reste à 0.

## L27-L31
**Quoi.** Liste les groupes par type (`information`, `account`, `action`, `attack`), sans doublon, dans l'ordre d'apparition. **Pourquoi par type (stratification).** Sinon, par hasard, tous les groupes d'attaque pourraient tomber en entraînement et le test ne contiendrait aucune attaque.

## L32-L43
**Quoi.** Pour chaque type : tri par empreinte, puis découpe par proportions cumulées. `round(cumulative * n)` donne la fin de chaque tranche ; la dernière partition prend tout le reste (`end = n`) pour qu'aucun groupe ne soit oublié par un arrondi. **Exemple réel.** 27 groupes → train 14, validation 5, calibration 4, test 4. **Si on remplaçait `round` par `int`.** Les petites partitions perdraient des groupes au profit du test. **Limite.** Avec 3 à 9 groupes par type, certaines partitions d'un type peuvent être vides.

## L46-L51
**Quoi.** Gel : on écrit l'identifiant et l'empreinte du corpus, la graine, les partitions triées, puis l'empreinte de tout cela. **Pourquoi l'empreinte du corpus.** Si l'on modifie un scénario, le corpus change d'empreinte et l'ancienne répartition est refusée (L60).

## L54-L65
**Quoi.** Relecture avec trois refus : fichier modifié après gel (l'empreinte recalculée ne correspond plus) ; répartition d'une autre version du corpus ; groupes manquants, en trop, ou partition inconnue. **Test.** `test_frozen_split_detects_tampering_and_other_corpus` déplace un groupe de partition et vérifie le refus ; `test_committed_split_matches_corpus` vérifie le fichier versionné. **Limite.** L'empreinte détecte une modification ; elle n'empêche pas quelqu'un de recalculer une nouvelle empreinte. La garantie réelle vient de l'historique Git du fichier.
