#!/usr/bin/env python3
"""
Backfill ponctuel de l'historique des cotes depuis l'API de paris de Manifold
(/v0/bets), qui n'a pas d'endpoint "historique" tout fait comme Polymarket/
Kalshi : on reconstruit un historique quotidien en paginant les paris (les
plus récents d'abord, via le curseur `before`) jusqu'à la création du marché,
et en gardant le dernier `probAfter` de chaque jour par candidat.

Ne backfille que les candidats dont le prix actuel dépasse SIGNIFICANCE_THRESHOLD,
même logique que backfill_history.py (Polymarket) et backfill_kalshi_history.py.

Usage: python backfill_manifold_history.py
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
MANIFOLD_MARKET_URL = "https://api.manifold.markets/v0/market"
MANIFOLD_BETS_URL = "https://api.manifold.markets/v0/bets"

SIGNIFICANCE_THRESHOLD = 0.01  # on ne backfille que les candidats à >= 1%
PAGE_SIZE = 1000
MAX_PAGES = 200  # garde-fou : jusqu'à 200 000 paris avant d'abandonner


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def fetch_market(market_id: str) -> dict:
    resp = requests.get(f"{MANIFOLD_MARKET_URL}/{market_id}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def significant_answer_names(market: dict) -> dict[str, str]:
    """{answerId: nom} pour les candidats au-dessus du seuil de significativité."""
    names = {}
    for a in market.get("answers", []):
        if a.get("isOther") or a.get("resolution"):
            continue
        if float(a["probability"]) >= SIGNIFICANCE_THRESHOLD:
            names[a["id"]] = a["text"]
    return names


def fetch_all_bets(market_id: str, until_ts_ms: int) -> list[dict]:
    """Pagine les paris du plus récent au plus ancien jusqu'à until_ts_ms (création du marché)."""
    all_bets = []
    before = None
    for _ in range(MAX_PAGES):
        params = {"contractId": market_id, "limit": PAGE_SIZE}
        if before:
            params["before"] = before
        resp = requests.get(MANIFOLD_BETS_URL, params=params, timeout=20)
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break
        all_bets.extend(page)
        oldest = page[-1]
        if oldest["createdTime"] <= until_ts_ms:
            break
        before = oldest["id"]
        time.sleep(0.15)
    return all_bets


def build_daily(bets: list[dict], answer_names: dict[str, str]) -> dict[str, dict[str, tuple[float, float]]]:
    """
    {nom: {jour ISO: (timestamp unix, prix)}} — les paris sont parcourus du plus
    récent au plus ancien, donc le premier pari rencontré pour un (candidat, jour)
    est déjà le dernier de ce jour-là.
    """
    per_candidate_daily: dict[str, dict[str, tuple[float, float]]] = {}
    seen_days: set[tuple[str, str]] = set()

    for bet in bets:
        name = answer_names.get(bet.get("answerId"))
        if not name:
            continue
        ts = bet["createdTime"] / 1000
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        key = (name, day)
        if key in seen_days:
            continue
        seen_days.add(key)
        per_candidate_daily.setdefault(name, {})[day] = (ts, float(bet["probAfter"]))

    return per_candidate_daily


def build_history_entries(per_candidate_daily: dict[str, dict[str, tuple[float, float]]]) -> list[dict]:
    """Même logique de fusion/forward-fill que les autres scripts de backfill."""
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

    for entry in config["markets"]:
        if entry.get("source") != "manifold":
            continue
        slug = entry["slug"]
        market_id = entry["market_id"]
        print(f"Backfill '{market_id}'...")
        try:
            market = fetch_market(market_id)
        except requests.RequestException as e:
            print(f"  [!] Erreur réseau pour '{market_id}': {e}", file=sys.stderr)
            continue

        answer_names = significant_answer_names(market)
        print(f"  {len(answer_names)} candidats significatifs (prix >= {SIGNIFICANCE_THRESHOLD:.0%})")

        try:
            bets = fetch_all_bets(market_id, market.get("createdTime", 0))
        except requests.RequestException as e:
            print(f"  [!] Erreur historique pour '{market_id}': {e}", file=sys.stderr)
            continue
        print(f"  {len(bets)} paris récupérés")

        per_candidate_daily = build_daily(bets, answer_names)
        if not per_candidate_daily:
            continue

        backfilled = build_history_entries(per_candidate_daily)

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
