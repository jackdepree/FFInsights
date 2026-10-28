"""Exploration backfill: ESPN game odds and player-prop lines, 2022 to today.

This is exploration code (rule i). It moves into the package when odds-collection
reaches Building.

Raw responses are saved append-only as gzipped JSON, one file per game per fetch:
    <data>/raw/espn_odds/season=<YYYY>/<event_id>__final.json.gz        game was over when fetched
    <data>/raw/espn_odds/season=<YYYY>/<event_id>__<fetched_utc>.json.gz  pre-game snapshot
Re-running skips games whose final file already exists, so it is safe to resume.

Usage: python backfill_espn.py [--seasons 2022 2023 2024 2025 2026] [--delay 0.4]
       python backfill_espn.py --current-season   (what the scheduled collector runs)
Needs: requests
"""
import argparse
import gzip
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

PCF_DIR = Path(__file__).resolve().parents[3]
# Temporary until the package's central config exists (rule f).
DATA_DIR = Path(os.environ.get("PCF_DATA_DIR", PCF_DIR / "data"))
RAW_DIR = DATA_DIR / "raw" / "espn_odds"

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
ODDS = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{e}/competitions/{e}/odds"

# Books that have carried NFL props on ESPN: DraftKings (100 in 2026, 40 earlier), ESPN BET (58),
# SugarHouse (41), Caesars NJ (45), MGM (47), PointsBet (48), Caesars CO (52).
PROP_PROVIDERS = {"100", "58", "40", "41", "45", "47", "48", "52"}
SEASON_WEEKS = {2: range(1, 19), 3: range(1, 6)}  # seasontype 2 = regular season, 3 = postseason
UPCOMING_WINDOW = timedelta(days=7)

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0 (compatible; PCF personal research)"


def get_json(url, delay, retries=4):
    """GET a JSON document politely. Returns None on 404."""
    for attempt in range(retries):
        time.sleep(delay)
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as err:
            wait = 2 ** attempt * 5
            print(f"  retry {attempt + 1}/{retries} in {wait}s: {err}", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}")


def list_events(season, delay):
    """Yield one dict per game from ESPN's scoreboard for a season."""
    for seasontype, weeks in SEASON_WEEKS.items():
        for week in weeks:
            board = get_json(f"{SCOREBOARD}?dates={season}&seasontype={seasontype}&week={week}", delay)
            for ev in (board or {}).get("events", []):
                comp = ev["competitions"][0]
                teams = {c["homeAway"]: c["team"]["abbreviation"] for c in comp["competitors"]}
                yield {
                    "event_id": ev["id"],
                    "name": ev["name"],
                    "kickoff": ev["date"],
                    "season": season,
                    "seasontype": seasontype,
                    "week": week,
                    "completed": comp["status"]["type"]["completed"],
                    "home": teams.get("home"),
                    "away": teams.get("away"),
                }


def fetch_props(event_id, provider_id, delay):
    items, page, page_count = [], 1, 1
    while page <= page_count:
        doc = get_json(f"{ODDS.format(e=event_id)}/{provider_id}/propBets?limit=1000&page={page}", delay)
        if not doc:
            break
        items += doc.get("items", [])
        page_count = doc.get("pageCount", 1)
        page += 1
    return items


def fetch_event(ev, delay):
    odds = get_json(ODDS.format(e=ev["event_id"]), delay) or {}
    props = {}
    for item in odds.get("items", []):
        provider = item.get("provider", {})
        pid, name = str(provider.get("id")), provider.get("name", "")
        if pid in PROP_PROVIDERS and "live" not in name.lower():
            found = fetch_props(ev["event_id"], pid, delay)
            if found:
                props[pid] = {"provider_name": name, "items": found}
    return {"event": ev, "fetched_at": datetime.now(timezone.utc).isoformat(), "odds": odds, "props": props}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seasons", type=int, nargs="+", default=[2022, 2023, 2024, 2025, 2026])
    parser.add_argument("--current-season", action="store_true",
                        help="only the NFL season in progress (Jan-Feb belong to the previous year's season)")
    parser.add_argument("--delay", type=float, default=0.4, help="seconds between requests")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    seasons = [now.year if now.month >= 3 else now.year - 1] if args.current_season else args.seasons

    for season in seasons:
        out_dir = RAW_DIR / f"season={season}"
        out_dir.mkdir(parents=True, exist_ok=True)
        events = list(list_events(season, args.delay))
        saved = skipped = n_props = 0
        for i, ev in enumerate(events, 1):
            kickoff = datetime.fromisoformat(ev["kickoff"].replace("Z", "+00:00"))
            upcoming = not ev["completed"] and now <= kickoff <= now + UPCOMING_WINDOW
            final_path = out_dir / f"{ev['event_id']}__final.json.gz"
            if final_path.exists() or not (ev["completed"] or upcoming):
                skipped += 1
                continue
            record = fetch_event(ev, args.delay)
            stamp = now.strftime("%Y%m%dT%H%M%SZ")
            path = final_path if ev["completed"] else out_dir / f"{ev['event_id']}__{stamp}.json.gz"
            with gzip.open(path, "wt", encoding="utf-8") as f:
                json.dump(record, f)
            saved += 1
            n_props += sum(len(p["items"]) for p in record["props"].values())
            if i % 25 == 0 or i == len(events):
                print(f"{season}: {i}/{len(events)} games checked, {saved} saved, {n_props:,} props", flush=True)
        print(f"== {season} done: {saved} saved, {skipped} skipped, {n_props:,} props", flush=True)


if __name__ == "__main__":
    main()
