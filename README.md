# Polymarket France

Site perso affichant des marchés prédictifs (Polymarket, Kalshi, Manifold) concernant la
France, traduits en français. Lecture seule, données publiques. Non affilié à ces plateformes.

## Structure

```
collector/                    scripts Python de collecte
  config.json                  liste des marchés suivis + traductions (champ "source")
  fetch_markets.py              Polymarket : appelle l'API Gamma, met à jour data/markets.json
  backfill_history.py           Polymarket : backfill l'historique via l'API CLOB
  fetch_kalshi.py                Kalshi : appelle l'API publique Kalshi
  backfill_kalshi_history.py     Kalshi : backfill l'historique via les candlesticks
  fetch_manifold.py              Manifold : appelle l'API publique Manifold
  backfill_manifold_history.py   Manifold : backfill l'historique en reconstituant les
                                  paris quotidiens (pas d'endpoint "historique" dédié)
data/
  markets.json                 historique des prix (généré/mis à jour par les scripts)
site/                         site Astro qui lit data/markets.json et l'affiche
.github/workflows/            cron GitHub Actions (collecte horaire + commit auto)
```

Un même marché peut être suivi sur plusieurs plateformes à la fois (champ `pairs_with` sur
l'entrée secondaire, voir plus bas) : la carte du site les fusionne alors en une seule, avec
un petit slider pour basculer entre les sources.

## Démarrage rapide

### 1. Tester la collecte en local

```bash
cd collector
pip install -r requirements.txt
python fetch_markets.py
python fetch_kalshi.py
python fetch_manifold.py
```

Ça remplit/complète `data/markets.json`. Relancez les scripts plusieurs fois (ou attendez
entre deux runs) pour accumuler de l'historique et voir apparaître les courbes — ou lancez
`backfill_history.py`/`backfill_kalshi_history.py`/`backfill_manifold_history.py` une fois
pour récupérer l'historique existant directement depuis chaque plateforme.

### 2. Lancer le site en local

```bash
cd site
npm install
npm run dev
```

Ouvrez http://localhost:4321

### 3. Ajouter un marché à suivre

Éditez `collector/config.json` et ajoutez une entrée. Pour un marché Polymarket, le
`slug` est celui de l'URL (ex: `polymarket.com/event/mon-marche` → slug = `mon-marche`) :

```json
{
  "source": "polymarket",
  "slug": "mon-marche",
  "title_fr": "Titre traduit",
  "description_fr": "Description traduite"
}
```

Pour un marché Kalshi, il faut le `series_ticker` et l'`event_ticker` (visibles dans
l'URL ou via l'API `/trade-api/v2/series`), plus un `slug` propre au site (préfixé
`kalshi-` par convention, pour ne pas entrer en collision avec un slug Polymarket) :

```json
{
  "source": "kalshi",
  "slug": "kalshi-mon-marche",
  "series_ticker": "KXMONMARCHE",
  "event_ticker": "KXMONMARCHE-27",
  "title_fr": "Titre traduit",
  "description_fr": "Description traduite"
}
```

Pour un marché Manifold, il faut le `market_id` (l'id du contrat, pas le slug — visible
via `api.manifold.markets/v0/slug/{slug-de-l-url}`), plus un `slug` propre au site
(préfixé `manifold-`) :

```json
{
  "source": "manifold",
  "slug": "manifold-mon-marche",
  "market_id": "abc123",
  "market_slug": "mon-marche-sur-lurl-manifold",
  "title_fr": "Titre traduit",
  "description_fr": "Description traduite"
}
```

Si ce marché suit la même question qu'un marché déjà présent (sur une autre plateforme),
ajoutez `"pairs_with": "<slug-du-marché-principal>"` pour que le site les fusionne en une
seule carte avec un slider au lieu d'afficher deux cartes séparées.

### 4. Déployer

- **Site** : connectez le repo à Vercel ou Netlify (build command `npm run build` dans
  `site/`, output `site/dist`). Chaque push déclenche un rebuild automatique.
- **Collecte** : le workflow `.github/workflows/update-data.yml` tourne déjà toutes les
  heures sur GitHub Actions dès que le repo est poussé sur GitHub — rien d'autre à
  configurer. Il commit `data/markets.json` à chaque run, ce qui déclenche le rebuild
  du site côté Vercel/Netlify.

## Limites de ce premier jet

- Pas de déduplication des points d'historique proches (chaque run ajoute un point,
  même si le prix n'a pas bougé) — à améliorer si l'historique devient volumineux.
- Pas de gestion des marchés qui se clôturent/résolvent (le script continue de les
  interroger tel quel).
- Traduction 100% manuelle via `config.json`, comme demandé.
