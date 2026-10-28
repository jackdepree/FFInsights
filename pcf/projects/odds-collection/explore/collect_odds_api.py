"""Exploration collector: The Odds API snapshots (free Starter tier, 500 credits/month).

Each run saves:
    <data>/raw/odds_api/season=<YYYY>/game_lines__<fetched_utc>.json.gz   all games: h2h, spreads, totals (3 credits)
    <data>/raw/odds_api/season=<YYYY>/props__<event_id>.json.gz           player props with prices, once per game,
                                                                          fetched in the last hours before kickoff
Each game's props are fetched only once, so a week of about 16 games costs about 80 credits.
The run stops early if the credits left fall below --reserve.

The key comes from the ODDS_API_KEY environment variable, or from pcf/.env. If no key is set, the run
skips quietly. The key is never printed: errors report only the HTTP status, because this runs in
public Actions logs.

This is exploration code (rule i). It moves into the package when odds-collection reaches Building.

Usage: python collect_odds_api.py [--window-hours 14] [--reserve 40]
Needs: requests
"""
import argparse
import gzip
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

PCF_DIR = Path(__file__).resolve().parents[3]
# Temporary until the package's central config exists (rule f).
DATA_DIR = Path(os.environ.get("PCF_DATA_DIR", PCF_DIR / "data"))
RAW_DIR = DATA_DIR / "raw" / "odds_api"

API = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl"
PROP_MARKETS = ["player_anytime_td", "player_receptions", "player_reception_yds",
                "player_rush_yds", "player_pass_yds"]


def api_key():
    if os.environ.get("ODDS_API_KEY"):
        return os.environ["ODDS_API_KEY"]
    env_file = PCF_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "ODDS_API_KEY" and value.strip():
                return value.strip()
    return None


def get(path, key, **params):
    """GET from The Odds API. Returns (json, credits_remaining). Never prints the key."""
    r = requests.get(f"{API}{path}", params={"apiKey": key, **params}, timeout=30)
    if not r.ok:
        sys.exit(f"The Odds API returned HTTP {r.status_code} for {path}")
    remaining = r.headers.get("x-requests-remaining")
    return r.json(), (float(remaining) if remaining is not None else None)


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--window-hours", type=float, default=14,
                        help="fetch props for games kicking off within this many hours")
    parser.add_argument("--reserve", type=float, default=40, help="stop if credits left drop below this")
    args = parser.parse_args()

    key = api_key()
    if not key:
        print("ODDS_API_KEY not set: skipping The Odds API snapshot")
        return

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    season = now.year if now.month >= 3 else now.year - 1
    out_dir = RAW_DIR / f"season={season}"

    lines, remaining = get("/odds", key, regions="us", markets="h2h,spreads,totals", oddsFormat="american")
    save(out_dir / f"game_lines__{stamp}.json.gz", {"fetched_at": now.isoformat(), "data": lines})
    print(f"game lines: {len(lines)} games saved, credits left {remaining}")

    events, _ = get("/events", key)  # free: costs no credits
    soon = [
        e for e in events
        if now <= datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) <= now + timedelta(hours=args.window_hours)
    ]
    fetched = 0
    for event in soon:
        path = out_dir / f"props__{event['id']}.json.gz"
        if path.exists():
            continue
        if remaining is not None and remaining < args.reserve:
            print(f"stopping: credits left {remaining} < reserve {args.reserve}")
            break
        props, remaining = get(f"/events/{event['id']}/odds", key, regions="us",
                               markets=",".join(PROP_MARKETS), oddsFormat="american")
        save(path, {"fetched_at": datetime.now(timezone.utc).isoformat(), "event": event, "data": props})
        fetched += 1
    print(f"props: {fetched} of {len(soon)} games in the next {args.window_hours:g}h saved, credits left {remaining}")


if __name__ == "__main__":
    main()
