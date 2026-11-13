"""The team-efficiency variants: one per side (offense, defense), horizon (next 3 games, rest of
season) and rung of the ladder (brief, "What this changes in the brief"; decision 0032).

| Rung | Variant suffix | The rating it forecasts from |
|---|---|---|
| 0 | `league` | none: the league's level (the training rows' mean) |
| - | `usual` | the usual way: ridge on plays inside the garbage-time rule (F1's yardstick) |
| 1 | `ridge` | ridge on every play, counted equally (the bar every hunch had to beat) |
| 2 | `dml` | DML with the game state: the situation propensity (H42, F7) |
| 3 | `combo` | DML on plays counted by the gap-aware representativeness weights (H41, H44; F8) |

Each forecast is y = a + b1 x own rating + b2 x the opponents' mean rating + b3 x home share,
weighted least squares in each training window (the exploration's map, refit walk-forward).
Ranges are the prediction plus the training misses' q10, q50, q90, per number of games in the
window (`left_<horizon>`, also where range coverage is judged). Baselines: each rung against the
one below it and the league; `usual` against the league.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import Expert
from pcf.experts.team_efficiency import features as F

c = pl.col
LADDER = ("league", "usual", "ridge", "dml", "combo")
BELOW = {"usual": ("league",), "ridge": ("usual", "league"), "dml": ("ridge", "league"),
         "combo": ("dml", "ridge", "league")}  # fmt: skip
# The champion (the CEO, 2026-11-13: every play, counted equally), which carries the published
# ratings for higher layers
PUBLISHER = ("off", "next3", "ridge")


class _Efficiency(Expert):
    id = "team-efficiency"
    cadence = "in_season"
    grain = "team_game"
    inputs = F.INPUTS
    run = "saturday"
    groups: ClassVar[tuple[str, ...]]  # the window's size, `left_<horizon>`
    side: ClassVar[str]
    horizon: ClassVar[str]
    rung: ClassVar[str]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return F.at_moment(view, games)

    def features_history(self, view, moments: pl.DataFrame) -> pl.DataFrame:
        return F.history(view, moments)

    def target(self, view) -> pl.DataFrame:
        return F.targets(view.table("team_game"), self.side, self.horizon)

    def _x(self, rows: pl.DataFrame) -> np.ndarray:
        h, s, r = self.horizon, self.side, self.rung
        one = np.ones((rows.height, 1))
        if r == "league":
            return one
        cols = [f"{s}_{r}", f"opp_{h}_{s}_{r}", f"home_{h}"]
        return np.column_stack([one, rows.select(cols).to_numpy().astype(float)])

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        x, y, w = self._x(train), train["y"].to_numpy(), train["weight"].to_numpy()
        sw = np.sqrt(w)
        beta = np.linalg.lstsq(x * sw[:, None], y * sw, rcond=None)[0]
        by = list(self.groups)
        resid = train.select(*by, "weight").with_columns(resid=pl.Series(y - x @ beta))
        return {"beta": beta, "offsets": fit_offsets(resid, by)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        by = list(self.groups)
        out = rows.select(*F.KEYS, *by).with_columns(mean=pl.Series(self._x(rows) @ model["beta"]))
        return with_ranges(out, model["offsets"], by).drop(by)

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        names = ["intercept"] + ([] if self.rung == "league" else ["own", "opp", "home"])
        return {
            "coefficients": dict(zip(names, map(float, model["beta"]), strict=True)),
            "offsets": model["offsets"].to_dicts(),
        }


def _make(side: str, horizon: str, rung: str, below: list[type[Expert]]) -> type[Expert]:
    variant = f"{side}_{horizon}_{rung}"
    attrs: dict[str, Any] = {
        "__module__": __name__,
        "__doc__": f"{side} EPA per play over the {horizon} horizon, from the {rung} rating.",
        "side": side,
        "horizon": horizon,
        "rung": rung,
        "groups": (f"left_{horizon}",),
        "variant": variant,
        "quantity": f"{side}_epa_{horizon}",
        "baselines": classmethod(lambda cls, b=tuple(below): list(b)),
    }
    if (side, horizon, rung) == PUBLISHER:
        attrs["publishes"] = F.PUBLISHED
    name = "".join(p.title() for p in variant.split("_"))
    return type(name, (_Efficiency,), attrs)


VARIANTS: dict[str, type[Expert]] = {}
for _side in F.SIDES:
    for _h in F.HORIZONS:
        _made: dict[str, type[Expert]] = {}
        for _r in LADDER:
            _made[_r] = _make(_side, _h, _r, [_made[b] for b in BELOW.get(_r, ())])
            VARIANTS[_made[_r].variant] = _made[_r]
            globals()[_made[_r].__name__] = _made[_r]
