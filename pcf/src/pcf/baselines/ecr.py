"""FantasyPros' expert consensus ranking (ECR) as a projection: the benchmark the charter names
("at least as accurate as ECR").

ECR is a rank, not points (baselines#F7). Each position's rank-to-points curve is an isotonic
fit on training weeks: a better rank never projects fewer points. Ranges come from training
residuals per position and rank band (D7). It's judged where an honest weekly ranking exists: the
Saturday run, Sunday and Monday games, from 2022 after a 2021 training season (D4). The `ecr`
table part already holds only games that kick off after the snapshot is known (D3).
"""

from __future__ import annotations

from typing import Any

import polars as pl
from sklearn.isotonic import IsotonicRegression

from pcf.baselines.common import POSITIONS, fit_offsets, target_points, with_ranges
from pcf.core.contract import Expert

c = pl.col
# Rank bands for the ranges: the starters in a 12-team league, then the next two tiers.
BANDS = (12, 24, 36)
BY = ("position", "band")


def band(rank: pl.Expr) -> pl.Expr:
    out = pl.when(rank <= BANDS[0]).then(pl.lit(f"1-{BANDS[0]}"))
    for lo, hi in zip(BANDS, BANDS[1:], strict=False):
        out = out.when(rank <= hi).then(pl.lit(f"{lo + 1}-{hi}"))
    return out.otherwise(pl.lit(f"{BANDS[-1] + 1}+"))


class Ecr(Expert):
    id = "baselines"
    variant = "ecr"
    cadence = "in_season"
    grain = "player_game"
    inputs = {"player_game": ("stats", "ecr")}
    quantity = "ppr_points"
    kind = "amount"
    run = "saturday"
    groups = ("position", "band")
    benchmark = True
    first_train = 2021

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        """This moment's ranked player-games: rank, expert spread, position and rank band."""
        season = int(games["season"].max())
        pg = view.table("player_game", seasons=[season])
        return (
            pg.filter(
                c("game_id").is_in(games["game_id"].implode())
                & c("ecr_known_at").is_not_null()
                & c("ecr_position").is_in(POSITIONS)
            )
            .select(*self.keys(), "ecr_rank", "ecr_sd", position="ecr_position")
            .with_columns(band=band(c("ecr_rank")))
        )

    def target(self, view) -> pl.DataFrame:
        return target_points(view.table("player_game"), "ppr", self.keys())

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        curves = {}
        for (pos,), g in train.group_by("position"):
            iso = IsotonicRegression(increasing=False, out_of_bounds="clip")
            iso.fit(
                g["ecr_rank"].to_numpy(), g["y"].to_numpy(), sample_weight=g["weight"].to_numpy()
            )
            curves[pos] = iso
        fitted = self._curve(curves, train)
        resid = train.select(*BY, "weight", resid=c("y") - fitted)
        return {"curves": curves, "offsets": fit_offsets(resid, BY)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        rows = rows.filter(c("position").is_in(list(model["curves"])))
        out = rows.select(*self.keys(), *BY).with_columns(mean=self._curve(model["curves"], rows))
        return with_ranges(out, model["offsets"], BY).select(
            *self.keys(), "mean", "q10", "q50", "q90"
        )

    @staticmethod
    def _curve(curves: dict[str, IsotonicRegression], rows: pl.DataFrame) -> pl.Series:
        """Each row's projected points from its position's curve, in row order."""
        out = [0.0] * rows.height
        for (pos,), g in rows.with_row_index("i").group_by("position"):
            pred = curves[pos].predict(g["ecr_rank"].to_numpy())
            for i, p in zip(g["i"].to_list(), pred, strict=True):
                out[i] = float(p)
        return pl.Series("mean", out)

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        """How ECR compares with PCF's own yardsticks, all at the Saturday run."""
        from pcf.baselines.averages import RollingAverage, SeasonAverage
        from pcf.baselines.lasso import Lasso

        return [RollingAverage, SeasonAverage, Lasso]

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        """Each position's curve at a few ranks."""
        ranks = [1, 6, 12, 24, 36, 48]
        return {
            pos: dict(zip(ranks, iso.predict(ranks).round(2).tolist(), strict=True))
            for pos, iso in model["curves"].items()
        }
