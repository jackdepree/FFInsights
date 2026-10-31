"""Small helpers the table builders share."""

from collections.abc import Sequence

import polars as pl

from pcf.core.log import get_logger

log = get_logger(__name__)


def on_spine(df: pl.DataFrame, spine: pl.DataFrame, keys: Sequence[str], what: str) -> pl.DataFrame:
    """Rows of a part whose keys are on the spine; the rest are dropped and counted in the log."""
    out = df.join(spine.select(keys), on=keys, how="semi")
    if out.height < df.height:
        log.info("%s: %d rows not on the spine dropped", what, df.height - out.height)
    return out


def merge(frames: Sequence[pl.DataFrame], keys: Sequence[str]) -> pl.DataFrame:
    """Several sources of one part, joined on their keys: a row from any of them, `season` from
    whichever has it, and the latest `known_at`."""
    out = frames[0]
    for other in frames[1:]:
        out = (
            out.join(other, on=keys, how="full", coalesce=True, suffix="_other")
            .with_columns(
                season=pl.coalesce("season", "season_other"),
                known_at=pl.max_horizontal("known_at", "known_at_other"),
            )
            .drop("season_other", "known_at_other")
        )
    return out


def prefixed(df: pl.DataFrame, prefix: str, keep: Sequence[str]) -> pl.DataFrame:
    """Every column but `keep` renamed `<prefix><column>`, for sources whose names would clash
    with another part's (NGS, PFR, ff_opportunity)."""
    return df.rename({c: f"{prefix}{c}" for c in df.columns if c not in keep})


def team_games(cal_games: pl.DataFrame) -> pl.DataFrame:
    """Calendar games → one row per team and game: game_id, season, week, game_type, team,
    opponent, home, kickoff."""
    sides = []
    for side, other in (("home_team", "away_team"), ("away_team", "home_team")):
        sides.append(
            cal_games.select(
                "game_id",
                "season",
                "week",
                "game_type",
                team=pl.col(side),
                opponent=pl.col(other),
                home=pl.lit(side == "home_team"),
                kickoff="kickoff",
            )
        )
    return pl.concat(sides).with_columns(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32)
    )
