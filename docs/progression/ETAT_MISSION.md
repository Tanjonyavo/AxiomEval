# État de la mission — point de reprise

Mis à jour le 2026-11-11 (01:10 UTC). Branche `feat/mission-s24`. Corpus v2 et S9 refaite : commits `5ec1646` à `60f8d37`. Rien n'est poussé. Bilan : `docs/progression/RAPPORT_FINAL_S24.md`.

Régénérer les manuels : `python tools/pedagogie/build.py` puis `node tools/pedagogie/print.mjs <playwright/index.mjs>` (depuis la racine du dépôt). Pour expliquer un fichier, ajouter `docs/pedagogie/explications/<chemin avec __>.md` avec des sections `## Ldébut-Lfin`.

## Dernier module réellement terminé

S09 (baselines) **IMPLÉMENTÉ ET TESTÉ** sur le corpus v2 (180 groupes, 4 320 exécutions réelles) : la régression logistique dépasse la majorité avec des intervalles groupés disjoints ; limite de généralisation aux familles inconnues (`docs/experiments/S09_BASELINES_V2.md`).

## Environnement vérifié

- Python 3.14.5 dans `.venv` ; paquets ajoutés : fastapi 0.162, uvicorn 0.54, httpx 0.28, numpy 2.5, scikit-learn 1.9, scipy 1.18.
- Ollama 0.40.16 portable dans `%LOCALAPPDATA%\Programs\Ollama` ; modèles `qwen2.5:1.5b-instruct` et `qwen2.5:0.5b-instruct`. Lancer `ollama serve` avant toute collecte.
- RTX 3060 6 Go ; environ 15 Go de disque libre au début de la mission.
- 131 tests passent (`python -m unittest discover -s tests`), 1 ignoré sans `AXIOMEVAL_LIVE=1`.

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

## Prochaines actions, dans l'ordre

1. Corriger F-003 (documents internes récupérables) puis créer une release r5 et la collecter : aujourd'hui, les 4 releases sont REJECT sur v2.
2. S15 avancée partiellement : calibrer les probabilités S9 (le Brier de la logistique est pire que la majorité sur familles inconnues) ; conserver les prédictions pour un bootstrap apparié des différences entre modèles.
3. S10 : installer PyTorch (CPU suffit), GRU sur la séquence d'événements du préfixe, même horizon et mêmes partitions que S9 (gelée, release et famille tenues à l'écart).
4. S11–S12 : Transformer compact, ablations (ordre, texte/structure, contexte de capacité, horizon), courbes d'apprentissage ; gate G12.
5. Transfert (§9) : un second agent ou domaine ; non commencé.
6. S13–S16, S17–S20, S21–S24 selon `docs/audit/AUDIT_INITIAL_S24.md`.
7. Manuels pédagogiques : expliquer le corpus v2, le caviardage des variantes et l'évaluation par familles ; compléter l'explication ligne par ligne.
