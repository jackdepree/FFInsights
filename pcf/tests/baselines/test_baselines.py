"""The baselines on the synthetic league, extended with the stats the lasso reads, a weekly ECR
that ranks players by their skill, and closing lines from the teams' strength."""

import numpy as np
import polars as pl
import pytest

from pcf.baselines import VARIANTS, Ecr, Lasso, MarketWin, RollingAverage, scored
from pcf.baselines.common import fit_offsets, weighted_quantiles, with_ranges
from pcf.baselines.lasso import STATS, TDS
from pcf.baselines.market import no_vig_home
from pcf.core.contract import check_expert, find_all
from pcf.data.gateway import FrameSource, Gateway
from pcf.data.timeline.calendar import day_start
from pcf.validation import backtest, leakage
from pcf.validation.validate import validate

from ..validation import world

c = pl.col
TEST = [2022, 2023]
UTC = pl.Datetime("us", "UTC")
THURSDAY = 4


def _et_day(moment: pl.Expr) -> pl.Expr:
    return moment.dt.convert_time_zone("America/New_York").dt.date()


def _weekday(moment: pl.Expr) -> pl.Expr:
    return _et_day(moment).dt.weekday()


def _frames() -> dict:
    parts = world.frames()
    k = world.cal()
    roster = parts[("player_game", "roster")]
    rng = np.random.default_rng(3)
    stats = parts[("player_game", "stats")].with_columns(
        fantasy_points=c("fantasy_points_ppr") * 0.9,
        **{s: pl.Series(rng.uniform(0, 5, roster.height)) for s in [*STATS, *TDS]},
    )
    # ECR: the players ranked by skill within each position and game, known Saturday 00:00 ET
    # before the Sunday games; the Thursday game has no honest snapshot (baselines#F2).
    kick = k.games.select(
        "game_id", "kickoff", wd=_weekday(c("kickoff")), day=_et_day(c("kickoff"))
    )
    skill = world.players().select("gsis_id", "skill")
    ecr = (
        roster.join(kick, on="game_id")
        .filter(c("wd") != THURSDAY)
        .join(skill, on="gsis_id")
        .with_columns(
            ecr_rank=c("skill")
            .rank("ordinal", descending=True)
            .over("season", "week", "position")
            .cast(pl.Float64),
            # Saturday 00:00 ET, the day after a Friday scrape (Sunday: 1 day back, Monday: 2)
            known_at=day_start(c("day") - pl.duration(days=(c("wd") + 1) % 7)).cast(UTC),
        )
        .select(
            "gsis_id",
            "game_id",
            "season",
            "ecr_rank",
            "known_at",
            ecr_sd=pl.lit(1.0),
            ecr_position="position",
        )  # fmt: skip
    )
    # Closing lines and results from the teams' total skill
    team = (
        roster.join(skill, on="gsis_id").group_by("game_id", "team").agg(strength=c("skill").sum())
    )
    sched = parts[("game", "schedule")]
    g = (
        sched.select("game_id", "season", "home_team", "away_team", "kickoff")
        .join(team.rename({"team": "home_team", "strength": "home"}), on=["game_id", "home_team"])
        .join(team.rename({"team": "away_team", "strength": "away"}), on=["game_id", "away_team"])
        .with_columns(spread_line=((c("home") - c("away")) / 4).round(1))
    )
    noise = rng.normal(0, 13, g.height)
    g = g.with_columns(
        result=(c("spread_line") + pl.Series(noise)).round(0), total_line=pl.lit(44.0)
    )
    p = 1 / (1 + np.exp(-g["spread_line"].to_numpy() / 6))
    ml = lambda q: np.where(q > 0.5, -100 * q / (1 - q), 100 * (1 - q) / q).round(0)  # noqa: E731
    pregame = g.select(
        "game_id", "season", "spread_line", "total_line",
        home_moneyline=pl.Series(ml(p * 1.02)), away_moneyline=pl.Series(ml((1 - p) * 1.02)),
        known_at=c("kickoff").cast(UTC),
    )  # fmt: skip
    result = g.select(
        "game_id", "season", "result",
        total=c("total_line") + pl.Series(rng.normal(0, 10, g.height)),
        known_at=(c("kickoff") + pl.duration(hours=4)).cast(UTC),
    )  # fmt: skip
    return parts | {
        ("player_game", "stats"): stats,
        ("player_game", "ecr"): ecr,
        ("game", "pregame"): pregame,
        ("game", "result"): result,
    }


@pytest.fixture(scope="module")
def gw():
    return Gateway(FrameSource(_frames()), world.cal())


@pytest.fixture(scope="module")
def runs(gw):
    return {name: backtest.run(cls(), gw, TEST) for name, cls in VARIANTS.items()}


def test_every_variant_meets_the_contract_and_is_found():
    assert {cls.variant for cls in find_all("baselines")} == set(VARIANTS)
    for cls in VARIANTS.values():
        check_expert(cls)
    assert Ecr.benchmark and MarketWin.benchmark and not Lasso.benchmark


def test_the_rolling_average_is_the_last_four_games(runs):
    bt = runs["rolling4"]
    pred = bt.history.join(
        bt.features.select("gsis_id", "game_id", "last4"), on=["gsis_id", "game_id"]
    )
    assert (pred["mean"] == pred["last4"]).all()
    assert pred.filter((c("q10") > c("q50")) | (c("q50") > c("q90"))).is_empty()


def test_ranges_are_per_position_and_cover_about_80_percent(runs):
    """One spread per position (D7): QBs no longer under-covered (validation-harness#F15)."""
    for name in ("rolling4", "lasso", "ecr"):
        bt = runs[name]
        inside = bt.scored.join(
            bt.features.select("gsis_id", "game_id", "position"), on=["gsis_id", "game_id"]
        )
        by_pos = inside.group_by("position").agg(
            share=((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()
        )
        assert by_pos["share"].is_between(0.65, 0.92).all(), (name, by_pos)


def test_the_lasso_beats_the_rolling_average_when_skill_is_stable(runs):
    """Points are skill plus noise, so 4 games is a noisy estimate of the skill. (ECR isn't
    compared here: in a 6-team league a rank is one of 4, too coarse to say much.)"""
    assert runs["lasso"].scored["loss"].mean() < runs["rolling4"].scored["loss"].mean()


def test_ecr_never_ranks_a_thursday_game(runs, gw):
    games = gw.calendar.games.select("game_id", "kickoff", wd=_weekday(c("kickoff")))
    rows = runs["ecr"].history.join(games, on="game_id")
    assert rows.height and not (rows["wd"] == THURSDAY).any()
    assert (rows["as_of"] < rows["kickoff"]).all()


def test_ecr_s_curve_never_projects_more_for_a_worse_rank(runs, gw):
    model = Ecr().fit(runs["ecr"].features.join(runs["ecr"].targets, on=["gsis_id", "game_id"])
                      .with_columns(weight=pl.lit(1.0)))  # fmt: skip
    for iso in model["curves"].values():
        curve = iso.predict(np.arange(1, 7))
        assert (np.diff(curve) <= 1e-12).all()


def test_the_market_runs_at_kickoff(runs, gw):
    bt = runs["market_margin"]
    rows = bt.history.join(gw.calendar.games.select("game_id", "kickoff"), on="game_id")
    assert rows.height and (rows["as_of"] == rows["kickoff"]).all()
    lines = bt.history.join(bt.features.select("game_id", "spread_line"), on="game_id")
    assert (lines["mean"] == lines["spread_line"]).all()


def test_no_vig_removes_the_margin_proportionally():
    df = pl.DataFrame({"h": [-150, 120, -110], "a": [130, -140, -110]})
    p = df.select(no_vig_home(c("h"), c("a")))["h"].to_list()
    assert p[0] == pytest.approx(0.6 / (0.6 + 100 / 230))
    assert p[1] == pytest.approx((100 / 220) / (100 / 220 + 140 / 240))
    assert p[2] == pytest.approx(0.5)


def test_benchmarks_skip_the_signal_test_and_say_so(gw):
    v = validate(MarketWin(), gw, TEST, shuffles=5, n_cutoffs=3)
    assert v.signal is None
    nine = next(ch for ch in v.checks if ch.number == 9)
    assert nine.passed and "benchmark" in nine.detail
    assert v.passed
    assert v.bt.scored["mean"].is_between(0, 1).all()


@pytest.mark.parametrize("name", ["rolling4", "lasso", "ecr", "market_margin"])
def test_each_baseline_passes_the_blocking_leakage_checks(runs, gw, name):
    checks = leakage.run_checks(runs[name], gw, n_cutoffs=4)
    assert all(ch.passed for ch in checks if ch.blocking), [ch for ch in checks if not ch.passed]


def test_another_scoring_is_another_variant(gw):
    half = scored(RollingAverage, "half")
    assert half.variant == "rolling4_half" and half.quantity == "half_points"
    check_expert(half)
    bt = backtest.run(half(), gw, [2023])
    ppr = backtest.run(RollingAverage(), gw, [2023])
    assert (bt.history["mean"] < ppr.history["mean"]).all()  # standard is 0.9 x PPR here
    with pytest.raises(ValueError, match="one scoring"):
        scored(Ecr, "half")


def test_weighted_quantiles_and_ranges():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    assert weighted_quantiles(x, np.ones(4), [0.5]) == [2.0]
    assert weighted_quantiles(x, np.array([0, 0, 0, 1.0]), [0.1]) == [4.0]
    resid = pl.DataFrame({"g": ["a", "a", "b"], "resid": [-1.0, 1.0, 5.0], "weight": [1.0] * 3})
    off = fit_offsets(resid, ["g"])
    rows = pl.DataFrame({"g": ["a", "z"], "mean": [10.0, 10.0]})
    out = with_ranges(rows, off, ["g"])
    assert out.filter(c("g") == "a")["q90"][0] == 11.0
    assert out.filter(c("g") == "z")["q90"][0] == 15.0  # unseen group: the overall offsets
    assert (with_ranges(rows, fit_offsets(resid))["q50"] == 11.0).all()


def test_a_baseline_is_judged_at_the_model_s_run_but_a_benchmark_at_its_own():
    from pcf.validation.validate import at_run

    sat = at_run(RollingAverage(), "saturday")
    assert sat.run == "saturday" and type(sat).label() == "baselines/rolling4"
    assert at_run(Ecr(), "tuesday").run == "saturday"
    assert at_run(MarketWin(), "tuesday").run == "kickoff"
