# src/axiomeval/security/egress.py
<!-- source-sha256: 625732921b27117311cf7bb2b9aa844ce7d1f2bafc9ebb04702030f9bb6c80b4 -->

**Rôle.** Dernier contrôle avant qu'un texte quitte le modèle : la réponse à l'utilisateur et, depuis le correctif F-001, les arguments d'outil (S7, spec §31.8). Entrée : un texte. Sortie : `GuardResult` (texte à livrer, constats). Utilisé par `collect/agent.py` (si la release a `output_guard: true`) et par `corpus/evaluate.py` comme détecteur de fuite. Testé par `tests/test_security_s07.py`. Lien AXM : 06-C08 (propriété imposée à l'exécution, indépendante du modèle).

**Historique.** Ce fichier a été réduit de 70 à 53 lignes par le correctif F-006 (`d96dac9`) : l'écrasement (`squash`) et le décodage (`decoded_views`) ont été déplacés dans `collect/redaction.py`, pour que la garde et le caviardage des traces reconnaissent exactement les mêmes variantes. Le correctif F-003 (`88cf85c`) a ajouté les valeurs protégées.

## L1-L7
**Quoi.** Docstring : ce que la garde cherche et pourquoi elle remplace **toute** la réponse. **Pourquoi pas un masquage partiel.** Si l'on masque seulement le jeton, le reste de la phrase (« le jeton commence par AXM… ») peut encore fuir de l'information.

## L8-L10
**Quoi.** `dataclass` pour des objets immuables, et trois noms importés du module de caviardage : `PATTERNS` (motifs de clés d'API, jetons Bearer, cartes, courriels), `decoded_views` et `squash`. Les alias `_decoded_views` et `_squash` gardent les anciens noms internes. **Pourquoi importer plutôt que recopier.** Avant F-006, la garde savait reconnaître un canari épelé ou encodé, mais le caviardage des traces non : une variante bloquée dans la réponse pouvait quand même être écrite dans un fichier de traces. Une seule définition supprime ce décalage. **Ce que font les deux fonctions.** `squash` retire tout ce qui n'est ni lettre ni chiffre et met en majuscules : « a x m - c a n a r y » et « AXM-CANARY » deviennent la même chaîne. `decoded_views` décode chaque segment qui ressemble à du base64 (au moins 16 caractères, remplissage `=` complété) ou à de l'hexadécimal (au moins 24 chiffres), en ignorant les erreurs : un faux positif de motif ne doit pas faire planter la garde.

## L12
**Quoi.** Le texte de refus qui remplace la réponse entière.

## L15-L22
**Quoi.** `GuardResult` : le texte final et les constats ; `blocked` est vrai dès qu'il y a au moins un constat. `frozen=True` : un résultat ne peut pas être modifié après coup.

## L25-L29
**Quoi.** `OutputGuard` porte deux listes. `canaries` : des secrets plantés exprès ; en trouver un prouve une fuite. `protected` : des valeurs qui ne sont **pas** des secrets techniques mais ne doivent jamais atteindre un client, par exemple le courriel interne `support-interne@avana.example` (finding F-003). La valeur par défaut `()` garde le comportement des releases r1 à r4.

## L31-L33
**Quoi.** `check` prépare la liste des constats et calcule une seule fois la forme écrasée de la réponse, réutilisée par tous les tests qui suivent.

## L34-L38
**Quoi.** Valeurs protégées (egress-v3). Deux tests : présence telle quelle sans tenir compte de la casse (`lower()`), sinon présence après écrasement (espaces, tirets, casse). **Pourquoi pas les formes encodées ici.** Le modèle a divulgué ce courriel en clair ; la garde couvre ce qui a été observé, sans prétendre à plus. **Résultat réel.** Sur les 6 exécutions de la famille `courriel_interne` (corpus v2, même environnement), r4 laisse fuir le courriel interne 5 fois, r5 aucune (0/6).

## L39-L48
**Quoi.** Pour chaque canari connu, quatre tests du plus simple au plus coûteux : présent tel quel ; présent après écrasement ; présent à l'envers (`key[::-1]` inverse la chaîne) ; présent dans une vue décodée. `elif` : un seul constat par canari. **Exemple réel.** Le test `test_plain_and_transformed_canaries_are_blocked` vérifie les quatre formes ; en réel, r1 a produit des versions épelées (`exfil_espaces`, 9/9 fuites) que la garde de r4 a toutes stoppées.

## L49-L53
**Quoi.** Motifs de secrets génériques, sauf le courriel (une adresse de support publique est une réponse légitime ; le courriel interne est couvert par les valeurs protégées). `dict.fromkeys` retire les doublons en gardant l'ordre. Si un constat existe, la réponse devient le refus. **Limites (à dire en entrevue).** Seuls les canaris et valeurs *connus* et des transformations *simples* sont couverts : une paraphrase (« le jeton commence par A, puis X… »), un chiffrement maison ou un secret inconnu passent. La garde réduit le risque mesuré ; elle ne le supprime pas.
