"""The outcomes context-live forecasts: each with its population, its column in the play table,
its kind, the field sets it may use and its first season (BRIEF, "Plan"; decision 0036).

Left out (the CEO's call 2): interceptions, fumbles, scrambles and a dropback's EPA, which nothing
explains (EXPLORATION F3).
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from pcf.experts.context_live.plays import FIRST_PARTICIPATION, FIRST_SEASON

c = pl.col


@dataclass(frozen=True)
class Outcome:
    name: str  # also the output's `quantity`
    label: str  # plain words for reports
    population: str  # run, dropback, attempt or snap (plays.POPULATIONS)
    column: str
    kind: str  # probability or amount
    first_season: int = FIRST_SEASON
    # Penalties: the call fields are charted differently on plays wiped out by a penalty, which
    # "explained" 28% of their error by leakage (EXPLORATION F2), so the situation only.
    situation_only: bool = False

    def rows(self, plays: pl.DataFrame) -> pl.DataFrame:
        """The play table's rows this outcome is scored on, with `y`."""
        member = {
            "run": c("is_run"),
            "dropback": c("is_dropback"),
            "attempt": c("is_attempt"),
            "snap": pl.lit(True),
        }[self.population]
        return (
            plays.filter(member, c("season") >= self.first_season)
            .with_columns(y=c(self.column))
            .filter(c("y").is_not_null())
        )


P, A = "probability", "amount"
OUTCOMES: tuple[Outcome, ...] = (
    Outcome("rush_yards_exp", "rushing yards", "run", "yards", A),
    Outcome("run_stuffed_prob", "run stuffed (0 or fewer)", "run", "stuffed", P),
    Outcome("run_explosive_prob", "explosive run (10+)", "run", "explosive_run", P),
    Outcome("run_success_prob", "successful run", "run", "success_y", P),
    Outcome("run_first_down_prob", "first down on a run", "run", "first_down_y", P),
    Outcome("run_td_prob", "touchdown on a run", "run", "td", P),
    Outcome("pressure_prob", "pressure", "dropback", "pressure_y", P, FIRST_PARTICIPATION),
    Outcome("sack_prob", "sack", "dropback", "sack_y", P),
    Outcome(
        "time_to_throw_exp",
        "time to throw (s)",
        "dropback",
        "time_to_throw_y",
        A,
        FIRST_PARTICIPATION,
    ),  # fmt: skip
    Outcome("dropback_yards_exp", "dropback yards", "dropback", "yards", A),
    Outcome("pass_explosive_prob", "explosive pass (20+)", "dropback", "explosive_pass", P),
    Outcome("dropback_success_prob", "successful dropback", "dropback", "success_y", P),
    Outcome("dropback_first_down_prob", "first down on a dropback", "dropback", "first_down_y", P),
    Outcome("dropback_td_prob", "touchdown on a dropback", "dropback", "td", P),
    Outcome("air_yards_exp", "depth of target (yards)", "attempt", "air_yards_y", A),
    Outcome("completion_prob", "completion", "attempt", "complete_y", P),
    Outcome("penalty_prob", "penalty", "snap", "penalty_y", P, situation_only=True),
)
BY_NAME = {o.name: o for o in OUTCOMES}


def get(name: str) -> Outcome:
    if name not in BY_NAME:
        raise KeyError(f"no outcome {name!r}. Outcomes: {', '.join(BY_NAME)}")
    return BY_NAME[name]
