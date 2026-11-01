"""The improved slot labels on every season with participation, from the local raw copy."""

import polars as pl
import pytest

from pcf.data.clean import legacy, standard
from pcf.data.clean.depth_charts import (
    daily_depth_rows,
    depth_labels,
    drop_off_roster,
    weekly_depth_rows,
)
from pcf.data.clean.players import players_on_play, plays_with_players
from pcf.data.sources.nflverse import scan
from pcf.data.timeline import games, team_kickoffs

PBP = ["game_id", "play_id", "play_type", "season", "week", "season_type", "posteam", "defteam"]
OLD = ["offense_players", "defense_players", "game_id", "play_id", "play_type", "season", "week"]
ROSTER = ["season", "week", "team", "gsis_id", "position", "depth_chart_position", "status"]

pytestmark = pytest.mark.local_data


@pytest.fixture(scope="module")
def labels() -> pl.DataFrame:
    weekly = weekly_depth_rows(scan("depth_charts", range(2015, 2025)).collect())
    schedules = standard.schedules(scan("schedules").filter(pl.col("season") >= 2025).collect())
    kickoffs = team_kickoffs(games(schedules))
    daily = daily_depth_rows(scan("depth_charts", [2025]).collect(), kickoffs)
    rosters = standard.weekly_rosters(scan("weekly_rosters", [2025]).collect())
    daily = drop_off_roster(daily, rosters)
    return depth_labels(pl.concat([weekly, daily]))


def _season(season: int, labels: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    from pcf.data.clean.slots import slot_labels

    plays = plays_with_players(
        scan("pbp", [season]).select(PBP).collect(),
        scan("participation", [season])
        .select("nflverse_game_id", "play_id", "offense_players", "defense_players")
        .collect(),
    )
    rosters = standard.weekly_rosters(scan("weekly_rosters", [season]).select(ROSTER).collect())
    return plays, slot_labels(players_on_play(plays), labels, rosters)


@pytest.mark.parametrize("season", range(2016, 2026))
def test_every_season_meets_the_expectations(season, labels):
    _, out = _season(season, labels)
    assert (out["label_source"] == "none").mean() < 0.002
    known = out.filter(pl.col("label_source") != "none")
    sides = known.group_by("game_id", "play_id", "side").agg(
        n=pl.len(), labels=pl.col("position_label").n_unique()
    )
    assert (sides["labels"] == sides["n"]).all()  # no two players share a label
    qbs = (
        out.filter(pl.col("side") == "offense")
        .group_by("game_id", "play_id")
        .agg(qb=(pl.col("position") == "QB").sum())
    )
    assert (qbs["qb"] >= 1).mean() >= 0.99  # two QBs is real football (results F14)
    assert (out["position"] == "special").mean() < 0.005
    assert (out["label_source"] == "week").mean() > 0.94


@pytest.mark.parametrize("season", [2016, 2020, 2024])
def test_chart_positions_agree_with_the_old_code(season, labels):
    """Where both read that week's chart, the position (not the depth number) should agree."""
    plays, out = _season(season, labels)
    old = legacy.pivot_long_both_sides(
        legacy.pivot_wide_both_sides(plays.select(OLD).to_pandas()),
        scan("depth_charts", [season]).collect().to_pandas(),
    )
    old = pl.from_pandas(old[["game_id", "play_id", "player_id", "position_label"]]).rename(
        {"player_id": "gsis_id", "position_label": "old_label"}
    )
    both = out.filter(pl.col("label_source") == "week").join(
        old, on=["game_id", "play_id", "gsis_id"]
    )
    same = both["position"] == both["old_label"].str.replace(r"\d+$", "")
    assert same.mean() > 0.95
