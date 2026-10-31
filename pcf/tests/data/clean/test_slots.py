import polars as pl
import pytest

from pcf.data.clean import standard
from pcf.data.clean.depth_charts import (
    daily_depth_rows,
    depth_labels,
    game_day_cutoffs,
    weekly_depth_rows,
)
from pcf.data.clean.players import players_on_play, plays_with_players
from pcf.data.clean.slots import position_groups, slot_labels

from .conftest import fixture


def _players(rows):
    df = pl.DataFrame(rows, schema=["week", "gsis_id"], orient="row")
    return df.with_columns(
        game_id=pl.lit("g") + pl.col("week").cast(pl.String),
        play_id=pl.lit(1),
        season=pl.lit(2024),
        season_type=pl.lit("REG"),
        side=pl.lit("offense"),
        team=pl.lit("KC"),
        slot=pl.int_range(1, pl.len() + 1).over("week"),
    )


def _labels(rows):
    df = pl.DataFrame(rows, schema=["week", "gsis_id", "position_label"], orient="row")
    return df.with_columns(
        season=pl.lit(2024, pl.Int32),
        week=pl.col("week").cast(pl.Int32),
        team=pl.lit("KC"),
        position=pl.col("position_label").str.replace(r"\d+$", ""),
    )


def _rosters(rows):
    df = pl.DataFrame(rows, schema=["week", "gsis_id", "depth_chart_position"], orient="row")
    return df.with_columns(season=pl.lit(2024), team=pl.lit("KC"), position=pl.lit(None, pl.String))


def _by_player(out, week):
    week = out.filter(pl.col("week") == week)
    return dict(
        zip(
            week["gsis_id"],
            zip(week["position_label"], week["label_source"], strict=True),
            strict=True,
        )
    )


def test_fallback_chain():
    labels = _labels(
        [
            (1, "wr_a", "WR1"),
            (1, "wr_b", "WR2"),
            (2, "wr_a", "WR1"),
            (2, "wr_c", "WR2"),  # wr_b's old label is taken this week
            (2, "lt", "LT1"),
            (2, "rt", "RT1"),
            (2, "rt2", "RT2"),
        ]
    )
    players = _players(
        [(2, "wr_a"), (2, "wr_b"), (2, "wr_c"), (2, "new_wr"), (2, "new_t"), (2, "ghost")]
    )
    rosters = _rosters([(2, "new_wr", "WR"), (2, "new_t", "T"), (2, "wr_b", "WR")])
    got = _by_player(slot_labels(players, labels, rosters), 2)
    assert got == {
        "wr_a": ("WR1", "week"),
        "wr_c": ("WR2", "week"),
        "wr_b": ("WR3", "earlier_week"),  # next free number at their earlier position
        "new_wr": ("WR4", "roster"),
        "new_t": ("T3", "roster"),  # past the deepest tackle on either side (RT2)
        "ghost": ("unknown", "none"),
    }


def test_an_earlier_label_is_kept_when_free():
    labels = _labels([(1, "wr_b", "WR2"), (2, "wr_a", "WR1")])
    players = _players([(2, "wr_a"), (2, "wr_b")])
    got = _by_player(slot_labels(players, labels, _rosters([(2, "x", "WR")])), 2)
    assert got["wr_b"] == ("WR2", "earlier_week")


def test_position_groups_come_from_the_labels():
    groups = position_groups(["QB1", "LT1", "T3", "WR2", "S4", "CB1", "special1", "unknown"])
    assert groups["ol"] == ["LT1", "T3"]
    assert groups["offense"] == ["QB1", "WR2", "LT1", "T3"]
    assert groups["defense"] == ["CB1", "S4"]
    assert groups["special"] == ["special1"]
    with pytest.raises(ValueError, match="no position group"):
        position_groups(["XX1"])


def _check_expectations(out: pl.DataFrame, plays: int) -> None:
    """What football says must hold on any game (CONVENTIONS.md expectation tests)."""
    assert out.filter(pl.col("label_source") == "none").height == 0
    sides = out.group_by("game_id", "play_id", "side").agg(
        n=pl.len(), labels=pl.col("position_label").n_unique(), ids=pl.col("gsis_id").n_unique()
    )
    assert (sides["labels"] == sides["n"]).all()  # no two players share a label
    assert (sides["ids"] == sides["n"]).all()  # no player twice on one side
    assert (sides["n"] == 11).mean() >= 0.99
    assert sides.height == 2 * plays
    qbs = (
        out.filter(pl.col("side") == "offense")
        .group_by("game_id", "play_id")
        .agg(qb=(pl.col("position") == "QB").sum())
    )
    # At least one QB: two is real football (Taysom Hill, 2018 Lamar Jackson packages).
    assert (qbs["qb"] >= 1).mean() >= 0.99
    assert (out["position"] == "special").mean() < 0.005
    assert set(position_groups(out["position_label"]))  # every label has a group


def test_two_2024_games_meet_the_expectations():
    plays = plays_with_players(fixture("pbp_2024"), fixture("participation_2024"))
    players = players_on_play(plays)
    labels = depth_labels(weekly_depth_rows(fixture("depth_charts_2024")))
    rosters = standard.weekly_rosters(
        fixture("weekly_rosters_2024").with_columns(status=pl.lit("ACT"))
    )
    out = slot_labels(players, labels, rosters)
    _check_expectations(out, players.select("game_id", "play_id").n_unique())
    assert out.height == players.height


def test_a_2025_game_from_daily_charts_meets_the_expectations():
    plays = plays_with_players(fixture("pbp_2025"), fixture("participation_2025"))
    players = players_on_play(plays)
    cutoffs = game_day_cutoffs(fixture("schedules_2025"))
    labels = depth_labels(daily_depth_rows(fixture("depth_charts_2025"), cutoffs))
    rosters = standard.weekly_rosters(
        fixture("weekly_rosters_2025").with_columns(status=pl.lit("ACT"))
    )
    out = slot_labels(players, labels, rosters)
    _check_expectations(out, players.select("game_id", "play_id").n_unique())
    assert (out["label_source"] == "week").mean() > 0.95
