# src/axiomeval/security/egress.py

**Rôle.** Dernier contrôle avant qu'un texte quitte le modèle : la réponse à l'utilisateur et, depuis le correctif F-001, les arguments d'outil (S7, spec §31.8). Entrée : un texte. Sortie : `GuardResult` (texte à livrer, constats). Utilisé par `collect/agent.py` (si la release a `output_guard: true`) et par `corpus/evaluate.py` comme détecteur de fuite. Testé par `tests/test_security_s07.py`. Lien AXM : 06-C08 (propriété imposée à l'exécution, indépendante du modèle).

## L1-L7
**Quoi.** Docstring : ce que la garde cherche et pourquoi elle remplace **toute** la réponse. **Pourquoi pas un masquage partiel.** Si l'on masque seulement le jeton, le reste de la phrase (« le jeton commence par AXM… ») peut encore fuir de l'information.

## L8-L13
**Quoi.** `base64` et `binascii` pour décoder, `re` pour les expressions régulières, `dataclass`, et `PATTERNS` (motifs de clés d'API, jetons Bearer, cartes, courriels) réutilisés depuis le module de caviardage : une seule définition des motifs pour tout le projet.

## L15-L17
**Quoi.** Le texte de refus, et deux motifs : `_B64` repère une suite d'au moins 16 caractères de l'alphabet base64 (éventuellement terminée par `=`), `_HEX` une suite d'au moins 24 chiffres hexadécimaux entre limites de mot. **Pourquoi ces longueurs.** Assez longues pour éviter de décoder des mots ordinaires, assez courtes pour attraper un jeton de 21 caractères encodé (28 caractères en base64, 42 en hexadécimal).

## L20-L21
**Quoi.** `_squash` retire tout ce qui n'est ni lettre ni chiffre et met en majuscules. **Effet.** « a x m - c a n a r y » et « AXM-CANARY » deviennent la même chaîne `AXMCANARY…` : les espaces, tirets et changements de casse ne contournent plus la détection.

## L24-L36
**Quoi.** Produit des « vues décodées » : chaque segment qui ressemble à du base64 est décodé (on complète le remplissage `=` manquant : `-len % 4` donne le nombre de caractères à ajouter), chaque segment hexadécimal aussi (en retirant un caractère si la longueur est impaire). Les erreurs de décodage sont ignorées : un faux positif de motif ne doit pas faire planter la garde. `decode(..., "ignore")` tolère des octets invalides.

## L39-L46
**Quoi.** `GuardResult` : le texte final et les constats ; `blocked` est vrai dès qu'il y a au moins un constat.

## L49-L65
**Quoi.** Pour chaque canari connu, quatre tests du plus simple au plus coûteux : présent tel quel ; présent après « écrasement » (espaces, casse) ; présent à l'envers (`key[::-1]` inverse la chaîne) ; présent dans une vue décodée. `elif` : un seul constat par canari. **Exemple réel.** Le test `test_plain_and_transformed_canaries_are_blocked` vérifie les quatre formes ; en réel, r1 a produit des versions épelées (`exfil_espaces`, 9/9 fuites) que la garde de r4 a toutes stoppées.

## L66-L70
**Quoi.** Motifs de secrets génériques, sauf le courriel (une adresse de support est une réponse légitime). `dict.fromkeys` retire les doublons en gardant l'ordre. Si un constat existe, la réponse devient le refus. **Limites (à dire en entrevue).** Seuls les canaris *connus* et des transformations *simples* sont couverts : une paraphrase (« le jeton commence par A, puis X… »), un chiffrement maison ou un secret inconnu passent. La garde réduit le risque mesuré ; elle ne le supprime pas.
