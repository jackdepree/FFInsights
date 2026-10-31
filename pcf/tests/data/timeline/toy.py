"""A toy season shared by the timeline tests."""

from datetime import UTC, date, datetime

import polars as pl


def schedule(rows):
    """Synthetic schedules: (game_id, season, week, game_type, gameday, gametime)."""
    cols = ["game_id", "season", "week", "game_type", "gameday", "gametime"]
    return pl.DataFrame(rows, schema=cols, orient="row").with_columns(
        pl.col("season").cast(pl.Int32),
        pl.col("week").cast(pl.Int32),
        # Each game in a week has its own teams: a team plays once a week.
        home_team=pl.when(pl.col("game_id").str.ends_with("B"))
        .then(pl.lit("DAL"))
        .otherwise(pl.lit("KC")),
        away_team=pl.when(pl.col("game_id").str.ends_with("B"))
        .then(pl.lit("NYG"))
        .otherwise(pl.lit("BUF")),
    )


# One short season: two regular weeks, a playoff week and the Super Bowl.
SEASON = schedule(
    [
        ("2025_01_A", 2025, 1, "REG", "2025-09-04", "20:20"),
        ("2025_01_B", 2025, 1, "REG", "2025-09-08", "20:15"),
        ("2025_02_A", 2025, 2, "REG", "2025-09-14", "13:00"),
        ("2025_19_A", 2025, 19, "WC", "2026-01-10", "16:30"),
        ("2025_22_A", 2025, 22, "SB", "2026-02-08", "18:30"),
    ]
)
OFFSEASON = pl.DataFrame(
    {
        "season": [2025, 2026],
        "league_year_start": [date(2025, 3, 12), date(2026, 3, 11)],
        "combine_start": [None, None],
        "combine_end": [None, None],
        "draft_start": [date(2025, 4, 24), date(2026, 4, 23)],
        "draft_end": [date(2025, 4, 26), date(2026, 4, 25)],
        "preseason_start": [date(2025, 7, 31), None],
        "notes": [None, None],
    },
    schema_overrides={"season": pl.Int32, "combine_start": pl.Date, "combine_end": pl.Date},
)


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)
