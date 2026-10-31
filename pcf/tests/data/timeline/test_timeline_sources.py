"""The calendar and every known-at rule on the full local raw copy."""

from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.data.clean import standard
from pcf.data.sources.nflverse import DATASETS, scan
from pcf.data.timeline import calendar, known_at, offseason_dates, phase_at

pytestmark = pytest.mark.local_data

# Big files: only the columns their rule reads.
COLUMNS = {
    "pbp": ["game_id"],
    "participation": ["nflverse_game_id"],
    "ftn_charting": ["nflverse_game_id"],
}


@pytest.fixture(scope="module")
def cal():
    return calendar(standard.schedules(scan("schedules").collect()))


def test_every_game_from_2000_has_a_published_kickoff_time():
    s = scan("schedules").filter(pl.col("season") >= 2000).collect()
    assert s["gametime"].null_count() == 0


def test_the_first_play_comes_within_30_minutes_of_kickoff(cal):
    first = (
        scan("pbp", range(2011, 2026))
        .select("game_id", "time_of_day")
        .drop_nulls()
        .group_by("game_id")
        .agg(first=pl.col("time_of_day").min().str.to_datetime(time_zone="UTC"))
        .collect()
    )
    late = first.join(cal.games, on="game_id").select(
        minutes=(pl.col("first") - pl.col("kickoff")).dt.total_minutes()
    )["minutes"]
    assert late.len() > 4000
    assert late.is_between(-5, 30).mean() >= 0.99  # timeline#F1, #F2


def test_every_game_falls_in_its_own_week(cal):
    g = cal.games.join(cal.weeks, on=["season", "week"])
    assert g.height == cal.games.height
    assert ((g["kickoff"] >= g["start"]) & (g["kickoff"] < g["end"])).all()
    w = cal.weeks.sort("start")
    assert (w["start"].shift(-1).drop_nulls() >= w["end"].head(-1)).all()  # no overlap


def test_phases_are_in_time_order(cal):
    p = cal.phases
    assert p["start"].is_sorted()
    assert phase_at(cal, datetime(2026, 10, 31, 18, tzinfo=UTC)) == {
        "season": 2026,
        "phase": "regular_season",
        "week": 8,
    }


def test_each_draft_holds_its_years_busiest_pick_trading_day():
    t = scan("trades").collect().unique("trade_id")
    busiest = (
        t.filter(pl.col("pick_season") == pl.col("trade_date").dt.year())
        .group_by(season=pl.col("trade_date").dt.year().cast(pl.Int32), day="trade_date")
        .len()
        .sort("season", "len", "day", descending=[False, True, False])
        .group_by("season", maintain_order=True)
        .head(1)
        .filter(pl.col("season") <= 2025)  # the trades file stops before the 2026 draft (F7)
    )
    j = busiest.join(offseason_dates(), on="season")
    assert j.height == 24
    assert j["day"].is_between(j["draft_start"], j["draft_end"]).all()


@pytest.mark.parametrize("dataset", sorted(DATASETS))
def test_every_rule_runs_on_its_full_dataset(dataset, cal):
    lf = scan(dataset)
    if dataset in COLUMNS:
        lf = lf.select(COLUMNS[dataset])
    out = known_at(dataset, lf.collect(), cal, fetched_at=datetime.now(UTC))
    assert out.height > 0


def test_no_injury_report_is_known_before_it_was_modified_or_after_kickoff(cal):
    df = standard.injuries(scan("injuries", range(2010, 2026)).collect())
    out = known_at("injuries", df, cal)
    assert (out["known_at"] >= out["date_modified"]).fill_null(True).all()
    kick = pl.concat(
        [
            cal.games.select("season", "week", "game_type", team=pl.col(t), kickoff="kickoff")
            for t in ("home_team", "away_team")
        ]
    )
    j = out.join(kick, on=["season", "week", "game_type", "team"])
    assert (j["known_at"] <= j["kickoff"]).mean() > 0.999


def test_daily_depth_charts_are_known_at_their_snapshot(cal):
    df = scan("depth_charts", [2025, 2026]).collect()
    out = known_at("depth_charts", df, cal)
    assert out["known_at"].equals(df["dt"].str.to_datetime(time_zone="UTC").alias("known_at"))
