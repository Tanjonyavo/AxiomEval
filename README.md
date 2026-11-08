# AxiomEval

Prototype Python pour construire des évaluations reproductibles de systèmes IA : observations structurées, contrôles déterministes, décisions expliquées et rapports JSON/HTML.

## État actuel

Le socle de semaine 1 est exécutable localement. Il valide une configuration, relie une cible et un scénario à une exécution, vérifie les preuves, détecte un outil interdit et produit un verdict.

**Les quatre démonstrations utilisent des observations synthétiques.** Aucun modèle IA ni outil métier n’est exécuté. Cette version sert à vérifier l’architecture et les règles du contrôle ; elle n’est pas prête pour la production.

## Installation

Prérequis : **Python 3.12 ou plus récent** et Git. PyYAML est la seule dépendance d’exécution. Aucun GPU ni clé API n’est nécessaire.

Depuis PowerShell :

```powershell
git clone https://github.com/Tanjonyavo/AxiomEval.git
Set-Location AxiomEval
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m axiomeval --version
```

Sous Linux ou macOS, utiliser `python3` pour créer l’environnement et `.venv/bin/python` pour les commandes suivantes. Exécuter les exemples depuis la racine du dépôt.

## Démonstrations

```powershell
.\.venv\Scripts\python.exe -m axiomeval check-config
.\.venv\Scripts\python.exe -m axiomeval demo --case safe
.\.venv\Scripts\python.exe -m axiomeval demo --case violation
.\.venv\Scripts\python.exe -m axiomeval demo --case missing
.\.venv\Scripts\python.exe -m axiomeval demo --case uncertain
```

Avec la configuration par défaut :

| Cas | Verdict | Code de sortie | Signification |
|---|---|---:|---|
| `safe` | `PROMOTE` | 0 | Le contrôle configuré est satisfait. |
| `violation` | `REJECT` | 10 | Un outil interdit a été observé sans ambiguïté. |
| `missing` | `INCOMPLETE` | 11 | La preuve requise manque. |
| `uncertain` | `HOLD` | 12 | L’observation demande une revue. |
| Erreur de configuration ou d’écriture | Erreur | 2 | La commande ne peut pas accomplir le travail. |

Les codes 10, 11 et 12 sont des résultats attendus du contrôle. `PROMOTE` reste une recommandation limitée au périmètre testé et ne déclenche aucun déploiement.

Chaque exécution écrit `report.json` et `report.html` dans un dossier distinct sous `reports/generated/`. Les chemins sont affichés dans le terminal. Ouvrir le HTML dans un navigateur pour lire le résultat.

Options disponibles : `--config configs/default.yaml`, `--output reports/generated` et `--help`. La commande installée `axiomeval` utilise la même entrée que `python -m axiomeval`.

## Comparaison appariée hors ligne

[TX-01](labs/README.md) vérifie un plan synthétique, apparie les exécutions de deux versions, calcule un écart par groupes et rapporte le signal de permission séparément. Le JSON exporte les lignes normalisées et les coûts. Les 6 tests de TX‑01 s’ajoutent aux 26 tests du socle S1.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Les 26 tests du socle S1 couvrent la configuration (y compris YAML trop imbriqué et texte non encodable en UTF-8), les identifiants, les priorités des verdicts, les preuves manquantes/altérées/périmées/mal liées, les doublons, l'égalité des données JSON/HTML et la CLI. Voir les [résultats et limites de validation](docs/semaine-01/validation.md) et l'[audit du 2 novembre 2026](docs/semaine-01/audit.md).

Deux supports pédagogiques décrivent le code après correction : [01 - Résumé de la semaine 1](docs/semaine-01/pdf/01-resume-semaine-1.pdf) et [02 - Comprendre et maîtriser techniquement la semaine 1](docs/semaine-01/pdf/02-comprendre-maitriser-semaine-1.pdf).

## Architecture

```text
Configuration → Cible + scénario → Exécution + preuves
                                      ↓
                           Évaluation déterministe
                                      ↓
                           Décision et ses raisons
                                      ↓
                              JSON + HTML
```

Le paquet `src/axiomeval/` sépare les modèles métier, l’évaluation, la politique de décision, les rapports et la CLI. Les modèles restent indépendants des entrées/sorties.

- [Architecture et contrats](docs/architecture.md)
- [Choix de conception et alternatives](docs/decisions.md)

## Limites

Les empreintes vérifient la cohérence locale du contenu ; elles n’authentifient pas son auteur. Les observations d’outils de cette version ne constituent pas encore des trajectoires temporelles. Les modèles appris, mesures statistiques et contrôles d’accès de production restent à développer.

Utiliser des données synthétiques : les rapports incluent les paramètres du scénario et cette version ne réalise pas encore la suppression des données sensibles.

## Parcours intégré de développement et d’apprentissage

La [roadmap active 18 - AXM, produit et recherche](docs/18%20-%20Refonte%20AXM%20-%20Produit%20et%20recherche/00%20-%20Commencer%20ici.md) organise la reprise depuis ce socle, avec 132 notions, 51 laboratoires et les choix de périmètre scientifique. Les statuts techniques ci-dessus ne sont pas modifiés par ce calendrier.

La refonte AXM 2.0 ajoute douze blocs mathématiques et un avant-projet de recherche. [AXM-07 et R6](docs/18%20-%20Refonte%20AXM%20-%20Produit%20et%20recherche/23%20-%20AXM-07%20-%20Regression%20et%20recherche.md) ajoutent un cours de régression et une étude à temps fixé, dans un calendrier de 136 semaines et 2 045 h. Le budget complet de formation et projet est détaillé dans la roadmap 18; les quatre démonstrations du logiciel restent synthétiques.
