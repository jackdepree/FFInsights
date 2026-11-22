# ruff: noqa: E501
"""voe, fourth look (2026-11-21): the CEO's H89, success (EPA above 0) as VOE's outcome against EPA.

Two arms on the second look's machinery (`ratings.py`), identical except for the outcome: the
leftover, the plain plus-minus, ratings (a) and (b), and the VOE lasso are all built on the arm's
outcome. The VOE lasso's inputs are the slot ratings, the plus-minus sums, the situation
expectation and context-live's back-history expectations (calls16); its target is the outcome
itself. The counterexample (knockout) replaces a side's ratings by each slot's average.

Yardsticks (the CEO: both must improve): the roster-change test on a team's next-season EPA over
expected a play (the same target for both arms), and the movers' repeat of each arm's plain
plus-minus. Discovery only, 2016-2024 regular seasons; the 2025 vault not read. Design and pass
rule committed before the run (EXPLORATION.md, "Fourth look"; commit 856477b).

Run from pcf/:  python projects/voe/explore/success_look.py > projects/voe/explore/success_look.txt
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LassoCV, LinearRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402
import ratings as rt  # noqa: E402

from pcf.data.clean import standard  # noqa: E402
from pcf.experts.context_live import back  # noqa: E402

c = pl.col
log = fl.log
RNG = np.random.default_rng(21)
ARMS = ("epa", "success")
CTX = {"pressure_prob": "pr", "sack_prob": "sk", "completion_prob": "cp",
       "time_to_throw_exp": "tt", "air_yards_exp": "ay", "rush_yards_exp": "ry"}  # fmt: skip
CACHE = fl.get_config().zone("interim") / "voe_success_look"


def plays() -> pl.DataFrame:
    """fl.plays(), with both outcomes and both expectations (each season fit on the six before it)."""
    cols = ["game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "play_type", "two_point_attempt",
            "yardline_100", "down", "ydstogo", "goal_to_go", "qtr", "half_seconds_remaining", "score_differential", "wp", "epa", "desc"]  # fmt: skip
    p = fl.part("play", "pbp", range(2010, 2025), cols)
    p = p.filter((c("season_type") == "REG") & c("play_type").is_in(["run", "pass"]) & (c("two_point_attempt") == 0)
                 & c("posteam").is_not_null() & c("epa").is_not_null()).with_columns(
        c("play_id").cast(pl.Int64), pass_=(c("play_type") == "pass").cast(pl.Float64), succ=(c("epa") > 0).cast(pl.Float64)
    ).rename({"pass_": "pass"})  # fmt: skip
    p = standard.standard_teams(p, "posteam").pipe(standard.standard_teams, "defteam")
    out = []
    for s in fl.SEASONS:
        tr = p.filter(c("season").is_between(s - 6, s - 1))
        te = p.filter(c("season") == s)
        kw = dict(max_iter=200, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=200, random_state=0)
        me = HistGradientBoostingRegressor(**kw).fit(tr.select(fl.SIT).to_numpy(), tr["epa"].to_numpy())
        ms = HistGradientBoostingClassifier(**kw).fit(tr.select(fl.SIT).to_numpy(), tr["succ"].to_numpy())
        x = te.select(fl.SIT).to_numpy()
        out.append(te.with_columns(xepa=pl.Series(me.predict(x)), xsucc=pl.Series(ms.predict_proba(x)[:, 1])))
    p = pl.concat(out).with_columns(r_epa=c("epa") - c("xepa"), r_success=c("succ") - c("xsucc"))
    return p.drop("season_type", "two_point_attempt")


def context() -> pl.DataFrame:
    rep = json.loads((back.cache_dir() / "back_calls16.json").read_text())
    h = pl.read_parquet(rep["path"]).select("game_id", c("play_id").cast(pl.Int64), "quantity", "mean")
    w = h.filter(c("quantity").is_in(list(CTX))).pivot(on="quantity", index=["game_id", "play_id"], values="mean")
    return w.rename({q: f"ctx_{s}" for q, s in CTX.items() if q in w.columns})


def fit(keys, X, Fm, sums, slots, side_o, Cx, y_raw):
    """The second look's fit_all, with the CEO's inputs: the lasso's target is the outcome itself and
    its inputs add the context columns `Cx`; the simple rung is the plain sums on the leftover."""
    S = len(slots)
    seas, ptype = keys["season"].to_numpy(), keys["play_type"].to_numpy()
    resid, games = keys["resid"].to_numpy(), keys["game_id"].to_numpy()
    vo = {m: np.zeros(len(resid)) for m in ("sums", "lasso")}
    vd = {m: np.zeros(len(resid)) for m in ("sums", "lasso")}
    test = np.zeros(len(resid), bool)
    diag = []
    for T in rt.TEST:
        for pt in ("pass", "run"):
            tr = np.flatnonzero((seas < T) & (ptype == pt))
            te = np.flatnonzero((seas == T) & (ptype == pt))
            test[te] = True
            Xtr, Xte, Ftr, Fte = X[tr], X[te], Fm[tr], Fm[te]
            cnt = np.maximum((Ftr > 0).sum(axis=0), 1)
            msl = np.concatenate([Xtr[:, :S].sum(axis=0) / cnt, Xtr[:, S : 2 * S].sum(axis=0) / cnt])
            smean = {k: (sums[k][0][tr].mean(), sums[k][1][tr].mean()) for k in sums}
            Xo = rt.knock(Xte, Fte, te, side_o, sums, smean, msl, "o", S)
            Xd = rt.knock(Xte, Fte, te, side_o, sums, smean, msl, "d", S)
            # the simple rung: plain sums of (a) and (b), on the leftover
            cols = [2 * S, 2 * S + 1]
            m = LinearRegression().fit(Xtr[:, cols], resid[tr])
            pa, po, pdd = m.predict(Xte[:, cols]), m.predict(Xo[:, cols]), m.predict(Xd[:, cols])
            vo["sums"][te], vd["sums"][te] = pa - po, pdd - pa
            # the CEO's design: slots, sums and the context, to the outcome itself
            full = list(range(2 * S + 2))
            Z = lambda A, idx, full=full: np.hstack([A[:, full], Cx[idx]]).astype(np.float64)  # noqa: E731
            gcode = np.unique(games[tr], return_inverse=True)[1]
            splits = list(GroupKFold(3).split(tr, groups=gcode))
            m = make_pipeline(StandardScaler(), LassoCV(alphas=20, cv=splits, max_iter=5000))
            m.fit(Z(Xtr, tr), y_raw[tr])
            pa, po, pdd = m.predict(Z(Xte, te)), m.predict(Z(Xo, te)), m.predict(Z(Xd, te))
            vo["lasso"][te], vd["lasso"][te] = pa - po, pdd - pa
            coef = m[-1].coef_
            diag.append((T, pt, int((coef[: 2 * S] != 0).sum()), 2 * S, float(coef[2 * S]), float(coef[2 * S + 1])))
            log("fit", T, pt)
    return vo, vd, test, diag


def arm(p: pl.DataFrame, name: str, ctx: pl.DataFrame) -> dict:
    path = CACHE / f"{name}.pkl"
    if path.exists():
        log("arm read from the cache", name)
        return pickle.loads(path.read_bytes())
    pa = p.with_columns(resid=c(f"r_{name}"), y_raw=c("epa") if name == "epa" else c("succ"),
                        xexp=c("xepa") if name == "epa" else c("xsucc"))  # fmt: skip
    on = fl.on_field(pa)
    info = fl.player_info(on)
    R, pmdf, _ = rt.make_ratings(pa, on, info)
    keys, X, Fm, sums, slots, side_o = rt.build(on, R)
    k2 = keys.select("game_id", "play_id").join(
        pa.select("game_id", "play_id", "y_raw", "xexp").join(ctx, on=["game_id", "play_id"], how="left"),
        on=["game_id", "play_id"], how="left",
    )  # fmt: skip
    ccols = ["xexp", *[f"ctx_{s}" for s in CTX.values()]]
    Cx = k2.select([c(x).fill_null(0.0) for x in ccols]).to_numpy().astype(np.float32)
    print(f"  {name}: context columns present on {100 * k2['ctx_pr'].is_not_null().mean():.0f}% (pressure) and {100 * k2['ctx_ry'].is_not_null().mean():.0f}% (run yards) of the plays")
    vo, vd, test, diag = fit(keys, X, Fm, sums, slots, side_o, Cx, k2["y_raw"].to_numpy())
    V = keys.select("game_id", "play_id", "season", "posteam", "defteam").with_columns(
        *(pl.Series(f"vo_{m}", vo[m]) for m in vo), *(pl.Series(f"vd_{m}", vd[m]) for m in vd)
    ).filter(pl.Series(test))
    team = on.group_by("gsis_id", "season").agg(team=c("team").mode().first())
    out = {"V": V, "pmdf": pmdf, "info": info, "team": team, "diag": diag}
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(out))
    return out


def roster(tr: pl.DataFrame, V: pl.DataFrame, m: str) -> pl.DataFrame:
    return pl.concat([
        V.group_by(team=c("posteam"), season=c("season")).agg(roster=c(f"vo_{m}").mean()).with_columns(side=pl.lit("offense")),
        V.group_by(team=c("defteam"), season=c("season")).agg(roster=c(f"vd_{m}").mean()).with_columns(side=pl.lit("defense")),
    ])  # fmt: skip


def travel_se(tr: pl.DataFrame, rs: pl.DataFrame):
    """The roster-change test's squared errors, last season alone (se0) and with the roster (se1), 2020-2024."""
    d = tr.join(tr.select("team", "side", season=c("season") + 1, last=c("rate")), on=["team", "season", "side"]).join(
        rs, on=["team", "season", "side"]).sort("side", "season", "team")  # fmt: skip
    se0, se1, keys = [], [], []
    for side in ("offense", "defense"):
        ds = d.filter(c("side") == side)
        for t in range(2020, 2025):
            a, b = ds.filter(c("season") < t), ds.filter(c("season") == t)
            for cols, store in ((["last"], se0), (["last", "roster"], se1)):
                mm = LinearRegression().fit(a.select(cols).to_numpy(), a["rate"].to_numpy())
                store.append((b["rate"].to_numpy() - mm.predict(b.select(cols).to_numpy())) ** 2)
            keys.append((b["team"] + "_" + side).to_numpy())
    return np.concatenate(se0), np.concatenate(se1), np.concatenate(keys)


def gain_ci(se0, se1, keys, n=2000):
    teams = np.unique(keys)
    idx = [np.flatnonzero(keys == k) for k in teams]
    g = 1 - se1.sum() / se0.sum()
    bs = []
    for _ in range(n):
        pick = np.concatenate([idx[k] for k in RNG.integers(0, len(teams), len(teams))])
        bs.append(1 - se1[pick].sum() / se0[pick].sum())
    return 100 * g, *(100 * np.percentile(bs, [5, 95]))


def pairs(a: dict) -> pl.DataFrame:
    """Plain plus-minus this season and next, players with 300+ plays in both, each season's mean out."""
    pm, info, team = a["pmdf"], a["info"], a["team"]
    q = (
        pm.join(info.select("gsis_id", "season", "n", "group"), on=["gsis_id", "season"])
        .join(team, on=["gsis_id", "season"])
        .join(pm.select("gsis_id", season=c("season") - 1, pm_next=c("pm")), on=["gsis_id", "season"])
        .join(info.select("gsis_id", season=c("season") - 1, n_next=c("n")), on=["gsis_id", "season"])
        .join(team.select("gsis_id", season=c("season") - 1, team_next=c("team")), on=["gsis_id", "season"])
        .filter((c("n") >= 300) & (c("n_next") >= 300))
        .with_columns(moved=c("team") != c("team_next"))
    )
    return q.with_columns(c("pm") - c("pm").mean().over("season"), c("pm_next") - c("pm_next").mean().over("season"))


def r(x, y) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def main() -> None:
    p = plays()
    log("plays", p.height)
    ps = p.filter(c("season").is_in(fl.SEASONS))
    print("== THE TWO OUTCOMES, 2016-2024 regular seasons ==")
    print(f"  plays {ps.height}; success rate {ps['succ'].mean():.3f}; EPA a play {ps['epa'].mean():+.3f}")
    for s in (2019, 2024):
        x = ps.filter(c("season") == s)
        print(f"  {s}: the situation explains {100 * (1 - ((x['r_epa']) ** 2).sum() / ((x['epa'] - x['epa'].mean()) ** 2).sum()):.2f}% of EPA's squared error, {100 * (1 - ((x['r_success']) ** 2).sum() / ((x['succ'] - x['succ'].mean()) ** 2).sum()):.2f}% of success's")
    print(f"  the two leftovers agree r = {r(ps['r_epa'].to_numpy(), ps['r_success'].to_numpy()):.3f} per play")
    ctx = context()
    A = {name: arm(p, name, ctx) for name in ARMS}

    print("\n== THE LASSO'S CHOICES (standardized coefficients on the sums of (a) and (b)) ==")
    for name in ARMS:
        print(f"  {name}: " + "; ".join(f"{T} {pt}: {k}/{tot} slot inputs kept, sum (a) {a_:+.4f}, sum (b) {b_:+.4f}" for T, pt, k, tot, a_, b_ in A[name]["diag"] if T in (2019, 2024)))

    print("\n== YARDSTICK 1: THE ROSTER-CHANGE TEST (a team's next-season EPA over expected a play, offense and defense pooled, 2020-2024; % of squared error removed beyond last season; 90% by resampling teams) ==")
    tr = fl.team_rates(ps.with_columns(resid=c("r_epa")))
    se = {}
    for m, lab in (("lasso", "the CEO's design (VOE lasso, knockout)"), ("sums", "the simple rung (plain sums of a and b)")):
        for name in ARMS:
            se0, se1, keys = travel_se(tr, roster(tr, A[name]["V"], m))
            se[(name, m)] = (se0, se1, keys)
            g, lo, hi = gain_ci(se0, se1, keys)
            n = len(keys) // 2
            go = 1 - se1[:n].sum() / se0[:n].sum()
            gd = 1 - se1[n:].sum() / se0[n:].sum()
            print(f"  {lab:<42} {name:>7}: {g:+.2f}% (90% {lo:+.2f} to {hi:+.2f}); offense {100 * go:+.2f}%, defense {100 * gd:+.2f}%")
        a0, a1, ka = se[("success", m)]
        b0, b1, kb = se[("epa", m)]
        assert (ka == kb).all() and np.allclose(a0, b0)
        teams = np.unique(ka)
        idx = [np.flatnonzero(ka == k) for k in teams]
        diff = 100 * ((1 - a1.sum() / a0.sum()) - (1 - b1.sum() / b0.sum()))
        bs = []
        for _ in range(2000):
            pick = np.concatenate([idx[k] for k in RNG.integers(0, len(teams), len(teams))])
            bs.append(100 * ((b1[pick].sum() - a1[pick].sum()) / a0[pick].sum()))
        lo, hi = np.percentile(bs, [5, 95])
        print(f"  {lab:<42} success less EPA: {diff:+.2f} points (90% {lo:+.2f} to {hi:+.2f})")

    print("\n== YARDSTICK 2: THE MOVERS' REPEAT (plain plus-minus this season against next; 300+ plays in both; each season's mean out) ==")
    P = {name: pairs(A[name]) for name in ARMS}
    j = P["epa"].select("gsis_id", "season", "group", "moved", e=c("pm"), e_n=c("pm_next")).join(
        P["success"].select("gsis_id", "season", s=c("pm"), s_n=c("pm_next")), on=["gsis_id", "season"])  # fmt: skip
    for lab, q in (("all", j), ("stayed", j.filter(~c("moved"))), ("moved", j.filter(c("moved")))):
        print(f"  {lab:>6} ({q.height} pairs): EPA {r(q['e'], q['e_n']):+.3f}; success {r(q['s'], q['s_n']):+.3f}")
    mv = j.filter(c("moved"))
    ids = mv["gsis_id"].unique().to_list()
    idx = {g: np.flatnonzero(mv["gsis_id"].to_numpy() == g) for g in ids}
    E, En, Sx, Sn = (mv[k].to_numpy() for k in ("e", "e_n", "s", "s_n"))
    bs = []
    for _ in range(2000):
        pick = np.concatenate([idx[ids[i]] for i in RNG.integers(0, len(ids), len(ids))])
        bs.append(r(Sx[pick], Sn[pick]) - r(E[pick], En[pick]))
    d = r(Sx, Sn) - r(E, En)
    lo, hi = np.percentile(bs, [5, 95])
    print(f"  movers, success less EPA: {d:+.3f} (90% {lo:+.3f} to {hi:+.3f})")
    print("  movers by group (EPA | success): " + "; ".join(
        f"{g} {r(mv.filter(c('group') == g)['e'], mv.filter(c('group') == g)['e_n']):+.2f} | {r(mv.filter(c('group') == g)['s'], mv.filter(c('group') == g)['s_n']):+.2f} (n {mv.filter(c('group') == g).height})"
        for g in fl.GROUPS if mv.filter(c("group") == g).height >= 10))  # fmt: skip
    print(f"  the two arms' plus-minus agree r = {r(j['e'], j['s']):.3f} (player-seasons above)")
    log("done")


if __name__ == "__main__":
    main()
