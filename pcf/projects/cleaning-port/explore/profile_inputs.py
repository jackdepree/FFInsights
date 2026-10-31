"""Light exploration for cleaning-port: what do the old cleaning functions need, and does our raw
copy give it to them?

1. Profiles participation (player lists per play) and depth charts, season by season.
2. Runs the old functions, read straight from old/code/Fatigue_Model_Prod.ipynb (read only), on
   our raw copy for a few seasons, and counts what they keep, drop and label.

Run from pcf/:  uv run python projects/cleaning-port/explore/profile_inputs.py
"""

import ast
import json
import time
import warnings

import numpy as np
import pandas as pd
import polars as pl

from pcf.config import PCF_DIR
from pcf.data.sources.nflverse import scan

OLD_NOTEBOOK = PCF_DIR.parent / "old" / "code" / "Fatigue_Model_Prod.ipynb"
PORTED = {"pivot_wide_both_sides", "clean_depth_charts", "pivot_long_both_sides"}


def old_functions() -> dict:
    """Compile the old functions from the notebook's code cells, without running anything else."""
    nb = json.loads(OLD_NOTEBOOK.read_text(encoding="utf-8"))
    namespace: dict = {"pd": pd, "np": np}
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        try:
            tree = ast.parse("".join(cell["source"]))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in PORTED:
                exec(compile(ast.Module([node], []), str(OLD_NOTEBOOK), "exec"), namespace)
    return {k: namespace[k] for k in PORTED}


def profile_participation() -> None:
    print("\n== participation ==")
    for season in range(2016, 2026):
        p = scan("participation", [season]).collect()
        n_off = p["offense_players"].str.split(";").list.len()
        n_def = p["defense_players"].str.split(";").list.len()
        empty = p["offense_players"].is_null() | (p["offense_players"] == "")
        print(
            f"{season}: {p.height:6,} plays x {p.width} cols | empty offense list {empty.mean():.1%}"
            f" | offense 11: {(n_off == 11).mean():.1%}, defense 11: {(n_def == 11).mean():.1%}"
            f" | max {n_off.max()}/{n_def.max()}"
        )
    print("columns (2025):", scan("participation", [2025]).collect_schema().names())


def profile_depth_charts() -> None:
    print("\n== depth charts ==")
    for season in [2016, 2020, 2024, 2025, 2026]:
        d = scan("depth_charts", [season]).collect()
        print(f"{season}: {d.height:,} rows | columns: {d.columns}")
        for col in ["formation", "position", "depth_position", "week", "game_type", "pos_grp"]:
            if col in d.columns:
                vc = d[col].value_counts(sort=True).head(12)
                print(f"   {col}: {dict(zip(vc[col].to_list(), vc['count'].to_list()))}")
        if "dt" in d.columns:
            print(f"   dt: {d['dt'].n_unique()} distinct, {d['dt'].min()} -> {d['dt'].max()}")


def run_old(fns: dict, season: int) -> None:
    # play_id is a float in older play-by-play files and an integer in participation.
    pbp = (
        scan("pbp", [season])
        .select("game_id", "play_id", "play_type", "season", "week", "season_type")
        .with_columns(pl.col("play_id").cast(pl.Int64))
        .collect()
    )
    part = (
        scan("participation", [season])
        .select("nflverse_game_id", "play_id", "offense_players", "defense_players")
        .with_columns(pl.col("play_id").cast(pl.Int64))
        .collect()
    )
    plays = pbp.join(part, left_on=["game_id", "play_id"], right_on=["nflverse_game_id", "play_id"], how="left")
    depth = scan("depth_charts", [season]).collect().to_pandas()
    plays_pd = plays.to_pandas()
    t = time.time()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wide = fns["pivot_wide_both_sides"](plays_pd)
        clean = fns["clean_depth_charts"](depth)
        long = fns["pivot_long_both_sides"](wide, depth)
    rp = plays.filter(pl.col("play_type").is_in(["run", "pass"]))
    no_list = rp["offense_players"].is_null() | (rp["offense_players"] == "")
    n_off = rp["offense_players"].str.split(";").list.len()
    n_def = rp["defense_players"].str.split(";").list.len()
    print(
        f"{season}: run/pass plays with no player list {no_list.mean():.1%};"
        f" with 11 a side {((n_off == 11) & (n_def == 11)).mean():.1%}"
    )
    # How many listed players have no depth-chart row that week (the old code labels them 'special')
    ids = rp.select("season", "week", "season_type", pl.concat_list(
        pl.col("offense_players").str.split(";"), pl.col("defense_players").str.split(";")
    ).alias("gsis_id")).explode("gsis_id").filter(pl.col("gsis_id").is_not_null() & (pl.col("gsis_id") != ""))
    dc = pl.from_pandas(clean[["season", "week", "gsis_id"]]).unique().with_columns(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), hit=pl.lit(True))
    hits = ids.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32)).join(
        dc, on=["season", "week", "gsis_id"], how="left")
    by = hits.group_by("season_type").agg(unmatched=pl.col("hit").is_null().mean(), n=pl.len()).sort("season_type")
    print(f"   listed players with no depth-chart row that week: {by.rows()}")
    pbp_weeks = sorted(rp.filter(pl.col("season_type") == "POST")["week"].unique().to_list())
    dc_post = sorted(set(clean.loc[clean["game_type"] != "REG", "week"].unique()))
    print(f"   playoff weeks: play-by-play {pbp_weeks}, depth charts {dc_post}")
    run_pass = len(rp)
    slots = long.groupby(["game_id", "play_id"]).size()
    special = (long["position_label"] == "special").mean()
    print(
        f"{season}: run/pass plays {run_pass:,} -> wide {len(wide):,} -> long {len(long):,} rows"
        f" ({len(long) / max(len(wide), 1):.1f} per play) | plays with 22 players {(slots == 22).mean():.1%}"
        f" | labelled 'special' {special:.1%} | {time.time() - t:.0f}s"
    )
    top = long["position_label"].value_counts().head(15)
    print(f"   top labels: {dict(top)}")
    print(f"   clean depth charts: {len(clean):,} rows, weeks {sorted(clean['week'].unique())[:25]}")


def main() -> None:
    profile_participation()
    profile_depth_charts()
    print("\n== old functions on our raw copy ==")
    fns = old_functions()
    for season in [2016, 2020, 2024, 2025]:
        try:
            run_old(fns, season)
        except Exception as e:  # noqa: BLE001 - exploration: report and continue
            print(f"{season}: FAILED {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
