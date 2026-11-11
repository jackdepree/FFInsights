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

**Elo against the close** (live-experts brief, goal 3): `close_card` sets Elo's margin, total and
win chance beside the closing line on the same games, in the measure of Elo's own results
(elo#F2): the average miss in points for margins and totals, log loss for win chances. The close
is nflverse's (the `game` table), known only at kickoff, so it's scored here, not forecast.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.baselines.market import LINES, MarketMargin, no_vig_home
from pcf.config import get_config
from pcf.core import ledger
from pcf.core.contract import find
from pcf.data.gateway import END_OF_TIME, Gateway
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
    # live-experts (2026-11-10): Elo's final runs (elo RESULTS, 2026-11-07; margin and win after
    # the seed-locked flag) and schemes-v2's 2016-2024 runs of its finals (RESULTS R11) and of the
    # season-to-date yardsticks.
    "elo/margin": "21082e26cec94ea1920081554197d201",
    "elo/total": "417b504c3ce84c748d0b541e4de3fcc4",
    "elo/win": "b811be4301f54f1491bfce1ef29e06d5",
    "elo/wins_next3": "90d57816ef164d3395dd5221ed385e87",
    "elo/wins_rest": "4cad4574dece445aab2aa8a24ca2ca16",
    "schemes-v2/pass_oe_rung2": "113ae2db33d9420e94bff28115903c70",
    "schemes-v2/shotgun_rung2": "dfa8be869d8141c2804a0fd1bd8bdc30",
    "schemes-v2/depth_rung2": "b3fb56d819f942b5a78148aa42864347",
    "schemes-v2/tempo_shrunk": "88ffef17f0334deeb8612daf9c3fa093",
    "schemes-v2/pass_oe_season": "dd60066c72b84035b373b5e0390f7524",
    "schemes-v2/shotgun_season": "5d02ab2e4bf24c5e9c24281d9d80fea9",
    "schemes-v2/depth_season": "c5668b5ba84548f6bc3409cd60b0f43a",
    "schemes-v2/tempo_season": "1a254c4d28664558a50e50f4e4566b4e",
}
# Elo's game forecasts and the closing line each is set against (None: the no-vig moneylines).
CLOSE: dict[str, str | None] = {
    "elo/margin": "spread_line",
    "elo/total": "total_line",
    "elo/win": None,
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


def closing_lines(gateway: Gateway) -> pl.DataFrame:
    """Every game's closing spread, total and moneylines, as the market benchmarks read them."""
    m = MarketMargin()
    g = gateway.view(END_OF_TIME, m.cadence, m.inputs).table("game")
    return g.filter(c("pregame_known_at").is_not_null()).select("game_id", *LINES)


def against_close(scored: pl.DataFrame, label: str, lines: pl.DataFrame) -> dict | None:
    """One Elo model's scored rows beside the close on the same games: games, the measure, Elo's
    value, the close's, and how far Elo is behind (positive: the close was better)."""
    line = CLOSE[label]
    close = no_vig_home(c("home_moneyline"), c("away_moneyline")) if line is None else c(line)
    both = scored.join(
        lines.select("game_id", close=close.cast(pl.Float64)), on="game_id"
    ).drop_nulls("close")
    if both.is_empty():
        return None
    if line is None:
        measure = "log loss"
        ours = both.select(scores.log_loss()).to_series().mean()
        theirs = both.select(scores.log_loss(p="close")).to_series().mean()
    else:
        measure = "average miss, points"
        ours = both.select(scores.absolute_error()).to_series().mean()
        theirs = both.select(scores.absolute_error(q="close")).to_series().mean()
    return {
        "model": label,
        "games": both.height,
        "measure": measure,
        "elo": ours,
        "close": theirs,
        "behind_close": ours - theirs,
    }


def close_card(record: str = "live", clone=None, gateway: Gateway | None = None) -> pl.DataFrame:
    """One row per Elo game model with scored forecasts: Elo against the closing line."""
    gateway = gateway or Gateway()
    rows = ledger.read(record, clone)
    if rows.is_empty():
        return pl.DataFrame()
    lines = closing_lines(gateway)
    out = []
    for label in CLOSE:
        part = rows.filter(c("model") == label)
        if part.is_empty():
            continue
        scored = _scored(part, label, gateway)
        row = against_close(scored, label, lines) if scored.height else None
        if row:
            out.append(row)
    return pl.DataFrame(out)
