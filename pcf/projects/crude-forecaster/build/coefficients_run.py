# ruff: noqa: E501
"""crude-forecaster: the lasso's coefficients, readable (the CEO, 2026-11-19: "You can look at the
coefficients"). For each target, next game: the champion lasso with every finished expert added,
fit on 2016-2024 as a 2025 forecast would be, each input in yards per unit with a 90% interval
from 200 refits on resampled weeks, and how often the refits kept it. `yardstick.coefficients`
does the work.

Run from pcf/ (PCF_DATA_DIR set):
    python projects/crude-forecaster/build/coefficients_run.py > projects/crude-forecaster/build/coefficients.txt
"""

from __future__ import annotations

import polars as pl

from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config

OUT = get_config().zone("outputs") / "crude-forecaster" / "coefficients"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("crude-forecaster: the lasso's coefficients, next game, every finished expert added; fit on 2016-2024 (recency-weighted, half-life 4 seasons).")
    print("per unit = yards per one unit of the input, other inputs held; per sd = yards per one standard deviation (comparable across inputs).")
    print("90% interval from 200 refits on whole weeks resampled, penalty held. Not t-tests or p-values: the lasso chose and shrank these inputs on the same rows.")
    for target in ("passing", "rushing", "receiving", "team"):
        board = Y.load_board(target, "next")
        added = tuple(board.base.expert_groups())
        t = Y.coefficients(board, added=added, draws=200)
        t.write_parquet(OUT / f"{target}_next.parquet")
        print(f"\n== {target} next game (penalty {t['alpha'][0]:.4f}, {t['rows'][0]} rows)")
        print(f"  {'input':<20}{'group':<15}{'per sd':>9}{'per unit':>11}   {'90% interval':<22}{'kept':>6}")
        for r in t.filter(pl.col("per_sd") != 0).iter_rows(named=True):
            print(f"  {r['input']:<20}{r['group']:<15}{r['per_sd']:>9.2f}{r['per_unit']:>11.3f}   {r['lo']:>9.3f} to {r['hi']:<9.3f}{100 * r['kept']:>5.0f}%")
        zero = t.filter(pl.col("per_sd") == 0)["input"].to_list()
        print(f"  set to zero: {', '.join(zero) if zero else 'none'}")


if __name__ == "__main__":
    main()
