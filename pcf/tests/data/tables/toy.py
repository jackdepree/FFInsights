"""A toy season for the table tests: one regular week and the Super Bowl, KC at home to BUF."""

from datetime import UTC, date, datetime

import polars as pl

from pcf.config import PCF_DIR
from pcf.data.tables.games import FACTS, PREGAME, RESULT
from pcf.data.timeline import calendar

GAMES = pl.DataFrame(
    {
        "game_id": ["2025_01_BUF_KC", "2025_22_BUF_KC"],
        "season": [2025, 2025],
        "week": [1, 22],
        "game_type": ["REG", "SB"],
        "gameday": ["2025-09-07", "2026-02-08"],
        "gametime": ["13:00", "18:30"],
        "home_team": ["KC", "KC"],
        "away_team": ["BUF", "BUF"],
        "home_score": [27, None],
        "away_score": [20, None],
        "spread_line": [3.5, 1.5],
        "home_moneyline": [-180, -120],
        "away_moneyline": [150, 100],
        "home_rest": [7, 14],
        "away_rest": [7, 13],
    },
    schema_overrides={"season": pl.Int32, "week": pl.Int32, "home_score": pl.Int64},
)
OFFSEASON = pl.DataFrame(
    {"season": [2025], "draft_start": [date(2025, 4, 24)], "draft_end": [date(2025, 4, 26)]},
    schema_overrides={"season": pl.Int32},
)


def schedules() -> pl.DataFrame:
    """The toy games with every schedule column the tables read (the rest null)."""
    have = set(GAMES.columns)
    extra = [c for c in [*FACTS, *PREGAME, *RESULT] if c not in have and c != "kickoff"]
    out = GAMES.with_columns(pl.lit(None).alias(c) for c in extra)
    return out.with_columns(
        home_spread=-pl.col("spread_line"),
        result=pl.col("home_score") - pl.col("away_score"),
    )


def cal():
    full = OFFSEASON.with_columns(
        pl.lit(None, pl.Date).alias(c)
        for c in ["league_year_start", "combine_start", "combine_end", "preseason_start"]
    ).with_columns(notes=pl.lit(None, pl.String))
    return calendar(schedules(), full)


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


KICK = utc(2025, 9, 7, 17)  # 1 PM Eastern


FIXTURES = PCF_DIR / "tests" / "fixtures" / "cleaning_port"


def fixture(name: str) -> pl.DataFrame:
    """Public nflverse rows saved by cleaning-port: two 2024 week-10 games (DET at HOU, DEN at
    KC) and their teams' charts and rosters."""
    return pl.read_parquet(FIXTURES / f"{name}.parquet")


def cal_2024():
    """A calendar with the two fixture games and a Super Bowl to end their season."""
    games = pl.DataFrame(
        {
            "game_id": ["2024_10_DET_HOU", "2024_10_DEN_KC", "2024_22_KC_PHI"],
            "season": [2024, 2024, 2024],
            "week": [10, 10, 22],
            "game_type": ["REG", "REG", "SB"],
            "gameday": ["2024-11-10", "2024-11-10", "2025-02-09"],
            "gametime": ["20:20", "13:00", "18:30"],
            "home_team": ["HOU", "KC", "PHI"],
            "away_team": ["DET", "DEN", "KC"],
        },
        schema_overrides={"season": pl.Int32, "week": pl.Int32},
    )
    off = pl.DataFrame(
        {"season": [2024], "draft_start": [date(2024, 4, 25)], "draft_end": [date(2024, 4, 27)]},
        schema_overrides={"season": pl.Int32},
    )
    full = off.with_columns(
        pl.lit(None, pl.Date).alias(c)
        for c in ["league_year_start", "combine_start", "combine_end", "preseason_start"]
    ).with_columns(notes=pl.lit(None, pl.String))
    return calendar(games, full)


SUPER_BOWL_2024 = utc(2025, 2, 9, 23, 30)
