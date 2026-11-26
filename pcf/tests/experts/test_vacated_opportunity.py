"""vacated opportunity (decision 0050): the walk's point-in-time grid, the plus-minus's design,
the Saturday chance a top player plays, the choice model and the offseason gate, on synthetic rows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from pcf.experts.vacated_opportunity import choice as C
from pcf.experts.vacated_opportunity import common as K
from pcf.experts.vacated_opportunity import live as L
from pcf.experts.vacated_opportunity import offseason as O
from pcf.experts.vacated_opportunity import rates as R

c = pl.col
KICK = datetime(2019, 9, 8, 17, tzinfo=UTC)


def _tg(weeks: int = 6, team: str = "AAA", season: int = 2019) -> pl.DataFrame:
    return pl.DataFrame({
        "game_id": [f"{season}_{w:02d}_{team}" for w in range(1, weeks + 1)], "team": team,
        "season": pl.Series([season] * weeks, dtype=pl.Int32), "week": list(range(1, weeks + 1)),
        "kickoff": [KICK + timedelta(days=7 * (w - 1)) for w in range(1, weeks + 1)], "coach": "X",
    })  # fmt: skip


def _pg(tg: pl.DataFrame, shares: dict[str, list[float | None]], group: str = "WR") -> pl.DataFrame:
    rows = []
    for pid, v in shares.items():
        for (gid, wk), s in zip(tg.select("game_id", "week").iter_rows(), v, strict=True):
            if s is not None:
                rows.append({"gsis_id": pid, "game_id": gid, "season": 2019, "week": wk, "team": "AAA",
                             "group": group, "snaps": 60.0 * s, "share": s, "tgt_share": s / 4,
                             "car_share": 0.0})  # fmt: skip
    return pl.DataFrame(rows).with_columns(c("season").cast(pl.Int32))


# ---------------------------------------------------------------- the walk's grid
def test_grid_is_point_in_time():
    tg = _tg()
    a = {
        "p1": [0.9, 0.9, 0.8, 0.9, 0.9, 0.9],
        "p2": [0.5, 0.6, None, 0.5, 0.6, 0.5],
        "p3": [0.2, 0.3, 0.4, 0.2, 0.3, 0.2],
    }
    b = {k: v[:4] + [0.0 if x is None else min(1.0, x + 0.3) for x in v[4:]] for k, v in a.items()}
    ga = L.grid(_pg(tg, a), tg, 2019)
    gb = L.grid(_pg(tg, b), tg, 2019)
    feats = ["gsis_id", "week", "n", "cs", "share_td", "sd_share", "rank", "top"]
    early_a = ga.filter(c("week") <= 5).select(feats).sort("gsis_id", "week")
    early_b = gb.filter(c("week") <= 5).select(feats).sort("gsis_id", "week")
    assert early_a.equals(early_b)  # changing weeks 5-6 moves nothing known before week 5's kickoff
    row = ga.filter((c("gsis_id") == "p2") & (c("week") == 4)).row(0, named=True)
    assert row["n"] == 2 and row["share_td"] == pytest.approx(0.55)  # week 3 missed: not counted
    assert ga.filter((c("gsis_id") == "p2") & (c("week") == 3))["played"].item() is False


# ---------------------------------------------------------------- the plus-minus's design
def test_design_recovers_a_planted_rate():
    rng = np.random.default_rng(3)
    rows, ab = [], []
    for t in range(40):
        team = f"T{t}"
        base = {f"{team}_w{i}": rng.uniform(0.3, 0.7) for i in range(3)}
        for g in range(16):
            gid = f"{team}_{g}"
            out = rng.random() < 0.3
            if out:
                ab.append(
                    {
                        "j": f"{team}_top",
                        "team": team,
                        "game_id": gid,
                        "group_j": "WR",
                        "w_share": 0.9,
                    }
                )
            for pid, b in base.items():
                y = b + (0.3 * 0.9 if out else 0.0) + rng.normal(0, 0.02)
                rows.append(
                    {
                        "gsis_id": pid,
                        "team": team,
                        "season": 2019,
                        "game_id": gid,
                        "group": "WR",
                        "share": y,
                    }
                )
    d = R.design(pl.DataFrame(rows), pl.DataFrame(ab), "share", "w_share", ("WR",), pair=False)
    b = R.ridge(d.X, d.y, 0.1)
    assert dict(zip(d.keys, b, strict=True))["WR>WR"] == pytest.approx(0.3, abs=0.02)


# ---------------------------------------------------------------- the Saturday chance he plays
def test_chances_follow_the_rules():
    top = pl.DataFrame({
        "gsis_id": ["off", "res", "av", "late", "old"], "game_id": "g", "team": "AAA",
        "season": pl.Series([2019, 2019, 2019, 2019, 2015], dtype=pl.Int32), "week": 3, "kickoff": KICK,
    })  # fmt: skip
    rep = pl.DataFrame(
        {
            "gsis_id": ["late", "old"],
            "game_id": "g",
            "team": "AAA",
            "status": ["Questionable", "Doubtful"],
        }
    )
    ros = pl.DataFrame({"gsis_id": ["res", "av", "late"], "team": "AAA", "season": pl.Series([2019] * 3, dtype=pl.Int32),
                        "week": 3, "reserve": [True, False, False]})  # fmt: skip
    avail = pl.DataFrame({"gsis_id": ["av", "late"], "game_id": "g", "p_play": [0.6, 0.2],
                          "as_of": [KICK - timedelta(hours=20), KICK + timedelta(hours=1)]})  # fmt: skip
    fb = {"none": 0.94, "Questionable": 0.73, "Doubtful": 0.005, "Out": 0.0}
    t = L.chances(top, rep, ros, avail, fb)
    got = {r["gsis_id"]: (r["p_play"], r["p_src"]) for r in t.iter_rows(named=True)}
    assert got["off"] == (0.0, "off_roster")  # not on the 53 or a reserve list that week
    assert got["res"] == (0.0, "reserve")
    assert got["av"] == (0.6, "availability")
    assert got["late"] == (0.73, "report")  # availability's row was made after kickoff: not used
    assert got["old"] == (0.005, "report")  # before 2016 there's no roster_week to read


# ---------------------------------------------------------------- the choice model
def _toy_arrays(seed: int = 0) -> C.Arrays:
    rng = np.random.default_rng(seed)
    play, ps, nest, chosen, out_ch = [], [], [], [], []
    for p in range(60):
        members = rng.choice(6, size=4, replace=False)
        pick = rng.integers(-1, 4)
        for i, m in enumerate(members):
            play.append(p)
            ps.append(int(m))
            nest.append(int(m) % 3)
            chosen.append(i == pick)
        out_ch.append(pick == -1)
    return C.Arrays(
        np.array(play), np.array(ps), np.array(nest), np.array(chosen), np.array(out_ch), 60, 6
    )


def test_choice_gradient_matches_finite_differences():
    a = _toy_arrays()
    lam = np.array([0.6, 0.85, 1.0])
    theta = np.random.default_rng(1).normal(0, 0.5, a.n_ps + C.OUT)
    f0, g = C._loglik(theta, a, lam, 1.0)
    num = np.zeros_like(theta)
    for i in range(theta.size):
        e = np.zeros_like(theta)
        e[i] = 1e-6
        num[i] = (
            C._loglik(theta + e, a, lam, 1.0)[0] - C._loglik(theta - e, a, lam, 1.0)[0]
        ) / 2e-6
    assert np.isfinite(f0)
    assert np.allclose(g, num, atol=1e-5)


def test_divert_keeps_shares_and_favours_the_nest():
    target = np.array([0.25, 0.15, 0.15, 0.1])  # WR, WR, TE, RB
    snap = np.array([0.9, 0.8, 0.8, 0.6])
    nest = np.array([0, 0, 1, 2])
    lam = np.array([0.5, 1.0, 1.0])
    same = C.divert(target, snap, snap, nest, lam)
    assert np.allclose(same, target, atol=1e-6)  # no on-field change, no change in shares
    gone = C.divert(target, snap, np.array([0.0, 0.8, 0.8, 0.6]), nest, lam)
    gain = gone - target
    assert gone[0] < 0.01  # the absent WR gets nothing
    assert (gain[1:] > 0).all()
    assert gain[1] / target[1] > gain[2] / target[2]  # his nest-mate gains more, per unit of share


# ---------------------------------------------------------------- the offseason gate
def test_offseason_gate():
    st = pl.DataFrame({
        "gsis_id": ["wr_a", "wr_b", "ol_a"], "team": "AAA", "season": pl.Series([2019] * 3, dtype=pl.Int32),
        "group": ["WR", "WR", "OL"], "pkey": ["WR", "WR", "OL"], "with_": [0.5, 0.4, 0.8],
        "intake": [False, True, True],
    })  # fmt: skip
    dep = pl.DataFrame({"team": "AAA", "pkey": ["WR", "OL"], "j": ["wr_gone", "ol_gone"], "group_j": ["WR", "OL"],
                        "wj": [0.9, 0.95]})  # fmt: skip
    fit = R.Fit({"WR>WR": 0.2, "OL>OL": 0.1, "wr_a>wr_gone>2019": 0.05}, 1.0, 2019)
    f = O.forecast(st, dep, fit, K.GROUPS).sort("gsis_id")
    r = {x["gsis_id"]: x for x in f.iter_rows(named=True)}
    assert r["wr_a"]["f_pm"] == pytest.approx(0.5 + 0.9 * (0.2 + 0.05))  # pooled + his pair part
    assert r["wr_a"]["f_gate"] == pytest.approx(r["wr_a"]["f_pm"])  # left empty: the plus-minus
    assert r["wr_b"]["f_gate"] == pytest.approx(0.4)  # a top WR came in: no change
    assert r["ol_a"]["f_gate"] == pytest.approx(0.8 + 0.95 * 0.1)  # the lines aren't gated
    assert r["wr_a"]["f_prop"] == pytest.approx(
        0.5 + 0.9 * 0.5 / 0.9
    )  # the proportional split, for reference
