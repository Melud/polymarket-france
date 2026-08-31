#!/usr/bin/env python3
"""
Récupère les marchés Polymarket listés dans config.json via l'API Gamma
et ajoute un point d'historique (prix courants) dans data/markets.json.

Usage: python fetch_markets.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "collector" / "config.json"
DATA_PATH = ROOT / "data" / "markets.json"
GAMMA_URL = "https://gamma-api.polymarket.com/events"


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def fetch_event(slug: str) -> dict | None:
    resp = requests.get(GAMMA_URL, params={"slug": slug}, timeout=15)
    resp.raise_for_status()
    events = resp.json()
    if not events:
        print(f"  [!] Aucun event trouvé pour le slug '{slug}'", file=sys.stderr)
        return None
    return events[0]


def extract_outcomes(event: dict) -> list[dict]:
    """
    Gère les deux cas possibles :
    - un event = un seul marché avec plusieurs outcomes (ex: Oui/Non)
    - un event = plusieurs sous-marchés (un par candidat), chacun binaire
    """
    markets = event.get("markets", [])
    results = []

    if len(markets) == 1:
        m = markets[0]
        outcomes = json.loads(m.get("outcomes", "[]"))
        prices = json.loads(m.get("outcomePrices", "[]"))
        for name, price in zip(outcomes, prices):
            results.append({"name": name, "price": float(price)})
    else:
        # un sous-marché par candidat/option, on prend le prix "Yes" de chacun
        for m in markets:
            # marchés archivés/inactifs (ex. "Other" retiré par Polymarket) :
            # leur outcomePrices est obsolète, on les ignore comme le fait
            # l'interface Polymarket elle-même
            if m.get("active") is False or m.get("archived") is True:
                continue
            outcomes = json.loads(m.get("outcomes", "[]"))
            prices = json.loads(m.get("outcomePrices", "[]"))
            label = m.get("groupItemTitle") or m.get("question", "?")
            if outcomes and prices:
                yes_idx = outcomes.index("Yes") if "Yes" in outcomes else 0
                results.append({"name": label, "price": float(prices[yes_idx])})

    results.sort(key=lambda o: o["price"], reverse=True)
    return results


def main():
    config = load_json(CONFIG_PATH, {"markets": []})
    data = load_json(DATA_PATH, {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for entry in config["markets"]:
        slug = entry["slug"]
        print(f"Fetching '{slug}'...")
        try:
            event = fetch_event(slug)
        except requests.RequestException as e:
            print(f"  [!] Erreur réseau pour '{slug}': {e}", file=sys.stderr)
            continue
        if event is None:
            continue

        outcomes = extract_outcomes(event)
        volume = float(event.get("volume", 0) or 0)

        record = data.setdefault(slug, {
            "title_en": event.get("title", ""),
            "title_fr": entry.get("title_fr", event.get("title", "")),
            "description_fr": entry.get("description_fr", ""),
            "url": f"https://polymarket.com/event/{slug}",
            "style": entry.get("style", "candidates"),
            "category": entry.get("category", "Autres"),
            "history": [],
        })
        # garder les traductions, le style et la catégorie à jour si modifiés dans config.json
        record["title_fr"] = entry.get("title_fr", record["title_fr"])
        record["description_fr"] = entry.get("description_fr", record["description_fr"])
        record["style"] = entry.get("style", record.get("style", "candidates"))
        record["category"] = entry.get("category", record.get("category", "Autres"))

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
