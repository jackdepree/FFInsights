"""team-efficiency exploration, step 5: H42, double machine learning (DML) to separate
"situationally explained success" from "a team's innate ability".

The partially linear model: a play's EPA = team effects (offense, defense, home) + g(situation) +
noise. DML (Robinson's partialling out) estimates the team effects in two steps:

1. **The outcome model:** g, a play's expected EPA from its situation, a gradient-boosted model
   fitted on 2006-2015 only. The leftover is y~ = EPA - g(situation).
2. **The situation propensity** (the CEO's "propensity" in its classic causal sense, kept apart
   from step 3's representativeness weights): within the season so far, the chance that a play in
   this kind of situation belongs to each offense and each defense (and is at home). It's
   cross-fitted: plays in one half of the games use shares from the other half. The team
   indicators less their propensity, D~, are what's left of "which team" once the situation
   is known.
3. **Team effects** from a ridge regression of y~ on D~, with the same recency weight and prior
   as every other variant.

Two versions of the situation, because the score is partly the team's own doing (a mediator):
- **with game state:** down, distance, field, clock, the score and the win chance (propensity
  bins: win-chance band x half);
- **without game state:** down, distance, field and clock only (bins: down x field third).
And, to see what each step adds, partialling out the outcome model alone (no propensity).

Scored on the main test against all plays equal. Writes h42_dml.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/h42_dml.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"
X_STATE = ["down", "ydstogo", "yardline_100", "half_seconds_remaining", "game_seconds_remaining", "qtr", "score_differential", "wp"]
X_NOSTATE = ["down", "ydstogo", "yardline_100", "half_seconds_remaining", "game_seconds_remaining", "qtr"]
ND = 2 * C.NT + 1  # offense, defense, home
ALPHA = 50.0  # propensity smoothing, in plays


def outcome_model(p: pl.DataFrame, xs: list[str]) -> np.ndarray:
    tr = p.filter(c("season").is_in(C.WEIGHT_FIT))
    m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=500, random_state=0)
    m.fit(tr.select(xs).to_numpy().astype(float), tr["epa"].to_numpy())
    return m.predict(p.select(xs).to_numpy().astype(float))


def cells(p: pl.DataFrame, bin_expr: pl.Expr) -> pl.DataFrame:
    """Per (game, offense, bin): plays and summed y~, with team indices and the cross-fit fold."""
    q = p.with_columns(bin=bin_expr, fold=(c("game_id").hash(7) % 2).cast(pl.Int8))
    g = q.group_by("season", "week", "game_id", "posteam", "defteam", "home", "fold", "bin").agg(n=pl.len().cast(pl.Float64), sy=c("yt").sum())
    return g.with_columns(a=c("posteam").replace_strict(C.TIX), b=c("defteam").replace_strict(C.TIX))


def _dml_fit(rows: np.ndarray, ref_week: float, po: np.ndarray, pd_: np.ndarray, prm: C.Params, wscale: float, nbins: int) -> tuple[np.ndarray, np.ndarray]:
    """rows: week, a, b, home, fold, bin, n, sy. Robinson's regression with cross-fitted
    propensities, ridge toward the prior."""
    if rows.shape[0] == 0:
        return po.copy(), pd_.copy()
    wk, a, b, h, fold, bn, n, sy = (rows[:, i] for i in range(8))
    a, b, fold, bn = a.astype(int), b.astype(int), fold.astype(int), bn.astype(int)
    r = 0.5 ** ((ref_week - wk) / prm.half_life)
    m = n * r
    q = sy * r
    A = np.zeros((ND, ND))
    rhs = np.zeros(ND)
    # Per fold and bin: M, V = sum m D, sum q, sum q D; Q = sum m D D'.
    for f in (0, 1):
        sel_f = fold == f
        oth = ~sel_f
        # The other fold's propensities per bin (smoothed toward its overall shares).
        Vo_all = np.zeros(ND)
        np.add.at(Vo_all, a[oth], m[oth])
        np.add.at(Vo_all, C.NT + b[oth], m[oth])
        Vo_all[2 * C.NT] = (m[oth] * h[oth]).sum()
        Mo_all = m[oth].sum()
        Ebar = Vo_all / Mo_all if Mo_all > 0 else np.zeros(ND)
        for k in range(nbins):
            so = oth & (bn == k)
            Mo = m[so].sum()
            Vo = np.zeros(ND)
            np.add.at(Vo, a[so], m[so])
            np.add.at(Vo, C.NT + b[so], m[so])
            Vo[2 * C.NT] = (m[so] * h[so]).sum()
            E = (Vo + ALPHA * Ebar) / (Mo + ALPHA)
            s = sel_f & (bn == k)
            if not s.any():
                continue
            ms, qs, as_, bs, hs = m[s], q[s], a[s], b[s], h[s]
            M = ms.sum()
            V = np.zeros(ND)
            np.add.at(V, as_, ms)
            np.add.at(V, C.NT + bs, ms)
            V[2 * C.NT] = (ms * hs).sum()
            Q = np.zeros((ND, ND))
            ib = C.NT + bs
            ih = np.full(len(ms), 2 * C.NT)
            for i1, i2, wv in ((as_, as_, ms), (ib, ib, ms), (as_, ib, ms), (ib, as_, ms), (as_, ih, ms * hs), (ih, as_, ms * hs), (ib, ih, ms * hs), (ih, ib, ms * hs), (ih, ih, ms * hs)):
                np.add.at(Q, (i1, i2), wv)
            A += Q - np.outer(V, E) - np.outer(E, V) + M * np.outer(E, E)
            QD = np.zeros(ND)
            np.add.at(QD, as_, qs)
            np.add.at(QD, C.NT + bs, qs)
            QD[2 * C.NT] = (qs * hs).sum()
            rhs += QD - E * qs.sum()
    lam = prm.lam * wscale
    pen = np.full(ND, lam)
    pen[2 * C.NT] = 1e-6
    A[np.diag_indices_from(A)] += pen
    rhs[: C.NT] += lam * po
    rhs[C.NT : 2 * C.NT] += lam * pd_
    th = np.linalg.solve(A, rhs)
    return th[: C.NT], th[C.NT : 2 * C.NT]


def walk_dml(cl: pl.DataFrame, prm: C.Params, nbins: int) -> pl.DataFrame:
    wscale = float(cl.group_by("game_id", "posteam").agg(c("n").sum())["n"].mean())
    out = []
    po, pd_ = np.zeros(C.NT), np.zeros(C.NT)
    for season in C.SEASONS:
        cs = cl.filter(c("season") == season)
        rows = cs.select("week", "a", "b", "home", "fold", "bin", "n", "sy").to_numpy().astype(float)
        last = int(cs["week"].max())
        for w in range(1, last + 1):
            o, d = _dml_fit(rows[rows[:, 0] < w], w, po, pd_, prm, wscale, nbins)
            out.append(pl.DataFrame({"season": season, "week": w, "team": C.TEAMS, "o": o, "d": d}))
        o, d = _dml_fit(rows, last + 1, po, pd_, prm, wscale, nbins)
        po, pd_ = prm.pull * (o - o.mean()), prm.pull * (d - d.mean())
    return pl.concat(out)


def tune_dml(cl, nbins, ufs):
    best, bv = None, np.inf
    for prm in C.GRID:
        r = walk_dml(cl, prm, nbins)
        v = C.mse(C.fit_score(C.predict_frame(r, ufs["next3"]), ["own", "opp", "home"]), C.TUNE)
        if v < bv:
            best, bv, br = prm, v, r
    return best, br, C.score_ratings(br, ufs)


def main() -> None:
    t0 = time.time()
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    p = C.plays()
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    eq = {h: pl.read_parquet(CACHE / f"equal_{h}.parquet") for h in ("next3", "rest")}

    g_state = outcome_model(p, X_STATE)
    g_nost = outcome_model(p, X_NOSTATE)
    later = p["season"].to_numpy() >= 2016
    e = p["epa"].to_numpy()
    for nm, g in (("with game state", g_state), ("without game state", g_nost)):
        say(f"Outcome model {nm}: share of EPA's spread it explains, 2016-2024 (out of sample): {1 - np.var(e[later] - g[later]) / np.var(e[later]):.3%}")

    wpband = pl.when(c("wp") < 0.1).then(0).when(c("wp") < 0.25).then(1).when(c("wp") < 0.4).then(2).when(c("wp") < 0.6).then(3).when(c("wp") < 0.75).then(4).when(c("wp") < 0.9).then(5).otherwise(6)
    state_bins = (wpband * 2 + (c("qtr") > 2).cast(pl.Int32)).cast(pl.Int32)
    nost_bins = ((c("down").fill_null(1).clip(1, 4) - 1) * 3 + (c("yardline_100") / 33.4).floor().clip(0, 2)).cast(pl.Int32)

    results = {}
    for nm, g, bins, nb in (("with game state", g_state, state_bins, 14), ("without game state", g_nost, nost_bins, 12)):
        q = p.with_columns(yt=pl.Series(e - g))
        prm, out = C.tune(C.sides(q, "yt"), sched, ufs)
        results[f"partial out only, {nm}"] = out
        say(f"partial out only, {nm}: settings {prm} ({time.time() - t0:.0f}s)")
        cl = cells(q, bins)
        prm, r, out = tune_dml(cl, nb, ufs)
        results[f"DML, {nm}"] = out | {"_ratings": r}
        r.write_parquet(CACHE / f"ratings_dml_{'state' if 'with' in nm else 'nostate'}.parquet")
        say(f"DML, {nm}: settings {prm} ({time.time() - t0:.0f}s)")

    say("")
    say("The main test, 2016-2024: skill against all plays equal (plain ridge on EPA)")
    for h in ("next3", "rest"):
        for k, v in results.items():
            say(f"  {h:5s} {k:38s} {C.fmt(C.skill(v[h], eq[h]))} | off {C.fmt(C.skill(v[h], eq[h], side='off'))} def {C.fmt(C.skill(v[h], eq[h], side='def'))}")
    say("")
    say("2020-2024 only:")
    for h in ("next3", "rest"):
        for k, v in results.items():
            say(f"  {h:5s} {k:38s} {C.fmt(C.skill(v[h], eq[h], seasons=list(range(2020, 2025))))}")
    say("")
    say("How far DML moves the ratings from plain ridge (end of season, 2016-2024; EPA per play):")
    er = pl.read_parquet(CACHE / "equal_ratings.parquet")
    for k in ("DML, with game state", "DML, without game state"):
        r = results[k]["_ratings"]
        j = r.join(er, on=["season", "week", "team"], suffix="_eq").filter(c("season") >= 2016)
        j = j.filter(c("week") == c("week").max().over("season"))
        say(f"  {k}: r with plain ridge offense {np.corrcoef(j['o'], j['o_eq'])[0, 1]:.3f}, defense {np.corrcoef(j['d'], j['d_eq'])[0, 1]:.3f}; spread (sd) offense {j['o'].std():.3f} against {j['o_eq'].std():.3f}, defense {j['d'].std():.3f} against {j['d_eq'].std():.3f}")
    (HERE / "h42_dml.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
