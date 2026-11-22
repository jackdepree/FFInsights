"""The forecast of opportunity: next game's expected points (decision 0041), as a spike forecast.

Most rostered backs and receivers get no chance in a given game (inactive, or on the field without
the ball), so the forecast has two parts, like participation's (decision 0014):
1. the chance he gets at least one target or carry (`p_nonzero`);
2. his expected points if he does (`if_nonzero_mean`).

`mean` is the two multiplied. The ranges come from the mixture: 0 with the first part's remaining
chance, else the second part plus the misses seen at his position and size of forecast. Those misses
are measured on the latest 20% of each training window from parts fit on the earlier 80% (a fitted
model's own misses are too small); the parts are then refit on all of it. The lasso picks its
penalty on the same split (the baselines' rule).

| Variant | Inputs | Method | Rung |
|---|---|---|---|
| `last4` | His expected points over his last 4 rostered games (absent: 0) | average | 0 |
| `counts` | Playing time (participation's inputs) and past targets, carries, snaps | lasso | 1 |
| `xfp` | `counts` + past expected points | lasso | 1 |
| `eff` | `xfp` + past points over expected (per chance), yards after the catch | lasso | 1 |
| `eff_trees` | `eff`'s inputs | boosted trees | 3 |
| `eff_rec_yards`, `eff_rush_yards` | `eff` + past expected yards (the yardstick) | lasso | 1 |
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.baselines.lasso import ALPHAS, fit_lasso, predict_lasso, weighted_mse
from pcf.core.contract import Expert
from pcf.experts.opportunity_quality import features as F
from pcf.experts.opportunity_quality.common import FIRST_SEASON, KNOWN, known_games
from pcf.experts.participation.twopart import fit_logistic

c = pl.col
HOLDOUT = 0.2  # the latest share of each training window
LEVELS = np.linspace(0.01, 0.99, 99)  # the miss quantiles kept, read by interpolation
SIZE_BINS = (3.0, 6.0, 10.0, 15.0)  # sizes of forecast (expected points if he gets the ball)
MIN_BIN = 200
FLOOR = 0.05  # the smallest forecast if he gets the ball: a chance is never worth nothing
TREES = {"max_iter": 200, "learning_rate": 0.06, "max_leaf_nodes": 15, "min_samples_leaf": 100,
         "l2_regularization": 1.0, "random_state": 0}  # fmt: skip
GROUPS = ("position", "played_recently", "young")
TARGETS = {"xfp": "xfp", "xrec": "xrec", "xrush": "xrush"}


class _Base(Expert):
    """What every opportunity-quality forecast shares: the rows, the inputs and the outcome."""

    id = "opportunity-quality"
    cadence = "in_season"
    grain = "player_game"
    inputs = F.INPUTS
    kind = "amount"
    run = "saturday"
    groups = GROUPS
    first_train = FIRST_SEASON
    scoring: ClassVar[str] = "ppr"
    columns: ClassVar[list[str]] = F.EFF
    outcome: ClassVar[str] = "xfp"  # a column of `known_games`

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return F.features(view, games, self.keys(), self.scoring)

    def target(self, view) -> pl.DataFrame:
        pg = view.table("player_game")
        return known_games(pg, self.scoring).select(
            *self.keys(), y=self.outcome, known_at="known_at"
        )

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [Last4]


class Last4(_Base):
    """Rung 0: his expected points over his last 4 rostered games, an absence counting 0."""

    variant = "last4"
    quantity = "xfp_ppr"
    columns = ["xfp_r4"]

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        resid = train.select("position", "weight", resid=c("y") - c("xfp_r4"))
        return {"offsets": fit_offsets(resid, ("position",))}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.select(*self.keys(), "position", mean="xfp_r4")
        return with_ranges(out, model["offsets"], ("position",)).select(
            *self.keys(), "mean", *[c(q).clip(0.0) for q in ("q10", "q50", "q90")]
        )

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return []


def _fit_amount(x, y, w, method: str) -> dict[str, Any]:
    if method == "trees":
        from sklearn.ensemble import HistGradientBoostingRegressor

        return {"trees": HistGradientBoostingRegressor(**TREES).fit(x, y, sample_weight=w)}
    cut = int(len(y) * (1 - HOLDOUT))
    early = fit_lasso(x[:cut], y[:cut], w[:cut], ALPHAS)
    errors = [weighted_mse(predict_lasso(m, x[cut:]), y[cut:], w[cut:]) for m in early]
    alpha = float(ALPHAS[int(np.argmin(errors))])
    (model,) = fit_lasso(x, y, w, [alpha])
    return model | {"alpha": alpha}


def _predict_amount(model: dict[str, Any], x: np.ndarray) -> np.ndarray:
    if "trees" in model:
        return model["trees"].predict(x)
    return predict_lasso(model, x)


def _fit_chance(x, y, w, method: str):
    if method == "trees":
        from sklearn.ensemble import HistGradientBoostingClassifier

        if len(np.unique(y)) < 2:
            return fit_logistic(x, y, w)
        return HistGradientBoostingClassifier(**TREES).fit(x, y, sample_weight=w)
    return fit_logistic(x, y, w)


def _miss_grid(pos: np.ndarray, size: np.ndarray, resid: np.ndarray) -> dict[str, np.ndarray]:
    """position → miss quantiles (`LEVELS`) per size of forecast; a thin bin uses the position's
    whole set of misses."""
    grid = {}
    bins = np.digitize(size, SIZE_BINS)
    for p in np.unique(pos):
        on = pos == p
        whole = np.quantile(resid[on], LEVELS)
        grid[str(p)] = np.vstack([
            np.quantile(resid[on & (bins == b)], LEVELS) if (on & (bins == b)).sum() >= MIN_BIN
            else whole
            for b in range(len(SIZE_BINS) + 1)
        ])  # fmt: skip
    grid["_all"] = np.tile(np.quantile(resid, LEVELS), (len(SIZE_BINS) + 1, 1))
    return grid


def _miss_at(grid, pos: np.ndarray, size: np.ndarray, level: np.ndarray) -> np.ndarray:
    """The miss at each row's `level` (0-1) for its position and size of forecast."""
    out = np.zeros(len(size))
    bins = np.digitize(size, SIZE_BINS)
    for p in np.unique(pos):
        g = grid.get(str(p), grid["_all"])
        for b in np.unique(bins[pos == p]):
            i = (pos == p) & (bins == b)
            out[i] = np.interp(level[i], LEVELS, g[b])
    return out


class _TwoPart(_Base):
    """The chance of a chance, and the expected points if he gets one."""

    spike = True
    method: ClassVar[str] = "lasso"

    def _x(self, rows: pl.DataFrame) -> np.ndarray:
        return rows.select(self.columns).to_numpy().astype(float)

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        x, y, w = self._x(train), train["y"].to_numpy().astype(float), train["weight"].to_numpy()
        on = y > 0
        pos = train["position"].to_numpy()
        cut = int(len(y) * (1 - HOLDOUT))  # train is in time order (`walk` sorts it)
        early, late = np.arange(len(y)) < cut, np.arange(len(y)) >= cut
        amount_early = _fit_amount(x[early & on], y[early & on], w[early & on], self.method)
        s_late = np.maximum(_predict_amount(amount_early, x[late & on]), FLOOR)
        grid = _miss_grid(pos[late & on], s_late, y[late & on] - s_late)
        return {
            "chance": _fit_chance(x, on.astype(int), w, self.method),
            "amount": _fit_amount(x[on], y[on], w[on], self.method),
            "grid": grid,
        }

    def parts(self, model: dict[str, Any], rows: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        x = self._x(rows)
        p = np.clip(model["chance"].predict_proba(x)[:, 1], 1e-6, 1 - 1e-6)
        s = np.maximum(_predict_amount(model["amount"], x), FLOOR)
        return p, s

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        p, s = self.parts(model, rows)
        pos = rows["position"].to_numpy()
        grid = model["grid"]
        quant = {}
        for name, level in (("q10", 0.1), ("q50", 0.5), ("q90", 0.9)):
            u = (level - (1 - p)) / p  # where the level falls in the part with the ball
            v = s + _miss_at(grid, pos, s, np.clip(u, LEVELS[0], LEVELS[-1]))
            quant[name] = np.where(u <= 0, 0.0, np.maximum(v, 0.0))
            lvl = np.full(len(s), level)
            quant[f"if_nonzero_{name}"] = np.maximum(s + _miss_at(grid, pos, s, lvl), 0.0)
        out = rows.select(*self.keys()).with_columns(
            mean=pl.Series(p * s), p_nonzero=pl.Series(p), if_nonzero_mean=pl.Series(s),
            **{k: pl.Series(v) for k, v in quant.items()},
        )  # fmt: skip
        return (
            out.with_columns(
                q50=pl.max_horizontal("q10", "q50"),
            )
            .with_columns(
                q90=pl.max_horizontal("q50", "q90"),
                if_nonzero_q50=pl.max_horizontal("if_nonzero_q10", "if_nonzero_q50"),
            )
            .with_columns(if_nonzero_q90=pl.max_horizontal("if_nonzero_q50", "if_nonzero_q90"))
        )

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        amount = model["amount"]
        if "coef" not in amount:
            return {}
        coef = dict(zip(self.columns, np.round(amount["coef"], 4).tolist(), strict=True))
        return {"alpha": amount["alpha"], "kept": int(np.sum(amount["coef"] != 0)), **coef}


class Counts(_TwoPart):
    variant = "counts"
    quantity = "xfp_ppr"
    columns = F.COUNTS


class Xfp(_TwoPart):
    variant = "xfp"
    quantity = "xfp_ppr"
    columns = F.XFP


class Eff(_TwoPart):
    """The shipped candidate: expected points with efficiency in them (H61)."""

    variant = "eff"
    quantity = "xfp_ppr"
    columns = F.EFF

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [Last4, Counts, Xfp]


class EffTrees(_TwoPart):
    variant = "eff_trees"
    quantity = "xfp_ppr"
    columns = F.EFF
    method = "trees"

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [Eff]


class EffRecYards(_TwoPart):
    """Next game's expected receiving yards (the yards-only yardstick's input)."""

    variant = "eff_rec_yards"
    quantity = "xrec_yards"
    columns = F.YARDS
    outcome = "xrec"


class EffRushYards(_TwoPart):
    """Next game's expected rushing yards."""

    variant = "eff_rush_yards"
    quantity = "xrush_yards"
    columns = F.YARDS
    outcome = "xrush"


VARIANTS = {cls.variant: cls for cls in (Last4, Counts, Xfp, Eff, EffTrees, EffRecYards,
                                         EffRushYards)}  # fmt: skip
__all__ = ["KNOWN", "VARIANTS"]
