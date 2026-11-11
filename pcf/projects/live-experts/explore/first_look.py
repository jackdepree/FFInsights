"""live-experts light exploration (2026-11-10): can Elo and the schemes-v2 trait forecasts go through
the ledger's live path (`pcf.validation.live.forecast`) for week 10, and how long does each take?

It forecasts at the Thursday and Saturday noon moments (Eastern) of 2026 week 10 with the data
already on this PC (no refresh), writes nothing and pushes nothing. Per model: rows, seconds
(features, fit and predict), the input check's flags, and the first rows.

Run from pcf/: PYTHONUTF8=1 .venv/Scripts/python.exe projects/live-experts/explore/first_look.py
"""

# ruff: noqa: E501
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import polars as pl

from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.validation import live

ET = ZoneInfo("America/New_York")
MODELS = [
    ("elo", "margin"),
    ("elo", "total"),
    ("elo", "win"),
    ("elo", "wins_next3"),
    ("elo", "wins_rest"),
    ("schemes-v2", "pass_oe_rung2"),
    ("schemes-v2", "shotgun_rung2"),
    ("schemes-v2", "depth_rung2"),
    ("schemes-v2", "tempo_shrunk"),
]
MOMENTS = (datetime(2026, 11, 12, 12, 5, tzinfo=ET), datetime(2026, 11, 14, 12, 5, tzinfo=ET))


def main() -> None:
    for local in MOMENTS:
        at = local.astimezone(UTC)
        print(f"\n===== now = {local}", flush=True)
        g = Gateway()
        for pid, var in MODELS:
            e = find(pid, var)()
            t = time.perf_counter()
            try:
                f = live.forecast(e, g, at, "trial")
            except Exception as err:  # report and carry on, as the live run does
                print(f"{pid}/{var}: FAILED {err!r}", flush=True)
                continue
            dt = time.perf_counter() - t
            if f is None:
                print(f"{pid}/{var}: nothing due ({dt:.0f}s)", flush=True)
                continue
            flagged = f.checks.filter(pl.col("flag"))["input"].to_list()
            secs = json.dumps({k: round(v, 1) for k, v in f.seconds.items()})
            print(f"{pid}/{var}: {f.rows.height} rows, {dt:.0f}s {secs} keys={e.keys()} kind={e.kind} flagged={flagged}", flush=True)
            with pl.Config(tbl_cols=12, tbl_width_chars=220, float_precision=2, tbl_rows=4):
                print(f.rows.head(4), flush=True)
    spread_check()


def spread_check() -> None:
    """Football sanity: Elo's margin against nflverse's current spread (home-positive) for week 10."""
    from pcf.data.sources.nflverse import scan

    g = Gateway()
    elo = pl.concat(
        live.forecast(find("elo", "margin")(), g, m.astimezone(UTC), "trial").rows.select("game_id", elo="mean")
        for m in MOMENTS
    )
    s = scan("schedules", None).filter(pl.col("game_id").is_in(elo["game_id"].implode())).select("game_id", "spread_line").collect()
    x = elo.join(s, on="game_id").drop_nulls()
    print(f"\nElo margin against the spread: {x.height} games, r {x.select(pl.corr('elo', 'spread_line')).item():.2f}, average gap {(x['elo'] - x['spread_line']).abs().mean():.1f} points")


if __name__ == "__main__":
    main()
