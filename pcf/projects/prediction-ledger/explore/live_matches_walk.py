"""Does the live run forecast exactly what the backtest would (2026-11-07)? Week 9's Thursday game,
forecast by `pcf.validation.live.forecast` at its moment, against `backtest.walk` refitting at the
same step. Both fit at Thursday noon on the same rows, so they should match to the last digit.
Run from pcf/: .venv/Scripts/python.exe projects/prediction-ledger/explore/live_matches_walk.py

Nothing is scored or written: 2026 is live, and this only compares two forecasts.
"""

import sys
import time
from datetime import UTC, datetime

import polars as pl

from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.validation import backtest, live

c = pl.col
VARIANT = sys.argv[1] if len(sys.argv) > 1 else "trees_week"
NOW = datetime(2026, 11, 5, 17, 0, tzinfo=UTC)  # Thursday 12:00 Eastern


def main() -> None:
    e = find("participation", VARIANT)()
    gw = Gateway()
    print("due:", live.due_games(gw, e.run, NOW).to_dicts())
    t = time.perf_counter()
    f = live.forecast(e, gw, NOW, "check")
    print(f"live forecast: {f.rows.height} rows in {time.perf_counter() - t:.0f} s; {f.seconds}")
    print("input check flags:", f.checks.filter(c("flag"))["input"].to_list())
    with pl.Config(tbl_rows=40, tbl_width_chars=150):
        print(f.checks.head(8))
    so_far = live.steps_so_far(e, gw, NOW)
    feats = backtest.feature_history(e, gw, so_far)
    week = [s for s in so_far if s.season == 2026 and s.week == 9]
    pred = backtest.walk(e, feats, backtest.targets(e, gw), so_far, [week[0].index], "step")
    keys = e.keys()
    both = f.rows.join(pred, on=keys, suffix="_walk")
    diff = both.select(
        *[(c(q) - c(f"{q}_walk")).abs().max().alias(q) for q in ("mean", "q10", "q50", "q90")]
    )
    print(f"rows matched: {both.height} of {f.rows.height}; largest differences:")
    print(diff)
    print(
        "train_end:", f.rows["train_end"].unique().to_list(), pred["train_end"].unique().to_list()
    )


if __name__ == "__main__":
    main()
