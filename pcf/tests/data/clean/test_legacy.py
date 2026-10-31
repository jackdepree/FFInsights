"""Golden tests: the copy in pcf.data.clean.legacy gives exactly what the old notebook gives."""

import pandas as pd
import polars as pl
import pytest

from pcf.data.clean import legacy
from pcf.data.clean.players import plays_with_players
from pcf.data.sources.nflverse import scan

from .reference import reference

PLAY_COLUMNS = [
    "offense_players",
    "defense_players",
    "game_id",
    "play_id",
    "play_type",
    "season",
    "week",
]


def _both(fn: str, *frames: pd.DataFrame):
    """Run the copy and the reference on separate copies of the same input."""
    ours = getattr(legacy, fn)(*(f.copy() for f in frames))
    theirs = reference()[fn](*(f.copy() for f in frames))
    return ours, theirs


def _inputs(plays: pl.DataFrame, depth: pl.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # The old notebooks passed exactly these columns (Fatigue_Model_Prod, data_preparation).
    return plays.select(PLAY_COLUMNS).to_pandas(), depth.to_pandas()


def test_copy_matches_the_notebook_on_two_2024_games(plays_2024, depth_2024):
    plays, depth = _inputs(plays_2024, depth_2024)
    for ours, theirs in [
        _both("pivot_wide_both_sides", plays),
        _both("clean_depth_charts", depth),
    ]:
        pd.testing.assert_frame_equal(ours, theirs)
    wide = legacy.pivot_wide_both_sides(plays)
    ours, theirs = _both("pivot_long_both_sides", wide, depth)
    pd.testing.assert_frame_equal(ours, theirs)
    assert len(ours) > 5_000  # about 250 run and pass plays x 22 players
    assert legacy.get_position_groups(None) == reference()["get_position_groups"](None)


@pytest.mark.local_data
@pytest.mark.parametrize("season", range(2016, 2025))
def test_copy_matches_the_notebook_on_every_season(season):
    pbp = scan("pbp", [season]).select(
        "game_id", "play_id", "play_type", "season", "week", "season_type", "posteam", "defteam"
    )
    part = scan("participation", [season]).select(
        "nflverse_game_id", "play_id", "offense_players", "defense_players"
    )
    plays = plays_with_players(pbp.collect(), part.collect())
    plays, depth = _inputs(plays, scan("depth_charts", [season]).collect())
    wide, wide_ref = _both("pivot_wide_both_sides", plays)
    pd.testing.assert_frame_equal(wide, wide_ref)
    ours, theirs = _both("pivot_long_both_sides", wide, depth)
    pd.testing.assert_frame_equal(ours, theirs)
