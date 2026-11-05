"""Is the third part right for QBs (2026-11-04)? `trees_spikes` adds the chance of every snap,
which moved QBs' range coverage from 75.7% to 88.5% and put only 12.0% of results above q50. Are
those new misses, or the same arithmetic as the spike at 0 (F13), now at the top?
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/qb_every_snap.py

Scored on QB games they played: is the chance of every snap calibrated, does the range hold 80% on
games that were neither 0 nor every snap, and what would coverage be if each forecast were exactly
true (results drawn from each row's own forecast, as in coverage_deep_dive.py)?
"""

import numpy as np
import polars as pl

from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.experts.participation.twopart import BINS, FULL, LEVELS, TreesSpikes
from pcf.validation import backtest, calibration

c = pl.col
KEYS = ["gsis_id", "game_id"]
SEASONS = list(range(2016, 2025))
RNG = 20261104
DRAWS = 40


class Capture(TreesSpikes):
    rows: list[pl.DataFrame] = []
    grids: list[np.ndarray] = []

    def predict(self, model, rows):
        g = rows.filter(c("position") == "QB")
        if g.height and "QB" in model["parts"]:
            x = g.select(self.columns).to_numpy().astype(float)
            _, full, share = model["parts"]["QB"]
            s = self.predict_share(share, x).clip(0, 1)
            t = full.predict_proba(x)[:, 1]
            listed = self._listed(x)
            grid = model["grid"]["QB"][listed, np.digitize(s, BINS)]
            self.rows.append(g.select(*KEYS, "depth1").with_columns(t=pl.Series(t), s=pl.Series(s)))
            self.grids.append(grid)
        return super().predict(model, rows)


def main() -> None:
    bt = backtest.run(Capture(), Gateway(), SEASONS, refit="season")
    d = pl.concat(Capture.rows).with_row_index("i")
    grid = np.vstack(Capture.grids)
    d = d.join(bt.scored, on=KEYS)
    g = grid[d["i"].to_numpy()]
    d = d.with_columns(
        rest10=pl.Series((d["s"].to_numpy() + g[:, 9]).clip(0, 1)),
        rest90=pl.Series((d["s"].to_numpy() + g[:, 89]).clip(0, 1)),
    )
    keep = (d["y"] > 0).to_numpy()
    on, go = d.filter(c("y") > 0), g[keep]

    every = on.select(y=(c("y") >= FULL).cast(pl.Float64), mean="t")
    r = calibration.probability_report(every)
    print(
        f"QB games played: {on.height:,}; every snap in {every['y'].mean():.1%}, said {every['mean'].mean():.1%}"
    )
    print(
        f"Chance of every snap: error {r['error']:.2f} points, slope {r['slope']:.3f}, passed {r['passed']}"
    )
    with pl.Config(float_precision=3, tbl_rows=12):
        print(r["table"])

    rest = on.filter(c("y") < FULL)
    print(f"Games neither 0 nor every snap: {rest.height:,}; range holds "
          f"{rest.select(((c('y') >= c('rest10')) & (c('y') <= c('rest90'))).mean()).item():.1%}, "
          f"{rest.select((c('y') < c('rest10')).mean()).item():.1%} below, "
          f"{rest.select((c('y') > c('rest90')).mean()).item():.1%} above")  # fmt: skip

    # If each forecast were exactly true
    rng = np.random.default_rng(RNG)
    t, s = on["t"].to_numpy(), on["s"].to_numpy()
    q10, q50, q90 = (on[f"if_nonzero_{q}"].to_numpy() for q in ("q10", "q50", "q90"))
    inside, above = [], []
    for _ in range(DRAWS):
        u = rng.random(len(t))
        every_snap = u >= 1 - t
        v = np.clip(u / np.maximum(1 - t, 1e-6), 0, 1)
        at = np.clip((v - LEVELS[0]) / (LEVELS[1] - LEVELS[0]), 0, len(LEVELS) - 1)
        lo = at.astype(int)
        hi = np.minimum(lo + 1, len(LEVELS) - 1)
        i = np.arange(len(t))
        y = (s + go[i, lo] + (at - lo) * (go[i, hi] - go[i, lo])).clip(0, 1)
        y[every_snap] = 1.0
        inside.append(((y >= q10) & (y <= q90)).mean())
        above.append((y > q50).mean())
    y = on["y"].to_numpy()
    print(f"\nRange, QB games played: actual {((y >= q10) & (y <= q90)).mean():.1%}; "
          f"if exactly true {np.mean(inside):.1%}")  # fmt: skip
    print(f"Above q50: actual {(y > q50).mean():.1%}; if exactly true {np.mean(above):.1%}")
    free = on.filter(c("if_nonzero_q50") < FULL)
    print(f"Where q50 is below 100% ({free.height:,} of {on.height:,}): "
          f"{free.select((c('y') > c('if_nonzero_q50')).mean()).item():.1%} above q50")  # fmt: skip

    names = load("player_game", parts=["injury"], seasons=[2024]).select(*KEYS, "full_name", "week")
    show = d.join(names, on=KEYS).filter(c("full_name") == "Josh Allen").sort("week")
    print("\nOne starter's 2024")
    for x in show.iter_rows(named=True):
        print(f"  wk {x['week']:>2} chance of 0 {1 - x['p_nonzero']:>4.0%}  every snap {x['t']:>4.0%}  "
              f"otherwise {x['s']:>4.0%}  range {x['if_nonzero_q10']:>4.0%} to {x['if_nonzero_q90']:>4.0%}  "
              f"result {x['y']:>4.0%}")  # fmt: skip


if __name__ == "__main__":
    main()
