"""The live run on the synthetic league, with 2023 standing in for the live season: which games are
due, that a live forecast is exactly the backtest's, and that a replay matches a live run."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from pcf.config import Seasons, get_config
from pcf.validation import backtest, live
from pcf.validation.toy import RecentPoints

from . import world

c = pl.col
LIVE = 2023


@pytest.fixture(autouse=True)
def live_2023(monkeypatch):
    cfg = replace(get_config(), seasons=Seasons(2020, 2021, 2022, LIVE))
    monkeypatch.setattr(live, "get_config", lambda: cfg)


@pytest.fixture(scope="module")
def gw():
    return world.gateway()


def week3(gw):
    from pcf.data.timeline.moments import game_moments

    return (
        game_moments(gw.calendar, "tuesday")
        .filter((c("season") == LIVE) & (c("week") == 3))
        .sort("kickoff")
    )


def test_due_games_are_past_their_moment_and_before_kickoff(gw):
    games = week3(gw)
    moment = games["moment"][0]
    assert live.due_games(gw, "tuesday", moment - timedelta(minutes=1)).is_empty()
    due = live.due_games(gw, "tuesday", moment + timedelta(hours=1))
    assert due["game_id"].to_list() == games["game_id"].to_list()
    after_first = games["kickoff"][0] + timedelta(minutes=1)
    assert (
        live.due_games(gw, "tuesday", after_first)["game_id"].to_list()
        == (games["game_id"].to_list()[1:])
    )


def test_a_live_forecast_is_the_backtest_s_forecast(gw):
    e = RecentPoints()
    now = week3(gw)["moment"][0] + timedelta(hours=1)
    f = live.forecast(e, gw, now, "check")
    so_far = live.steps_so_far(e, gw, now)
    step = [s for s in so_far if s.season == LIVE and s.week == 3][0]
    feats = backtest.feature_history(e, gw, so_far)
    walked = backtest.walk(e, feats, backtest.targets(e, gw), so_far, [step.index], "step")
    keys = e.keys()
    both = f.rows.join(walked, on=keys, suffix="_walk")
    assert both.height == f.rows.height == walked.height
    for q in ("mean", "q10", "q50", "q90"):
        assert (both[q] - both[f"{q}_walk"]).abs().max() == 0
    assert (f.rows["kickoff"] > now).all()
    assert (f.rows["train_end"] <= f.rows["as_of"]).all()


class Publishing(RecentPoints):
    """The toy, publishing one of its features, as Elo publishes its ratings."""

    variant = "publishing"
    publishes = ("last4",)


def test_a_live_forecast_carries_what_the_expert_publishes(gw):
    e = Publishing()
    now = week3(gw)["moment"][0] + timedelta(hours=1)
    f = live.forecast(e, gw, now, "check")
    feats = backtest.feature_history(e, gw, live.steps_so_far(e, gw, now))
    both = f.rows.join(feats.select(*e.keys(), "as_of", "last4"), on=[*e.keys(), "as_of"])
    assert both.height == f.rows.height
    assert both.filter(c("last4") != c("last4_right")).is_empty()


def test_the_ledger_runs_participation_first():
    """A slow run must never cost participation its kickoff (live-experts, technical call)."""
    projects = [p for p, _ in live.MODELS]
    last_participation = max(i for i, p in enumerate(projects) if p == "participation")
    assert projects[: last_participation + 1] == ["participation"] * (last_participation + 1)
    assert len(set(live.MODELS)) == len(live.MODELS)


def test_every_ledger_model_exists():
    from pcf.core.contract import find

    for project, variant in live.MODELS:
        assert find(project, variant).variant == variant


def test_a_live_run_sees_no_later_moment(gw):
    e = RecentPoints()
    now = week3(gw)["moment"][0] + timedelta(hours=1)
    so_far = live.steps_so_far(e, gw, now)
    latest = max(s.games["moment"].max() for s in so_far)
    assert latest <= now


def test_a_replay_matches_the_live_run_it_stands_for(gw):
    e = RecentPoints()
    now = week3(gw)["moment"][0] + timedelta(hours=1)
    later = now + timedelta(days=14)
    feats = backtest.feature_history(e, gw, live.steps_so_far(e, gw, later))
    replayed = live.forecast(e, gw, now, "replay", feats)
    direct = live.forecast(e, gw, now, "live")
    keys = e.keys()
    assert replayed.rows.drop("run_id").sort(keys).equals(direct.rows.drop("run_id").sort(keys))


def test_the_input_check_compares_the_same_weeks(gw):
    e = RecentPoints()
    now = week3(gw)["moment"][0] + timedelta(hours=1)
    f = live.forecast(e, gw, now, "check")
    assert set(f.checks["input"]) == {"last4", "games", "season_avg"}
    assert not f.checks["flag"].any()


def test_nothing_is_due_between_weeks(gw):
    games = week3(gw)
    after = games["kickoff"].max() + timedelta(minutes=1)
    assert live.forecast(RecentPoints(), gw, after, "x") is None


# --------------------------------------------------- the late injury file (found by the 2026-11-07
# test run: a time-zone name was passed where Python needs the zone)

SATURDAY_NOON = datetime(2026, 11, 7, 17, 0, tzinfo=UTC)


def fresh(updated):
    return lambda season: {"injuries": {"file_updated": updated, "fetched": updated}}


def test_no_wait_on_a_tuesday(monkeypatch):
    def fail(season):
        raise AssertionError("shouldn't look at the file")

    monkeypatch.setattr(live, "freshness", fail)
    tuesday = SATURDAY_NOON - timedelta(days=4)
    out = live.wait_for_injuries(tuesday, tuesday + timedelta(days=5), LIVE)
    assert out == {"waited_minutes": 0, "injury_file_today": None}


def test_no_wait_when_today_s_file_is_in(monkeypatch):
    monkeypatch.setattr(live, "freshness", fresh(SATURDAY_NOON - timedelta(hours=3)))
    out = live.wait_for_injuries(SATURDAY_NOON, SATURDAY_NOON + timedelta(days=1), LIVE)
    assert out["injury_file_today"] is True and out["waited_minutes"] == 0


def test_a_stale_file_near_kickoff_runs_without_waiting(monkeypatch):
    monkeypatch.setattr(live, "freshness", fresh(SATURDAY_NOON - timedelta(days=1)))
    soon = SATURDAY_NOON + timedelta(minutes=30)
    out = live.wait_for_injuries(SATURDAY_NOON, soon, LIVE)
    assert out["injury_file_today"] is False and out["waited_minutes"] == 0


def test_a_refresh_that_fails_once_is_tried_again(monkeypatch):
    """nflverse can replace a file mid-download (live-experts, 2026-11-10): one retry, then real."""
    from types import SimpleNamespace

    from pcf.data import tables
    from pcf.data.sources import nflverse

    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("schedules/games.parquet: downloaded content doesn't match")
        return SimpleNamespace(downloaded=0)

    monkeypatch.setattr(nflverse, "refresh", flaky)
    monkeypatch.setattr(tables, "build", lambda **_: None)
    monkeypatch.setattr(live, "freshness", lambda season: {})
    monkeypatch.setattr(live, "RETRY_SECONDS", 0)
    assert live.pull(LIVE)["downloaded"] == 0
    assert len(calls) == 2

    def down():
        raise RuntimeError("down")

    monkeypatch.setattr(nflverse, "refresh", down)
    with pytest.raises(RuntimeError, match="down"):
        live.pull(LIVE)
