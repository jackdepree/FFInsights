"""The crude forecaster's rungs (crude-forecaster brief, "Baselines"): the season-so-far average,
a lasso, boosted trees (xgboost) and their mix, plus honest ranges.

Every rung is fit the same way: on the training window's earlier 80% first (the lasso picks its
penalty there, as the baselines' lasso does), scored on the latest 20%, then refit on all of it.
The latest 20%'s misses give the ranges: their q10, q50 and q90 in each group and fifth of the
forecast (yards misses grow with the forecast).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import polars as pl
import xgboost as xgb

from pcf.baselines.common import fit_offsets, weighted_quantiles, with_ranges
from pcf.baselines.lasso import ALPHAS, fit_lasso, predict_lasso, weighted_mse

c = pl.col
METHODS = ("season", "lasso", "trees", "mix")
HOLDOUT = 0.2  # the latest share of each training window: the penalty and the ranges
BIN_LEVELS = (0.2, 0.4, 0.6, 0.8)  # fifths of the holdout's forecasts, for the ranges
# The trees: fixed, deliberately plain settings (no tuning: a yardstick changes rarely). Row and
# column subsampling are on, so seeds measure the fitting noise (the brief's step 3).
TREES: dict[str, Any] = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 4,
    "min_child_weight": 50,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "tree_method": "hist",
    "n_jobs": 4,  # leaves room for a parallel build on the same PC
}


def _fit_trees(x: np.ndarray, y: np.ndarray, w: np.ndarray, seed: int) -> xgb.XGBRegressor:
    model = xgb.XGBRegressor(**TREES, random_state=seed)
    model.fit(x, y, sample_weight=w)
    return model


def _fit_core(method: str, x, y, w, seed: int, alpha: float | None) -> dict[str, Any]:
    """One rung fit on these rows (the lasso at a given penalty)."""
    out: dict[str, Any] = {"method": method}
    if method in ("lasso", "mix"):
        (out["lasso"],) = fit_lasso(x, y, w, [alpha])
    if method in ("trees", "mix"):
        out["trees"] = _fit_trees(x, y, w, seed)
    return out


def predict_core(model: dict[str, Any], x: np.ndarray, season_x: np.ndarray) -> np.ndarray:
    """A rung's point forecast. `season_x`: the season-so-far average (rung 0's forecast)."""
    method = model["method"]
    if method == "season":
        return season_x
    parts = []
    if "lasso" in model:
        parts.append(predict_lasso(model["lasso"], x))
    if "trees" in model:
        parts.append(model["trees"].predict(x))
    return np.mean(parts, axis=0)


def pick_alpha(x, y, w, cut: int) -> float:
    """The lasso's penalty: the one with the smallest weighted error on the window's latest 20%
    when fit on the rest (the baselines' lasso's rule)."""
    early = fit_lasso(x[:cut], y[:cut], w[:cut], ALPHAS)
    errors = [weighted_mse(predict_lasso(m, x[cut:]), y[cut:], w[cut:]) for m in early]
    return float(ALPHAS[int(np.argmin(errors))])


def fit(
    method: str,
    train: pl.DataFrame,
    columns: Sequence[str],
    by: Sequence[str],
    seed: int,
    season_column: str,
) -> dict[str, Any]:
    """A rung from training rows in time order (features, `y`, `weight`, the `by` columns and
    `season_column`, the season-so-far average that is rung 0's forecast)."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    x = train.select(columns).to_numpy().astype(float)
    y = train["y"].to_numpy().astype(float)
    w = train["weight"].to_numpy().astype(float)
    sx = train[season_column].to_numpy().astype(float)
    cut = int(len(y) * (1 - HOLDOUT))
    alpha = pick_alpha(x, y, w, cut) if method in ("lasso", "mix") else None
    early = _fit_core(method, x[:cut], y[:cut], w[:cut], seed, alpha)
    held = predict_core(early, x[cut:], sx[cut:])
    edges = weighted_quantiles(held, w[cut:], BIN_LEVELS)
    resid = (
        train[cut:]
        .select(*by, "weight")
        .with_columns(
            resid=pl.Series(y[cut:] - held),
            bin=pl.Series(np.searchsorted(edges, held), dtype=pl.Int32),
        )
    )
    model = _fit_core(method, x, y, w, seed, alpha)
    offsets = fit_offsets(resid, [*by, "bin"])
    return model | {"alpha": alpha, "edges": edges, "offsets": offsets, "season": season_column}


def predict(
    model: dict[str, Any], rows: pl.DataFrame, columns: Sequence[str], by: Sequence[str]
) -> pl.DataFrame:
    """`mean`, `q10`, `q50` and `q90` for the rows (plus the `by` columns)."""
    x = rows.select(columns).to_numpy().astype(float)
    mean = predict_core(model, x, rows[model["season"]].to_numpy().astype(float))
    out = rows.with_columns(
        mean=pl.Series(mean),
        bin=pl.Series(np.searchsorted(model["edges"], mean), dtype=pl.Int32),
    )
    return with_ranges(out, model["offsets"], [*by, "bin"]).drop("bin")


def contributions(model: dict[str, Any], x: np.ndarray, columns: Sequence[str]) -> np.ndarray:
    """Each input's SHAP value for each row (rows × columns), the explanation, never the test
    (the brief). The lasso's are exact (coefficient × distance from the training mean); the
    trees' are xgboost's TreeSHAP; the mix averages them."""
    parts = []
    if "lasso" in model:
        m = model["lasso"]
        parts.append((x - m["mu"]) / m["sd"] * m["coef"])
    if "trees" in model:
        booster = model["trees"].get_booster()
        parts.append(booster.predict(xgb.DMatrix(x), pred_contribs=True)[:, : len(columns)])
    if not parts:
        return np.zeros_like(x)
    return np.mean(parts, axis=0)
