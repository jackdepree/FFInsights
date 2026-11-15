"""The `play` part `leverage` (snap-leverage project, decision 0033): how much the win chance can
swing on each snap, from the situation before it alone (the CEO's "variance of winning percent
added per play based on conditions/situations").

- **The model:** gradient-boosted trees of WPA² on the situation (`X`: quarter, clock, score
  margin, down, distance, field position, both teams' timeouts, the win chance going in), fit on
  the regular-season snaps of up to `pace.TRAIN_SEASONS` seasons before (never fewer than
  `pace.MIN_TRAIN_SEASONS`), never the season itself. The exploration's version (snap-leverage
  F1) correlated 0.54-0.58 with the actual swing in every held-out season.
- **`wpa_sd`:** its square root, the spread of WPA a snap like this allows (win-chance units).
- **`leverage`:** `wpa_sd` over its mean on the training snaps, so 1.0 is an average snap.
- **`high_stakes`:** leverage at or above the training snaps' 80th percentile, fixed from the
  training seasons (the exploration cut each season at its own, which looks ahead in-season).

Snaps are runs, passes, kneels and spikes with a win chance, every season type; two-point tries
are left out. nflverse's WPA is in-sample before 2020 (tag-tables#F4). The builders are pure:
rows in, rows out; the build step caches each season's fit.
"""

from __future__ import annotations

import pickle
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from pcf.data.tables.pace import training_seasons

c = pl.col
PBP_COLUMNS = [
    "game_id", "play_id", "season", "season_type", "play_type", "two_point_attempt", "qtr",
    "game_seconds_remaining", "half_seconds_remaining", "score_differential", "down", "ydstogo",
    "yardline_100", "posteam_timeouts_remaining", "defteam_timeouts_remaining", "wp", "wpa",
]  # fmt: skip
X = [
    "qtr", "game_seconds_remaining", "half_seconds_remaining", "score_differential", "down",
    "ydstogo", "yardline_100", "posteam_timeouts_remaining", "defteam_timeouts_remaining", "wp",
]  # fmt: skip
SNAP_TYPES = ("pass", "run", "qb_kneel", "qb_spike")
HIGH_STAKES = 0.8  # the top fifth of the training snaps
TREES = {"max_iter": 300, "learning_rate": 0.08, "max_leaf_nodes": 63, "min_samples_leaf": 200,
         "random_state": 0}  # fmt: skip
MODEL_VERSION = 1  # bump when the snaps, the inputs or the fit settings change
CACHE_FILE = "leverage.pkl"


def snap_rows(pbp: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play (`PBP_COLUMNS`) → the snaps leverage is computed on, with `X` as floats and a
    `regular` flag (the fit uses regular-season snaps with a WPA)."""
    return (
        pbp.filter(
            c("play_type").is_in(SNAP_TYPES)
            & (c("two_point_attempt").fill_null(0) == 0)
            & c("wp").is_not_null()
            & c("wp").is_not_nan()
        )
        .with_columns(c("down").fill_null(0), regular=c("season_type") == "REG")
        .with_columns(c(X).cast(pl.Float64), c("play_id").cast(pl.Int64))
    )


def fit(snaps: pl.DataFrame, seasons: list[int]) -> dict[str, Any]:
    """The model, its training mean spread and its high-stakes cut, from the training seasons'
    regular-season snaps with a WPA."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    t = snaps.filter(c("regular") & c("wpa").is_not_null() & c("wpa").is_not_nan())
    x = t.select(X).to_numpy()
    model = HistGradientBoostingRegressor(**TREES).fit(x, (t["wpa"] ** 2).to_numpy())
    sd = np.sqrt(np.clip(model.predict(x), 1e-8, None))
    base = float(sd.mean())
    return {"model": model, "base": base, "cut": float(np.quantile(sd / base, HIGH_STAKES)),
            "seasons": list(seasons)}  # fmt: skip


def check_fit(fitted: dict[str, Any], season: int) -> None:
    """A fit was made only on seasons before `season` (the vintage rule) and is usable."""
    late = [s for s in fitted["seasons"] if s >= season]
    if late:
        raise ValueError(f"leverage for {season} was fit on {late}")
    if not (np.isfinite(fitted["base"]) and fitted["base"] > 0 and fitted["cut"] > 0):
        raise ValueError(f"leverage for {season}: a bad fit (base {fitted['base']})")


def apply(snaps: pl.DataFrame, fitted: dict[str, Any]) -> pl.DataFrame:
    """Snaps → the part: game_id, play_id, season, wpa_sd, leverage, high_stakes."""
    sd = np.sqrt(np.clip(fitted["model"].predict(snaps.select(X).to_numpy()), 1e-8, None))
    li = sd / fitted["base"]
    return (
        snaps.select("game_id", "play_id", c("season").cast(pl.Int32))
        .with_columns(
            wpa_sd=pl.Series(sd), leverage=pl.Series(li), high_stakes=pl.Series(li >= fitted["cut"])
        )
        .sort("game_id", "play_id")
    )


def cache_key(season: int, train: list[int]) -> str:
    return f"v{MODEL_VERSION}:{season}:{','.join(map(str, train))}"


def fitted_for(
    season: int, have: list[int], snaps_of: Callable[[int], pl.DataFrame], cache_dir: Path
) -> dict[str, Any] | None:
    """The fit for `season`, from `cache_dir/season=<season>` or fit on the training seasons'
    snaps (`snaps_of(season)`) and cached. None when too few earlier seasons exist."""
    train = training_seasons(season, have)
    if not train:
        return None
    key = cache_key(season, train)
    path = cache_dir / f"season={season}" / CACHE_FILE
    if path.exists():
        with path.open("rb") as f:
            cached = pickle.load(f)  # PCF's own interim files
        if cached.get("key") == key:
            check_fit(cached["fitted"], season)
            return cached["fitted"]
    fitted = fit(pl.concat([snaps_of(s) for s in train], how="diagonal_relaxed"), train)
    check_fit(fitted, season)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump({"key": key, "fitted": fitted}, f)
    tmp.replace(path)
    return fitted
