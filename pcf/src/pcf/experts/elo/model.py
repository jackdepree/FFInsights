"""The Elo expert's variants: the home margin, the total and the home win chance, each from the
same features (`features.py`) and each fit inside the harness's training window.

The walk's settings are fixed (exploration F3, F4). What the harness fits, per training window:
- **margin:** home margin = b1 x rating gap + b2 x home field + b3 x QB-missing difference
  + b4 x same-team-share difference + b5 x seed-locked difference (away - home, final week only;
  I19), weighted least squares, no intercept; ranges from the training misses (q10, q50, q90).
- **total:** total = a + b1 x the offense/defense total + b2 x QBs missing + b3 x share missing.
- **win:** a logistic curve on the margin variant's five features, no intercept (exploration F24:
  a fitted curve rather than a fixed normal one). Ties have no outcome.

Each has a `_simple` twin, the brief's yardstick (rung 1): the same walk with no QB or same-team
adjustment (margin and win: rating gap and home field; total: the offense/defense total). The
full variant must beat it, and both are judged against the closing line.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.baselines.market import MarketMargin, MarketTotal, MarketWin
from pcf.core.contract import Expert
from pcf.experts.elo import features as F
from pcf.experts.elo.ratings import Settings

c = pl.col
MARGIN_X = ("gap", "hfa", "qb_diff", "share_diff", "lock_diff")
TOTAL_X = ("od_total", "qb_sum", "share_missing")
SIMPLE_MARGIN_X = ("gap", "hfa")
SIMPLE_TOTAL_X = ("od_total",)


def _wls(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    sw = np.sqrt(w)
    return np.linalg.lstsq(x * sw[:, None], y * sw, rcond=None)[0]


class _Elo(Expert):
    id = "elo"
    cadence = "in_season"
    grain = "game"
    inputs = {
        "game": ("schedule", "result"),
        "player_game": ("roster", "snaps", "injury"),
    }
    run = "saturday"
    settings: ClassVar[Settings] = Settings()
    x: ClassVar[tuple[str, ...]] = MARGIN_X
    intercept: ClassVar[bool] = False

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return F.at_moment(view, games, self.settings)

    def features_history(self, view, moments: pl.DataFrame) -> pl.DataFrame:
        return F.history(view, moments, self.settings)

    def target(self, view) -> pl.DataFrame:
        g = view.table("game").filter(c("result_known_at").is_not_null())
        return g.select("game_id", y=self._y(), known_at="result_known_at")

    def _y(self) -> pl.Expr:
        return (c("home_score") - c("away_score")).cast(pl.Float64)

    def _design(self, rows: pl.DataFrame) -> np.ndarray:
        x = rows.select(self.x).to_numpy().astype(float)
        return np.column_stack([np.ones(len(x)), x]) if self.intercept else x

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        x, y, w = self._design(train), train["y"].to_numpy(), train["weight"].to_numpy()
        beta = _wls(x, y, w)
        resid = train.select("weight").with_columns(resid=pl.Series(y - x @ beta))
        return {"beta": beta, "offsets": fit_offsets(resid)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.select("game_id").with_columns(
            mean=pl.Series(self._design(rows) @ model["beta"])
        )
        return with_ranges(out, model["offsets"])

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        names = (("intercept",) if self.intercept else ()) + self.x
        return {
            "coefficients": dict(zip(names, map(float, model["beta"]), strict=True)),
            "offsets": model["offsets"].to_dicts(),
        }


class EloMargin(_Elo):
    """The home team's margin: the rating gap, home field and H1's adjustments."""

    variant = "margin"
    quantity = "home_margin"
    publishes = F.PUBLISHED  # the ratings, for higher layers (decision 0021)

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [EloMarginSimple, MarketMargin]


class EloMarginSimple(EloMargin):
    """Rung 1: the rating gap and home field only."""

    variant = "margin_simple"
    x = SIMPLE_MARGIN_X
    publishes = ()

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [MarketMargin]


class EloTotal(_Elo):
    """Total points, from the offense and defense ratings and H1's adjustments."""

    variant = "total"
    quantity = "total_points"
    x = TOTAL_X
    intercept = True

    def _y(self) -> pl.Expr:
        return (c("home_score") + c("away_score")).cast(pl.Float64)

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [EloTotalSimple, MarketTotal]


class EloTotalSimple(EloTotal):
    """The offense/defense total only."""

    variant = "total_simple"
    x = SIMPLE_TOTAL_X

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [MarketTotal]


class EloWin(_Elo):
    """The home team wins: a logistic curve on the margin's features. Ties have no outcome."""

    variant = "win"
    quantity = "home_win"
    kind = "probability"

    def _y(self) -> pl.Expr:
        m = c("home_score") - c("away_score")
        return pl.when(m > 0).then(1.0).when(m < 0).then(0.0)

    def fit(self, train: pl.DataFrame) -> LogisticRegression:
        x, y, w = self._design(train), train["y"].to_numpy(), train["weight"].to_numpy()
        return LogisticRegression(C=1e6, fit_intercept=False, max_iter=1000).fit(
            x, y.astype(int), sample_weight=w
        )

    def predict(self, model: LogisticRegression, rows: pl.DataFrame) -> pl.DataFrame:
        p = model.predict_proba(self._design(rows))[:, 1]
        return rows.select("game_id").with_columns(mean=pl.Series(p))

    def explain(self, model: LogisticRegression) -> dict[str, Any]:
        return {"coefficients": dict(zip(self.x, map(float, model.coef_[0]), strict=True))}

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [EloWinSimple, MarketWin]


class EloWinSimple(EloWin):
    """A logistic curve on the rating gap and home field only."""

    variant = "win_simple"
    x = SIMPLE_MARGIN_X

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [MarketWin]
