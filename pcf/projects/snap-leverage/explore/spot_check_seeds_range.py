"""snap-leverage spot-check, part 2 (the CEO's pick, 2026-11-14: "R2: the seeds"). The same checks as
spot_check_seeds.py, on the range score (the verdict's score) instead of squared error:
1. no early stopping (all 250 trees; no seed in the fit);
2. an interval with both kinds of luck: each draw picks a random seed and resamples weeks.
For leverage share (lev) and the full rung against plain. Needs commit 892d39c (the retired
variants; loaded as spot_check_seeds.py does). Writes spot_check_seeds_range.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/spot_check_seeds_range.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

from pcf.data.gateway import for_expert
from pcf.validation import backtest as B
from pcf.validation.scores import mean_pinball
from pcf.validation.splits import steps

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from spot_check_seeds import K, SEEDS, retired  # noqa: E402

c = pl.col
RUNGS = ("plain", "lev", "full")


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    M = retired()
    plain = M.VARIANTS["snap_next3_plain"]()
    gw = for_expert(plain)
    every = steps(gw.calendar, plain.cadence, range(2019, 2025), plain.run, None)
    test = [s.index for s in every if s.season >= 2020]
    feats = B.feature_history(plain, gw, every)
    y = B.targets(plain, gw)

    def scored(r: str) -> pl.DataFrame:
        p = B.walk(M.VARIANTS[f"snap_next3_{r}"](), feats, y, every, test, refit="season")
        return p.join(y.select(*K, "y"), on=K).with_columns(loss=mean_pinball()).select(*K, "as_of", "loss")

    def pct(a: pl.DataFrame, b: pl.DataFrame) -> float:
        j = a.join(b.select(*K, lb="loss"), on=K)
        return 100 * (j["lb"].sum() / j["loss"].sum() - 1)

    say("Snap share, next 3 games, scored 2020-2024; range score, % of plain's (+ = worse)")
    say("")
    say("1. No early stopping (all 250 trees; no seed in the fit at all):")
    M.TREES["early_stopping"] = False
    free = {r: scored(r) for r in RUNGS}
    del M.TREES["early_stopping"]
    for r in ("lev", "full"):
        say(f"   {r:4s} vs plain: {pct(free['plain'], free[r]):+.3f}%")

    runs = {}
    for seed in SEEDS:
        M.TREES["random_state"] = seed
        for r in RUNGS:
            runs[(r, seed)] = scored(r)
    M.TREES["random_state"] = 0
    say("")
    say("2. Per seed (a check against seeds.txt, which these should repeat):")
    for r in ("lev", "full"):
        say(f"   {r:4s}: " + ", ".join(f"{pct(runs[('plain', s)], runs[(r, s)]):+.3f}%" for s in SEEDS))

    say("")
    say("3. 90% interval resampling weeks and the seed together (4,000 draws):")
    for r in ("lev", "full"):
        wk = {}
        for s in SEEDS:
            j = runs[("plain", s)].join(runs[(r, s)].select(*K, lb="loss"), on=K)
            g = j.with_columns(wk=c("as_of").dt.strftime("%Y-%m-%d")).group_by("wk").agg(c("loss").sum(), c("lb").sum()).sort("wk")
            wk[s] = (g["loss"].to_numpy(), g["lb"].to_numpy())
        n = len(wk[SEEDS[0]][0])
        rng = np.random.default_rng(0)
        draws = []
        for _ in range(4000):
            a, b = wk[SEEDS[rng.integers(len(SEEDS))]]
            i = rng.integers(0, n, n)
            draws.append(100 * (b[i].sum() / a[i].sum() - 1))
        d = np.array(draws)
        lo, hi = np.percentile(d, [5, 95])
        say(f"   {r:4s} vs plain: {d.mean():+.3f}% (90% {lo:+.3f} to {hi:+.3f}); helps in {np.mean(d < 0):.1%} of draws")
    (HERE / "spot_check_seeds_range.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
