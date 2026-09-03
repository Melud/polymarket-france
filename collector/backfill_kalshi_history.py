#!/usr/bin/env python3
"""
Backfill ponctuel de l'historique des cotes depuis l'API de candlesticks de
Kalshi (/series/{series_ticker}/markets/{ticker}/candlesticks), qui conserve
l'historique quotidien complet par candidat depuis la création du marché —
contrairement au endpoint /events qui ne donne que le prix courant.

Ne backfille que les candidats dont le prix actuel dépasse SIGNIFICANCE_THRESHOLD,
même logique que backfill_history.py (Polymarket).

Usage: python backfill_kalshi_history.py
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
KALSHI_EVENTS_URL = "https://api.elections.kalshi.com/trade-api/v2/events"
KALSHI_SERIES_URL = "https://api.elections.kalshi.com/trade-api/v2/series"

SIGNIFICANCE_THRESHOLD = 0.01  # on ne backfille que les candidats à >= 1%
PERIOD_INTERVAL_MINUTES = 1440  # un point par jour


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


def significant_candidates(event: dict) -> list[dict]:
    candidates = []
    for m in event.get("markets", []):
        if m.get("status") != "active":
            continue
        price_str = m.get("last_price_dollars")
        if price_str is None:
            continue
        price = float(price_str)
        if price < SIGNIFICANCE_THRESHOLD:
            continue
        name = m.get("yes_sub_title") or m.get("subtitle") or m.get("ticker", "?")
        created = m.get("created_time")
        start_ts = (
            int(datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp())
            if created
            else 0
        )
        candidates.append({
            "name": name,
            "ticker": m["ticker"],
            "price": price,
            "start_ts": start_ts,
        })

    candidates.sort(key=lambda c: c["price"], reverse=True)
    return candidates


def fetch_daily_history(series_ticker: str, ticker: str, start_ts: int, end_ts: int) -> dict[str, tuple[int, float]]:
    """Retourne {jour ISO: (timestamp unix de fin de bougie, prix)}."""
    resp = requests.get(
        f"{KALSHI_SERIES_URL}/{series_ticker}/markets/{ticker}/candlesticks",
        params={"start_ts": start_ts, "end_ts": end_ts, "period_interval": PERIOD_INTERVAL_MINUTES},
        timeout=20,
    )
    resp.raise_for_status()
    points = resp.json().get("candlesticks", [])

    daily: dict[str, tuple[int, float]] = {}
    for point in points:
        ts = point["end_period_ts"]
        price_block = point.get("price") or {}
        close = price_block.get("close_dollars")
        if close is not None:
            price = float(close)
        else:
            # pas d'échange ce jour-là : on retombe sur le milieu bid/ask
            bid = (point.get("yes_bid") or {}).get("close_dollars")
            ask = (point.get("yes_ask") or {}).get("close_dollars")
            if bid is None or ask is None:
                continue
            price = (float(bid) + float(ask)) / 2
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        daily[day] = (ts, price)
    return daily


def build_history_entries(per_candidate_daily: dict[str, dict[str, tuple[int, float]]]) -> list[dict]:
    """Même logique de fusion/forward-fill que backfill_history.py (Polymarket)."""
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
            if name in per_candidate_daily
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
    now_ts = int(datetime.now(timezone.utc).timestamp())

    for entry in config["markets"]:
        if entry.get("source") != "kalshi":
            continue
        slug = entry["slug"]
        event_ticker = entry["event_ticker"]
        series_ticker = entry["series_ticker"]
        print(f"Backfill '{event_ticker}'...")
        try:
            event = fetch_event(event_ticker)
        except requests.RequestException as e:
            print(f"  [!] Erreur réseau pour '{event_ticker}': {e}", file=sys.stderr)
            continue
        if event is None:
            continue

        candidates = significant_candidates(event)
        print(f"  {len(candidates)} candidats significatifs (prix >= {SIGNIFICANCE_THRESHOLD:.0%})")

        per_candidate_daily = {}
        for c in candidates:
            try:
                per_candidate_daily[c["name"]] = fetch_daily_history(
                    series_ticker, c["ticker"], c["start_ts"], now_ts
                )
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
            "url": f"https://kalshi.com/markets/{series_ticker.lower()}/{event_ticker.lower()}",
            "source": "kalshi",
            "style": entry.get("style", "candidates"),
            "category": entry.get("category", "Autres"),
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
