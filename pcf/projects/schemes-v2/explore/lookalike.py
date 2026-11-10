"""Scheme against scheme, A2 (the CEO, 2026-11-09): does the rematch pattern hold for look-alike opponents?

"it should also hold for teams that play against another opponent that fits the same scheme as past
opponents ... different teams that fit similar styles share similar outcomes in the same direction
after accounting for elo or average epa."

For every offense and every pair of its games in a season against two *different* defenses:
- each game's residual is the offense's EPA per play beyond both units' season strength, leaving
  out both games (as in F20);
- the two defenses' style similarity: minus the distance between their season style vectors
  (each tendency standardized within the season), so higher is more alike;
- their strength similarity: minus the gap between their season EPA allowed (the CEO's "good team
  against bad team" check).
The test: the product of the two residuals (as a correlation) regressed on style similarity, with
strength similarity and weeks apart as controls. Positive means an offense does alike against
alike defenses: the matchup travels with the style, not just the opponent. The mirror runs for each
defense against pairs of look-alike offenses.
Null: style vectors shuffled among units within the season (200 times). Intervals resample
offense (or defense) team-seasons.

Styles: offense = pass rate over expected, shotgun, no-huddle, throw depth, outside runs, tempo
(2006-2024; plus 11 and heavy personnel from 2016); defense = man, two-high, blitz, box over
expected (2018-2024: coverage is charted from 2018). The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/lookalike.py
"""

# ruff: noqa: E501
from __future__ import annotations

from collections import defaultdict

import numpy as np
import polars as pl
from rematch import Strength, fit, load

from pcf.config import get_config

c = pl.col
RNG = np.random.default_rng(20261111)
SHUFFLES = 200
DRAWS = 1000
OFF_STYLE = ["proe", "shotgun_oe", "no_huddle_oe", "adot", "outside_run", "tempo"]
OFF_STYLE_16 = OFF_STYLE + ["p11", "heavy"]
DEF_STYLE = ["d_man", "d_two_high", "d_blitz", "d_box_oe"]


def styles(cols: list[str], first: int) -> dict:
    tg = pl.read_parquet(get_config().zone("interim") / "schemes_v2" / "team_game.parquet").filter(
        c("season") >= first
    )
    m = tg.group_by("season", "team").agg(*[c(x).fill_nan(None).mean() for x in cols])
    m = m.with_columns(
        *[((c(x) - c(x).mean().over("season")) / c(x).std().over("season")) for x in cols]
    ).drop_nulls()
    return {
        (r["season"], r["team"]): np.array([r[x] for x in cols]) for r in m.iter_rows(named=True)
    }


def pairs(s: pl.DataFrame, st: Strength, b, side: str, first: int):
    """Every pair of one unit's games against two different opponents in a season."""
    s = s.filter(c("season") >= first)
    unit, opp = ("off", "dfn") if side == "off" else ("dfn", "off")
    by = defaultdict(list)
    for r in s.iter_rows(named=True):
        by[(r["season"], r[unit])].append(r)
    opp_by = defaultdict(list)
    for r in s.iter_rows(named=True):
        opp_by[(r["season"], r[opp])].append(r["y"])
    allowed = {k: float(np.mean(v)) for k, v in opp_by.items()}
    out = []
    for (season, u), games in by.items():
        for i in range(len(games)):
            for j in range(i + 1, len(games)):
                g1, g2 = games[i], games[j]
                if g1[opp] == g2[opp]:
                    continue
                skip = {g1["game_id"], g2["game_id"]}
                e = []
                for g in (g1, g2):
                    so, sd = st.pair(season, g["off"], g["dfn"], skip)
                    e.append(g["y"] - (b[0] + b[1] * so + b[2] * sd))
                out.append(
                    (
                        season,
                        u,
                        g1[opp],
                        g2[opp],
                        e[0],
                        e[1],
                        abs(g2["week"] - g1["week"]),
                        -abs(allowed[(season, g1[opp])] - allowed[(season, g2[opp])]),
                    )
                )
    return out


def run(rows, sty: dict, label: str) -> None:
    rows = [
        r
        for r in rows
        if (r[0], r[2]) in sty and (r[0], r[3]) in sty and np.isfinite(r[4]) and np.isfinite(r[5])
    ]
    season = np.array([r[0] for r in rows])
    unit = np.array([f"{r[0]}-{r[1]}" for r in rows])
    o1 = [(r[0], r[2]) for r in rows]
    o2 = [(r[0], r[3]) for r in rows]
    e1, e2 = np.array([r[4] for r in rows]), np.array([r[5] for r in rows])
    sd = np.sqrt(0.5 * (e1.var() + e2.var()))
    prod = (e1 - e1.mean()) * (e2 - e2.mean()) / sd**2  # each pair's contribution to a correlation
    gap = np.array([r[6] for r in rows], float)
    ssim = np.array([r[7] for r in rows])

    def sims(st):
        return -np.array([np.linalg.norm(st[a] - st[b]) for a, b in zip(o1, o2, strict=True)])

    def z(x):
        return (x - x.mean()) / x.std()

    gapz, ssz = z(gap), z(ssim)

    def slope(sim, idx=None):
        i = np.arange(len(prod)) if idx is None else idx
        X = np.column_stack([np.ones(len(i)), z(sim)[i], ssz[i], gapz[i]])
        return np.linalg.lstsq(X, prod[i], rcond=None)[0]

    sim = sims(sty)
    b = slope(sim)
    q = np.quantile(sim, [0.2, 0.8])
    hi, lo = prod[sim >= q[1]].mean(), prod[sim <= q[0]].mean()
    # null: shuffle style vectors among units within each season
    null = []
    keys = list(sty)
    for _ in range(SHUFFLES):
        sh = {}
        for s_ in np.unique([k[0] for k in keys]):
            ks = [k for k in keys if k[0] == s_]
            vs = [sty[k] for k in ks]
            perm = RNG.permutation(len(ks))
            sh.update({k: vs[p] for k, p in zip(ks, perm, strict=True)})
        null.append(slope(sims(sh))[1])
    null = np.array(null)
    # interval: resample unit-seasons
    groups = defaultdict(list)
    for k, u in enumerate(unit):
        groups[u].append(k)
    gk = list(groups)
    boots = []
    for _ in range(DRAWS):
        pick = RNG.choice(len(gk), len(gk))
        idx = np.concatenate([groups[gk[p]] for p in pick])
        boots.append(slope(sim, idx)[1:3])
    boots = np.array(boots)
    print(
        f"\n== {label}: {len(rows):,} pairs of games ({len(groups):,} unit-seasons, {season.min()}-{season.max()})"
    )
    print(f"   overall r between a unit's two residuals (different opponents): {prod.mean():+.3f}")
    print(f"   most alike fifth of opponent pairs: r {hi:+.3f}; least alike fifth: r {lo:+.3f}")
    print(
        f"   style similarity: {b[1]:+.4f} r per sd (90% {np.quantile(boots[:, 0], 0.05):+.4f} to {np.quantile(boots[:, 0], 0.95):+.4f}); "
        f"shuffled styles at or above: {np.mean(null >= b[1]):.1%}"
    )
    print(
        f"   strength similarity (the 'good against bad' check): {b[2]:+.4f} r per sd (90% {np.quantile(boots[:, 1], 0.05):+.4f} to {np.quantile(boots[:, 1], 0.95):+.4f}); weeks apart {b[3]:+.4f}"
    )


def main() -> None:
    s = load()
    st = Strength(s)
    b, _, _ = fit(s, st)
    run(
        pairs(s, st, b, "off", 2018),
        styles(DEF_STYLE, 2018),
        "1. An offense against look-alike defenses (2018-2024: man, two-high, blitz, box)",
    )
    run(
        pairs(s, st, b, "def", 2006),
        styles(OFF_STYLE, 2006),
        "2. A defense against look-alike offenses (2006-2024: pass, shotgun, no-huddle, depth, outside runs, tempo)",
    )
    run(
        pairs(s, st, b, "def", 2016),
        styles(OFF_STYLE_16, 2016),
        "   the same, 2016-2024 with personnel (11, heavy)",
    )


if __name__ == "__main__":
    main()
