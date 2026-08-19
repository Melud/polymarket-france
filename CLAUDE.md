# Polymarket France — contexte projet

## Objectif
Site perso affichant les marchés Polymarket concernant la France (présidentielle 2027,
budget, etc.), traduits en français. Lecture seule, aucune fonctionnalité de pari.
Non affilié à Polymarket.

## Stack
- **Collecte** : script Python (`collector/fetch_markets.py`), exécuté avec `uv run`
  (dépendances déclarées en inline PEP 723 dans le script, pas de requirements.txt)
- **Stockage** : `data/markets.json`, historique de prix accumulé à chaque run
- **Orchestration** : GitHub Actions (`.github/workflows/update-data.yml`), cron horaire,
  commit + push automatique du JSON mis à jour
- **Site** : Astro (`site/`), statique, lit `data/markets.json` au build, graphiques via
  Chart.js (CDN)

## Arborescence
```
collector/
  config.json          liste des marchés suivis (slug + traductions fr)
  fetch_markets.py      appelle l'API Gamma de Polymarket, met à jour data/markets.json
data/
  markets.json          historique des prix (généré)
site/
  src/pages/index.astro     page d'accueil, lit data/markets.json
  src/components/MarketCard.astro   carte par marché (barres + courbe)
.github/workflows/update-data.yml   cron GitHub Actions
README.md
```

## API utilisée
Gamma API de Polymarket, publique, sans authentification :
`https://gamma-api.polymarket.com/events?slug=<slug>`

Un event peut contenir soit un seul market avec plusieurs `outcomes`, soit plusieurs
sub-markets (un par candidat) chacun binaire — `fetch_markets.py` gère les deux cas
(voir `extract_outcomes()`).

## État d'avancement
- Structure complète posée, un seul marché configuré pour l'instant
  (`next-french-presidential-election`)
- Script testé syntaxiquement mais pas encore exécuté avec succès en conditions réelles
  depuis la France (voir bug connu ci-dessous)
- Site Astro jamais buildé/testé en local pour l'instant

## Bug connu — important
Depuis la France, l'appel à `gamma-api.polymarket.com` échoue avec une erreur SSL
(`Hostname mismatch` / certificat invalide). Cause probable : le blocage ANJ de
Polymarket en France (juillet 2026), qui redirige le trafic vers une page de blocage
dont le certificat ne correspond pas au domaine demandé.
- Le **GitHub Actions** (runners hébergés hors de France) devrait fonctionner malgré
  ce blocage — c'est le point à valider en priorité une fois le repo poussé sur GitHub.
- Pour du dev en local depuis la France, un VPN est probablement nécessaire.

## Prochaines étapes possibles
1. Pousser le repo sur GitHub et vérifier que le workflow `update-data.yml` tourne et
   commit bien des données valides (test du contournement du blocage FR)
2. `cd site && npm install && npm run dev` pour valider le rendu du site avec les
   données réelles une fois `data/markets.json` peuplé
3. Ajouter d'autres marchés France dans `collector/config.json`
4. Déployer le site (Vercel/Netlify) branché sur le repo GitHub
5. Éventuellement : dédupliquer les points d'historique quasi identiques, gérer la
   clôture/résolution des marchés
