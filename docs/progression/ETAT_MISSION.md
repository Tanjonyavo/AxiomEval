# État de la mission — point de reprise

Mis à jour le 2026-11-11 (après-midi). Branche `feat/mission-s24`. Dernier commit de fond : `9f0d0bc` (retest r7). Rien n'est poussé. Bilan : `docs/progression/RAPPORT_FINAL_S24.md`.

Régénérer les manuels : `python tools/pedagogie/build.py` puis `node tools/pedagogie/print.mjs <playwright/index.mjs> [filtre de nom]` (depuis la racine du dépôt ; Playwright est dans `C:/Users/ramia/career-ops/node_modules/playwright/index.mjs`). Pour expliquer un fichier, ajouter `docs/pedagogie/explications/<chemin avec __>.md` avec des sections `## Ldébut-Lfin`.

Guide de la journée du 11 novembre (corpus v3, S10, F-007/F-008, r7, pistes) : `docs/pedagogie/PDF/AxiomEval_Guide_v3_S10_et_Pistes.pdf`, source `docs/pedagogie/sources/AxiomEval_Guide_v3_S10_et_Pistes.md`.

**Attention : `build.py` échoue aujourd'hui** (`IndexError`) : les explications de `security/egress.py` (fichier passé de 70 à 53 lignes) et de `stats/paired.py` (lignes ajoutées) sont périmées. Le guide a été rendu seul, sans relancer les volumes de code. Réécrire ces plages avant de régénérer les volumes.

## Dernier module réellement terminé

S10 (séquences) **IMPLÉMENTÉ ET TESTÉ** sur le corpus v3 ; hypothèse H-S10 non soutenue (`docs/experiments/S10_SEQUENCES_V3.md`). S09 (baselines) **IMPLÉMENTÉ ET TESTÉ** sur le corpus v2 (180 groupes, 4 320 exécutions réelles) : la régression logistique dépasse la majorité avec des intervalles groupés disjoints ; limite de généralisation aux familles inconnues (`docs/experiments/S09_BASELINES_V2.md`).

## Environnement vérifié

- Python 3.14.5 dans `.venv` ; paquets ajoutés : fastapi 0.162, uvicorn 0.54, httpx 0.28, numpy 2.5, scikit-learn 1.9, scipy 1.18.
- Ollama 0.40.16 portable dans `%LOCALAPPDATA%\Programs\Ollama` ; modèles `qwen2.5:1.5b-instruct` et `qwen2.5:0.5b-instruct`. Lancer `ollama serve` avant toute collecte.
- RTX 3060 6 Go ; environ 15 Go de disque libre au début de la mission.
- 160 tests passent (`python -m unittest discover -s tests`), 1 ignoré sans `AXIOMEVAL_LIVE=1`. Le test GRU exige PyTorch (extra `seq`) ; sans lui il est ignoré.

## Données réelles (locales, non publiées)

Corpus v1 : `data/runs/*.jsonl`, empreintes dans `data/MANIFEST.json`. Corpus v2 : `data/runs/v2/*.jsonl` (4 × 1 080 exécutions), empreintes dans `data/MANIFEST_V2.json`. Recollecter (environ 4 exécutions par seconde ; ~20 min pour les 4 releases si la machine ne se met pas en veille) :

```powershell
.\.venv\Scripts\python.exe -m axiomeval collect --release configs/releases/r1-baseline.yaml --out data/runs/r1-baseline.jsonl --draws 2
.\.venv\Scripts\python.exe -m axiomeval collect --corpus-dir fixtures/security --release configs/releases/r1-baseline.yaml --out data/runs/security-r1-baseline.jsonl --draws 3
.\.venv\Scripts\python.exe -m axiomeval collect --corpus-dir fixtures/corpus-v2 --release configs/releases/r1-baseline.yaml --out data/runs/v2/r1-baseline.jsonl --draws 2
.\.venv\Scripts\python.exe tools/data/manifest.py data/runs/v2 data/MANIFEST_V2.json
```

S9 sur v2 : `ml-baselines --runs data/runs/v2/*.jsonl --out reports/s09/v2_baselines.json` dure environ 36 min (boosting dense sur le vocabulaire TF-IDF, 11 protocoles × 1 000 bootstraps).

## Décisions prises (ne pas les rediscuter sans raison)

1. Référence technique : spécification 32 semaines ; S04–S06 faits avant S07 car bloquants.
2. Unité statistique : le groupe (modèle de scénario + paramètres). Paraphrases et tirages sont moyennés dans le groupe.
3. Décision de release : borne de Hoeffding unilatérale (valide, conservatrice) ; bootstrap groupé en diagnostic seulement.
4. Brèche (effet réel) → REJECT ; tentative stoppée par un contrôle → HOLD (revue).
5. Température 0,7 et graine = graine de release + numéro de tirage : sinon les répétitions seraient des copies.
6. Les tests unitaires valident le harnais ; les conclusions scientifiques viennent des collectes réelles.
7. Le corpus v1 reste figé (ses exécutions et rapports restent valides) ; v2 vit dans `fixtures/corpus-v2/`, généré par `tools/corpus/build_corpus_v2.py`.
8. Chaque enregistrement nomme son corpus et l'empreinte de son environnement (documents, commandes, politique) ; un verdict qui mélange deux corpus ou deux environnements est INCOMPLETE.

## En cours au 2026-11-11 (point de reprise exact)

- **F-003 corrigé dans le code** (`88cf85c`) : release `configs/releases/r5-protected.yaml` = r4 + valeur protégée, même graine. Rejeu de la fuite réelle testé (r4 brèche, r5 tentative bloquée).
- **Retest réel terminé** (`data/runs/v2-env/`, `reports/s05/v2env_compare_r4-guarded_r5-protected.json`) : r5 bloque les 5 fuites de r4 ; verdict r4 → r5 REJECT à cause de F-004 seulement.
- **S9 refaite** avec `prefix-features-v2` (`reports/s09/v2_baselines_features_v2.json`, `docs/experiments/S09_BASELINES_V2.md`) : conclusions maintenues ; la logistique a un Brier égal à la majorité (et non pire) sur familles inconnues.
- **F-004/F-005 corrigés** (`9923985`, release `r6-bound`) : 0 brèche sur 1 080 exécutions réelles ; verdict r5 → r6 HOLD, premier verdict non-REJECT sur v2.
- **S10 bloquée sur v2, avec mesure** : sur 4 320 trajectoires réelles, 797 sur 1 080 par release font un seul appel au modèle (4 événements), les autres deux appels (8 événements). D'où le corpus v3 (`0f8a098`) : v2 + 9 familles multi-étapes (65 groupes), 245 groupes au total.
- **Code S10 validé par les tests** (`9f3aa96`) : `src/axiomeval/ml/sequence.py`, commande `ml-sequence`, extra `seq` (torch). Un essai de fumée sur v2 r1 + r4 (1 tirage de graines, 50 bootstraps) a seulement vérifié que la chaîne tourne ; ce n'est pas un résultat.
- **Collecte v3 terminée** : r1, r6, r7 (3 × 1 470, `data/MANIFEST_V3.json`). Aucune exécution à 3 appels (`docs/experiments/V3_TRAJECTOIRES.md`).
- **S10 faite** (`fcb2b49`, `docs/experiments/S10_SEQUENCES_V3.md`) : GRU meilleur Brier que l'agrégat à l'horizon 2, mais l'ordre mélangé donne le même gain ; H-S10 non soutenue. Relancer : `ml-sequence --runs data/runs/v3/r1-baseline.jsonl data/runs/v3/r6-bound.jsonl --out reports/s10/v3_sequence.json` (environ 20 min sur CPU).
- **F-007/F-008** : release r7 (`write-checks-v1`, `a6910c0`) ; brèches 40 → 6, remboursements conditionnels légitimes 18/36 → 0/36 ; r6 → r7 REJECT (`docs/security/FINDINGS.md`).

## Prochaines actions, dans l'ordre

1. Revue humaine des 119 tentatives bloquées de r6 (condition du HOLD), puis plus de groupes pour démontrer la non-infériorité (~520).
2. Calibration (S15 partielle) et conservation des prédictions pour un bootstrap apparié des différences entre modèles.
3. F-008 résiduel : mesurer « lecture dans un pas antérieur obligatoire » ou un message de refus qui invite à redemander (release r8), en surveillant les remboursements conditionnels légitimes.
4. Transformer compact (S11), ablations S12 (événements retrieval/outil, capacité égalisée, courbes d'apprentissage), gate G12.
5. Transfert (§9) vers un second agent ou domaine ; non commencé.
6. S13–S24 selon `docs/audit/AUDIT_INITIAL_S24.md`.
7. Manuels pédagogiques : corpus v2, caviardage des variantes, évaluation par familles, valeurs protégées, liaison à la demande.
