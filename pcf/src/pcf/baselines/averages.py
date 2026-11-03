"""The averages: a player's fantasy points over the last 4 games, this season so far, and last
season (VALIDATION.md §6). No fit but the ranges: q10, q50 and q90 are the average plus each
position's training residuals (D7)."""

from __future__ import annotations

from typing import Any, ClassVar

import polars as pl

from pcf.baselines.common import (
    fit_offsets,
    known_games,
    predicted_rows,
    target_points,
    with_ranges,
)
from pcf.core.contract import Expert

c = pl.col
BY = ("position",)


class _Average(Expert):
    """One average as the prediction. `scoring` sets the fantasy format (D2)."""

    id = "baselines"
    cadence = "in_season"
    grain = "player_game"
    inputs = {"player_game": ("stats",)}
    kind = "amount"
    run = "tuesday"
    groups = ("position",)
    scoring: ClassVar[str] = "ppr"
    column: ClassVar[str]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        """last4, season_avg (this season so far, else last season's), last_season and games,
        from the player's games known in the view."""
        season = int(games["season"].max())
        pg = view.table("player_game", seasons=[season - 1, season])
        known = known_games(pg, self.scoring)
        avgs = known.group_by("gsis_id").agg(
            last4=c("points").tail(4).mean(),
            games=c("points").len().cast(pl.Int32),
            this_season=c("points").filter(c("season") == season).mean(),
            last_season=c("points").filter(c("season") == season - 1).mean(),
        )
        return (
            predicted_rows(pg, games, self.keys())
            .join(avgs, on="gsis_id", how="inner")
            .with_columns(season_avg=pl.coalesce("this_season", "last_season"))
            .drop("this_season")
        )

    def target(self, view) -> pl.DataFrame:
        return target_points(view.table("player_game"), self.scoring, self.keys())

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        resid = train.drop_nulls(self.column).select(*BY, "weight", resid=c("y") - c(self.column))
        return {"offsets": fit_offsets(resid, BY)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        # Rows without this average (rookies, for last season's) get no prediction.
        out = rows.drop_nulls(self.column).select(*self.keys(), *BY, mean=c(self.column))
        return with_ranges(out, model["offsets"], BY).select(
            *self.keys(), "mean", "q10", "q50", "q90"
        )

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return {"offsets": model["offsets"].to_dicts()}


class RollingAverage(_Average):
    """The last 4 games (across the season boundary)."""

    variant = "rolling4"
    quantity = "ppr_points"
    column = "last4"


class SeasonAverage(_Average):
    """This season so far; in week 1, last season's."""

    variant = "season"
    quantity = "ppr_points"
    column = "season_avg"


class LastSeason(_Average):
    """Last season's per-game average (rookies have none, so no prediction)."""

    variant = "last_season"
    quantity = "ppr_points"
    column = "last_season"
