"""live-experts full trial (2026-11-10): a fresh pull, then every ledger model (`live.MODELS`) at the
Saturday noon moment of 2026 week 10, written to a throwaway local ledger folder (never pushed,
never `pcf-data`). It times the pull and each model, checks every model wrote rows for every due
game, that Elo's margin file keeps its ratings, and reads the folder back as the scorecard would.

A run at a future moment can't go through `live.run` itself: the ledger refuses rows written before
their `as_of`, and the live record waits for that day's injury file. So this calls the same steps
(`pull`, `forecast`, `Run.write`) with the write's clock set to the moment.

Run from pcf/: PYTHONUTF8=1 .venv/Scripts/python.exe projects/live-experts/explore/full_trial.py
"""

# ruff: noqa: E501
from __future__ import annotations

import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

from pcf.core import ledger
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.validation import live

ET = ZoneInfo("America/New_York")
AT = datetime(2026, 11, 14, 12, 5, tzinfo=ET).astimezone(UTC)


def main() -> None:
    t = time.perf_counter()
    pulled = live.pull(2026)
    print(f"pull: {time.perf_counter() - t:.0f}s, downloaded {pulled['downloaded']}", flush=True)
    g = Gateway()
    due = live.due_games(g, "saturday", AT)
    print(f"due at {AT}: {due.height} games", flush=True)
    folder = Path(tempfile.mkdtemp(prefix="live-experts-trial-"))
    run = ledger.open_run(2026, "trial", AT, "trial", pulled["pulled_at"], "live", folder)
    total = 0.0
    for pid, var in live.MODELS:
        e = find(pid, var)()
        t = time.perf_counter()
        f = live.forecast(e, g, AT, run.name)
        secs = time.perf_counter() - t
        total += secs
        if f is None:
            print(f"{e.label()}: NOTHING DUE", flush=True)
            continue
        info = run.write(e.label(), f.rows, e.keys(), e.kind, now=AT, publishes=e.publishes)
        flagged = f.checks.filter(pl.col("flag"))["input"].to_list()
        print(f"{e.label()}: {info['rows']} rows, {info['games']} games, {secs:.0f}s, flagged {flagged}", flush=True)
    print(f"all models: {total / 60:.1f} minutes", flush=True)
    run.close({"note": "full trial, not pushed"})
    rows = ledger.read("live", folder)
    print(rows.group_by("model").agg(rows=pl.len(), games=pl.col("game_id").n_unique()).sort("model"))
    margin = pl.read_parquet(run.folder / ledger.file_name("elo/margin"))
    print("elo/margin ratings kept:", [x for x in find("elo", "margin").publishes if x in margin.columns])
    with pl.Config(tbl_cols=10, float_precision=1):
        print(margin.select("game_id", "mean", "home_rating", "away_rating", "hfa", "h_qb", "a_qb").head(5))


if __name__ == "__main__":
    main()
