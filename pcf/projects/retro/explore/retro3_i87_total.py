# ruff: noqa: E501
"""IDEAS I87 (retro 3's quick group, 2026-11-23): the closing total after an in-season QB change.

I83 (retro 2) found the closing spread about a point too kind to a team in games 1-4 after an
in-season change of starting QB. The total may carry it more cleanly. Claude's odds, written
2026-11-20 before this run: 45% that the total is too high there by 1+ point; 20% that unders
clear 52.4% beyond the shuffles.

One row per game, 2006-2024 regular season (the 2025 vault and 2026 left out). A game is flagged
when either team is in games 1-4 after an in-season QB change (I47's flag). The miss is points
scored minus the closing total; the bet is the under (pushes left out). The same weeks' other
games are the comparison; intervals from resampling weeks; the under's rate against 52.4% and
against 400 shuffles of the flag within each week. Helpers from retro2_i83_line.py.

Run from pcf/:  python projects/retro/explore/retro3_i87_total.py > projects/retro/explore/retro3_i87_total.txt
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
spec = importlib.util.spec_from_file_location("i83", Path(__file__).with_name("retro2_i83_line.py"))
i83 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i83)
Q = "starting QB changed in season, games 1-4 after"
Q5 = "starting QB changed in season, games 5 on after"


def main() -> None:
    src = Gateway().source
    te = i83.i47.team_events(src)
    line = src.part("team_game", "pregame").select("game_id", "team", "total_line")
    res = src.part("team_game", "result").select("game_id", "team", "points_for", "points_against")
    typ = src.part("game", "schedule").select("game_id", "game_type")
    t = (
        te.join(line, on=["game_id", "team"]).join(res, on=["game_id", "team"]).join(typ, on="game_id")
        .filter(c("season").is_between(i83.FIRST, i83.LAST) & (c("game_type") == "REG"))
        .drop_nulls(["total_line", "points_for"])
        .with_columns(c(Q).fill_null(False), c(Q5).fill_null(False))
    )  # fmt: skip
    g = (
        t.group_by("game_id")
        .agg(
            c("season").first(),
            c("week").first(),
            c("total_line").first(),
            pts=(c("points_for") + c("points_against")).first(),
            **{Q: c(Q).any(), Q5: c(Q5).any(), "both teams": c(Q).all()},
        )
        .with_columns(miss=c("pts") - c("total_line"))
        .with_columns(cover=pl.when(c("miss") < 0).then(1.0).when(c("miss") > 0).then(0.0))
    )
    rng = np.random.default_rng(get_config().seed)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(240)
    pl.Config.set_fmt_str_lengths(60)
    pl.Config.set_float_precision(3)
    print(f"games {i83.FIRST}-{i83.LAST}, regular season, with a closing total: {g.height}")
    print(f"the total's average miss overall: {g['miss'].mean():+.3f} points; under rate {g['cover'].mean():.3f}\n")
    print("== the total's miss (points minus the closing total), flagged games minus the same weeks' others; 90% from resampling weeks")
    print(pl.DataFrame([{"games flagged": f, **i83.gap(g, f, rng)} for f in (Q, Q5, "both teams")]))
    print("\n== the pre-registered bet: the under in games 1-4 after (and, shown beside it, games 5 on)")
    print(pl.DataFrame([{"games flagged": f, **i83.cover(g, f, 1, rng)} for f in (Q, Q5)]))
    print("   (side 'on' here means the under)")


if __name__ == "__main__":
    main()
