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
  - labels de dates sans les heures,
  - échelle Y qui s'arrête juste au-dessus du prix max réel des séries
    affichées plutôt que d'être fixée à 100 %,
  - ligne verticale en pointillés au survol + tooltip listant tous les
    candidats, leurs cotes et la date à la position survolée (`interaction:
    mode "index"` + plugin Chart.js personnalisé `crosshairPlugin`).
- Couleurs par candidat alignées sur les nuances politiques (Wikipédia) plutôt
  qu'arbitraires — `site/src/lib/candidateColors.ts` (ajouté depuis une autre
  machine, mergé sans conflit).

## Permissions outillage

- `.claude/settings.json` (suivi par git, distinct de `settings.local.json`)
  contient un allowlist de commandes lecture-seule fréquemment utilisées
  (`gh api`, `gh run view`, `curl -s`, `Set-Location`, `Test-Path`) pour réduire
  les demandes de confirmation répétées.

## Pistes non traitées (du README)

- Pas de déduplication des points d'historique proches dans la collecte horaire.
- Pas de gestion des marchés clôturés/résolus.
- Un seul marché suivi pour l'instant (`next-french-presidential-election`).
