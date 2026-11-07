"""The scorecard's interval: n whole weeks drawn from the backtest's same week numbers."""

import polars as pl

from pcf.validation.ledger_score import interval


def weeks(losses: dict[int, float], rows: int = 100) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2020] * len(losses),
            "week": list(losses),
            "rows": [rows] * len(losses),
            "loss": [v * rows for v in losses.values()],
        }
    )


def test_identical_weeks_give_a_point_interval():
    lo, hi = interval(weeks({1: 0.04, 2: 0.04, 3: 0.04}), [1, 2], seed=1)
    assert abs(lo - 0.04) < 1e-12 and abs(hi - 0.04) < 1e-12


def test_only_the_live_week_numbers_are_drawn():
    lo, hi = interval(weeks({1: 0.02, 2: 0.03, 17: 0.10}), [1, 2], seed=1)
    assert 0.02 <= lo <= hi <= 0.03


def test_more_weeks_give_a_narrower_interval():
    pool = pl.concat(
        weeks({w: 0.02 + 0.002 * ((w + s) % 5) for w in range(1, 19)}).with_columns(
            season=pl.lit(s)
        )
        for s in range(2016, 2025)
    )
    lo1, hi1 = interval(pool, [5], seed=1)
    lo8, hi8 = interval(pool, list(range(1, 9)), seed=1)
    assert hi8 - lo8 < hi1 - lo1
