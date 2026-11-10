"""Strengthening the learned matchup types (I26; the CEO, 2026-11-09: "Strengthen the matchup types").

F26 (types from the season's earlier games, k 2, λ 1) predicts what strength misses at r +0.031 in
2015-2024 and +0.37 points per sd against the close. Four variants, fixed before running, each
judged exactly as F26 (earlier games only; the same strength-only baseline and miss; offense EPA per
play over all scrimmage plays; weeks 6+; 2015-2024; defenses swapped within the week for the null,
20 times; the close):
- **V1, a quieter outcome:** the types are learned from success rate instead of EPA per play
  (success is a yes/no per play, so it carries less noise per game); the part is judged against the
  EPA miss as is (r doesn't depend on scale; a rescale fitted in-sample could flip its sign).
- **V2, passing and rushing apart:** types learned separately from EPA per dropback and EPA per
  run; the part is the offense's pass share (earlier games) × the passing part + the rest × the
  rushing part.
- **V3, carried across seasons:** this season's hidden numbers are pulled toward last season's
  (ridge toward the prior, weight λ0 = 4), from a fit on all of last season (known by then), so
  weeks 2-5 get forecasts too (reported apart).
- **V23:** V2 and V3 together.
Pass/run splits come from play-by-play (regular season, scrimmage plays, kneels and spikes out).
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/strengthen.py V1   (or V2, V3, V23, V0; 2015-2024 only)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys

import numpy as np
import polars as pl
from latent import BIAS_LAM, ITERS
from rematch import load
from walkforward import market

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
K, LAM, LAM0 = 2, 1.0, 4.0
FIRST_WEEK = 6
SHUFFLES = 20
SPLIT = get_config().zone("interim") / "schemes_v2" / "side_split.parquet"


def side_split() -> pl.DataFrame:
    if SPLIT.exists():
        return pl.read_parquet(SPLIT)
    out = []
    for s in range(2005, 2025):
        p = (
            read_part("play", "pbp", [s])
            .select(
                "game_id",
                "season_type",
                "posteam",
                "pass",
                "rush",
                "qb_kneel",
                "qb_spike",
                "epa",
                "success",
            )
            .collect()
            .filter(
                (c("season_type") == "REG")
                & ((c("pass") == 1) | (c("rush") == 1))
                & (c("qb_kneel") == 0)
                & (c("qb_spike") == 0)
                & c("posteam").is_not_null()
                & c("epa").is_not_null()
            )
        )
        out.append(
            p.group_by("game_id", team="posteam").agg(
                pass_epa=c("epa").filter(c("pass") == 1).mean(),
                run_epa=c("epa").filter(c("pass") == 0).mean(),
                n_pass=(c("pass") == 1).sum(),
                n_run=(c("pass") == 0).sum(),
                success=c("success").mean(),
            )
        )
    t = pl.concat(out)
    t.write_parquet(SPLIT)
    return t


def als(o, d, y, no, nd, k, lam, rng, U0=None, V0=None, lam0=0.0):
    """Strengths and k hidden numbers; with U0/V0, the numbers are pulled toward them (weight lam0)."""
    ok = np.isfinite(y)
    o, d, y = o[ok], d[ok], y[ok]
    mu = y.mean() if len(y) else 0.0
    a, b = np.zeros(no), np.zeros(nd)
    U = U0.copy() if U0 is not None else rng.normal(0, 0.01, (no, k))
    V = V0.copy() if V0 is not None else rng.normal(0, 0.01, (nd, k))
    P_u = U0 if U0 is not None else np.zeros((no, k))
    P_v = V0 if V0 is not None else np.zeros((nd, k))
    io = [np.flatnonzero(o == i) for i in range(no)]
    jd = [np.flatnonzero(d == j) for j in range(nd)]
    for _ in range(ITERS if k else 5):
        inter = (U[o] * V[d]).sum(1) if k else 0.0
        r = y - mu - b[d] - inter
        a = np.array([r[ix].sum() / (len(ix) + BIAS_LAM) if len(ix) else 0.0 for ix in io])
        r = y - mu - a[o] - inter
        b = np.array([r[ix].sum() / (len(ix) + BIAS_LAM) if len(ix) else 0.0 for ix in jd])
        if not k:
            continue
        r = y - mu - a[o] - b[d]
        for i, ix in enumerate(io):
            Vi = V[d[ix]]
            U[i] = np.linalg.solve(
                Vi.T @ Vi + (lam + lam0) * np.eye(k), Vi.T @ r[ix] + lam0 * P_u[i]
            )
        for j, ix in enumerate(jd):
            Uj = U[o[ix]]
            V[j] = np.linalg.solve(
                Uj.T @ Uj + (lam + lam0) * np.eye(k), Uj.T @ r[ix] + lam0 * P_v[j]
            )
    return mu, a, b, U, V


def shuffled_dfn(t: pl.DataFrame, rng) -> list[str]:
    dfn = t["dfn"].to_list()
    wk = t["week"].to_numpy()
    for w in np.unique(wk):
        i = np.flatnonzero(wk == w)
        vals = [t["dfn"][int(j)] for j in rng.permutation(i)]
        for a_, v in zip(i, vals, strict=True):
            dfn[a_] = v
    return dfn


def priors(s: pl.DataFrame, yr: int, teams: list[str], outcome: str, rng, shuffle: bool):
    """Last season's hidden numbers per team (all of last season), mapped onto this season's teams."""
    t = s.filter(c("season") == yr - 1).sort("week", "game_id", "off")
    if t.height == 0:
        return None, None
    dfn = shuffled_dfn(t, rng) if shuffle else t["dfn"].to_list()
    tt = sorted(set(t["off"].to_list()) | set(dfn))
    ix = {x: i for i, x in enumerate(tt)}
    o = np.array([ix[x] for x in t["off"].to_list()])
    d = np.array([ix[x] for x in dfn])
    *_, U, V = als(o, d, t[outcome].to_numpy(), len(tt), len(tt), K, LAM, rng)
    U0, V0 = np.zeros((len(teams), K)), np.zeros((len(teams), K))
    for i, x in enumerate(teams):
        if x in ix:
            U0[i], V0[i] = U[ix[x]], V[ix[x]]
    return U0, V0


def season(s: pl.DataFrame, yr: int, variant: str, rng, shuffle: bool) -> pl.DataFrame:
    t = s.filter(c("season") == yr).sort("week", "game_id", "off")
    dfn = shuffled_dfn(t, rng) if shuffle else t["dfn"].to_list()
    teams = sorted(set(t["off"].to_list()) | set(dfn))
    ix = {x: i for i, x in enumerate(teams)}
    o = np.array([ix[x] for x in t["off"].to_list()])
    d = np.array([ix[x] for x in dfn])
    wk = t["week"].to_numpy()
    y = t["y"].to_numpy()
    carry = variant in ("V3", "V23")
    split = variant in ("V2", "V23")
    outs = ["pass_epa", "run_epa"] if split else (["success"] if variant == "V1" else ["y"])
    pri = {out: priors(s, yr, teams, out, rng, shuffle) if carry else (None, None) for out in outs}
    miss = np.full(len(y), np.nan)
    part = np.full(len(y), np.nan)
    first = 2 if carry else FIRST_WEEK
    for w in np.unique(wk):
        if w < first:
            continue
        tr, te = wk < w, wk == w
        mu, a, b, _, _ = als(o[tr], d[tr], y[tr], len(teams), len(teams), 0, 0, rng)
        miss[te] = y[te] - (mu + a[o[te]] + b[d[te]])
        parts = {}
        for out in outs:
            U0, V0 = pri[out]
            *_, U, V = als(
                o[tr],
                d[tr],
                t[out].to_numpy()[tr],
                len(teams),
                len(teams),
                K,
                LAM,
                rng,
                U0,
                V0,
                LAM0 if U0 is not None else 0.0,
            )
            parts[out] = ((U[o] * V[d]).sum(1), U, V)
        if split:
            npass, nrun = t["n_pass"].to_numpy().astype(float), t["n_run"].to_numpy().astype(float)
            share = np.zeros(len(teams))
            for i in range(len(teams)):
                m = tr & (o == i)
                share[i] = (
                    npass[m].sum() / max(npass[m].sum() + nrun[m].sum(), 1) if m.any() else 0.55
                )
            p = share[o] * parts["pass_epa"][0] + (1 - share[o]) * parts["run_epa"][0]
        elif variant == "V1":
            p = parts["success"][0]  # judged against the EPA miss as is: r doesn't depend on scale
        else:
            p = parts["y"][0]
        part[te] = p[te]
    return t.select("game_id", "season", "week", "off").with_columns(
        miss=pl.Series(miss), part=pl.Series(part)
    )


def run(s, seasons, variant, rng, shuffle=False) -> pl.DataFrame:
    return pl.concat([season(s, yr, variant, rng, shuffle) for yr in seasons]).filter(
        c("part").is_not_nan() & c("miss").is_not_nan()
    )


def r(df: pl.DataFrame) -> float:
    return float(np.corrcoef(df["part"].to_numpy(), df["miss"].to_numpy())[0, 1])


def main() -> None:
    variant = sys.argv[1] if len(sys.argv) > 1 else "V0"
    rng = np.random.default_rng(20261118)
    s = load().join(
        side_split(), left_on=["game_id", "off"], right_on=["game_id", "team"], how="left"
    )
    test = range(2015, 2025)
    new = run(s, test, variant, rng)
    nulls = [run(s, test, variant, rng, shuffle=True) for _ in range(SHUFFLES)]
    main6 = new.filter(c("week") >= FIRST_WEEK)
    n6 = [n.filter(c("week") >= FIRST_WEEK) for n in nulls]
    nr = np.array([r(n) for n in n6])
    print(
        f"== {variant}: weeks 6+, 2015-2024: {main6.height:,} sides, r {r(main6):+.4f}; shuffled: mean {nr.mean():+.4f}, 95th {np.quantile(nr, 0.95):+.4f}, at or above {np.mean(nr >= r(main6)):.0%}"
    )
    for lo, hi in ((6, 9), (10, 13), (14, 18)):
        print(f"   weeks {lo}-{hi}: r {r(main6.filter(c('week').is_between(lo, hi))):+.4f}")
    if variant in ("V3", "V23"):
        early = new.filter(c("week") < FIRST_WEEK)
        ne = np.array([r(n.filter(c("week") < FIRST_WEEK)) for n in nulls])
        print(
            f"   weeks 2-5 (only possible when carried): {early.height:,} sides, r {r(early):+.4f}; shuffled at or above {np.mean(ne >= r(early)):.0%}"
        )
    by = " ".join(f"{yr % 100:02d}:{r(main6.filter(c('season') == yr)):+.3f}" for yr in test)
    print(f"   by season (weeks 6+): {by}")
    mr, n, x, y = market(main6)
    mn = np.array([market(nn)[0] for nn in n6])
    pts = np.polyfit(x / x.std(), y, 1)[0]
    print(
        f"   against the close (weeks 6+): {n:,} games, r {mr:+.4f} ({pts:+.2f} points per sd); shuffled at or above {np.mean(mn >= mr):.0%}"
    )


if __name__ == "__main__":
    main()
