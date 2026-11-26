"""Aging, method 1 (EXPLORATION.md): the noise ceiling, delta curves with the survivor fix, the age model
against no age, and H121, H122, H120 and H117's "real" half. Discovery only, 2002-2024; the 2025 vault is closed.

Run from pcf/:  python projects/aging/explore/m1_curves.py   (writes m1_curves.txt; saves the forecasts for method 3)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import os

from aging_common import CACHE, DEF, OFF, Say, boot_gain, k_of, load, pairs, wls  # noqa: E402

c = pl.col
RNG = np.random.default_rng(1)
AGES = list(range(21, 36))
# the age model's form: "steps" (pre-registered: one step a year of age, 21-35) or "smooth" (a cubic in age, a side run)
FORM = os.environ.get("AGING_FORM", "steps")
say = Say(Path(__file__).with_name(f"m1_curves{'' if FORM == 'steps' else '_smooth'}.txt"))
BANDS = {"young": (0, 25), "prime": (26, 29), "old": (30, 99)}


def rows(d, pos, kind):
    """The rows a model sees: usage (every pair, zeros for departures) or efficiency (survivors who had chances)."""
    x = d.filter(c("pos") == pos)
    if kind == "u":
        x = x.filter(c("cu2").is_not_null()).with_columns(x=c("pu"), y=c("cu2"), w=pl.lit(1.0), nn=c("ud2").fill_null(0))
    else:
        x = x.filter(c("pe").is_not_null() & c("ce2").is_not_null() & (c("n2") > 0)).with_columns(x=c("pe"), y=c("ce2"), w=c("n2").cast(pl.Float64), nn=c("n2"))
    return x.with_columns(T=c("season") + 1)


def design(x, kind_cols):
    cols = []
    if "int" in kind_cols:
        cols.append(np.ones(x.height))
    if "x" in kind_cols:
        cols.append(x["x"].to_numpy())
    if "age" in kind_cols:
        if FORM == "steps":
            a = x["a"].to_numpy()
            cols += [(a == k).astype(float) for k in AGES]
        else:
            z = (x["age"].clip(21, 36).to_numpy() - 27) / 5
            cols += [z, z**2, z**3]
    if "star" in kind_cols:
        a = x["age"].to_numpy()
        for st in ("star", "never"):
            s = (x["star"] == st).to_numpy()
            for lo, hi in BANDS.values():
                cols.append((s & (a >= lo) & (a < hi + 1)).astype(float))
    if "role" in kind_cols:
        a = x["age"].to_numpy()
        for r in kind_cols["role"]:
            s = (x["coarse"] == r).to_numpy()
            for lo, hi in BANDS.values():
                cols.append((s & (a >= lo) & (a < hi + 1)).astype(float))
    return np.column_stack(cols)


def walk(x, specs, first_T, ridge=1e-4):
    """Walk-forward forecasts for each spec (a dict of design parts), fit on targets before T, by T."""
    out = []
    for T in range(first_T, 2025):
        tr, te = x.filter(c("T") < T), x.filter(c("T") == T)
        if tr.height < 200 or te.height == 0:
            continue
        cols = {}
        for name, spec in specs.items():
            b = wls(design(tr, spec), tr["y"].to_numpy(), tr["w"].to_numpy(), ridge)
            cols[name] = design(te, spec) @ b
        out.append(te.with_columns(**{k: pl.Series(v) for k, v in cols.items()}))
    return pl.concat(out) if out else None


def agecols(z):
    if FORM == "steps":
        return [(z["a"].to_numpy() == a).astype(float) for a in AGES]
    q = (z["age"].clip(21, 36).to_numpy() - 27) / 5
    return [q, q**2, q**3]


def chained(x, val, w):
    """The delta method: weighted mean change at each age, chained from 0 at age 23."""
    m = x.group_by("a").agg(d=(c(val) * c(w)).sum() / c(w).sum(), n=pl.len()).sort("a")
    m = m.filter(c("n") >= 15)
    d = dict(zip(m["a"].to_list(), m["d"].to_list()))
    lvl, cur = {}, 0.0
    for a in range(23, 36):
        lvl[a] = cur
        cur += d.get(a, 0.0)
    cur = 0.0
    for a in range(22, 20, -1):
        cur -= d.get(a, 0.0)
        lvl[a] = cur
    return lvl, d


def main() -> None:
    d = pairs()
    g, s = load("game"), load("season")
    say(f"# Method 1: delta curves, the survivor fix and the age model (2026-11-25; age form: {FORM})", "",
        "Pairs of seasons s to s + 1, 2002-2024 (defense 2013-2024). Usage is a share of the team's opportunities over his roster weeks, 0 next season if he left;",
        "efficiency is EPA per opportunity; both centred by the position's mean that season and pulled back by k. Ages are on September 1, in whole years, 21-35 (ends pooled).",
        f"Pairs: {d.height:,}; players: {d['gsis_id'].n_unique():,}.", "")

    # ---------------- the noise ceiling
    say("## The noise ceiling", "",
        "Next season's rate against the no-age baseline (his pulled rate times a fitted pull, plus an intercept), all seasons: the baseline's leftover spread, the part of it that",
        "is noise in next season's rate (sigma2 / next season's attempts; 0 for a player who left), and the rest, the true change: the room an age model has.", "",
        "| Position | Kind | Rows | k | Leftover spread (weighted) | Noise share | Room (true change share) |", "|---|---|---|---|---|---|---|")
    sig = {}
    for pos in OFF + DEF:
        for kind in ("u", "e") if pos in OFF else ("u",):
            x = rows(d, pos, kind)
            s2, t2, k = k_of(g, s, kind, pos, 2025)
            sig[(pos, kind)] = s2
            X = design(x, {"int": 1, "x": 1})
            b = wls(X, x["y"].to_numpy(), x["w"].to_numpy())
            r = x["y"].to_numpy() - X @ b
            w = x["w"].to_numpy()
            nn = x["nn"].to_numpy().astype(float)
            noise = np.where(nn > 0, s2 / np.maximum(nn, 1e-9), 0.0)
            tot = np.sum(w * r**2) / w.sum()
            nz = np.sum(w * noise) / w.sum()
            say(f"| {pos} | {'usage' if kind == 'u' else 'efficiency'} | {x.height} | {k:.0f} | {tot:.5f} | {nz / tot:.0%} | {1 - nz / tot:.0%} |")

    # ---------------- the curves
    say("", "## The delta curves (chained from 0 at age 23; centred units: usage in points of share, efficiency in EPA per opportunity)", "",
        "Survivors only against the survivor fix. Usage: survivors (he played next season) against all, with a departure's usage at 0. Efficiency: survivors against",
        "ghosts (a departure's next efficiency at his position's 20th percentile that season). The still-playing column is the share who play next season at that age.", "")
    peak = {}
    ghost_steeper = []
    for pos in OFF + DEF:
        x = d.filter(c("pos") == pos)
        su = x.filter(~c("gone") & c("pu2").is_not_null()).with_columns(du=c("pu2") - c("pu"), wu=2 / (1 / c("u_num").clip(1) + 1 / (c("u2") * c("ud2")).clip(1)))
        # with departures: weighted by this season's opportunities (a departure has none next season)
        al = x.filter(c("cu2").is_not_null()).with_columns(du=pl.coalesce(c("pu2"), c("cu2")) - c("pu"), wu=c("u_num").cast(pl.Float64))
        lu_s, _ = chained(su, "du", "wu")
        lu_a, _ = chained(al, "du", "wu")
        peak[pos] = max(range(22, 34), key=lambda a: lu_s.get(a, -9))
        still = x.group_by("a").agg(p=1 - c("gone").mean(), n=pl.len()).sort("a")
        stl = dict(zip(still["a"].to_list(), still["p"].to_list()))
        line = f"- **{pos}** usage, survivors: " + ", ".join(f"{a} {100 * lu_s[a]:+.1f}" for a in range(22, 35, 2))
        line += "; with departures: " + ", ".join(f"{a} {100 * lu_a[a]:+.1f}" for a in range(22, 35, 2))
        line += f". Peak (survivors): {peak[pos]}. Still playing: " + ", ".join(f"{a} {stl.get(a, float('nan')):.0%}" for a in range(22, 35, 3))
        say(line)
        if pos in OFF:
            e = x.filter(c("pe").is_not_null())
            rep = d.filter((c("pos") == pos) & c("pe2").is_not_null()).group_by("season").agg(rep=c("pe2").quantile(0.2))
            ee = e.join(rep, on="season", how="left")
            sv = ee.filter(c("pe2").is_not_null() & (c("n2") > 0)).with_columns(de=c("pe2") - c("pe"), we=2 / (1 / c("e_den").clip(1) + 1 / c("n2").clip(1)))
            gh = ee.filter(c("pe2").is_not_null() & (c("n2") > 0) | c("gone")).with_columns(
                de=pl.when(c("gone")).then(c("rep") - c("pe")).otherwise(c("pe2") - c("pe")),
                we=pl.when(c("gone")).then(c("e_den").clip(1)).otherwise(2 / (1 / c("e_den").clip(1) + 1 / c("n2").clip(1))))  # fmt: skip
            le_s, _ = chained(sv, "de", "we")
            le_g, _ = chained(gh, "de", "we")
            say(f"  - efficiency, survivors: " + ", ".join(f"{a} {le_s[a]:+.3f}" for a in range(22, 35, 2)) + "; with ghosts: " + ", ".join(f"{a} {le_g[a]:+.3f}" for a in range(22, 35, 2)))
            ghost_steeper.append((pos, (le_g[34] - le_g[30]) - (le_s[34] - le_s[30])))
    say("", "Ghosts against survivors, efficiency's fall from 30 to 34 (more negative: the fix makes the curve steeper): " + ", ".join(f"{p} {v:+.3f}" for p, v in ghost_steeper))

    # ---------------- the age model against no age; H121 positions; H122
    say("", "## The age model against no age (walk-forward, targets 2010-2024; defense 2016-2024)", "",
        "| Position | Kind | Test rows | Age model against no age | 90% interval | Clear | Share of the room explained | Mixed check (player level added) against the age model |", "|---|---|---|---|---|---|---|---|")
    F = {}
    clear_u, clear_e = 0, 0
    for pos in OFF + DEF:
        for kind in ("u", "e") if pos in OFF else ("u",):
            x = rows(d, pos, kind)
            f = walk(x, {"base": {"int": 1, "x": 1}, "age": {"int": 1, "x": 1, "age": 1}}, 2010 if pos in OFF else 2016)
            # mixed check: the player's mean leftover from the age model in earlier seasons (fit before T), shrunk
            f = f.sort("gsis_id", "T")
            F[(pos, kind)] = f
            gn = boot_gain(f, "age", "base", RNG)
            nn = f["nn"].to_numpy().astype(float)
            w = f["w"].to_numpy()
            noise = np.sum(w * np.where(nn > 0, sig[(pos, kind)] / np.maximum(nn, 1e-9), 0))
            sse_b = np.sum(w * (f["y"] - f["base"]).to_numpy() ** 2)
            sse_a = np.sum(w * (f["y"] - f["age"]).to_numpy() ** 2)
            room = sse_b - noise
            share = (sse_b - sse_a) / room if room > 0 else np.nan
            ok = gn[1] > 0
            clear_u += ok and kind == "u" and pos in OFF
            clear_e += ok and kind == "e"
            # the mixed-model check: his earlier leftovers from the age model, shrunk by their count (5 seasons' weight)
            f2 = f.with_columns(res=c("y") - c("age")).with_columns(
                cs=c("res").cum_sum().over("gsis_id") - c("res"), cn=pl.int_range(pl.len()).over("gsis_id"))
            f2 = f2.with_columns(mixed=c("age") + c("cs") / (c("cn") + 5))
            gm = boot_gain(f2, "mixed", "age", RNG)
            say(f"| {pos} | {'usage' if kind == 'u' else 'efficiency'} | {f.height} | {gn[0]:+.2%} | {gn[1]:+.2%} to {gn[2]:+.2%} | {'yes' if ok else 'no'} | {share:.1%} | {gm[0]:+.2%} ({gm[1]:+.2%} to {gm[2]:+.2%}) |")
    say("", f"Age against no age: clear for usage at {clear_u} of 4 offensive positions (the bet: 4 of 4) and for efficiency at {clear_e} of 4 (the bet: 2+).")

    # H122: usage's explained share of the room against efficiency's, players resampled
    say("", "### H122: does age show more in usage than in efficiency?", "",
        "The share of the room (the true change) the age model explains, usage against efficiency, at each offensive position; players resampled (1,000 draws).", "",
        "| Position | Usage's share | Efficiency's share | Difference (90%) | Usage clearly larger |", "|---|---|---|---|---|")
    h122 = 0
    for pos in OFF:
        parts = []
        for kind in ("u", "e"):
            f = F[(pos, kind)]
            nn = f["nn"].to_numpy().astype(float)
            f = f.with_columns(nz=pl.Series(np.where(nn > 0, sig[(pos, kind)] / np.maximum(nn, 1e-9), 0.0)))
            p = f.group_by("gsis_id").agg(b=(c("w") * (c("y") - c("base")) ** 2).sum(), a=(c("w") * (c("y") - c("age")) ** 2).sum(), z=(c("w") * c("nz")).sum())
            parts.append(p)
        ids = np.union1d(parts[0]["gsis_id"].to_numpy(), parts[1]["gsis_id"].to_numpy())
        mats = []
        for p in parts:
            m = pl.DataFrame({"gsis_id": ids}).join(p, on="gsis_id", how="left").fill_null(0)
            mats.append(np.column_stack([m["b"].to_numpy(), m["a"].to_numpy(), m["z"].to_numpy()]))
        def sh(M):
            b, a, z = M.sum(0)
            return (b - a) / (b - z) if b - z > 0 else np.nan
        su, se = sh(mats[0]), sh(mats[1])
        idx = RNG.integers(0, len(ids), (1000, len(ids)))
        diffs = np.array([sh(mats[0][i]) - sh(mats[1][i]) for i in idx])
        lo, hi = np.nanquantile(diffs, [0.05, 0.95])
        ok = lo > 0
        h122 += ok
        say(f"| {pos} | {su:.1%} | {se:.1%} | {su - se:+.1%} ({lo:+.1%} to {hi:+.1%}) | {'yes' if ok else 'no'} |")
    say("", f"H122: usage clearly larger at {h122} of 4 (the rule: 3 of 4).")

    # H121: position steps against shared steps
    say("", "### H121: do positions age differently?", "",
        "Position-specific age steps against one shared set of steps (each position keeps its own intercept and pull), walk-forward, pooled.", "")
    for kind, poss in (("u", OFF + DEF), ("e", OFF)):
        X = pl.concat([rows(d, p, kind) for p in poss], how="diagonal_relaxed")
        out = []
        for T in range(2010, 2025):
            tr, te = X.filter(c("T") < T), X.filter(c("T") == T)
            if te.height == 0:
                continue
            def dz(z, shared):
                cols = []
                for p in poss:
                    m = (z["pos"] == p).to_numpy().astype(float)
                    cols += [m, m * z["x"].to_numpy()]
                    if not shared:
                        cols += [m * v for v in agecols(z)]
                if shared:
                    cols += agecols(z)
                return np.column_stack(cols)
            pr = {}
            for nm, sh_ in (("shared", True), ("bypos", False)):
                b = wls(dz(tr, sh_), tr["y"].to_numpy(), tr["w"].to_numpy(), 1e-4)
                pr[nm] = dz(te, sh_) @ b
            out.append(te.with_columns(shared=pl.Series(pr["shared"]), bypos=pl.Series(pr["bypos"])))
        Fp = pl.concat(out)
        # each position's own errors are on its own scale: score per position, then report the pooled count
        res = []
        for p in poss:
            gp = boot_gain(Fp.filter(c("pos") == p), "bypos", "shared", RNG)
            res.append(f"{p} {gp[0]:+.2%} ({gp[1]:+.2%} to {gp[2]:+.2%})")
        say(f"- {'usage' if kind == 'u' else 'efficiency'}: " + "; ".join(res))

    # H121's side bet: roles within a position (2016+)
    say("", "Roles within a position (the side bet, 2016+): age steps by roles-and-archetypes' coarse role (young, prime, old bands) on top of the position's steps.", "")
    import glob

    ra = pl.read_parquet(glob.glob(str(CACHE.parent.parent / "outputs" / "roles-archetypes" / "*" / "history.parquet"))[0])
    ra = ra.sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first").select("gsis_id", "season", "coarse")
    for pos in OFF:
        for kind in ("u", "e"):
            x = rows(d, pos, kind).join(ra, on=["gsis_id", "season"], how="inner").drop_nulls("coarse")
            roles = [r for r, n in x.group_by("coarse").len().iter_rows() if n >= 60]
            if len(roles) < 2:
                continue
            f = walk(x, {"age": {"int": 1, "x": 1, "age": 1}, "role": {"int": 1, "x": 1, "age": 1, "role": roles}}, 2018)
            gr = boot_gain(f, "role", "age", RNG)
            say(f"- {pos} {'usage' if kind == 'u' else 'efficiency'} (roles: {', '.join(roles)}): {gr[0]:+.2%} ({gr[1]:+.2%} to {gr[2]:+.2%}){' clear' if gr[1] > 0 else ''}")

    # H120: stars
    say("", "### H120: do stars age differently?", "",
        "A star: a top-5 PPR season at his position up to s. Never: no top-24 season (top-12 QB, TE). Star-by-age-band steps (young under 26, prime 26-29, old 30+) on top of the age model, walk-forward.", "",
        "| Position | Kind | Stars against the age model (90%) | Clear | Mean next-season change, stars: young, prime, old | Never: young, prime, old |", "|---|---|---|---|---|---|")
    h120 = []
    for kind in ("u", "e"):
        for pos in OFF:
            x = rows(d, pos, kind)
            f = walk(x, {"age": {"int": 1, "x": 1, "age": 1}, "star": {"int": 1, "x": 1, "age": 1, "star": 1}}, 2010)
            gs = boot_gain(f, "star", "age", RNG)
            h120.append((pos, kind, gs[1] > 0))
            def pat(stv):
                z = x.filter(c("star") == stv).with_columns(dlt=c("y") - c("x"))
                o = []
                for lo, hi in BANDS.values():
                    b = z.filter((c("age") >= lo) & (c("age") < hi + 1))
                    o.append(f"{(b['dlt'] * b['w']).sum() / max(b['w'].sum(), 1e-9):+.3f} ({b.height})")
                return ", ".join(o)
            say(f"| {pos} | {'usage' if kind == 'u' else 'efficiency'} | {gs[0]:+.2%} ({gs[1]:+.2%} to {gs[2]:+.2%}) | {'yes' if gs[1] > 0 else 'no'} | {pat('star')} | {pat('never')} |")
    say("", f"H120: stars' steps clear for {sum(h[2] for h in h120)} of {len(h120)} position-kinds.")

    # H117's real half
    say("", "### H117 (real half): two ways to decline?", "",
        f"Usage decliners: next season's usage at most two-thirds of this season's, at or past the position's usage peak (survivors' curve: {', '.join(f'{p} {peak[p]}' for p in OFF)}), with",
        "10+ opportunities in both seasons. Their efficiency change (pulled): its spread, the part noise gives, and the true spread (players resampled); then persistence: did a decliner",
        "who kept his efficiency (change at or above 0) keep it again in his next decline season?", "")
    allx = []
    for pos in OFF:
        x = d.filter((c("pos") == pos) & (c("age") >= peak[pos]) & c("pe2").is_not_null() & (c("e_den") >= 10) & (c("n2") >= 10) & (c("u2") <= c("u") * 2 / 3))
        k = x["ke"][0]
        s2 = sig[(pos, "e")]
        x = x.with_columns(de=c("pe2") - c("pe"), nz=(c("e_den") / (c("e_den") + k)) ** 2 * s2 / c("e_den") + (c("n2") / (c("n2") + k)) ** 2 * s2 / c("n2"))
        allx.append(x.with_columns(posx=pl.lit(pos)))
        de, nz = x["de"].to_numpy(), x["nz"].to_numpy()
        ids = x["gsis_id"].to_numpy()
        u, inv = np.unique(ids, return_inverse=True)
        grp = [np.flatnonzero(inv == i) for i in range(len(u))]
        def ts(ix):
            return np.var(de[ix]) - np.mean(nz[ix])
        bs = [ts(np.concatenate([grp[i] for i in RNG.integers(0, len(u), len(u))])) for _ in range(500)]
        lo, hi = np.quantile(bs, [0.05, 0.95])
        say(f"- {pos}: {x.height} decline seasons; spread {np.var(de):.4f}, noise {np.mean(nz):.4f}, true spread {ts(np.arange(len(de))):+.4f} ({lo:+.4f} to {hi:+.4f}); kept efficiency: {np.mean(de >= 0):.0%}")
    X = pl.concat(allx).sort("gsis_id", "season").with_columns(kept=(c("de") >= 0))
    nx = X.with_columns(kept_next=c("kept").shift(-1).over("gsis_id")).drop_nulls("kept_next")
    a = nx.filter(c("kept") & c("kept_next")).height
    b = nx.filter(c("kept") & ~c("kept_next")).height
    cc = nx.filter(~c("kept") & c("kept_next")).height
    dd = nx.filter(~c("kept") & ~c("kept_next")).height
    orr = (a + 0.5) * (dd + 0.5) / ((b + 0.5) * (cc + 0.5))
    se = np.sqrt(1 / (a + 0.5) + 1 / (b + 0.5) + 1 / (cc + 0.5) + 1 / (dd + 0.5))
    say(f"- Persistence, players with two decline seasons ({nx.height}): kept then kept {a}, kept then lost {b}, lost then kept {cc}, lost then lost {dd}; odds ratio {orr:.2f} (90% {orr * np.exp(-1.645 * se):.2f} to {orr * np.exp(1.645 * se):.2f}).")

    # save the age model's efficiency forecasts for method 3 (H119)
    pl.concat([F[(p, "e")].with_columns(posx=pl.lit(p)) for p in OFF], how="diagonal_relaxed").write_parquet(CACHE / "m1_eff_forecasts.parquet")
    pl.concat([F[(p, "u")].with_columns(posx=pl.lit(p)) for p in OFF], how="diagonal_relaxed").write_parquet(CACHE / "m1_use_forecasts.parquet")
    (CACHE / "peaks.txt").write_text(",".join(f"{p}:{peak[p]}" for p in OFF))
    say.save()


if __name__ == "__main__":
    main()
