"""The pace variants. Ranges are the prediction plus the training misses' q10, q50, q90.

**Habits** (per habit `<h>` in `features.HABITS`): `<h>_league`, `_last4` and `_season` (rung 0
averages) and `<h>_shrunk` (rung 1: schemes-v2's blend of the league's level and the team's gaps
from it, reused).

**Volume** (per `<v>` in plays, dropbacks, runs), each a weighted least squares on gaps from the
league's level:
- `<v>_league`, `<v>_season`, `<v>_last_season`: rung 0 averages (the brief's simple averages).
- `<v>_neutral`: rung 1, the usual way: the team's own volume history, what the opposing defense
  allows, both offenses' and defenses' efficiency and plays per drive (pace#F9), and both teams'
  **neutral** habits (tempo, neutral pass rate over expected). No line: it's known only at
  kickoff (`features`).
- `<v>_full`: the same with the **full-sample** habits (pace over expected, pass rate over
  expected, no-huddle) in place of the neutral ones. It must beat `<v>_neutral` (the brief's test
  of H22) and the averages.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import Expert
from pcf.experts.pace import features as F
from pcf.experts.schemes_v2 import model as S

c = pl.col
AVERAGES = ("league", "last4", "season")
VOLUME_AVERAGES = ("league", "season", "last_season")
HISTORY = ("shrunk", "last4", "last_season", "coach")
# what the opposing defense allows, per volume measure
ALLOWED = {"plays": "def_plays", "dropbacks": "def_dropbacks", "runs": "def_runs"}
EFFICIENCY = ("epa", "ppd")  # with the opponent's defense: def_epa, def_ppd
HABIT_SETS = {"neutral": tuple(F.NEUTRAL), "full": F.FULL_HABITS}


class _Pace(Expert):
    id = "pace"
    cadence = "in_season"
    grain = "team_game"
    inputs = F.INPUTS
    run = "saturday"
    kind_of: ClassVar[str]  # "habit" or "volume"
    trait: ClassVar[str]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        return F.at_moment(view, games, self.kind_of)

    def features_history(self, view, moments: pl.DataFrame) -> pl.DataFrame:
        return F.history(view, moments, self.kind_of)

    def target(self, view) -> pl.DataFrame:
        value, weight = {**F.HABITS, **F.VOLUME}[self.trait]
        tg = view.table("team_game").filter(c(value).is_not_null())
        if weight != "one":
            tg = tg.filter(c(weight) > 0)
        return tg.select(*F.KEYS, y=c(value).cast(pl.Float64), known_at=F.KNOWN)


class _HabitAverage(_Pace, S._Average):
    """Rung 0: one average of a habit as the prediction."""

    kind_of = "habit"


class _HabitBlend(_Pace, S._Blend):
    """Rung 1: schemes-v2's blend, on a habit."""

    kind_of = "habit"


class _VolumeAverage(_Pace, S._Average):
    """Rung 0: one average of the team's volume."""

    kind_of = "volume"


class _VolumeModel(_Pace):
    """Rung 1: weighted least squares on the league's level and gaps from it."""

    kind_of = "volume"
    habits: ClassVar[str]  # "neutral" or "full"

    def _columns(self) -> list[tuple[str, pl.Expr]]:
        v = self.trait
        league = c(f"{v}_league")
        cols = [("intercept", pl.lit(1.0)), ("league", league)]
        cols += [(p, c(f"{v}_{p}") - league) for p in HISTORY]
        a = ALLOWED[v]
        cols.append(("opp_allows", c(f"opp_{a}_shrunk") - c(f"opp_{a}_league")))
        for e in EFFICIENCY:
            cols.append((e, c(f"{e}_shrunk") - c(f"{e}_league")))
            cols.append((f"opp_def_{e}", c(f"opp_def_{e}_shrunk") - c(f"opp_def_{e}_league")))
        for h in HABIT_SETS[self.habits]:
            cols.append((h, c(f"{h}_shrunk") - c(f"{h}_league")))
            cols.append((f"opp_{h}", c(f"opp_{h}_shrunk") - c(f"opp_{h}_league")))
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


def _yardsticks(models: list[type[Expert]]) -> classmethod:
    return classmethod(lambda cls: list(models))


def _make(name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> type[Expert]:
    return type(name, bases, {"__module__": __name__, **attrs})


def _habit_variants(habit: str) -> list[type[Expert]]:
    """A habit's four variants: each average judged against the league's level, the blend
    against all three averages."""
    common = {"trait": habit, "quantity": habit}
    title = habit.title().replace("_", "")
    made = {
        p: _make(
            f"{title}{p.title()}",
            (_HabitAverage,),
            {**common, "part": p, "variant": f"{habit}_{p}"},
        )
        for p in AVERAGES
    }
    for p in AVERAGES[1:]:
        made[p].baselines = _yardsticks([made["league"]])  # type: ignore[attr-defined]
    made["shrunk"] = _make(
        f"{title}Shrunk",
        (_HabitBlend,),
        {
            **common,
            "variant": f"{habit}_shrunk",
            "baselines": _yardsticks([made[p] for p in AVERAGES]),
        },
    )
    return list(made.values())


def _volume_variants(v: str) -> list[type[Expert]]:
    """A volume measure's five variants: the averages against the league's level, the usual way
    against the averages, and the full-sample habits against the usual way and the averages."""
    common = {"trait": v, "quantity": v}
    title = v.title()
    made = {
        p: _make(f"{title}{''.join(w.title() for w in p.split('_'))}", (_VolumeAverage,),
                 {**common, "part": p, "variant": f"{v}_{p}"})
        for p in VOLUME_AVERAGES
    }  # fmt: skip
    for p in VOLUME_AVERAGES[1:]:
        made[p].baselines = _yardsticks([made["league"]])  # type: ignore[attr-defined]
    averages = [made[p] for p in VOLUME_AVERAGES[1:]]
    made["neutral"] = _make(
        f"{title}Neutral",
        (_VolumeModel,),
        {
            **common,
            "habits": "neutral",
            "variant": f"{v}_neutral",
            "baselines": _yardsticks(averages),
        },
    )
    made["full"] = _make(
        f"{title}Full",
        (_VolumeModel,),
        {
            **common,
            "habits": "full",
            "variant": f"{v}_full",
            "baselines": _yardsticks([made["neutral"], *averages]),
        },
    )
    return list(made.values())


VARIANTS: dict[str, type[Expert]] = {}
for _cls in [
    *[k for h in F.HABITS for k in _habit_variants(h)],
    *[k for v in F.VOLUME for k in _volume_variants(v)],
]:
    VARIANTS[_cls.variant] = _cls
    globals()[_cls.__name__] = _cls  # `pcf.core.contract.find` looks in the module
