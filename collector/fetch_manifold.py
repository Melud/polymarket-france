#!/usr/bin/env python3
"""
Récupère les marchés Manifold listés dans config.json (source="manifold") via
l'API publique Manifold (api.manifold.markets) et ajoute un point d'historique
(prix courants) dans data/markets.json.

Usage: python fetch_manifold.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "collector" / "config.json"
DATA_PATH = ROOT / "data" / "markets.json"
MANIFOLD_MARKET_URL = "https://api.manifold.markets/v0/market"


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def fetch_market(market_id: str) -> dict:
    resp = requests.get(f"{MANIFOLD_MARKET_URL}/{market_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def extract_outcomes(market: dict) -> list[dict]:
    """
    Marché à choix multiples (une réponse par candidat) : on prend la
    probabilité courante de chacun, en ignorant le bucket générique "Other"
    (isOther) et les réponses individuellement résolues/retirées.
    """
    results = []
    for a in market.get("answers", []):
        if a.get("isOther") or a.get("resolution"):
            continue
        results.append({"name": a["text"], "price": float(a["probability"])})

    results.sort(key=lambda o: o["price"], reverse=True)
    return results


def main():
    config = load_json(CONFIG_PATH, {"markets": []})
    data = load_json(DATA_PATH, {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for entry in config["markets"]:
        if entry.get("source") != "manifold":
            continue
        slug = entry["slug"]
        market_id = entry["market_id"]
        print(f"Fetching '{market_id}'...")
        try:
            market = fetch_market(market_id)
        except requests.RequestException as e:
            print(f"  [!] Erreur réseau pour '{market_id}': {e}", file=sys.stderr)
            continue

        outcomes = extract_outcomes(market)
        volume = float(market.get("volume", 0) or 0)
        url = market.get("url") or f"https://manifold.markets/{entry.get('market_slug', '')}"

        record = data.setdefault(slug, {
            "title_en": market.get("question", ""),
            "title_fr": entry.get("title_fr", market.get("question", "")),
            "description_fr": entry.get("description_fr", ""),
            "url": url,
            "source": "manifold",
            "style": entry.get("style", "candidates"),
            "category": entry.get("category", "Autres"),
            "pairs_with": entry.get("pairs_with"),
            "history": [],
        })
        # garder les traductions, le style et la catégorie à jour si modifiés dans config.json
        record["title_fr"] = entry.get("title_fr", record["title_fr"])
        record["description_fr"] = entry.get("description_fr", record["description_fr"])
        record["source"] = "manifold"
        record["style"] = entry.get("style", record.get("style", "candidates"))
        record["category"] = entry.get("category", record.get("category", "Autres"))
        record["pairs_with"] = entry.get("pairs_with", record.get("pairs_with"))

        record["history"].append({
            "ts": now,
            "volume": volume,
            "outcomes": outcomes,
        })

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK — données écrites dans {DATA_PATH}")


if __name__ == "__main__":
    main()
