"""Robustness for F24 (route C), run after seeing its result, so it is reported as such.

1. Every (k, λ) on 2015-2024: is the test result specific to the chosen setting?
2. The chosen setting season by season, both eras.
3. Where the shuffled null centers in each era (20 shuffles), to see whether 2006-2014's
   slightly negative values are just the null level.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/latent_check.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
from latent import GRID, RNG, collect, r
from rematch import load


def main() -> None:
    s = load()
    test = range(2015, 2025)
    miss, parts, _ = collect(s, test, GRID, RNG)
    print("== 1. Every setting on 2015-2024")
    for cfg in GRID:
        print(f"   k {cfg[0]}, λ {cfg[1]:>4}: r {r(parts[cfg], miss):+.4f}")
    best = (2, 1)
    print("\n== 2. The chosen setting (k 2, λ 1), season by season")
    for yr in range(2006, 2025):
        m, p, _ = collect(s, [yr], [best], RNG)
        print(f"   {yr}: r {r(p[best], m):+.3f}")
    print("\n== 3. The shuffled null's centre (20 shuffles each)")
    for label, yrs in (("2006-2014", range(2006, 2015)), ("2015-2024", test)):
        real_m, real_p, _ = collect(s, yrs, [best], RNG)
        nl = [
            r(p0[best], m0)
            for m0, p0, _ in (collect(s, yrs, [best], RNG, shuffle=True) for _ in range(20))
        ]
        print(
            f"   {label}: real r {r(real_p[best], real_m):+.4f}; null mean {np.mean(nl):+.4f}, sd {np.std(nl):.4f}"
        )


if __name__ == "__main__":
    main()
