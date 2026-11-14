"""team-efficiency exploration (2026-11-12), step 1: one compact play table for every hunch test.

Regular-season passes and runs 2006-2024 (never the 2025 vault) from nflverse play-by-play, with
EPA, WPA, win chance, series and drive ids, teams standardised as PCF's tables do. Kneels, spikes
and two-point tries are left out (they aren't plays a team tries to gain on).

Adds the EPA-WPA gap (H44): a play's WPA less what its EPA is usually worth in win chance at that
moment, from a gradient-boosted model fitted on 2006-2015 only (no look-ahead into the scored
seasons).

Writes `<interim>/team-efficiency/plays.parquet` (gitignored). Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/build_plays.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.config import get_config
from pcf.data.clean import standard
from pcf.data.tables.store import read_part

c = pl.col
SEASONS = range(2006, 2025)
TUNE = range(2006, 2016)
COLS = [
    "game_id", "play_id", "season", "week", "season_type", "posteam", "defteam", "home_team",
    "away_team", "down", "ydstogo", "yardline_100", "qtr", "half_seconds_remaining",
    "game_seconds_remaining", "score_differential", "wp", "vegas_wp", "ep", "epa", "wpa",
    "vegas_wpa", "success", "pass", "rush", "play_type", "two_point_attempt", "series",
    "series_success", "series_result", "fixed_drive", "fixed_drive_result", "posteam_score",
    "defteam_score", "spread_line", "total_line",
]
GAP_X = ["epa", "wp", "score_differential", "game_seconds_remaining", "half_seconds_remaining", "qtr", "down", "ydstogo", "yardline_100"]


def main() -> None:
    p = (
        read_part("play", "pbp", seasons=list(SEASONS))
        .select(COLS)
        .filter(
            (c("season_type") == "REG")
            & c("play_type").is_in(["pass", "run"])
            & (c("two_point_attempt").fill_null(0) == 0)
            & c("epa").is_not_null()
            & ~c("epa").is_nan()
            & c("wpa").is_not_null()
            & ~c("wpa").is_nan()
        )
        .collect()
    )
    for t in ("posteam", "defteam", "home_team", "away_team"):
        p = standard.standard_teams(p, t)
    p = p.with_columns(
        home=(c("posteam") == c("home_team")).cast(pl.Int8),
        is_pass=(c("play_type") == "pass").cast(pl.Int8),
        drive_key=pl.concat_str("game_id", "posteam", "fixed_drive", separator="|"),
        series_key=pl.concat_str("game_id", "posteam", "series", separator="|"),
    )
    # The EPA-WPA gap: WPA less its usual value for this EPA at this moment (fitted on 2006-2015).
    tune = p.filter(c("season").is_in(list(TUNE)))
    X = tune.select(GAP_X).to_numpy().astype(float)
    m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.1, max_leaf_nodes=63, random_state=0)
    m.fit(X, tune["wpa"].to_numpy())
    pred = m.predict(p.select(GAP_X).to_numpy().astype(float))
    p = p.with_columns(wpa_expected=pl.Series(pred), gap=c("wpa") - pl.Series(pred))
    r2_tune = 1 - np.var(tune["wpa"].to_numpy() - m.predict(X)) / np.var(tune["wpa"].to_numpy())
    later = p.filter(c("season") >= 2016)
    r2_later = 1 - (later["gap"].var() / later["wpa"].var())
    out = get_config().zone("interim") / "team-efficiency"
    out.mkdir(parents=True, exist_ok=True)
    p.write_parquet(out / "plays.parquet")
    print(f"plays {p.height:,}, seasons {p['season'].min()}-{p['season'].max()}, games {p['game_id'].n_unique():,}")
    print(f"WPA explained by EPA and the moment: R2 {r2_tune:.3f} (2006-2015, fitted), {r2_later:.3f} (2016-2024)")
    print(p.group_by("season").agg(pl.len(), c("series_key").n_unique().alias("series"), c("drive_key").n_unique().alias("drives")).sort("season"))


if __name__ == "__main__":
    main()
