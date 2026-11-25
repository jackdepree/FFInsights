"""Games played for any reason (decision 0047 calls 18 and 21): the composite the brief names, his
rate of playing when healthy times the share of the window he isn't health-absent, and its range
from earlier seasons' misses.

    gp = hrate x (1 - E[health absences] / n)
    hrate = (games played this season + 4 x 0.9) / (games not health-absent this season + 4)

The health count's own range can't cover a benching, a scratch or a release (participation's), so
the range is the forecast plus the q10, q50 and q90 of earlier seasons' misses (outcome − gp) in
the same size of forecast: the conventional residual range, refit each season.

The fitted healthy rate (I129, decision 0047 call 27) replaces the shrunk rate where a fit is
possible: the share of his not-health-absent games he plays over the rest of the season, fit
walk-forward by season with a weighted logistic on his record (the shrunk rate's log-odds, his
last game's snap share, his season's snaps, age, games this season, whether he played last game,
position). It counts what the shrunk rate can't: releases, benchings and scratches ahead.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

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
    """Each scored season's ranges from the misses of the seasons before it (rows: season, gp,
    y)."""
    out = []
    for s in seasons:
        train = rows.filter((c("season") < s) & c("y").is_not_null())
        if train.height < MIN_ROWS:
            continue
        out.append(ranges(fit_ranges(train), rows.filter(c("season") == s)))
    return pl.concat(out) if out else rows.head(0)


# ---------------------------------------------------------------- I129: the fitted healthy rate
RECORD = ("lh", "ls", "lss", "ag", "gs", "lp", "p_RB", "p_WR", "p_TE")


def record(rows: pl.DataFrame) -> pl.DataFrame:
    """The fitted rate's inputs from the row's record (hrate, last_share, log_snaps_s, age,
    games_s, last_played, position), all known at the row's moment."""
    lh = np.log(np.clip(rows["hrate"].to_numpy(), 0.02, 0.98))
    lh = lh - np.log1p(-np.clip(rows["hrate"].to_numpy(), 0.02, 0.98))
    return rows.with_columns(
        lh=pl.Series(lh),
        ls=c("last_share").fill_null(0.0),
        lss=c("log_snaps_s").fill_null(0.0),
        ag=c("age").fill_null(26.0),
        gs=c("games_s").fill_null(0.0),
        lp=c("last_played").cast(pl.Float64).fill_null(0.0),
        **{f"p_{p}": (c("position") == p).cast(pl.Float64) for p in ("RB", "WR", "TE")},
    )


def healthy_share(rows: pl.DataFrame) -> pl.DataFrame:
    """The outcome the rate is fit to: of the window's `n` games, the share he played (`y`, the
    share of all n) among those he wasn't health-absent (`hy`), weighted by those games."""
    return rows.with_columns(healthy_n=(c("n") - c("hy")).clip(0)).with_columns(
        hshare=pl.when(c("healthy_n") > 0).then((c("y") * c("n") / c("healthy_n")).clip(0, 1))
    )


def fit_healthy(train: pl.DataFrame) -> LogisticRegression:
    """A weighted logistic of the healthy share on the record (rows with hshare, healthy_n)."""
    t = record(train).filter(c("hshare").is_not_null())
    x = t.select(RECORD).to_numpy().astype(float)
    h, w = t["hshare"].to_numpy(), t["healthy_n"].to_numpy().astype(float)
    m = LogisticRegression(C=1.0, max_iter=3000)
    return m.fit(np.vstack([x, x]), np.r_[np.ones(len(h)), np.zeros(len(h))],
                 sample_weight=np.r_[h * w, (1 - h) * w])  # fmt: skip


def walk_healthy(rows: pl.DataFrame, seasons: list[int]) -> pl.DataFrame:
    """Each season's fitted healthy rate (`hrate_fit`) and games played (`gp_fit`) from a fit on
    the seasons before it. `rows`: games_played's columns plus the record, `season`, and for the
    training seasons the outcome (`y`, the share of the window played), `hy` and `n`."""
    out = []
    shares = healthy_share(rows)
    for s in seasons:
        train = shares.filter((c("season") < s) & c("hshare").is_not_null())
        if train.height < MIN_ROWS:
            continue
        test = record(rows.filter(c("season") == s))
        p = fit_healthy(train).predict_proba(test.select(RECORD).to_numpy().astype(float))[:, 1]
        out.append(
            test.drop(RECORD)
            .with_columns(hrate_fit=pl.Series(p))
            .with_columns(gp_fit=c("hrate_fit") * (1 - c("ha_share")))
        )
    return pl.concat(out) if out else rows.head(0)
