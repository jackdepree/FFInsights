"""One model per outcome and rung: the base rate, a linear model and boosted trees, on a field set
(`plays.FIELD_SETS`). Chances for yes-or-no outcomes; for amounts a mean and a range (q10, q50,
q90). Decision 0036.

- **base:** the training rows' (weighted) rate, or mean and quantiles.
- **linear:** logistic or ridge regression; splines for the clock, distance, field position and
  score, one column per value for downs, counts and flags (missing is its own value), traits
  scaled. Ranges: the mean plus the training residuals' quantiles.
- **trees:** histogram gradient boosting with the exploration's settings (EXPLORATION, first_look);
  ranges from three quantile-loss fits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler

from pcf.experts.context_live import plays
from pcf.experts.context_live.outcomes import Outcome

METHODS = ("base", "linear", "trees")
LEVELS = {"q10": 0.1, "q50": 0.5, "q90": 0.9}
# The exploration's trees (first_look.py), kept so the build's numbers read against it.
TREES = dict(
    max_iter=150,
    learning_rate=0.06,
    max_leaf_nodes=15,
    min_samples_leaf=80,
    l2_regularization=1.0,
    early_stopping=False,
)
SPLINE = ["ydstogo", "yardline_100", "half_seconds_remaining", "game_seconds_remaining",
          "score_differential"]  # fmt: skip
# Fixed codes, so every fit reads a category the same way; anything else is missing.
CATEGORIES = {"qb_location": ["U", "S", "P"], "starting_hash": ["L", "M", "R"]}


def matrix(rows: pl.DataFrame, fields: list[str]) -> np.ndarray:
    """The fields as floats; a category is its index in `CATEGORIES` (missing: NaN)."""
    cols = []
    for f in fields:
        if f in CATEGORIES:
            idx = {v: float(i) for i, v in enumerate(CATEGORIES[f])}
            cols.append(rows[f].replace_strict(idx, default=None, return_dtype=pl.Float64))
        else:
            cols.append(rows[f].cast(pl.Float64))
    return pl.DataFrame(cols).to_numpy().astype(float) if cols else np.empty((rows.height, 0))


def weighted_quantile(y: np.ndarray, w: np.ndarray, q: float) -> float:
    order = np.argsort(y)
    cw = np.cumsum(w[order])
    return float(y[order][np.searchsorted(cw, q * cw[-1])])


def _linear_design(fields: list[str]) -> ColumnTransformer:
    spline = [i for i, f in enumerate(fields) if f in SPLINE]
    scaled = [i for i, f in enumerate(fields) if f in plays.TRAITS]
    onehot = [i for i in range(len(fields)) if i not in spline and i not in scaled]
    parts = []
    if spline:
        parts.append(
            (
                "spline",
                make_pipeline(
                    SimpleImputer(strategy="median"), SplineTransformer(n_knots=6, degree=3)
                ),
                spline,
            )  # fmt: skip
        )
    if onehot:
        parts.append(
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="infrequent_if_exist", min_frequency=30, sparse_output=False
                ),
                onehot,
            )  # fmt: skip
        )
    if scaled:
        parts.append(
            (
                "scaled",
                make_pipeline(
                    SimpleImputer(strategy="median", add_indicator=True), StandardScaler()
                ),
                scaled,
            )  # fmt: skip
        )
    return ColumnTransformer(parts)


@dataclass
class Fitted:
    """One outcome's fitted rung. `predict` gives mean (and q10, q50, q90 for amounts)."""

    outcome: str
    kind: str
    method: str
    fields: list[str]
    parts: dict[str, Any] = field(default_factory=dict)

    def predict(self, rows: pl.DataFrame) -> pl.DataFrame:
        n = rows.height
        if self.method == "base":
            out = {k: np.full(n, v) for k, v in self.parts.items()}
        else:
            x = matrix(rows, self.fields)
            if self.kind == "probability":
                out = {"mean": self.parts["mean"].predict_proba(x)[:, 1]}
            else:
                mean = self.parts["mean"].predict(x)
                out = {"mean": mean}
                if self.method == "linear":
                    for q in LEVELS:
                        out[q] = mean + self.parts[q]
                else:
                    for q in LEVELS:
                        out[q] = self.parts[q].predict(x)
        if self.kind == "amount":
            qs = np.sort(np.column_stack([out[q] for q in LEVELS]), axis=1)
            out.update({q: qs[:, i] for i, q in enumerate(LEVELS)})
        else:
            out["mean"] = np.clip(out["mean"], 1e-6, 1 - 1e-6)
        return pl.DataFrame({k: np.asarray(v, dtype=float) for k, v in out.items()})


def fit(
    train: pl.DataFrame, outcome: Outcome, fields: list[str], method: str, seed: int = 0
) -> Fitted:
    """Fit one rung on training rows with `y` and `weight`."""
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    y = train["y"].to_numpy().astype(float)
    w = train["weight"].to_numpy().astype(float) if "weight" in train.columns else np.ones(len(y))
    kind = outcome.kind
    out = Fitted(outcome.name, kind, method, list(fields))
    if method == "base":
        out.parts["mean"] = float(np.average(y, weights=w))
        if kind == "amount":
            for q, level in LEVELS.items():
                out.parts[q] = weighted_quantile(y, w, level)
        return out
    x = matrix(train, fields)
    # A column with no values in the window (traits before their first season) is left out.
    keep = [f for i, f in enumerate(fields) if not np.isnan(x[:, i]).all()]
    if len(keep) < len(fields):
        out.fields = keep
        x = matrix(train, keep)
    if method == "linear":
        est: Pipeline
        if kind == "probability":
            est = make_pipeline(
                _linear_design(out.fields), LogisticRegression(C=1.0, max_iter=2000)
            )
        else:
            est = make_pipeline(_linear_design(out.fields), Ridge(alpha=1.0))
        est.fit(x, y, **{est.steps[-1][0] + "__sample_weight": w})
        out.parts["mean"] = est
        if kind == "amount":
            resid = y - est.predict(x)
            for q, level in LEVELS.items():
                out.parts[q] = weighted_quantile(resid, w, level)
        return out
    cats = np.array([f in CATEGORIES for f in out.fields], dtype=bool)
    settings = dict(TREES, categorical_features=cats if cats.any() else None, random_state=seed)
    if kind == "probability":
        out.parts["mean"] = HistGradientBoostingClassifier(**settings).fit(x, y, sample_weight=w)
    else:
        out.parts["mean"] = HistGradientBoostingRegressor(**settings).fit(x, y, sample_weight=w)
        for q, level in LEVELS.items():
            out.parts[q] = HistGradientBoostingRegressor(
                loss="quantile", quantile=level, **settings
            ).fit(x, y, sample_weight=w)
    return out


def importances(model: Fitted, rows: pl.DataFrame, seed: int = 0, top: int = 8) -> dict[str, float]:
    """Permutation importance of each field for the mean on `rows` (squared error, a probability's
    Brier): how much worse the mean gets when the field is shuffled."""
    if model.method == "base" or rows.is_empty():
        return {}
    rng = np.random.default_rng(seed)
    y = rows["y"].to_numpy().astype(float)
    base = float(np.mean((y - model.predict(rows)["mean"].to_numpy()) ** 2))
    out = {}
    for f in model.fields:
        shuffled = rows.with_columns(pl.Series(f, rows[f].to_numpy()[rng.permutation(rows.height)]))
        err = float(np.mean((y - model.predict(shuffled)["mean"].to_numpy()) ** 2))
        out[f] = err - base
    return dict(sorted(out.items(), key=lambda kv: -kv[1])[:top])


class ContextModel(BaseEstimator):
    """Every outcome's shipped rung in one object, for MLflow (`tracking.log_model`)."""

    def __init__(self, fitted: dict[str, Fitted] | None = None, train_end: str = ""):
        self.fitted = fitted
        self.train_end = train_end

    def predict(self, rows: pl.DataFrame) -> dict[str, pl.DataFrame]:
        return {name: m.predict(rows) for name, m in (self.fitted or {}).items()}
