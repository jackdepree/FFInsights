"""Stabilization, method 2a (EXPLORATION.md): the CEO's hunches H113 (teammates prop rates up or
hold them down) and H114 (a consistent measure sets where the others regress to). Discovery only,
2006-2024; the 2025 vault is closed.

Run from pcf/:  python projects/stabilization/explore/m2_hunches.py   (writes m2_hunches.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import RidgeCV

sys.path.insert(0, str(Path(__file__).parent))
from stab_common import MEASURES, Say, boot_gain, fit_m1, load, player_seasons  # noqa: E402

c = pl.col
RNG = np.random.default_rng(1)
say = Say(Path(__file__).with_suffix(".txt"))

# H113: the teammates' conditions each group's rates are read against (pre-registered)
COND = {"hs": "the team's hit-or-sack rate allowed", "oc": "the passer's completion over expected to other players",
        "pr": "the team's pass rate over expected", "op": "the rest of the defense's pressures a dropback",
        "ocat": "the rest of the coverage's catch rate allowed"}  # fmt: skip
COND_OF = {**{m: ["hs", "oc", "pr"] for m in ("tprr", "yprr", "adot", "catch_oe", "yac_oe")},
           **{m: ["op"] for m in ("press_per_snap", "hits_per_snap")},
           **{m: ["ocat"] for m in ("tgt_per_cov", "catch_allowed", "adot_allowed", "missed_tackle")}}  # fmt: skip
# H114: the consistent measures (season r >= 0.5 in method 1) each rate's target is predicted from
CONSISTENT = {"receiver": ["tprr", "yprr", "adot"], "back": ["car_per_run", "tprr", "yprr", "adot"],
              "qb": ["hitsack", "scramble"], "rusher": ["hits_per_snap"], "coverage": ["tgt_per_cov"]}  # fmt: skip


def first_of(s, m):
    return int(s.filter(c("measure") == m)["season"].min())


class Fits:
    """M1's k and position-season means, cached by (measure, before)."""

    def __init__(self, s, game):
        self.s, self.game, self.cache = s, game, {}
        self.psm = (s.filter((c("den") >= 10) & c("pos").is_not_null()).group_by("measure", "pos", "season")
                    .agg(mu=c("num").sum() / c("den").sum(), m=pl.len()).filter(c("m") >= 20).drop("m"))  # fmt: skip

    def k(self, m, before):
        if (m, before) not in self.cache:
            self.cache[(m, before)] = fit_m1(self.s, self.game, m, before)
        return self.cache[(m, before)]


def season_dev(s, fits, m, before):
    """Each player-season of m: x, n, its position-season mean, and M1's pulled deviation n/(n+k)(x - mu)."""
    k = fits.k(m, before)[3]
    d = s.filter(c("measure") == m).join(fits.psm.filter(c("measure") == m).drop("measure"), on=["pos", "season"])
    return d.select("gsis_id", "season", "pos", "team", x=c("num") / c("den"), n="den", mu="mu").with_columns(
        dev=c("n") / (c("n") + k) * (c("x") - c("mu")))


# ---------------------------------------------------------------- H113


def player_cond(game, cond, m, keys):
    """The player's teammates' conditions over his games of measure m, centred by the season's mean."""
    g = game.filter(c("measure") == m).select("gsis_id", "game_id", "season").join(cond, on=["gsis_id", "game_id"])
    out = None
    for k in keys:
        a = g.drop_nulls([f"{k}_n", f"{k}_d"]).filter(c(f"{k}_d") > 0).group_by("gsis_id", "season").agg(v=c(f"{k}_n").sum() / c(f"{k}_d").sum(), d=c(f"{k}_d").sum())
        lm = a.group_by("season").agg(lm=(c("v") * c("d")).sum() / c("d").sum())
        a = a.join(lm, on="season").select("gsis_id", "season", **{k: c("v") - c("lm")})
        out = a if out is None else out.join(a, on=["gsis_id", "season"], how="inner")
    return out


def team_cond(cond, game, keys):
    """Team-season conditions (every roster player's rows: about the team's total), centred by season."""
    seas = game.select("game_id", "season").unique()
    g = cond.join(seas, on="game_id")
    out = None
    for k in keys:
        a = g.drop_nulls([f"{k}_n", f"{k}_d"]).filter(c(f"{k}_d") > 0).group_by("team", "season").agg(v=c(f"{k}_n").sum() / c(f"{k}_d").sum(), d=c(f"{k}_d").sum())
        lm = a.group_by("season").agg(lm=(c("v") * c("d")).sum() / c("d").sum())
        a = a.join(lm, on="season").select("team", "season", **{k: c("v") - c("lm")})
        out = a if out is None else out.join(a, on=["team", "season"], how="inner")
    return out


def wls(X, y, w):
    Xi = np.column_stack([np.ones(len(y)), X])
    W = w / w.sum()
    return np.linalg.solve(Xi.T @ (Xi * W[:, None]), Xi.T @ (W * y))


def h113(s, game, fits, cond):
    say("", "## H113: do teammates prop a player's rates up or hold them down?", "",
        "**Real:** a player's change in rate (each season centred by its position's mean) regressed on the change in his teammates' conditions (centred by the season's mean),",
        "weighted by 1/(1/n1 + 1/n2), players resampled (1,000 draws, 90% intervals). Receivers: the three conditions together. Effects in the rate's units per 1 unit of the condition,",
        "and per a typical change (the condition's spread of changes, 1 sd).", "",
        "| Measure | Condition | Pairs | Movers | Effect per typical change | 90% interval | Clear of 0 | Movers only (per typical change) |", "|---|---|---|---|---|---|---|---|")
    real_rows, clear = [], 0
    pc_cache = {}
    for m, keys in COND_OF.items():
        d = season_dev(s, fits, m, 2025)
        pc = player_cond(game, cond, m, keys)
        pc_cache[m] = pc
        a = d.join(pc, on=["gsis_id", "season"])
        pr = a.join(a.with_columns(c("season") - 1), on=["gsis_id", "season"], suffix="2").filter((c("n") >= 10) & (c("n2") >= 10))
        if pr.height < 100:
            continue
        dy = ((pr["x2"] - pr["mu2"]) - (pr["x"] - pr["mu"])).to_numpy()
        dX = np.column_stack([(pr[f"{k}2"] - pr[k]).to_numpy() for k in keys])
        w = (1 / (1 / pr["n"] + 1 / pr["n2"])).to_numpy()
        mover = (pr["team"] != pr["team2"]).to_numpy()
        b = wls(dX, dy, w)[1:]
        ids = pr["gsis_id"].to_numpy()
        uid, inv = np.unique(ids, return_inverse=True)
        groups = [np.flatnonzero(inv == i) for i in range(len(uid))]
        bs = []
        for _ in range(1000):
            pick = np.concatenate([groups[i] for i in RNG.integers(0, len(uid), len(uid))])
            bs.append(wls(dX[pick], dy[pick], w[pick])[1:])
        bs = np.array(bs)
        bm = wls(dX[mover], dy[mover], w[mover])[1:] if mover.sum() > 50 else np.full(len(keys), np.nan)
        sd = dX.std(0)
        for j, k in enumerate(keys):
            lo, hi = np.quantile(bs[:, j], [0.05, 0.95])
            ok = lo > 0 or hi < 0
            clear += ok
            real_rows.append((m, k, b[j], lo, hi, ok))
            say(f"| {m} | {COND[k]} | {pr.height} | {mover.sum()} | {b[j] * sd[j]:+.4f} | {lo * sd[j]:+.4f} to {hi * sd[j]:+.4f} | {'yes' if ok else 'no'} | {bm[j] * sd[j]:+.4f} |")
    say("", f"Coefficients clear of 0: {clear} of {len(real_rows)} (about {0.1 * len(real_rows):.1f} expected by chance at 90%).")

    # pays: take the teammates' part out, pull back the usual way, put it back at next season's expected condition
    say("", "**Pays:** M1 with the teammates' part taken out, then put back at next season's expected condition (his next team's condition last season, times that condition's own",
        "season-to-season slope), against M1. Fit before each target season (walk-forward); players resampled.", "",
        "| Measure | Rows | Target seasons | Gain over M1 (share of its squared error) | 90% interval | Clear |", "|---|---|---|---|---|---|")
    pays = []
    tcs = {}
    for m, keys in COND_OF.items():
        if tuple(keys) not in tcs:
            tcs[tuple(keys)] = team_cond(cond, game, keys)
        tc = tcs[tuple(keys)]
        dev_all = season_dev(s, fits, m, 2025).join(pc_cache[m], on=["gsis_id", "season"])
        first = max(first_of(s, m), 2006 if keys != ["op"] and keys != ["ocat"] else 2018)
        out = []
        for T in range(first + 3, 2025):
            mus, s2, t2, k = fits.k(m, T)
            # beta on pairs ending before T
            a = dev_all.filter(c("season") < T)
            pr = a.join(a.with_columns(c("season") - 1), on=["gsis_id", "season"], suffix="2").filter((c("n") >= 10) & (c("n2") >= 10))
            if pr.height < 100:
                continue
            dy = ((pr["x2"] - pr["mu2"]) - (pr["x"] - pr["mu"])).to_numpy()
            dX = np.column_stack([(pr[f"{q}2"] - pr[q]).to_numpy() for q in keys])
            b = wls(dX, dy, (1 / (1 / pr["n"] + 1 / pr["n2"])).to_numpy())[1:]
            # each condition's season-to-season slope, teams, before T
            t = tc.filter(c("season") < T)
            tp = t.join(t.with_columns(c("season") - 1), on=["team", "season"], suffix="2")
            slope = [float(np.polyfit(tp[q].to_numpy(), tp[f"{q}2"].to_numpy(), 1)[0]) for q in keys]
            last = dev_all.filter(c("season") == T - 1).filter(c("pos").is_in(list(mus)))
            nxt = s.filter((c("measure") == m) & (c("season") == T)).select("gsis_id", team_next="team", y=c("num") / c("den"), w="den")
            f = last.join(nxt, on="gsis_id").join(tc.filter(c("season") == T - 1).select("team", *[pl.col(q).alias(f"e_{q}") for q in keys]).rename({"team": "team_next"}), on="team_next", how="left")
            if f.height == 0:
                continue
            mu = f["pos"].replace_strict(mus).to_numpy()
            x, n = f["x"].to_numpy(), f["n"].to_numpy()
            own = sum(b[j] * f[q].to_numpy() for j, q in enumerate(keys))
            exp = sum(b[j] * slope[j] * f[f"e_{q}"].fill_null(0).to_numpy() for j, q in enumerate(keys))
            # the player's x is centred on his own season's position mean; mu is last season's, so the same season here
            x_adj = x - own
            m1 = mu + n / (n + k) * (x - mu)
            h = mu + n / (n + k) * (x_adj - mu) + exp
            out.append(pl.DataFrame({"gsis_id": f["gsis_id"], "T": T, "y": f["y"], "w": f["w"], "m1": m1, "h113": h, "mover": (f["team"] != f["team_next"]).to_numpy()}))
        if not out:
            continue
        F = pl.concat(out)
        g = boot_gain(F, "h113", "m1", RNG)
        ok = g[1] > 0
        pays.append((m, g, ok))
        gm = boot_gain(F.filter(c("mover")), "h113", "m1", RNG) if F["mover"].sum() > 100 else (np.nan,) * 3
        say(f"| {m} | {F.height} | {F['T'].min()}-{F['T'].max()} | {g[0]:+.2%} (movers {gm[0]:+.2%}) | {g[1]:+.2%} to {g[2]:+.2%} | {'yes' if ok else 'no'} |")
    say("", f"H113 real: {'held' if clear else 'failed'} ({clear} clear of 0); pays: {sum(p[2] for p in pays)} of {len(pays)} rates clear of 0 over M1.")
    return real_rows, pays


# ---------------------------------------------------------------- H114


def h114(s, game, fits):
    say("", "## H114: does a consistent measure set where the other rates regress to?", "",
        "Each rate is pulled toward a target predicted from the player's other consistent measures last season (their M1 pulled values: tprr, yprr, aDOT for receivers;",
        "plus carries a run snap for backs; hit-or-sack and scramble rates for QBs; QB hits a pass snap for rushers; targets a coverage snap for coverage), centred by position.",
        "The target is a ridge regression (alpha by GCV) of next season's centred rate on them, fit on earlier seasons. The weight on his own rate comes from the true spread",
        "left around that target (k grows by the share of next season's true spread the target removes). Side columns: the ridge with his own pulled rate added (the target",
        "and the weight fit together), and his own pulled rate alone recalibrated (what the side model gets from rescaling the pull, not from the other measures).", "",
        "| Measure | From | Rows | Features | k (M1 to conditional) | H114 against M1 | 90% interval | Clear | Ridge with own rate against M1 | Own rate recalibrated against M1 | What the other measures add (ridge against recalibrated) |",
        "|---|---|---|---|---|---|---|---|---|---|---|")
    res = []
    for m, grp in MEASURES.items():
        feats = [f for f in CONSISTENT[grp] if f != m]
        if not feats:
            continue
        first = max(first_of(s, f) for f in [m, *feats])
        out, ks = [], []
        for T in range(first + 3, 2025):
            mus, s2, t2, k = fits.k(m, T)
            own = season_dev(s, fits, m, T)
            F = own
            for f in feats:
                F = F.join(season_dev(s, fits, f, T).select("gsis_id", "season", **{f"f_{f}": "dev"}), on=["gsis_id", "season"], how="left")
            F = F.with_columns([c(f"f_{f}").fill_null(0) for f in feats])
            nxt = s.filter(c("measure") == m).select("gsis_id", season=c("season") - 1, y=c("num") / c("den"), w="den")
            P = F.join(nxt, on=["gsis_id", "season"])
            tr = P.filter((c("season") < T - 1) & (c("n") >= 10))
            te = P.filter((c("season") == T - 1) & c("pos").is_in(list(mus)))
            if tr.height < 200 or te.height == 0:
                continue
            Xf = [f"f_{f}" for f in feats]
            yt, wt = (tr["y"] - tr["mu"]).to_numpy(), tr["w"].to_numpy()
            r1 = RidgeCV(alphas=np.logspace(-6, 0, 13), fit_intercept=False).fit(tr.select(Xf).to_numpy(), yt, sample_weight=wt)
            r2 = RidgeCV(alphas=np.logspace(-6, 0, 13), fit_intercept=False).fit(tr.select(["dev", *Xf]).to_numpy(), yt, sample_weight=wt)
            r3 = RidgeCV(alphas=np.logspace(-6, 0, 13), fit_intercept=False).fit(tr.select(["dev"]).to_numpy(), yt, sample_weight=wt)
            mc_tr = r1.predict(tr.select(Xf).to_numpy())
            N, W = len(yt), wt.sum()
            V0 = np.sum(wt * yt**2) / W - s2 * N / W
            Vc = np.sum(wt * (yt - mc_tr) ** 2) / W - s2 * N / W
            kc = k * V0 / Vc if (Vc > 0 and V0 > 0) else k
            ks.append((k, kc))
            mu = te["pos"].replace_strict(mus).to_numpy()  # = te's own position-season mean (T-1)
            x, n = te["x"].to_numpy(), te["n"].to_numpy()
            mc = mu + r1.predict(te.select(Xf).to_numpy())
            out.append(pl.DataFrame({"gsis_id": te["gsis_id"], "T": T, "y": te["y"], "w": te["w"],
                                     "m1": mu + n / (n + k) * (x - mu), "h114": mc + n / (n + kc) * (x - mc),
                                     "ridge": mu + r2.predict(te.select(["dev", *Xf]).to_numpy()), "recal": mu + r3.predict(te.select(["dev"]).to_numpy())}))  # fmt: skip
        if not out:
            continue
        D = pl.concat(out)
        g = boot_gain(D, "h114", "m1", RNG)
        g2 = boot_gain(D, "ridge", "m1", RNG)
        g3 = boot_gain(D, "recal", "m1", RNG)
        g4 = boot_gain(D, "ridge", "recal", RNG)
        ok = g[1] > 0
        res.append((m, g, ok, g2, g3, g4))
        k0, kc = np.mean([a for a, _ in ks]), np.mean([b for _, b in ks])
        say(f"| {m} | {first} | {D.height} | {', '.join(feats)} | {k0:.0f} to {kc:.0f} | {g[0]:+.2%} | {g[1]:+.2%} to {g[2]:+.2%} | {'yes' if ok else 'no'} | {g2[0]:+.2%} ({g2[1]:+.2%} to {g2[2]:+.2%}) | {g3[0]:+.2%} ({g3[1]:+.2%} to {g3[2]:+.2%}) | {g4[0]:+.2%} ({g4[1]:+.2%} to {g4[2]:+.2%}) |")
    n_ok = sum(r[2] for r in res)
    say("", f"Side: the other measures add to his own recalibrated rate, clear of 0, for {sum(r[5][1] > 0 for r in res)} of {len(res)}; "
        f"recalibrating his own pull alone beats M1 clearly for {sum(r[4][1] > 0 for r in res)} of {len(res)} (M1's within-season pull isn't next season's).")
    say("", f"H114: {n_ok} of {len(res)} rates clear of 0 over M1 (one or more: {'held' if n_ok else 'failed'}; most: {'held' if n_ok > len(res) / 2 else 'failed'}).")
    return res


def main() -> None:
    s, game = player_seasons()
    fits = Fits(s, game)
    cond = load("cond")
    say("# Method 2a: the CEO's hunches (2026-11-25)")
    h113(s, game, fits, cond)
    h114(s, game, fits)
    say.save()


if __name__ == "__main__":
    main()
