"""The ledger's scorecard (prediction-ledger brief, goal 5; VALIDATION.md §9, live vs backtest gap).

Each model's counted forecasts are scored once their outcomes are known: the main score (range
score for shares, log loss for chances), the readable one (average miss of the median, or Brier),
and range coverage. Then they're set against the model's own backtest:

- **The interval.** A live average over n weeks is noisier than a 9-season average, so it's set
  against what n weeks of the backtest give. We draw n whole weeks at random (with replacement)
  from the backtest's same week numbers, 2016-2024, 2,000 times, and take the middle 90% of those
  n-week averages. Whole weeks, because rows in one week share their surprises (compare.py does the
  same).
- **The flag.** After at least 4 live weeks, a model whose live score is worse than that interval's
  worse end is flagged for review (§9). A replay is scored the same way but never flags: it's not
  a record.

The backtests are pinned in `BACKTESTS`, so a new experiment run never changes the yardstick.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.core import ledger
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.validation import scores
from pcf.validation.backtest import targets, test_seasons

c = pl.col
MIN_WEEKS = 4  # VALIDATION.md §9
DRAWS = 2000
LEVEL = 0.90
# Each ledger model's backtest: the --refit season runs after the Thursday move (decision 0016).
BACKTESTS = {
    "participation/trees_week": "2abc96bcab5047f5b7d505416f538b0f",
    "participation/active": "1a5406548afa4be181c2e88b9fa3b987",
    "participation/lasso_h3": "f0da29878af8420a9266b12159974a17",
    "participation/lasso_rest": "2de0578db3d7464db2607b0ded902481",
    "participation/last_game": "f4bd4f92864b40ebb83d5e979c174ae4",
}


def _expert(label: str):
    project, _, variant = label.partition("/")
    return find(project, variant or None)()


def _scored(rows: pl.DataFrame, label: str, gateway: Gateway) -> pl.DataFrame:
    """Rows with a known outcome, with `loss`, `readable`, `covered` and `week`."""
    e = _expert(label)
    y = targets(e, gateway).select(*e.keys(), "y")
    out = scores.row_losses(rows.join(y, on=e.keys(), how="inner"), e.kind)
    covered = (c("y") >= c("q10")) & (c("y") <= c("q90")) if e.kind == "amount" else pl.lit(None)
    return out.with_columns(
        covered=covered,
        season=c("game_id").str.slice(0, 4).cast(pl.Int32),
        week=c("game_id").str.slice(5, 2).cast(pl.Int32),
    )


def backtest_weeks(label: str, gateway: Gateway) -> pl.DataFrame:
    """The model's pinned backtest, 2016-2024, as one row per season and week: rows and summed
    loss."""
    e = _expert(label)
    path = get_config().zone("outputs") / e.id / e.variant / BACKTESTS[label] / "history.parquet"
    seasons = test_seasons()
    h = _scored(pl.read_parquet(path), label, gateway).filter(c("season").is_in(seasons))
    return h.group_by("season", "week").agg(rows=pl.len(), loss=c("loss").sum())


def interval(weeks: pl.DataFrame, live_weeks: list[int], seed: int) -> tuple[float, float]:
    """The middle 90% of the backtest's averages over as many weeks as were live, drawn as whole
    weeks from the same week numbers."""
    pool = weeks.filter(c("week").is_in(live_weeks))
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, pool.height, size=(DRAWS, len(live_weeks)))
    rows = pool["rows"].to_numpy()[pick].sum(axis=1)
    loss = pool["loss"].to_numpy()[pick].sum(axis=1)
    means = loss / rows
    tail = (1 - LEVEL) / 2
    return float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail))


def scorecard(record: str = "live", clone=None, gateway: Gateway | None = None) -> pl.DataFrame:
    """One row per model: live weeks and rows scored, the live and backtest scores, the backtest's
    interval for that many weeks, coverage, and the flag."""
    gateway = gateway or Gateway()
    rows = ledger.read(record, clone)
    if rows.is_empty():
        return pl.DataFrame()
    seed = get_config().seed
    out = []
    for (label,), part in rows.group_by("model", maintain_order=True):
        if label not in BACKTESTS:
            continue
        live = _scored(part, label, gateway)
        if live.is_empty():
            continue
        weeks = sorted(live["week"].unique().to_list())
        bt = backtest_weeks(label, gateway)
        same = bt.filter(c("week").is_in(weeks))
        lo, hi = interval(bt, weeks, seed)
        score = live["loss"].mean()
        out.append(
            {
                "model": label,
                "weeks": len(weeks),
                "rows": live.height,
                "score_x100": score * 100,
                "backtest_x100": same["loss"].sum() / same["rows"].sum() * 100,
                "interval_lo_x100": lo * 100,
                "interval_hi_x100": hi * 100,
                "readable_x100": live["readable"].mean() * 100,
                "coverage": live["covered"].mean() if live["covered"].dtype == pl.Boolean else None,
                "worse_than_interval": score > hi,
                "flag": record == "live" and len(weeks) >= MIN_WEEKS and score > hi,
            }
        )
    return pl.DataFrame(out)
