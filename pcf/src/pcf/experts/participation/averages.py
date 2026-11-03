"""Rung 0: a player's own recent share as the prediction. No fit but the ranges, which are the
average plus each position's training residuals, kept between 0 and 1."""

from __future__ import annotations

from typing import Any, ClassVar

import polars as pl

from pcf.baselines.common import fit_offsets, predicted_rows, with_ranges
from pcf.core.contract import PREDICTION, Expert
from pcf.experts.participation.common import FIRST_SEASON, known_shares, target_share

c = pl.col
BY = ("position",)


class _Average(Expert):
    """One average of the player's known shares as the prediction."""

    id = "participation"
    cadence = "in_season"
    grain = "player_game"
    inputs = {"player_game": ("snaps", "game_status")}
    kind = "amount"
    run = "saturday"
    groups = ("position",)
    first_train = FIRST_SEASON
    column: ClassVar[str]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        """last_game, last3, last3_active and games, from the player's games known in the view.
        A player never active has no last3_active: that's 0, as they've never played a snap."""
        season = int(games["season"].max())
        pg = view.table("player_game", seasons=[season - 1, season])
        avgs = (
            known_shares(pg)
            .group_by("gsis_id")
            .agg(
                last_game=c("share").last(),
                last3=c("share").tail(3).mean(),
                last3_active=c("share").filter(c("active")).tail(3).mean(),
                games=c("share").len().cast(pl.Int32),
            )
            .with_columns(c("last3_active").fill_null(0.0))
        )
        return predicted_rows(pg, games, self.keys()).join(avgs, on="gsis_id", how="inner")

    def target(self, view) -> pl.DataFrame:
        return target_share(view.table("player_game"), self.keys())

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        resid = train.select(*BY, "weight", resid=c("y") - c(self.column))
        return {"offsets": fit_offsets(resid, BY)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.select(*self.keys(), *BY, mean=c(self.column))
        return with_ranges(out, model["offsets"], BY).select(
            *self.keys(), *[c(p).clip(0.0, 1.0) for p in PREDICTION]
        )

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return {"offsets": model["offsets"].to_dicts()}


class LastGame(_Average):
    """Last game's share, 0 if inactive."""

    variant = "last_game"
    quantity = "snap_share"
    column = "last_game"


class Last3(_Average):
    """The last 3 games' average, an absence counting as 0."""

    variant = "last3"
    quantity = "snap_share"
    column = "last3"


class Last3Active(_Average):
    """The last 3 games the player was active, so an absence doesn't read as a lost role."""

    variant = "last3_active"
    quantity = "snap_share"
    column = "last3_active"
