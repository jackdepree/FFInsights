"""stabilization: the filter, the in-season centring and class, the point-in-time checkpoints
(PFR's lag), the stand-in correction, the opponents' usual and the gains, on synthetic rows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from pcf.experts.stabilization import correct as Co
from pcf.experts.stabilization import drift as F
from pcf.experts.stabilization import evaluate as E
from pcf.experts.stabilization import history as Hs
from pcf.experts.stabilization import inseason as I
from pcf.experts.stabilization import opponents as O
from pcf.experts.stabilization import rates as R
from pcf.experts.stabilization import standins as St

c = pl.col
T0 = datetime(2018, 9, 9, 17, tzinfo=UTC)


def _games(
    players: int = 60,
    seasons=(2017, 2018, 2019),
    weeks: int = 12,
    lag_days: float = 0.5,
    seed: int = 0,
) -> pl.DataFrame:
    """Player-games of one measure: fixed true rates, binomial outcomes, one game a week."""
    rng = np.random.default_rng(seed)
    true = np.clip(rng.normal(0.2, 0.05, players), 0.02, 0.9)
    rows = []
    for s in seasons:
        for i in range(players):
            for wk in range(1, weeks + 1):
                kick = T0.replace(year=s) + timedelta(days=7 * (wk - 1))
                den = float(rng.integers(15, 40))
                rows.append(
                    {
                        "gsis_id": f"p{i:02d}",
                        "game_id": f"{s}_{wk:02d}_{i}",
                        "season": s,
                        "week": wk,
                        "team": f"T{i % 8}",
                        "pos": "WR" if i % 2 else "TE",
                        "num": float(rng.binomial(int(den), true[i])),
                        "den": den,
                        "kickoff": kick,
                        "known_at": kick + timedelta(days=lag_days),
                    }
                )
    return pl.DataFrame(rows)


def test_the_filter_without_drift_is_static_m1():
    """q = q_s = 0: the local-level filter's level is every past attempt pooled, pulled by k."""
    df = pl.DataFrame(
        {
            "gsis_id": ["a"] * 4,
            "season": [2018, 2018, 2019, 2019],
            "week": [1, 2, 1, 2],
            "d": [0.1, -0.05, 0.2, 0.0],
            "n": [20.0, 30.0, 25.0, 10.0],
        }
    )
    L = F.pad(df, "gsis_id")
    sigma2, tau2 = 0.16, 0.004
    m, P, _, _ = F.run(L, 0.0, 0.0, sigma2, tau2)
    n, d = df["n"].to_numpy(), df["d"].to_numpy()
    k = sigma2 / tau2
    want = np.cumsum(n * d) / (np.cumsum(n) + k)
    np.testing.assert_allclose(m[0], want, rtol=1e-9)
    np.testing.assert_allclose(P[0], sigma2 / (np.cumsum(n) + k), rtol=1e-9)


def test_drift_forgets_the_past():
    df = pl.DataFrame(
        {
            "gsis_id": ["a"] * 3,
            "season": [2018] * 3,
            "week": [1, 2, 3],
            "d": [0.3, 0.3, -0.3],
            "n": [30.0] * 3,
        }
    )
    L = F.pad(df, "gsis_id")
    static = F.run(L, 0.0, 0.0, 0.16, 0.004)[0][0, -1]
    moving = F.run(L, 0.004, 0.0, 0.16, 0.004)[0][0, -1]
    assert moving < static  # the last game counts more when the level drifts


def test_in_season_centring_uses_last_seasons_mean_and_the_first_games_class():
    g = _games()
    # player p01 switches class late in 2018: his class there must stay his first game's
    g = g.with_columns(
        pos=pl.when((c("gsis_id") == "p01") & (c("season") == 2018) & (c("week") > 3))
        .then(pl.lit("TE"))
        .otherwise(c("pos"))
    )
    rows = R.season_rows(g)
    gc = I.centred_games(g, rows, "gsis_id", "pos")
    p01 = gc.filter((c("gsis_id") == "p01") & (c("season") == 2018))
    assert p01["pos"].unique().to_list() == ["WR"]
    mu17 = R.class_means(rows).filter((c("pos") == "WR") & (c("season") == 2017))["mu"][0]
    assert p01["mu"].unique().to_list() == pytest.approx([mu17])


def _frame(g: pl.DataFrame, lagged: bool, T: int = 2019):
    rows = R.season_rows(g)
    return I.season_frame(g, rows, T, lagged=lagged)[0].filter(c("season") == T)


def test_checkpoints_ignore_the_future():
    g = _games()
    full = _frame(g, lagged=False)
    cut = T0.replace(year=2019) + timedelta(days=7 * 7 + 1)  # after week 8
    late = c("known_at") > cut
    g2 = g.with_columns(num=pl.when(late).then(c("den") * 0.99).otherwise(c("num")))
    scr = _frame(g2, lagged=False)
    a = full.filter(c("next_kick") <= cut).select("gsis_id", "gi", "m1", "m", "P", "N")
    b = scr.select("gsis_id", "gi", m1_b="m1", m_b="m", P_b="P", N_b="N")
    j = a.join(b, on=["gsis_id", "gi"])
    assert j.height > 0
    for x in ("m1", "m", "P", "N"):
        np.testing.assert_allclose(j[x], j[f"{x}_b"], rtol=1e-12)
    # and the scored targets after the cutoff did change, so the test can see a leak
    assert not np.allclose(
        full.filter(c("gi") == 8)["y"].drop_nulls(), scr.filter(c("gi") == 8)["y"].drop_nulls()
    )


def test_pfr_lag_reads_only_games_known_by_the_next_kickoff():
    g = _games(lag_days=9.0)  # known after the next game has kicked off
    cp = _frame(g, lagged=True)
    assert (cp["gi_known"] < cp["gi"]).all()  # always one game behind
    used = (
        g.sort("gsis_id", "season", "week")
        .with_columns(gi_known=pl.int_range(1, pl.len() + 1).over("gsis_id", "season"))
        .select("gsis_id", "season", "gi_known", known_used="known_at")
    )
    j = cp.join(used, on=["gsis_id", "season", "gi_known"], how="inner")
    assert j.height > 0 and (j["known_used"] <= j["next_kick"]).all()
    on_time = _frame(_games(lag_days=0.5), lagged=True)
    assert (on_time["gi_known"] == on_time["gi"]).all()


def test_stand_in_correction_uses_last_seasons_ratio():
    g = pl.DataFrame(
        {
            "gsis_id": ["a"] * 2 + ["b"] * 2,
            "season": [2018, 2019] * 2,
            "pos": ["RB"] * 4,
            "exact": [80.0, 50.0, 100.0, 100.0],
            "standin": [100.0, 100.0, 100.0, 100.0],
        }
    )
    out = St.corrected(g).sort("gsis_id", "season")
    a19 = out.filter((c("gsis_id") == "a") & (c("season") == 2019))
    # last season: his ratio 0.8 and the position's 0.9, pulled with 200 attempts' weight
    want = (80 + 200 * 0.9) / (100 + 200) * 100
    assert a19["corr"][0] == pytest.approx(want)
    assert out.filter(c("season") == 2018)["corr"].to_list() == pytest.approx([100.0, 100.0])


def test_opponents_usual_is_known_before_the_game():
    rng = np.random.default_rng(0)
    rows = []
    for s in (2018, 2019):
        for i in range(8):
            for wk in range(1, 9):
                rows.append(
                    {
                        "team": f"T{i}",
                        "season": s,
                        "week": wk,
                        "game_id": f"{s}{i}{wk}",
                        "side": "off",
                        "measure": "shotgun",
                        "den": 60.0,
                        "num": float(rng.binomial(60, 0.3 + 0.05 * (i - 4) / 4)),
                    }
                )
    tg = pl.DataFrame(rows)
    u = O.opponent_usual(tg, "shotgun", k=300.0)
    # week 8 changed for two teams, the league's total kept: no earlier usual may move
    wk8 = (c("week") == 8) & (c("season") == 2019)
    tg2 = tg.with_columns(
        num=pl.when(wk8 & (c("team") == "T0"))
        .then(c("num") + 20)
        .when(wk8 & (c("team") == "T1"))
        .then(c("num") - 20)
        .otherwise(c("num"))
    )
    u2 = O.opponent_usual(tg2, "shotgun", k=300.0)
    j = (
        u.join(u2, on=["team", "game_id"], suffix="_2")
        .join(tg.select("team", "game_id", "season", "week"), on=["team", "game_id"])
        .filter(~((c("season") == 2019) & (c("week") == 8)))
    )
    np.testing.assert_allclose(j["usual"], j["usual_2"], atol=1e-12)
    first = u.join(tg.select("team", "game_id", "season", "week"), on=["team", "game_id"])
    assert first.filter((c("season") == 2018) & (c("week") == 1))["usual"].abs().max() < 1e-12


def test_gain_and_its_interval():
    rng = np.random.default_rng(0)
    y = rng.normal(size=400)
    f = pl.DataFrame(
        {
            "gsis_id": [f"p{i % 80}" for i in range(400)],
            "y": y,
            "w": 1.0,
            "good": y + rng.normal(scale=0.3, size=400),
            "bad": np.zeros(400),
        }
    )
    g = E.gain(f, "good", "bad", seed=1)
    assert g.gain > 0.8 and g.clear and not g.worse
    assert E.gain(f, "bad", "bad", seed=1).gain == pytest.approx(0.0)
    assert E.sse_gain(f, "good", "bad") == pytest.approx(g.gain)


def test_history_scale_uses_earlier_seasons_only():
    rng = np.random.default_rng(3)
    n = 400
    season = np.repeat([2018, 2019, 2020], n)
    y = rng.normal(scale=2.0, size=3 * n)  # the misses are twice the stated sd
    f = pl.DataFrame({"season": season, "y": y, "_fc": 0.0, "_var": 1.0, "mean": 0.0, "_w": 1.0})
    out = Hs.history_scale(f)
    sc = out.group_by("season").agg(pl.col("range_scale").first()).sort("season")
    assert sc["range_scale"][0] == pytest.approx(1.0)  # nothing earlier
    assert sc["range_scale"][1] == pytest.approx(2.0, rel=0.15)
    f2 = f.with_columns(y=pl.when(pl.col("season") == 2020).then(99.0).otherwise(pl.col("y")))
    out2 = Hs.history_scale(f2)  # a later season's misses change no earlier scale
    np.testing.assert_allclose(out2["range_scale"].to_numpy(), out["range_scale"].to_numpy())
    cov = out.filter(pl.col("season") > 2018)["_cov"].mean()
    assert 0.74 < cov < 0.86


def test_run_snap_correction_uses_last_season_and_the_floor():
    games = pl.DataFrame(
        {
            "gsis_id": ["a", "a", "b", "b"],
            "game_id": ["g1", "g2", "g3", "g4"],
            "season": [2017, 2018, 2017, 2018],
            "pos": ["RB"] * 4,
            "num": [10.0, 12.0, 2.0, 2.0],
            "den": [10.0, 10.0, 10.0, 10.0],
        }
    )
    exact = pl.DataFrame(
        {
            "gsis_id": ["a", "a", "b", "b"],
            "game_id": ["g1", "g2", "g3", "g4"],
            "run_snaps": [15.0, 999.0, 5.0, 999.0],  # 2018's counts can't touch 2018's ratio
        }
    )
    out = Co.corrected_games(games, exact, "run_snaps", floor=False).sort("game_id")
    r17 = out.filter(pl.col("season") == 2017)["ratio_used"].to_list()
    assert r17 == pytest.approx([1.0, 1.0])  # no completed season before 2017 here
    pos = 20.0 / 20.0  # the position's 2017 ratio
    a18 = out.filter(pl.col("game_id") == "g2")["ratio_used"][0]
    assert a18 == pytest.approx((15.0 + Co.PRIOR * pos) / (10.0 + Co.PRIOR))
    floored = Co.corrected_games(games, exact, "run_snaps", floor=True)
    assert (floored["den"] >= floored["num"]).all()  # never more carries than run snaps
