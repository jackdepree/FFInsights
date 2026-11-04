"""Rungs 1 and 2: two parts, fit per position (brief D3).

1. The chance a player takes an offensive snap.
2. Their share if they do.

The prediction's `mean` is the two multiplied. Its ranges come from the mixture: a spike at 0 with
the first part's remaining chance, and otherwise the second part's prediction plus the residuals
seen at that position and size of prediction. Residuals are measured on the latest 20% of each
training window from a model fit on the earlier 80%, because a tree's in-sample residuals are far
too small; the final parts are then refit on all of it.

The spike is "no offensive snap", not "inactive", because the outcome says only that: 8% of rows
are active with no snap (F1). `Active` reports the chance of being active itself.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, ClassVar

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from pcf.baselines.lasso import ALPHAS, fit_lasso, predict_lasso, weighted_mse
from pcf.core.contract import Expert
from pcf.experts.participation.common import FIRST_SEASON, known_shares, target_share
from pcf.experts.participation.features import BACK, CAREER, EXTRA, FEATURES, INPUTS, features

c = pl.col
HOLDOUT = 0.2  # the latest share of each training window
BINS = np.array([0.1, 0.25, 0.5, 0.75])  # sizes of the share-if-on-field prediction
LEVELS = np.linspace(0.01, 0.99, 99)
MIN_BIN = 30
QUANTILES = {"q10": 0.1, "q50": 0.5, "q90": 0.9}
TREES = {"max_iter": 150, "learning_rate": 0.08, "max_leaf_nodes": 15, "random_state": 0}


def _constant(value: float):
    """A model for a position whose training rows all have one outcome."""

    class Constant:
        def predict(self, x):
            return np.full(len(x), value)

        def predict_proba(self, x):
            return np.column_stack([np.full(len(x), 1 - value), np.full(len(x), value)])

    return Constant()


def fit_logistic(x: np.ndarray, y: np.ndarray, w: np.ndarray):
    if len(np.unique(y)) < 2:
        return _constant(float(y[0]) if len(y) else 0.5)
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    return m.fit(x, y, logisticregression__sample_weight=w)


def _residual_grid(rows: list[tuple[str, np.ndarray, np.ndarray]]) -> dict[str, np.ndarray]:
    """position → residual quantiles per size of prediction (a bin with few rows uses them all)."""
    grid = {}
    for pos, pred, resid in rows:
        if not len(resid):
            grid[pos] = np.zeros((len(BINS) + 1, len(LEVELS)))
            continue
        bins = np.digitize(pred, BINS)
        everyone = np.quantile(resid, LEVELS)
        grid[pos] = np.vstack(
            [
                np.quantile(resid[bins == b], LEVELS) if (bins == b).sum() >= MIN_BIN else everyone
                for b in range(len(BINS) + 1)
            ]
        )
    return grid


def mixture_quantiles(p: np.ndarray, s: np.ndarray, grid: np.ndarray, level: float) -> np.ndarray:
    """The `level` quantile of "0 with chance 1-p, else s + a residual", kept between 0 and 1."""
    p = np.clip(p, 1e-6, 1.0)
    u = (level - (1 - p)) / p  # where the level falls within the on-field part
    out = np.zeros(len(p))
    on_field = u > 0
    bins = np.digitize(s, BINS)
    for b in np.unique(bins[on_field]):
        i = on_field & (bins == b)
        out[i] = s[i] + np.interp(u[i], LEVELS, grid[b])
    return np.clip(out, 0.0, 1.0)


class _TwoPart(Expert):
    """The two parts' shared recipe. A rung says how to fit each part and with which inputs."""

    id = "participation"
    cadence = "in_season"
    grain = "player_game"
    inputs = INPUTS
    kind = "amount"
    run = "saturday"
    groups = ("position", "played_recently")
    first_train = FIRST_SEASON
    columns: ClassVar[list[str]] = FEATURES

    @abstractmethod
    def fit_on_field(self, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> Any: ...

    @abstractmethod
    def fit_share(self, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> Any: ...

    @abstractmethod
    def predict_share(self, part: Any, x: np.ndarray) -> np.ndarray: ...

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return features(view, games, self.keys())

    def target(self, view) -> pl.DataFrame:
        return target_share(view.table("player_game"), self.keys())

    def _parts(self, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[Any, Any]:
        on = y > 0
        return self.fit_on_field(x, on.astype(int), w), self.fit_share(x[on], y[on], w[on])

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        model, residuals = {}, []
        for pos, g in train.partition_by("position", as_dict=True).items():
            x = g.select(self.columns).to_numpy().astype(float)
            y = g["y"].to_numpy().astype(float)
            w = g["weight"].to_numpy().astype(float)
            cut = int(len(y) * (1 - HOLDOUT))  # train is in time order (`walk` sorts it)
            _, early = self._parts(x[:cut], y[:cut], w[:cut])
            late = y[cut:] > 0
            pred = self.predict_share(early, x[cut:][late]).clip(0, 1)
            residuals.append((pos[0], pred, y[cut:][late] - pred))
            model[pos[0]] = self._parts(x, y, w)
        return {"parts": model, "grid": _residual_grid(residuals)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = []
        for pos, g in rows.partition_by("position", as_dict=True).items():
            if pos[0] not in model["parts"]:
                continue
            x = g.select(self.columns).to_numpy().astype(float)
            on_field, share = model["parts"][pos[0]]
            p = on_field.predict_proba(x)[:, 1]
            s = self.predict_share(share, x).clip(0, 1)
            q = {k: mixture_quantiles(p, s, model["grid"][pos[0]], v) for k, v in QUANTILES.items()}
            out.append(g.select(self.keys()).with_columns(
                mean=pl.Series(p * s), **{k: pl.Series(v) for k, v in q.items()},
            ))  # fmt: skip
        return pl.concat(out).with_columns(
            q10=pl.min_horizontal("q10", "q50"), q90=pl.max_horizontal("q90", "q50")
        )


class Lasso(_TwoPart):
    """A logistic model for taking a snap, and a lasso for the share. The penalty is chosen inside
    each training window, on its latest 20%. Box-score stats, career share and the return from an
    absence are offered here; the lasso keeps what earns its place (D5)."""

    variant = "lasso"
    quantity = "snap_share"
    columns = [*FEATURES, *CAREER, *EXTRA, *BACK]

    def fit_on_field(self, x, y, w):
        return fit_logistic(x, y, w)

    def fit_share(self, x, y, w):
        if len(y) < MIN_BIN:
            return {"constant": float(y.mean()) if len(y) else 0.0}
        cut = int(len(y) * (1 - HOLDOUT))
        early = fit_lasso(x[:cut], y[:cut], w[:cut], ALPHAS)
        errors = [weighted_mse(predict_lasso(m, x[cut:]), y[cut:], w[cut:]) for m in early]
        alpha = float(ALPHAS[int(np.argmin(errors))])
        (model,) = fit_lasso(x, y, w, [alpha])
        return model | {"alpha": alpha}

    def predict_share(self, part, x):
        return np.full(len(x), part["constant"]) if "constant" in part else predict_lasso(part, x)

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        from pcf.experts.participation.averages import Last3, LastGame

        return [LastGame, Last3]

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        """Coefficients per standard deviation of each input, per position (zero: dropped)."""
        out = {}
        for pos, (_, share) in model["parts"].items():
            if "coef" in share:
                kept = {k: round(float(v), 4) for k, v in zip(self.columns, share["coef"],
                                                              strict=True) if v != 0}  # fmt: skip
                out[pos] = {"alpha": share["alpha"], "kept": kept}
        return out


class Trees(_TwoPart):
    """Boosted trees for both parts. Box-score stats aren't offered: trees found no use for them
    (F7)."""

    variant = "trees"
    quantity = "snap_share"
    columns = [*FEATURES]

    def fit_on_field(self, x, y, w):
        if len(np.unique(y)) < 2:
            return _constant(float(y[0]) if len(y) else 0.5)
        return HistGradientBoostingClassifier(**TREES).fit(x, y, sample_weight=w)

    def fit_share(self, x, y, w):
        if len(y) < MIN_BIN:
            return _constant(float(y.mean()) if len(y) else 0.0)
        return HistGradientBoostingRegressor(**TREES).fit(x, y, sample_weight=w)

    def predict_share(self, part, x):
        return part.predict(x)

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        from pcf.experts.participation.averages import LastGame

        return [LastGame, Lasso]


class TreesCareer(Trees):
    """The trees with career share too: does it earn its place (D5, F9)?"""

    variant = "trees_career"
    quantity = "snap_share"
    columns = [*FEATURES, *CAREER]


class Active(Expert):
    """The chance a player is on the game-day active list, the first half of "will they play"."""

    id = "participation"
    variant = "active"
    cadence = "in_season"
    grain = "player_game"
    inputs = INPUTS
    quantity = "p_active"
    kind = "probability"
    run = "saturday"
    groups = ("position", "played_recently")
    first_train = FIRST_SEASON
    columns: ClassVar[list[str]] = FEATURES

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return features(view, games, self.keys())

    def target(self, view) -> pl.DataFrame:
        known = known_shares(view.table("player_game"))
        return known.select(*self.keys(), y=c("active").cast(pl.Float64), known_at="known_at")

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        model = {}
        for pos, g in train.partition_by("position", as_dict=True).items():
            x = g.select(self.columns).to_numpy().astype(float)
            y = g["y"].to_numpy().astype(int)
            w = g["weight"].to_numpy().astype(float)
            if len(np.unique(y)) < 2:
                model[pos[0]] = _constant(float(y[0]))
            else:
                model[pos[0]] = HistGradientBoostingClassifier(**TREES).fit(x, y, sample_weight=w)
        return model

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = []
        for pos, g in rows.partition_by("position", as_dict=True).items():
            if pos[0] in model:
                x = g.select(self.columns).to_numpy().astype(float)
                out.append(g.select(self.keys()).with_columns(
                    mean=pl.Series(model[pos[0]].predict_proba(x)[:, 1])
                ))  # fmt: skip
        return pl.concat(out).with_columns(pl.lit(None, pl.Float64).alias(q) for q in QUANTILES)
