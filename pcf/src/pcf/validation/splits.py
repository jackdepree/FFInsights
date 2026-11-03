"""Walk-forward splits: the only splitters in PCF (docs/VALIDATION.md §2, leakage check 7).

One step is a week (in season), a season (retrospective) or an event (offseason events). Each
step has its games, each game its prediction moment (`pcf.data.timeline.moments`), and the step's
model is fit at its earliest moment, on outcomes known by then.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import polars as pl

from pcf.data.timeline import Calendar
from pcf.data.timeline.moments import event_moments, game_moments, season_moments

c = pl.col
GAME_COLUMNS = ["game_id", "season", "week", "kickoff", "moment"]


@dataclass(frozen=True)
class Step:
    index: int
    season: int
    week: int | None
    at: datetime  # when the step's model is fit: its earliest prediction moment
    games: pl.DataFrame  # GAME_COLUMNS: the games it predicts, each with its moment


def steps(
    cal: Calendar,
    cadence: str,
    seasons: Sequence[int],
    run: str = "tuesday",
    event: str | None = None,
) -> list[Step]:
    """The walk-forward steps over `seasons`, in time order."""
    seasons = list(seasons)
    games = cal.games.select("game_id", "season", "week", "kickoff").filter(
        c("season").is_in(seasons)
    )
    if cadence == "in_season":
        moments = game_moments(cal, run).filter(c("season").is_in(seasons))
        groups = moments.select(GAME_COLUMNS).partition_by(
            "season", "week", maintain_order=False, as_dict=True
        )
        ordered = sorted(groups.items(), key=lambda kv: kv[1]["moment"].min())
        return [
            Step(i, int(s), int(w), frame["moment"].min(), frame.sort("moment", "game_id"))
            for i, ((s, w), frame) in enumerate(ordered)
        ]
    if cadence == "retrospective":
        at = season_moments(cal)
    elif cadence == "offseason_events":
        if event is None:
            raise ValueError("offseason_events steps need an event")
        at = event_moments(cal, event)
    else:
        raise ValueError(f"no cadence {cadence!r}")
    at = at.filter(c("season").is_in(seasons)).sort("season")
    out = []
    for i, (season, moment) in enumerate(at.iter_rows()):
        frame = games.filter(c("season") == season).with_columns(
            moment=pl.lit(moment).cast(pl.Datetime("us", "UTC"))
        )
        out.append(Step(i, int(season), None, moment, frame.select(GAME_COLUMNS)))
    return out


def step_table(all_steps: Sequence[Step]) -> pl.DataFrame:
    """One row per game: game_id, step, step_season, step_week, as_of (its prediction moment)."""
    return pl.concat(
        [
            s.games.select(
                "game_id",
                step=pl.lit(s.index, pl.Int32),
                step_season=pl.lit(s.season, pl.Int32),
                step_week=pl.lit(s.week, pl.Int32),
                as_of=c("moment"),
            )
            for s in all_steps
        ]
    )


def assert_walk_forward(train: pl.DataFrame, at: datetime) -> None:
    """Leakage check 7 at runtime: every training row was predicted before the fit moment and its
    outcome was known by then."""
    moment = pl.lit(at).cast(pl.Datetime("us", "UTC"))
    late = train.filter((c("as_of") >= moment) | (c("known_at") > moment)).height
    if late:
        raise AssertionError(f"{late} training rows come from at or after the fit moment {at}")
