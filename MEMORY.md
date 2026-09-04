# Récapitulatif du projet

Ce fichier retrace ce qui a été fait sur Polymarket France, pour garder le contexte
entre sessions (et entre machines). Pour le fonctionnement général, voir `README.md`
et `CLAUDE.md`.

## État actuel

- **Repo GitHub** : https://github.com/Melud/polymarket-france (public)
- **Site en ligne** : https://polymarket-france.vercel.app/
- **Collecte** : GitHub Actions, cron horaire (`.github/workflows/update-data.yml`)
- **Déploiement** : Vercel, connecté au repo GitHub — chaque push sur `master`
  (y compris les commits automatiques du bot de collecte) redéploie le site
  automatiquement. Root Directory du projet Vercel = `site`.

## Historique des étapes

### 1. Mise en route initiale
- Le script de collecte (`collector/fetch_markets.py`) fonctionne avec `uv run`,
  en s'appuyant sur le `.venv` local (pas de PEP 723 inline en pratique, malgré ce
  qu'indiquait le `CLAUDE.md` initial — `requirements.txt` classique + venv).
- Le bug SSL/ANJ décrit initialement dans `CLAUDE.md` ne s'est pas manifesté :
  l'API Gamma de Polymarket a répondu normalement depuis cette machine.
- Site Astro testé en local (`npm install && npm run dev`), fonctionne sur le port 4321.
- **Point d'attention machine** : Node.js/npm et GitHub CLI (`gh`) ne sont pas
  toujours dans le PATH des shells bash/PowerShell utilisés par l'outil, alors
  qu'ils fonctionnent dans `cmd`. Contournement : appeler les binaires par leur
  chemin complet (`C:\Program Files\nodejs\...`, `C:\Program Files\GitHub CLI\gh.exe`).

### 2. Mise sur GitHub
- Repo créé et poussé via GitHub CLI (`gh repo create ... --push`).
- Un premier push du workflow `.github/workflows/update-data.yml` a échoué avec
  `refusing to allow an OAuth App to create or update workflow ... without workflow scope`
  → résolu avec `gh auth refresh -s workflow`.
- **Bug rencontré** : après le premier push, le workflow n'apparaissait pas dans
  l'API/UI GitHub Actions (`workflows` list vide), alors que le fichier était bien
  présent sur la branche par défaut. Résolu en renommant le `name:` du workflow et
  en repoussant — GitHub a alors correctement indexé le fichier. Cause exacte non
  identifiée (possible délai/bug d'indexation côté GitHub sur un repo tout neuf).
- Workflow testé manuellement (`gh workflow run`) et confirmé fonctionnel : la
  collecte tourne bien depuis les runners GitHub (hors France), contournant le
  blocage ANJ qui affecte l'accès direct depuis la France.

### 3. Déploiement Vercel
- La connexion CLI (`vercel login`) échoue en environnement non-interactif (elle
  attend un choix de méthode de connexion). Solution retenue : import du repo
  directement depuis le dashboard web (https://vercel.com/new), avec Root
  Directory réglé sur `site`. Détection auto du framework Astro, déploiement
  continu à chaque push GitHub.

### 4. Backfill de l'historique des cotes
- Constat : l'API Gamma ne donne que le prix courant, pas d'historique.
- Solution : l'**API CLOB** de Polymarket (`clob.polymarket.com/prices-history`)
  conserve l'historique complet par candidat depuis la création du marché, via
  le `clobTokenId` de chaque sous-marché (accessible dans la réponse Gamma).
- Script ponctuel ajouté : `collector/backfill_history.py`. Ne backfille que les
  candidats dont le prix courant dépasse 1 % (`SIGNIFICANCE_THRESHOLD`), pour
  éviter de charger ~40 candidats à 0,15 % qui n'ont jamais bougé. Résultat :
  12 candidats significatifs, 274 jours d'historique ajoutés (depuis le
  12/11/2025, date de création du marché).
- Les séries par candidat ont des timestamps non alignés (CLOB) → fusionnées en
  snapshots journaliers synchronisés avec forward-fill (dernier prix connu
  reporté tant qu'il n'y a pas de nouveau point ce jour-là), pour rester
  compatible avec le format existant de `data/markets.json` sans toucher au
  code du site.

### 5. Améliorations UI
- Liste des candidats : 6 affichés par défaut + bouton « Voir X de plus » pour
  dérouler le reste (`MarketCard.astro`).
- Graphique (Chart.js) :
  - hauteur augmentée (320px) pour la lisibilité,
  - labels de dates sans les heures, au format JJ/MM/AA (année sur 2 chiffres
    ajoutée pour lever l'ambiguïté sur un historique qui dépasse un an),
  - échelle Y qui s'arrête juste au-dessus du prix max réel des séries
    affichées plutôt que d'être fixée à 100 %,
  - ligne verticale en pointillés au survol + tooltip listant tous les
    candidats, leurs cotes et la date à la position survolée (`interaction:
    mode "index"` + plugin Chart.js personnalisé `crosshairPlugin`).
- Couleurs par candidat alignées sur les nuances politiques (Wikipédia) plutôt
  qu'arbitraires — `site/src/lib/candidateColors.ts` (ajouté depuis une autre
  machine, mergé sans conflit).
  - Source : `Modèle:Infobox Parti politique français/couleurs` sur Wikipédia
    (couleur de nuance, pas de candidat — deux candidats du même parti
    partagent donc la même couleur).
  - Palette : codes Wikipédia stricts, sans altération — RN `#0D378A`
    (Bardella, Le Pen) · LR `#0066CC` (Retailleau, Lisnard) · Horizons
    `#0001B8` (Philippe) · Renaissance `#FFEB00` (Attal) · LFI `#CC2443`
    (Mélenchon) · Place Publique `#FFC0C0` (Glucksmann) · PS `#FF8080`
    (Hollande) · sans étiquette `#999999` (Villepin, faute de couleur
    officielle) · repli générique `#4f8cff` pour tout nom non reconnu.
  - Un essai précédent avait éclairci RN/LR/Horizons (trop proches du noir
    sur fond sombre) mais l'utilisateur a préféré l'inverse : garder les
    couleurs Wikipédia telles quelles et changer le **fond du site** plutôt
    que les couleurs de parti (voir juste en dessous).
  - Couleur transmise à la fois aux barres de score (`MarketCard.astro`) et
    aux courbes Chart.js (`index.astro`, via un champ `color` ajouté à
    `chartData.series`).
- Pourcentages arrondis à l'unité (plus de décimale) sur les barres de score
  et dans les données passées au graphique (`Math.round(price * 100)` au lieu
  de `Math.round(price * 1000) / 10`).
- **Bug de timezone corrigé** : `toLocaleString`/`toLocaleDateString` sans
  `timeZone` explicite convertissent l'UTC stocké dans `data/markets.json`
  selon le fuseau du serveur qui *build* le site, pas un fuseau français fixe
  — d'où un « Maj : ... » décalé de 2h sur le déploiement Vercel (build en
  UTC) par rapport à un build local (Paris, UTC+2 l'été). Fix : `timeZone:
  "Europe/Paris"` ajouté dans `MarketCard.astro` (heure de mise à jour) et
  `index.astro` (dates de l'axe du graphique).
- **Thème du site passé de sombre à clair** (fond `#f4f3f0`, cartes blanches,
  texte `#1a1a1a`) pour que les couleurs de parti Wikipédia (bleus foncés
  RN/LR/Horizons compris) restent lisibles sans avoir à être modifiées.
  Touché : `body`/`.intro` dans `index.astro`, `.card`/`.bar-track`/
  `.toggle-btn`/`footer` dans `MarketCard.astro`, et les couleurs du tooltip
  + de la ligne de crosshair Chart.js (fond blanc, texte foncé). Vérifié en
  local via capture d'écran (Edge headless).

### 7. Bug critique trouvé et corrigé : le graphique ne s'est jamais affiché en production
- En voulant vérifier 3 ajustements demandés sur le graphique (voir ci-dessous),
  build de prod (`npm run build` + `astro preview`) testé pour la première
  fois — jusque-là, tout avait été vérifié via `astro dev` uniquement.
- **Découverte** : dans le HTML généré par `astro build`, la balise
  `<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>` disparaît
  entièrement — Astro tente de la traiter comme un script à bundler (elle n'a
  pas la directive `is:inline`) et la supprime silencieusement puisqu'une URL
  externe n'est pas un module local résolvable. Confirmé en rechargeant le
  commit HEAD tel quel (clean build) ET en inspectant directement le HTML
  servi par `https://polymarket-france.vercel.app/` avec `curl` : le tag est
  bien absent du site en ligne. Résultat concret : `Chart` n'était jamais
  défini côté navigateur, `Chart.register(...)` levait une exception, et
  **aucun graphique en courbes ne s'est jamais affiché sur le site déployé**
  depuis la création du projet (seules les barres de score fonctionnaient).
- Fix : `<script is:inline src="...">` sur cette balise — indique à Astro de
  la laisser telle quelle sans essayer de la bundler. Vérifié avec un script
  Puppeteer piloté via `msedge.exe` local (`puppeteer-core`, sans télécharger
  de nouveau navigateur) : canvas correctement dimensionné (670×320, contre
  300×150 par défaut avant le fix) et rempli de pixels réels après le fix.
- **Point de vigilance pour la suite** : tester un changement Astro touchant
  aux `<script>`/`<style>` uniquement via `astro dev` ne suffit pas — le mode
  dev et le build statique de prod peuvent diverger. Faire un
  `npm run build && npm run preview` au moins une fois avant de considérer un
  changement de ce type comme vérifié.

### 8. Ajustements du graphique (marché "second tour")
- Axe Y : plafond désormais arrondi à la **dizaine** (au lieu de 5), plafonné
  à 100 % — pour n'avoir que des tranches de 10 % au lieu de valeurs comme 95%.
- Légende : marqueurs changés de carrés creux (`fillStyle` transparent +
  `strokeStyle` coloré, artefact du `backgroundColor: "transparent"` des
  datasets) à des traits de couleur, via `legend.labels.usePointStyle: true` +
  `pointStyleWidth: 20` + `pointStyle: "line"` sur chaque dataset.
- Points au survol : cercles creux → disques pleins, en fixant
  `pointBackgroundColor`/`pointBorderColor` (et leurs variantes `Hover`) à la
  couleur du candidat avec `pointBorderWidth: 0`.
- **Bug introduit puis corrigé** : `pointStyle: "line"` posé au niveau du
  dataset affecte à la fois la légende ET les points réels du graphique —
  du coup les points de survol étaient devenus des traits au lieu de disques
  (l'inverse de ce qui était demandé), et avec `pointBorderWidth: 0` le trait
  de la légende devenait invisible (aucune couleur visible) dans un vrai
  navigateur. Fix : retirer `pointStyle` du dataset (les points de survol
  retrouvent leur style par défaut `circle`, remplis en disque plein comme
  voulu) et gérer le rendu en traits de la légende séparément via un
  `legend.labels.generateLabels` personnalisé (`fillStyle`/`strokeStyle` =
  couleur du candidat, `lineWidth: 3`, `pointStyle: "line"`), indépendant de
  la config des points du graphique.

### 9. Tri dynamique de l'infobulle au survol
- Demande : au survol du graphique, la liste des candidats dans l'infobulle
  doit être triée du plus probable au moins probable **à la date survolée**,
  pas dans l'ordre fixe du classement final (la légende, elle, reste dans
  l'ordre fixe du dernier prix connu — c'est normal, seule l'infobulle doit
  changer).
- Fix : `tooltip.itemSort: (a, b) => (b.raw ?? 0) - (a.raw ?? 0)`. Vérifié en
  survolant une date ancienne (05/06/26) où Jordan Bardella était à 78% et
  Marine Le Pen à 13% (alors qu'elle mène largement aujourd'hui) : Bardella
  apparaît bien en tête de l'infobulle à cette date-là.

### 10. Troisième marché ajouté : primaire du Parti socialiste
- `socialist-party-of-france-presidential-nominee-20260710182042067`
  ("Candidat du Parti socialiste") ajouté dans `config.json`. Même routine
  que les précédents : `fetch_markets.py` (déjà générique) le couvre
  automatiquement pour la collecte horaire, `backfill_history.py` a ajouté
  48 jours d'historique (14/07/2026 → veille), 9 candidats significatifs.
- Ce marché a aussi des sous-marchés `active: false` ("Person D" à "Person
  AO", "Other" — des emplacements réservés non utilisés) : déjà filtrés par
  le fix `active`/`archived` mis en place pour le marché "second tour", rien
  à refaire.
- **Bug trouvé et corrigé** : ce marché orthographie certains noms sans
  accent ("Raphael Glucksmann", "Francois Hollande") alors que les deux
  autres marchés utilisent les accents ("Raphaël", "François") — la
  correspondance exacte de `candidateColors.ts` les ratait donc, ces deux
  candidats retombaient sur le gris de repli au lieu de leur vraie couleur.
  Fix : `candidateColor()` compare désormais les noms normalisés (accents
  retirés via `.normalize("NFD").replace(/\p{Diacritic}/gu, "")`) plutôt que
  les chaînes brutes. Vérifié avec les couleurs CSS calculées réellement dans
  le navigateur (`rgb(255,192,192)` pour Glucksmann, `rgb(255,128,128)` pour
  Hollande), pas seulement à l'œil sur une capture.
  - Point de vigilance pour cette regex : écrire une classe de caractères
    avec des accents combinants **littéraux** (copiés-collés) dans le code
    source s'est révélé fragile — le résultat dépend de l'encodage utilisé
    pour relire le fichier (cassé différemment selon Node vs PowerShell dans
    mes tests). Toujours préférer une syntaxe ASCII pure comme
    `\p{Diacritic}` (ou un échappement `\u....` explicite) pour ce genre de
    regex Unicode.

### 11. Couleurs individuelles pour la primaire PS
- Constat de l'utilisateur : tous les candidats du marché "Candidat du Parti
  socialiste" sont logiquement de la même nuance (PS), donc avec la
  convention habituelle ils tomberaient tous sur le même rose ou sur le gris
  de repli — illisible pour un graphique où ils s'affrontent entre eux.
- Deux options proposées (nuancier rose/bordeaux vs palette catégorielle
  distincte), l'utilisateur a choisi la **palette catégorielle**. Raphaël
  Glucksmann et François Hollande gardent leurs couleurs déjà établies
  (Place Publique `#FFC0C0`, PS `#FF8080`, utilisées aussi dans les deux
  autres marchés) ; les 8 autres candidats reçoivent chacun une teinte
  arbitraire mais distincte, choisie pour ne pas entrer en collision avec les
  couleurs de parti utilisées ailleurs sur le site (Faure `#2E8B57` vert,
  Brun `#8E44AD` violet, Royal `#E67E22` orange, Bouamrane `#16A085`
  turquoise, Vallaud `#6D4C41` marron, Guedj `#B7950B` ocre, Cazeneuve
  `#34495E` ardoise, Delga `#9B59B6` mauve).
- Vérifié en conditions de prod : les 10 couleurs calculées dans le
  navigateur sont bien toutes distinctes (bouton "Voir 4 de moins" déplié).
- **Évolution demandée juste après** : l'utilisateur voulait en fait que ce
  marché ait un code couleur **totalement indépendant**, y compris pour
  Glucksmann et Hollande (qui gardaient jusque-là leurs couleurs globales
  Place Publique/PS). `candidateColor()` a donc été étendue avec un second
  paramètre optionnel `marketSlug` ; `candidateColors.ts` définit désormais
  `MARKET_PALETTES`, une palette dédiée par slug qui prend le pas sur
  `CANDIDATE_COLORS` quand elle existe pour ce marché — une même personne
  peut ainsi avoir une couleur différente d'un marché à l'autre, en toute
  cohérence avec le fait que ce marché-ci oppose des candidats du même parti
  entre eux. Palette complète pour
  `socialist-party-of-france-presidential-nominee-...` : Glucksmann
  `#D6482B` (vermillon), Hollande `#1F6F8B` (bleu pétrole), les 8 autres
  inchangés. `MarketCard.astro` passe désormais `slug` à chaque appel de
  `candidateColor()`. Vérifié : les deux autres marchés gardent bien les
  couleurs globales d'origine pour ces deux candidats, seul le marché PS
  utilise la nouvelle palette indépendante.

## Permissions outillage

- `.claude/settings.json` (suivi par git, distinct de `settings.local.json`)
  contient un allowlist de commandes lecture-seule fréquemment utilisées
  (`gh api`, `gh run view`, `curl -s`, `Set-Location`, `Test-Path`) pour réduire
  les demandes de confirmation répétées.

### 6. Deuxième marché ajouté
- `next-french-presidential-election-who-will-advance-to-the-2nd-round`
  ("Qui accédera au second tour ?") ajouté dans `collector/config.json` —
  même principe que le premier marché (un sous-marché binaire par candidat),
  donc compatible tel quel avec `extract_outcomes()`.
- **Bug trouvé et corrigé** : le sous-marché "Other" ("Will another person
  advance...") apparaissait sur notre site (~33%) alors qu'il n'apparaît pas
  sur la page Polymarket elle-même. Cause : c'est le seul sous-marché avec
  `"active": false` / `"archived": true` — Polymarket le masque de sa propre
  UI, et son `outcomePrices` est obsolète (le vrai dernier prix négocié,
  `lastTradePrice`, était de 9%, pas 32,5%). Fix dans
  `extract_outcomes()` (`fetch_markets.py`) : on ignore désormais tout
  sous-marché avec `active: false` ou `archived: true`, comme le fait
  Polymarket. À garder en tête pour tout futur marché à sous-marchés
  multiples — vérifier les flags `active`/`archived` si un outcome semble
  incohérent avec la page Polymarket.
- Beaucoup de candidats de ce marché (Bompard, Knafo, Cazeneuve, Faure,
  Roussel, Borne, Lecornu, Darmanin, Barnier, Panot, Wauquiez, Bayrou,
  Zemmour, Autain, Delga, Ruffin, Braun-Pivet, Asselineau, Bertrand, Royal,
  Tondelier, Pécresse, Castex, Guetté...) n'ont pas de couleur dédiée dans
  `candidateColors.ts` → repli générique. Seuls les 6 premiers outcomes sont
  affichés par défaut donc l'impact visuel immédiat est faible, mais à
  étoffer si on veut une couleur fidèle pour tout le monde.
- `FALLBACK_COLOR` changé de bleu (`#4f8cff`) à gris neutre (`#999999`,
  identique à la couleur "sans étiquette" de Villepin) — un candidat non
  mappé n'a pas de couleur arbitraire, juste l'absence de nuance connue.
- Testé en local : `.venv` créé (`python -m venv .venv` + `pip install -r
  collector/requirements.txt`, absent sur cette machine avant), collecteur
  lancé manuellement, site vérifié par capture d'écran — les deux cartes de
  marché s'affichent correctement, couleurs et pourcentages cohérents.
- **Collecte horaire** : rien à ajouter au workflow — `fetch_markets.py`
  boucle déjà sur toutes les entrées de `config.json`, donc le cron existant
  (`update-data.yml`, toutes les heures) couvre ce nouveau marché
  automatiquement dès qu'il est dans `config.json`.
- **Backfill historique** : `collector/backfill_history.py` boucle lui aussi
  sur tous les marchés de `config.json` (pas besoin de le paramétrer par
  marché). Relancé après le fix "Other" (voir juste au-dessus, même filtre
  `active`/`archived` ajouté ici) : 90 jours ajoutés pour ce marché
  (02/06/2026 → 30/08/2026, création du marché → veille), 35 candidats
  significatifs (seuil 1%), aucun conflit avec l'historique du premier
  marché (déjà couvert, ignoré).

### 12. Quatrième marché ajouté : un marché binaire, avec un style de carte dédié
- `will-france-pass-a-national-budget-by-december-31` ("Le budget sera-t-il
  voté avant le 31 décembre ?") — contrairement aux 3 précédents, ce n'est
  pas une course à plusieurs candidats mais un marché Oui/Non simple
  (`len(markets) == 1`, outcomes `["Yes","No"]`).
- L'utilisateur voulait un **style visuel différent** pour ce type de
  marché plutôt que de le forcer dans le format "liste de barres". Deux
  options proposées (jauge/gros pourcentage vs barre unique Oui/Non),
  l'utilisateur a choisi la **jauge circulaire**.
- Mécanisme choisi pour distinguer les styles : un champ `"style":
  "binary"` dans `config.json` par marché (défaut implicite : `"candidates"`),
  propagé dans `data/markets.json` par `fetch_markets.py` ET
  `backfill_history.py` (`record["style"]`) pour que le choix de composant
  se fasse uniquement à partir des données déjà chargées, sans re-parser
  `config.json` côté site.
- Nouveau composant `site/src/components/BinaryMarketCard.astro` : anneau
  conic-gradient CSS (pas de librairie) avec le pourcentage "Oui" au centre,
  légende "X% Non" en dessous, puis le même graphique Chart.js que les
  autres cartes (réutilise le script générique `renderCharts()` de
  `index.astro`, qui cible tout `canvas.chart` peu importe le composant
  d'origine). Couleur dédiée `#2A9D8F` (teal neutre) — volontairement pas
  une nuance de parti puisque ce marché ne concerne pas un candidat/parti.
  `index.astro` choisit `BinaryMarketCard` vs `MarketCard` selon
  `market.style === "binary"`.
- **Bug latent trouvé en généralisant** : `backfill_history.py` ne gérait
  jusque-là que le cas "plusieurs sous-marchés par candidat" — pour un
  marché à un seul sous-marché (Oui/Non), il aurait utilisé la question
  entière comme nom de "candidat" et ignoré un des deux outcomes,
  divergeant de `fetch_markets.py` qui gère déjà ce cas séparément.
  `significant_candidates()` a été alignée sur la même logique à deux
  branches (`len(markets) == 1` vs sous-marchés multiples) que
  `extract_outcomes()`. Backfill obtenu : 136 jours (28/03/2026 → veille).
- Vérifié en conditions de prod (build + Puppeteer) : jauge et graphique
  s'affichent correctement, pixels réels confirmés sur les 4 cartes (plus
  seulement à l'œil sur une capture).

### 13. Favicon
- Le site n'avait pas de favicon jusqu'ici. Demande : un remix du repère
  Polymarket (triangles imbriqués) recoloré aux couleurs du drapeau français.
- Itéré via un artifact de propositions (plusieurs allers-retours : d'abord
  trop éloigné du logo Polymarket, puis un souci de trou entre les
  triangles, puis un souci inverse de chevauchement/collision). Solution
  retenue : **trois triangles isocèles qui partagent exactement leurs
  arêtes** (mêmes coordonnées des deux côtés) plutôt que des triangles
  pleins qu'on fait se chevaucher approximativement — structurellement ni
  trou ni superposition possible, contrairement aux tentatives précédentes
  qui réglaient le chevauchement à la main. Forme finale : un trapèze
  (bleu à gauche, blanc en haut au milieu, rouge à droite), contour extérieur
  uniquement (pas d'arêtes internes tracées).
- Fichier : `site/public/favicon.svg` (viewBox 0 0 32 32, 3 `<polygon>` +
  contour). Branché via `<link rel="icon" type="image/svg+xml"
  href="/favicon.svg" />` dans le `<head>` de `index.astro`. Vérifié en
  conditions de build de prod (le fichier est bien copié dans `dist/`, le
  lien pointe bien dessus) + capture d'écran du SVG servi en taille réelle.

### 14. Motif de trait pour distinguer les courbes de couleur proche
- Retour utilisateur : sur le graphique, les courbes se ressemblent trop
  (bleus RN/LR/Horizons) — mais il veut **garder ces couleurs** (fidélité
  Wikipédia), pas les changer.
- Propositions faites (motif de trait / surbrillance légende au survol /
  étiquette en bout de courbe) — l'utilisateur a choisi le **motif de
  trait**, uniquement pour les couleurs qui se ressemblent.
- Implémenté : `candidateLineDash()` dans `candidateColors.ts`, une table
  séparée de `CANDIDATE_COLORS` (RN reste plein, LR passe en tirets
  `[6,4]`, Horizons en pointillés `[2,3]`) — les autres candidats
  n'ont pas besoin d'un motif puisque leurs couleurs sont déjà distinctes.
  `MarketCard.astro` ajoute `dash` à chaque série ; `index.astro` applique
  `borderDash` sur chaque dataset Chart.js, et le `generateLabels` de la
  légende lit aussi `ds.borderDash` (`lineDash`) pour que le motif apparaisse
  dans la légende, pas seulement sur la courbe.
- Vérifié en inspectant directement la config Chart.js réelle
  (`Chart.getChart(canvas).data.datasets`) plutôt qu'une capture d'écran :
  Philippe (Horizons) a bien `dash:[2,3]`, Le Pen/Bardella (RN, même
  couleur) restent à `dash:[]`. La capture plein-page a un souci de timing
  déjà connu cette session (le canvas se retrouve parfois vide au moment du
  screenshot alors que son contenu réel — vérifié via `getImageData` — est
  correct) ; ne pas s'y fier seule pour ce genre de vérification, préférer
  lire la config Chart.js ou les pixels du canvas directement.

### 15. Retour en arrière sur les motifs de trait → étiquettes en bout de courbe
- L'utilisateur n'a finalement pas aimé le motif de trait (section 14) et a
  demandé à tester l'option "étiquette en bout de courbe" proposée
  précédemment (indiquée comme "option 2" par l'utilisateur, mais correspond
  à la 3ᵉ option textuelle des propositions initiales — suivi de la
  description, pas du numéro).
- Motif de trait entièrement retiré (`candidateLineDash()`,
  `CANDIDATE_DASH`, `dash` dans `MarketCard.astro`, `borderDash`/`lineDash`
  dans `index.astro`) — retour à `candidateColors.ts` sans cette notion.
- Nouveau : plugin Chart.js `endLabelsPlugin` dans `index.astro` — dessine le
  nom du candidat directement à l'extrémité droite de sa courbe (couleur du
  trait), avec une séparation verticale minimale (12px) entre étiquettes pour
  éviter qu'elles se chevauchent quand plusieurs courbes finissent au même
  niveau. `layout.padding.right: 96` réservé sur le graphique pour laisser la
  place aux étiquettes. La légende du haut est conservée (elle permet aussi
  de masquer/afficher une courbe au clic), donc le nommage est temporairement
  redondant entre légende et étiquettes — pas retiré sans qu'on me le
  demande.
- **Outil de capture d'écran** : `page.screenshot({ clip: ... })` s'est
  montré peu fiable dans cet environnement (retourne une image blanche alors
  que `getImageData`/l'inspection de la config Chart.js confirment un rendu
  correct) — y compris après avoir essayé d'attendre plus longtemps ou de
  forcer un repaint. Contournement qui fonctionne de façon fiable : capture
  plein "viewport" (`fullPage:false`, sans `clip`) puis recadrage a
  posteriori avec Pillow (`Image.crop`). Préférer cette méthode aux tests
  `clip` pour toute vérification visuelle future de graphique.

### 16. Étiquettes de courbe : initiales en grand + rappel dans la légende
- Ajustement de la section 15 : au lieu du nom complet en bout de courbe,
  seulement les initiales, en plus gros/gras (`bold 13px` au lieu de `10px`),
  et un rappel "Nom complet (Initiales)" dans la légende du haut.
- `candidateInitials(name)` ajoutée dans `candidateColors.ts` : initiale de
  chaque mot séparé par espace/trait d'union, ex. "Jean-Luc Mélenchon" →
  "JLM", "Marine Le Pen" → "MLP", "Édouard Philippe" → "ÉP" (accent conservé
  sur la lettre, `toUpperCase()` le gère nativement). Calculée une fois côté
  build dans `MarketCard.astro` (`initials` ajouté à chaque série du
  graphique), pas recalculée côté client.
- `endLabelsPlugin` (index.astro) utilise `ds.initials ?? ds.label` — la
  carte binaire (marché budget, une seule série "Oui", pas d'`initials`
  fournie) retombe donc sur le nom complet sans qu'on ait eu besoin de la
  toucher. Marge droite réservée réduite de 96px à 36px (les initiales
  prennent beaucoup moins de place qu'un nom complet).
- Vérifié par capture d'écran (méthode fiable établie en section 15 :
  plein viewport sans `clip` + recadrage Pillow) : légende affiche bien
  "Marine Le Pen (MLP)" etc., bout de courbe affiche juste "MLP" en gras.

### 17. Navigation par catégories : onglets sticky
- Réflexion sur l'organisation de la liste à mesure qu'elle grandit. 4
  maquettes proposées via un artifact avec le contenu réel du site
  (sections groupées / onglets sticky / sommaire fixe à gauche / liste
  compacte dépliable) — l'utilisateur a choisi les **onglets sticky**.
- Nouveau champ `"category"` dans `config.json` par marché (`"Présidentielle"`
  pour les 2 marchés électoraux, `"Partis"` pour la primaire PS, `"Budget"`
  pour le marché budget), propagé dans `data/markets.json` par
  `fetch_markets.py`/`backfill_history.py` de la même façon que `"style"`
  (repli `"Autres"` si absent).
- `index.astro` calcule la liste des catégories présentes (ordre préféré
  Présidentielle → Partis → Budget, puis toute catégorie inconnue à la
  suite), affiche une barre de pills `position: sticky; top: 0` juste sous
  l'intro (masquée automatiquement s'il n'y a qu'une seule catégorie). Un
  clic sur une pill affiche/masque les `.card` selon leur attribut
  `data-category` (ajouté sur l'`<article>` dans `MarketCard.astro` et
  `BinaryMarketCard.astro`) — pas de rechargement de page, juste un
  toggle de `hidden`.
- Vérifié avec Puppeteer : clic sur "Présidentielle" ne laisse plus visibles
  que les 2 marchés électoraux (vérifié par le DOM, pas seulement à l'œil).

### 18. Cinq nouveaux marchés + fix des initiales pour les outcomes "date"
- Demande : dresser la liste de tous les marchés Polymarket tagués "France"
  (via `https://gamma-api.polymarket.com/events?tag_id=1378&closed=false`,
  tag "France" trouvé via `/tags/slug/france`) pour choisir quoi ajouter.
  32 marchés ouverts recensés, présentés en anglais groupés par thème avec
  échéance et volume. L'utilisateur en a choisi 5 :
  - `2027-french-presidential-election-who-will-be-on-the-ballot` → catégorie
    Présidentielle (candidats, 46 sous-marchés)
  - `french-presidential-election-who-will-announce-a-run-in-2026` →
    Présidentielle (candidats, 21 sous-marchés)
  - `macron-out-in-2025` → nouvelle catégorie **Gouvernement** (échéances,
    pas des candidats — voir plus bas)
  - `lecornu-out-as-french-pm-by-381` → Gouvernement (échéances)
  - `french-election-called-by` → Gouvernement (échéances ; porte en réalité
    sur une élection **législative** anticipée, pas la présidentielle — d'où
    le rattachement à Gouvernement plutôt qu'à Présidentielle malgré le nom)
  - Nouvel onglet "Gouvernement" apparu automatiquement dans la barre de
    pills (aucun code à toucher, juste la valeur `category` dans
    `config.json`).
- **Particularité structurelle** : ces 3 marchés "Gouvernement" ont des
  sous-marchés nommés par **échéance** ("December 31, 2026", "October 31")
  plutôt que par candidat — déjà géré tel quel par `extract_outcomes()`
  (même logique générique groupItemTitle), aucun changement de collecteur
  nécessaire. Aucun sous-marché archivé/fantôme trouvé dans ces 5 marchés
  (vérifié comme pour "Other" précédemment).
- **Bug trouvé et corrigé** : `candidateInitials()` (section 16) prenait la
  première lettre de chaque mot — pour des échéances, "December 31, 2026"
  et "December 31, 2025" donnaient toutes les deux "D32" (collision dans la
  légende et en bout de courbe), pareil pour "July 31, 2026"/"June 30, 2026"
  → "J32". Fix : détection d'un libellé de date (regex `Mois JJ[, AAAA]`) et
  reformatage en `JJ/MM/AA` (ou `JJ/MM` sans année), cohérent avec le format
  déjà utilisé sur l'axe du graphique. Vérifié directement dans la config
  Chart.js : les 5 échéances du marché Macron donnent maintenant 5 valeurs
  distinctes (31/12/26, 31/12/25, 31/07/26, 30/06/26, 31/10/25).

### 19. Retrait de 2 des 5 marchés ajoutés en section 18
- L'utilisateur est revenu sur son choix juste après : retrait de
  `macron-out-in-2025` ("Macron quittera-t-il le pouvoir ?") et
  `french-election-called-by` ("Une élection législative sera-t-elle
  annoncée ?"). Reste dans la catégorie "Gouvernement" : uniquement
  `lecornu-out-as-french-pm-by-381`.
- Point technique retenu : retirer une entrée de `config.json` ne suffit
  pas, `fetch_markets.py`/`backfill_history.py` n'effacent jamais les
  entrées disparues de `data/markets.json` (ils ne font qu'ajouter/mettre à
  jour ce qui est présent dans la config) — il faut supprimer manuellement
  la clé du JSON de données en plus de la retirer de `config.json`.

### 20. Masquer les échéances déjà résolues dans les marchés "date"
- Demande : sur "Lecornu quittera-t-il Matignon ?" (et tout futur marché du
  même type), les échéances passées ("July 31, 2026", "December 31, 2025"...
  toutes à 0 %) n'ont plus d'intérêt une fois la date dépassée.
- Plutôt que de parser/deviner la date exacte de chaque échéance (fragile —
  certaines n'ont pas d'année, ex. "October 31", "November 30", et
  deviner l'année aurait pu se tromper), le filtre se base sur le **prix** :
  `isDateLabel(name)` (nouvelle fonction exportée dans `candidateColors.ts`,
  réutilise la regex déjà en place pour `candidateInitials`) ET prix < 0,5 %
  → outcome masqué. Une échéance déjà passée sans que l'événement se soit
  produit retombe et reste à ~0 %, donc ce critère la capture correctement
  sans avoir besoin de connaître la date d'aujourd'hui ni l'année exacte du
  libellé.
- Important : ce filtre ne s'applique qu'aux outcomes qui **ressemblent à
  une date** (`isDateLabel`) — un candidat à 0 % dans un marché normal
  (présidentielle, primaire...) reste affiché, ce n'est pas la même
  information (une échéance à 0 % est morte ; un candidat à 0 % est juste
  peu probable, encore intéressant dans une course).
- Filtre appliqué une seule fois sur `outcomes` dans `MarketCard.astro`,
  avant le découpage visible/extra et avant le calcul de `topNames` pour le
  graphique — les échéances mortes disparaissent donc à la fois des barres
  et de la courbe. Vérifié : pour Lecornu, seules "December 31, 2026" (28,5 %)
  et "September 30, 2026" (1,35 %) restent affichées, les 6 autres
  échéances à 0 % ont disparu.

### 21. Couleurs globales manquantes : Faure (PS) et Arthaud (LO)
- Remarque de l'utilisateur : Olivier Faure et Nathalie Arthaud n'avaient
  pas de couleur dans les marchés "généraux" (présidentielle, second tour,
  ballot, annonce 2026) alors que leur parti est connu.
- Cause : ils sont apparus via les marchés ajoutés en section 18 (ballot,
  annonce 2026) et via la liste étendue du second tour — seuls les
  candidats des tout premiers marchés avaient été mappés dans
  `CANDIDATE_COLORS`, pas de mise à jour faite depuis.
- Ajoutés : Olivier Faure → `#FF8080` (PS, même couleur qu'Hollande —
  cohérent avec la convention "même parti = même couleur" du mapping
  global). Nathalie Arthaud → `#BB0000` (LO, code Wikipédia officiel du
  parti, trouvé dans `Modèle:Infobox Parti politique français/couleurs`,
  même source que le reste de la palette).
- Faure a aussi une couleur dédiée (`#2E8B57`, vert) dans
  `MARKET_PALETTES` pour le marché "Candidat du Parti socialiste" — les deux
  coexistent sans conflit, le lookup par marché passe avant le lookup
  global. Vérifié : `#FF8080` dans les 4 marchés généraux, `#2E8B57`
  uniquement dans la primaire PS.
- Reste potentiellement d'autres candidats des marchés à 21-46
  sous-marchés (ballot, annonce 2026) dont le parti est connu mais non
  mappé — pas fait de passe exhaustive, seulement les deux signalés.

### 22. Aperçus de lien (Open Graph) — texte dynamique, pas d'image
- Demande : faire en sorte que les previews façon WhatsApp affichent le
  contenu du site (le premier marché en exemple) plutôt que l'URL brute.
- Deux parties distinctes : titre/description (facile, sans risque) vs
  image de la vignette (le site n'a qu'un favicon SVG, WhatsApp veut du
  raster). Trois options proposées pour l'image (bannière statique / image
  générée dynamiquement au build / pas d'image) — l'utilisateur a choisi
  **pas d'image pour l'instant**.
- Implémenté dans `index.astro` : `og:title`/`og:description` +
  `twitter:card summary` (pas `summary_large_image`, qui suppose une image)
  + `<meta name="description">`, tous calculés au build à partir du
  **premier marché de la liste** et de son candidat en tête. Ordre inversé
  sur retour utilisateur juste après : la question du marché passe en
  premier, le candidat en tête ensuite (ex. "Qui remportera la prochaine
  élection présidentielle française ? — Marine Le Pen en tête avec 33%"),
  donc mis à jour à chaque rebuild horaire sans intervention. Le `<title>`
  de l'onglet reste volontairement statique
  ("Polymarket France — marchés prédictifs traduits") — seul l'aperçu de
  partage change, pas le titre d'onglet/favoris.
- Si une image est voulue plus tard : bannière statique (rapide) ou
  génération dynamique au build (plus de travail, nécessite une lib de
  rendu SVG→PNG type `satori`/`@vercel/og`).

### 23. Bouton "copier le lien direct" par marché
- Demande ambiguë au départ ("le lien direct de chaque pari") : lien par
  marché (carte entière) ou par candidat/option (chaque outcome a sa propre
  page Polymarket) ? L'utilisateur a choisi **un lien par marché**.
- Bouton 🔗 ajouté dans l'en-tête de chaque carte (`MarketCard.astro` et
  `BinaryMarketCard.astro`, à côté du titre), qui copie dans le
  presse-papiers une ancre vers CE site (`{origin}{pathname}#card-{slug}`,
  l'`id` de la carte existait déjà pour d'autres besoins). Retour visuel :
  le 🔗 devient ✅ 1,2s. Script partagé dans `index.astro` (comme le filtre
  par catégorie).
- **Point de robustesse** : `navigator.clipboard.writeText()` peut dans
  certains contextes (document pas au premier plan, permission en attente)
  ne jamais résoudre ni rejeter — testé en conditions réelles avec
  Puppeteer où `clipboard.readText()` restait bloqué indéfiniment (a
  nécessité de tuer les process msedge suspendus). Plutôt que `try/await`
  simple, le clic fait courir `navigator.clipboard.writeText()` contre un
  `Promise.race` avec un timeout de 800ms — si ça ne résout pas à temps,
  repli sur `window.prompt()` pour que l'utilisateur puisse copier le lien
  manuellement plutôt que de rester bloqué sans aucun retour. En pratique,
  `writeText()` seul (sans `readText()`) a fonctionné du premier coup dans
  le test headless — c'est bien `readText()` spécifiquement qui posait
  problème, pas `writeText()`, mais le filet de sécurité reste utile.

### 24. Ancre de carte masquée par la barre de pills sticky
- Bug remonté juste après la mise en place du bouton "copier le lien" :
  sauter sur `#card-slug` plaçait le haut de la carte **sous** la barre de
  pills sticky (~60px de haut, mesuré), donc le titre du marché restait cru
  sous le bandeau après un saut d'ancre.
- Fix : `.card { scroll-margin-top: 5rem; }` dans le style global
  d'`index.astro` — le navigateur laisse maintenant cette marge au-dessus
  de la carte visée au lieu de la coller sous la barre. Vérifié en
  mesurant les positions réelles avant/après (`cardTop` passe de -0.3px,
  caché, à 79.7px, bien en dessous du bas de la barre à 59.8px).

### 25. Titre OG simplifié
- Retour utilisateur sur le rendu réel de la preview (capture d'écran
  fournie) : le titre "Polymarket France — {titre du premier marché}" était
  trop long/pas voulu — juste "Polymarket France". `og:title`/
  `twitter:title` fixés à `"Polymarket France"` (constante, plus de suffixe
  dynamique). La description reste dynamique (question + candidat en tête),
  seul le titre est redevenu statique.

### 26. Page dédiée par marché — aperçu de lien correct au partage
- Demande : que le lien "copier" d'un marché donne un aperçu de partage
  affichant CE marché, pas toujours le premier de la liste.
- **Explication du blocage technique** : impossible avec une simple ancre
  (`#card-slug`) sur une seule page — les robots qui génèrent les previews
  (WhatsApp, etc.) lisent le HTML de l'URL exacte partagée sans jamais voir
  le fragment `#...` (jamais envoyé au serveur, jamais exécuté de JS). Seule
  solution : une page statique dédiée par marché, avec ses propres balises
  Open Graph.
- Implémenté : `site/src/pages/marche/[slug].astro` (route dynamique Astro,
  `getStaticPaths()` génère une page par entrée de `data/markets.json`,
  même mécanisme de lecture fichier que `index.astro`). `og:title`/`title`
  = titre du marché (contrairement à la page d'accueil qui reste
  volontairement générique "Polymarket France"), description dynamique
  identique (question + candidat en tête). Contenu de la page : lien
  "← Tous les marchés" + la carte du marché (même composant
  `MarketCard`/`BinaryMarketCard` que la page d'accueil) + le graphique.
- **Refactor pour éviter la duplication** : extrait `BaseLayout.astro`
  (le `<head>` avec meta/OG + le style global body/main/pillbar/back-link,
  paramétré par props `title`/`description`/`ogTitle`/`ogDescription`/`url`)
  et `ChartScripts.astro` (crosshair + endLabels + `renderCharts()` + le
  handler du bouton copier-lien), tous deux utilisés par `index.astro` ET
  `marche/[slug].astro`. Attention lors du split : le handler du bouton
  "Voir X de plus" est resté dans le propre `<script>` de `MarketCard.astro`
  (pas dupliqué dans `ChartScripts.astro`) — Astro dédoublonne déjà les
  scripts de composants par page, donc le dupliquer aurait attaché le même
  listener deux fois et cassé le toggle (clique → ouvre puis se referme
  aussitôt).
- Le bouton 🔗 pointe désormais vers `{origin}/marche/{slug}/` au lieu de
  `{pathname}#card-{slug}` — ancien lien par ancre remplacé, plus utilisé.
- Vérifié en conditions de prod (build + Puppeteer) : les 7 pages
  `/marche/{slug}/` sont bien générées, chacune avec son propre
  `og:title`/`og:description`, le graphique et le bouton copier
  fonctionnent sur la page dédiée, et la page d'accueil (barre de pills,
  filtre, 7 cartes) n'a rien perdu dans le refactor.

### 27. Lissage exponentiel (EMA) passé en prod, α=0,5
- Suite à la question d'un ami de l'utilisateur ("SMC comme The Economist ?"
  → Sequential Monte Carlo, technique de lissage bayésien des courbes de
  sondages) : discussion des méthodes de lissage possibles (SMA, EMA,
  médiane glissante, LOESS, Kalman, SMC) avec pour/contre, puis détail
  mathématique du lissage exponentiel simple (SES) à la demande de
  l'utilisateur ("je suis matheux") — récurrence, forme close en moyenne
  géométrique pondérée, retard moyen `(1-α)/α`, équivalence avec une SMA de
  `N` points via `α=2/(N+1)`, réduction de variance `α/(2-α)`, lien avec le
  filtre de Kalman en régime stationnaire (SES = cas particulier).
- Maquette dans un artifact (données réelles des 7 marchés, candidat le
  plus haut de chaque marché, brut + 3 niveaux de lissage superposés en
  épaisseur croissante, légende cliquable pour isoler une courbe sur tous
  les graphiques à la fois). Plage d'α ajustée sur retour utilisateur vers
  plus léger (0,5 / 0,25 / 0,1 au lieu de 0,333 / 0,133 / 0,065).
  - Bug rencontré et corrigé dans l'artifact : mauvais nom de fichier/version
    cdnjs pour Chart.js (`Chart.js/4.4.4/chart.umd.min.js` → 404 silencieux,
    donc zone de graphique vide). Version/casse correctes trouvées via
    `api.cdnjs.com/libraries?search=chart.js` : `Chart.js/4.5.1/chart.umd.min.js`.
- **Passé en prod avec α=0,5** (le plus léger testé, N≈3). Nouveau fichier
  `site/src/lib/smoothing.ts` (`ema()`, même formule que la maquette).
  Appliqué dans `MarketCard.astro` ET `BinaryMarketCard.astro`, uniquement
  sur les données du **graphique** — les barres de score et le pourcentage
  affiché restent le prix brut du dernier relevé, pas lissé (distinction
  volontaire : la jauge/barre doit montrer le vrai prix actuel, seule la
  courbe historique bénéficie du lissage).
- Vérifié précisément (pas juste visuellement) : valeurs de la courbe lissée
  comparées à la main pour les 15 premiers points de Marine Le Pen — chaque
  valeur correspond exactement au calcul théorique `s(t)=0,5·y(t)+0,5·s(t-1)`
  arrondi à l'entier le plus proche.

### 28. Investigation des écarts de mise à jour + cron décalé
- L'utilisateur a remarqué un "Maj" vieux de 3h sur le site. Vérifié via
  l'API GitHub (`api.github.com/repos/.../actions/workflows/.../runs`,
  188 runs récupérés sur 2 pages) : **tous les runs se terminent en
  succès**, ce n'est pas un plantage du script.
- Le vrai problème : le déclenchement `schedule` de GitHub lui-même. Rythme
  réel par jour : ~23/jour (quasi horaire) du 20 au 26 août, puis chute
  nette à ~2-6/jour à partir du 27 août — sans aucun changement de notre
  côté (le fichier du workflow n'a plus bougé depuis le 19/08, vérifié par
  `git log --follow`). C'est cohérent avec une dégradation connue et non
  documentée officiellement des workflows `schedule` sur les dépôts
  publics/gratuits, qui s'aggrave avec le temps indépendamment de
  l'activité réelle du dépôt.
- Décision : décaler quand même le cron de `0 * * * *` à `17 * * * *`
  (éviter le créneau `:00`, le plus chargé côté GitHub, comme recommandé
  dans leur documentation) — amélioration probablement partielle, pas une
  vraie garantie de retour à un rythme horaire. Une solution plus fiable
  (déclencheur externe type cron-job.org ou cron Vercel appelant
  `workflow_dispatch`) a été proposée mais pas retenue pour l'instant.

### 29. Intégration de Kalshi comme deuxième source de marchés
- Avant d'implémenter, exploré à la demande de l'utilisateur une maquette
  (artifact) des options d'intégration multi-plateformes (badge de source +
  double filtre thème/source combinable), affinée sur trois retours de
  layout successifs (badge à la place du bouton lien → badge empilé sous le
  bouton → badge finalement aligné sur la même ligne que le sous-titre,
  décision retenue et reproduite sur le vrai site).
- Recherche API : Kalshi (`api.elections.kalshi.com/trade-api/v2`) est
  publique, sans authentification. Un "event" Kalshi (ex. `KXFRENCHPRES-27`)
  contient un sous-marché binaire Oui/Non par candidat — même structure que
  le cas multi-sous-marchés de Polymarket. Prix courant : `last_price_dollars`
  sur chaque market (déjà une fraction 0–1, même convention que
  `outcomePrices` de Polymarket). Historique quotidien : endpoint
  `/series/{series}/markets/{ticker}/candlesticks` (bien plus riche que prévu :
  certains marchés Kalshi ont un historique quotidien continu depuis leur
  création, ex. 565 jours pour "Prochaine élection présidentielle française"
  contre une fenêtre bien plus courte côté Polymarket).
- 4 marchés Kalshi ajoutés (équivalents directs de marchés Polymarket déjà
  suivis, pas de correspondance trouvée côté Kalshi pour "budget" ni
  "annonce de candidature 2026") : `KXFRENCHPRES-27` (présidentielle),
  `KXFRPRESADVANCE-26APR18` (second tour), `KXFRPRESBALLOT-27JUN30`
  (bulletins 2027), `KXFRPSNOM-26OCT01` (nominé du bloc socialiste).
- `collector/config.json` : chaque entrée porte désormais un champ
  `"source"` (`"polymarket"` ou `"kalshi"`) ; les entrées Kalshi utilisent
  `series_ticker`/`event_ticker` au lieu de `slug` pour interroger l'API,
  mais gardent un `slug` (préfixé `kalshi-`) comme clé JSON/URL.
- Deux nouveaux scripts collecteurs, calqués sur le modèle Polymarket
  existant : `collector/fetch_kalshi.py` (snapshot courant, filtre les
  marchés `status != "active"`) et `collector/backfill_kalshi_history.py`
  (backfill quotidien via les candlesticks, même seuil de significativité
  1% et même logique de fusion/forward-fill que `backfill_history.py`).
  `fetch_markets.py`/`backfill_history.py` ignorent désormais explicitement
  les entrées `source != "polymarket"` (auparavant ils auraient tenté de
  fetcher un ticker Kalshi via l'API Gamma et échoué).
  Les deux scripts ont été exécutés en local avec succès : 565 jours
  backfillés pour le marché présidentiel, 49-53 jours pour les trois autres.
- `.github/workflows/update-data.yml` : ajout d'une étape "Fetch Kalshi
  markets" (`python collector/fetch_kalshi.py`) après celle de Polymarket,
  avant le commit — même cron, même dépendance (`requests`, déjà dans
  `requirements.txt`).
- Site : nouveau `site/src/lib/sources.ts` (`sourceLabel()`) : badge de
  plateforme ajouté dans `MarketCard.astro` et `BinaryMarketCard.astro`
  (aligné avec le sous-titre, comme validé sur la maquette), lien de pied de
  carte devenu dynamique (`Voir sur {Polymarket|Kalshi} ↗` au lieu du texte
  Polymarket en dur). Palette de couleurs `MARKET_PALETTES` du marché PS
  (candidateColors.ts) partagée entre la carte Polymarket et son équivalent
  Kalshi (même candidats, même palette dédiée). Texte d'intro de la page
  d'accueil mis à jour pour mentionner les deux plateformes.
- Vérifié en conditions quasi réelles : build Astro complet (11 marchés → 11
  pages `/marche/{slug}/` générées, aucune erreur), puis Puppeteer sur le
  site buildé servi en local — les 11 cartes s'affichent avec le bon badge
  (7 Polymarket, 4 Kalshi), le graphique de la page dédiée Kalshi affiche
  bien les 565 jours d'historique backfillés, le lien de pied de page pointe
  vers `kalshi.com/markets/...`.

### 30. Remplacement du badge par un slider Polymarket/Kalshi (une carte par question)
- L'utilisateur a changé d'avis sur la présentation de la section 29 : plutôt
  que deux cartes séparées (une par plateforme) distinguées par un badge, il
  a demandé une maquette où une **même question suivie sur les deux
  plateformes n'affiche qu'une seule carte**, avec un petit slider dans
  l'en-tête pour basculer les barres/le graphique entre les deux sources.
  Maquette affinée sur un retour ("boutons plus petits et discrets") avant
  validation ("ok on peut passer ça en prod").
- Regroupement : nouveau champ `pairs_with` sur les 4 entrées Kalshi de
  `config.json` (pointant vers le slug Polymarket équivalent), propagé dans
  `data/markets.json` par `fetch_kalshi.py`/`backfill_kalshi_history.py`.
  Nouveau `site/src/lib/groupMarkets.ts` : `groupMarkets()` fusionne les
  entrées liées par `pairs_with` en un seul groupe `{slug, sources: {polymarket,
  kalshi}}` (un `pairs_with` orphelin — cible absente — n'est pas fusionné,
  le marché reste affiché seul plutôt que de disparaître) ; `findGroupForSlug()`
  retrouve, pour un slug de page dédiée précis, son groupe ET quelle source
  doit être active par défaut (pour que le contenu visible corresponde à
  l'aperçu de lien OG de CE slug précis).
- `MarketCard.astro` réécrit : prend désormais `sources` (map source→
  {slug, market}) au lieu d'un `market` unique. Calcule les barres/graphique
  pour CHAQUE source au build, avec un slider (`.source-switch`, sliding
  thumb en CSS) si plusieurs sources, sinon une simple mention texte
  "Source : X" (le badge coloré de la section 29 est retiré). Toutes les
  vues par source sont embarquées en JSON dans un attribut `data-sources` du
  `<article>` pour le swap côté client. `BinaryMarketCard.astro` garde un
  `market` unique (aucun marché binaire Kalshi n'existe pour l'instant) mais
  adopte la même mention "Source : X" pour rester visuellement cohérent.
- `ChartScripts.astro` : le handler de clic sur le slider régénère le HTML
  des barres, mute `chart.data`/`chart.options.scales.y.max` puis appelle
  `chart.update()` (instance Chart.js maintenant gardée sur `canvas._chart`),
  et met à jour le lien + le texte de pied de carte — sans recharger la page
  ni dupliquer le canvas (un canvas caché aurait un `offsetWidth` nul et
  poserait des problèmes de rendu Chart.js).
- **Bug découvert et corrigé pendant la vérification** : les barres
  régénérées côté client perdaient tout leur style (plus de piste/remplissage
  visible). Cause : Astro scope le CSS d'un composant via un attribut
  `data-astro-cid-*` ajouté au HTML rendu au build — les nœuds recréés par
  `innerHTML` en JS n'ont pas cet attribut, donc les règles scopées
  (`.bar-row`, `.bar-track`, `.bar-fill`, `.bars`) ne s'appliquaient plus.
  Corrigé en passant ces règles précises en `:global(...)` dans le `<style>`
  du composant (pas tout le bloc, pour ne pas faire fuir le reste vers les
  autres composants).
- `index.astro`/`[slug].astro` utilisent désormais `groupMarkets()` pour
  construire les cartes (7 cartes sur la page d'accueil : 4 fusionnées + 3
  Polymarket seul, au lieu de 11 cartes séparées) ; les pages dédiées par
  slug existent toujours pour CHAQUE entrée d'origine (y compris les 4 slugs
  Kalshi), chacune affichant la même carte fusionnée mais avec sa propre
  source activée par défaut.
- Outillage : Edge headless s'est mis à échouer silencieusement dans cet
  environnement pendant la vérification (`--dump-dom` sur une simple
  data-URL ne produisait plus rien, indépendamment de Puppeteer/du site) —
  contourné en utilisant Chrome (`C:/Program Files/Google/Chrome/Application/
  chrome.exe`, déjà installé) comme `executablePath` à la place. À retenir
  pour la suite si Edge headless refait des siennes dans cet environnement.
- Vérifié via Puppeteer+Chrome sur le site buildé servi en local : page
  d'accueil = 7 cartes ; clic sur le slider d'une carte change bien le
  candidat en tête affiché, le lien de pied de carte (URL + texte) et le
  graphique (nouvelles séries, nouveau plafond d'axe Y) sans toucher aux
  autres cartes ; le bouton "voir N de plus" fonctionne après un changement
  de source ; la page dédiée `/marche/kalshi-french-socialist-bloc-nominee/`
  s'ouvre bien avec Kalshi pré-sélectionné dans le slider ; la page dédiée
  budget (sans équivalent Kalshi) n'affiche aucun slider, juste "Source :
  Polymarket".

## Pistes non traitées (du README)

- Pas de déduplication des points d'historique proches dans la collecte horaire.
- Pas de gestion des marchés clôturés/résolus.
- Couleurs de candidats incomplètes pour le marché "second tour" (voir
  section 6 ci-dessus).
- **Idée notée pour plus tard (pas encore commencée)** : Metaculus et
  Manifold restent à intégrer (Kalshi est fait, voir section 29). Metaculus
  exige désormais un compte + token d'API ; Manifold est ouvert sans auth
  (`api.manifold.markets/v0/search-markets`).
- **Idée notée pour plus tard (pas retenue pour l'instant)** : le cron
  `schedule` de GitHub Actions s'est révélé peu fiable dans la durée (voir
  section 28) — un déclencheur externe (cron-job.org, ou un cron Vercel
  appelant `workflow_dispatch` via l'API GitHub) donnerait un rythme de
  collecte plus proche du réel "toutes les heures" si le décalage à `17 *
  * * *` ne suffit pas.
- **Idée notée pour plus tard (pas encore commencée)** : ajouter des pages/
  sections "À propos", "Explications" et "Contact" au site.
