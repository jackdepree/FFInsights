"""Participation's rung 0 on the synthetic league, extended with snap counts: one player sits out
two games, another has no snap-count row in a game they were active for."""

import polars as pl
import pytest

from pcf.core.contract import check_expert, find_all
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.experts.participation.averages import Last3, Last3Active, LastGame
from pcf.experts.participation.common import known_shares, target_share
from pcf.validation import backtest, leakage

from ..validation import world

c = pl.col
UTC = pl.Datetime("us", "UTC")
SEASON = 2023
ABSENT_WEEKS = (5, 6)


def _absent() -> str:
    """One RB, out for two games in the middle of a season."""
    return world.players().filter(c("position") == "RB")["gsis_id"][0]


def _parts() -> dict:
    parts = world.frames()
    roster = parts[("player_game", "roster")]
    k = world.cal().games.select("game_id", "kickoff")
    rows = roster.join(k, on="game_id").with_columns(
        out=(c("gsis_id") == _absent())
        & (c("season") == SEASON)
        & c("week").is_in(list(ABSENT_WEEKS))
    )
    snaps = rows.filter(~c("out")).select(
        "gsis_id", "game_id", "season", "week",
        offense_snaps=pl.lit(60, pl.Int64),
        offense_pct=pl.lit(0.8),
        known_at=(c("kickoff") + pl.duration(hours=24)).cast(UTC),
    )  # fmt: skip
    status = rows.select(
        "gsis_id", "game_id", "season",
        status=pl.when(c("out")).then(pl.lit("INA")).otherwise(pl.lit("ACT")),
        known_at=(c("kickoff") - pl.duration(minutes=90)).cast(UTC),
    )  # fmt: skip
    return {**parts, ("player_game", "snaps"): snaps, ("player_game", "game_status"): status}


@pytest.fixture(scope="module")
def gateway() -> Gateway:
    return Gateway(FrameSource(_parts()), world.cal())


def _pg(gateway, moment=END_OF_TIME) -> pl.DataFrame:
    return gateway.view(moment, "in_season", LastGame.inputs).table("player_game")


def test_the_variants_meet_the_contract():
    assert {x.variant for x in find_all("participation")} >= {"last_game", "last3", "last3_active"}
    for cls in (LastGame, Last3, Last3Active):
        check_expert(cls)


def test_an_inactive_player_with_no_snap_row_has_share_zero(gateway):
    y = target_share(_pg(gateway), LastGame.keys())
    assert y.height == _pg(gateway).height  # nobody dropped for missing a snap-count row
    assert y["known_at"].null_count() == 0
    rb = known_shares(_pg(gateway)).filter(
        (c("gsis_id") == _absent()) & (c("season") == SEASON) & c("week").is_in(list(ABSENT_WEEKS))
    )
    assert rb["share"].to_list() == [0.0, 0.0]
    assert rb["active"].to_list() == [False, False]


def test_an_absence_counts_in_last3_but_not_in_last3_active(gateway):
    games = world.cal().games.filter((c("season") == SEASON) & (c("week") == ABSENT_WEEKS[-1] + 1))
    moment = games["kickoff"].min() - pl.duration(hours=12)
    moment = pl.select(moment).item() if isinstance(moment, pl.Expr) else moment
    view = gateway.view(moment, "in_season", LastGame.inputs)
    f = LastGame().features(view, games.select("game_id", "season", "week", "kickoff"))
    rb = f.filter(c("gsis_id") == _absent()).to_dicts()[0]
    assert rb["last_game"] == 0.0
    assert rb["last3"] == pytest.approx(0.8 / 3)
    assert rb["last3_active"] == pytest.approx(0.8)


def test_shares_of_a_game_not_yet_played_are_not_seen(gateway):
    first = world.cal().games.filter(c("season") == SEASON)["kickoff"].min()
    pg = gateway.view(first, "in_season", LastGame.inputs).table("player_game")
    assert known_shares(pg)["season"].max() < SEASON


@pytest.mark.parametrize("cls", [LastGame, Last3Active])
def test_a_backtest_is_in_bounds_and_passes_the_leakage_checks(gateway, cls):
    bt = backtest.run(cls(), gateway, [2022, 2023])
    h = bt.scored
    assert h["q10"].min() >= 0 and h["q90"].max() <= 1
    assert h.filter(c("mean") > 1).is_empty()
    assert h.height > 0
    checks = leakage.run_checks(bt, gateway, None, 3, 0)
    assert all(ch.passed or not ch.blocking for ch in checks)
