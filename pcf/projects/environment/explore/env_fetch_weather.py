"""Environment's exploration: fetch each game's weather from Open-Meteo (the CEO's sign-off, 2026-11-27).

- **archive:** the observed weather (ERA5 and its blends, "best match"), hourly, for every outdoor or open-roof game
  1999-2024, on the kickoff's UTC day and the next. It stands in for a forecast before 2022 (a stated assumption).
- **forecast:** the historical forecast API (the first hours of each run stitched together), the same hours, 2022-2024,
  so the gap between a forecast and the observed weather can be measured where both exist.
Saved raw, one JSON per game, under data/raw/open_meteo/<kind>/ (gitignored). Resumable: a saved game is skipped.
No key and no personal data in the requests. Run from pcf/:  python projects/environment/explore/env_fetch_weather.py
"""

# ruff: noqa: E501
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.data.gateway import read_part

HERE = Path(__file__).parent
VARS = "temperature_2m,precipitation,rain,snowfall,wind_speed_10m,wind_gusts_10m"
HOSTS = {
    "archive": "https://archive-api.open-meteo.com/v1/archive",
    "forecast": "https://historical-forecast-api.open-meteo.com/v1/forecast",
}


def games() -> pl.DataFrame:
    g = read_part("game", "schedule", list(range(1999, 2025)), None).collect()
    st = pl.read_csv(HERE / "stadiums.csv")
    g = g.filter(pl.col("roof").is_null() | pl.col("roof").is_in(["outdoors", "open"])).join(
        st, on="stadium_id", how="left"
    )
    assert g["lat"].null_count() == 0, g.filter(pl.col("lat").is_null())["stadium_id"].unique()
    return g.select("game_id", "season", "kickoff", "stadium_id", "lat", "lon")


def fetch(kind: str, row: dict, out: Path) -> bool:
    d0 = row["kickoff"].date()
    q = {
        "latitude": row["lat"],
        "longitude": row["lon"],
        "start_date": str(d0),
        "end_date": str(d0 + timedelta(days=1)),
        "hourly": VARS,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "GMT",
    }
    url = HOSTS[kind] + "?" + urllib.parse.urlencode(q)
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pcf-research/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out.write_text(r.read().decode("utf-8"), encoding="utf-8")
            return True
        except Exception as e:  # noqa: BLE001
            wait = 60 if "429" in str(e) else 5 * (attempt + 1)
            print(f"{kind} {row['game_id']}: {e}; retry in {wait}s", flush=True)
            time.sleep(wait)
    return False


def main() -> None:
    raw = get_config().zone("raw") / "open_meteo"
    g = games()
    plan = [("archive", g), ("forecast", g.filter(pl.col("season") >= 2022))]
    for kind, rows in plan:
        d = raw / kind
        d.mkdir(parents=True, exist_ok=True)
        todo = [r for r in rows.iter_rows(named=True) if not (d / f"{r['game_id']}.json").exists()]
        print(f"{kind}: {rows.height} games, {len(todo)} to fetch", flush=True)
        fails = 0
        for i, r in enumerate(todo):
            fails += not fetch(kind, r, d / f"{r['game_id']}.json")
            time.sleep(0.25)
            if i % 500 == 0:
                print(f"{kind}: {i}/{len(todo)}", flush=True)
        print(f"{kind}: done, {fails} failed", flush=True)
    json.dump({"vars": VARS}, sys.stdout)


if __name__ == "__main__":
    main()
