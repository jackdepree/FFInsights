"""Prediction moments: when PCF makes each prediction (validation-harness brief, CEO decision 1C).

The three weekly runs are the named moments. A model declares its run, and each game is
predicted at the latest run before its kickoff whose kind it may use: a `saturday` model
predicts Thursday games at the Wednesday run, never after kickoff.

Retrospective models predict a season at 10:00 ET on the first day of its week-1 window;
offseason-events models at the start of the event's phase.
"""

from datetime import datetime

import polars as pl

from pcf.data.timeline.calendar import ET, Calendar

c = pl.col

# The weekly runs (ARCHITECTURE.md, "Running it"): weekday (Monday = 1) and hour, Eastern time.
RUNS: dict[str, tuple[int, int]] = {
    "tuesday": (2, 10),  # the full weekly run, after Monday night
    "wednesday": (3, 16),  # Thursday's injury reports and the week's practice news
    "saturday": (6, 12),  # Sunday's final injury reports; before any Saturday game
}
# Retrospective moments, and weeks with no allowed run before a game: 10:00 ET on the first day.
FIRST_DAY_HOUR = 10
EVENTS = ("free_agency", "draft")


def allowed(run: str) -> list[str]:
    """The runs a model declaring `run` may be predicted at: its own and the earlier ones."""
    if run not in RUNS:
        raise ValueError(f"no run {run!r}. Runs: {', '.join(RUNS)}")
    order = list(RUNS)
    return order[: order.index(run) + 1]


def _local(day: pl.Expr, hour: int) -> pl.Expr:
    """A calendar day (Eastern) and an hour → that moment in UTC."""
    return (
        (day.cast(pl.Datetime("us")) + pl.duration(hours=hour))
        .dt.replace_time_zone(ET)
        .dt.convert_time_zone("UTC")
    )


def runs(cal: Calendar) -> pl.DataFrame:
    """Every run in every week window: season, week, run, at (UTC). A long window (the week
    before the Super Bowl) has a run on each matching day."""
    days = (
        cal.weeks.select(
            "season",
            "week",
            "start",
            "end",
            day=pl.date_ranges(
                c("start").dt.convert_time_zone(ET).dt.date(),
                (c("end") - pl.duration(microseconds=1)).dt.convert_time_zone(ET).dt.date(),
            ),
        )
        .explode("day")
        .with_columns(weekday=c("day").dt.weekday())
    )
    out = []
    for name, (weekday, hour) in RUNS.items():
        out.append(
            days.filter(c("weekday") == weekday).select(
                "season", "week", run=pl.lit(name), at=_local(c("day"), hour), start="start"
            )
        )
    return pl.concat(out).filter(c("at") >= c("start")).drop("start").sort("at")


def game_moments(cal: Calendar, run: str = "tuesday") -> pl.DataFrame:
    """Each game's prediction moment for a model declaring `run`: game_id, season, week,
    kickoff, moment, and `fallback`. A week that starts mid-week (a Tuesday or Wednesday game the
    week before, as in 2010 and 2020-21, or a Friday-start week 1 in 1999-2001) can have no allowed
    run before a game: its moment is then 10:00 ET on the window's first day (`fallback`), or
    the window's start if that's already past kickoff."""
    games = cal.games.select("game_id", "season", "week", "kickoff")
    chosen = (
        games.join(runs(cal).filter(c("run").is_in(allowed(run))), on=["season", "week"])
        .filter(c("at") < c("kickoff"))
        .group_by("game_id")
        .agg(moment=c("at").max())
    )
    starts = cal.weeks.select(
        "season",
        "week",
        "start",
        first_day=_local(c("start").dt.convert_time_zone(ET).dt.date(), FIRST_DAY_HOUR),
    )
    early = pl.when(c("first_day") < c("kickoff")).then("first_day").otherwise("start")
    return (
        games.join(chosen, on="game_id", how="left")
        .join(starts, on=["season", "week"], how="left")
        .with_columns(fallback=c("moment").is_null())
        .with_columns(moment=pl.coalesce(c("moment"), early))
        .drop("start", "first_day")
        .sort("moment", "game_id")
    )


def season_moments(cal: Calendar) -> pl.DataFrame:
    """Each season's retrospective moment: 10:00 ET on the first day of its week-1 window."""
    first = cal.weeks.group_by("season").agg(c("start").min())
    return first.select(
        "season",
        moment=_local(c("start").dt.convert_time_zone(ET).dt.date(), FIRST_DAY_HOUR),
    ).sort("season")


def event_moments(cal: Calendar, event: str) -> pl.DataFrame:
    """Each season's moment for an offseason event: the start of its phase (free agency, draft)."""
    if event not in EVENTS:
        raise ValueError(f"no event {event!r}. Events: {', '.join(EVENTS)}")
    return cal.phases.filter(c("phase") == event).select("season", moment="start").sort("season")


def season_ends(cal: Calendar) -> dict[int, datetime]:
    """When each finished season ends: the end of its Super Bowl week."""
    ends = cal.weeks.filter("super_bowl").select("season", "end")
    return dict(ends.iter_rows())
