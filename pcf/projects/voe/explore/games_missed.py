# ruff: noqa: E501
"""voe, third look (2026-11-20): the CEO's direction (c), "use missed games to size ratings" (Claude's I73).

1. What each position's absence costs: a team-game's EPA over expected a play (its side, less the
   opponent's season rate leaving this game out), against the same team-season's other games, with all
   of the game's absences of regulars at once (a fixed effect per team-season; plays-weighted).
2. Sizing: the change modelled as k x missing share x his usual play share x (his rating less his
   replacement's); k fit per rating, for QBs and for everyone else.
3. The extension (H73's idea): fit on 2018-2021 (group averages on 2016-2021), score held-out team-games
   2022-2024; and the roster-change test 2022-2024 with sized ratings.
Discovery only; the 2025 vault not read. Design and odds: BRIEF.md, "The CEO's direction after the second look".

Run from pcf/:  python projects/voe/explore/games_missed.py > projects/voe/explore/games_missed.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402
import mlp_check as mc  # noqa: E402
import ratings as rt  # noqa: E402

c = pl.col
log = fl.log
RNG = np.random.default_rng(17)
CL = ["team", "season", "side"]
OFF_G, DEF_G = ["QB", "RB", "WR", "TE", "OL"], ["DL", "LB", "DB"]
GCOLS = [f"{s[0]}_{g}" for s, gs in (("offense", OFF_G), ("defense", DEF_G)) for g in gs]
RATINGS = {
    "ra": "plus-minus from his own stats (a)",
    "rs": "own-stats rating (b)",
    "rp": "plus-minus with last season's prior (first look)",
}


# ---------------------------------------------------------------- team-games and absences
def team_games(p, on):
    tgs = (
        on.select("game_id", "play_id", "team", "side", "season", "week", "y")
        .unique(["game_id", "play_id", "side"])
        .group_by("game_id", "team", "side", "season", "week")
        .agg(n_g=pl.len(), s_g=c("y").sum())
    )
    tot = tgs.group_by(CL).agg(S=c("s_g").sum(), N=c("n_g").sum())
    opp = p.select("game_id", "posteam", "defteam").unique("game_id")
    pairs = pl.concat([
        opp.select("game_id", team=c("posteam"), opp=c("defteam")),
        opp.select("game_id", team=c("defteam"), opp=c("posteam")),
    ])  # fmt: skip
    o = (
        tgs.join(tot, on=CL)
        .with_columns(loo=(c("S") - c("s_g")) / (c("N") - c("n_g")))
        .select("game_id", "team", "side", "loo")
    )
    g = tgs.join(pairs, on=["game_id", "team"]).with_columns(
        oside=pl.when(c("side") == "offense").then(pl.lit("defense")).otherwise(pl.lit("offense"))
    )
    g = g.join(
        o.rename({"team": "opp", "side": "oside", "loo": "opp_loo"}),
        on=["game_id", "opp", "oside"],
        how="left",
    )
    last_week = p.group_by("season").agg(wmax=c("week").max())
    g = g.join(last_week, on="season").filter(c("week") < c("wmax"))
    return g.with_columns(y=c("s_g") / c("n_g") + c("opp_loo").fill_null(0)).drop("wmax", "oside")


STARTERS = {"QB": 1, "RB": 1, "WR": 3, "TE": 1, "OL": 5, "DL": 4, "LB": 2, "DB": 5}


def absences(on, tg, lo, hi, starters=False):
    """Players whose typical share of their side's plays (median over their games) is in [lo, hi), with 4+ games at lo or more; one row per eligible team-game."""
    pg = (
        on.group_by("gsis_id", "game_id", "team", "side", "season", "week")
        .agg(k=pl.len(), group=c("group").first())
        .join(
            tg.select("game_id", "team", "side", "n_g"), on=["game_id", "team", "side"], how="left"
        )
        .with_columns(share=c("k") / c("n_g"))
    )
    ps = pg.group_by("gsis_id", *CL).agg(
        usual=c("share").median(),
        n_on=(c("share") >= lo).sum(),
        first=c("week").min(),
        last=c("week").max(),
        group=c("group").mode().first(),
        tot=c("k").sum(),
    )
    reg = ps.filter((c("usual") >= lo) & (c("usual") < hi) & (c("n_on") >= 4))
    if starters:  # each team-season's main starters by plays at each group (QB1, RB1, WR1-3, ...)
        reg = (
            ps.filter(c("n_on") >= 4)
            .with_columns(rk=c("tot").rank("ordinal", descending=True).over([*CL, "group"]))
            .filter(c("rk") <= c("group").replace_strict(STARTERS, default=0))
            .drop("rk")
        )
    # did he play for another team later that season? then his games after leaving don't count
    later = ps.select("gsis_id", "season", o_team=c("team"), o_first=c("first"))
    moved = (
        reg.join(later, on=["gsis_id", "season"])
        .filter((c("o_team") != c("team")) & (c("o_first") > c("last")))
        .select("gsis_id", *CL)
        .unique()
        .with_columns(moved=pl.lit(True))
    )
    reg = reg.join(moved, on=["gsis_id", *CL], how="left").with_columns(c("moved").fill_null(False))
    E = reg.join(tg.select("game_id", *CL, "week"), on=CL)
    E = E.filter((c("week") >= c("first")) & (~c("moved") | (c("week") <= c("last"))))
    E = E.join(
        pg.select("gsis_id", "game_id", "side", "share"),
        on=["gsis_id", "game_id", "side"],
        how="left",
    ).with_columns(c("share").fill_null(0.0))
    return E.with_columns(miss=(1 - c("share") / c("usual")).clip(0, 1)), pg


def wls_parts(df, xcols, ycol="y", w="n_g"):
    """Within team-season (plays-weighted) demeaning; returns X, y, w, cluster codes."""
    d = df.with_columns(
        *(
            (c(x) - (c(x) * c(w)).sum().over(CL) / c(w).sum().over(CL)).alias(f"{x}_d")
            for x in [*xcols, ycol]
        )
    )
    d = d.with_columns(cl=pl.concat_str(CL, separator="|")).sort("cl")
    cl = np.unique(d["cl"].to_numpy(), return_inverse=True)[1]
    return (
        d.select([f"{x}_d" for x in xcols]).to_numpy(),
        d[f"{ycol}_d"].to_numpy(),
        d[w].to_numpy().astype(float),
        cl,
        d,
    )


def wls(X, y, w, cl, nboot=500, nperm=0):
    k = X.shape[1]
    A = np.zeros((cl.max() + 1, k, k))
    b = np.zeros((cl.max() + 1, k))
    for j in range(k):
        b[:, j] = np.bincount(cl, w * X[:, j] * y, cl.max() + 1)
        for m in range(k):
            A[:, j, m] = np.bincount(cl, w * X[:, j] * X[:, m], cl.max() + 1)
    beta = np.linalg.solve(A.sum(0) + 1e-12 * np.eye(k), b.sum(0))
    bs = []
    for _ in range(nboot):
        s = RNG.integers(0, len(A), len(A))
        bs.append(np.linalg.solve(A[s].sum(0) + 1e-12 * np.eye(k), b[s].sum(0)))
    lo, hi = np.percentile(bs, [5, 95], axis=0) if nboot else (beta, beta)
    perms = []
    for _ in range(nperm):
        Xp = X[np.argsort(cl + RNG.random(len(cl)), kind="stable")]
        bp = np.array([np.bincount(cl, w * Xp[:, j] * y, cl.max() + 1).sum() for j in range(k)])
        Ap = np.array([[np.sum(w * Xp[:, j] * Xp[:, m]) for m in range(k)] for j in range(k)])
        perms.append(np.linalg.solve(Ap + 1e-12 * np.eye(k), bp))
    return beta, lo, hi, (np.percentile(perms, [5, 95], axis=0) if nperm else None)


# ---------------------------------------------------------------- the replacement
def sizing_terms(E, pg, R, info):
    """Per team-game-side: sum over regulars of miss x usual x (r_i - r_repl), for each rating, split QB / others."""
    Rr = R.select("gsis_id", "season", *RATINGS)
    newlvl = (
        R.filter(c("new") == 1)
        .join(info.select("gsis_id", "season", "group"), on=["gsis_id", "season"])
        .group_by("season", "group")
        .agg(*(c(r).mean().alias(f"{r}_new") for r in RATINGS))
    )
    E = E.filter(c("season") >= 2018)
    g0 = E.filter(c("miss") == 0).group_by("gsis_id", *CL).agg(n0=pl.len())
    mates = pg.select(
        j=c("gsis_id"),
        game_id=c("game_id"),
        team=c("team"),
        side=c("side"),
        season=c("season"),
        group=c("group"),
        share_j=c("share"),
    )
    # each regular's group-mates, their mean share over his full games, and their share in his missed games
    base = (
        E.filter(c("miss") == 0).select("gsis_id", "game_id", *CL, "group")
        .join(mates, on=["game_id", *CL, "group"])
        .filter(c("j") != c("gsis_id"))
        .group_by("gsis_id", "j", *CL).agg(s0=c("share_j").sum())
        .join(g0, on=["gsis_id", *CL])
        .with_columns(mean0=c("s0") / c("n0"))
    )  # fmt: skip
    M = E.filter(c("miss") > 0).select("gsis_id", "game_id", *CL, "group", "miss", "usual")
    inc = (
        M.join(mates, on=["game_id", *CL, "group"])
        .filter(c("j") != c("gsis_id"))
        .join(base.select("gsis_id", "j", *CL, "mean0"), on=["gsis_id", "j", *CL], how="left")
        .with_columns(inc=(c("share_j") - c("mean0").fill_null(0)).clip(0, None))
        .join(Rr.rename({"gsis_id": "j"}), on=["j", "season"], how="left")
        .group_by("gsis_id", "game_id", *CL)
        .agg(
            *((c("inc") * c(r).fill_null(0)).sum().alias(f"{r}_x") for r in RATINGS),
            winc=c("inc").sum(),
        )
    )
    Z = (
        M.join(inc, on=["gsis_id", "game_id", *CL], how="left")
        .join(Rr, on=["gsis_id", "season"], how="left")
        .join(newlvl, on=["season", "group"], how="left")
        .with_columns(
            *(
                pl.when(c("winc") > 0)
                .then(c(f"{r}_x") / c("winc"))
                .otherwise(c(f"{r}_new"))
                .alias(f"{r}_rep")
                for r in RATINGS
            )
        )
        .with_columns(
            *(
                (c("miss") * c("usual") * (c(r).fill_null(0) - c(f"{r}_rep").fill_null(0))).alias(
                    f"z_{r}"
                )
                for r in RATINGS
            )
        )
        .with_columns(cls=pl.when(c("group") == "QB").then(pl.lit("qb")).otherwise(pl.lit("oth")))
    )
    zz = Z.group_by("game_id", *CL, "cls").agg(*(c(f"z_{r}").sum() for r in RATINGS))
    zz = zz.pivot(on="cls", index=["game_id", *CL], values=[f"z_{r}" for r in RATINGS])
    return zz, Z


def run(tag, p, on, info, tg, E, Pl, pg, R):
    print("\n#################### " + tag + " ####################")
    print(
        "\n== 1. WHAT AN ABSENCE COSTS (per full game missed by one regular; EPA over expected a play for his side; 90% by resampling team-seasons) =="
    )
    beta_A = {}
    for side, groups in (("offense", OFF_G), ("defense", DEF_G)):
        X = (
            E.filter(c("side") == side)
            .group_by("game_id", *CL, "group")
            .agg(m=c("miss").sum())
            .pivot(on="group", index=["game_id", *CL], values="m")
        )
        Xp = (
            Pl.filter(c("side") == side)
            .group_by("game_id", *CL, "group")
            .agg(m=c("miss").sum())
            .pivot(on="group", index=["game_id", *CL], values="m")
        )
        Xp = Xp.rename({g: f"pl_{g}" for g in groups if g in Xp.columns})
        d = (
            tg.filter(c("side") == side)
            .join(X, on=["game_id", *CL], how="left")
            .join(Xp, on=["game_id", *CL], how="left")
            .fill_null(0)
        )
        for g in groups:
            if g not in d.columns:
                d = d.with_columns(pl.lit(0.0).alias(g))
            if f"pl_{g}" not in d.columns:
                d = d.with_columns(pl.lit(0.0).alias(f"pl_{g}"))
        Xm, y, w, cl, _ = wls_parts(d, groups)
        beta, lo, hi, null = wls(Xm, y, w, cl, nboot=500, nperm=200)
        Xq, yq, wq, clq, _ = wls_parts(d, [f"pl_{g}" for g in groups])
        bq, lq, hq, _ = wls(Xq, yq, wq, clq, nboot=300)
        print(f"  {side} ({len(np.unique(cl))} team-seasons, {len(y):,} team-games):")
        for i, g in enumerate(groups):
            beta_A[(side, g)] = beta[i]
            print(
                f"    {g}: {beta[i]:+.4f} ({lo[i]:+.4f} to {hi[i]:+.4f}); shuffled null 90% {null[0][i]:+.4f} to {null[1][i]:+.4f}; placebo, a non-regular (typical share 10-50%) {bq[i]:+.4f} ({lq[i]:+.4f} to {hq[i]:+.4f})"
            )

    print(
        "\n== 2. SIZING THE RATINGS (k: how many times the rating must be scaled to match real absences; 2018-2024) =="
    )
    zz, Z = sizing_terms(E, pg, R, info)
    print(
        f"  absences with a replacement found among group-mates whose plays rose: {(Z['winc'].fill_null(0) > 0).mean():.0%} (the rest use the group's new-player level)"
    )
    print("  his rating less his replacement's, mean over absences of half a game or more (QB | others): " + "; ".join(
        f"{r} {Z.filter((c('cls') == 'qb') & (c('miss') >= 0.5))[r].mean() - Z.filter((c('cls') == 'qb') & (c('miss') >= 0.5))[f'{r}_rep'].mean():+.4f} | {Z.filter((c('cls') == 'oth') & (c('miss') >= 0.5))[r].mean() - Z.filter((c('cls') == 'oth') & (c('miss') >= 0.5))[f'{r}_rep'].mean():+.4f}" for r in RATINGS))  # fmt: skip
    D = tg.filter(c("season") >= 2018).join(zz, on=["game_id", *CL], how="left").fill_null(0)
    for col in [f"z_{r}_{k}" for r in RATINGS for k in ("qb", "oth")]:
        if col not in D.columns:
            D = D.with_columns(pl.lit(0.0).alias(col))
    ks = {}
    for r, lab in RATINGS.items():
        cols = [f"z_{r}_qb", f"z_{r}_oth"]
        Xm, y, w, cl, _ = wls_parts(D, cols)
        beta, lo, hi, _ = wls(Xm, y, w, cl, nboot=500)
        ks[r] = -beta
        print(
            f"  {lab}: k for QBs {-beta[0]:.1f} (90% {-hi[0]:.1f} to {-lo[0]:.1f}); for everyone else {-beta[1]:.1f} ({-hi[1]:.1f} to {-lo[1]:.1f})"
        )
    Gc = (
        E.filter(c("season") >= 2018)
        .group_by("game_id", *CL, "group")
        .agg(m=c("miss").sum())
        .with_columns(group=c("side").str.slice(0, 1) + "_" + c("group"))
        .pivot(on="group", index=["game_id", *CL], values="m")
    )
    D2 = D.join(Gc, on=["game_id", *CL], how="left").fill_null(0)
    for col in GCOLS:
        if col not in D2.columns:
            D2 = D2.with_columns(pl.lit(0.0).alias(col))
    print(
        "  with each group's average absence cost in the same fit (k then says only whether a bigger rating gap means a bigger drop):"
    )
    for r, lab in RATINGS.items():
        Xm, y, w, cl, _ = wls_parts(D2, [*GCOLS, f"z_{r}_qb", f"z_{r}_oth"])
        beta, lo, hi, _ = wls(Xm, y, w, cl, nboot=500)
        print(
            f"    {lab}: k for QBs {-beta[-2]:.1f} (90% {-hi[-2]:.1f} to {-lo[-2]:.1f}); for everyone else {-beta[-1]:.1f} ({-hi[-1]:.1f} to {-lo[-1]:.1f})"
        )

    print(
        "\n== 3. THE EXTENSION: FIT ON 2018-2021 (group averages 2016-2021), SCORE HELD-OUT TEAM-GAMES 2022-2024 =="
    )
    print(
        "  share of the within-season error in a team-game's rate removed (plays-weighted), against predicting no change; 90% by resampling team-seasons"
    )
    allg = OFF_G + DEF_G
    G = (
        E.group_by("game_id", *CL, "group")
        .agg(m=c("miss").sum())
        .with_columns(group=c("side").str.slice(0, 1) + "_" + c("group"))
    )
    G = G.pivot(on="group", index=["game_id", *CL], values="m")
    gcols = GCOLS
    F = (
        tg.join(G, on=["game_id", *CL], how="left")
        .join(zz, on=["game_id", *CL], how="left")
        .fill_null(0)
    )
    for col in gcols + [f"z_{r}_{k}" for r in RATINGS for k in ("qb", "oth")]:
        if col not in F.columns:
            F = F.with_columns(pl.lit(0.0).alias(col))
    _ = allg

    def score(cols, fit_from):
        tr_ = F.filter(c("season").is_between(fit_from, 2021))
        te_ = F.filter(c("season") >= 2022)
        Xa, ya, wa, cla, _ = wls_parts(tr_, cols)
        beta, *_ = wls(Xa, ya, wa, cla, nboot=0)
        Xb, yb, wb, clb, _ = wls_parts(te_, cols)
        pr = Xb @ beta
        e0 = np.bincount(clb, wb * yb**2)
        e1 = np.bincount(clb, wb * (yb - pr) ** 2)
        return e0, e1

    res = {}
    specs = {
        "group averages (each group's absence cost)": (gcols, 2016),
        "group averages, fit on 2018-2021 only": (gcols, 2018),
        **{f"sized {RATINGS[r]}": ([f"z_{r}_qb", f"z_{r}_oth"], 2018) for r in RATINGS},
        **{
            f"group averages + sized {RATINGS[r]}": (gcols + [f"z_{r}_qb", f"z_{r}_oth"], 2018)
            for r in ("ra", "rs")
        },
    }
    for name, (cols, f0) in specs.items():
        e0, e1 = score(cols, f0)
        res[name] = (e0, e1)
        bs = [
            1 - e1[s].sum() / e0[s].sum()
            for s in (RNG.integers(0, len(e0), len(e0)) for _ in range(1000))
        ]
        lo, hi = np.percentile(bs, [5, 95])
        print(
            f"    {name:<62} {100 * (1 - e1.sum() / e0.sum()):+.3f}% ({100 * lo:+.3f} to {100 * hi:+.3f})"
        )
    a0, a1 = res["group averages, fit on 2018-2021 only"]
    for r in ("ra", "rs"):
        _, b1 = res[f"sized {RATINGS[r]}"]
        bs = [
            (a1[s].sum() - b1[s].sum()) / a0[s].sum()
            for s in (RNG.integers(0, len(a0), len(a0)) for _ in range(1000))
        ]
        lo, hi = np.percentile(bs, [5, 95])
        print(
            f"    sized {r} less group averages (same fit seasons): {100 * (a1.sum() - b1.sum()) / a0.sum():+.3f} points ({100 * lo:+.3f} to {100 * hi:+.3f})"
        )

    print(
        "\n== 4. THE ROSTER-CHANGE TEST WITH SIZED RATINGS (2022-2024; k from 2018-2021; the new-player share in the baseline) =="
    )
    D21 = D.filter(c("season") <= 2021)
    k21 = {}
    for r in ("ra", "rp"):
        Xm, y, w, cl, _ = wls_parts(D21, [f"z_{r}_qb", f"z_{r}_oth"])
        k21[r] = -wls(Xm, y, w, cl, nboot=0)[0]
    print(
        "  k fit on 2018-2021: "
        + "; ".join(f"{r} QB {k21[r][0]:.1f}, others {k21[r][1]:.1f}" for r in k21)
    )
    used = on.group_by("team", "season", "side", "gsis_id").agg(n_on=pl.len())
    ntot = on.group_by("team", "season", "side").agg(n_team=c("play_id").n_unique())
    x = (
        used.join(ntot, on=CL)
        .join(R, on=["gsis_id", "season"])
        .join(info.select("gsis_id", "season", "group"), on=["gsis_id", "season"])
    )
    x = x.with_columns(sh=c("n_on") / c("n_team"), isqb=(c("group") == "QB"))
    tv = x.group_by(CL).agg(
        share_new=(c("sh") * c("new")).sum() / c("sh").sum(),
        rp_plain=(c("sh") * c("rp")).sum(),
        ra_plain=(c("sh") * c("ra")).sum(),
        ra_sized=(
            c("sh") * c("ra") * pl.when(c("isqb")).then(k21["ra"][0]).otherwise(k21["ra"][1])
        ).sum(),
        rp_sized=(
            c("sh") * c("rp") * pl.when(c("isqb")).then(k21["rp"][0]).otherwise(k21["rp"][1])
        ).sum(),
    )
    trt = fl.team_rates(p.filter(c("season").is_in(fl.SEASONS)))
    for col, lab in (("rp_plain", "plus-minus with prior (first look), unsized"), ("rp_sized", "plus-minus with prior, sized (QB and others)"),
                     ("ra_plain", "plus-minus from his own stats (a), unsized"), ("ra_sized", "plus-minus from his own stats (a), sized")):  # fmt: skip
        mc.travel_cols(trt, tv, [col], ["share_new"], lab, start=2022)


def main():
    p = fl.plays()
    on = fl.on_field(p)
    info = fl.player_info(on)
    tg = team_games(p, on)
    E, pg = absences(on, tg, 0.5, 1.01)
    Pl, _ = absences(on, tg, 0.1, 0.5)
    log("absences", E.height, Pl.height)

    print("== DATA ==")
    print(
        f"Team-games (each side), 2016-2024, final weeks dropped: {tg.height:,}; regulars (typical share 50%+, 4+ games): {E.select('gsis_id', *CL).unique().height:,} player-team-seasons"
    )
    print(
        "  absences of half a game or more, by group: "
        + "; ".join(
            f"{g} {E.filter((c('group') == g) & (c('miss') >= 0.5)).height:,}" for g in fl.GROUPS
        )
    )
    print(
        "  whole games missed (share 0): "
        + "; ".join(
            f"{g} {E.filter((c('group') == g) & (c('share') == 0)).height:,}" for g in fl.GROUPS
        )
    )
    sd_within = tg.with_columns(r=c("s_g") / c("n_g")).with_columns(
        d=c("r") - c("r").mean().over(CL)
    )
    print(
        f"  noise: a team-game's rate less its season's mean has sd {sd_within['d'].std():.3f} EPA a play (a game is about {tg['n_g'].median():.0f} plays: dice alone {1.378 / np.sqrt(tg['n_g'].median()):.3f})"
    )

    R, pmdf, pmp = rt.make_ratings(p, on, info)
    run("[pre-registered: partial games count as partial absences]", p, on, info, tg, E, Pl, pg, R)
    whole = c("share") == 0
    Ew = E.with_columns(miss=whole.cast(pl.Float64))
    Plw = Pl.with_columns(miss=whole.cast(pl.Float64))
    run(
        "[check: whole games missed only (no snaps); partial games count as played]",
        p,
        on,
        info,
        tg,
        Ew,
        Plw,
        pg,
        R,
    )
    Es, _ = absences(on, tg, 0.5, 1.01, starters=True)
    run(
        "[check: each team-season's main starters by plays (QB1, RB1, WR1-3, TE1, OL1-5, DL1-4, LB1-2, DB1-5), whole games missed only]",
        p, on, info, tg, Es.with_columns(miss=whole.cast(pl.Float64)), Plw, pg, R,
    )  # fmt: skip
    log("done")


if __name__ == "__main__":
    main()
