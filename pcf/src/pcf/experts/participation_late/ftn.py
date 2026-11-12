"""FTN's charting per play as inputs to the on-field model (participation-late#F2).

Per play, centred so 0 is the usual play:
- `bf`: players in the offense's backfield, capped at 3, minus 1;
- `box`: defenders in the box, 3 to 9, minus 6;
- `rush`: pass rushers / 4 (0 on runs); `blitz`: blitzers, capped at 4;
- `motion`, `pa` (play action), `screen`: 0 or 1;
- `fmiss`: 1 when the play isn't charted (FTN starts in 2022; about 3% of later plays), with the
  others 0.

The model learns a weight for each per position group, so two in the backfield can raise a back's
chance and lower a receiver's.
"""

from __future__ import annotations

import polars as pl

c = pl.col
FIRST_SEASON = 2022
COLUMNS = ["bf", "box", "rush", "blitz", "motion", "pa", "screen", "fmiss"]
RAW = [
    "n_offense_backfield",
    "n_defense_box",
    "n_pass_rushers",
    "n_blitzers",
    "is_motion",
    "is_play_action",
    "is_screen_pass",
]


def features(play: pl.DataFrame) -> pl.DataFrame:
    """`play` rows with FTN's columns → game_id, play_id and the input columns (charted plays
    only)."""
    f = play.select("game_id", "play_id", *RAW).filter(c("n_offense_backfield").is_not_null())
    return f.select(
        "game_id",
        c("play_id").cast(pl.Int64),
        bf=(c("n_offense_backfield").clip(0, 3) - 1).cast(pl.Float64),
        box=(c("n_defense_box").clip(3, 9) - 6).cast(pl.Float64),
        rush=(c("n_pass_rushers").clip(0, 8) / 4).cast(pl.Float64),
        blitz=c("n_blitzers").clip(0, 4).cast(pl.Float64),
        motion=c("is_motion").cast(pl.Float64),
        pa=c("is_play_action").cast(pl.Float64),
        screen=c("is_screen_pass").cast(pl.Float64),
    ).with_columns([c(x).fill_null(0.0) for x in COLUMNS if x != "fmiss"])


def join(g: pl.DataFrame, feats: pl.DataFrame) -> pl.DataFrame:
    """The grid with the FTN columns (`fmiss` 1 and the rest 0 where a play isn't charted)."""
    out = g.join(feats, on=["game_id", "play_id"], how="left")
    return out.with_columns(fmiss=c("bf").is_null().cast(pl.Float64)).with_columns(
        [c(x).fill_null(0.0) for x in COLUMNS if x != "fmiss"]
    )
