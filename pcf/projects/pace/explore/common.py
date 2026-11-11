"""Shared loaders for the pace exploration (2026-11-10)."""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
NEUTRAL = (0.2, 0.8)


def plays() -> pl.DataFrame:
    from pcf.data.clean import standard

    p = pl.read_parquet(get_config().zone("interim") / "pace" / "plays.parquet")
    p = standard.standard_teams(p, "home_team")
    return p.with_columns(
        team=c("posteam"),
        neutral=(
            c("wp").is_between(*NEUTRAL)
            & c("down").is_between(1, 3)
            & (c("half_seconds_remaining") > 120)
            & (c("qtr") <= 4)
        ).fill_null(False),
        pass_oe=(c("pass") - c("xpass")),
    )


def ols(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    X1 = np.column_stack([np.ones(len(y)), X])
    return np.linalg.lstsq(X1, y, rcond=None)[0]


def r2(y: np.ndarray, X: np.ndarray) -> float:
    X1 = np.column_stack([np.ones(len(y)), X])
    b = np.linalg.lstsq(X1, y, rcond=None)[0]
    res = y - X1 @ b
    return 1 - res.var() / y.var()


def boot(df: pl.DataFrame, fn, by: str = "season", n: int = 200, seed: int = 7) -> tuple[float, float, float]:
    """fn(df) -> float, with a 90% interval from resampling whole `by` blocks (team-seasons or
    weeks)."""
    est = fn(df)
    keys = df[by].unique().to_list()
    rng = np.random.default_rng(seed)
    parts = df.partition_by(by, as_dict=True)
    parts = {k[0] if isinstance(k, tuple) else k: v for k, v in parts.items()}
    vals = []
    for _ in range(n):
        pick = rng.choice(keys, size=len(keys), replace=True)
        vals.append(fn(pl.concat([parts[k] for k in pick])))
    lo, hi = np.nanpercentile(vals, [5, 95])
    return est, lo, hi


def prior_mean(df: pl.DataFrame, col: str, by=("team", "season"), order="week", n: int | None = None, name: str | None = None) -> pl.DataFrame:
    """Season-to-date (or last-n) mean of `col` over games before this one."""
    if name is None:
        name = f"{col}_prior" if n is None else f"{col}_last{n}"
    s = df.sort(*by, order)
    if n is None:
        expr = c(col).shift(1).cum_sum().over(by) / c(col).shift(1).cum_count().over(by)
    else:
        expr = c(col).shift(1).rolling_mean(n, min_samples=1).over(by)
    return s.with_columns(expr.alias(name))
