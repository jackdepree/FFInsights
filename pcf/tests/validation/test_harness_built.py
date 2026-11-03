"""The harness on the real tables (needs `pcf tables build`): moments for every game, the gateway
against `load`, the Monday-night leak (validation-harness#F2) and the toy's checks."""

from datetime import UTC, datetime

import polars as pl
import pytest

from pcf.data.gateway import Gateway, TableSource
from pcf.data.tables.store import load
from pcf.data.timeline import calendar
from pcf.data.timeline.moments import RUNS, game_moments
from pcf.validation import backtest, leakage
from pcf.validation.toy import RecentPoints

from . import planted

pytestmark = pytest.mark.local_data
c = pl.col
SEASONS = [2023, 2024]


@pytest.fixture(scope="module")
def gw():
    return Gateway(TableSource(seasons=SEASONS))


@pytest.mark.parametrize("run", list(RUNS))
def test_every_game_since_1999_has_a_moment_before_kickoff(run):
    m = game_moments(calendar(load("game", parts=["schedule"])), run)
    assert m["moment"].null_count() == 0
    assert m.filter(c("moment") >= c("kickoff")).is_empty()
    # Only weeks that start mid-week fall back (1999-2001 week 1, 2010, 2020-21: F11)
    assert m["fallback"].sum() <= 125


def test_a_view_is_load_at_its_moment(gw):
    at = datetime(2024, 11, 5, 15, tzinfo=UTC)
    parts = ("stats", "snaps", "injury")
    view = gw.view(at, "in_season", {"player_game": parts}).table("player_game", seasons=[2024])
    loaded = load("player_game", at=at, seasons=[2024], parts=list(parts))
    keys = ["gsis_id", "game_id"]
    assert view.sort(keys).equals(loaded.sort(keys))


@pytest.fixture(scope="module")
def bt(gw):
    return backtest.run(RecentPoints(), gw, [2024])


def test_the_toy_passes_every_blocking_check_on_real_data(gw, bt):
    checks = leakage.run_checks(bt, gw, n_cutoffs=6)
    assert all(ch.passed for ch in checks if ch.blocking), [ch for ch in checks if not ch.passed]


def test_the_monday_night_leak_is_caught_on_real_data(gw):
    """ "Earlier games" is not "known at Tuesday 10 AM": Monday night's stats arrive Tuesday
    night. The honest bulk version passes; the "earlier games" one fails."""
    cuts = leakage.cutoffs(gw.calendar, [2024], 4, seed=2)
    honest = backtest.run(planted.HonestBulk(), gw, [2024])
    assert leakage.future_check(honest, gw, cuts, "delete").passed
    leaky = backtest.run(planted.EarlierGamesBulk(), gw, [2024])
    assert not leakage.future_check(leaky, gw, cuts, "delete").passed


def test_the_toys_four_game_average_matches_a_hand_count(bt):
    """The brief's check: last4 by hand, from kickoff + 24 hours (the stats rule in
    DATA_SOURCES.md) rather than the gateway's known_at, for 300 sampled rows."""
    kick = load("game", parts=["schedule"], seasons=SEASONS).select("game_id", "kickoff")
    played = (
        load("player_game", parts=["stats"], seasons=SEASONS)
        .filter(c("fantasy_points_ppr").is_not_null())
        .join(kick, on="game_id")
        .select("gsis_id", "season", "week", "kickoff", points="fantasy_points_ppr")
    )
    rows = bt.features.filter(c("step_season") == 2024).sample(300, seed=4)
    for r in rows.iter_rows(named=True):
        seen = played.filter(
            (c("gsis_id") == r["gsis_id"])
            & (c("kickoff") + pl.duration(hours=24) <= r["as_of"])
            & c("season").is_between(r["step_season"] - 1, r["step_season"])
        ).sort("season", "week")
        assert seen.tail(4)["points"].mean() == pytest.approx(r["last4"], rel=1e-9), r
