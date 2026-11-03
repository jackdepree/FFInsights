"""The baselines on the real tables (needs `pcf tables build` with the ECR archive)."""

import polars as pl
import pytest

from pcf.data.tables.store import load
from pcf.data.timeline.calendar import ET

pytestmark = pytest.mark.local_data
c = pl.col
SEASONS = [2021, 2022, 2023, 2024]


@pytest.fixture(scope="module")
def ecr():
    # A part comes with the spine: keep the ranked rows
    rows = load("player_game", parts=["ecr"], seasons=SEASONS).drop_nulls("ecr_known_at")
    kick = load("game", parts=["schedule"], seasons=SEASONS).select("game_id", "kickoff")
    return rows.join(kick, on="game_id")


def test_every_ecr_row_is_known_before_its_kickoff(ecr):
    assert ecr.height > 20_000
    assert (ecr["ecr_known_at"] < ecr["kickoff"]).all()
    assert ((ecr["kickoff"] - ecr["ecr_known_at"]).dt.total_days() <= 4).all()


def test_thursday_games_are_almost_never_ranked(ecr):
    """The Friday snapshot comes after Thursday's kickoff (baselines#F2): only the odd week with
    an earlier snapshot ranks a Thursday game."""
    day = ecr.with_columns(wd=c("kickoff").dt.convert_time_zone(ET).dt.weekday())
    share = day.group_by("wd").len().with_columns(share=c("len") / c("len").sum())
    thursday = share.filter(c("wd") == 4)["share"]
    assert thursday.is_empty() or thursday[0] < 0.03


def test_each_position_s_top_ranks_are_there_most_weeks(ecr):
    top = ecr.filter(c("ecr_rank") <= 12).group_by("season", "ecr_position").len()
    # 2024 starts in week 4 (baselines#F1): at least 11 weeks of a top 12
    assert (top["len"] >= 11 * 12).all(), top.sort("len")
