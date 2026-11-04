"""Is the lasso's penalty grid wide enough for shares? (2026-11-03)
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/penalty_grid.py

The grid came from `baselines`, whose outcome is fantasy points, on a scale of tens. A share runs 0-1,
so the same penalty bites harder, and a final fit chose the grid's smallest value at every position.
This reruns the lasso rungs with a grid 100 times lower and compares them with the saved runs, on
the same rows, and with the next-game trees.
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.experts.participation import horizons, twopart
from pcf.validation import backtest
from pcf.validation.compare import compare

sys.path.insert(0, str(Path(__file__).parent))
from compare_rungs import KEYS, history  # noqa: E402

c = pl.col
WIDER = np.geomspace(1.0, 1e-5, 26)
SEASONS = list(range(2016, 2025))


def main() -> None:
    gw = Gateway()
    twopart.ALPHAS = WIDER
    horizons.ALPHAS = WIDER
    for variant, rival in [("lasso", "trees"), ("lasso_h3", "trees_h3"), ("lasso_rest", "trees_rest")]:
        wide = backtest.run(find("participation", variant)(), gw, SEASONS, refit="season").scored
        wide = wide.with_columns(step=c("game_id").str.slice(0, 7))
        was = history(variant, gw)
        cmp = compare(wide, was, KEYS, "step", ("wider", "saved"))
        print(f"== {variant}: wider grid - saved, pinball x100 {cmp.diff * 100:+.3f} "
              f"({cmp.lo * 100:+.3f} to {cmp.hi * 100:+.3f}): {cmp.verdict}, {cmp.rows:,} rows")  # fmt: skip
        other = compare(history(rival, gw), wide, KEYS, "step", (rival, "wider"))
        print(f"   {rival} - wider lasso {other.diff * 100:+.3f} "
              f"({other.lo * 100:+.3f} to {other.hi * 100:+.3f}): {other.verdict}", flush=True)  # fmt: skip


if __name__ == "__main__":
    main()
