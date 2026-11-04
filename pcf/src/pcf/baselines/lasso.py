"""The lasso: fantasy points from box-score history only (D6). No ECR and no market lines.

Features are a player's averages over the last 4 games and this season so far (points, targets,
receptions, carries, yards, attempts, touchdowns), last season's points, games played and
position. The penalty is chosen inside each training window: fit on its earlier 80%, scored on
its latest 20%, then refit on all of it. Weights are the recency weights. Ranges come from each
position's training residuals (D7).
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl
from sklearn.linear_model import lasso_path

from pcf.baselines.common import (
    POSITIONS,
    fit_offsets,
    known_games,
    predicted_rows,
    target_points,
    with_ranges,
)
from pcf.core.contract import Expert

c = pl.col
STATS = [
    "targets",
    "receptions",
    "carries",
    "receiving_yards",
    "rushing_yards",
    "passing_yards",
    "attempts",
]
TDS = ["passing_tds", "rushing_tds", "receiving_tds"]
WINDOWS = ("l4", "szn")
AVERAGED = ["points", *STATS, "tds"]
FEATURES = [
    *[f"{w}_{s}" for w in WINDOWS for s in AVERAGED],
    "last_season",
    "no_last_season",
    "games",
    *[f"is_{p}" for p in POSITIONS[1:]],  # QB is the base
]
# Penalties on standardized features; below 1e-3 the lasso is ordinary least squares here.
ALPHAS = np.geomspace(1.0, 1e-3, 16)
MAX_ITER = 5000
HOLDOUT = 0.2  # the latest share of each training window, for choosing the penalty
BY = ("position",)


class Lasso(Expert):
    id = "baselines"
    variant = "lasso"
    cadence = "in_season"
    grain = "player_game"
    inputs = {"player_game": ("stats",)}
    quantity = "ppr_points"
    kind = "amount"
    run = "tuesday"
    groups = ("position",)
    scoring: ClassVar[str] = "ppr"

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        season = int(games["season"].max())
        pg = view.table("player_game", seasons=[season - 1, season])
        known = known_games(pg, self.scoring, [*STATS, *TDS]).with_columns(
            tds=pl.sum_horizontal(TDS)
        )
        this = c("season") == season
        avgs = known.group_by("gsis_id").agg(
            *[c(s).fill_null(0).tail(4).mean().alias(f"l4_{s}") for s in AVERAGED],
            *[c(s).fill_null(0).filter(this).mean().alias(f"szn_{s}") for s in AVERAGED],
            last_season=c("points").filter(~this).mean(),
            games=c("points").len().cast(pl.Float64),
        )
        return (
            predicted_rows(pg, games, self.keys())
            .join(avgs, on="gsis_id", how="inner")
            .with_columns(
                *[c(f"szn_{s}").fill_null(c(f"l4_{s}")) for s in AVERAGED],
                no_last_season=c("last_season").is_null().cast(pl.Float64),
                last_season=c("last_season").fill_null(c("l4_points")),
                **{f"is_{p}": (c("position") == p).cast(pl.Float64) for p in POSITIONS[1:]},
            )
        )

    def target(self, view) -> pl.DataFrame:
        return target_points(view.table("player_game"), self.scoring, self.keys())

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        x = train.select(FEATURES).to_numpy().astype(float)
        y = train["y"].to_numpy().astype(float)
        w = train["weight"].to_numpy().astype(float)
        cut = int(len(y) * (1 - HOLDOUT))  # train is in time order (`walk` sorts it)
        early = fit_lasso(x[:cut], y[:cut], w[:cut], ALPHAS)
        errors = [weighted_mse(predict_lasso(m, x[cut:]), y[cut:], w[cut:]) for m in early]
        alpha = float(ALPHAS[int(np.argmin(errors))])
        (model,) = fit_lasso(x, y, w, [alpha])
        resid = train.select(*BY, "weight").with_columns(resid=pl.Series(y - predict_lasso(model, x)))
        return model | {"alpha": alpha, "offsets": fit_offsets(resid, BY)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        mean = predict_lasso(model, rows.select(FEATURES).to_numpy().astype(float))
        out = rows.select(*self.keys(), *BY).with_columns(mean=pl.Series(mean))
        return with_ranges(out, model["offsets"], BY).select(
            *self.keys(), "mean", "q10", "q50", "q90"
        )

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        from pcf.baselines.averages import RollingAverage, SeasonAverage

        return [RollingAverage, SeasonAverage]

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        """Coefficients per standard deviation of each feature (zero: dropped by the lasso)."""
        coef = dict(zip(FEATURES, np.round(model["coef"], 4).tolist(), strict=True))
        return {"alpha": model["alpha"], "kept": int(np.sum(model["coef"] != 0)), **coef}


def fit_lasso(x: np.ndarray, y: np.ndarray, w: np.ndarray, alphas) -> list[dict[str, Any]]:
    """Weighted lasso fits on standardized features, one per alpha: centre and scale with the
    weights, then scale each row by √weight so the squared loss is weighted."""
    w = w / w.sum()
    mu = w @ x
    sd = np.sqrt(w @ (x - mu) ** 2)
    sd[sd == 0] = 1.0
    y_mu = float(w @ y)
    root = np.sqrt(w * len(w))[:, None]
    z = (x - mu) / sd * root
    _, coefs, _ = lasso_path(z, (y - y_mu) * root[:, 0], alphas=list(alphas), max_iter=MAX_ITER)
    return [{"mu": mu, "sd": sd, "y_mu": y_mu, "coef": coefs[:, i]} for i in range(len(alphas))]


def predict_lasso(model: dict[str, Any], x: np.ndarray) -> np.ndarray:
    return model["y_mu"] + ((x - model["mu"]) / model["sd"]) @ model["coef"]


def weighted_mse(pred: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    return float(np.sum(w * (pred - y) ** 2) / np.sum(w))
