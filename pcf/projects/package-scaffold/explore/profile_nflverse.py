"""Light exploration for package-scaffold: a descriptive profile of the core nflverse tables.

For each table: rows, columns, seasons covered, date columns (earliest and latest), whether the
expected key columns are unique (its level of detail), and in-memory size. Play-by-play is loaded
one season at a time to keep memory low.

Run from any folder:  python pcf/projects/package-scaffold/explore/profile_nflverse.py
Needs nflreadpy and polars. Prints a markdown table; nothing is saved.
"""

import sys
import time

import nflreadpy as nfl
import polars as pl

sys.stdout.reconfigure(encoding="utf-8")

DATE_NAMES = ("date", "gameday", "dt", "date_pulled", "scrape_date", "trade_date", "date_modified")

# loader, kwargs, expected unique key columns (the table's level of detail)
TABLES = {
    "schedules": (nfl.load_schedules, {"seasons": True}, ["game_id"]),
    "player_stats": (nfl.load_player_stats, {"seasons": True}, ["player_id", "season", "week", "season_type"]),
    "team_stats": (nfl.load_team_stats, {"seasons": True}, ["team", "season", "week", "season_type"]),
    "snap_counts": (nfl.load_snap_counts, {"seasons": True}, ["pfr_player_id", "game_id"]),
    "ff_opportunity": (nfl.load_ff_opportunity, {"seasons": True}, ["player_id", "game_id"]),
    "nextgen_receiving": (nfl.load_nextgen_stats, {"seasons": True, "stat_type": "receiving"}, ["player_gsis_id", "season", "week", "season_type"]),
    "pfr_advstats_rec": (nfl.load_pfr_advstats, {"seasons": True, "stat_type": "rec", "summary_level": "week"}, ["pfr_player_id", "game_id"]),
    "participation": (nfl.load_participation, {"seasons": True}, ["nflverse_game_id", "play_id"]),
    "ftn_charting": (nfl.load_ftn_charting, {"seasons": True}, ["nflverse_game_id", "nflverse_play_id"]),
    "depth_charts": (nfl.load_depth_charts, {"seasons": True}, None),
    "injuries": (nfl.load_injuries, {"seasons": True}, ["gsis_id", "season", "week", "game_type"]),
    "rosters_weekly": (nfl.load_rosters_weekly, {"seasons": True}, ["gsis_id", "season", "week"]),
    "players": (nfl.load_players, {}, ["gsis_id"]),
    "ff_playerids": (nfl.load_ff_playerids, {}, None),
    "ff_rankings_all": (nfl.load_ff_rankings, {"type": "all"}, None),
    "combine": (nfl.load_combine, {"seasons": True}, None),
    "draft_picks": (nfl.load_draft_picks, {"seasons": True}, ["season", "pick"]),
    "trades": (nfl.load_trades, {}, None),
    "contracts": (nfl.load_contracts, {}, None),
    "officials": (nfl.load_officials, {"seasons": True}, None),
}


def date_range(df: pl.DataFrame) -> str:
    out = []
    for c in df.columns:
        dtype = df.schema[c]
        if dtype in (pl.Date, pl.Datetime) or isinstance(dtype, pl.Datetime) or (
            dtype == pl.Utf8 and any(c == n or c.endswith("_" + n) for n in DATE_NAMES)
        ):
            s = df[c].drop_nulls()
            if len(s):
                out.append(f"`{c}` {str(s.min())[:10]} → {str(s.max())[:10]}")
    return "; ".join(out[:3]) or "—"


def profile(name: str, df: pl.DataFrame, keys: list[str] | None, secs: float) -> str:
    seasons = "—"
    if "season" in df.columns:
        seasons = f"{df['season'].min()}–{df['season'].max()}"
    if keys and all(k in df.columns for k in keys):
        dupes = df.height - df.select(keys).unique().height
        grain = f"unique on {', '.join(keys)}" if dupes == 0 else f"{dupes:,} duplicate rows on {', '.join(keys)}"
    else:
        grain = "not checked"
    mb = df.estimated_size("mb")
    return f"| {name} | {df.height:,} | {df.width} | {seasons} | {date_range(df)} | {grain} | {mb:,.0f} MB | {secs:.0f}s |"


print("| Table | Rows | Columns | Seasons | Dates | Level of detail | Memory | Load |")
print("|---|---|---|---|---|---|---|---|")

# Play-by-play, one season at a time
t0, rows, mb, cols, per_season = time.time(), 0, 0.0, 0, []
dates = []
for season in range(1999, 2027):
    p = nfl.load_pbp(season)
    rows += p.height
    mb += p.estimated_size("mb")
    cols = p.width
    per_season.append((season, p.height))
    dates += [p["game_date"].drop_nulls().min(), p["game_date"].drop_nulls().max()]
    dupes = p.height - p.select(["game_id", "play_id"]).unique().height
    if dupes:
        print(f"<!-- pbp {season}: {dupes} duplicate game_id+play_id -->")
    del p
print(f"| pbp (all seasons) | {rows:,} | {cols} | 1999–2026 | `game_date` {min(dates)} → {max(dates)} | unique on game_id, play_id per season | {mb:,.0f} MB | {time.time() - t0:.0f}s |")

for name, (loader, kwargs, keys) in TABLES.items():
    t0 = time.time()
    try:
        df = loader(**kwargs)
        print(profile(name, df, keys, time.time() - t0))
    except Exception as e:  # a failing loader is itself a finding
        print(f"| {name} | failed: {type(e).__name__}: {str(e)[:80]} | | | | | | |")

print("\nPlay-by-play rows per season:", ", ".join(f"{s}: {n:,}" for s, n in per_season))
