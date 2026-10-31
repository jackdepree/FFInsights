"""Apply every known-at rule to its full dataset in the raw copy, and report what comes out.

Run from pcf/:  uv run python projects/timeline/explore/check_rules.py
"""

import sys
import time
from datetime import UTC, datetime

import polars as pl

from pcf.data.clean import standard
from pcf.data.sources.nflverse import DATASETS, scan
from pcf.data.timeline import RULES, calendar, known_at

# Big files: only the columns a rule reads.
COLUMNS = {
    "pbp": ["game_id", "season", "week"],
    "participation": ["nflverse_game_id"],
    "ftn_charting": ["nflverse_game_id", "season", "week"],
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cal = calendar(standard.schedules(scan("schedules").collect()))
    now = datetime.now(UTC)
    rows = []
    for name in sorted(DATASETS):
        t = time.time()
        lf = scan(name)
        if name in COLUMNS:
            lf = lf.select(COLUMNS[name])
        try:
            df = lf.collect()
            out = known_at(name, df, cal, fetched_at=now)
            rows.append(
                {
                    "dataset": name,
                    "rows": out.height,
                    "first": out["known_at"].min(),
                    "last": out["known_at"].max(),
                    "seconds": round(time.time() - t, 1),
                    "error": None,
                }
            )
        except Exception as e:  # noqa: BLE001 - report every failure, then move on
            rows.append({"dataset": name, "error": f"{type(e).__name__}: {e}"[:150]})
        print(rows[-1], flush=True)
    missing = sorted(set(DATASETS) - set(RULES))
    print("datasets with no rule:", missing)


if __name__ == "__main__":
    main()
