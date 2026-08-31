#!/usr/bin/env python3
"""
Backfill ponctuel de l'historique des cotes depuis l'API CLOB de Polymarket
(clob.polymarket.com/prices-history), qui conserve l'historique complet par
candidat depuis la création du marché — contrairement à la Gamma API qui ne
donne que le prix courant.

Ne backfille que les candidats dont le prix actuel dépasse SIGNIFICANCE_THRESHOLD,
pour garder un fichier et un graphique lisibles (la plupart des ~40 candidats
d'un marché comme la présidentielle sont plats à 0.15% et n'ont jamais bougé).

Usage: python backfill_history.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "collector" / "config.json"
DATA_PATH = ROOT / "data" / "markets.json"
GAMMA_URL = "https://gamma-api.polymarket.com/events"
CLOB_HISTORY_URL = "https://clob.polymarket.com/prices-history"

SIGNIFICANCE_THRESHOLD = 0.01  # on ne backfille que les candidats à >= 1%
FIDELITY_MINUTES = 1440  # un point par jour


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


def significant_candidates(event: dict) -> list[dict]:
    """
    Pour chaque sous-marché (un par candidat), récupère le nom, le prix "Yes"
    courant et le clobTokenId associé — nécessaire pour interroger l'historique.
    Ne garde que ceux au-dessus du seuil de significativité.
    """
    markets = event.get("markets", [])
    candidates = []

    if len(markets) == 1:
        # un seul marché avec plusieurs outcomes (ex: Oui/Non) — on garde
        # chaque outcome tel quel, pas de regroupement par candidat
        m = markets[0]
        if m.get("active") is False or m.get("archived") is True:
            return []
        outcomes = json.loads(m.get("outcomes", "[]"))
        prices = json.loads(m.get("outcomePrices", "[]"))
        token_ids = json.loads(m.get("clobTokenIds", "[]"))
        for name, price, token_id in zip(outcomes, prices, token_ids):
            price = float(price)
            if price >= SIGNIFICANCE_THRESHOLD:
                candidates.append({"name": name, "token_id": token_id, "price": price})
    else:
        for m in markets:
            # marchés archivés/inactifs (ex. "Other" retiré par Polymarket) :
            # même filtre que fetch_markets.py, pour ne pas backfiller un
            # historique basé sur un outcomePrices obsolète
            if m.get("active") is False or m.get("archived") is True:
                continue
            outcomes = json.loads(m.get("outcomes", "[]"))
            prices = json.loads(m.get("outcomePrices", "[]"))
            token_ids = json.loads(m.get("clobTokenIds", "[]"))
            if not outcomes or not prices or not token_ids:
                continue
            yes_idx = outcomes.index("Yes") if "Yes" in outcomes else 0
            price = float(prices[yes_idx])
            if price >= SIGNIFICANCE_THRESHOLD:
                label = m.get("groupItemTitle") or m.get("question", "?")
                candidates.append({"name": label, "token_id": token_ids[yes_idx], "price": price})

    candidates.sort(key=lambda c: c["price"], reverse=True)
    return candidates


def fetch_daily_history(token_id: str) -> dict[str, tuple[int, float]]:
    """Retourne {jour ISO: (timestamp unix du dernier point du jour, prix)}."""
    resp = requests.get(
        CLOB_HISTORY_URL,
        params={"market": token_id, "interval": "max", "fidelity": FIDELITY_MINUTES},
        timeout=20,
    )
    resp.raise_for_status()
    points = resp.json().get("history", [])

    daily: dict[str, tuple[int, float]] = {}
    for point in points:
        ts = point["t"]
        price = float(point["p"])
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        if day not in daily or ts > daily[day][0]:
            daily[day] = (ts, price)
    return daily


def build_history_entries(per_candidate_daily: dict[str, dict[str, tuple[int, float]]]) -> list[dict]:
    """
    Fusionne les séries journalières par candidat (timestamps non alignés)
    en une liste de snapshots synchronisés (un par jour), avec forward-fill :
    un candidat garde son dernier prix connu tant qu'il n'a pas de nouveau
    point ce jour-là.
    """
    all_days = sorted({day for daily in per_candidate_daily.values() for day in daily})
    last_price: dict[str, float] = {}
    entries = []

    for day in all_days:
        day_ts = None
        for name, daily in per_candidate_daily.items():
            if day in daily:
                ts, price = daily[day]
                last_price[name] = price
                day_ts = ts if day_ts is None else max(day_ts, ts)

        outcomes_today = [
            {"name": name, "price": price}
            for name, price in last_price.items()
            if name in per_candidate_daily  # garde uniquement les candidats déjà apparus
        ]
        outcomes_today.sort(key=lambda o: o["price"], reverse=True)

        ts_iso = (
            datetime.fromtimestamp(day_ts, tz=timezone.utc).isoformat(timespec="seconds")
            if day_ts is not None
            else f"{day}T12:00:00+00:00"
        )
        entries.append({"ts": ts_iso, "volume": 0.0, "outcomes": outcomes_today})

    return entries


def main():
    config = load_json(CONFIG_PATH, {"markets": []})
    data = load_json(DATA_PATH, {})

    for entry in config["markets"]:
        slug = entry["slug"]
        print(f"Backfill '{slug}'...")
        try:
            event = fetch_event(slug)
        except requests.RequestException as e:
            print(f"  [!] Erreur réseau pour '{slug}': {e}", file=sys.stderr)
            continue
        if event is None:
            continue

        candidates = significant_candidates(event)
        print(f"  {len(candidates)} candidats significatifs (prix >= {SIGNIFICANCE_THRESHOLD:.0%})")

        per_candidate_daily = {}
        for c in candidates:
            try:
                per_candidate_daily[c["name"]] = fetch_daily_history(c["token_id"])
            except requests.RequestException as e:
                print(f"    [!] Erreur historique pour '{c['name']}': {e}", file=sys.stderr)
            time.sleep(0.2)

        if not per_candidate_daily:
            continue

        backfilled = build_history_entries(per_candidate_daily)

        record = data.setdefault(slug, {
            "title_en": event.get("title", ""),
            "title_fr": entry.get("title_fr", event.get("title", "")),
            "description_fr": entry.get("description_fr", ""),
            "url": f"https://polymarket.com/event/{slug}",
            "style": entry.get("style", "candidates"),
            "history": [],
        })

        existing_history = record.get("history", [])
        existing_days = {h["ts"][:10] for h in existing_history}
        new_entries = [e for e in backfilled if e["ts"][:10] not in existing_days]

        merged = new_entries + existing_history
        merged.sort(key=lambda h: h["ts"])
        record["history"] = merged

        if new_entries:
            print(f"  {len(new_entries)} jours ajoutés ({new_entries[0]['ts'][:10]} -> {new_entries[-1]['ts'][:10]})")
        else:
            print("  Aucun nouveau jour à ajouter (déjà couvert)")

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK — données écrites dans {DATA_PATH}")


if __name__ == "__main__":
    main()
