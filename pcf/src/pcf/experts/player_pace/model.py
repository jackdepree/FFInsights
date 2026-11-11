"""The `player-pace` variants: each team's next-game habits and volume with its expected players
(features: `pcf.experts.player_pace.features`). Ranges are the prediction plus the training
misses' q10, q50, q90.

Habits (`proe`, `pace_oe`), each a weighted least squares on gaps from the league's level:
- `<h>_team`: the team's own history only (league, shrunk season, last 4, last season, the head
  coach's): the like-for-like yardstick. Team pace's `<h>_shrunk` is the other.
- `<h>_qb`: the same plus the expected starting QB (his own history's gap, the part of it the
  team's habits don't carry, a change of starter, a rookie).
- `proe_lineup`: `proe_qb` plus the pass lean of the skill players ruled out (`lineup_out`).

Volume (`plays`, `dropbacks`, `runs`): `<v>_qb` is team pace's `<v>_full` plus the expected QB's
columns; `<v>_full` is its yardstick.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.experts.pace import model as PM
from pcf.experts.player_pace import features as F

c = pl.col
HISTORY = PM.HISTORY  # shrunk, last4, last_season, coach
QB = {
    "proe": ("qb_proe_gap", "qb_proe_other", "qb_change", "qb_rookie"),
    "pace_oe": ("qb_pace_gap", "qb_pace_other", "qb_change", "qb_rookie"),
}
VOLUME_QB = (
    "qb_proe_gap", "qb_proe_other", "qb_pace_gap", "qb_pace_other", "qb_change", "qb_rookie",
)  # fmt: skip


class _PlayerPace(PM._Pace):
    id = "player-pace"
    inputs = F.INPUTS
    first_train = 2010  # injury reports from 2009; the QB's history needs earlier seasons
    publishes = ("qb_proe_gap", "qb_pace_gap", "qb_share", "qb_change", "qb_rookie", "lineup_out")

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return F.at_moment(view, games, self.kind_of)

    def features_history(self, view, moments: pl.DataFrame) -> pl.DataFrame:
        return F.history(view, moments, self.kind_of)


class _HabitLinear(_PlayerPace):
    """A weighted least squares on the habit's gaps from the league's level, plus `extra`."""

    kind_of = "habit"
    extra: ClassVar[tuple[str, ...]] = ()

    def _columns(self) -> list[tuple[str, pl.Expr]]:
        h = self.trait
        league = c(f"{h}_league")
        cols = [("intercept", pl.lit(1.0)), ("league", league)]
        cols += [(p, (c(f"{h}_{p}") - league).fill_null(0.0)) for p in HISTORY]
        cols += [(x, c(x).fill_null(0.0)) for x in self.extra]
        return cols

    def _design(self, rows: pl.DataFrame) -> np.ndarray:
        return rows.select(e.alias(n) for n, e in self._columns()).to_numpy().astype(float)

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
        names = [n for n, _ in self._columns()]
        return {
            "coefficients": dict(zip(names, map(float, model["beta"]), strict=True)),
            "offsets": model["offsets"].to_dicts(),
        }


class _VolumeQB(_PlayerPace, PM._VolumeModel):
    """Team pace's full volume model plus the expected QB's columns."""

    kind_of = "volume"
    habits = "full"

    def _columns(self) -> list[tuple[str, pl.Expr]]:
        return [*super()._columns(), *((x, c(x).fill_null(0.0)) for x in VOLUME_QB)]


def _make(name: str, base: type, attrs: dict[str, Any]) -> type:
    return type(name, (base,), {"__module__": __name__, **attrs})


def _yardsticks(models: list[type]) -> classmethod:
    return classmethod(lambda cls: list(models))


def _variants() -> list[type]:
    made: list[type] = []
    for h, title in (("proe", "Proe"), ("pace_oe", "PaceOe")):
        common = {"trait": h, "quantity": h}
        team = _make(f"{title}Team", _HabitLinear, {**common, "variant": f"{h}_team"})
        qb = _make(
            f"{title}Qb",
            _HabitLinear,
            {
                **common,
                "variant": f"{h}_qb",
                "extra": QB[h],
                "baselines": _yardsticks([team, PM.VARIANTS[f"{h}_shrunk"]]),
            },
        )
        made += [team, qb]
        if h == "proe":
            made.append(
                _make(
                    "ProeLineup",
                    _HabitLinear,
                    {
                        **common,
                        "variant": "proe_lineup",
                        "extra": (*QB[h], "lineup_out"),
                        "baselines": _yardsticks([qb]),
                    },
                )
            )
    for v in ("plays", "dropbacks", "runs"):
        made.append(
            _make(
                f"{v.title()}Qb",
                _VolumeQB,
                {
                    "trait": v,
                    "quantity": v,
                    "variant": f"{v}_qb",
                    "baselines": _yardsticks([PM.VARIANTS[f"{v}_full"]]),
                },
            )
        )
    return made


VARIANTS: dict[str, type] = {}
for _cls in _variants():
    VARIANTS[_cls.variant] = _cls
    globals()[_cls.__name__] = _cls
del _cls
