"""Availability's standing measures (decision 0047): the snap-weighted adjusted games lost, and
what proneness and absences look like as measures (their consistency, CLAUDE.md's second test).

**Snap-weighted adjusted games lost** (the CEO's version of Football Outsiders'): per team-game,
the sum over its players' health absences of each one's weight, his snap share on his side in
his earlier games that season, known before the game (the CEO, 2026-11-24: "only what was known
before the game to weight by their share"). Before his first game of a season, last season's
share; with neither, his position's average share last season (decision 0047 call 7).
Offense (QB, RB, WR, TE, OL) and defense (DL, LB, DB) are summed apart; specialists are left out.
"""

from __future__ import annotations

import polars as pl

from pcf.experts.availability.common import FIRST_TRAIN

c = pl.col
OFFENSE = ("QB", "RB", "WR", "TE", "OL")
DEFENSE = ("DL", "LB", "DB")


def weights(tl: pl.DataFrame) -> pl.DataFrame:
    """Each player-game's weight from his record: gsis_id, game_id, side, weight (see the
    module's doc). `tl` is `common.timeline` over every season wanted (and the one before)."""
    tl = tl.filter(c("position").is_in([*OFFENSE, *DEFENSE])).sort("gsis_id", "season", "week")
    share = pl.when(c("played")).then(c("share"))
    earlier = (share.fill_null(0.0).cum_sum() - share.fill_null(0.0)).over("gsis_id", "season")
    n_earlier = (
        (c("played").cast(pl.Float64).cum_sum() - c("played").cast(pl.Float64))
        .over("gsis_id", "season")
    )  # fmt: skip
    tl = tl.with_columns(this_season=pl.when(n_earlier > 0).then(earlier / n_earlier))
    last = (
        tl.filter(c("played"))
        .group_by("gsis_id", "season")
        .agg(last_season=c("share").mean())
        .with_columns(c("season") + 1)
    )
    pos = (
        tl.filter(c("played"))
        .group_by("position", "season")
        .agg(pos_share=c("share").mean())
        .with_columns(c("season") + 1)
    )
    return (
        tl.join(last, on=["gsis_id", "season"], how="left")
        .join(pos, on=["position", "season"], how="left")
        .select(
            "gsis_id", "game_id", "team", "season", "week", "position", "absent",
            side=pl.when(c("position").is_in(list(OFFENSE))).then(pl.lit("off")).otherwise(pl.lit("def")),
            weight=pl.coalesce("this_season", "last_season", "pos_share"),
        )
    )  # fmt: skip


def agl(tl: pl.DataFrame) -> pl.DataFrame:
    """Snap-weighted adjusted games lost per team-game and side (2016 on): agl (weighted), and
    the plain count of health absences of players whose weight is 0.5 or more (`starters_out`)."""
    w = weights(tl).filter(c("season") >= FIRST_TRAIN)
    return (
        w.group_by("game_id", "team", "season", "week", "side")
        .agg(
            agl=(c("absent").cast(pl.Float64) * c("weight")).sum(),
            starters_out=(c("absent") & (c("weight") >= 0.5)).sum().cast(pl.Float64),
        )
        .sort("season", "week", "team", "side")
    )


def agl_forecast(hist: pl.DataFrame, w: pl.DataFrame, column: str = "mean") -> pl.DataFrame:
    """A team-game's forecast of snap-weighted games lost over a window: the sum over its
    players' rows (`hist`: gsis_id, game_id, `column`, the games of health absence expected) of
    each one's weight going into that game (`weights`)."""
    j = hist.select("gsis_id", "game_id", column).join(
        w.select("gsis_id", "game_id", "team", "side", "weight"), on=["gsis_id", "game_id"]
    )
    return j.group_by("game_id", "team", "side").agg(
        agl_hat=(c(column) * c("weight")).sum()
    )
