# AxiomEval — Mathématiques et IA, semaines 01 à 26

Chaque section : variables, hypothèses, raisonnement, exemple numérique réel ou vérifiable, lien avec le code, limites. Les sections 1 à 7 portent sur du code **implémenté** ; les sections 8 à 12 préparent S10–S18 (**non implémenté**). Références AXM : `Math IA\AXM\16 - Refonte mathématique et visuelle\AXM-0x\A - Manuel integral.pdf`.

[TOC]

## 1. Empreintes et chaîne d'événements (S03) — AXM : aucune (cryptographie appliquée)

**Objet.** \(h_0 = 0^{64}\), \(h_i = \mathrm{SHA256}(\mathrm{json}(e_i, h_{i-1}))\). L'empreinte finale \(h_n\) dépend de tous les événements et de leur ordre.

**Raisonnement.** Modifier \(e_k\) change \(h_k\), donc \(h_{k+1}\), …, \(h_n\) (effet en cascade). Réordonner deux événements change les entrées hachées. Trouver un \(e'_k \ne e_k\) donnant le même \(h_k\) demanderait une collision SHA-256, infaisable en pratique (\(\approx 2^{128}\) opérations par le paradoxe des anniversaires).

**Code.** `collect/trace.py::TraceEvent`, `validate_trace`, `trace_digest`. **Limite.** Une empreinte prouve l'intégrité, pas l'auteur : sans signature, quelqu'un peut recalculer une chaîne entière.

## 2. Unités, groupes et différences appariées (S04–S05) — AXM 03-C04, 04-C01

**Variables.** Groupes \(g = 1..G\). Pour la release \(r\), \(Y_{g,j}^{(r)} \in \{0,1\}\) succès de l'exécution \(j\) du groupe \(g\) (paraphrases × tirages, \(m_g\) exécutions). Taux du groupe : \(\bar Y_g^{(r)} = \frac{1}{m_g}\sum_j Y_{g,j}^{(r)}\). Différence appariée : \(D_g = \bar Y_g^{(c)} - \bar Y_g^{(b)} \in [-1, 1]\). Estimande : \(\Delta = \mathbb{E}[D_g]\) sur la population des groupes.

**Pourquoi apparier.** \(\mathrm{Var}(D_g) = \mathrm{Var}(\bar Y^{(c)}) + \mathrm{Var}(\bar Y^{(b)}) - 2\,\mathrm{Cov}\). Les deux releases passent le même groupe : la difficulté du groupe crée une covariance positive qui **réduit** la variance de la différence.

**Pourquoi le groupe et non l'exécution.** Les \(m_g\) exécutions d'un groupe sont corrélées (même situation). Compter \(n = \sum m_g\) observations indépendantes sous-estimerait la variance. Avec corrélation intra-groupe \(\rho\), la variance d'une moyenne de \(m\) valeurs est \(\frac{\sigma^2}{m}(1 + (m-1)\rho)\) : si \(\rho\) est grand, \(m\) répétitions valent à peine plus qu'une.

**Code.** `stats/paired.py::group_rates`, `paired_comparison`.

## 3. Inégalité de Hoeffding et décision de non-infériorité (S05) — AXM 03-C06, 04-C04

**Énoncé.** \(X_1..X_n\) indépendantes, \(X_i \in [a, b]\), \(\bar X\) leur moyenne, \(\mu = \mathbb E[\bar X]\). Pour \(t > 0\) : \(P(\bar X - \mu \le -t) \le \exp\!\left(-\frac{2 n t^2}{(b-a)^2}\right)\).

**Esquisse de preuve.** Méthode de Chernoff : pour \(\lambda > 0\), \(P(\mu - \bar X \ge t) \le e^{-\lambda t}\,\mathbb E[e^{\lambda(\mu - \bar X)}]\) (inégalité de Markov sur l'exponentielle). Par indépendance, l'espérance se factorise. Le lemme de Hoeffding borne chaque facteur : pour une variable centrée dans un intervalle de largeur \(w\), \(\mathbb E[e^{s Z}] \le e^{s^2 w^2/8}\). On obtient \(\exp(-\lambda t + \lambda^2 w^2/(8n))\), minimisé en \(\lambda = 4nt/w^2\), d'où \(\exp(-2nt^2/w^2)\).

**Rayon.** Poser la borne égale à \(\alpha\) : \(t = w\sqrt{\ln(1/\alpha)/(2n)}\). Avec \(w = 2\) (car \(D_g \in [-1,1]\)) : \(t = 2\sqrt{\ln(1/\alpha)/(2n)} = \sqrt{2\ln(1/\alpha)/n}\).

**Vérification numérique (données réelles).** \(n = 27\), \(\alpha = 0{,}05\), \(\ln 20 = 2{,}9957\) : \(t = \sqrt{2 \times 2{,}9957/27} = \sqrt{0{,}22190} = 0{,}4711\). Le fichier `reports/s05/compare_r1-baseline_r4-guarded.json` contient `hoeffding_radius = 0.4711`.

**Décision.** Hypothèse défavorable \(H_0 : \Delta \le -m\). On conclut à la non-infériorité si \(\bar D - t > -m\). Sous \(H_0\), \(P(\bar D - t > -m) \le P(\bar D - \Delta > t) \le \alpha\) : le risque de fausse promotion est au plus \(\alpha\).

**Taille nécessaire.** \(\bar D - t > -m \iff n > \frac{w^2 \ln(1/\alpha)}{2(\bar D + m)^2}\). Réel : r1→r4, \(\bar D = -0{,}0123\), \(m = 0{,}10\) : \(n > 4 \times 2{,}9957/(2 \times 0{,}0877^2) \approx 780\).

**Hypothèses et limites.** Indépendance des groupes (nos groupes viennent de 18 familles : ceux d'une même famille partagent un modèle de question, l'indépendance est approximative). Borne valable pour tout \(n\), mais conservatrice : elle n'utilise que la largeur \(w\), pas la variance réelle (une borne de Bernstein ou empirique-Bernstein serait plus serrée).

## 4. Bootstrap groupé (S05, S09) — AXM 04-C05

**Principe.** Approcher la loi de \(\bar D\) en tirant \(G\) groupes **avec remise** parmi les \(G\) observés, \(B\) fois, et prendre les quantiles 2,5 % et 97,5 % des moyennes obtenues (intervalle percentile).

**Pourquoi par groupe.** Rééchantillonner les exécutions casserait la dépendance intra-groupe et donnerait un intervalle trop étroit.

**Réel.** r2→r4 : \([0{,}019 ; 0{,}148]\) alors que Hoeffding donne une borne inférieure de −0,391 : le bootstrap est bien plus étroit, mais c'est une **approximation** (justifiée asymptotiquement, discutable à 27 groupes). C'est pourquoi la décision utilise Hoeffding.

**Code.** `stats/paired.py` (L96–L99), `ml/baselines.py::group_bootstrap`.

## 5. Borne exacte de Clopper-Pearson (S05, S07) — AXM 04-C04 (« borne binomiale exacte »)

**Énoncé.** \(k\) succès sur \(n\) essais de Bernoulli indépendants. Borne supérieure unilatérale à \(1 - \alpha\) : le plus grand \(p\) tel que \(P(X \le k \mid p) = \sum_{i=0}^{k}\binom{n}{i}p^i(1-p)^{n-i} > \alpha\). La fonction décroît en \(p\), d'où la bissection.

**Cas \(k = 0\).** \((1-p)^n = \alpha \Rightarrow p = 1 - \alpha^{1/n}\). Pour \(n = 27\) : \(1 - 0{,}05^{1/27} = 1 - e^{-2{,}9957/27} = 1 - e^{-0{,}11095} = 0{,}105\) — le rapport affiche « ≤ 11 % » pour 0/27 brèche de r4. Pour \(n = 9\) : \(1 - 0{,}05^{1/9} = 0{,}283\) (« ≤ 28 % »).

**Limite.** Les tirages d'un même scénario sont corrélés : l'effectif utile est plus petit que \(n\), la borne vraie plus haute.

## 6. Régression logistique, log loss, Brier (S09) — AXM 05-C03, 05-C04, 06-C01

**Modèle.** \(p(x) = \sigma(w^\top x + b)\), \(\sigma(z) = 1/(1 + e^{-z})\).

**Perte (log loss).** \(\ell(w) = -\frac1n\sum_i [y_i \ln p_i + (1-y_i)\ln(1-p_i)] + \frac{1}{2Cn}\|w\|^2\) (forme proportionnelle à celle de scikit-learn). C'est l'entropie croisée : maximiser la vraisemblance d'un modèle de Bernoulli.

**Gradient.** Comme \(\sigma'(z) = \sigma(z)(1-\sigma(z))\), \(\partial \ell / \partial w = \frac1n \sum_i (p_i - y_i)\,x_i + \frac{w}{Cn}\). La perte est convexe : un minimum global unique, atteint par l'optimiseur (`lbfgs`).

**C.** Petit \(C\) = forte régularisation. Choisi par validation croisée groupée sur l'entraînement (`select_c`) : C = 1 retenu.

**Brier.** \(\frac1n\sum (p_i - y_i)^2\). Score propre : il est minimisé en espérance par la vraie probabilité. Une prédiction constante égale à la prévalence \(\pi\) donne \(\pi(1-\pi)\) : réel, \(0{,}54 \times 0{,}46 \approx 0{,}248\), proche des 0,256 de la baseline majoritaire (dont \(\pi\) vient de l'entraînement, pas du test).

**PR-AUC (précision moyenne).** \(\sum_k (R_k - R_{k-1}) P_k\) sur les seuils. Une prédiction aléatoire vaut en moyenne la prévalence (≈ 0,54 ici), d'où la baseline majoritaire à 0,542.

**Vérification (test unitaire).** \(y = (0,0,1,1)\), \(p = (0{,}1 ; 0{,}4 ; 0{,}35 ; 0{,}8)\) : ROC-AUC = 3 paires bien ordonnées sur 4 = 0,75 ; PR-AUC = \((1 + 2/3)/2 = 0{,}833\) (`tests/test_ml_s09.py::test_metrics_on_known_values`).

## 7. TF-IDF (S09)

\(\mathrm{tfidf}(t, d) = (1 + \ln \mathrm{tf}_{t,d}) \cdot \left(\ln\frac{1+N}{1+\mathrm{df}_t} + 1\right)\), puis normalisation L2 (`sublinear_tf=True`, valeurs par défaut de scikit-learn). Le vocabulaire et les \(\mathrm{df}\) sont appris sur l'entraînement uniquement ; un mot nouveau au test est ignoré (test `test_featurizer_learns_vocabulary_from_train_only`).

---

## 8. Préparation S10 — rétropropagation dans un GRU (non implémenté) — AXM 05-C05, 05-C07, 02-C02

GRU : \(z_t = \sigma(W_z x_t + U_z h_{t-1})\), \(r_t = \sigma(W_r x_t + U_r h_{t-1})\), \(\tilde h_t = \tanh(W x_t + U(r_t \odot h_{t-1}))\), \(h_t = (1 - z_t)\odot h_{t-1} + z_t \odot \tilde h_t\). La rétropropagation dans le temps applique la règle de la chaîne à travers \(t\) ; la porte \(z_t\) limite la disparition du gradient. **Masquage** : les positions de remplissage ne doivent contribuer ni à la perte ni au dernier état utilisé. **Vérification à faire** : comparer gradient analytique et différences finies \(\frac{\ell(w+\varepsilon) - \ell(w-\varepsilon)}{2\varepsilon}\) (AXM 05-C05).

## 9. Préparation S11 — attention (non implémenté) — AXM 05-C08

\(\mathrm{Attention}(Q,K,V) = \mathrm{softmax}(QK^\top/\sqrt{d_k} + M)V\) ; \(M\) vaut \(-\infty\) aux positions masquées. Le facteur \(1/\sqrt{d_k}\) garde la variance des scores proche de 1 quand les composantes sont de variance 1 (somme de \(d_k\) produits). Coût \(O(L^2 d)\) en longueur \(L\).

## 10. Préparation S13 — perte contrastive InfoNCE (non implémenté) — AXM 05-C09

\(\ell_i = -\ln \frac{\exp(\mathrm{sim}(z_i, z_i^+)/\tau)}{\sum_{k} \exp(\mathrm{sim}(z_i, z_k)/\tau)}\). *Collapse* : si toutes les représentations sont égales, la perte vaut \(\ln K\) et ne diminue plus ; surveiller la variance des représentations.

## 11. Préparation S15–S16 — calibration et prédiction conforme (non implémenté) — AXM 06-C01, 06-C04

ECE à \(B\) classes : \(\sum_b \frac{n_b}{n}|\mathrm{acc}_b - \mathrm{conf}_b|\) (dépend du découpage annoncé). Conformal split : scores \(s_1..s_n\) sur la calibration, \(\hat q\) = le \(\lceil (n+1)(1-\alpha)\rceil\)-ième plus petit ; sous **échangeabilité**, \(P(Y \in C(X)) \ge 1 - \alpha\). Exemple : \(n = 100\), \(\alpha = 0{,}1\) → \(\lceil 90{,}9 \rceil = 91\)-ième score. La garantie disparaît sous changement de release si l'échangeabilité ne tient plus.

## 12. Préparation S17–S18 — décision coûteuse et OOD (non implémenté) — AXM 03-C07, 06-C05, 01-C08

Décision bayésienne : envoyer en revue si \(p \cdot c_{\text{faux PROMOTE}} > (1-p)\cdot c_{\text{revue inutile}}\), soit \(p > \frac{c_r}{c_r + c_f}\). Distance de Mahalanobis \(d(x) = \sqrt{(x-\mu)^\top \Sigma^{-1}(x-\mu)}\) avec \(\Sigma\) régularisée \(\Sigma + \lambda I\) (inversibilité, AXM 01-C08).
