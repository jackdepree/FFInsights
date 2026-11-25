"""Games played for any reason (decision 0047 calls 18 and 21): the composite the brief names, his
rate of playing when healthy times the share of the window he isn't health-absent, and its range
from earlier seasons' misses.

    gp = hrate x (1 - E[health absences] / n)
    hrate = (games played this season + 4 x 0.9) / (games not health-absent this season + 4)

The health count's own range can't cover a benching, a scratch or a release (participation's), so
the range is the forecast plus the q10, q50 and q90 of earlier seasons' misses (outcome − gp) in
the same size of forecast: the conventional residual range, refit each season.
"""

from __future__ import annotations

import numpy as np
import polars as pl

c = pl.col
PRIOR, WEIGHT = 0.9, 4.0
EDGES = np.array([0.5, 0.7, 0.8, 0.9])
MIN_ROWS = 200


def healthy_rate() -> pl.Expr:
    """His rate of playing when not health-absent, this season so far, shrunk to 0.9 by 4 games."""
    denom = (c("games_s") - c("absent_s")).clip(0) + WEIGHT
    return ((c("played_s") + WEIGHT * PRIOR) / denom).clip(0.0, 1.0)


def games_played(rows: pl.DataFrame) -> pl.DataFrame:
    """`rows`: a window forecast's history (mean, the expected games of health absence, and
    n_window) with the record's played_s, games_s, absent_s. Adds hrate, ha_share and gp, the share
    of the window's games he plays for any reason."""
    return rows.with_columns(hrate=healthy_rate(), ha_share=c("mean") / c("n_window")).with_columns(
        gp=c("hrate") * (1 - c("ha_share"))
    )


def _bin(gp: np.ndarray) -> np.ndarray:
    return np.digitize(gp, EDGES)


def fit_ranges(train: pl.DataFrame) -> dict[int, np.ndarray]:
    """The q10, q50 and q90 of the misses (`y` − `gp`) per size of forecast; bins with under 200
    rows use every row's."""
    e = (train["y"] - train["gp"]).to_numpy()
    b = _bin(train["gp"].to_numpy())
    every = np.quantile(e, [0.1, 0.5, 0.9])
    return {k: (np.quantile(e[b == k], [0.1, 0.5, 0.9]) if (b == k).sum() >= MIN_ROWS else every)
            for k in range(len(EDGES) + 1)}  # fmt: skip


def ranges(model: dict[int, np.ndarray], rows: pl.DataFrame) -> pl.DataFrame:
    """gp10, gp50, gp90 for `rows` (with gp), clipped to 0..1."""
    gp = rows["gp"].to_numpy()
    q = np.stack([model[k] for k in _bin(gp)]) if len(gp) else np.zeros((0, 3))
    return rows.with_columns(
        **{f"gp{n}": pl.Series(np.clip(gp + q[:, i], 0.0, 1.0)) for i, n in enumerate((10, 50, 90))}
    )


def walk_ranges(rows: pl.DataFrame, seasons: list[int]) -> pl.DataFrame:
    """Each scored season's ranges from the misses of the seasons before it (rows: season, gp, y)."""
    out = []
    for s in seasons:
        train = rows.filter((c("season") < s) & c("y").is_not_null())
        if train.height < MIN_ROWS:
            continue
        out.append(ranges(fit_ranges(train), rows.filter(c("season") == s)))
    return pl.concat(out) if out else rows.head(0)
