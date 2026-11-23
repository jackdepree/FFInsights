# ruff: noqa: E501
"""voe, fifth look (2026-11-22): the CEO's H90 (training on predictable plays), H91 (a slightly
below-average counterexample) and H92 (a simple net for interactions).

The reference is the fourth look's EPA arm, the CEO's design: a lasso on the slot ratings, the
plus-minus sums and context-live's expectations, to the play's EPA, pass and run apart, fit on 2018 to
T-1 and scored on season T (2019-2024). Each arm changes one thing against it. Yardsticks: the
roster-change test (side knockouts) and the movers' repeat of each arm's player values (H90: the plain
plus-minus fit the arm's way; H91 and H92: each slot knocked out on its own). Discovery only,
2016-2024 regular seasons; the 2025 vault not read. Design and pass rules committed before the run
(EXPLORATION.md, "Fifth look"; commit 9c41bae).

Run from pcf/:  python projects/voe/explore/fifth_look.py > projects/voe/explore/fifth_look.txt 2> projects/voe/explore/fifth_look.log
"""

from __future__ import annotations

import math
import pickle
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import polars as pl
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LassoCV
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402
import ratings as rt  # noqa: E402
import success_look as sl  # noqa: E402

c = pl.col
log = fl.log
RNG = np.random.default_rng(22)
CTXC = ["xexp", *[f"ctx_{s}" for s in sl.CTX.values()]]
OGROUPS = [("o", g) for g in ("QB", "RB", "WR", "TE", "OL")] + [
    ("d", g) for g in ("DL", "LB", "DB")
]
NAMED = [
    ("QB", "OL"),
    ("QB", "WR"),
    ("QB", "TE"),
    ("QB", "RB"),
    ("OL", "DL"),
    ("WR", "DB"),
    ("TE", "LB"),
]
F20 = {
    "QB": 0.049,
    "RB": 0.010,
    "WR": 0.014,
    "TE": 0.014,
    "OL": 0.013,
    "DL": 0.011,
    "LB": 0.021,
    "DB": 0.016,
}
SEEDS = (0, 1, 2)
# arm: (features, model, training plays)
ARMS = {
    "ref": ("base", "lasso", "all"),
    "strat": ("base", "lasso", "pred_half"),
    "wvar": ("base", "lasso", "weights"),
    "leak": ("base", "lasso", "close_half"),
    "named": ("named", "lasso", "all"),
    "pairs": ("pairs", "lasso", "all"),
    "mlp": ("base", "mlp", "all"),
    "mlp_w": ("base", "mlp", "weights"),
}
SLOT_ARMS = ("ref", "named", "pairs", "mlp", "mlp_w")
LABEL = {
    "ref": "the reference lasso (the fourth look's EPA arm)",
    "strat": "H90: trained on the predictable half (before the snap)",
    "wvar": "H90 textbook: weighted by 1 / expected variance",
    "leak": "H90 leak: trained on the half closest to expectation (after the fact)",
    "ref_repl": "H91: the reference, against replacement level",
    "named": "H92 rung 2: named interactions",
    "pairs": "H92 rung 3: all pairs of group totals and context",
    "mlp": "H92: the CEO's net (32 units, 3 seeds)",
    "mlp_w": "H92 + H90: the net, weighted by 1 / expected variance",
}


# ---------------------------------------------------------------- plays to slot matrices (rt.build, plus rp by slot and the player rows)
def build5(on, R):
    o = on.filter(c("season").is_in(rt.PLAY_SEASONS)).join(R, on=["gsis_id", "season"], how="left")
    o = o.with_columns(c("rp").fill_null(0.0), c("ra").fill_null(0.0), c("rs").fill_null(0.0))
    keys = (o.select("game_id", "play_id", "season", "week", "posteam", "defteam", "resid", "play_type")
            .unique(["game_id", "play_id"]).sort("season", "game_id", "play_id").with_row_index("ri"))  # fmt: skip
    o = o.join(keys.select("game_id", "play_id", "ri"), on=["game_id", "play_id"])
    o = o.with_columns(k0=c("side").str.slice(0, 1) + "_" + c("position_label").fill_null("x"))
    share = o.group_by("k0").agg(s=pl.len() / keys.height)
    keep = set(share.filter(c("s") >= 0.005)["k0"].to_list())
    o = o.with_columns(
        key=pl.when(c("k0").is_in(list(keep)))
        .then(c("k0"))
        .otherwise(c("side").str.slice(0, 1) + "_" + c("group") + "_x")
    )
    slots = sorted(o["key"].unique().to_list())
    sidx = {k: i for i, k in enumerate(slots)}
    P, S = keys.height, len(slots)
    o = o.with_columns(si=c("key").replace_strict(sidx, return_dtype=pl.Int64))
    ri, si = o["ri"].to_numpy(), o["si"].to_numpy()
    off = o["side"].to_numpy() == "offense"
    sd = {k: float(o[k].std()) for k in ("ra", "rs", "rp")}
    Xa, Xs, Xp, Fm = (np.zeros((P, S), np.float32) for _ in range(4))
    np.add.at(Xa, (ri, si), (o["ra"].to_numpy() / sd["ra"]).astype(np.float32))
    np.add.at(Xs, (ri, si), (o["rs"].to_numpy() / sd["rs"]).astype(np.float32))
    np.add.at(Xp, (ri, si), (o["rp"].to_numpy() / sd["rp"]).astype(np.float32))
    np.add.at(Fm, (ri, si), 1.0)
    sums = {}
    for k in ("ra", "rs", "rp"):
        v = o[k].to_numpy() / sd[k]
        sums[k] = (np.bincount(ri[off], v[off], P), np.bincount(ri[~off], v[~off], P))
    X = np.hstack(
        [
            Xa,
            Xs,
            np.column_stack([sums[k][0] - sums[k][1] for k in ("ra", "rs", "rp")]).astype(
                np.float32
            ),
        ]
    )
    side_o = np.array([k.startswith("o_") for k in slots])
    sg = o.group_by("si").agg(g=c("group").mode().first()).sort("si")["g"].to_list()
    sgroup = [(slots[j][0], sg[j]) for j in range(S)]
    o = o.with_columns(ra_s=c("ra") / sd["ra"], rs_s=c("rs") / sd["rs"], rp_s=c("rp") / sd["rp"])
    log("matrices", P, "plays", S, "slots")
    return (
        keys,
        X,
        Xp,
        Fm,
        sums,
        slots,
        side_o,
        sgroup,
        o.select("ri", "si", "gsis_id", "season", "side", "group", "ra_s", "rs_s", "rp_s"),
    )


# ---------------------------------------------------------------- expected variance, judged before the snap
def expected_variance(pa: pl.DataFrame, ctx: pl.DataFrame) -> pl.DataFrame:
    d = (
        pa.filter(c("season") >= 2017)
        .join(ctx, on=["game_id", "play_id"], how="left")
        .with_columns(v=c("r_epa") ** 2)
    )
    feats = [*fl.SIT, "xepa", *[f"ctx_{s}" for s in sl.CTX.values()]]
    out = []
    for s in rt.PLAY_SEASONS:
        tr, te = d.filter(c("season") < s), d.filter(c("season") == s)
        m = HistGradientBoostingRegressor(
            loss="poisson",
            max_iter=200,
            learning_rate=0.08,
            max_leaf_nodes=31,
            min_samples_leaf=200,
            random_state=0,
        )
        m.fit(tr.select(feats).to_numpy(), tr["v"].to_numpy())
        out.append(
            te.select("game_id", "play_id", vhat=pl.Series(m.predict(te.select(feats).to_numpy())))
        )
        log("expected variance", s)
    return pl.concat(out)


# ---------------------------------------------------------------- features
def group_totals(Xb, S, members):
    """Per play, each (side, group)'s total of ratings (a) and (b): 8 + 8 columns."""
    A = np.column_stack([Xb[:, m].sum(axis=1) for m in members])
    B = np.column_stack([Xb[:, [S + j for j in m]].sum(axis=1) for m in members])
    return A, B


def feats(Xb, Cb, kind, S, members):
    base = np.hstack([Xb[:, : 2 * S + 2], Cb]).astype(np.float64)
    if kind == "base":
        return base
    A, B = group_totals(Xb, S, members)
    if kind == "named":
        T = A + B
        gi = {g: i for i, (_, g) in enumerate(OGROUPS)}
        cols = [T[:, gi[a]] * T[:, gi[b]] for a, b in NAMED]
        off, de = T[:, :5].sum(axis=1), T[:, 5:].sum(axis=1)
        cols += [off * Cb[:, k] for k in range(Cb.shape[1])] + [
            de * Cb[:, k] for k in range(Cb.shape[1])
        ]
        return np.hstack([base, np.column_stack(cols)])
    Z = np.hstack([A, B, Cb])
    return np.hstack(
        [base, np.column_stack([Z[:, i] * Z[:, j] for i, j in combinations(range(Z.shape[1]), 2)])]
    )


# ---------------------------------------------------------------- models
def fit_model(kind, Ztr, y, w, splits):
    if kind == "lasso":
        m = make_pipeline(StandardScaler(), LassoCV(alphas=20, cv=splits, max_iter=5000))
        m.fit(Ztr, y, lassocv__sample_weight=w)
        return [m]
    ms = []
    for s in SEEDS:
        m = make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(32,), alpha=1e-3, batch_size=512, learning_rate_init=1e-3,
                                                         early_stopping=True, validation_fraction=0.15, n_iter_no_change=10, max_iter=200, random_state=s))  # fmt: skip
        m.fit(Ztr, y, mlpregressor__sample_weight=w)
        ms.append(m)
    return ms


def predict(ms, Z):
    return np.mean([m.predict(Z) for m in ms], axis=0)


def slot_knock(ms, kind, Xte, Cte, Xpte, Fte, refa, refb, refp, side_o, S, members, pfull):
    """Each slot knocked out on its own; returns the change (good = +) per held-out play and slot."""
    D = np.zeros((len(Xte), S), np.float32)
    for j in range(S):
        f = np.flatnonzero(Fte[:, j] > 0)
        if len(f) == 0:
            continue
        sg = 1.0 if side_o[j] else -1.0
        Xk = Xte[f].copy()
        Xk[:, 2 * S] -= sg * (Xk[:, j] - refa[j])
        Xk[:, 2 * S + 1] -= sg * (Xk[:, S + j] - refb[j])
        Xk[:, 2 * S + 2] -= sg * (Xpte[f, j] - refp[j])
        Xk[:, j], Xk[:, S + j] = refa[j], refb[j]
        D[f, j] = sg * (pfull[f] - predict(ms, feats(Xk, Cte[f], kind, S, members)))
    return D


def repl_gaps(o, info, T):
    """Replacement level: per (side, group) and rating, the backups' (under 300 plays) average less everyone's, plays-weighted, seasons before T."""
    t = o.filter(c("season") < T).join(
        info.select("gsis_id", "season", "n"), on=["gsis_id", "season"]
    )
    t = t.with_columns(sd=c("side").str.slice(0, 1))
    a = t.group_by("sd", "group").agg(*(c(k).mean().alias(k) for k in ("ra_s", "rs_s", "rp_s")))
    b = (
        t.filter(c("n") < 300)
        .group_by("sd", "group")
        .agg(*(c(k).mean().alias(f"{k}_b") for k in ("ra_s", "rs_s", "rp_s")))
    )
    j = a.join(b, on=["sd", "group"])
    return {
        (r["sd"], r["group"]): tuple(r[f"{k}_b"] - r[k] for k in ("ra_s", "rs_s", "rp_s"))
        for r in j.iter_rows(named=True)
    }


def fit_all(keys, X, Xp, Fm, sums, slots, side_o, sgroup, Cx, y_raw, vhat, o, info):
    S = len(slots)
    members = [[j for j in range(S) if sgroup[j] == g] for g in OGROUPS]
    seas, ptype = keys["season"].to_numpy(), keys["play_type"].to_numpy()
    resid, games = keys["resid"].to_numpy(), keys["game_id"].to_numpy()
    names = [*ARMS, "ref_repl"]
    vo = {m: np.zeros(len(resid)) for m in names}
    vd = {m: np.zeros(len(resid)) for m in names}
    se = {m: np.zeros(len(resid)) for m in [*ARMS, "base"]}
    D = {m: np.zeros((len(resid), S), np.float32) for m in [*SLOT_ARMS, "ref_repl"]}
    test = np.zeros(len(resid), bool)
    diag = []
    for T in rt.TEST:
        gaps = repl_gaps(o, info, T)
        for pt in ("pass", "run"):
            tr = np.flatnonzero((seas < T) & (ptype == pt))
            te = np.flatnonzero((seas == T) & (ptype == pt))
            test[te] = True
            Xtr, Xte, Ftr, Fte = X[tr], X[te], Fm[tr], Fm[te]
            filled = np.maximum((Ftr > 0).sum(axis=0), 1)
            msl = np.concatenate(
                [Xtr[:, :S].sum(axis=0) / filled, Xtr[:, S : 2 * S].sum(axis=0) / filled]
            )
            mp = Xp[tr].sum(axis=0) / filled
            cnt = Ftr.sum(axis=0) / filled  # players in the slot when it is filled
            per_play = Ftr.mean(axis=0)  # players in the slot per play
            gap = np.array([gaps.get(sgroup[j], (0.0, 0.0, 0.0)) for j in range(S)])
            msl_r = msl + np.concatenate([gap[:, 0] * cnt, gap[:, 1] * cnt])
            mp_r = mp + gap[:, 2] * cnt
            smean = {k: (sums[k][0][tr].mean(), sums[k][1][tr].mean()) for k in sums}
            smean_r = {}
            for i, k in enumerate(("ra", "rs", "rp")):
                shift_o = float((gap[side_o, i] * per_play[side_o]).sum())
                shift_d = float((gap[~side_o, i] * per_play[~side_o]).sum())
                smean_r[k] = (smean[k][0] + shift_o, smean[k][1] + shift_d)
            Xo = rt.knock(Xte, Fte, te, side_o, sums, smean, msl, "o", S)
            Xd = rt.knock(Xte, Fte, te, side_o, sums, smean, msl, "d", S)
            Xo_r = rt.knock(Xte, Fte, te, side_o, sums, smean_r, msl_r, "o", S)
            Xd_r = rt.knock(Xte, Fte, te, side_o, sums, smean_r, msl_r, "d", S)
            gcode = np.unique(games[tr], return_inverse=True)[1]
            ytr = y_raw[tr]
            se["base"][te] = (y_raw[te] - ytr.mean()) ** 2
            v = np.clip(vhat[tr], *np.percentile(vhat[tr], [5, 95]))
            wv = (1 / v) / (1 / v).mean()
            for name, (fk, mk, rows) in ARMS.items():
                if rows == "all" or rows == "weights":
                    sub = np.arange(len(tr))
                elif rows == "pred_half":
                    sub = np.flatnonzero(vhat[tr] < np.median(vhat[tr]))
                else:
                    sub = np.flatnonzero(np.abs(resid[tr]) < np.median(np.abs(resid[tr])))
                w = wv[sub] if rows == "weights" else None
                splits = list(GroupKFold(3).split(sub, groups=gcode[sub]))
                Ztr = feats(Xtr[sub], Cx[tr][sub], fk, S, members)
                ms = fit_model(mk, Ztr, ytr[sub], w, splits)
                del Ztr
                pa = predict(ms, feats(Xte, Cx[te], fk, S, members))
                po, pdd = (
                    predict(ms, feats(Xo, Cx[te], fk, S, members)),
                    predict(ms, feats(Xd, Cx[te], fk, S, members)),
                )
                vo[name][te], vd[name][te] = pa - po, pdd - pa
                se[name][te] = (y_raw[te] - pa) ** 2
                if name == "ref":
                    po_r, pd_r = (
                        predict(ms, feats(Xo_r, Cx[te], fk, S, members)),
                        predict(ms, feats(Xd_r, Cx[te], fk, S, members)),
                    )
                    vo["ref_repl"][te], vd["ref_repl"][te] = pa - po_r, pd_r - pa
                    D["ref_repl"][te] = slot_knock(
                        ms,
                        fk,
                        Xte,
                        Cx[te],
                        Xp[te],
                        Fte,
                        msl_r[:S],
                        msl_r[S:],
                        mp_r,
                        side_o,
                        S,
                        members,
                        pa,
                    )
                if name in SLOT_ARMS:
                    D[name][te] = slot_knock(
                        ms,
                        fk,
                        Xte,
                        Cx[te],
                        Xp[te],
                        Fte,
                        msl[:S],
                        msl[S:],
                        mp,
                        side_o,
                        S,
                        members,
                        pa,
                    )
                if mk == "lasso":
                    coef = ms[0][-1].coef_
                    diag.append(
                        (
                            T,
                            pt,
                            name,
                            int((coef != 0).sum()),
                            len(coef),
                            int((coef[2 * S + 2 + len(CTXC) :] != 0).sum()) if fk != "base" else 0,
                            len(sub),
                        )
                    )
                log("fit", T, pt, name)
    return vo, vd, se, D, test, diag


# ---------------------------------------------------------------- the plus-minus, fit the arm's way (H90's yardstick 2)
def rapm_w(rows: pl.DataFrame, alpha: float) -> dict:
    keys = (
        rows.select("game_id", "play_id", "resid", "w")
        .unique(["game_id", "play_id"])
        .with_row_index("r")
    )
    r = rows.join(keys.select("game_id", "play_id", "r"), on=["game_id", "play_id"])
    ids = r["gsis_id"].unique().sort().to_list()
    col = {g: i for i, g in enumerate(ids)}
    ci = np.array([col[g] for g in r["gsis_id"].to_list()])
    sw = np.sqrt(keys["w"].to_numpy())
    sign = np.where(r["side"].to_numpy() == "offense", 1.0, -1.0) * sw[r["r"].to_numpy()]
    X = sp.csr_matrix((sign, (r["r"].to_numpy(), ci)), shape=(keys.height, len(ids)))
    y = keys["resid"].to_numpy()
    y = (y - np.average(y, weights=sw**2)) * sw
    b = lsqr(X, y, damp=math.sqrt(alpha), atol=1e-8, btol=1e-8, iter_lim=3000)[0]
    return dict(zip(ids, b, strict=True))


def pm_arms(on: pl.DataFrame, vh: pl.DataFrame) -> dict:
    q = on.filter(c("season").is_in(rt.PLAY_SEASONS)).join(vh, on=["game_id", "play_id"])
    pk = q.select("game_id", "play_id", "season", "play_type", "resid", "vhat").unique(
        ["game_id", "play_id"]
    )
    pk = pk.with_columns(
        med_v=c("vhat").median().over("season", "play_type"), med_r=c("resid").abs().median().over("season", "play_type"),
        vc=c("vhat").clip(c("vhat").quantile(0.05).over("season"), c("vhat").quantile(0.95).over("season")),
    ).with_columns(wv=1 / c("vc")).with_columns(wv=c("wv") / c("wv").mean().over("season"))  # fmt: skip
    out = {}
    for name, w in (("ref", pl.lit(1.0)), ("strat", (c("vhat") < c("med_v")).cast(pl.Float64)), ("wvar", c("wv")),
                    ("leak", (c("resid").abs() < c("med_r")).cast(pl.Float64))):  # fmt: skip
        pw = pk.select("game_id", "play_id", w=w)
        rows = q.join(pw, on=["game_id", "play_id"]).filter(c("w") > 0)
        out[name] = pl.concat([
            pl.DataFrame({"gsis_id": list(v), "pm": list(v.values())}).with_columns(season=pl.lit(s))
            for s in rt.PLAY_SEASONS for v in [rapm_w(rows.filter(c("season") == s).select("game_id", "play_id", "gsis_id", "side", "resid", "w"), rt.ALPHA)]
        ])  # fmt: skip
        log("plus-minus", name)
    return out


# ---------------------------------------------------------------- scoring
def player_values(D, o, Fm, test_ri):
    t = o.filter(pl.Series(test_ri[o["ri"].to_numpy()]))
    ri, si = t["ri"].to_numpy(), t["si"].to_numpy()
    v = D[ri, si] / Fm[ri, si]
    return (
        t.select("gsis_id", "season")
        .with_columns(v=pl.Series(v))
        .group_by("gsis_id", "season")
        .agg(pm=c("v").mean())
    )


def r(x, y) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def movers(PV: dict, info, team, ref: str = "ref"):
    P = {k: sl.pairs({"pmdf": v, "info": info, "team": team}) for k, v in PV.items()}
    base = P[ref].select("gsis_id", "season", "moved", "group", e=c("pm"), e_n=c("pm_next"))
    res = {}
    for k in PV:
        j = base.join(
            P[k].select("gsis_id", "season", s=c("pm"), s_n=c("pm_next")), on=["gsis_id", "season"]
        )
        out = {}
        for lab, q in (
            ("all", j),
            ("stayed", j.filter(~c("moved"))),
            ("moved", j.filter(c("moved"))),
        ):
            out[lab] = (r(q["s"], q["s_n"]), q.height)
        mv = j.filter(c("moved"))
        ids = mv["gsis_id"].unique().to_list()
        gid = mv["gsis_id"].to_numpy()
        idx = {g: np.flatnonzero(gid == g) for g in ids}
        E, En, Sx, Sn = (mv[x].to_numpy() for x in ("e", "e_n", "s", "s_n"))
        bs = []
        for _ in range(1000):
            pick = np.concatenate([idx[ids[i]] for i in RNG.integers(0, len(ids), len(ids))])
            bs.append(r(Sx[pick], Sn[pick]) - r(E[pick], En[pick]))
        out["diff"] = (r(Sx, Sn) - r(E, En), *np.percentile(bs, [5, 95]))
        out["agree"] = r(j["e"], j["s"])
        res[k] = out
    return res


def paired_travel(tr, V, arm, ref="ref"):
    a0, a1, ka = sl.travel_se(tr, sl.roster(tr, V, arm))
    b0, b1, kb = sl.travel_se(tr, sl.roster(tr, V, ref))
    assert (ka == kb).all() and np.allclose(a0, b0)
    teams = np.unique(ka)
    idx = [np.flatnonzero(ka == k) for k in teams]
    g, lo, hi = sl.gain_ci(a0, a1, ka)
    bs = []
    for _ in range(2000):
        pick = np.concatenate([idx[k] for k in RNG.integers(0, len(teams), len(teams))])
        bs.append(100 * (b1[pick].sum() - a1[pick].sum()) / a0[pick].sum())
    d = 100 * (b1.sum() - a1.sum()) / a0.sum()
    n = len(ka) // 2
    return (
        g,
        lo,
        hi,
        d,
        *np.percentile(bs, [5, 95]),
        100 * (1 - a1[:n].sum() / a0[:n].sum()),
        100 * (1 - a1[n:].sum() / a0[n:].sum()),
    )


def fit_share(se_m, se_r, se_b, games, mask, n=1000):
    gi, g = np.unique(games[mask], return_inverse=True)
    a, b, z = (np.bincount(g, x[mask], len(gi)) for x in (se_m, se_r, se_b))
    est, dif = 1 - a.sum() / z.sum(), (b.sum() - a.sum()) / z.sum()
    bs = []
    for _ in range(n):
        i = RNG.integers(0, len(gi), len(gi))
        bs.append((b[i].sum() - a[i].sum()) / z[i].sum())
    lo, hi = np.percentile(bs, [5, 95])
    return 100 * est, 100 * dif, 100 * lo, 100 * hi


def main() -> None:
    p = sl.plays()
    log("plays", p.height)
    ctx = sl.context()
    pa = p.with_columns(resid=c("r_epa"))
    on = fl.on_field(pa)
    info = fl.player_info(on)
    R, pmdf, _ = rt.make_ratings(pa, on, info)
    keys, X, Xp, Fm, sums, slots, side_o, sgroup, o = build5(on, R)
    vh = expected_variance(p, ctx)
    k2 = keys.select("ri", "game_id", "play_id").join(
        pa.select("game_id", "play_id", "epa", xexp=c("xepa")).join(ctx, on=["game_id", "play_id"], how="left"), on=["game_id", "play_id"], how="left"
    ).join(vh, on=["game_id", "play_id"], how="left").sort("ri")  # fmt: skip
    assert (k2["ri"].to_numpy() == np.arange(keys.height)).all()
    Cx = k2.select([c(x).fill_null(0.0) for x in CTXC]).to_numpy().astype(np.float32)
    vhat = k2["vhat"].to_numpy()
    assert not np.isnan(vhat).any()
    y_raw = k2["epa"].to_numpy()
    team = on.group_by("gsis_id", "season").agg(team=c("team").mode().first())

    print(
        "== EXPECTED VARIANCE (judged before the snap; each season fit on the seasons before it, 2017 on) =="
    )
    rs2 = keys["resid"].to_numpy() ** 2
    for s in (2019, 2024):
        m = keys["season"].to_numpy() == s
        q = np.quantile(vhat[m], [0.5])[0]
        lo, hi = vhat[m] < q, vhat[m] >= q
        print(
            f"  {s}: the predictable half's real squared leftover {rs2[m][lo].mean():.3f} against the rest's {rs2[m][hi].mean():.3f}; r(expected, real) = {r(vhat[m], rs2[m]):.3f}"
        )
    m = keys["play_type"].to_numpy() == "pass"
    print(f"  expected variance: pass plays {vhat[m].mean():.3f}, run plays {vhat[~m].mean():.3f}")

    cache = fl.get_config().zone("interim") / "voe_fifth_look" / "fits.pkl"
    if cache.exists():
        vo, vd, se, PV, test, diag = pickle.loads(cache.read_bytes())
        log("fits read from the cache")
    else:
        vo, vd, se, D, test, diag = fit_all(
            keys, X, Xp, Fm, sums, slots, side_o, sgroup, Cx, y_raw, vhat, o, info
        )
        PV = {k: player_values(D[k], o, Fm, test) for k in D}
        del D
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps((vo, vd, se, PV, test, diag)))

    print(
        "\n== THE LASSOS' CHOICES (2019 and 2024: inputs kept / inputs; interaction terms kept; training plays) =="
    )
    for T, pt, name, k, tot, ki, n in diag:
        if T in (2019, 2024):
            print(f"  {T} {pt:<4} {name:<6}: {k}/{tot} kept; interactions kept {ki}; {n} plays")

    gm = keys["game_id"].to_numpy()
    tm = test
    seas, ptype = keys["season"].to_numpy(), keys["play_type"].to_numpy()
    med_v = np.zeros(len(vhat))
    med_r = np.zeros(len(vhat))
    resid = keys["resid"].to_numpy()
    for T in rt.TEST:
        for pt in ("pass", "run"):
            mm = (seas == T) & (ptype == pt)
            med_v[mm] = np.median(vhat[mm])
            med_r[mm] = np.median(np.abs(resid[mm]))
    sets = {
        "all held-out plays": tm,
        "the predictable half (before the snap)": tm & (vhat < med_v),
        "the half closest to expectation (after the fact)": tm & (np.abs(resid) < med_r),
    }
    print(
        "\n== HELD-OUT PLAY FIT (% of EPA's squared error removed against the training mean; the arm less the reference; 90% by resampling games) =="
    )
    for lab, mask in sets.items():
        print(f"  {lab}:")
        for name in ARMS:
            est, dif, lo, hi = fit_share(se[name], se["ref"], se["base"], gm, mask)
            print(
                f"    {LABEL[name]:<72} {est:+.3f}%  less the reference {dif:+.3f} (90% {lo:+.3f} to {hi:+.3f})"
            )

    print(
        "\n== YARDSTICK 1: THE ROSTER-CHANGE TEST (next-season EPA over expected a play, offense and defense pooled, 2020-2024; % of squared error removed beyond last season; 90% by resampling teams) =="
    )
    V = (
        keys.select("game_id", "play_id", "season", "posteam", "defteam")
        .with_columns(
            *(pl.Series(f"vo_{m}", vo[m]) for m in vo), *(pl.Series(f"vd_{m}", vd[m]) for m in vd)
        )
        .filter(pl.Series(test))
    )
    tr = fl.team_rates(p.filter(c("season").is_in(fl.SEASONS)).with_columns(resid=c("r_epa")))
    for name in [*ARMS, "ref_repl"]:
        g, lo, hi, d, dlo, dhi, go, gd = paired_travel(tr, V, name)
        print(
            f"  {LABEL[name]:<72} {g:+.2f}% (90% {lo:+.2f} to {hi:+.2f}); offense {go:+.2f}%, defense {gd:+.2f}%; less the reference {d:+.2f} points (90% {dlo:+.2f} to {dhi:+.2f})"
        )

    print(
        "\n== YARDSTICK 2: THE MOVERS' REPEAT (this season against next, 300+ plays in both, each season's mean out; the arm less the reference, 90% by resampling players) =="
    )
    print("  H90: the plain plus-minus, fit the arm's way (2018-2024)")
    PM = pm_arms(on, vh)
    res = movers(PM, info, team)
    for k, out in res.items():
        print(
            f"    {LABEL[k]:<72} all {out['all'][0]:+.3f} ({out['all'][1]}); stayed {out['stayed'][0]:+.3f}; moved {out['moved'][0]:+.3f} ({out['moved'][1]}); movers less the reference {out['diff'][0]:+.3f} (90% {out['diff'][1]:+.3f} to {out['diff'][2]:+.3f}); agree with the reference {out['agree']:.3f}"
        )
    print(
        "  H91 and H92: each player's value from the model (each slot knocked out on its own; 2019-2024)"
    )
    res = movers(PV, info, team)
    for k, out in res.items():
        print(
            f"    {LABEL[k]:<72} all {out['all'][0]:+.3f} ({out['all'][1]}); stayed {out['stayed'][0]:+.3f}; moved {out['moved'][0]:+.3f} ({out['moved'][1]}); movers less the reference {out['diff'][0]:+.3f} (90% {out['diff'][1]:+.3f} to {out['diff'][2]:+.3f}); agree with the reference {out['agree']:.3f}"
        )

    print(
        "\n== H91'S SIZING: MAIN STARTERS' VALUE PER PLAY (300+ plays) AGAINST WHAT A MAIN STARTER'S ABSENCE COSTS (F20), EPA a play =="
    )
    gap = {}
    for k in ("ref", "ref_repl"):
        q = (
            PV[k]
            .join(info.select("gsis_id", "season", "n", "group"), on=["gsis_id", "season"])
            .filter(c("n") >= 300)
        )
        row = q.group_by("group").agg(v=c("pm").mean(), n=pl.len())
        vals = {d["group"]: d["v"] for d in row.to_dicts()}
        gap[k] = sum((vals[g] - F20[g]) ** 2 for g in F20)
        print(
            f"  {LABEL[k]:<72} "
            + "; ".join(f"{g} {vals[g]:+.4f} (F20 {F20[g]:.3f})" for g in F20)
            + f"; squared gap {gap[k]:.6f}"
        )
    print(
        f"  the squared gap with replacement level is {100 * (1 - gap['ref_repl'] / gap['ref']):.1f}% smaller than with the average"
    )
    print(
        f"  per-player values, average against replacement level: r = {r(*(PV[k].sort('gsis_id', 'season')['pm'].to_numpy() for k in ('ref', 'ref_repl'))):.4f}"
    )
    log("done")


if __name__ == "__main__":
    main()
