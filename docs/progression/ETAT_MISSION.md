# État de la mission — point de reprise

Mis à jour le 2026-11-10. Branche `feat/mission-s24`, dernier commit technique `3846051`, manuels pédagogiques `9ac6dbd`. Rien n'est poussé. Bilan : `docs/progression/RAPPORT_FINAL_S24.md`.

Régénérer les manuels : `python tools/pedagogie/build.py` puis `node tools/pedagogie/print.mjs <playwright/index.mjs>` (depuis la racine du dépôt). Pour expliquer un fichier, ajouter `docs/pedagogie/explications/<chemin avec __>.md` avec des sections `## Ldébut-Lfin`.

## Dernier module réellement terminé

S09 (baselines) au niveau **PARTIEL** : code, tests et expérience réelle faits ; conclusion impossible faute de groupes.

## Environnement vérifié

- Python 3.14.5 dans `.venv` ; paquets ajoutés : fastapi 0.162, uvicorn 0.54, httpx 0.28, numpy 2.5, scikit-learn 1.9, scipy 1.18.
- Ollama 0.40.16 portable dans `%LOCALAPPDATA%\Programs\Ollama` ; modèles `qwen2.5:1.5b-instruct` et `qwen2.5:0.5b-instruct`. Lancer `ollama serve` avant toute collecte.
- RTX 3060 6 Go ; environ 15 Go de disque libre au début de la mission.
- 121 tests passent (`python -m unittest discover -s tests`), 1 ignoré sans `AXIOMEVAL_LIVE=1`.

## Données réelles (locales, non publiées)

`data/runs/*.jsonl`, empreintes dans `data/MANIFEST.json`. Recollecter :

```powershell
.\.venv\Scripts\python.exe -m axiomeval collect --release configs/releases/r1-baseline.yaml --out data/runs/r1-baseline.jsonl --draws 2
.\.venv\Scripts\python.exe -m axiomeval collect --corpus-dir fixtures/security --release configs/releases/r1-baseline.yaml --out data/runs/security-r1-baseline.jsonl --draws 3
```

## Décisions prises (ne pas les rediscuter sans raison)

1. Référence technique : spécification 32 semaines ; S04–S06 faits avant S07 car bloquants.
2. Unité statistique : le groupe (modèle de scénario + paramètres). Paraphrases et tirages sont moyennés dans le groupe.
3. Décision de release : borne de Hoeffding unilatérale (valide, conservatrice) ; bootstrap groupé en diagnostic seulement.
4. Brèche (effet réel) → REJECT ; tentative stoppée par un contrôle → HOLD (revue).
5. Température 0,7 et graine = graine de release + numéro de tirage : sinon les répétitions seraient des copies.
6. Les tests unitaires valident le harnais ; les conclusions scientifiques viennent des collectes réelles.

## Prochaines actions, dans l'ordre

1. **Agrandir le corpus** (bloquant pour S10–S12) : viser 150 à 300 groupes en ajoutant des familles réellement différentes (pas seulement de nouveaux paramètres), un second agent ou domaine pour le transfert (§9), puis recollecter 2 releases × 2 tirages.
2. Refaire S9 sur le grand corpus ; ajouter calibration (S15) et analyse d'erreurs.
3. S10 : installer PyTorch (CPU suffit), GRU sur la séquence d'événements du préfixe, même horizon et même budget que S9.
4. S11–S12 : Transformer compact, ablations (ordre, texte/structure, contexte de capacité, horizon), courbes d'apprentissage ; gate G12.
5. S13–S16, S17–S20, S21–S24 selon `docs/audit/AUDIT_INITIAL_S24.md`.
6. Manuels pédagogiques : compléter l'explication ligne par ligne des fichiers listés comme incomplets dans `docs/pedagogie/INDEX_CODE_EXPLIQUE.md`.
