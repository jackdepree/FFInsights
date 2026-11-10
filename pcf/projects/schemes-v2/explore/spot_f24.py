"""The CEO's spot-check of F24 (2026-11-09): matchup types learned from results, in depth.

1. Stability: the chosen setting (k 2, λ 1) on 2015-2024 with 5 different random seeds (folds and
   starting values).
2. Without 2021: r on the other nine test seasons, against 20 shuffles.
3. The in-season trend control. A team that improves through the season, and the defenses it
   happened to meet late, could look like a "matchup type". Here each unit also gets a slope on
   the week (ridge), in the baseline and inside the factor model; does the matchup part still
   predict what strength *and trend* miss?
4. The learned 2021 types, by team, next to their charted styles (season means of man, two-high,
   blitz, box over expected, pressure).
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/spot_f24.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from latent import BIAS_LAM, FOLDS, ITERS, als, collect, r
from rematch import load

from pcf.config import get_config

c = pl.col
BEST = (2, 1)
TEST = range(2015, 2025)
SLOPE_LAM = 20.0


def als_trend(o, d, wk, y, no, nd, k, lam, rng):
    """Strengths, per-unit week slopes and k factors, by alternating ridge least squares."""
    mu = y.mean()
    a, b, sa, sb = np.zeros(no), np.zeros(nd), np.zeros(no), np.zeros(nd)
    U = rng.normal(0, 0.01, (no, k)) if k else np.zeros((no, 0))
    V = rng.normal(0, 0.01, (nd, k)) if k else np.zeros((nd, 0))
    io = [np.flatnonzero(o == i) for i in range(no)]
    jd = [np.flatnonzero(d == j) for j in range(nd)]
    for _ in range(ITERS):
        inter = (U[o] * V[d]).sum(1) if k else 0.0
        rr = y - mu - b[d] - sb[d] * wk - inter
        for i, ix in enumerate(io):
            if len(ix):
                X = np.column_stack([np.ones(len(ix)), wk[ix]])
                a[i], sa[i] = np.linalg.solve(
                    X.T @ X + np.diag([BIAS_LAM, SLOPE_LAM]), X.T @ rr[ix]
                )
        rr = y - mu - a[o] - sa[o] * wk - inter
        for j, ix in enumerate(jd):
            if len(ix):
                X = np.column_stack([np.ones(len(ix)), wk[ix]])
                b[j], sb[j] = np.linalg.solve(
                    X.T @ X + np.diag([BIAS_LAM, SLOPE_LAM]), X.T @ rr[ix]
                )
        if not k:
            continue
        rr = y - mu - a[o] - sa[o] * wk - b[d] - sb[d] * wk
        for i, ix in enumerate(io):
            if len(ix):
                Vi = V[d[ix]]
                U[i] = np.linalg.solve(Vi.T @ Vi + lam * np.eye(k), Vi.T @ rr[ix])
        for j, ix in enumerate(jd):
            if len(ix):
                Uj = U[o[ix]]
                V[j] = np.linalg.solve(Uj.T @ Uj + lam * np.eye(k), Uj.T @ rr[ix])
    return mu, a, b, sa, sb, U, V


def trend_test(s, seasons, rng):
    miss_all, part_all = [], []
    for yr in seasons:
        t = s.filter(c("season") == yr)
        teams = sorted(set(t["off"].to_list()) | set(t["dfn"].to_list()))
        ix = {x: i for i, x in enumerate(teams)}
        o = np.array([ix[x] for x in t["off"].to_list()])
        d = np.array([ix[x] for x in t["dfn"].to_list()])
        wk = (t["week"].to_numpy() - 9.0) / 8.0
        y = t["y"].to_numpy()
        fold = rng.permutation(len(y)) % FOLDS
        miss, part = np.zeros(len(y)), np.zeros(len(y))
        for f in range(FOLDS):
            tr, te = fold != f, fold == f
            mu, a, b, sa, sb, _, _ = als_trend(
                o[tr], d[tr], wk[tr], y[tr], len(teams), len(teams), 0, 0, rng
            )
            miss[te] = y[te] - (mu + a[o[te]] + sa[o[te]] * wk[te] + b[d[te]] + sb[d[te]] * wk[te])
            *_, U, V = als_trend(o[tr], d[tr], wk[tr], y[tr], len(teams), len(teams), *BEST, rng)
            part[te] = (U[o[te]] * V[d[te]]).sum(1)
        miss_all.append(miss)
        part_all.append(part)
    return np.concatenate(miss_all), np.concatenate(part_all)


def main() -> None:
    s = load()
    print("== 1. Stability: the chosen setting on 2015-2024, 5 seeds")
    vals = []
    for seed in range(5):
        m, p, _ = collect(s, TEST, [BEST], np.random.default_rng(seed))
        vals.append(r(p[BEST], m))
    print(f"   r by seed: {', '.join(f'{v:+.3f}' for v in vals)}; mean {np.mean(vals):+.3f}")

    print("\n== 2. Without 2021")
    rng = np.random.default_rng(7)
    nine = [yr for yr in TEST if yr != 2021]
    reals = []
    for seed in range(5):
        m, p, _ = collect(s, nine, [BEST], np.random.default_rng(100 + seed))
        reals.append(r(p[BEST], m))
    nl = [
        r(p0[BEST], m0)
        for m0, p0, _ in (collect(s, nine, [BEST], rng, shuffle=True) for _ in range(20))
    ]
    print(
        f"   nine seasons, 5 seeds: r {', '.join(f'{v:+.3f}' for v in reals)} (mean {np.mean(reals):+.3f}); shuffled: mean {np.mean(nl):+.3f}, sd {np.std(nl):.3f}, "
        f"95th {np.quantile(nl, 0.95):+.3f}"
    )

    print("\n== 3. With each unit's in-season trend in the baseline and the model (2015-2024)")
    vals = []
    for seed in range(3):
        m, p = trend_test(s, TEST, np.random.default_rng(200 + seed))
        vals.append(r(p, m))
    print(
        f"   r by seed: {', '.join(f'{v:+.3f}' for v in vals)}; mean {np.mean(vals):+.3f} (without the trend control, section 1's mean)"
    )

    print("\n== 4. The learned 2021 types (whole season, k 2, λ 1)")
    t = s.filter(c("season") == 2021)
    teams = sorted(set(t["off"].to_list()) | set(t["dfn"].to_list()))
    ix = {x: i for i, x in enumerate(teams)}
    o = np.array([ix[x] for x in t["off"].to_list()])
    d = np.array([ix[x] for x in t["dfn"].to_list()])
    mu, a, b, U, V = als(
        o, d, t["y"].to_numpy(), len(teams), len(teams), *BEST, np.random.default_rng(0)
    )
    # rotate to the main direction of the matchup part
    W = U @ V.T
    uu, sv, vt = np.linalg.svd(W)
    u1, v1 = uu[:, 0] * np.sqrt(sv[0]), vt[0] * np.sqrt(sv[0])
    print(f"   strength of the two directions: {sv[0]:.3f}, {sv[1]:.3f}")
    tg = (
        pl.read_parquet(get_config().zone("interim") / "schemes_v2" / "team_game.parquet")
        .filter(c("season") == 2021)
        .group_by("team")
        .agg(
            *[
                c(x).fill_nan(None).mean()
                for x in (
                    "d_man",
                    "d_two_high",
                    "d_blitz",
                    "d_box_oe",
                    "d_pressure",
                    "proe",
                    "adot",
                    "shotgun_oe",
                )
            ]
        )
    )
    sty = {r_["team"]: r_ for r_ in tg.iter_rows(named=True)}
    print(
        "   defenses along the main direction (v), with charted styles: man, two-high, blitz, box over exp, pressure"
    )
    order = np.argsort(v1)
    for j in list(order[:5]) + list(order[-5:]):
        st = sty[teams[j]]
        print(
            f"      {teams[j]:<4} v {v1[j]:+.3f}   man {st['d_man']:.2f}  two-high {st['d_two_high']:.2f}  blitz {st['d_blitz']:.2f}  box {st['d_box_oe']:+.2f}  pressure {st['d_pressure']:.2f}  (strength {b[j]:+.3f})"
        )
    print("   offenses along it (u), with pass over expected, depth, shotgun over expected")
    order = np.argsort(u1)
    for i in list(order[:5]) + list(order[-5:]):
        st = sty[teams[i]]
        print(
            f"      {teams[i]:<4} u {u1[i]:+.3f}   pass oe {st['proe']:+.3f}  depth {st['adot']:.1f}  shotgun oe {st['shotgun_oe']:+.3f}  (strength {a[i]:+.3f})"
        )
    dcols = ["d_man", "d_two_high", "d_blitz", "d_box_oe", "d_pressure"]
    vd = np.array([[sty[x][cname] for cname in dcols] for x in teams], float)
    print(
        "   r between the defenses' learned direction and each charted style: "
        + ", ".join(
            f"{cname} {np.corrcoef(v1, vd[:, k])[0, 1]:+.2f}" for k, cname in enumerate(dcols)
        )
    )
    ocols = ["proe", "adot", "shotgun_oe"]
    vo = np.array([[sty[x][cname] for cname in ocols] for x in teams], float)
    print(
        "   r between the offenses' learned direction and each charted style: "
        + ", ".join(
            f"{cname} {np.corrcoef(u1, vo[:, k])[0, 1]:+.2f}" for k, cname in enumerate(ocols)
        )
    )
    print("   (32 teams: |r| above about 0.35 is beyond chance at 5%)")


if __name__ == "__main__":
    main()
