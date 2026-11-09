"""The anti-trait variants (CEO, 2026-11-09): each team's gain from an option in its next game,
from its use of the option (the anti-trait: low use is avoidance) and its past gains
(`anti_features.py`). Ranges are the prediction plus the training misses' q10, q50, q90.

Per option `<o>`, with the quantity `<o>_gain` (EPA per play with the option less without; for
defenses, EPA prevented):

| Variant | What | Rung |
|---|---|---|
| `<o>_gain_league` | The league's gain | 0 |
| `<o>_gain_season` (offense) / `<o>_gain_last_season` (defense) | The team's own past gain | 0 |
| `<o>_gain_avoid` | The league's gain plus a fitted weight on the team's use (**anti-trait**) | 1 |
| `<o>_gain_blend` | The same plus the team's past gains | 1 |

The anti-trait claim (H15, F17-F18) is that the weight on use is above zero: avoiders gain less.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import Expert
from pcf.experts.schemes_v2 import anti_features as A
from pcf.experts.schemes_v2 import features as F

c = pl.col
# the blend's gaps from the league's gain
OFFENSE_GAPS = ("shrunk", "last_season", "coach")
DEFENSE_GAPS = ("last_season",)
# A defense's features need a finished season with the option charted (blitzes 2016 on, coverage
# 2018 on), and its outcomes are known only after the season: the first season with rows to fit.
FIRST_TRAIN = {"blitz": 2017, "man": 2019, "two_high": 2019}


class _Gain(Expert):
    id = "schemes-v2"
    cadence = "in_season"
    grain = "team_game"
    run = "saturday"
    inputs = A.OFFENSE_INPUTS  # a defense's variants read `A.DEFENSE_INPUTS`
    option: ClassVar[str]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return A.at_moment(view, games, self.option)

    def features_history(self, view, moments: pl.DataFrame) -> pl.DataFrame:
        return A.history(view, moments, self.option)

    def target(self, view) -> pl.DataFrame:
        o = self.option
        known = "tendencies_known_at" if o in A.OFFENSE else "charted_known_at"
        tg = view.table("team_game").filter(c(f"{o}_gain").is_not_null() & (c(f"{o}_gain_n") > 0))
        return tg.select(*F.KEYS, y=c(f"{o}_gain").cast(pl.Float64), known_at=known)


class _Average(_Gain):
    """Rung 0: one average as the prediction."""

    part: ClassVar[str]

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        resid = train.select("weight", resid=c("y") - c(f"{self.option}_gain_{self.part}"))
        return {"offsets": fit_offsets(resid)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.select(*F.KEYS, mean=c(f"{self.option}_gain_{self.part}"))
        return with_ranges(out, model["offsets"])

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return {"offsets": model["offsets"].to_dicts()}


class _Fitted(_Gain):
    """Rung 1: weighted least squares on the league's gain, the team's use and (`gaps`) the team's
    past gains less the league's."""

    gaps: ClassVar[tuple[str, ...]]

    def _names(self) -> tuple[str, ...]:
        return ("league", "use", *self.gaps)

    def _design(self, rows: pl.DataFrame) -> np.ndarray:
        o = self.option
        league = c(f"{o}_gain_league")
        gaps = [(c(f"{o}_gain_{p}") - league).alias(p) for p in self.gaps]
        cols = rows.select(league.alias("league"), c(f"{o}_use").alias("use"), *gaps)
        return cols.to_numpy().astype(float)

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        x, y, w = self._design(train), train["y"].to_numpy(), train["weight"].to_numpy()
        sw = np.sqrt(w)
        beta = np.linalg.lstsq(x * sw[:, None], y * sw, rcond=None)[0]
        resid = train.select("weight").with_columns(resid=pl.Series(y - x @ beta))
        return {"beta": beta, "offsets": fit_offsets(resid)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.select(F.KEYS).with_columns(mean=pl.Series(self._design(rows) @ model["beta"]))
        return with_ranges(out, model["offsets"])

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return {
            "coefficients": dict(zip(self._names(), map(float, model["beta"]), strict=True)),
            "offsets": model["offsets"].to_dicts(),
        }


def _yardsticks(models: list[type[Expert]]) -> classmethod:
    return classmethod(lambda cls: list(models))


def _variants(option: str) -> list[type[Expert]]:
    """An option's four variants. The own-history average and the anti-trait are judged against
    the league's gain; the blend against all three."""
    offense = option in A.OFFENSE
    own = "season" if offense else "last_season"
    name = option.title().replace("_", "")
    common = {
        "option": option,
        "quantity": f"{option}_gain",
        "inputs": A.OFFENSE_INPUTS if offense else A.DEFENSE_INPUTS,
        "first_train": FIRST_TRAIN.get(option),
        "__module__": __name__,
    }
    league = type(
        f"{name}GainLeague",
        (_Average,),
        {**common, "part": "league", "variant": f"{option}_gain_league"},
    )
    past = type(
        f"{name}Gain{own.title().replace('_', '')}",
        (_Average,),
        {
            **common,
            "part": own,
            "variant": f"{option}_gain_{own}",
            "baselines": _yardsticks([league]),
        },
    )
    avoid = type(
        f"{name}GainAvoid",
        (_Fitted,),
        {
            **common,
            "gaps": (),
            "variant": f"{option}_gain_avoid",
            "baselines": _yardsticks([league]),
        },
    )
    blend = type(
        f"{name}GainBlend",
        (_Fitted,),
        {
            **common,
            "gaps": OFFENSE_GAPS if offense else DEFENSE_GAPS,
            "variant": f"{option}_gain_blend",
            "baselines": _yardsticks([league, past, avoid]),
        },
    )
    return [league, past, avoid, blend]


OPTIONS = (*A.OFFENSE, *A.DEFENSE)
VARIANTS: dict[str, type[Expert]] = {}
for _option in OPTIONS:
    for _cls in _variants(_option):
        VARIANTS[_cls.variant] = _cls
        globals()[_cls.__name__] = _cls  # `pcf.core.contract.find` looks in the module
