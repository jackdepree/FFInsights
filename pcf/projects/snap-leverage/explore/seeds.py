"""snap-leverage build (2026-11-14): does the no-noise verdict survive the trees' random seed?

The trees stop early on a random tenth of each training window (scikit-learn's default above
10,000 rows), so one seed is one draw. The build's own walk-forward (the harness's features,
targets and `walk`, refit each season, 2020-2024) for `snap_next3_plain`, `_lev` and `_full` with
five seeds; each seed's paired difference (range score and squared error, % of plain's; + = worse)
and the spread across seeds. Writes seeds.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/seeds.py
It needs the retired expert package, `pcf.experts.snap_leverage` (decision 0034): check out
commit 892d39c to rerun it.
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.data.gateway import for_expert
from pcf.experts.snap_leverage import model as M
from pcf.validation import backtest as B
from pcf.validation.scores import mean_pinball
from pcf.validation.splits import steps

c = pl.col
HERE = Path(__file__).parent
SEEDS = (0, 1, 2, 3, 4)
K = ["gsis_id", "game_id"]


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    plain = M.VARIANTS["snap_next3_plain"]()
    gw = for_expert(plain)
    every = steps(gw.calendar, plain.cadence, range(2019, 2025), plain.run, None)
    test = [s.index for s in every if s.season >= 2020]
    feats = B.feature_history(plain, gw, every)  # every rung's features, one pass
    y = B.targets(plain, gw)
    say(f"snap share, next 3 games, 2020-2024: {feats.height:,} feature rows")
    say("seed | lev vs plain: range, squared error | full vs plain: range, squared error")
    res = {"lev": [], "full": []}
    for seed in SEEDS:
        M.TREES["random_state"] = seed
        scored = {}
        for r in ("plain", "lev", "full"):
            e = M.VARIANTS[f"snap_next3_{r}"]()
            p = B.walk(e, feats, y, every, test, refit="season")
            scored[r] = p.join(y.select(*K, "y"), on=K).with_columns(
                loss=mean_pinball(), se=(c("y") - c("mean")) ** 2
            )
        row = [f"{seed:4d}"]
        for r in ("lev", "full"):
            j = scored["plain"].select(*K, "loss", "se").join(
                scored[r].select(*K, lb="loss", sb="se"), on=K
            )
            rs = 100 * (j["lb"].sum() / j["loss"].sum() - 1)
            ss = 100 * (j["sb"].sum() / j["se"].sum() - 1)
            res[r].append((rs, ss))
            row.append(f"{rs:+.3f}%, {ss:+.3f}%")
        say(" | ".join(row))
    for r in ("lev", "full"):
        a = np.array(res[r])
        say(f"{r} vs plain over {len(SEEDS)} seeds: range {a[:, 0].mean():+.3f}% "
            f"(from {a[:, 0].min():+.3f} to {a[:, 0].max():+.3f}); squared error "
            f"{a[:, 1].mean():+.3f}% (from {a[:, 1].min():+.3f} to {a[:, 1].max():+.3f})")  # fmt: skip
    (HERE / "seeds.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
