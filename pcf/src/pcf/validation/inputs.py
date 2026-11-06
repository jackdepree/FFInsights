"""The input check: does a run's data look like the data its model was validated on?

The leakage checks catch data seen too early. They can't catch data that never arrives: from 2025
every injury report was hidden from the Saturday run, and nothing failed, because a model just
treats a missing report as a healthy player (prediction-ledger#F1, #F3). This compares each input's
fill rates with the same weeks of a backtest. The bars are in docs/VALIDATION.md, section 9. A flag
means look, not stop.
"""

import polars as pl

c = pl.col

# Flag an input whose share of non-zero or missing rows moves by more than this many points.
GAP_POINTS = 5.0
# Fewer live rows than this and a gap can be chance (one Thursday game is about 30).
MIN_ROWS = 200
# An input that has gone entirely quiet is flagged at any size, if the backtest's rate would have
# filled at least this many of the live rows.
MIN_EXPECTED = 5

SCHEMA = {
    "input": pl.String,
    "used_backtest": pl.Float64,
    "used_live": pl.Float64,
    "missing_backtest": pl.Float64,
    "missing_live": pl.Float64,
    "gap": pl.Float64,
    "flag": pl.Boolean,
}


def _rates(values: pl.Series) -> tuple[float, float]:
    """Points of rows that are non-zero, and points that are missing."""
    values = values.cast(pl.Float64)
    filled = values.fill_null(0.0).fill_nan(0.0)
    return float((filled != 0).mean() or 0.0) * 100, float(values.is_null().mean() or 0.0) * 100


def input_check(backtest: pl.DataFrame, live: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    """One row per numeric input, largest gap first. `flag` is true where an input looks different
    from the backtest. Text inputs are skipped. Either side having no rows gives an empty result."""
    rows = []
    if backtest.is_empty() or live.is_empty():
        return pl.DataFrame(schema=SCHEMA)
    for col in columns:
        if not (backtest.schema[col].is_numeric() or backtest.schema[col] == pl.Boolean):
            continue
        used_b, missing_b = _rates(backtest[col])
        used_l, missing_l = _rates(live[col])
        gap = max(abs(used_b - used_l), abs(missing_b - missing_l))
        quiet = used_l == 0 and used_b / 100 * live.height >= MIN_EXPECTED
        rows.append(
            {
                "input": col,
                "used_backtest": used_b,
                "used_live": used_l,
                "missing_backtest": missing_b,
                "missing_live": missing_l,
                "gap": gap,
                "flag": quiet or (gap > GAP_POINTS and live.height >= MIN_ROWS),
            }
        )
    return pl.DataFrame(rows, schema=SCHEMA).sort("gap", descending=True)
