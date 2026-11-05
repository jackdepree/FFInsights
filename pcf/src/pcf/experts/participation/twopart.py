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

Every variant saves both parts next to the blend (`SPIKE_PARTS`), and the harness judges each. Two
later variants fix what that showed (decision 0014, F23): `TreesStatus` gives players on the injury
report their own residuals, and `TreesSpikes` adds a third part where exactly 100% is common, in
practice QBs: the chance of taking every snap if they play.
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
FULL = 0.999  # a share this high is every snap
MIN_FULL = 0.2  # a third part only where this many of a position's on-field games are every snap
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


def _by_size(pred: np.ndarray, resid: np.ndarray, fallback: np.ndarray) -> np.ndarray:
    """Residual quantiles per size of prediction (a bin with few rows uses the fallback)."""
    bins = np.digitize(pred, BINS)
    return np.vstack(
        [
            np.quantile(resid[bins == b], LEVELS) if (bins == b).sum() >= MIN_BIN else fallback
            for b in range(len(BINS) + 1)
        ]
    )


def _residual_grid(
    rows: list[tuple[str, np.ndarray, np.ndarray, np.ndarray | None]],
) -> dict[str, np.ndarray]:
    """position → residual quantiles per size of prediction, and first per injury-report status
    (not listed, listed) if the rows carry one. Too few listed rows fall back to all listed rows,
    then to everyone in that size."""
    grid = {}
    for pos, pred, resid, listed in rows:
        if not len(resid):
            shape = (len(BINS) + 1, len(LEVELS))
            grid[pos] = np.zeros(shape if listed is None else (2, *shape))
            continue
        everyone = _by_size(pred, resid, np.quantile(resid, LEVELS))
        if listed is None:
            grid[pos] = everyone
            continue
        on = listed.astype(bool)
        whole = np.quantile(resid[on], LEVELS) if on.sum() >= MIN_BIN else None
        bins = np.digitize(pred, BINS)
        report = np.vstack(
            [
                np.quantile(resid[on & (bins == b)], LEVELS)
                if (on & (bins == b)).sum() >= MIN_BIN
                else (whole if whole is not None else everyone[b])
                for b in range(len(BINS) + 1)
            ]
        )
        off = ~on
        plain = (
            _by_size(pred[off], resid[off], np.quantile(resid, LEVELS)) if off.any() else everyone
        )
        grid[pos] = np.stack([plain, report])
    return grid


def mixture_quantiles(
    p: np.ndarray,
    s: np.ndarray,
    grid: np.ndarray,
    level: float,
    full: np.ndarray | None = None,
    listed: np.ndarray | None = None,
) -> np.ndarray:
    """The `level` quantile of "0 with chance 1-p, else every snap with chance `full`, else s + a
    residual", kept between 0 and 1. A grid with a status dimension is read by `listed`."""
    p = np.clip(p, 1e-6, 1.0)
    u = (level - (1 - p)) / p  # where the level falls within the on-field part
    t = np.zeros(len(p)) if full is None else np.clip(full, 0.0, 1 - 1e-6)
    every = (t > 0) & (u >= 1 - t)  # the top of the on-field part is exactly 100%
    v = u / (1 - t)  # where it falls within the rest
    out = np.where(every, 1.0, 0.0)
    on_field = (u > 0) & ~every
    bins = np.digitize(s, BINS)
    status = np.zeros(len(p), dtype=int) if listed is None else listed.astype(int)
    for st in np.unique(status[on_field]):
        rows = grid[st] if grid.ndim == 3 else grid
        for b in np.unique(bins[on_field & (status == st)]):
            i = on_field & (status == st) & (bins == b)
            out[i] = s[i] + np.interp(v[i], LEVELS, rows[b])
    return np.clip(out, 0.0, 1.0)


class _TwoPart(Expert):
    """The two parts' shared recipe. A rung says how to fit each part and with which inputs."""

    id = "participation"
    cadence = "in_season"
    grain = "player_game"
    inputs = INPUTS
    kind = "amount"
    run = "saturday"
    groups = ("position", "played_recently", "report")
    first_train = FIRST_SEASON
    columns: ClassVar[list[str]] = FEATURES
    spike = True
    by_status: ClassVar[bool] = False  # residuals per injury-report status
    full_part: ClassVar[bool] = False  # a third part where exactly 100% is common

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

    def _parts(self, x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[Any, Any, Any]:
        """On the field, every snap if on the field (or None), and the share otherwise."""
        on = y > 0
        on_field = self.fit_on_field(x, on.astype(int), w)
        every = y >= FULL
        if not (self.full_part and on.any() and every[on].mean() >= MIN_FULL):
            return on_field, None, self.fit_share(x[on], y[on], w[on])
        rest = on & ~every
        # Logistic, in every rung: boosted trees were badly overconfident here (slope 0.67)
        full = fit_logistic(x[on], every[on].astype(int), w[on])
        return on_field, full, self.fit_share(x[rest], y[rest], w[rest])

    def _listed(self, x: np.ndarray) -> np.ndarray:
        return (x[:, self.columns.index("report")] >= 1).astype(int)

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        model, residuals = {}, []
        for pos, g in train.partition_by("position", as_dict=True).items():
            x = g.select(self.columns).to_numpy().astype(float)
            y = g["y"].to_numpy().astype(float)
            w = g["weight"].to_numpy().astype(float)
            cut = int(len(y) * (1 - HOLDOUT))  # train is in time order (`walk` sorts it)
            _, full, early = self._parts(x[:cut], y[:cut], w[:cut])
            late = y[cut:] > 0
            if full is not None:
                late &= y[cut:] < FULL
            xl, yl = x[cut:][late], y[cut:][late]
            pred = self.predict_share(early, xl).clip(0, 1)
            listed = self._listed(xl) if self.by_status else None
            residuals.append((pos[0], pred, yl - pred, listed))
            model[pos[0]] = self._parts(x, y, w)
        return {"parts": model, "grid": _residual_grid(residuals)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = []
        for pos, g in rows.partition_by("position", as_dict=True).items():
            if pos[0] not in model["parts"]:
                continue
            x = g.select(self.columns).to_numpy().astype(float)
            on_field, full, share = model["parts"][pos[0]]
            p = on_field.predict_proba(x)[:, 1]
            s = self.predict_share(share, x).clip(0, 1)
            t = None if full is None else full.predict_proba(x)[:, 1]
            listed = self._listed(x) if self.by_status else None
            grid = model["grid"][pos[0]]
            if_on = s if t is None else t + (1 - t) * s
            blend = {k: mixture_quantiles(p, s, grid, v, t, listed) for k, v in QUANTILES.items()}
            given = {
                f"if_nonzero_{k}": mixture_quantiles(np.ones(len(p)), s, grid, v, t, listed)
                for k, v in QUANTILES.items()
            }
            out.append(g.select(self.keys()).with_columns(
                mean=pl.Series(p * if_on), p_nonzero=pl.Series(p), if_nonzero_mean=pl.Series(if_on),
                **{k: pl.Series(v) for k, v in {**blend, **given}.items()},
            ))  # fmt: skip
        return pl.concat(out).with_columns(
            q10=pl.min_horizontal("q10", "q50"),
            q90=pl.max_horizontal("q90", "q50"),
            if_nonzero_q10=pl.min_horizontal("if_nonzero_q10", "if_nonzero_q50"),
            if_nonzero_q90=pl.max_horizontal("if_nonzero_q90", "if_nonzero_q50"),
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
        for pos, (_, _, share) in model["parts"].items():
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


class TreesStatus(Trees):
    """The trees, with separate residuals for players on the injury report: their ranges were too
    narrow (F23). The mean doesn't change."""

    variant = "trees_status"
    quantity = "snap_share"
    by_status = True

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [Trees]


class TreesSpikes(TreesStatus):
    """TreesStatus plus a third part where taking every snap is common, in practice QBs (F23)."""

    variant = "trees_spikes"
    quantity = "snap_share"
    full_part = True


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
