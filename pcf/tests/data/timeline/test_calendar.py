from datetime import date, datetime

import polars as pl
import pytest

from pcf.data.timeline import calendar, games, offseason_dates, phase_at, weeks
from pcf.data.timeline.calendar import OFFSEASON_COLUMNS, missing_offseason_row

from .toy import OFFSEASON, SEASON, schedule, utc


def test_kickoff_is_eastern_time_in_utc_across_daylight_saving():
    g = games(SEASON)
    kick = dict(zip(g["game_id"], g["kickoff"], strict=True))
    assert kick["2025_01_A"] == utc(2025, 9, 5, 0, 20)  # 8:20 PM EDT
    assert kick["2025_22_A"] == utc(2026, 2, 8, 23, 30)  # 6:30 PM EST


def test_a_game_with_no_time_gets_1_pm_eastern():
    g = games(schedule([("1999_01_A", 1999, 1, "REG", "1999-09-12", None)]))
    assert g["kickoff"].item() == utc(1999, 9, 12, 17)


def test_weeks_are_contiguous_and_end_after_their_last_game_day():
    w = weeks(games(SEASON))
    assert w["week"].to_list() == [1, 2, 19, 22]
    # Week 1 starts two days before the Thursday opener and ends the night after Monday's game.
    assert w["start"][0] == utc(2025, 9, 2, 4)
    assert w["end"][0] == utc(2025, 9, 9, 4)
    assert (w["start"].shift(-1).drop_nulls() == w["end"].head(-1)).all()
    assert w["phase"].to_list() == ["regular_season"] * 2 + ["postseason"] * 2
    assert w["super_bowl"].to_list() == [False, False, False, True]


def test_phases_follow_the_calendar_in_order():
    cal = calendar(SEASON, OFFSEASON)
    p = cal.phases
    assert p["phase"].to_list() == [
        "free_agency",
        "draft",
        "after_draft",
        "preseason",
        "regular_season",
        "postseason",
        "offseason",
        "free_agency",
        "draft",
        "after_draft",
    ]
    assert p["season"].to_list()[-4:] == [2026] * 4  # the offseason belongs to the next season
    assert (p["start"].shift(-1).drop_nulls() == p["end"].drop_nulls()).all()
    assert p["start"][0] == utc(2025, 3, 12, 20)  # 4 PM EDT


def test_a_year_with_free_agency_after_the_draft_still_works():
    lockout = OFFSEASON.with_columns(
        league_year_start=pl.when(pl.col("season") == 2025)
        .then(date(2025, 7, 25))
        .otherwise("league_year_start")
    )
    p = calendar(SEASON, lockout).phases.filter(pl.col("season") == 2025)
    assert p["phase"].to_list()[:4] == ["draft", "after_draft", "free_agency", "preseason"]


def test_no_next_offseason_until_the_super_bowl_is_scheduled():
    no_sb = SEASON.filter(pl.col("game_type") != "SB")
    p = calendar(no_sb, OFFSEASON.filter(pl.col("season") == 2025)).phases
    assert p.filter(pl.col("season") == 2026).height == 0
    assert p["end"][-1] is None


def test_phase_at():
    cal = calendar(SEASON, OFFSEASON)
    assert phase_at(cal, utc(2025, 9, 10, 12)) == {
        "season": 2025,
        "phase": "regular_season",
        "week": 2,
    }
    assert phase_at(cal, utc(2025, 4, 25, 12)) == {"season": 2025, "phase": "draft", "week": None}
    assert phase_at(cal, utc(2026, 2, 20)) == {"season": 2026, "phase": "offseason", "week": None}
    # Week windows are contiguous: the toy season's gap after week 2 belongs to the next week.
    assert phase_at(cal, utc(2025, 12, 1))["week"] == 19
    with pytest.raises(ValueError, match="before"):
        phase_at(cal, utc(2020, 1, 1))
    with pytest.raises(ValueError, match="timezone"):
        phase_at(cal, datetime(2025, 9, 10))


def test_deleting_later_games_changes_no_earlier_week():
    full = weeks(games(SEASON))
    early = weeks(games(SEASON.filter(pl.col("week") <= 2)))
    assert early.equals(full.filter(pl.col("week") <= 2))


def test_the_offseason_dates_file():
    d = offseason_dates()
    assert d["season"].to_list() == list(range(2002, d["season"].max() + 1))
    assert d["season"].max() >= 2026
    assert set(OFFSEASON_COLUMNS) <= set(d.columns)
    assert d["draft_start"].null_count() == 0
    assert (d["draft_start"] <= d["draft_end"]).all()
    assert (d["combine_end"] < d["draft_start"]).all()
    assert (d["combine_start"] <= d["combine_end"]).all()
    assert (d["draft_end"] < d["preseason_start"]).all()
    # Free agency opens before the draft, except the 2011 lockout.
    before = d.filter(pl.col("season") != 2011)
    assert (before["league_year_start"] < before["draft_start"]).all()


def test_a_missing_offseason_row_is_due_from_february():
    d = pl.DataFrame({"season": [2025, 2026]})
    assert missing_offseason_row(d, date(2027, 1, 31)) is None
    assert missing_offseason_row(d, date(2027, 2, 1)) == 2027


def test_next_years_offseason_row_is_there_when_due():
    due = missing_offseason_row(offseason_dates())
    assert due is None, (
        f"add the {due} row to src/pcf/data/timeline/offseason_dates.csv (league year, combine, "
        "draft, first preseason game)"
    )
