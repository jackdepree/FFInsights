"""The snap-leverage variants: one per target and rung of the ladder (the CEO, 2026-11-14: "1c, 2
yes"; decision 0033).

| Target | Quantity | |
|---|---|---|
| `lev_next3` | leverage share, next 3 games (true participation) | what the expert forecasts |
| `lev_rest` | leverage share over the rest of the regular season | |
| `snap_next3` | official snap share over the next 3 games | the no-noise test (the CEO) |

| Rung | Suffix | Features |
|---|---|---|
| 0 | `plain` | snap share only (`features.PLAIN`): the yardstick |
| 1 | `lev` | plus leverage share (`features.LEV`) |
| 2 | `full` | plus the passing-down role gap and trust over expected (`features.ROLE`) |

Every rung is the same gradient-boosted trees (the exploration's, F6), so a comparison changes
only the features. Ranges: the latest 20% of each training window, refit without it, gives the
misses' q10, q50, q90 by position group; clipped to 0-1. Baselines: each rung against the ones
below. **The no-noise test:** `snap_next3_lev` and `snap_next3_full` against `snap_next3_plain`;
if they fail it, the project becomes an investigation and feature engineering (the CEO).
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import PREDICTION, Expert
from pcf.experts.snap_leverage import features as F

c = pl.col
TREES = {"max_iter": 250, "learning_rate": 0.06, "max_leaf_nodes": 31, "min_samples_leaf": 100,
         "random_state": 0}  # fmt: skip  # the exploration's (F6)
HOLDOUT = 0.2  # the latest share of each training window, for the ranges
BY = ("position",)
TARGETS = {"lev_next3": ("lev", "next3"), "lev_rest": ("lev", "rest"),
           "snap_next3": ("snap", "next3")}  # fmt: skip
QUANTITY = {"lev_next3": "leverage_share_next3", "lev_rest": "leverage_share_rest",
            "snap_next3": "snap_share_next3"}  # fmt: skip
RUNGS = {"plain": F.PLAIN, "lev": [*F.PLAIN, *F.LEV], "full": [*F.PLAIN, *F.LEV, *F.ROLE]}
BELOW = {"plain": (), "lev": ("plain",), "full": ("lev", "plain")}
PUBLISHER = "snap_next3_full"  # carries the published measures for higher layers


class _SnapLeverage(Expert):
    id = "snap-leverage"
    cadence = "in_season"
    grain = "player_game"
    inputs = F.INPUTS
    run = "saturday"
    groups = BY
    first_train = F.FIRST_SEASON
    first_read = F.FIRST_SEASON - 1  # last season's shares
    measure: ClassVar[str]
    horizon: ClassVar[str]
    columns: ClassVar[list[str]]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return F.at_moment(view, games)

    def target(self, view) -> pl.DataFrame:
        return F.targets(view, self.measure, self.horizon)

    def _x(self, rows: pl.DataFrame) -> np.ndarray:
        return rows.select(self.columns).to_numpy().astype(float)

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        x, y, w = self._x(train), train["y"].to_numpy(), train["weight"].to_numpy()
        # a column with no values in this window (last season's leverage share when 2019 is the
        # only training season) can't be binned: it's left out of this fit
        use = ~np.isnan(x).all(axis=0)
        x = x[:, use]
        cut = int(len(y) * (1 - HOLDOUT))  # `walk` sorts the training rows in time order
        early = HistGradientBoostingRegressor(**TREES).fit(x[:cut], y[:cut], sample_weight=w[:cut])
        resid = y[cut:] - early.predict(x[cut:]).clip(0, 1)
        offsets = fit_offsets(
            train[cut:].select(*BY, "weight").with_columns(resid=pl.Series(resid)), BY
        )
        trees = HistGradientBoostingRegressor(**TREES).fit(x, y, sample_weight=w)
        return {"trees": trees, "offsets": offsets, "use": use}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        mean = model["trees"].predict(self._x(rows)[:, model["use"]]).clip(0, 1)
        out = rows.select(*self.keys(), *BY).with_columns(mean=pl.Series(mean))
        return with_ranges(out, model["offsets"], BY).select(
            *self.keys(), *[c(p).clip(0.0, 1.0) for p in PREDICTION]
        )

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        used = [col for col, u in zip(self.columns, model["use"], strict=True) if u]
        return {"features": used, "offsets": model["offsets"].to_dicts()}


def _make(target: str, rung: str, below: list[type[Expert]]) -> type[Expert]:
    measure, horizon = TARGETS[target]
    variant = f"{target}_{rung}"
    attrs: dict[str, Any] = {
        "__module__": __name__,
        "__doc__": f"{QUANTITY[target]} from the {rung} features.",
        "measure": measure,
        "horizon": horizon,
        "columns": RUNGS[rung],
        "variant": variant,
        "quantity": QUANTITY[target],
        "baselines": classmethod(lambda cls, b=tuple(below): list(b)),
    }
    if variant == PUBLISHER:
        attrs["publishes"] = F.PUBLISHED
    name = "".join(p.title() for p in variant.split("_"))
    return type(name, (_SnapLeverage,), attrs)


VARIANTS: dict[str, type[Expert]] = {}
for _t in TARGETS:
    _made: dict[str, type[Expert]] = {}
    for _r in RUNGS:
        _made[_r] = _make(_t, _r, [_made[b] for b in BELOW[_r]])
        VARIANTS[_made[_r].variant] = _made[_r]
        globals()[_made[_r].__name__] = _made[_r]
