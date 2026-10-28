"""Exploration parser: turn raw ESPN odds files into two tidy tables.

    <data>/interim/espn_odds/props.parquet       one row per player prop per book per fetch
    <data>/interim/espn_odds/game_lines.parquet  one row per game per book per fetch (open and close)

Rows are joined to nflverse ids: game_id from load_schedules, gsis_id from load_ff_playerids.
This is exploration code (rule i). It moves into the package when odds-collection reaches Building.

Usage: python parse_espn.py
Needs: polars, nflreadpy
"""
import gzip
import json
import os
from pathlib import Path

import nflreadpy as nfl
import polars as pl

PCF_DIR = Path(__file__).resolve().parents[3]
# Temporary until the package's central config exists (rule f).
DATA_DIR = Path(os.environ.get("PCF_DATA_DIR", PCF_DIR / "data"))
RAW_DIR = DATA_DIR / "raw" / "espn_odds"
OUT_DIR = DATA_DIR / "interim" / "espn_odds"


def american(side, key):
    """Read an American-odds or line value like '-110', '+3.5' or '44.5' as a float."""
    value = ((side or {}).get(key) or {}).get("american")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ref_id(obj, marker):
    """Pull the id that follows `marker` out of an ESPN $ref URL."""
    ref = (obj or {}).get("$ref", "")
    return ref.split(marker)[1].split("?")[0].split("/")[0] if marker in ref else None


def parse_file(path):
    record = json.load(gzip.open(path, "rt", encoding="utf-8"))
    ev, fetched_at = record["event"], record["fetched_at"]
    base = {
        "espn_event_id": ev["event_id"], "season": ev["season"], "seasontype": ev["seasontype"],
        "week": ev["week"], "kickoff": ev["kickoff"], "completed_at_fetch": ev["completed"],
        "fetched_at": fetched_at,
    }
    props = []
    for provider_id, block in record["props"].items():
        for item in block["items"]:
            props.append({
                **base,
                "provider_id": provider_id,
                "provider_name": block["provider_name"],
                "espn_athlete_id": ref_id(item.get("athlete"), "/athletes/"),
                "market_id": item.get("type", {}).get("id"),
                "market_name": item.get("type", {}).get("name"),
                "open_line": ((item.get("open") or {}).get("target") or {}).get("value"),
                "current_line": ((item.get("current") or {}).get("target") or {}).get("value"),
                "last_updated": item.get("lastUpdated"),
            })
    games = []
    for item in record["odds"].get("items", []):
        provider = item.get("provider", {})
        row = {**base, "provider_id": str(provider.get("id")), "provider_name": provider.get("name")}
        for when in ("open", "close"):
            totals = item.get(when) or {}
            home = (item.get("homeTeamOdds") or {}).get(when) or {}
            away = (item.get("awayTeamOdds") or {}).get(when) or {}
            row |= {
                f"{when}_home_spread": american(home, "pointSpread"),
                f"{when}_home_spread_price": american(home, "spread"),
                f"{when}_away_spread_price": american(away, "spread"),
                f"{when}_home_moneyline": american(home, "moneyLine"),
                f"{when}_away_moneyline": american(away, "moneyLine"),
                f"{when}_total": american(totals, "total"),
                f"{when}_over_price": american(totals, "over"),
                f"{when}_under_price": american(totals, "under"),
            }
        games.append(row)
    return props, games


def main():
    props, games = [], []
    files = sorted(RAW_DIR.glob("season=*/*.json.gz"))
    for path in files:
        p, g = parse_file(path)
        props += p
        games += g

    game_ids = (
        nfl.load_schedules()
        .select(pl.col("espn").cast(pl.Utf8).alias("espn_event_id"), "game_id")
        .drop_nulls()
    )
    player_ids = (
        nfl.load_ff_playerids()
        .select(pl.col("espn_id").cast(pl.Utf8).alias("espn_athlete_id"), "gsis_id", "name", "position")
        .drop_nulls("espn_athlete_id")
        .unique("espn_athlete_id")
    )
    props_df = pl.DataFrame(props, infer_schema_length=None).join(game_ids, on="espn_event_id", how="left")
    props_df = props_df.join(player_ids, on="espn_athlete_id", how="left")
    games_df = pl.DataFrame(games, infer_schema_length=None).join(game_ids, on="espn_event_id", how="left")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    props_df.write_parquet(OUT_DIR / "props.parquet")
    games_df.write_parquet(OUT_DIR / "game_lines.parquet")
    print(f"{len(files)} raw files -> {props_df.height:,} prop rows, {games_df.height:,} game-line rows")
    print(f"unmatched: game_id {props_df['game_id'].null_count():,} prop rows, "
          f"gsis_id {props_df.filter(pl.col('espn_athlete_id').is_not_null())['gsis_id'].null_count():,} prop rows")


if __name__ == "__main__":
    main()
