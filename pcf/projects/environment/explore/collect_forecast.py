"""Live collector: Open-Meteo's weather forecast for every upcoming outdoor or open-roof game (environment's brief,
the CEO, 2026-11-27: "you may add it now").

Forecasts issued before kickoff can't be re-downloaded later at the lead we fetched them (Open-Meteo's archive of
past forecasts keeps only each run's first hours), so they are saved like the betting lines, in the private pcf-data
repo (rule g's exception). The collector runs this beside the odds (Tue, Thu, Sat, Sun and Mon), so a Sunday game
gets forecasts from about 5, 3, 1 and 0 days out, and the Sunday 12:00 UTC run is the morning-of forecast.

Saved append-only, one file per game per fetch:
    <data>/raw/open_meteo_live/season=<YYYY>/<game_id>__<fetched_utc>.json
Each file holds the game, the stadium's coordinates, the kickoff and fetch times (UTC), the lead in hours, and
Open-Meteo's raw hourly response for the kickoff's UTC day and the next.

Usage: python collect_forecast.py [--days 7]
Needs: requests (no key; the requests carry only coordinates and dates). Prints counts only.
"""

# ruff: noqa: E501
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

HERE = Path(__file__).resolve().parent
PCF_DIR = HERE.parents[2]
# Temporary until this moves into the package with environment's build (rule f).
DATA_DIR = Path(os.environ.get("PCF_DATA_DIR", PCF_DIR / "data"))
RAW_DIR = DATA_DIR / "raw" / "open_meteo_live"

GAMES = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
FORECAST = "https://api.open-meteo.com/v1/forecast"
VARS = "temperature_2m,precipitation,rain,snowfall,wind_speed_10m,wind_gusts_10m,wind_direction_10m"
INDOORS = {"dome", "closed"}
ET = ZoneInfo("America/New_York")

session = requests.Session()
session.headers["User-Agent"] = "pcf-research/0.1"


def get(url: str, params: dict | None = None, tries: int = 5) -> requests.Response:
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r
        except requests.RequestException as err:
            wait = 65 if "429" in str(err) else 5 * (attempt + 1)
            print(f"  retry {attempt + 1}/{tries} in {wait}s ({type(err).__name__})", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"giving up on {url}")


def upcoming(now: datetime, days: int) -> list[dict]:
    """Games kicking off in the next `days` days, not in a dome or under a closed roof."""
    rows = csv.DictReader(io.StringIO(get(GAMES).text))
    out = []
    for g in rows:
        if not g["gameday"] or not g["gametime"] or g["roof"] in INDOORS:
            continue
        kick = datetime.strptime(f"{g['gameday']} {g['gametime']}", "%Y-%m-%d %H:%M").replace(
            tzinfo=ET
        )
        kick = kick.astimezone(UTC)
        if now < kick <= now + timedelta(days=days):
            out.append(
                {
                    "game_id": g["game_id"],
                    "season": g["season"],
                    "stadium_id": g["stadium_id"],
                    "roof": g["roof"],
                    "kickoff_utc": kick,
                }
            )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    now = datetime.now(UTC).replace(microsecond=0)
    stamp = now.strftime("%Y%m%dT%H%MZ")
    with open(HERE / "stadiums.csv", encoding="utf-8") as f:
        where = {r["stadium_id"]: (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)}
    games = upcoming(now, a.days)
    missing = sorted({g["stadium_id"] for g in games if g["stadium_id"] not in where})
    games = [g for g in games if g["stadium_id"] in where]
    saved = 0
    for g in games:
        lat, lon = where[g["stadium_id"]]
        k = g["kickoff_utc"]
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": VARS,
            "start_date": str(k.date()),
            "end_date": str(k.date() + timedelta(days=1)),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "GMT",
        }
        body = get(FORECAST, params).json()
        rec = {
            "game_id": g["game_id"],
            "stadium_id": g["stadium_id"],
            "roof": g["roof"],
            "lat": lat,
            "lon": lon,
            "kickoff_utc": k.isoformat(),
            "fetched_utc": now.isoformat(),
            "lead_hours": round((k - now).total_seconds() / 3600, 1),
            "source": FORECAST,
            "response": body,
        }
        d = RAW_DIR / f"season={g['season']}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{g['game_id']}__{stamp}.json").write_text(json.dumps(rec), encoding="utf-8")
        saved += 1
        time.sleep(0.3)
    print(
        f"Open-Meteo forecasts: {saved} games saved (outdoor or open, next {a.days} days)"
        + (
            f"; no coordinates for {len(missing)} stadiums: {', '.join(missing)}" if missing else ""
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
