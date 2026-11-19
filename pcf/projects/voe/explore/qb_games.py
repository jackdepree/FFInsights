# ruff: noqa: E501
"""voe, a sanity check for H72 (2026-11-19): does the leftover see a QB change at all? A team's
offense EPA over expected a play in games its season's main QB (most plays) missed, against its
games he played start to finish, the same team-season. Discovery only, 2016-2024.

Run from pcf/:  python projects/voe/explore/qb_games.py > projects/voe/explore/qb_games.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402

c = pl.col


def main():
    p = fl.plays()
    on = fl.on_field(p).filter((c("side") == "offense") & (c("group") == "QB"))
    off = (
        p.filter(c("season").is_in(fl.SEASONS))
        .group_by("game_id", team=c("posteam"), season=c("season"))
        .agg(rate=c("resid").mean(), n=pl.len())
    )
    qbp = on.group_by("gsis_id", "team", "season", "game_id").agg(k=pl.len())
    main_qb = (
        qbp.group_by("team", "season", "gsis_id")
        .agg(tot=c("k").sum())
        .sort("tot", descending=True)
        .unique(["team", "season"], keep="first")
    )
    g = (
        off.join(main_qb.select("team", "season", "gsis_id"), on=["team", "season"])
        .join(qbp.select("gsis_id", "game_id", "k"), on=["gsis_id", "game_id"], how="left")
        .with_columns(share=c("k").fill_null(0) / c("n"))
    )
    g = g.with_columns(
        kind=pl.when(c("share") >= 0.95)
        .then(pl.lit("played"))
        .when(c("share") == 0)
        .then(pl.lit("missed"))
        .otherwise(pl.lit("part"))
    )
    w = (
        g.group_by("team", "season", "kind")
        .agg(r=(c("rate") * c("n")).sum() / c("n").sum(), n=c("n").sum(), games=pl.len())
        .pivot(on="kind", index=["team", "season"], values=["r", "n", "games"])
    )
    w = w.filter(c("r_missed").is_not_null() & c("r_played").is_not_null())
    d = (w["r_missed"] - w["r_played"]).to_numpy()
    wt = (1 / (1 / w["n_missed"] + 1 / w["n_played"])).to_numpy()
    est = fl.wmean_ci(d, wt)
    print(
        f"Team-seasons where the main QB missed whole games: {w.height}; games missed {int(w['games_missed'].sum())}"
    )
    print(
        f"Offense EPA over expected a play, missed less played, same team-season: {est[0]:+.3f} (90% {est[1]:+.3f} to {est[2]:+.3f})"
    )
    print(
        f"For scale: the spread of teams' full-season offense rate {p.filter(c('season').is_in(fl.SEASONS)).group_by('posteam', 'season').agg(r=c('resid').mean())['r'].std():.3f}; a starter's plus-minus spread (QB, 300+ plays) about 0.004 a play at the chosen shrinkage"
    )
    _ = np


if __name__ == "__main__":
    main()
