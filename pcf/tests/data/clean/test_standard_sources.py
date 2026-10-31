"""Each normalization runs on its whole local dataset without meeting anything it doesn't know."""

import polars as pl
import pytest

from pcf.data.clean import standard
from pcf.data.sources.nflverse import scan

pytestmark = pytest.mark.local_data


def test_schedules():
    out = standard.schedules(scan("schedules").collect())
    assert set(out["roof"].drop_nulls()) <= set(standard.ROOFS)
    assert set(out["home_team"]) <= standard.TEAMS
    assert out.filter(pl.col("home_spread") != -pl.col("spread_line")).height == 0


def test_player_stats_and_expected_points():
    stats = standard.player_stats(scan("player_stats").collect())
    assert stats["gsis_id"].null_count() == 0
    efp = standard.ff_opportunity(scan("ff_opportunity").collect())
    assert efp["gsis_id"].null_count() == 0
    assert efp.select("gsis_id", "game_id").is_duplicated().sum() == 0


def test_snap_counts():
    out = standard.snap_counts(scan("snap_counts").collect(), scan("players").collect())
    assert out["gsis_id"].is_null().mean() < 0.002


def test_injuries():
    out = standard.injuries(scan("injuries").collect())
    key = ["season", "week", "game_type", "team", "gsis_id"]
    assert out.drop_nulls("gsis_id").select(key).is_duplicated().sum() == 0


def test_weekly_rosters():
    out = standard.weekly_rosters(scan("weekly_rosters").collect())
    key = ["season", "week", "team", "gsis_id"]
    assert out.drop_nulls("gsis_id").select(key).is_duplicated().sum() == 0


def test_participation():
    out = standard.participation(scan("participation").collect())
    assert "game_id" in out.columns
