"""`play.leverage`: how much the win chance can swing on a snap, fit on earlier seasons only."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from pcf.data.tables import leverage


def _pbp(season: int, n: int = 4000, seed: int = 0) -> pl.DataFrame:
    """Synthetic snaps whose WPA spread grows late in close games."""
    rng = np.random.default_rng(seed + season)
    qtr = rng.integers(1, 5, n)
    margin = rng.integers(-21, 22, n)
    close = (np.abs(margin) <= 8) & (qtr == 4)
    wpa = rng.normal(0, np.where(close, 0.08, 0.02))
    return pl.DataFrame(
        {
            "game_id": [f"{season}_{i // 150:02d}_A_B" for i in range(n)],
            "play_id": np.arange(n) % 150 + 1,
            "season": season,
            "season_type": "REG",
            "play_type": rng.choice(
                ["pass", "run", "qb_kneel", "field_goal"], n, p=[0.5, 0.4, 0.02, 0.08]
            ),
            "two_point_attempt": (rng.random(n) < 0.01).astype(int),
            "qtr": qtr,
            "game_seconds_remaining": (4 - qtr) * 900 + rng.integers(0, 900, n),
            "half_seconds_remaining": rng.integers(0, 1800, n),
            "score_differential": margin,
            "down": rng.integers(1, 5, n),
            "ydstogo": rng.integers(1, 15, n),
            "yardline_100": rng.integers(1, 99, n),
            "posteam_timeouts_remaining": rng.integers(0, 4, n),
            "defteam_timeouts_remaining": rng.integers(0, 4, n),
            "wp": np.clip(0.5 + margin / 50, 0.01, 0.99),
            "wpa": wpa,
        }
    )


def _snaps(season: int) -> pl.DataFrame:
    return leverage.snap_rows(_pbp(season))


def test_snaps_keep_scrimmage_plays_without_two_point_tries():
    s = _snaps(2020)
    assert set(s["play_type"].unique()) <= set(leverage.SNAP_TYPES)
    assert (s["two_point_attempt"] == 0).all()


def test_leverage_is_relative_to_the_training_snaps_and_finds_late_close_plays():
    train = [2017, 2018, 2019]
    fitted = leverage.fit(pl.concat([_snaps(s) for s in train]), train)
    own = leverage.apply(pl.concat([_snaps(s) for s in train]), fitted)
    assert own["leverage"].mean() == pytest.approx(1.0, abs=1e-6)
    assert own["high_stakes"].mean() == pytest.approx(0.2, abs=0.02)
    new = _snaps(2020)
    out = leverage.apply(new, fitted).join(
        new.select("game_id", "play_id", "qtr", "score_differential"), on=["game_id", "play_id"]
    )
    late = out.filter((pl.col("qtr") == 4) & (pl.col("score_differential").abs() <= 8))
    rest = out.filter(~((pl.col("qtr") == 4) & (pl.col("score_differential").abs() <= 8)))
    assert late["leverage"].mean() > 2 * rest["leverage"].mean()
    assert late["high_stakes"].mean() > 0.8
    assert set(leverage.apply(new, fitted).columns) == {
        "game_id",
        "play_id",
        "season",
        "wpa_sd",
        "leverage",
        "high_stakes",
    }


def test_a_fit_on_its_own_season_is_refused():
    fitted = leverage.fit(pl.concat([_snaps(s) for s in (2018, 2019, 2020)]), [2018, 2019, 2020])
    with pytest.raises(ValueError, match="fit on"):
        leverage.check_fit(fitted, 2020)
    leverage.check_fit(fitted, 2021)


def test_fits_are_cached_by_season_and_need_three_earlier_seasons(tmp_path):
    calls = []

    def snaps_of(s: int) -> pl.DataFrame:
        calls.append(s)
        return _snaps(s)

    assert leverage.fitted_for(2018, [2016, 2017, 2018], snaps_of, tmp_path) is None
    first = leverage.fitted_for(2021, [2017, 2018, 2019, 2020, 2021], snaps_of, tmp_path)
    assert first["seasons"] == [2017, 2018, 2019, 2020]
    n = len(calls)
    again = leverage.fitted_for(2021, [2017, 2018, 2019, 2020, 2021], snaps_of, tmp_path)
    assert len(calls) == n and again["base"] == first["base"]
    # a new earlier season changes the key, so it refits
    leverage.fitted_for(2021, [2016, 2017, 2018, 2019, 2020, 2021], snaps_of, tmp_path)
    assert len(calls) > n
