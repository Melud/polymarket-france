# Polymarket France

Site perso affichant les marchés Polymarket concernant la France, traduits en français.
Lecture seule, données publiques via l'API Gamma de Polymarket. Non affilié à Polymarket.

## Structure

```
collector/           script Python de collecte
  config.json         liste des marchés suivis + traductions
  fetch_markets.py     appelle l'API Gamma et met à jour data/markets.json
data/
  markets.json         historique des prix (généré/mis à jour par le script)
site/                 site Astro qui lit data/markets.json et l'affiche
.github/workflows/    cron GitHub Actions (collecte horaire + commit auto)
```

## Démarrage rapide

### 1. Tester la collecte en local

```bash
cd collector
pip install -r requirements.txt
python fetch_markets.py
```

Ça remplit/complète `data/markets.json`. Relancez le script plusieurs fois (ou attendez
entre deux runs) pour accumuler de l'historique et voir apparaître les courbes.

### 2. Lancer le site en local

```bash
cd site
npm install
npm run dev
```

Ouvrez http://localhost:4321

### 3. Ajouter un marché à suivre

Éditez `collector/config.json` et ajoutez une entrée avec le `slug` de l'URL Polymarket
(ex: `polymarket.com/event/mon-marche` → slug = `mon-marche`) et sa traduction :

```json
{
  "slug": "mon-marche",
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
