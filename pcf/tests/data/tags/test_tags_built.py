"""The brief's tests on the tags built from the local raw copy (`pcf tables build`)."""

from datetime import timedelta

import polars as pl
import pytest

from pcf.data.tables import load
from pcf.data.tables.store import files
from pcf.data.tags.catalog import LEVELS
from pcf.data.tags.check import complete_seasons, out_of_band, rates

pytestmark = pytest.mark.local_data
c = pl.col


@pytest.fixture(scope="module", autouse=True)
def _built():
    if not files("drive", "tags"):
        pytest.skip("tags not built: run `pcf tables build`")


@pytest.mark.parametrize("level", LEVELS)
def test_every_complete_season_is_in_band(level):
    out = out_of_band(level)
    assert out.height == 0, out


def test_every_tag_fires_in_every_season_it_covers():
    done = complete_seasons()
    for level in LEVELS:
        r = rates(level).filter(c("season").is_in(done), ~c("tag").str.contains("="))
        assert r.filter(c("share") == 0).height == 0, level


def test_three_and_outs_have_no_first_down():
    for season in (2001, 2024):
        drives = load("drive", seasons=[season])
        assert drives.filter(c("tag_three_and_out"))["first_downs"].max() == 0


def test_answer_drives_follow_an_opponent_touchdown():
    drives = load("drive", seasons=[2024]).sort("game_id", "fixed_drive")
    prev = drives.with_columns(
        prev_result=c("result").shift(1).over("game_id"),
        prev_team=c("posteam").shift(1).over("game_id"),
    ).filter(c("tag_answer_drive"))
    assert prev.height > 200
    assert (prev["prev_result"] == "Touchdown").all()
    assert (prev["prev_team"] != prev["posteam"]).all()


def test_garbage_time_is_never_neutral_script():
    plays = load("play", seasons=[2024], parts=["tags"])
    assert plays.filter(c("tag_garbage_time") & c("tag_neutral_script")).height == 0


def test_tags_are_known_no_earlier_than_what_they_label():
    kick = load("game", seasons=[2024], parts=[]).filter(c("game_id") == "2024_10_DEN_KC")
    kick = kick["kickoff"].item()
    seen = set()
    for at in (kick - timedelta(hours=3), kick - timedelta(minutes=30), kick + timedelta(days=2)):
        tg = load("team_game", at=at, seasons=[2024], parts=["pregame", "tags", "tags_result"])
        rows = tg.filter(c("game_id") == "2024_10_DEN_KC")
        seen.add(rows["tag_primetime"].is_not_null().all())
        # Team-game tags wait for the pregame part (starting QB, lines).
        assert (
            rows["tag_primetime"].is_not_null().all()
            == rows["pregame_known_at"].is_not_null().all()
        )
        assert rows["tag_weather_game"].is_not_null().any() == (at > kick)
        pg = load("player_game", at=at, seasons=[2024], parts=["tags", "tags_result", "stats"])
        rows = pg.filter(c("game_id") == "2024_10_DEN_KC")
        assert rows["tags_result_known_at"].is_not_null().any() == (at > kick)
        assert rows["stats_known_at"].is_not_null().any() == (at > kick)
    assert seen == {False, True}  # the moments straddle when the tags become known
