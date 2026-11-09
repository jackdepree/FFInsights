"""The trait variants: for each trait, three rung-0 averages and the rung-1 blend, all from the
same features (`features.py`). Ranges are the prediction plus the training misses' q10, q50, q90.

The blend (`<trait>_shrunk`) is weighted least squares on the league's level and four gaps from
it: the shrunk season to date, the last 4 games, last season, and the head coach's history.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import Expert
from pcf.experts.schemes_v2 import features as F

c = pl.col
BLEND = ("shrunk", "last4", "last_season", "coach")
AVERAGES = ("league", "last4", "season")


class _Trait(Expert):
    id = "schemes-v2"
    cadence = "in_season"
    grain = "team_game"
    inputs = F.INPUTS
    run = "saturday"
    trait: ClassVar[str]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return F.at_moment(view, games)

    def features_history(self, view, moments: pl.DataFrame) -> pl.DataFrame:
        return F.history(view, moments)

    def target(self, view) -> pl.DataFrame:
        value, plays = F.TRAITS[self.trait]
        tg = view.table("team_game").filter(c(value).is_not_null() & (c(plays) > 0))
        return tg.select(*F.KEYS, y=c(value).cast(pl.Float64), known_at="tendencies_known_at")


class _Average(_Trait):
    """Rung 0: one average as the prediction."""

    part: ClassVar[str]

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        resid = train.select("weight", resid=c("y") - c(f"{self.trait}_{self.part}"))
        return {"offsets": fit_offsets(resid)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.select(*F.KEYS, mean=c(f"{self.trait}_{self.part}"))
        return with_ranges(out, model["offsets"])

    def explain(self, model: dict[str, Any]) -> dict[str, Any]:
        return {"offsets": model["offsets"].to_dicts()}


class _Blend(_Trait):
    """Rung 1: the league's level plus fitted weights on the team's gaps from it."""

    def _design(self, rows: pl.DataFrame) -> np.ndarray:
        league = c(f"{self.trait}_league")
        gaps = [(c(f"{self.trait}_{p}") - league).alias(p) for p in BLEND]
        return rows.select(league.alias("league"), *gaps).to_numpy().astype(float)

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
        names = ("league", *BLEND)
        return {
            "coefficients": dict(zip(names, map(float, model["beta"]), strict=True)),
            "offsets": model["offsets"].to_dicts(),
        }


def _yardsticks(models: list[type[Expert]]) -> classmethod:
    return classmethod(lambda cls: list(models))


def _variants(trait: str) -> list[type[Expert]]:
    """A trait's four variants. Each average is judged against the league's level, and the blend
    against all three averages."""
    quantity = F.TRAITS[trait][0]
    name = trait.title().replace("_", "")
    common = {"trait": trait, "quantity": quantity, "__module__": __name__}
    made: dict[str, type[Expert]] = {}
    for part in AVERAGES:
        made[part] = type(
            f"{name}{part.title()}",
            (_Average,),
            {**common, "part": part, "variant": f"{trait}_{part}"},
        )
    for part in AVERAGES[1:]:
        made[part].baselines = _yardsticks([made["league"]])  # type: ignore[attr-defined]
    made["shrunk"] = type(
        f"{name}Shrunk",
        (_Blend,),
        {
            **common,
            "variant": f"{trait}_shrunk",
            "baselines": _yardsticks([made[p] for p in AVERAGES]),
        },
    )
    return list(made.values())


VARIANTS: dict[str, type[Expert]] = {}
for _trait in F.TRAITS:
    for _cls in _variants(_trait):
        VARIANTS[_cls.variant] = _cls
        globals()[_cls.__name__] = _cls  # `pcf.core.contract.find` looks in the module
