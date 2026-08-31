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

## Pistes non traitées (du README)

- Pas de déduplication des points d'historique proches dans la collecte horaire.
- Pas de gestion des marchés clôturés/résolus.
- Couleurs de candidats incomplètes pour le marché "second tour" (voir
  section 6 ci-dessus).
