"""opportunity-quality on the synthetic league (decision 0041): participation's world plus an
opportunity part where each player's chances follow his skill, so there's signal to find. Also the
regression measure's maths on hand-made rows."""

import numpy as np
import polars as pl
import pytest

from pcf.core.contract import check_expert, find_all
from pcf.data.gateway import END_OF_TIME, FrameSource, Gateway
from pcf.experts.opportunity_quality import regression as R
from pcf.experts.opportunity_quality.common import fp, known_games, xfp
from pcf.experts.opportunity_quality.horizons import HORIZONS, window_mean
from pcf.experts.opportunity_quality.model import VARIANTS, Counts, Eff, Last4
from pcf.validation import backtest, leakage
from pcf.validation.validate import validate

from ..validation import world
from .test_participation_models import _parts as participation_parts

c = pl.col
UTC = pl.Datetime("us", "UTC")
KEYS = ["gsis_id", "game_id"]


def _parts() -> dict:
    parts = participation_parts()
    roster = parts[("player_game", "roster")]
    snaps = parts[("player_game", "snaps")].select(*KEYS, "offense_pct")
    skill = world.players().select("gsis_id", "skill")
    k = world.cal().games.select("game_id", "kickoff")
    rng = np.random.default_rng(3)
    rows = (
        roster.filter(c("position").is_in(["RB", "WR", "TE"]))
        .join(k, on="game_id")
        .join(skill, on="gsis_id")
        .join(snaps, on=KEYS, how="left")
    )
    n = rows.height
    played = rows["offense_pct"].is_not_null().to_numpy()
    tgt = np.where(played, rng.poisson(rows["skill"].to_numpy() / 2), 0).astype(float)
    car = np.where(played, rng.poisson(1.0, n), 0).astype(float)
    catch_exp = 0.65 * tgt
    opp = rows.select(
        *KEYS, "season",
        oq_chances=pl.Series(tgt + car), oq_targets=pl.Series(tgt), oq_carries=pl.Series(car),
        oq_catches=pl.Series(np.round(catch_exp + rng.normal(0, 1, n)).clip(0, tgt)),
        oq_rec_yards=pl.Series(8 * catch_exp + rng.normal(0, 5, n)),
        oq_rush_yards=pl.Series(4 * car), oq_rec_tds=pl.lit(0.0), oq_rush_tds=pl.lit(0.0),
        oq_catch_exp=pl.Series(catch_exp), oq_rec_yards_exp=pl.Series(8 * catch_exp),
        oq_rush_yards_exp=pl.Series(4 * car), oq_rec_td_exp=pl.Series(0.04 * tgt),
        oq_rush_td_exp=pl.Series(0.03 * car), oq_gl_carries=pl.lit(0.0), oq_rz_targets=pl.lit(0.0),
        oq_ez_targets=pl.lit(0.0), oq_deep_targets=pl.Series(np.floor(tgt / 4)),
        oq_air_yards=pl.Series(8 * tgt), oq_yac_oe=pl.Series(rng.normal(0, 2, n)),
        oq_yac_n=pl.Series(np.round(catch_exp)),
        known_at=(c("kickoff") + pl.duration(hours=24)).cast(UTC),
    )  # fmt: skip
    return {**parts, ("player_game", "opportunity"): opp}


@pytest.fixture(scope="module")
def gateway() -> Gateway:
    return Gateway(FrameSource(_parts()), world.cal())


def test_every_variant_meets_the_contract():
    found = {x.variant for x in find_all("opportunity-quality")}
    assert found >= set(VARIANTS) | set(HORIZONS)
    for cls in [*VARIANTS.values(), *HORIZONS.values()]:
        check_expert(cls)


def test_points_in_any_scoring_add_up():
    row = pl.DataFrame({
        "oq_catch_exp": [2.0], "oq_rec_yards_exp": [30.0], "oq_rush_yards_exp": [10.0],
        "oq_rec_td_exp": [0.2], "oq_rush_td_exp": [0.1], "oq_catches": [3.0],
        "oq_rec_yards": [40.0], "oq_rush_yards": [5.0], "oq_rec_tds": [1.0], "oq_rush_tds": [0.0],
    })  # fmt: skip
    assert row.select(xfp("ppr")).item() == pytest.approx(2 + 4 + 1.8)
    assert row.select(xfp("standard")).item() == pytest.approx(4 + 1.8)
    assert row.select(fp("half")).item() == pytest.approx(1.5 + 4.5 + 6)
    with pytest.raises(ValueError, match="no scoring"):
        xfp("superflex")


def _games(gateway, season=2023, week=4) -> pl.DataFrame:
    return (
        world.cal()
        .games.filter((c("season") == season) & (c("week") == week))
        .select("game_id", "season", "week", "kickoff")
    )


def test_the_features_know_only_earlier_games(gateway):
    games = _games(gateway)
    moment = games["kickoff"].min() - pl.duration(hours=30)
    moment = pl.select(moment).item()
    view = gateway.view(moment, "in_season", Eff.inputs)
    f = Eff().features(view, games)
    assert set(f["position"]) <= {"RB", "WR", "TE"} and f.height
    # this week's own chances can't be an input: change them and nothing moves
    parts = _parts()
    opp = parts[("player_game", "opportunity")]
    parts[("player_game", "opportunity")] = opp.with_columns(
        oq_catch_exp=pl.when(c("game_id").is_in(games["game_id"].implode()))
        .then(99.0)
        .otherwise(c("oq_catch_exp"))
    )
    other = Gateway(FrameSource(parts), world.cal()).view(moment, "in_season", Eff.inputs)
    g = Eff().features(other, games)
    assert f.sort(KEYS).equals(g.sort(KEYS))
    assert all(col in f.columns for col in Eff.columns)


def test_the_target_counts_a_benched_game_as_zero(gateway):
    pg = gateway.view(END_OF_TIME, "in_season", Eff.inputs).table("player_game")
    y = Eff().target(gateway.view(END_OF_TIME, "in_season", Eff.inputs))
    assert y.height == known_games(pg).height
    out = y.join(
        _parts()[("player_game", "opportunity")].filter(c("oq_chances") == 0).select(KEYS), on=KEYS
    )
    assert out.height and (out["y"] == 0).all()


@pytest.mark.parametrize("cls", [Eff, Counts])
def test_the_spike_forecast_beats_shuffling_and_passes_the_leakage_checks(gateway, cls):
    v = validate(cls(), gateway, seasons=[2022, 2023], baselines=[Last4()], shuffles=20,
                 n_cutoffs=4,
                 refit="season")  # fmt: skip
    assert v.signal.passed
    assert all(ch.passed for ch in v.checks if ch.blocking), [
        (ch.name, ch.detail) for ch in v.checks if not ch.passed
    ]
    h = v.bt.history
    assert {"p_nonzero", "if_nonzero_mean"} <= set(h.columns)
    assert (h["q10"] <= h["q50"]).all() and (h["q50"] <= h["q90"]).all()


def test_a_horizon_runs_through_the_harness(gateway):
    bt = backtest.run(HORIZONS["eff_h3"](), gateway, seasons=[2023], refit="season")
    assert bt.scored.height and (bt.scored["q10"] >= 0).all()
    checks = leakage.run_checks(bt, gateway, None, n_cutoffs=3, seed=1)
    assert all(ch.passed for ch in checks if ch.blocking)


def test_a_window_counts_a_missing_week_as_zero_and_waits_for_its_last_game():
    sched = pl.DataFrame({
        "game_id": ["g1", "g2", "g3", "g4"], "season": [2020] * 4, "week": [1, 2, 3, 4],
        "game_type": ["REG"] * 4, "home_team": ["A"] * 4, "away_team": ["B"] * 4,
    })  # fmt: skip
    t = pl.datetime(2020, 9, 1, time_zone="UTC")
    rows = pl.DataFrame({
        "gsis_id": ["p", "q", "p", "p"], "game_id": ["g1", "g2", "g3", "g4"], "season": [2020] * 4,
        "week": [1, 2, 3, 4], "team": ["A"] * 4, "value": [6.0, 1.0, 3.0, 9.0],
    }).with_columns(known_at=pl.select(t).item())  # fmt: skip
    out = window_mean(rows, sched, KEYS, 3).filter(c("gsis_id") == "p")
    assert out["game_id"].to_list() == ["g1"]  # g3 and g4 don't have 3 games left
    assert out["y"][0] == pytest.approx((6 + 0 + 3) / 3)  # week 2: no row, counts 0
    rest = window_mean(rows, sched, KEYS, None).filter(c("gsis_id") == "p")
    assert rest.filter(c("game_id") == "g3")["y"][0] == pytest.approx(6.0)
    # a window whose last game nobody has a row for yet isn't scored
    assert window_mean(rows.filter(c("game_id") != "g3"), sched, KEYS, 3).height == 0


# ---------------------------------------------------------------- the regression measure
def _pg(n_players=60, seasons=(2015, 2016, 2017, 2018), seed=0) -> pl.DataFrame:
    """Player-games where each player has a true level per chance (spread 0.1) and each chance a
    spread of 1: the kept share should rise with chances."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_players):
        level = rng.normal(0, 0.1)
        chances = rng.integers(2, 12)
        for s in seasons:
            for w in range(1, 17):
                k = int(rng.poisson(chances))
                rows.append(
                    (
                        f"p{i}",
                        f"{s}_{w}_{i}",
                        s,
                        w,
                        "WR",
                        float(k),
                        float(k),
                        0.0,
                        float(rng.normal(level * k, np.sqrt(max(k, 1)))),
                        0.0,
                    )
                )
    cols = ["gsis_id", "game_id", "season", "week", "position", "chances", "targets", "carries",
            "poe", "yac"]  # fmt: skip
    return pl.DataFrame(rows, schema=cols, orient="row")


def _spread(seasons=(2015, 2016, 2017, 2018)) -> pl.DataFrame:
    return pl.DataFrame({
        "season": list(seasons), "position": ["WR"] * len(seasons),
        "kind": ["target"] * len(seasons),
        "n": [10_000] * len(seasons), "m1": [0.0] * len(seasons), "m2": [1.0] * len(seasons),
        "y1": [0.0] * len(seasons), "y2": [0.04] * len(seasons),
    })  # fmt: skip


def test_the_window_holds_only_earlier_games_and_the_future_only_later_ones():
    pg = _pg()
    win = R.windows(pg)
    first = win.filter((c("gsis_id") == "p0") & (c("season") == 2016)).sort("week")
    p0 = pg.filter(c("gsis_id") == "p0")
    last_season = p0.filter(c("season") == 2015)["chances"].sum()
    assert first["n"][0] == last_season  # week 1: last season only
    assert first["m"][0] == p0.filter(c("season") == 2016)["chances"].sum()
    # deleting the future leaves every window unchanged
    cut = R.windows(pg.filter((c("season") < 2016) | ((c("season") == 2016) & (c("week") <= 8))))
    both = win.join(cut, on=KEYS, suffix="_cut")
    assert both.height and (both["n"] == both["n_cut"]).all()
    assert (both["poe_w"] - both["poe_w_cut"]).abs().max() < 1e-9


def test_kept_share_rises_with_chances_and_the_parameters_see_only_earlier_seasons():
    pg = _pg()
    win, ps = R.windows(pg), R.player_seasons(pg)
    params = R.fit(win, ps, _spread(), 2018)
    assert params["seasons"] == list(range(2012, 2018))
    tau = params["pos"]["WR"]["tau2"] ** 0.5
    assert 0.03 < tau < 0.2  # the true spread is 0.1
    rows = R.measure(R.scored(win.filter(c("season") == 2018)), params)
    small, big = rows.filter(c("n") < 60)["k_B"].mean(), rows.filter(c("n") > 150)["k_B"].mean()
    assert small < big
    assert (rows["true_q10"] <= rows["mean_B"]).all() and (rows["mean_B"] <= rows["true_q90"]).all()
    assert rows["p_close_B"].is_between(0, 1).all()
    # changing the test season's outcomes changes no parameter
    shaken = pg.with_columns(
        poe=pl.when(c("season") == 2018).then(c("poe") * -5).otherwise(c("poe"))
    )
    p2 = R.fit(R.windows(shaken), R.player_seasons(shaken), _spread(), 2018)
    assert p2["pos"]["WR"] == pytest.approx(params["pos"]["WR"])


def test_game_noise_is_one_for_independent_chances_and_more_when_games_swing():
    """I101: φ ≈ 1 when chances are independent (`_pg`), above 1 when a whole game moves
    together, and it lowers B's kept share."""
    pg = _pg(n_players=120)
    sig = R._pooled(_spread(), [2015, 2016, 2017])
    ps = R.player_seasons(pg.filter(c("season") < 2018))
    assert R.game_noise(pg.filter(c("season") < 2018), ps, sig)["WR"] == pytest.approx(1.0, abs=0.1)
    rng = np.random.default_rng(1)
    swung = pg.with_columns(
        poe=c("poe") + pl.Series(rng.normal(0, 1.5, pg.height)) * c("chances").sqrt()
    )
    ps2 = R.player_seasons(swung.filter(c("season") < 2018))
    phi = R.game_noise(swung.filter(c("season") < 2018), ps2, sig)["WR"]
    assert phi > 2.0  # the chance-level spread is 1, the game adds 1.5² per chance
    win, ps_all = R.windows(swung), R.player_seasons(swung)
    plain, noisy = R.fit(win, ps_all, _spread(), 2018), R.fit(win, ps_all, _spread(), 2018, swung)
    assert noisy["pos"]["WR"]["phi"] == pytest.approx(phi, rel=0.2)
    assert plain["pos"]["WR"]["phi"] == 1
    rows = R.scored(win.filter(c("season") == 2018))
    assert R.measure(rows, noisy)["k_B"].mean() < R.measure(rows, plain)["k_B"].mean()


def test_a_gap_closes_when_the_future_lands_on_the_near_side_of_half_of_it():
    d = pl.DataFrame(
        {"gap": [0.4, 0.4, -0.4, -0.4], "future": [0.1, 0.3, -0.1, -0.3]}
    ).with_columns(half=c("gap") / 2)
    assert d.select(R.closed()).to_series().to_list() == [True, False, True, False]
    cal = R.fit_platt(np.array([0.2, 0.4, 0.6, 0.8] * 50), np.array([0, 0, 1, 1] * 50))
    assert R.platt(cal, np.array([0.8]))[0] > 0.8
