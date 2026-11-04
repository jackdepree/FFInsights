"""Participation's inputs, two-part models and horizons on the synthetic league, extended with snap
counts, game statuses, a depth chart, an injury report and box-score stats. Each player's share
follows their skill, so there's signal to find."""

from datetime import timedelta

import numpy as np
import polars as pl
import pytest

from pcf.core.contract import check_expert
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.experts.participation.features import features
from pcf.experts.participation.horizons import (
    LassoH3,
    LassoRest,
    SeasonRest,
    TreesH3,
    TreesRest,
    window_share,
)
from pcf.experts.participation.twopart import Active, Lasso, Trees, TreesCareer, mixture_quantiles
from pcf.validation import backtest, leakage

from ..validation import world

c = pl.col
UTC = pl.Datetime("us", "UTC")
SEASON = 2023
OUT_WEEK = 5
KEYS = ["gsis_id", "game_id"]


def _rb() -> str:
    return world.players().filter(c("position") == "RB")["gsis_id"][0]


def _parts() -> dict:
    parts = world.frames()
    roster = parts[("player_game", "roster")]
    skill = world.players().select("gsis_id", "skill")
    k = world.cal().games.select("game_id", "kickoff")
    rng = np.random.default_rng(5)
    rows = (
        roster.join(k, on="game_id")
        .join(skill, on="gsis_id")
        .with_columns(
            out=(c("gsis_id") == _rb()) & (c("season") == SEASON) & (c("week") == OUT_WEEK),
            pct=(c("skill") / 25 + pl.Series(rng.normal(0, 0.05, roster.height))).clip(0.02, 1.0),
        )
    )
    after = (c("kickoff") + pl.duration(hours=24)).cast(UTC)
    snaps = rows.filter(~c("out")).select(
        *KEYS, "season", "week",
        offense_snaps=pl.lit(60, pl.Int64), offense_pct="pct", st_pct=pl.lit(0.1), known_at=after,
    )  # fmt: skip
    status = rows.select(
        *KEYS, "season",
        status=pl.when(c("out")).then(pl.lit("INA")).otherwise(pl.lit("ACT")),
        known_at=(c("kickoff") - pl.duration(minutes=90)).cast(UTC),
    )  # fmt: skip
    depth = rows.select(
        *KEYS, "season",
        depth=pl.lit(1, pl.Int32), depth_mean=pl.lit(1.0),
        known_at=(c("kickoff") - pl.duration(days=5)).cast(UTC),
    )  # fmt: skip
    injury = rows.filter(c("out")).select(
        *KEYS, "season",
        report_status=pl.lit("Out"), practice_status=pl.lit("Did Not Participate In Practice"),
        known_at=(c("kickoff") - pl.duration(days=2)).cast(UTC),
    )  # fmt: skip
    stats = (
        parts[("player_game", "stats")]
        .join(rows.select(*KEYS, "pct"), on=KEYS)
        .with_columns(
            targets=(c("pct") * 10).cast(pl.Int32), carries=pl.lit(1, pl.Int32),
            receptions=pl.lit(1, pl.Int32), receiving_yards=c("pct") * 50,
            rushing_yards=pl.lit(5.0), attempts=pl.lit(0, pl.Int32), passing_epa=pl.lit(0.0),
            rushing_epa=pl.lit(0.1), receiving_epa=pl.lit(0.1),
        )
        .drop("pct")
    )  # fmt: skip
    roster = roster.with_columns(
        rookie_year=pl.lit(2010), years_exp=pl.lit(3), draft_number=pl.lit(50),
        birth_date=pl.date(1995, 1, 1),
    )  # fmt: skip
    schedule = parts[("game", "schedule")].with_columns(game_type=pl.lit("REG"))
    return {
        **parts,
        ("player_game", "roster"): roster,
        ("player_game", "snaps"): snaps,
        ("player_game", "game_status"): status,
        ("player_game", "depth"): depth,
        ("player_game", "injury"): injury,
        ("player_game", "stats"): stats,
        ("game", "schedule"): schedule,
    }


@pytest.fixture(scope="module")
def gateway() -> Gateway:
    return Gateway(FrameSource(_parts()), world.cal())


def _games(week: int) -> pl.DataFrame:
    """The RB's game that week."""
    team = world.players().filter(c("gsis_id") == _rb())["team"][0]
    theirs = (
        _parts()[("player_game", "roster")]
        .filter((c("team") == team) & (c("season") == SEASON) & (c("week") == week))
        .select("game_id")
        .unique()
    )
    return (
        world.cal()
        .games.join(theirs, on="game_id")
        .select("game_id", "season", "week", "kickoff")
    )


def _at_kickoff_minus(gateway, games, hours=24):
    moment = games["kickoff"].min() - timedelta(hours=hours)
    return gateway.view(moment, "in_season", Lasso.inputs)


def test_the_models_meet_the_contract():
    for cls in (Lasso, Trees, TreesCareer, Active, LassoH3, TreesH3, SeasonRest, TreesRest):
        check_expert(cls)


def test_the_report_and_a_past_absence_reach_the_features(gateway):
    games = _games(OUT_WEEK)
    f = features(_at_kickoff_minus(gateway, games), games, KEYS)
    rb = f.filter(c("gsis_id") == _rb()).to_dicts()[0]
    assert rb["report"] == 3 and rb["practice"] == 2  # the report, known two days before
    games = _games(OUT_WEEK + 1)
    f = features(_at_kickoff_minus(gateway, games), games, KEYS)
    rb = f.filter(c("gsis_id") == _rb()).to_dicts()[0]
    assert rb["missed_streak"] == 1 and rb["back"] == 1 and rb["last_game"] == 0
    assert rb["active_last"] > 0 and rb["back_career"] == pytest.approx(rb["career_active"])


def test_the_game_day_list_and_this_game_are_never_inputs(gateway):
    """D8: 90 minutes before kickoff isn't visible on Saturday."""
    games = _games(OUT_WEEK)
    view = _at_kickoff_minus(gateway, games)
    pg = view.table("player_game").filter(c("game_id").is_in(games["game_id"].implode()))
    assert pg["status"].null_count() == pg.height
    assert pg["offense_pct"].null_count() == pg.height


def test_a_hidden_chart_falls_back_to_the_last_known_one():
    parts = _parts()
    depth = parts[("player_game", "depth")]
    k = world.cal().games.select("game_id", "kickoff", "week", "season")
    # The chart for the week predicted is known only at kickoff, as daily charts are from 2025
    late = depth.join(k, on="game_id").with_columns(
        known_at=pl.when((c("season") == SEASON) & (c("week") == 6))
        .then(c("kickoff").cast(UTC)).otherwise(c("known_at"))
    ).drop("kickoff", "week", "season_right", strict=False)  # fmt: skip
    gw = Gateway(FrameSource({**parts, ("player_game", "depth"): late}), world.cal())
    games = _games(6)
    f = features(_at_kickoff_minus(gw, games), games, KEYS)
    assert f["unlisted"].sum() == 0 and f["depth1"].min() == 1


def test_mixture_quantiles_put_the_low_levels_at_zero():
    grid = np.tile(np.linspace(-0.2, 0.2, 99), (5, 1))
    p, s = np.array([0.5, 0.95]), np.array([0.8, 0.8])
    assert mixture_quantiles(p, s, grid, 0.1).tolist()[0] == 0  # sits out half the time
    assert mixture_quantiles(p, s, grid, 0.1)[1] > 0.5
    assert np.all(mixture_quantiles(p, s, grid, 0.9) <= 1)


@pytest.mark.parametrize("cls", [Lasso, Trees])
def test_a_two_part_backtest_beats_shuffling_and_passes_the_leakage_checks(gateway, cls):
    bt = backtest.run(cls(), gateway, [2022, 2023], refit="season")
    h = bt.scored
    assert h["mean"].min() >= 0 and h["mean"].max() <= 1
    assert (h["q10"] <= h["q50"]).all() and (h["q50"] <= h["q90"]).all()
    assert h["q10"].min() >= 0 and h["q90"].max() <= 1
    checks = leakage.run_checks(bt, gateway, None, 3, 0)
    assert all(ch.passed or not ch.blocking for ch in checks)


def test_the_active_probability_learns_who_is_out(gateway):
    bt = backtest.run(Active(), gateway, [2023], refit="season")
    h = bt.scored
    assert h["mean"].min() >= 0 and h["mean"].max() <= 1
    assert set(h["y"].unique().to_list()) <= {0.0, 1.0}


def test_a_window_counts_a_missed_or_off_roster_game_as_zero(gateway):
    view = gateway.view(END_OF_TIME, "in_season", LassoH3.inputs)
    pg, sched = view.table("player_game"), view.table("game")
    one = known = window_share(pg, sched, KEYS, 1)
    assert known.height > 0
    y3 = window_share(pg, sched, KEYS, 3)
    rb_game = pg.filter((c("gsis_id") == _rb()) & (c("season") == SEASON) & (c("week") == OUT_WEEK))
    start = rb_game["game_id"][0]
    y = y3.filter((c("gsis_id") == _rb()) & (c("game_id") == start))["y"][0]
    weeks = (
        pg.filter((c("gsis_id") == _rb()) & (c("season") == SEASON) & (c("week") >= OUT_WEEK))
        .sort("week")["game_id"].to_list()[:3]
    )  # fmt: skip
    share = one.filter((c("gsis_id") == _rb()) & c("game_id").is_in(weeks))["y"].to_list()
    assert 0.0 in share and y == pytest.approx(sum(share) / 3)
    # Dropping the rows of a later game (cut): the player's window still counts it, as 0
    later = weeks[-1]
    cut = pg.filter(~((c("gsis_id") == _rb()) & (c("game_id") == later)))
    y_cut = window_share(cut, sched, KEYS, 3).filter(
        (c("gsis_id") == _rb()) & (c("game_id") == start)
    )["y"][0]
    assert y_cut < y


def test_a_window_is_known_only_when_its_last_game_is(gateway):
    view = gateway.view(END_OF_TIME, "in_season", LassoH3.inputs)
    pg, sched = view.table("player_game"), view.table("game")
    last = window_share(pg, sched, KEYS, 3).join(
        pg.select(*KEYS, "known_at"), on=KEYS, suffix="_row"
    )
    assert (last["known_at"] > last["known_at_row"]).all()


def test_the_rest_of_season_horizon_runs_through_the_harness(gateway):
    bt = backtest.run(LassoRest(), gateway, [2023], refit="season")
    h = bt.scored
    assert h.height > 0 and h["mean"].min() >= 0 and h["mean"].max() <= 1
    checks = leakage.run_checks(bt, gateway, None, 3, 0)
    assert all(ch.passed or not ch.blocking for ch in checks)
