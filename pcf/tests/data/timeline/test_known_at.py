from datetime import date, datetime, timedelta

import polars as pl
import pytest

from pcf.data.sources.nflverse import DATASETS
from pcf.data.timeline import RULES, calendar, check_known_at, known_at
from pcf.data.timeline.known_at import _injury_fallback

from .toy import OFFSEASON, SEASON, schedule, utc

CAL = calendar(SEASON.with_columns(old_game_id=pl.col("game_id") + "_old"), OFFSEASON)
WEEK1_KICK = utc(2025, 9, 5, 0, 20)


def test_every_dataset_in_the_catalog_has_a_rule():
    assert set(DATASETS) <= set(RULES)


def test_game_results_are_known_a_day_after_kickoff():
    out = known_at("player_stats", pl.DataFrame({"game_id": ["2025_01_A"]}), CAL)
    assert out["known_at"].item() == WEEK1_KICK + timedelta(days=1)
    with pytest.raises(ValueError, match="not in the schedule"):
        known_at("pbp", pl.DataFrame({"game_id": ["1999_01_X"]}), CAL)


def test_ftn_two_weeks_after_and_officials_two_days_before():
    ftn = known_at("ftn_charting", pl.DataFrame({"nflverse_game_id": ["2025_01_A"]}), CAL)
    assert ftn["known_at"].item() == WEEK1_KICK + timedelta(days=14)
    off = pl.DataFrame(
        {"game_id": ["2025_01_A_old", "moved"], "season": [2025] * 2, "week": [1] * 2}
    )
    out = known_at("officials", off, CAL)
    # A moved game's old id isn't in the schedule: its week's last kickoff.
    assert out["known_at"].to_list() == [
        WEEK1_KICK - timedelta(days=2),
        utc(2025, 9, 9, 0, 15) - timedelta(days=2),
    ]


def test_participation_is_known_after_the_super_bowl():
    out = known_at("participation", pl.DataFrame({"nflverse_game_id": ["2025_01_A"]}), CAL)
    assert out["known_at"].item() == utc(2026, 2, 9, 23, 30)
    no_sb = calendar(SEASON.filter(pl.col("game_type") != "SB"), OFFSEASON)
    with pytest.raises(ValueError, match="Super Bowl"):
        known_at("participation", pl.DataFrame({"nflverse_game_id": ["2025_01_A"]}), no_sb)


def _injury_rows(season: int, week: int, team: str, game_type: str = "REG") -> pl.DataFrame:
    return pl.DataFrame(
        {"season": [season], "week": [week], "game_type": [game_type], "team": [team]}
    ).with_columns(date_modified=pl.lit(None, pl.Datetime("us", "UTC")))


def test_injuries_prefer_date_modified():
    df = _injury_rows(2025, 1, "KC").with_columns(
        date_modified=pl.lit(utc(2025, 9, 3, 20), pl.Datetime("us", "UTC"))
    )
    assert known_at("injuries", df, CAL)["known_at"].item() == utc(2025, 9, 3, 20)


def test_injury_teams_are_matched_in_pcf_codes():
    # Sunday 2025-09-14: known at noon Eastern on Saturday, seen by the Saturday run
    out = known_at("injuries", _injury_rows(2025, 2, "KAN"), CAL)
    assert out["known_at"].item() == utc(2025, 9, 13, 16)


@pytest.mark.parametrize(
    ("kickoff", "known"),
    [
        (utc(2025, 9, 14, 17), utc(2025, 9, 13, 16)),  # Sunday
        (utc(2025, 9, 15, 23), utc(2025, 9, 14, 16)),  # Monday
        (utc(2025, 12, 20, 18), utc(2025, 12, 19, 17)),  # Saturday
        # Thursday night (Eastern, so the next day in UTC): noon that Thursday
        (utc(2025, 9, 12, 0, 15), utc(2025, 9, 11, 16)),
        (utc(2025, 11, 28, 20), utc(2025, 11, 28, 17)),  # Friday
        (utc(2024, 12, 25, 18), utc(2024, 12, 25, 17)),  # Wednesday
        # Thanksgiving's 12:30 game: an hour before kickoff, since noon is too close
        (utc(2025, 11, 27, 17, 30), utc(2025, 11, 27, 16, 30)),
    ],
)
def test_injury_fallback_follows_the_report_day(kickoff, known):
    got = pl.select(_injury_fallback(pl.lit(kickoff, pl.Datetime("us", "UTC")))).item()
    assert got == known


def test_injury_fallback_is_seen_by_the_saturday_run_only_for_sunday_games():
    saturday_run = utc(2025, 9, 13, 16)
    sunday = pl.lit(utc(2025, 9, 14, 17), pl.Datetime("us", "UTC"))
    monday = pl.lit(utc(2025, 9, 15, 23), pl.Datetime("us", "UTC"))
    assert pl.select(_injury_fallback(sunday)).item() <= saturday_run
    assert pl.select(_injury_fallback(monday)).item() > saturday_run


def test_depth_charts_use_dt_or_the_start_of_their_week():
    df = pl.DataFrame(
        {
            "season": [2025, 2025, None],
            "week": [2, None, None],
            "dt": [None, None, "2025-09-06T07:00:00Z"],
        },
        schema_overrides={"season": pl.Int32, "week": pl.Int32},
    )
    out = known_at("depth_charts", df, CAL)
    assert out["known_at"].to_list() == [
        utc(2025, 9, 9, 4),  # week 2 starts the night after Monday's game
        utc(2026, 1, 11, 5),  # no week: the Super Bowl bye, so the Super Bowl week's start
        utc(2025, 9, 6, 7),
    ]


def test_weekly_rosters_are_known_at_the_start_of_the_week():
    out = known_at(
        "weekly_rosters", pl.DataFrame({"season": [2025], "week": [1], "team": ["KC"]}), CAL
    )
    assert out["known_at"].item() == utc(2025, 9, 2, 4)


def test_roster_status_is_known_an_hour_before_the_teams_kickoff():
    df = pl.DataFrame(
        {"season": [2025, 2025, 2025], "week": [1, 1, 2], "team": ["KC", "NYG", "DAL"]}
    )
    out = known_at("weekly_rosters", df, CAL)
    assert out["status_known_at"].to_list() == [
        WEEK1_KICK - timedelta(hours=1),
        utc(2025, 9, 9, 0, 15) - timedelta(hours=1),  # Monday night, 8:15 PM Eastern
        None,  # DAL has no game in week 2
    ]


def test_pfr_weekly_stats_use_the_start_of_the_week_after_next():
    three = schedule(
        [
            ("2025_01_A", 2025, 1, "REG", "2025-09-07", "13:00"),
            ("2025_02_A", 2025, 2, "REG", "2025-09-14", "13:00"),
            ("2025_03_A", 2025, 3, "REG", "2025-09-21", "13:00"),
        ]
    )
    out = known_at(
        "pfr_week_pass", pl.DataFrame({"season": [2025], "week": [1]}), calendar(three, OFFSEASON)
    )
    assert out["known_at"].item() == utc(2025, 9, 15, 4)  # week 3 starts the night after week 2


def test_ngs_weeks_and_season_totals():
    df = pl.DataFrame({"season": [2025, 2025, 2025], "week": [1, 23, 0]})
    out = known_at("ngs_passing", df, CAL)
    assert out["known_at"].to_list() == [
        utc(2025, 9, 10, 4),  # the day after week 1 ends
        utc(2026, 2, 10, 5),  # NGS's week 23 is the Super Bowl (week 22 here)
        utc(2025, 9, 16, 4),  # week 0: the day after the regular season ends
    ]
    unfinished = calendar(SEASON.filter(pl.col("game_type") == "REG"), OFFSEASON)
    with pytest.raises(ValueError, match="fetched_at"):
        known_at("ngs_passing", df.filter(pl.col("week") == 0), unfinished)
    fetched = utc(2025, 10, 1)
    out = known_at("ngs_passing", df.filter(pl.col("week") == 0), unfinished, fetched_at=fetched)
    assert out["known_at"].item() == fetched
    # Weekly rows of an unfinished season don't need a fetch time.
    weekly = known_at("ngs_passing", df.filter(pl.col("week") == 1), unfinished)
    assert weekly["known_at"].item() == utc(2025, 9, 10, 4)


def test_pfr_weekly_stats_wait_for_the_week_after_next():
    df = pl.DataFrame({"season": [2025, 2025], "week": [1, 22]})
    out = known_at("pfr_week_pass", df, CAL)
    assert out["known_at"].to_list() == [
        utc(2025, 9, 17, 4),  # the toy has no week 3: week 1's end + 8 days
        utc(2026, 2, 17, 5),  # the Super Bowl: its week's end + 8 days
    ]


def test_offseason_sources():
    out = known_at("combine", pl.DataFrame({"season": [2025, 1999]}), CAL)
    # No combine dates: the first day of the draft. A year not in the file: June 1.
    assert out["known_at"].to_list() == [utc(2025, 4, 24, 4), utc(1999, 6, 1, 4)]
    picks = known_at("draft_picks", pl.DataFrame({"season": [2025]}), CAL)
    assert picks["known_at"].item() == utc(2025, 4, 27, 4)
    trades = known_at("trades", pl.DataFrame({"trade_date": [date(2025, 3, 12)]}), CAL)
    assert trades["known_at"].item() == utc(2025, 3, 13, 4)
    ecr = known_at("ecr_week", pl.DataFrame({"scrape_date": ["2025-12-31"]}), CAL)
    assert ecr["known_at"].item() == utc(2026, 1, 1, 5)


def test_schedules_have_three_known_at_columns():
    out = known_at("schedules", SEASON.head(1), CAL)
    row = out.row(0, named=True)
    assert row["facts_known_at"] == utc(2025, 9, 2, 4)
    assert row["lines_known_at"] == WEEK1_KICK
    assert row["known_at"] == WEEK1_KICK + timedelta(days=1)


def test_playoff_matchups_are_known_at_the_start_of_their_week():
    out = known_at("schedules", SEASON.filter(pl.col("game_type") != "REG"), CAL)
    # Wild card week starts the midnight after week 2's last game day (the toy has no week 3+).
    assert out["facts_known_at"].to_list() == [utc(2025, 9, 15, 4), utc(2026, 1, 11, 5)]


def test_state_files_need_their_fetch_time():
    with pytest.raises(ValueError, match="fetched_at"):
        known_at("players", pl.DataFrame({"gsis_id": ["x"]}), CAL)
    out = known_at("players", pl.DataFrame({"gsis_id": ["x"]}), CAL, fetched_at=utc(2026, 1, 1))
    assert out["known_at"].item() == utc(2026, 1, 1)


def test_deleting_later_games_changes_no_earlier_known_at():
    df = pl.DataFrame({"season": [2025, 2025], "week": [1, 2], "team": ["KC", "KC"]})
    full = known_at("weekly_rosters", df, CAL)
    early = calendar(SEASON.filter(pl.col("week") <= 2), OFFSEASON)
    assert known_at("weekly_rosters", df, early)["known_at"].equals(full["known_at"])


def test_check_known_at_catches_each_problem():
    with pytest.raises(ValueError, match="no known_at"):
        check_known_at(pl.DataFrame({"x": [1]}))
    with pytest.raises(ValueError, match="UTC"):
        check_known_at(pl.DataFrame({"known_at": [datetime(2025, 1, 1)]}))
    with pytest.raises(ValueError, match="missing"):
        check_known_at(pl.DataFrame({"known_at": [utc(2025, 1, 1), None]}))
    early = pl.DataFrame({"known_at": [utc(2025, 1, 1)], "kickoff": [utc(2025, 1, 2)]})
    with pytest.raises(ValueError, match="before their kickoff"):
        check_known_at(early, not_before="kickoff")
    with pytest.raises(ValueError, match="no known-at rule"):
        known_at("nope", pl.DataFrame(), CAL)
