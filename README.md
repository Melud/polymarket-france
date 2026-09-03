# Polymarket France

Site perso affichant des marchés prédictifs (Polymarket, Kalshi) concernant la France,
traduits en français. Lecture seule, données publiques. Non affilié à ces plateformes.

## Structure

```
collector/                    scripts Python de collecte
  config.json                  liste des marchés suivis + traductions (champ "source")
  fetch_markets.py              Polymarket : appelle l'API Gamma, met à jour data/markets.json
  backfill_history.py           Polymarket : backfill l'historique via l'API CLOB
  fetch_kalshi.py                Kalshi : appelle l'API publique Kalshi
  backfill_kalshi_history.py     Kalshi : backfill l'historique via les candlesticks
data/
  markets.json                 historique des prix (généré/mis à jour par les scripts)
site/                         site Astro qui lit data/markets.json et l'affiche
.github/workflows/            cron GitHub Actions (collecte horaire + commit auto)
```

## Démarrage rapide

### 1. Tester la collecte en local

```bash
cd collector
pip install -r requirements.txt
python fetch_markets.py
python fetch_kalshi.py
```

Ça remplit/complète `data/markets.json`. Relancez les scripts plusieurs fois (ou attendez
entre deux runs) pour accumuler de l'historique et voir apparaître les courbes — ou lancez
`backfill_history.py`/`backfill_kalshi_history.py` une fois pour récupérer l'historique
existant directement depuis chaque plateforme.

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
