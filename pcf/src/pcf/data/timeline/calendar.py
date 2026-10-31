"""The NFL calendar: games with kickoff times, week windows and phases (timeline brief).

All times are UTC and timezone-aware. Day-based rules are worked out in US Eastern time, the
league's own clock, then converted.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from importlib.resources import files

import polars as pl

ET = "America/New_York"
# 1999 has no game times (timeline#F1). Its games get the most common slot.
STAND_IN_GAMETIME = "13:00"
# The new league year opens at 4 PM ET (in every year with a published time).
LEAGUE_YEAR_HOUR = 16
OFFSEASON_FILE = "offseason_dates.csv"
OFFSEASON_COLUMNS = [
    "league_year_start",
    "combine_start",
    "combine_end",
    "draft_start",
    "draft_end",
    "preseason_start",
]
GAME_COLUMNS = ["game_id", "old_game_id", "season", "week", "game_type", "home_team", "away_team"]

# Phases, named by the event that starts them. Offseason phases belong to the coming season.
PHASES = [
    "offseason",
    "free_agency",
    "draft",
    "after_draft",
    "preseason",
    "regular_season",
    "postseason",
]


def day_start(day: pl.Expr) -> pl.Expr:
    """A calendar day (Date) → midnight starting it in Eastern time, as UTC."""
    return day.cast(pl.Datetime("us")).dt.replace_time_zone(ET).dt.convert_time_zone("UTC")


def et_date(moment: pl.Expr) -> pl.Expr:
    """A UTC moment → its calendar day in Eastern time."""
    return moment.dt.convert_time_zone(ET).dt.date()


def games(schedules: pl.DataFrame) -> pl.DataFrame:
    """Schedules → one row per game with its kickoff (UTC): game_id, old_game_id, season, week,
    game_type, home_team, away_team, kickoff.

    `gametime` is US Eastern for every game, international ones included (timeline#F1). Pass
    schedules through `standard.schedules` first for PCF's team codes. `old_game_id` (needed only
    by the officials rule) is null if the input lacks it.
    """
    if "old_game_id" not in schedules.columns:
        schedules = schedules.with_columns(old_game_id=pl.lit(None, pl.String))
    return schedules.select(
        *GAME_COLUMNS,
        kickoff=(pl.col("gameday") + " " + pl.col("gametime").fill_null(STAND_IN_GAMETIME))
        .str.to_datetime("%Y-%m-%d %H:%M", time_zone=ET)
        .dt.convert_time_zone("UTC"),
    ).sort("kickoff", "game_id")


def team_kickoffs(game_rows: pl.DataFrame) -> pl.DataFrame:
    """Games → one row per team and game: season, week, team, kickoff."""
    return pl.concat(
        [
            game_rows.select("season", "week", team=pl.col(side), kickoff="kickoff")
            for side in ("home_team", "away_team")
        ]
    ).sort("season", "week", "team")


def weeks(game_rows: pl.DataFrame) -> pl.DataFrame:
    """Games → one row per season-week: season, week, phase, start, end (UTC), super_bowl.

    A week ends at midnight Eastern after its last game day, and the next week starts there, so
    weeks never overlap and every moment of a season falls in one (timeline#F3). Week 1 starts two
    days before its first game day: the Tuesday before a Thursday opener, like most weeks.
    """
    w = (
        game_rows.with_columns(day=et_date(pl.col("kickoff")))
        .group_by("season", "week")
        .agg(
            first_day=pl.col("day").min(),
            last_day=pl.col("day").max(),
            regular=(pl.col("game_type") == "REG").all(),
            super_bowl=(pl.col("game_type") == "SB").any(),
        )
        .sort("season", "week")
        .with_columns(end=day_start(pl.col("last_day") + pl.duration(days=1)))
    )
    return w.select(
        "season",
        "week",
        phase=pl.when("regular").then(pl.lit("regular_season")).otherwise(pl.lit("postseason")),
        start=pl.coalesce(
            pl.col("end").shift(1).over("season"),
            day_start(pl.col("first_day") - pl.duration(days=2)),
        ),
        end="end",
        super_bowl="super_bowl",
    )


def offseason_dates() -> pl.DataFrame:
    """The offseason dates file: one row per league year, with the dates in OFFSEASON_COLUMNS
    (null where no public source gave one) and notes."""
    text = files("pcf.data.timeline").joinpath(OFFSEASON_FILE).read_text(encoding="utf-8")
    return pl.read_csv(
        text.encode(),
        comment_prefix="#",
        schema_overrides={c: pl.Date for c in OFFSEASON_COLUMNS} | {"season": pl.Int32},
    )


def phases(week_rows: pl.DataFrame, offseason: pl.DataFrame) -> pl.DataFrame:
    """Week windows + offseason dates → one row per phase: season, phase, start, end (UTC).

    A phase runs from the event that starts it to the next event, so a year with an odd order
    still works (2011: free agency opened after the draft). A missing date merges its phase into
    the one before. The next offseason starts only once the Super Bowl is on the schedule, so the
    last phase (no end) is the current one.
    """
    by_week = week_rows.group_by("season", "phase").agg(start=pl.col("start").min())
    season_end = week_rows.filter("super_bowl").select("season", "end")
    events = pl.concat(
        [
            by_week,
            # The offseason for season Y starts when season Y-1 ends.
            season_end.select(season=pl.col("season") + 1, phase=pl.lit("offseason"), start="end"),
            offseason.select(
                "season",
                phase=pl.lit("free_agency"),
                start=day_start(pl.col("league_year_start")) + pl.duration(hours=LEAGUE_YEAR_HOUR),
            ),
            offseason.select(
                "season", phase=pl.lit("draft"), start=day_start(pl.col("draft_start"))
            ),
            offseason.select(
                "season",
                phase=pl.lit("after_draft"),
                start=day_start(pl.col("draft_end") + pl.duration(days=1)),
            ),
            offseason.select(
                "season", phase=pl.lit("preseason"), start=day_start(pl.col("preseason_start"))
            ),
        ],
        how="vertical_relaxed",
    ).drop_nulls("start")
    return (
        events.sort("start")
        .with_columns(end=pl.col("start").shift(-1))
        .select("season", "phase", "start", "end")
    )


@dataclass(frozen=True)
class Calendar:
    """Everything the known-at rules and `phase_at` need, built once by `calendar()`."""

    games: pl.DataFrame
    weeks: pl.DataFrame
    phases: pl.DataFrame
    offseason: pl.DataFrame


def calendar(schedules: pl.DataFrame, offseason: pl.DataFrame | None = None) -> Calendar:
    """Standardized schedules (+ the offseason dates file by default) → a Calendar."""
    offseason = offseason_dates() if offseason is None else offseason
    g = games(schedules)
    w = weeks(g)
    return Calendar(games=g, weeks=w, phases=phases(w, offseason), offseason=offseason)


def phase_at(cal: Calendar, moment: datetime) -> dict[str, object]:
    """The season, phase and week (None outside the season) a moment falls in."""
    if moment.tzinfo is None:
        raise ValueError("phase_at needs a timezone-aware moment")
    at = pl.DataFrame({"at": [moment]}).with_columns(pl.col("at").dt.convert_time_zone("UTC"))
    phase = at.join_asof(cal.phases, left_on="at", right_on="start", strategy="backward")
    week = at.join_asof(cal.weeks, left_on="at", right_on="start", strategy="backward")
    row = phase.row(0, named=True)
    if row["phase"] is None:
        raise ValueError(f"{moment} is before PCF's calendar starts")
    in_week = row["phase"] in ("regular_season", "postseason")
    w = week.row(0, named=True)
    return {
        "season": row["season"],
        "phase": row["phase"],
        "week": w["week"] if in_week and w["end"] > at["at"][0] else None,
    }


def missing_offseason_row(offseason: pl.DataFrame, today: date | None = None) -> int | None:
    """The league year whose row is due but missing (from February 1), or None."""
    today = today or datetime.now(UTC).date()
    due = today.year if today.month >= 2 else today.year - 1
    return None if due in set(offseason["season"]) else due
