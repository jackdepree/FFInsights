"""What the opportunity-quality models share: points from the `player_game.opportunity` part in any
scoring, and a view's known player-games.

- **Expected points (xfp):** catches expected × points a catch + expected yards × points a yard +
  expected touchdowns × points a touchdown, summed over the game's targets and carries.
- **Points (fp):** the same pieces as they happened. Points over expected (poe) = fp − xfp.
- A rostered RB, WR or TE in a game with play-by-play has a row; no chances means 0.
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from pcf.baselines.common import CHANCE_SCORING

c = pl.col
POSITIONS = ("RB", "WR", "TE")
FIRST_SEASON = 2013  # participation's feature code starts with the snap counts (2013)
FIRST_XFP = 2012  # the first season with expected points (decision 0041)
KNOWN = "opportunity_known_at"


def weights(scoring: str) -> tuple[float, float, float]:
    if scoring not in CHANCE_SCORING:
        raise ValueError(f"no scoring {scoring!r}. Scorings: {', '.join(CHANCE_SCORING)}")
    return CHANCE_SCORING[scoring]


def xfp(scoring: str = "ppr") -> pl.Expr:
    """A player-game's expected points from the opportunity part."""
    rec, yard, td = weights(scoring)
    return (
        rec * c("oq_catch_exp")
        + yard * (c("oq_rec_yards_exp") + c("oq_rush_yards_exp"))
        + td * (c("oq_rec_td_exp") + c("oq_rush_td_exp"))
    )


def fp(scoring: str = "ppr") -> pl.Expr:
    """A player-game's points on his targets and carries, as they happened."""
    rec, yard, td = weights(scoring)
    return (
        rec * c("oq_catches")
        + yard * (c("oq_rec_yards") + c("oq_rush_yards"))
        + td * (c("oq_rec_tds") + c("oq_rush_tds"))
    )


def yac_points(scoring: str = "ppr") -> pl.Expr:
    """The points his yards after the catch over expected were worth."""
    return weights(scoring)[1] * c("oq_yac_oe")


def known_games(pg: pl.DataFrame, scoring: str = "ppr", extra: Sequence[str] = ()) -> pl.DataFrame:
    """A view's RB, WR and TE player-games whose chances are known and have expected points,
    oldest first: keys, season, week, team, position, xfp, fp, poe, the counts, and whether he
    played (a chance or an offensive snap)."""
    return (
        pg.filter(
            c(KNOWN).is_not_null()
            & c("oq_catch_exp").is_not_null()
            & c("position").is_in(POSITIONS)
        )
        .select(
            "gsis_id",
            "game_id",
            "season",
            "week",
            "team",
            "position",
            *extra,
            xfp=xfp(scoring),
            fp=fp(scoring),
            chances="oq_chances",
            targets="oq_targets",
            carries="oq_carries",
            xrec="oq_rec_yards_exp",
            xrush="oq_rush_yards_exp",
            xtd=c("oq_rec_td_exp") + c("oq_rush_td_exp"),
            gl="oq_gl_carries",
            rz="oq_rz_targets",
            ez="oq_ez_targets",
            deep="oq_deep_targets",
            air="oq_air_yards",
            yac=yac_points(scoring),
            yac_n="oq_yac_n",
            known_at=KNOWN,
        )  # fmt: skip
        .with_columns(poe=c("fp") - c("xfp"))
        .sort("gsis_id", "season", "week")
    )
