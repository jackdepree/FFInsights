"""Football sanity for the plus-minus (2026-11-11): who sits at each end, 2016-2024, by group?
Pass rate over expected on the plays a player was on the field minus off them, same team-game,
weighted as in h26_h28_h29_h31.py; players with at least 150 of that weight."""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from common import CACHE, SEASONS, _part  # noqa: E402

c = pl.col
pg = pl.read_parquet(CACHE / "player_game_pm.parquet")
names = _part("player_game", "roster", SEASONS, ["gsis_id", "full_name"]).unique("gsis_id")
pm = (
    pg.filter(c("h_proe") > 0)
    .group_by("gsis_id", "side", "group")
    .agg(pm=(c("d_proe") * c("h_proe")).sum() / c("h_proe").sum(), w=c("h_proe").sum(), share=c("n_on").sum() / c("n_team").sum(), seasons=c("season").n_unique())
    .filter(c("w") >= 150)
    .join(names, on="gsis_id", how="left")
)
pl.Config.set_tbl_rows(80)
pl.Config.set_tbl_width_chars(200)
for g in ("QB", "RB", "WR", "TE", "DB", "LB"):
    d = pm.filter(c("group") == g).sort("pm")
    print(f"\n== {g}: {d.height} players; the 5 lowest and 5 highest (points of PROE)")
    show = pl.concat([d.head(5), d.tail(5)]).select("full_name", pm=(c("pm") * 100).round(1), share=c("share").round(2), seasons="seasons")
    print(show)
