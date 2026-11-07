"""Is a measure consistent? The second of the two tests every new measure gets (CLAUDE.md, "Two
tests for every new measure"; the register is `projects/CONSISTENCY.md`).

A measure is something we compute per team (or player) per game: a feature, a condition, a way
of summing up what happened. It's consistent when it's partly about *who* the team is: it repeats
within a season and from one season to the next, and teams differ on it. It's noise when it
doesn't, whatever its effect on a single game.

- **Week to week:** each unit-season's mean in odd weeks against its mean in even weeks,
  correlated across unit-seasons (split-half). Teams that don't differ, or a measure that's luck,
  give about 0.
- **Season to season:** each unit's mean in one season against the next season's.
- **Interval:** 90%, from Fisher's z, for both.
- **Verdict:** `noise` when the week-to-week interval reaches 0. `state` when it repeats within a
  season but the season-to-season interval reaches 0: something a team is in for a while (an
  injured quarterback), not something it is. `trait` when it repeats within and across seasons.
  The size of r says how much.

Nothing football-specific: the caller picks the units, the games (usually the regular season)
and the sign (a team's value net of its opponent's, for instance).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import polars as pl

c = pl.col
Z90 = 1.6449


def _r(x: np.ndarray, y: np.ndarray) -> float:
    ok = ~(np.isnan(x) | np.isnan(y))
    if ok.sum() < 4 or np.std(x[ok]) == 0 or np.std(y[ok]) == 0:
        return float("nan")
    return float(np.corrcoef(x[ok], y[ok])[0, 1])


def _interval(r: float, n: int) -> tuple[float, float]:
    if math.isnan(r) or n < 4:
        return float("nan"), float("nan")
    z = math.atanh(max(min(r, 0.999999), -0.999999))
    half = Z90 / math.sqrt(n - 3)
    return math.tanh(z - half), math.tanh(z + half)


def consistency(
    rows: pl.DataFrame,
    measures: Sequence[str],
    unit: str = "team",
    season: str = "season",
    week: str = "week",
) -> pl.DataFrame:
    """One row per measure: week-to-week r with its 90% interval, season-to-season r, the number
    of unit-seasons behind each, the typical size per game, and the verdict."""
    out = []
    for m in measures:
        x = rows.select(unit, season, week, v=c(m).cast(pl.Float64)).drop_nulls("v")
        halves = x.group_by(unit, season, odd=c(week) % 2 == 1).agg(c("v").mean())
        j = halves.filter(c("odd")).join(
            halves.filter(~c("odd")), on=[unit, season], suffix="_even"
        )
        wr = _r(j["v"].to_numpy(), j["v_even"].to_numpy())
        lo, hi = _interval(wr, j.height)
        seasons = x.group_by(unit, season).agg(c("v").mean())
        nxt = seasons.with_columns(c(season) - 1).rename({"v": "v_next"})
        s = seasons.join(nxt, on=[unit, season])
        sr = _r(s["v"].to_numpy(), s["v_next"].to_numpy())
        slo, shi = _interval(sr, s.height)
        if math.isnan(lo) or lo <= 0:
            verdict = "noise"
        elif math.isnan(slo) or slo <= 0:
            verdict = "state"
        else:
            verdict = "trait"
        out.append(
            {
                "measure": m,
                "week_r": wr,
                "week_lo": lo,
                "week_hi": hi,
                "season_r": sr,
                "season_lo": slo,
                "season_hi": shi,
                "unit_seasons": j.height,
                "season_pairs": s.height,
                "mean_abs": float(x["v"].abs().mean()) if x.height else float("nan"),
                "verdict": verdict,
            }
        )
    return pl.DataFrame(out)
