from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.data.clean.depth_charts import (
    daily_depth_rows,
    depth_labels,
    game_day_cutoffs,
    weekly_depth_rows,
)

from .conftest import fixture


def _weekly(rows):
    cols = ["season", "club_code", "week", "formation", "gsis_id", "position", "depth_position"]
    df = pl.DataFrame(rows, schema=[*cols, "depth_team"], orient="row")
    return df.with_columns(pl.col("week").cast(pl.Int32))


def test_weekly_positions_are_cleaned_as_before_and_teams_recoded():
    rows = weekly_depth_rows(
        _weekly(
            [
                (2017, "OAK", 1, "Offense", "a", "T", "LT", "1"),
                (2017, "OAK", 1, "Offense", "b", "LOT", None, "2"),
                (2017, "OAK", 1, "Defense", "c", "LDE", None, "1"),
                (2017, "OAK", 1, "Defense", "d", "LB", None, "1"),
                (2017, "OAK", 1, "Defense", "e", "DB", None, "2"),
                (2017, "OAK", 1, "Offense", "f", "K", None, "1"),
                (2017, "OAK", None, "Offense", "g", "QB", None, "1"),
                (2017, "OAK", 1, "Special Teams", "h", "PR", None, "1"),
            ]
        )
    )
    got = dict(zip(rows["gsis_id"], rows["position"], strict=True))
    assert got == {
        "a": "LT",
        "b": "LT",
        "c": "DE",
        "d": "MLB",
        "e": "CB",
        "f": "special",
        "g": "QB",
    }
    assert rows["team"].unique().to_list() == ["LV"]
    assert rows.filter(pl.col("gsis_id") == "g")["week"].item() == 23  # Super Bowl bye


def test_a_player_listed_twice_keeps_the_better_depth():
    rows = weekly_depth_rows(
        _weekly(
            [
                (2024, "KC", 1, "Offense", "a", "WR", "WR", "2"),
                (2024, "KC", 1, "Offense", "a", "TE", "TE", "1"),
            ]
        )
    )
    assert rows.select("position", "depth").row(0) == ("TE", 1)


def _rows(rows):
    return pl.DataFrame(
        rows, schema=["season", "week", "team", "gsis_id", "position", "depth"], orient="row"
    )


def test_labels_rank_by_season_average_depth_so_far():
    rows = _rows(
        [
            (2024, 1, "KC", "vet", "QB", 1),
            (2024, 1, "KC", "kid", "QB", 2),
            (2024, 2, "KC", "vet", "QB", 2),  # one week as backup
            (2024, 2, "KC", "kid", "QB", 1),
            (2024, 3, "KC", "vet", "QB", 2),
            (2024, 3, "KC", "kid", "QB", 1),
            (2025, 1, "KC", "vet", "QB", 2),  # a new season starts from scratch
            (2025, 1, "KC", "kid", "QB", 1),
        ]
    )
    labels = depth_labels(rows).select("season", "week", "gsis_id", "position_label")
    qb1 = labels.filter(pl.col("position_label") == "QB1").sort("season", "week")
    # Week 2: both average 1.5; the tie goes to this week's depth.
    assert qb1["gsis_id"].to_list() == ["vet", "kid", "kid", "kid"]


def test_later_weeks_never_change_earlier_labels():
    rows = weekly_depth_rows(fixture("depth_charts_2024"))
    full = depth_labels(rows).filter(pl.col("week") <= 5)
    cut = depth_labels(rows.filter(pl.col("week") <= 5))
    assert full.equals(cut)


def _daily(rows):
    cols = ["dt", "team", "gsis_id", "pos_grp", "pos_abb", "pos_slot", "pos_rank"]
    return pl.DataFrame(rows, schema=cols, orient="row")


def _cutoffs(rows):
    return pl.DataFrame(rows, schema=["season", "week", "team", "cutoff"], orient="row")


def test_daily_charts_use_the_latest_snapshot_before_each_cutoff():
    daily = _daily(
        [
            ("2025-09-01T07:00:00Z", "KC", "old_qb", "3WR 1TE", "QB", 9, 1),
            ("2025-09-06T07:00:00Z", "KC", "new_qb", "3WR 1TE", "QB", 9, 1),
            ("2025-09-08T07:00:00Z", "KC", "after", "3WR 1TE", "QB", 9, 1),
        ]
    )
    cut = _cutoffs([(2025, 1, "KC", datetime(2025, 9, 7, 4, tzinfo=UTC))])
    assert daily_depth_rows(daily, cut)["gsis_id"].to_list() == ["new_qb"]


def test_daily_depth_is_the_rank_within_each_wr_spot():
    daily = _daily(
        [
            ("2025-09-06T07:00:00Z", "KC", f"wr{rank}", "3WR 1TE", "WR", slot, rank)
            for slot, rank in [(1, 1), (2, 2), (8, 3), (1, 4), (2, 5)]
        ]
        + [("2025-09-06T07:00:00Z", "KC", "lde", "Base 4-3 D", "LDE", 1, 1)]
    )
    cut = _cutoffs([(2025, 1, "KC", datetime(2025, 9, 7, tzinfo=UTC))])
    rows = daily_depth_rows(daily, cut)
    depth = dict(zip(rows["gsis_id"], rows["depth"], strict=True))
    assert depth == {"wr1": 1, "wr2": 1, "wr3": 1, "wr4": 2, "wr5": 2, "lde": 1}
    assert rows.filter(pl.col("gsis_id") == "lde")["position"].item() == "DE"


def test_only_the_next_future_game_gets_todays_chart():
    daily = _daily([("2025-09-06T07:00:00Z", "KC", "qb", "3WR 1TE", "QB", 9, 1)])
    cut = _cutoffs(
        [
            (2025, 1, "KC", datetime(2025, 9, 7, tzinfo=UTC)),
            (2025, 2, "KC", datetime(2025, 9, 14, tzinfo=UTC)),
        ]
    )
    assert daily_depth_rows(daily, cut)["week"].to_list() == [1]


def test_daily_charts_refuse_a_position_pcf_does_not_map():
    daily = _daily([("2025-09-06T07:00:00Z", "KC", "x", "3WR 1TE", "SLOT", 1, 1)])
    cut = _cutoffs([(2025, 1, "KC", datetime(2025, 9, 7, tzinfo=UTC))])
    with pytest.raises(ValueError, match="SLOT"):
        daily_depth_rows(daily, cut)


def test_game_day_cutoff_is_midnight_in_new_york():
    sched = pl.DataFrame(
        {
            "season": [2025],
            "week": [1],
            "home_team": ["KC"],
            "away_team": ["OAK"],
            "gameday": ["2025-09-07"],
        }
    )
    cut = game_day_cutoffs(sched)
    assert cut["cutoff"].to_list() == [datetime(2025, 9, 7, 4, tzinfo=UTC)] * 2
    assert sorted(cut["team"]) == ["KC", "OAK"]  # recoding happens in standard.schedules
