# src/axiomeval/policy/authz.py
<!-- source-sha256: 6de4a446ade96fac1fd7c42452987582b640398690b51432c9baf69c6cabeb28 -->

**Rôle.** Décider, hors du modèle, si un appel d'outil proposé par l'agent peut s'exécuter (semaine S6, spec §31.7). Le modèle *propose* ; ce module *dispose*. Entrées : la politique, l'identité de session, le nom de l'outil, les arguments, les ressources (commandes) et l'heure. Sortie : une `Decision` enregistrée dans la trace. Utilisé par `collect/secure_tools.py` ; testé par `tests/test_policy_s06.py`. Lien AXM : 06-C08 (politiques de sécurité et propriétés d'exécution).

## L1-L6
**Quoi.** Docstring du module : trois principes. **Pourquoi.** Ils fixent le contrat avant le code : ordre fixe des règles, refus explicite, refus par défaut (*fail-closed*), identité venant de la session. **Si on l'enlève.** Rien ne casse, mais le lecteur perd le contrat ; c'est la première chose à citer en entrevue.

## L7-L15
**Quoi.** Imports. `hashlib` pour l'empreinte des arguments d'une approbation ; `json` pour lire la politique et canoniser les arguments ; `secrets` pour générer des jetons imprévisibles (contrairement à `random`, conçu pour la sécurité) ; `dataclass` et `field` pour des objets de données ; `datetime`/`timedelta` pour les expirations ; `Path` pour le fichier de politique ; `ConfigurationError` (fichier invalide) et `ValidationError` (objet invalide) viennent de `errors.py` ; `text()` de `models/validation.py` refuse une chaîne vide ou non encodable. **D'où / vers où.** Ces erreurs remontent jusqu'à la CLI, qui les affiche sans trace Python.

## L17-L22
**Quoi.** Trois constantes. `EFFECTS` : nature d'un outil (lecture, écriture, sensible). `IDENTITY_KEYS` : noms d'arguments qu'un modèle pourrait utiliser pour se faire passer pour quelqu'un d'autre (`customer_id`, `role`…). `CRITICAL_REASONS` : refus qui révèlent une tentative grave (outil inconnu, mauvais rôle, autre tenant, autre propriétaire, identité expirée). **Pourquoi `frozenset`.** Immuable et rapide pour le test d'appartenance `in`. **Si on retire un élément de `CRITICAL_REASONS`.** Le refus reste un refus, mais n'est plus marqué critique : l'évaluateur le classerait comme refus « doux ». **Test.** `test_user_to_admin_action_fails_closed` vérifie `d.critical`.

## L25-L39
**Quoi.** `Identity` : sujet, rôle, tenant, date d'expiration. `frozen=True` rend l'objet non modifiable après création : personne ne peut changer le rôle en cours de route. `__post_init__` s'exécute après le constructeur : il normalise les trois chaînes avec `text()` (via `object.__setattr__`, seule façon d'écrire dans un objet gelé) et refuse une date sans fuseau horaire (`utcoffset() is None`), car comparer une heure locale à une heure UTC donnerait une expiration fausse. `public()` renvoie l'identité sans la date, pour la trace. **Si on enlevait `frozen`.** Un bug pourrait modifier l'identité entre deux appels. **Test.** `test_stale_identity`.

## L42-L49
**Quoi.** `ToolRule` : la règle d'un outil. `roles` autorisés, `effect`, `owner_scoped` (l'outil agit sur une ressource qui appartient à quelqu'un), `max_amount` (plafond absolu) et `approval_above` (au-delà, une approbation humaine est requise). Les valeurs par défaut rendent ces contraintes optionnelles. **Exemple AxiomEval.** `refund_order` : rôles client et agent, écriture, propriétaire, plafond 500 $, approbation au-delà de 50 $ (`fixtures/corpus/policy.json`).

## L52-L58
**Quoi.** `Policy` : une version et un dictionnaire `outil → règle`. `rule()` renvoie `None` pour un outil absent. **Pourquoi c'est important.** Ce `None` déclenche plus bas le refus par défaut : un outil oublié dans la politique est refusé, jamais autorisé.

## L61-L67
**Quoi.** Lecture du fichier de politique. Toute erreur de lecture ou de JSON devient `ConfigurationError` (`from exc` garde la cause pour le débogage). On exige *exactement* les clés `version` et `rules`, et une liste pour `rules`. **Pourquoi « exactement ».** Une clé mal orthographiée (`rule` au lieu de `rules`) serait sinon ignorée en silence et produirait une politique vide.

## L68-L78
**Quoi.** Validation de chaque règle : dictionnaire, clés connues seulement (`<=` = sous-ensemble), clés obligatoires présentes (`tool`, `roles`, `effect`), effet connu, outil non dupliqué. Puis construction du `ToolRule` (les rôles deviennent un tuple immuable). **Si on acceptait les doublons.** La seconde règle écraserait la première sans prévenir. **Test.** `test_invalid_policy_files_refused` couvre clés manquantes, effet inconnu, doublon.

## L81-L83
**Quoi.** `args_digest` : empreinte SHA-256 de l'outil et de ses arguments, sérialisés de façon canonique (`sort_keys=True` : l'ordre des clés n'a pas d'influence). **Pourquoi.** Une approbation doit porter sur *ces* arguments exacts : changer 230 $ en 231 $ change l'empreinte. **Mathématique.** Une fonction de hachage cryptographique rend en pratique impossible de trouver deux arguments différents de même empreinte (résistance aux collisions).

## L86-L97
**Quoi.** `ApprovalStore` mémorise les approbations en attente et celles déjà utilisées. `issue` crée un jeton de 128 bits (`token_hex(16)`) et l'associe au sujet, au tenant, à l'outil, à l'empreinte des arguments et à une date limite (5 minutes par défaut). **D'où.** Dans un vrai système, un humain déclencherait `issue` ; ici, les tests le font.

## L99-L115
**Quoi.** `consume` vérifie un jeton, dans cet ordre : déjà utilisé → `approval-replayed` ; inconnu → `approval-unknown` ; expiré ; identité ou outil différents ; arguments différents. Si tout est bon, le jeton est retiré des attentes et ajouté aux utilisés (usage unique), et la fonction renvoie `None`. **Pourquoi renvoyer une raison au lieu de lever une exception.** Le refus est un résultat normal qui doit apparaître dans la trace. **Test.** `test_approval_is_single_use_bound_and_expiring` couvre les cinq cas.

## L118-L144
**Quoi.** `Decision` : tous les champs exigés par la spec §31.7 (identité demandée et effective, privilège demandé et effectif, portée autorisée, action observée, résultat, version de politique). `critical` est une propriété calculée : refus ET raison critique. `record()` produit le dictionnaire écrit dans l'événement `authz` de la trace. **Vers où.** `collect/agent.py` ajoute ce dictionnaire à la trace ; `corpus/evaluate.py` le lit pour noter la permission.

## L147-L158
**Quoi.** Début de `authorize`. `claimed` extrait les identités *prétendues* dans les arguments (ex. `customer_id: client-2`). `decide` est une fonction interne qui fabrique la `Decision` : l'identité demandée inclut les prétentions préfixées `claimed_`, mais l'identité *effective* reste celle de la session. **C'est la défense contre le « confused deputy ».** Le modèle peut écrire ce qu'il veut, cela ne change jamais qui agit. **Test.** `test_confused_deputy_claims_are_ignored_and_recorded`.

## L160-L165
**Quoi.** Trois premiers contrôles, dans l'ordre : identité expirée ; outil sans règle (refus par défaut) ; rôle non autorisé. **Pourquoi cet ordre.** Les contrôles les moins coûteux et les plus généraux d'abord ; une identité périmée ne doit même pas révéler si l'outil existe.

## L166-L175
**Quoi.** Contrôle de propriété pour les outils `owner_scoped`. La commande est cherchée (numéro normalisé en majuscules). Absente → autorisé avec la raison `allowed-not-found` : l'outil répondra « introuvable », rien n'est divulgué. Autre tenant → `cross-tenant`. Client qui n'est pas le propriétaire → `not-owner` (un agent de support du même tenant, lui, peut lire). La portée enregistrée devient `tenant:…/owner:…`. **Limite.** Répondre différemment pour « introuvable » et « refusé » laisse deviner l'existence d'une commande d'un autre client ; une version plus stricte répondrait pareil dans les deux cas.

## L176-L190
**Quoi.** Contrôles de montant. Conversion en `float` (refus si impossible), refus des montants négatifs, nuls ou NaN (`amount != amount` n'est vrai que pour NaN, car NaN n'est égal à rien, même pas à lui-même), plafond absolu, puis approbation au-delà du seuil : sans jeton → `approval-required` ; avec jeton → `consume` décide. **Si on oubliait le test NaN.** `float("nan") > 500` est faux : un NaN passerait le plafond. **Test.** `test_invalid_amounts`, `test_small_refund_allowed_large_needs_approval`.

## L191
**Quoi.** Tous les contrôles sont passés : autorisation avec la portée calculée. C'est le seul `True` « normal » de la fonction : il faut traverser toutes les règles pour l'atteindre.
