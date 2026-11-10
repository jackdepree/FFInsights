"""F20 corrected (spot-check, 2026-11-09): symmetric exclusions, with intervals, and gap-matched.

The spot-check found F20's baselines were biased low: the first meeting's strength included the
baseline game, which builds in a negative correlation. Here every pair (the rematch and every
baseline pair) leaves out both of its games, so all three carry the same estimation terms.
- all: every other game of the offense (other defenses) and of the defense (other offenses);
- gap-matched: only other games within 2 weeks of the rematch's week.
90% intervals resample team pairs (1,000 draws).

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/spot_f20b.py
"""

# ruff: noqa: E501
from __future__ import annotations

from collections import defaultdict

import numpy as np
from rematch import Strength, fit, load
from spot_f20 import rematches

RNG = np.random.default_rng(20261116)
DRAWS = 1000


def main() -> None:
    s = load()
    st = Strength(s)
    b, _, _ = fit(s, st)

    def res(r, skip):
        so, sd = st.pair(r["season"], r["off"], r["dfn"], skip)
        return r["y"] - (b[0] + b[1] * so + b[2] * sd)

    v = float(np.nanvar([res(r, {r["game_id"]}) for r in s.iter_rows(named=True)]))
    for label, near in (
        ("all other games", None),
        ("gap-matched (within 2 weeks of the rematch)", 2),
    ):
        real, bo, bd, cl, seasons = [], [], [], [], []
        for season, off, dfn, g1, g2, oth_o, oth_d in rematches(s):
            if near is not None:
                oth_o = [
                    r
                    for r in oth_o
                    if abs(r["week"] - g2["week"]) <= near and r["game_id"] != g1["game_id"]
                ]
                oth_d = [
                    r
                    for r in oth_d
                    if abs(r["week"] - g2["week"]) <= near and r["game_id"] != g1["game_id"]
                ]
            if not oth_o or not oth_d:
                continue
            sk = {g1["game_id"], g2["game_id"]}
            pr = res(g1, sk) * res(g2, sk)
            po = np.mean(
                [
                    res(g1, {g1["game_id"], r["game_id"]}) * res(r, {g1["game_id"], r["game_id"]})
                    for r in oth_o
                ]
            )
            pd_ = np.mean(
                [
                    res(g1, {g1["game_id"], r["game_id"]}) * res(r, {g1["game_id"], r["game_id"]})
                    for r in oth_d
                ]
            )
            if not np.isfinite(pr + po + pd_):
                continue
            real.append(pr)
            bo.append(po)
            bd.append(pd_)
            cl.append((season, *sorted((off, dfn))))
            seasons.append(season)
        real, bo, bd, seasons = map(np.array, (real, bo, bd, seasons))
        groups = defaultdict(list)
        for k, g in enumerate(cl):
            groups[g].append(k)
        keys = list(groups)

        def share(i):
            return (real[i].mean() - bo[i].mean() - bd[i].mean()) / v

        boots = [
            share(np.concatenate([groups[keys[p]] for p in RNG.choice(len(keys), len(keys))]))
            for _ in range(DRAWS)
        ]
        lo, hi = np.quantile(boots, [0.05, 0.95])
        print(f"\n== {label}: {len(real):,} rematches")
        print(
            f"   rematch r {real.mean() / v:+.3f}; offense baseline {bo.mean() / v:+.3f}; defense baseline {bd.mean() / v:+.3f}"
        )
        print(f"   pairing's share {share(np.arange(len(real))):+.1%} (90% {lo:+.1%} to {hi:+.1%})")
        for a, z in ((2006, 2015), (2016, 2024)):
            w = np.flatnonzero((seasons >= a) & (seasons <= z))
            print(f"   {a}-{z}: share {share(w):+.1%}")


if __name__ == "__main__":
    main()
