"""The brief's tests on the tables built from the local raw copy (`pcf tables build`)."""

import time
from datetime import timedelta

import polars as pl
import pytest

from pcf.data.schemas import TABLES, check_part
from pcf.data.tables import load
from pcf.data.tables.store import files

pytestmark = pytest.mark.local_data

PLAYER_TOTALS = ["passing_yards", "rushing_yards", "receptions", "receiving_yards"]


@pytest.fixture(scope="module", autouse=True)
def _built():
    if not all(files(name, t.spine) for name, t in TABLES.items()):
        pytest.skip("tables not built: run `pcf tables build`")


@pytest.mark.parametrize("name", list(TABLES))
def test_every_part_meets_the_contract(name):
    for part in TABLES[name].parts:
        for path in files(name, part):
            check_part(pl.read_parquet(path), name, part)


def test_the_spine_holds_everyone_who_played_before_the_game():
    for season in range(2002, 2027):
        pg = load("player_game", seasons=[season], parts=["stats", "snaps"])
        played = pg.filter(
            pl.col("stats_known_at").is_not_null() | pl.col("snaps_known_at").is_not_null()
        )
        assert played["on_roster"].mean() >= 0.998, season  # 2016: 0.9982 (grain-tables#F13)


def test_inactives_never_took_a_snap():
    pg = load("player_game", seasons=range(2019, 2027), parts=["game_status", "snaps"])
    inactive = pg.filter(pl.col("status") == "INA")
    assert inactive.height > 20_000
    snaps = pl.sum_horizontal("offense_snaps", "defense_snaps", "st_snaps").fill_null(0)
    assert inactive.filter(snaps > 0).height == 0


def test_players_add_up_to_their_team():
    pg = load("player_game", parts=["stats"])
    tg = load("team_game", parts=["stats"]).filter(pl.col("stats_known_at").is_not_null())
    sums = (
        pg.group_by("game_id", "team")
        .agg(pl.col(PLAYER_TOTALS).sum())
        .join(tg.select("game_id", "team", *PLAYER_TOTALS), on=["game_id", "team"], suffix="_t")
    )
    for col in PLAYER_TOTALS:
        assert ((sums[col] - sums[f"{col}_t"]).abs() <= 1).mean() >= 0.999, col


def test_team_game_has_two_rows_per_game():
    tg = load("team_game", parts=[])
    assert tg.group_by("game_id").len()["len"].unique().to_list() == [2]


@pytest.mark.parametrize(
    ("part", "seasons"), [("participation", range(2016, 2026)), ("ftn", range(2022, 2026))]
)
def test_play_parts_attach_to_run_and_pass_plays(part, seasons):
    for season in seasons:
        plays = load("play", seasons=[season], parts=[part])
        run_pass = plays.filter(pl.col("play_type").is_in(["run", "pass"]))
        assert run_pass[f"{part}_known_at"].is_not_null().mean() >= 0.995, season


def test_nothing_known_after_the_moment_comes_back():
    kick = load("game", seasons=[2024], parts=[]).filter(pl.col("game_id") == "2024_10_DEN_KC")
    kick = kick["kickoff"].item()
    for at in [kick - timedelta(days=3), kick, kick + timedelta(days=9)]:
        for name in TABLES:
            if name == "play":
                continue  # covered by player_game's timing and the unit tests; large
            out = load(name, at=at, seasons=[2024])
            for col in (c for c in out.columns if c.endswith("known_at")):
                assert not out[col].drop_nulls().gt(at).any(), (name, col, at)


def test_inactives_appear_an_hour_before_kickoff():
    game = load("game", seasons=[2024], parts=[]).filter(pl.col("game_id") == "2024_10_DEN_KC")
    kick = game["kickoff"].item()
    for at, known in [(kick - timedelta(minutes=61), 0), (kick - timedelta(minutes=59), 1.0)]:
        pg = load("player_game", at=at, seasons=[2024], parts=["game_status"])
        rows = pg.filter(pl.col("game_id") == "2024_10_DEN_KC")
        assert rows.height > 100
        assert rows["status"].is_not_null().mean() == known


def test_a_season_of_player_game_loads_in_under_two_seconds():
    t = time.time()
    load("player_game", seasons=[2024])
    assert time.time() - t < 2
