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

## Pistes non traitées (du README)

- Pas de déduplication des points d'historique proches dans la collecte horaire.
- Pas de gestion des marchés clôturés/résolus.
- Couleurs de candidats incomplètes pour le marché "second tour" (voir
  section 6 ci-dessus).
