"""The harness's own toy expert: PPR points from a player's recent games. Not the `baselines`
project, just a real model that runs every path end to end (validation-harness brief).

`RecentPoints` fits a weighted linear regression of PPR points on the last-4-games and
season-so-far averages known at the moment, with q10 and q90 from its training residuals.
`LastFour` is its no-fit baseline (the last-4 average itself), for the scorecard's comparison.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from pcf.core.contract import Expert

c = pl.col
POSITIONS = ("QB", "RB", "WR", "TE")
FEATURES = ["last4", "season_avg", "games"]
POINTS = "fantasy_points_ppr"


def _known_games(pg: pl.DataFrame) -> pl.DataFrame:
    """A player's games whose stats are known in this view, oldest first."""
    return (
        pg.filter(c("stats_known_at").is_not_null() & c(POINTS).is_not_null())
        .select("gsis_id", "season", "week", POINTS)
        .sort("gsis_id", "season", "week")
    )


class RecentPoints(Expert):
    id = "validation-harness"
    cadence = "in_season"
    grain = "player_game"
    inputs = {"player_game": ("stats",)}
    quantity = "ppr_points"
    kind = "amount"
    run = "tuesday"
    groups = ("position",)

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        season = int(games["season"].max())
        pg = view.table("player_game", seasons=[season - 1, season])
        known = _known_games(pg)
        recent = known.group_by("gsis_id").agg(
            last4=c(POINTS).tail(4).mean(), games=c(POINTS).len().cast(pl.Int32)
        )
        this_season = (
            known.filter(c("season") == season).group_by("gsis_id").agg(season_avg=c(POINTS).mean())
        )
        rows = pg.filter(
            c("game_id").is_in(games["game_id"].implode()) & c("position").is_in(POSITIONS)
        ).select(*self.keys(), "position")
        return (
            rows.join(recent, on="gsis_id", how="inner")
            .join(this_season, on="gsis_id", how="left")
            .with_columns(season_avg=c("season_avg").fill_null(c("last4")))
        )

    def target(self, view) -> pl.DataFrame:
        pg = view.table("player_game")
        return pg.filter(c("position").is_in(POSITIONS)).select(
            *self.keys(), y=c(POINTS), known_at=c("stats_known_at")
        )

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        x = np.column_stack(
            [np.ones(train.height), train.select(FEATURES).to_numpy().astype(float)]
        )
        y = train["y"].to_numpy().astype(float)
        w = np.sqrt(train["weight"].to_numpy().astype(float))
        beta, *_ = np.linalg.lstsq(x * w[:, None], y * w, rcond=None)
        resid = y - x @ beta
        return {"beta": beta, "offsets": np.quantile(resid, [0.1, 0.5, 0.9])}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        x = np.column_stack([np.ones(rows.height), rows.select(FEATURES).to_numpy().astype(float)])
        mean = x @ model["beta"]
        lo, mid, hi = model["offsets"]
        return rows.select(self.keys()).with_columns(
            mean=pl.Series(mean), q10=pl.Series(mean + lo), q50=pl.Series(mean + mid),
            q90=pl.Series(mean + hi),
        )  # fmt: skip

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return dict(zip(["intercept", *FEATURES], model["beta"].round(4).tolist(), strict=True))

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        """What the scorecard compares it with."""
        return [LastFour]


class LastFour(RecentPoints):
    """The no-fit baseline: the last-4 average, with ranges from its training residuals."""

    baseline = True

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        resid = (train["y"] - train["last4"]).to_numpy()
        return {"offsets": np.quantile(resid, [0.1, 0.5, 0.9])}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        lo, mid, hi = model["offsets"]
        return rows.select(
            *self.keys(), mean=c("last4"), q10=c("last4") + lo, q50=c("last4") + mid,
            q90=c("last4") + hi,
        )  # fmt: skip

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return {}
