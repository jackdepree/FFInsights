"""The betting market's closing line as a benchmark, at kickoff (D1, D5): the home margin
(spread), the total and the home team's win probability (no-vig moneylines).

nflverse's lines are the close, known at kickoff (validation-harness#F3, odds-collection#F3), so
these run at the `kickoff` moment, which only benchmarks may declare. The gateway hides their
outputs from any model running earlier. Ranges come from training residuals (the market doesn't
publish one); the win probability has no fit at all.
"""

from __future__ import annotations

from typing import Any, ClassVar

import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import Expert
from pcf.data.timeline.moments import KICKOFF

c = pl.col
LINES = ("spread_line", "total_line", "home_moneyline", "away_moneyline")


def implied(moneyline: pl.Expr) -> pl.Expr:
    """American odds → the implied probability, margin included."""
    return (
        pl.when(moneyline < 0)
        .then(-moneyline / (100 - moneyline))
        .otherwise(100 / (100 + moneyline))
    )


def no_vig_home(home: pl.Expr, away: pl.Expr) -> pl.Expr:
    """The home team's win probability with the bookmaker's margin removed proportionally
    (VALIDATION.md §8)."""
    return implied(home) / (implied(home) + implied(away))


class _Market(Expert):
    id = "baselines"
    cadence = "in_season"
    grain = "game"
    inputs = {"game": ("pregame", "result")}
    run = KICKOFF
    benchmark = True
    outcome: ClassVar[str]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        season = int(games["season"].max())
        g = view.table("game", seasons=[season])
        return g.filter(
            c("game_id").is_in(games["game_id"].implode()) & c("pregame_known_at").is_not_null()
        ).select("game_id", *LINES)

    def target(self, view) -> pl.DataFrame:
        g = view.table("game").filter(c("result_known_at").is_not_null())
        return g.select("game_id", y=self._y(), known_at="result_known_at")

    def _y(self) -> pl.Expr:
        return c(self.outcome).cast(pl.Float64)


class _Line(_Market):
    """A line as the median outcome, with ranges from training misses."""

    kind = "amount"
    line: ClassVar[str]

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        resid = train.drop_nulls(self.line).select("weight", resid=c("y") - c(self.line))
        return {"offsets": fit_offsets(resid)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.drop_nulls(self.line).select("game_id", mean=c(self.line).cast(pl.Float64))
        return with_ranges(out, model["offsets"])

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return {"offsets": model["offsets"].to_dicts()}


class MarketMargin(_Line):
    """The home team's margin: nflverse's `spread_line` is how much the home team is favored by."""

    variant = "market_margin"
    quantity = "home_margin"
    outcome = "result"
    line = "spread_line"


class MarketTotal(_Line):
    variant = "market_total"
    quantity = "total_points"
    outcome = "total"
    line = "total_line"


class MarketWin(_Market):
    """The home team wins: the no-vig closing moneyline. Ties have no outcome."""

    variant = "market_win"
    quantity = "home_win"
    kind = "probability"
    outcome = "result"

    def _y(self) -> pl.Expr:
        return pl.when(c("result") > 0).then(1.0).when(c("result") < 0).then(0.0)

    def fit(self, train: pl.DataFrame) -> None:
        return None

    def predict(self, model: None, rows: pl.DataFrame) -> pl.DataFrame:
        both = rows.drop_nulls(["home_moneyline", "away_moneyline"])
        return both.select("game_id", mean=no_vig_home(c("home_moneyline"), c("away_moneyline")))
