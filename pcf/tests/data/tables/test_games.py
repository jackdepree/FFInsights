from datetime import timedelta

import polars as pl

from pcf.data.schemas import check_parts
from pcf.data.tables.games import game_parts, team_game_parts

from .toy import KICK, cal, schedules, utc

WEEK1_START = utc(2025, 9, 5, 4)  # week 1 starts two days before its first game day


def test_game_parts_are_known_at_release_kickoff_and_the_day_after():
    parts = game_parts(schedules(), cal())
    check_parts(parts, "game")
    sched = parts["schedule"].sort("week")
    assert sched["known_at"].to_list()[0] == WEEK1_START
    # The Super Bowl matchup is known only when its week starts, not at week 1.
    assert sched["known_at"].to_list()[1] > utc(2025, 9, 8)
    assert parts["pregame"].sort("game_id")["known_at"].to_list()[0] == KICK
    # Only the played game has a result, known the day after.
    assert parts["result"]["known_at"].to_list() == [KICK + timedelta(days=1)]
    assert "home_score" not in parts["schedule"].columns


def test_team_game_has_two_rows_per_game_with_team_spreads_and_margins():
    parts = team_game_parts(schedules(), cal())
    check_parts(parts, "team_game")
    assert parts["schedule"].height == 4
    week1 = pl.col("game_id") == "2025_01_BUF_KC"
    pre = parts["pregame"].filter(week1).sort("team")
    assert pre.select("team", "spread", "moneyline").rows() == [
        ("BUF", 3.5, 150),
        ("KC", -3.5, -180),
    ]
    res = parts["result"].sort("team")
    assert res.select("team", "points_for", "points_against", "margin").rows() == [
        ("BUF", 20, 27, -7),
        ("KC", 27, 20, 7),
    ]
    spine = parts["schedule"].filter(week1).sort("team")
    assert spine.select("team", "opponent", "home", "rest").rows() == [
        ("BUF", "KC", False, 7),
        ("KC", "BUF", True, 7),
    ]


def test_team_stats_join_the_spine_in_pcf_team_codes():
    stats = pl.DataFrame(
        {
            "game_id": ["2025_01_BUF_KC", "2025_01_BUF_KC"],
            "season": [2025, 2025],
            "week": [1, 1],
            "season_type": ["REG", "REG"],
            "team": ["KC", "BUF"],
            "opponent_team": ["BUF", "KC"],
            "passing_yards": [250, 210],
        }
    )
    parts = team_game_parts(schedules(), cal(), stats)
    check_parts(parts, "team_game")
    assert parts["stats"]["known_at"].unique().to_list() == [KICK + timedelta(days=1)]
    assert set(parts["stats"].columns) == {"game_id", "team", "season", "passing_yards", "known_at"}
