from datetime import timedelta

import polars as pl

from pcf.data.clean import standard
from pcf.data.clean.depth_charts import depth_labels, weekly_depth_rows
from pcf.data.schemas import check_parts
from pcf.data.tables.plays import play_parts, player_play_parts

from .toy import SUPER_BOWL_2024, cal_2024, fixture, utc

DEN_KC = utc(2024, 11, 10, 18)  # 1 PM Eastern


def _ftn(pbp: pl.DataFrame) -> pl.DataFrame:
    """FTN-shaped rows for the fixture's run and pass plays."""
    plays = pbp.filter(pl.col("play_type").is_in(["run", "pass"]))
    return plays.select(
        nflverse_game_id="game_id",
        nflverse_play_id=pl.col("play_id").cast(pl.Int64),
        season="season",
        week="week",
        is_play_action=pl.lit(False),
        play_type=pl.lit("ftn's own"),  # a column play-by-play also has
        date_pulled=pl.lit("2024-12-01"),
    )


def test_play_parts_are_known_after_the_game_the_season_and_two_weeks():
    pbp = fixture("pbp_2024")
    part = fixture("participation_2024").with_columns(possession_team=pl.lit(None, pl.String))
    parts = play_parts(pbp, cal_2024(), part, _ftn(pbp))
    check_parts(parts, "play")
    den_kc = pl.col("game_id") == "2024_10_DEN_KC"
    assert parts["pbp"].height == pbp.height
    assert parts["pbp"].filter(den_kc)["known_at"].unique().to_list() == [
        DEN_KC + timedelta(days=1)
    ]
    assert parts["participation"]["known_at"].unique().to_list() == [
        SUPER_BOWL_2024 + timedelta(days=1)
    ]
    assert parts["ftn"].filter(den_kc)["known_at"].unique().to_list() == [
        DEN_KC + timedelta(days=14)
    ]
    # Play-by-play keeps its own column where FTN repeats it.
    assert "play_type" not in parts["ftn"].columns
    assert {"is_play_action", "known_at"} <= set(parts["ftn"].columns)


def test_player_play_has_each_listed_player_with_a_label():
    rosters = standard.weekly_rosters(
        fixture("weekly_rosters_2024").with_columns(status=pl.lit("ACT"))
    )
    labels = depth_labels(weekly_depth_rows(fixture("depth_charts_2024")))
    parts = player_play_parts(
        fixture("pbp_2024"), fixture("participation_2024"), labels, rosters, cal_2024()
    )
    check_parts(parts, "player_play")
    on_field = parts["on_field"]
    assert on_field.group_by("game_id", "play_id", "side").len()["len"].max() <= 11
    assert on_field["known_at"].unique().to_list() == [SUPER_BOWL_2024 + timedelta(days=1)]
    assert {"side", "team", "slot", "position_label", "label_source"} <= set(on_field.columns)
