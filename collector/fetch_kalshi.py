#!/usr/bin/env python3
"""
Récupère les marchés Kalshi listés dans config.json (source="kalshi") via
l'API publique Kalshi (api.elections.kalshi.com) et ajoute un point
d'historique (prix courants) dans data/markets.json.

Usage: python fetch_kalshi.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "collector" / "config.json"
DATA_PATH = ROOT / "data" / "markets.json"
KALSHI_EVENTS_URL = "https://api.elections.kalshi.com/trade-api/v2/events"


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def fetch_event(event_ticker: str) -> dict | None:
    resp = requests.get(
        f"{KALSHI_EVENTS_URL}/{event_ticker}",
        params={"with_nested_markets": "true"},
        timeout=15,
    )
    resp.raise_for_status()
    event = resp.json().get("event")
    if not event:
        print(f"  [!] Aucun event trouvé pour '{event_ticker}'", file=sys.stderr)
        return None
    return event


def extract_outcomes(event: dict) -> list[dict]:
    """
    Chaque event Kalshi contient un sous-marché binaire (Oui/Non) par candidat —
    même structure que le cas multi-sous-marchés de Polymarket. On prend le
    dernier prix "Yes" de chacun, en ignorant les marchés non actifs (candidat
    retiré, marché clôturé...).
    """
    results = []
    for m in event.get("markets", []):
        if m.get("status") != "active":
            continue
        price = m.get("last_price_dollars")
        if price is None:
            continue
        name = m.get("yes_sub_title") or m.get("subtitle") or m.get("ticker", "?")
        results.append({"name": name, "price": float(price)})

    results.sort(key=lambda o: o["price"], reverse=True)
    return results


def main():
    config = load_json(CONFIG_PATH, {"markets": []})
    data = load_json(DATA_PATH, {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for entry in config["markets"]:
        if entry.get("source") != "kalshi":
            continue
        slug = entry["slug"]
        event_ticker = entry["event_ticker"]
        print(f"Fetching '{event_ticker}'...")
        try:
            event = fetch_event(event_ticker)
        except requests.RequestException as e:
            print(f"  [!] Erreur réseau pour '{event_ticker}': {e}", file=sys.stderr)
            continue
        if event is None:
            continue

        outcomes = extract_outcomes(event)
        volume = sum(float(m.get("volume_fp", 0) or 0) for m in event.get("markets", []))

        record = data.setdefault(slug, {
            "title_en": event.get("title", ""),
            "title_fr": entry.get("title_fr", event.get("title", "")),
            "description_fr": entry.get("description_fr", ""),
            "url": f"https://kalshi.com/markets/{entry['series_ticker'].lower()}/{event_ticker.lower()}",
            "source": "kalshi",
            "style": entry.get("style", "candidates"),
            "category": entry.get("category", "Autres"),
            "pairs_with": entry.get("pairs_with"),
            "history": [],
        })
        # garder les traductions, le style et la catégorie à jour si modifiés dans config.json
        record["title_fr"] = entry.get("title_fr", record["title_fr"])
        record["description_fr"] = entry.get("description_fr", record["description_fr"])
        record["source"] = "kalshi"
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
