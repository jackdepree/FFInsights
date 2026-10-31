"""Known-at rules: one per nflverse dataset, each adding a UTC `known_at` column (rule c).

`known_at` is the earliest moment PCF could have had a row, for a live prediction
(docs/DATA_SOURCES.md). Each rule follows that file's table. Where a source carries its own
timestamp, the rule never comes before it. When unsure, the rule leans late.
"""

from collections.abc import Callable
from datetime import datetime

import polars as pl

from pcf.core.log import get_logger
from pcf.data.clean.standard import team
from pcf.data.timeline.calendar import Calendar, day_start

log = get_logger(__name__)

ONE_DAY = pl.duration(days=1)
# Injury reports without `date_modified` (2009, 2025→). Only 0.06% of 2010-2024 reports were
# modified later than this (timeline#F4).
INJURY_LEAD = pl.duration(hours=12)
# Draft years with no row in the offseason dates file: every draft has ended by June 1.
LATE_DRAFT_FALLBACK = (6, 1)


def _by_game(
    df: pl.DataFrame, cal: Calendar, column: str, offset: pl.Expr, key: str = "game_id"
) -> pl.DataFrame:
    """known_at = the game's kickoff + offset, matching `column` to the calendar's `key`."""
    kick = cal.games.select(pl.col(key).alias(column), "kickoff").drop_nulls(column)
    out = df.join(kick, on=column, how="left")
    _require(out, "kickoff", f"{column} values not in the schedule")
    return out.with_columns(known_at=pl.col("kickoff") + offset).drop("kickoff")


def _week_edge(
    df: pl.DataFrame, cal: Calendar, edge: str, offset: pl.Expr, week_shift: int = 0
) -> pl.Series:
    """Each row's week window `edge` ("start" or "end") + offset; `week_shift` weeks later."""
    w = cal.weeks.select("season", week=pl.col("week") - week_shift, at=pl.col(edge))
    keyed = df.select(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
    joined = keyed.join(w, on=["season", "week"], how="left", maintain_order="left")
    return joined.select(pl.col("at") + offset).to_series()


def _require(df: pl.DataFrame, column: str, what: str) -> None:
    missing = df.filter(pl.col(column).is_null()).height
    if missing:
        raise ValueError(f"known_at: {missing} rows have {what}")


def _season_end(cal: Calendar) -> pl.DataFrame:
    """season → the day after its Super Bowl kickoff (only seasons whose Super Bowl is set)."""
    return cal.games.filter(pl.col("game_type") == "SB").select(
        "season", season_end=pl.col("kickoff") + ONE_DAY
    )


def _fetched(fetched_at: datetime | None, dataset: str) -> datetime:
    if fetched_at is None:
        raise ValueError(f"{dataset} is a state file: pass fetched_at (when this copy was taken)")
    if fetched_at.tzinfo is None:
        raise ValueError("fetched_at must be timezone-aware")
    return fetched_at


def after_game(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Results of a game (play-by-play, player and team stats, snaps, expected fantasy points):
    kickoff + 1 day."""
    return _by_game(df, cal, "game_id", ONE_DAY)


def ftn_charting(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """FTN charting: kickoff + 14 days. Not `date_pulled`, which records later re-pulls
    (package-scaffold#F1)."""
    return _by_game(df, cal, "nflverse_game_id", pl.duration(days=14))


def officials(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Officials: kickoff − 2 days. Their `game_id` is the old 10-digit id. A few keep the id of
    a game that was moved or canceled (2021 COVID postponements, 2022 BUF at CIN); those use the
    latest kickoff of that week."""
    kick = cal.games.select(game_id="old_game_id", kickoff="kickoff")
    latest = cal.games.group_by("season", "week").agg(latest=pl.col("kickoff").max())
    out = df.join(kick, on="game_id", how="left").join(latest, on=["season", "week"], how="left")
    moved = out.filter(pl.col("kickoff").is_null()).height
    if moved:
        log.info(
            "officials: %d rows for moved or canceled games use their week's last kickoff", moved
        )
    out = out.with_columns(known_at=pl.coalesce("kickoff", "latest") - pl.duration(days=2))
    _require(out, "known_at", "a season-week not in the schedule")
    return out.drop("kickoff", "latest")


def participation(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Participation: published after the season, so the day after that season's Super Bowl."""
    seasons = cal.games.select(nflverse_game_id="game_id", season="season")
    out = df.join(seasons, on="nflverse_game_id", how="left").join(
        _season_end(cal), on="season", how="left"
    )
    _require(out, "season_end", "a game from a season without a Super Bowl yet")
    return out.rename({"season_end": "known_at"}).drop("season")


def _season_rows(
    df: pl.DataFrame, ends: pl.DataFrame, fetched_at: datetime | None, name: str
) -> pl.Series:
    """Season totals: the season's end where it has one, otherwise the copy's fetch time."""
    keyed = df.select(pl.col("season").cast(pl.Int32)).join(
        ends, on="season", how="left", maintain_order="left"
    )["season_end"]
    if keyed.is_null().any():
        keyed = keyed.fill_null(_fetched(fetched_at, f"{name} (an unfinished season)"))
    return keyed


def ngs(df: pl.DataFrame, cal: Calendar, fetched_at: datetime | None = None, **_: object):
    """Next Gen Stats: a week's rows the day after the week ends (after its last game + 1 day).
    Week 0 is the regular season's total: the day after the regular season ends. NGS numbers the
    Super Bowl one past the schedule (it counts the bye week), so later weeks map to it."""
    last = cal.weeks.group_by("season").agg(last=pl.col("week").max())
    keyed = df.select(pl.col("season").cast(pl.Int32), "week").join(
        last, on="season", how="left", maintain_order="left"
    )
    weekly = _week_edge(
        keyed.select("season", week=pl.min_horizontal("week", "last")), cal, "end", ONE_DAY
    )
    reg_end = (
        cal.weeks.filter(pl.col("phase") == "regular_season")
        .group_by("season")
        .agg(season_end=pl.col("end").max() + ONE_DAY)
    )
    finished = reg_end.join(
        cal.weeks.filter(pl.col("phase") == "postseason").select("season").unique(), on="season"
    )  # the regular season is over once postseason games are on the schedule
    totals = _season_rows(df, finished, fetched_at, "ngs week 0")
    out = df.with_columns(known_at=pl.when(pl.col("week") == 0).then(totals).otherwise(weekly))
    _require(out, "known_at", "a season-week not in the schedule")
    return out


def pfr_week(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """PFR advanced stats: about a week behind, so the start of the week after next (the Tuesday
    after the following week). Late in a season with no such week yet: the week's end + 8 days."""
    after_next = _week_edge(df, cal, "start", pl.duration(), week_shift=2)
    fallback = _week_edge(df, cal, "end", pl.duration(days=8))
    out = df.with_columns(known_at=after_next.fill_null(fallback))
    _require(out, "known_at", "a season-week not in the schedule")
    return out


def pfr_season(df: pl.DataFrame, cal: Calendar, fetched_at: datetime | None = None, **_: object):
    """PFR season totals: the day after the Super Bowl; an unfinished season, its fetch time."""
    return df.with_columns(known_at=_season_rows(df, _season_end(cal), fetched_at, "pfr"))


def depth_charts(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Depth charts: the snapshot's `dt` (2025→); weekly charts, the start of their week. The
    Super Bowl bye week (no week number) is the Super Bowl's week. The 2025→ files alone have
    no season or week."""
    snapshot = pl.col("dt").str.to_datetime(time_zone="UTC") if "dt" in df.columns else pl.lit(None)
    if "season" not in df.columns:
        out = df.with_columns(known_at=snapshot)
        _require(out, "known_at", "no dt")
        return out
    sb_week = cal.weeks.filter("super_bowl").select("season", sb=pl.col("week"))
    keyed = df.with_columns(pl.col("season").cast(pl.Int32)).join(
        sb_week, on="season", how="left", maintain_order="left"
    )
    week = keyed.select(season="season", week=pl.coalesce(pl.col("week").cast(pl.Int32), "sb"))
    weekly = _week_edge(week, cal, "start", pl.duration())
    out = df.with_columns(known_at=pl.coalesce(snapshot, weekly))
    _require(out, "known_at", "a season-week not in the schedule")
    return out


def week_start(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Weekly rosters: the start of that week."""
    out = df.with_columns(known_at=_week_edge(df, cal, "start", pl.duration()))
    _require(out, "known_at", "a season-week not in the schedule")
    return out


def injuries(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Injury reports: `date_modified`, when the report was last changed. Without it (2009,
    2025→): kickoff − 12 hours. "Noon ET the day before" was too early for 6-7% of 2021-2024
    reports, mostly Thursday games (timeline#F4)."""
    key = ["season", "week", "game_type", "team"]
    kick = pl.concat(
        [
            cal.games.select("season", "week", "game_type", team=pl.col(t), kickoff="kickoff")
            for t in ("home_team", "away_team")
        ]
    )
    if kick.select(key).is_duplicated().any():
        raise ValueError("known_at: a team plays twice in one week of the schedule")
    keyed = df.select(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), "game_type", team("team")
    ).join(kick, on=key, how="left", maintain_order="left")
    out = df.with_columns(
        known_at=pl.coalesce(pl.col("date_modified"), keyed["kickoff"] - INJURY_LEAD)
    )
    _require(out, "known_at", "no date_modified and no matching game")
    return out


def schedules(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Schedules carry three kinds of field, so three columns:
    - `facts_known_at`: date, teams, stadium, roof. Released in spring; here, conservatively, the
      start of the season's week 1. A flexed game's time is only right after the flex.
    - `lines_known_at`: spreads, totals and moneylines, which sit near the close: kickoff
      (odds-collection#F3).
    - `known_at`: the whole row, scores included: kickoff + 1 day.
    """
    week1 = cal.weeks.filter(pl.col("week") == 1).select("season", facts_known_at="start")
    kick = cal.games.select("game_id", lines_known_at="kickoff")
    out = df.join(kick, on="game_id", how="left").join(
        week1, on=pl.col("season").cast(pl.Int32), how="left"
    )
    return out.with_columns(known_at=pl.col("lines_known_at") + ONE_DAY)


def _offseason_day(df: pl.DataFrame, cal: Calendar, day: pl.Expr) -> pl.Series:
    """season → the start of `day` (an expression over the offseason dates file), in Eastern
    time; June 1 for years missing from the file or with no date."""
    dates = cal.offseason.select("season", day=day)
    keyed = df.select(pl.col("season").cast(pl.Int32)).join(
        dates, on="season", how="left", maintain_order="left"
    )
    late = pl.date(pl.col("season"), *LATE_DRAFT_FALLBACK)
    return keyed.select(day_start(pl.coalesce("day", late))).to_series()


def combine(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Combine results: the day after the combine ends. Without its dates, the first day of the
    draft (results are out by then, pro days included)."""
    day = pl.coalesce(pl.col("combine_end") + ONE_DAY, "draft_start")
    return df.with_columns(known_at=_offseason_day(df, cal, day))


def draft_picks(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Draft picks: the day after the draft ends (leaning late: a pick is known the day it's
    made, and this skips the draft's middle days)."""
    return df.with_columns(known_at=_offseason_day(df, cal, pl.col("draft_end") + ONE_DAY))


def _day_after(column: str, dtype: pl.DataType) -> pl.Expr:
    """A date column (or date string) → the start of the next day in Eastern time. Sources that
    give a day without a time are known by the end of it."""
    col = pl.col(column)
    day = col.str.to_date() if dtype == pl.String else col.cast(pl.Date)
    return day_start(day + ONE_DAY)


def trades(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """Trades: the end of `trade_date`."""
    return df.with_columns(known_at=_day_after("trade_date", df.schema["trade_date"]))


def ecr(df: pl.DataFrame, cal: Calendar, **_: object) -> pl.DataFrame:
    """FantasyPros rankings: the end of `scrape_date`."""
    return df.with_columns(known_at=_day_after("scrape_date", df.schema["scrape_date"]))


def state(
    df: pl.DataFrame,
    cal: Calendar,
    fetched_at: datetime | None = None,
    *,
    dataset: str = "state file",
    **_: object,
):
    """State and reference files (players, rosters, contracts, ids, teams): when this copy was
    taken (the manifest's fetch time, or the `snapshot()` moment)."""
    return df.with_columns(
        known_at=pl.lit(_fetched(fetched_at, dataset)).dt.convert_time_zone("UTC")
    )


Rule = Callable[..., pl.DataFrame]
RULES: dict[str, Rule] = {
    **{
        d: after_game
        for d in [
            "pbp",
            "player_stats",
            "team_stats",
            "snap_counts",
            "ff_opportunity",
            "ff_opportunity_pass",
            "ff_opportunity_rush",
        ]
    },
    "ftn_charting": ftn_charting,
    "officials": officials,
    "participation": participation,
    **{d: ngs for d in ["ngs_passing", "ngs_receiving", "ngs_rushing"]},
    **{d: pfr_week for d in ["pfr_week_pass", "pfr_week_rush", "pfr_week_rec", "pfr_week_def"]},
    **{
        d: pfr_season
        for d in ["pfr_season_pass", "pfr_season_rush", "pfr_season_rec", "pfr_season_def"]
    },
    "depth_charts": depth_charts,
    "weekly_rosters": week_start,
    "injuries": injuries,
    "schedules": schedules,
    "combine": combine,
    "draft_picks": draft_picks,
    "trades": trades,
    **{d: ecr for d in ["ecr_archive", "ecr_draft", "ecr_week"]},
    **{d: state for d in ["players", "rosters", "contracts", "player_ids", "teams"]},
}


def known_at(
    dataset: str, df: pl.DataFrame, cal: Calendar, fetched_at: datetime | None = None
) -> pl.DataFrame:
    """A dataset's rows with `known_at` added by its rule. `fetched_at` is needed for state files
    and for season totals of an unfinished season."""
    if dataset not in RULES:
        raise ValueError(f"no known-at rule for {dataset!r}")
    out = RULES[dataset](df, cal, fetched_at=fetched_at, dataset=dataset)
    check_known_at(out)
    return out


def check_known_at(df: pl.DataFrame, not_before: str | None = None) -> None:
    """Leakage check 2 (docs/ARCHITECTURE.md): `known_at` exists, is UTC and timezone-aware, has
    no nulls, and (with `not_before`) is never earlier than that event-time column."""
    if "known_at" not in df.columns:
        raise ValueError("no known_at column")
    dtype = df.schema["known_at"]
    if not isinstance(dtype, pl.Datetime) or dtype.time_zone != "UTC":
        raise ValueError(f"known_at must be a UTC datetime, not {dtype}")
    nulls = df["known_at"].null_count()
    if nulls:
        raise ValueError(f"known_at is missing on {nulls} rows")
    if not_before is not None:
        early = df.filter(pl.col("known_at") < pl.col(not_before)).height
        if early:
            raise ValueError(f"{early} rows are known before their {not_before}")
