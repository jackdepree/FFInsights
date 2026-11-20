# ruff: noqa: E501
"""voe, second look, checks (2026-11-20). Discovery only, 2016-2024.

1. Why the first small MLP failed (ratings.txt: -47% of a held-out play), and a fair refit:
   - inputs: the slot ratings are already in rating-spread units, so they aren't standardized again
     (standardizing a slot that is filled on 0.5% of plays makes its filled values 10+ units wide);
   - early stopping on the last training season (out of time), not a random slice of plays;
   - two MLPs: one on the lasso's inputs, one on the four side sums only (beside a linear fit on
     the same four).
2. The new-player question: the roster-change test uses who actually played, so a rating that marks
   new players below average can score by counting how many new players a team had to use. Does
   the sums' gain survive with that share in the baseline?

Run from pcf/:  python projects/voe/explore/mlp_check.py > projects/voe/explore/mlp_check.txt
"""

from __future__ import annotations

import copy
import pickle
import sys
import warnings
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402
import ratings as rt  # noqa: E402

c = pl.col
log = fl.log
SEEDS = (0, 1, 2)
RNG = np.random.default_rng(13)


class Const:
    """Early stopping's epoch 0: predict the training average (kept when no epoch beats it on validation)."""

    def __init__(self, v):
        self.v = v

    def predict(self, X):
        return np.full(len(X), self.v)


def fit_mlp(Xa, ya, Xv, yv, seed, hidden=(32,), alpha=1.0, epochs=60, patience=6):
    m = MLPRegressor(hidden_layer_sizes=hidden, alpha=alpha, batch_size=512, learning_rate_init=5e-4,
                     max_iter=1, warm_start=True, random_state=seed)  # fmt: skip
    base = float(((yv - ya.mean()) ** 2).mean())
    best, bm, bad, ep = base, Const(float(ya.mean())), 0, 0  # epoch 0: the training average
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        for ep in range(1, epochs + 1):  # noqa: B007
            m.fit(Xa, ya)
            v = float(((yv - m.predict(Xv)) ** 2).mean())
            if v < best - 1e-7:
                best, bm, bad = v, copy.deepcopy(m), 0
            else:
                bad += 1
            if bad >= patience:
                break
    return bm, ep, 100 * (1 - best / base)


def travel_cols(tr, rs, cols, base_extra, label, start=2020):
    d = tr.join(
        tr.select("team", "side", season=c("season") + 1, last=c("rate")),
        on=["team", "season", "side"],
    ).join(rs, on=["team", "season", "side"])
    for side in ["offense", "defense"]:
        ds = d.filter(c("side") == side).sort("season")
        se0, se1, keys = [], [], []
        for t in range(start, 2025):
            a, b = ds.filter(c("season") < t), ds.filter(c("season") == t)
            if b.height == 0 or a.height == 0:
                continue
            for cc, store in ((["last", *base_extra], se0), (["last", *base_extra, *cols], se1)):
                m = LinearRegression().fit(a.select(cc).to_numpy(), a["rate"].to_numpy())
                store.append((b["rate"].to_numpy() - m.predict(b.select(cc).to_numpy())) ** 2)
            keys.append(b["team"].to_numpy())
        se0, se1, keys = np.concatenate(se0), np.concatenate(se1), np.concatenate(keys)
        gain = 1 - se1.sum() / se0.sum()
        teams = np.unique(keys)
        idx = [np.flatnonzero(keys == k) for k in teams]
        bs = [
            1 - se1[p_].sum() / se0[p_].sum()
            for p_ in (
                np.concatenate([idx[k] for k in RNG.integers(0, len(teams), len(teams))])
                for _ in range(1000)
            )
        ]
        lo, hi = np.percentile(bs, [5, 95])
        print(
            f"    {label:<58} {side}: {100 * gain:+.2f}% (90% {100 * lo:+.2f} to {100 * hi:+.2f})"
        )


def main():
    p = fl.plays()
    on = fl.on_field(p)
    info = fl.player_info(on)
    pp = p.filter(c("season").is_in(fl.SEASONS))
    R, pmdf, pmp = rt.make_ratings(p, on, info)
    keys, X, Fm, sums, slots, side_o = rt.build(on, R)
    S = len(slots)
    seas, ptype, y, games = (
        keys["season"].to_numpy(),
        keys["play_type"].to_numpy(),
        keys["resid"].to_numpy(),
        keys["game_id"].to_numpy(),
    )
    weeks = keys["week"].to_numpy()

    print("== 1a. WHY THE FIRST MLP FAILED (2024 pass plays, seed 1, the first configuration) ==")
    tr = np.flatnonzero((seas < 2024) & (ptype == "pass"))
    te = np.flatnonzero((seas == 2024) & (ptype == "pass"))
    full = list(range(2 * S + 2))
    sc = StandardScaler().fit(X[tr][:, full])
    Zte = sc.transform(X[te][:, full])
    fill = (Fm[tr] > 0).mean(axis=0)
    worst = np.abs(Zte).max(axis=0)
    j = int(np.argmax(worst))
    print(
        f"  the largest standardized input on a held-out play: {worst[j]:.1f} units, in column {slots[j % S] if j < 2 * S else 'a sum'} (filled on {fill[j % S]:.2%} of training plays)"
    )
    print(
        f"  held-out plays with any input beyond 8 units: {(np.abs(Zte) > 8).any(axis=1).mean():.1%}"
    )
    m = make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(32,), alpha=1e-3, batch_size=512, learning_rate_init=1e-3,
                      early_stopping=True, validation_fraction=0.15, n_iter_no_change=10, max_iter=200, random_state=1))  # fmt: skip
    m.fit(X[tr][:, full], y[tr])
    pr = m.predict(X[te][:, full])
    q = np.percentile(pr, [1, 50, 99])
    print(
        f"  its predictions: 1% {q[0]:+.2f}, median {q[1]:+.2f}, 99% {q[2]:+.2f}, largest {np.abs(pr).max():.1f} EPA (a play's leftover has sd {y[te].std():.2f}); {(np.abs(pr) > 1).mean():.1%} of plays predicted beyond 1 EPA either way"
    )
    print(
        f"  the training mean is {y[tr].mean():+.3f}; the predictions' mean {pr.mean():+.3f}, sd {pr.std():.3f}"
    )

    print("\n== 1b. THE REFIT: out-of-time early stopping, slot inputs not restandardized ==")
    cache = fl.get_config().zone("interim") / "voe_second_look_fits.pkl"
    se, vo, vd, test, diag, names = pickle.loads(cache.read_bytes())
    Z4 = np.column_stack([sums["ra"][0], sums["ra"][1], sums["rs"][0], sums["rs"][1]])
    new = {k: np.zeros(len(y)) for k in ("mlp_fix", "mlp_sums", "ols_sums4")}
    nvo = {k: np.zeros(len(y)) for k in new}
    nvd = {k: np.zeros(len(y)) for k in new}
    seed_se = {f"{k}{s}": np.zeros(len(y)) for k in ("mlp_fix", "mlp_sums") for s in SEEDS}
    for T in rt.TEST:
        for pt in ("pass", "run"):
            trall = (seas < T) & (ptype == pt)
            te = np.flatnonzero((seas == T) & (ptype == pt))
            if T - 1 >= 2019:
                fit_i, val_i = (
                    np.flatnonzero(trall & (seas < T - 1)),
                    np.flatnonzero(trall & (seas == T - 1)),
                )
            else:
                fit_i, val_i = (
                    np.flatnonzero(trall & (weeks < 13)),
                    np.flatnonzero(trall & (weeks >= 13)),
                )
            tri = np.flatnonzero(trall)
            cnt = np.maximum((Fm[tri] > 0).sum(axis=0), 1)
            msl = np.concatenate(
                [X[tri][:, :S].sum(axis=0) / cnt, X[tri][:, S : 2 * S].sum(axis=0) / cnt]
            )
            smean = {k: (sums[k][0][tri].mean(), sums[k][1][tri].mean()) for k in sums}
            Xte = X[te]
            Xo = rt.knock(Xte, Fm[te], te, side_o, sums, smean, msl, "o", S)
            Xd = rt.knock(Xte, Fm[te], te, side_o, sums, smean, msl, "d", S)
            scale = np.ones(2 * S + 2, np.float32)
            scale[2 * S :] = X[tri][:, 2 * S : 2 * S + 2].std(axis=0)
            mu4, sd4 = Z4[tri].mean(axis=0), Z4[tri].std(axis=0)
            Z4te = Z4[te]
            Z4o, Z4d = Z4te.copy(), Z4te.copy()
            Z4o[:, 0], Z4o[:, 2] = mu4[0], mu4[2]
            Z4d[:, 1], Z4d[:, 3] = mu4[1], mu4[3]
            # the linear fit on the same four sums
            lm = LinearRegression().fit(Z4[tri], y[tri])
            a_, o_, d_ = lm.predict(Z4te), lm.predict(Z4o), lm.predict(Z4d)
            new["ols_sums4"][te], nvo["ols_sums4"][te], nvd["ols_sums4"][te] = (
                (y[te] - a_) ** 2,
                a_ - o_,
                d_ - a_,
            )
            for name in ("mlp_fix", "mlp_sums"):
                outs, eps, vals = [], [], []
                for s in SEEDS:
                    if name == "mlp_fix":
                        f = lambda M, sc_=scale: M[:, full] / sc_  # noqa: E731
                        mm, ep, vg = fit_mlp(f(X[fit_i]), y[fit_i], f(X[val_i]), y[val_i], s)
                        o3 = (mm.predict(f(Xte)), mm.predict(f(Xo)), mm.predict(f(Xd)))
                    else:
                        g = lambda M, mu_=mu4, sd_=sd4: (M - mu_) / sd_  # noqa: E731
                        mm, ep, vg = fit_mlp(
                            g(Z4[fit_i]), y[fit_i], g(Z4[val_i]), y[val_i], s, hidden=(16,)
                        )
                        o3 = (mm.predict(g(Z4te)), mm.predict(g(Z4o)), mm.predict(g(Z4d)))
                    seed_se[f"{name}{s}"][te] = (y[te] - o3[0]) ** 2
                    outs.append(o3)
                    eps.append(ep)
                    vals.append(vg)
                a_, o_, d_ = (np.mean([o[i] for o in outs], axis=0) for i in range(3))
                new[name][te], nvo[name][te], nvd[name][te] = (y[te] - a_) ** 2, a_ - o_, d_ - a_
                log(name, T, pt, "epochs", eps, "validation gain %", [round(v, 3) for v in vals])
    lab = {"lasso": "VOE lasso, slots and sums (from ratings.txt)", "sums": "plain sums (a)+(b), linear (from ratings.txt)",
           "ols_sums4": "linear on the four side sums", "mlp_fix": "small MLP refit, the lasso's inputs (3 seeds)",
           "mlp_sums": "small MLP, the four side sums (3 seeds)"}  # fmt: skip
    print(
        "  held-out plays 2019-2024, share of a play's EPA over expected explained (90% by resampling games):"
    )
    for k in ("lasso", "sums"):
        e = rt.r2_ci(se[k][test], se["base"][test], games[test])
        print(f"    {lab[k]:<52} {e[0]:+.3f}% ({e[1]:+.3f} to {e[2]:+.3f})")
    for k in ("ols_sums4", "mlp_fix", "mlp_sums"):
        e = rt.r2_ci(new[k][test], se["base"][test], games[test])
        print(f"    {lab[k]:<52} {e[0]:+.3f}% ({e[1]:+.3f} to {e[2]:+.3f})")
    for k, v in seed_se.items():
        print(f"      seed: {k:<12} {100 * (1 - v[test].sum() / se['base'][test].sum()):+.3f}%")

    print("\n  the roster-change test (2020-2024):")
    trt = fl.team_rates(pp)
    V = keys.filter(pl.Series(test))
    allv = {**{k: (vo[k], vd[k]) for k in ("lasso", "sums")}, **{k: (nvo[k], nvd[k]) for k in new}}
    tv = keys.with_columns(
        *(pl.Series(f"vo_{k}", v[0]) for k, v in allv.items()),
        *(pl.Series(f"vd_{k}", v[1]) for k, v in allv.items()),
    ).filter(pl.Series(test))
    team_vals = pl.concat([
        tv.group_by(team=c("posteam"), season=c("season")).agg(*(c(f"vo_{k}").mean().alias(k) for k in allv)).with_columns(side=pl.lit("offense")),
        tv.group_by(team=c("defteam"), season=c("season")).agg(*(c(f"vd_{k}").mean().alias(k) for k in allv)).with_columns(side=pl.lit("defense")),
    ])  # fmt: skip
    newshare = (
        on.filter(c("season").is_in(rt.TEST))
        .join(R.select("gsis_id", "season", "new"), on=["gsis_id", "season"])
        .group_by("team", "season", "side")
        .agg(share_new=c("new").mean())
    )
    team_vals = team_vals.join(newshare, on=["team", "season", "side"])
    for k in ("ols_sums4", "mlp_fix", "mlp_sums"):
        travel_cols(trt, team_vals, [k], [], lab[k])

    print("\n== 2. THE NEW-PLAYER QUESTION (the roster-change test, 2020-2024) ==")
    travel_cols(
        trt, team_vals, ["share_new"], [], "share of plays by players new that season, alone"
    )
    pmpdf = pl.concat(
        [
            pl.DataFrame({"gsis_id": list(v), "pm": list(v.values())}).with_columns(
                season=pl.lit(s)
            )
            for s, v in pmp.items()
        ]
    )
    team_vals = team_vals.join(
        fl.roster_sum(on, pmpdf, "pm").select("team", "season", "side", pmp_roster=c("roster")),
        on=["team", "season", "side"],
    )
    lab["pmp_roster"] = "first look's plus-minus with prior, roster sum"
    for k in ("pmp_roster", "sums", "lasso"):
        travel_cols(trt, team_vals, [k], [], f"{lab[k]}, against last season only")
        travel_cols(
            trt,
            team_vals,
            [k],
            ["share_new"],
            f"{lab[k]}, against last season + the new-player share",
        )
    print("  the own-stats rating's new-player values by group (season 2024's model; player-plays): " + "; ".join(
        f"{g} new {R.filter((c('season') == 2024) & (c('new') == 1)).join(info.select('gsis_id', 'season', 'group'), on=['gsis_id', 'season']).filter(c('group') == g)['rs'].mean():+.4f} vs known {R.filter((c('season') == 2024) & (c('new') == 0)).join(info.select('gsis_id', 'season', 'group'), on=['gsis_id', 'season']).filter(c('group') == g)['rs'].mean():+.4f}" for g in rt.GROUPS))  # fmt: skip

    print("\n== THE MISSED-QB CHECK FOR THE REFIT MODELS (2019-2024) ==")
    rt.qb_games(on, V.with_columns(*(pl.Series(f"vo_{k}", nvo[k][test]) for k in new)), list(new))
    log("done")


if __name__ == "__main__":
    main()
