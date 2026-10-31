"""Who was on the field: participation player lists joined to play-by-play, one row per player."""

from collections.abc import Sequence

import polars as pl

PLAY_KEYS = ["game_id", "play_id"]
SIDES = {"offense": "posteam", "defense": "defteam"}


def plays_with_players(pbp: pl.DataFrame, participation: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play with participation's columns added (null where a play has none).

    nfl_data_py used to do this join itself; nflverse publishes the two separately. `play_id` is a
    float in older play-by-play files and an integer in participation, so both become Int64.
    Raises if participation lists a play twice.
    """
    part = participation.rename({"nflverse_game_id": "game_id"}).with_columns(
        pl.col("play_id").cast(pl.Int64)
    )
    dupes = part.filter(part.select(PLAY_KEYS).is_duplicated())
    if dupes.height:
        raise ValueError(f"participation lists {dupes.height} plays twice, e.g. {dupes.row(0)}")
    # Columns both files share (old_game_id, possession_team, ...) are kept from play-by-play.
    extra = [c for c in part.columns if c in PLAY_KEYS or c not in pbp.columns]
    return pbp.with_columns(pl.col("play_id").cast(pl.Int64)).join(
        part.select(extra), on=PLAY_KEYS, how="left"
    )


def players_on_play(
    plays: pl.DataFrame, play_types: Sequence[str] = ("run", "pass")
) -> pl.DataFrame:
    """One row per listed player per play: game_id, play_id, season, week, season_type, side,
    team, slot, gsis_id.

    Unlike the old `pivot_wide_both_sides`, every listed player is kept (the old code cut lists
    at 11), and empty slots make no row. `slot` is the player's place in the list, 1 upward.
    """
    plays = plays.filter(pl.col("play_type").is_in(list(play_types)))
    sides = []
    for side, team in SIDES.items():
        sides.append(
            plays.select(
                *PLAY_KEYS,
                "season",
                "week",
                "season_type",
                side=pl.lit(side),
                team=pl.col(team),
                gsis_id=pl.col(f"{side}_players").str.split(";"),
            )
            .explode("gsis_id")
            .with_columns(pl.col("gsis_id").str.strip_chars())
            .with_columns(slot=pl.int_range(1, pl.len() + 1).over(*PLAY_KEYS, "side"))
            .filter(pl.col("gsis_id").is_not_null() & (pl.col("gsis_id") != ""))
        )
    return pl.concat(sides).sort(*PLAY_KEYS, "side", "slot")
