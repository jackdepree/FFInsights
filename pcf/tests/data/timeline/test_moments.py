"""Prediction moments (CEO decision 1C): the weekly runs, and each game at its latest allowed run
before kickoff."""

from datetime import date

import polars as pl
import pytest

from pcf.data.timeline import calendar
from pcf.data.timeline.moments import (
    allowed,
    event_moments,
    game_moments,
    runs,
    season_ends,
    season_moments,
)

from .toy import OFFSEASON, schedule, utc

c = pl.col
ET = "America/New_York"

# 2024 week 1-2 style: Thursday, Friday (Brazil), Sunday and Monday games, then week 2.
WEEKS = schedule(
    [
        ("2025_01_A", 2025, 1, "REG", "2025-09-04", "20:20"),
        ("2025_01_B", 2025, 1, "REG", "2025-09-08", "20:15"),
        ("2025_02_A", 2025, 2, "REG", "2025-09-11", "20:15"),
        ("2025_02_B", 2025, 2, "REG", "2025-09-14", "13:00"),
        ("2025_03_A", 2025, 3, "REG", "2025-09-21", "13:00"),
        ("2025_22_A", 2025, 22, "SB", "2026-02-08", "18:30"),
    ]
)


@pytest.fixture(scope="module")
def cal():
    return calendar(WEEKS, OFFSEASON)


def local(moment) -> str:
    return moment.astimezone(__import__("zoneinfo").ZoneInfo(ET)).strftime("%a %H:%M")


def test_runs_fall_on_their_days_inside_each_week(cal):
    r = runs(cal).filter((c("season") == 2025) & (c("week") == 2))
    assert [(n, local(at)) for n, at in r.select("run", "at").iter_rows()] == [
        ("tuesday", "Tue 10:00"),
        ("wednesday", "Wed 16:00"),
        ("saturday", "Sat 12:00"),
    ]


def test_each_game_gets_the_latest_allowed_run_before_kickoff(cal):
    def moments(run):
        m = game_moments(cal, run).filter(c("season") == 2025, c("week") <= 2)
        return {g: local(at) for g, at in m.select("game_id", "moment").iter_rows()}

    assert moments("tuesday") == {g: "Tue 10:00" for g in moments("tuesday")}
    sat = moments("saturday")
    assert sat["2025_01_A"] == "Wed 16:00"  # Thursday night: never Saturday's run
    assert sat["2025_01_B"] == "Sat 12:00"  # Monday night
    assert sat["2025_02_A"] == "Wed 16:00"
    assert sat["2025_02_B"] == "Sat 12:00"
    assert moments("wednesday")["2025_02_B"] == "Wed 16:00"


def test_no_moment_is_at_or_after_kickoff(cal):
    for run in ("tuesday", "wednesday", "saturday"):
        m = game_moments(cal, run)
        assert m.filter(c("moment") >= c("kickoff")).is_empty()


def test_a_benchmark_is_predicted_at_kickoff(cal):
    m = game_moments(cal, "kickoff")
    assert m.height == cal.games.height
    assert (m["moment"] == m["kickoff"]).all() and not m["fallback"].any()


def test_a_week_that_starts_after_its_runs_falls_back_to_10_am_on_its_first_day():
    # Week 1 ends on a Wednesday, so week 2 starts Thursday: its Tuesday run is after its game.
    rows = schedule(
        [
            ("2020_01_A", 2020, 1, "REG", "2020-09-13", "13:00"),
            ("2020_01_B", 2020, 1, "REG", "2020-09-16", "20:00"),
            ("2020_02_A", 2020, 2, "REG", "2020-09-20", "13:00"),
            ("2020_22_A", 2020, 22, "SB", "2021-02-07", "18:30"),
        ]
    )
    off = OFFSEASON.with_columns(season=pl.lit(2020, pl.Int32))
    m = game_moments(calendar(rows, off), "tuesday").filter(c("game_id") == "2020_02_A")
    assert m["fallback"][0]
    assert local(m["moment"][0]) == "Thu 10:00"


def test_the_runs_are_ordered():
    assert allowed("tuesday") == ["tuesday"]
    assert allowed("saturday") == ["tuesday", "wednesday", "saturday"]
    with pytest.raises(ValueError):
        allowed("sunday")


def test_season_event_and_end_moments(cal):
    assert local(season_moments(cal)["moment"][0]) == "Tue 10:00"
    draft = event_moments(cal, "draft").filter(c("season") == 2025)["moment"][0]
    assert draft.date() == date(2025, 4, 24)
    assert season_ends(cal)[2025] == utc(2026, 2, 9, 5)
