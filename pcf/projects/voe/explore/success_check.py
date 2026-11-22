# ruff: noqa: E501
"""voe, fourth look's check (2026-11-21, after the result, labelled as a check): the roster-change
test with a team's next-season success over expected as the target instead of EPA over expected,
so the target doesn't favour the EPA arm. Reads success_look.py's cached arms.

Run from pcf/:  python projects/voe/explore/success_check.py > projects/voe/explore/success_check.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402
import success_look as sl  # noqa: E402

c = pl.col


def main() -> None:
    p = sl.plays().filter(c("season").is_in(fl.SEASONS))
    ctx = sl.context()
    A = {name: sl.arm(p, name, ctx) for name in sl.ARMS}
    for target in ("r_success", "r_epa"):
        tr = fl.team_rates(p.with_columns(resid=c(target)))
        print(f"== Target: a team's next-season {'success' if target == 'r_success' else 'EPA'} over expected a play (pooled, 2020-2024)")
        for m in ("lasso", "sums"):
            se = {}
            for name in sl.ARMS:
                se[name] = sl.travel_se(tr, sl.roster(tr, A[name]["V"], m))
                g, lo, hi = sl.gain_ci(*se[name])
                print(f"  {m:>5} {name:>7}: {g:+.2f}% (90% {lo:+.2f} to {hi:+.2f})")
            a0, a1, ka = se["success"]
            b0, b1, _ = se["epa"]
            teams = np.unique(ka)
            idx = [np.flatnonzero(ka == k) for k in teams]
            bs = [100 * (b1[q].sum() - a1[q].sum()) / a0[q].sum() for q in (np.concatenate([idx[k] for k in sl.RNG.integers(0, len(teams), len(teams))]) for _ in range(2000))]
            print(f"  {m:>5} success less EPA: {100 * (b1.sum() - a1.sum()) / a0.sum():+.2f} points (90% {np.percentile(bs, 5):+.2f} to {np.percentile(bs, 95):+.2f})")


if __name__ == "__main__":
    main()
