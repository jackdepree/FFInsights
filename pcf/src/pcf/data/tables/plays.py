"""The `play` and `player_play` tables.

`play` is play-by-play (the spine, known the day after the game) with participation (known after
the Super Bowl, 2016-2025) and FTN charting (14 days after, 2022→) as parts. Where participation
or FTN repeat a play-by-play column, play-by-play's is kept. `player_play` is one row per player
on the field per run or pass play, with their slot label, known when participation is.
"""

import polars as pl

from pcf.core.log import get_logger
from pcf.data.clean import standard
from pcf.data.clean.players import PLAY_KEYS, players_on_play, plays_with_players
from pcf.data.clean.slots import slot_labels
from pcf.data.tables.frames import on_spine
from pcf.data.timeline import Calendar, known_at

log = get_logger(__name__)

# FTN columns with the same meaning as the keys or the spine's.
FTN_DROP = ["season", "week", "date_pulled"]


def _keyed(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.col("play_id").cast(pl.Int64), pl.col("season").cast(pl.Int32))


def _season(df: pl.DataFrame, cal: Calendar) -> pl.DataFrame:
    """Participation has no season column: it comes from the calendar."""
    return df.join(cal.games.select("game_id", "season"), on="game_id", how="left")


def _own_columns(df: pl.DataFrame, pbp: pl.DataFrame, what: str) -> pl.DataFrame:
    """Drop the columns play-by-play already has, except the keys."""
    repeats = [c for c in df.columns if c in pbp.columns and c not in PLAY_KEYS]
    if repeats:
        log.info("%s: play-by-play's %s kept", what, ", ".join(sorted(repeats)))
    return df.drop(repeats)


def play_parts(
    pbp: pl.DataFrame,
    cal: Calendar,
    participation: pl.DataFrame | None = None,
    ftn: pl.DataFrame | None = None,
) -> dict[str, pl.DataFrame]:
    """Raw play-by-play (+ raw participation, FTN charting) → the `play` parts: pbp (the
    spine), participation, ftn."""
    spine = _keyed(known_at("pbp", pbp, cal))
    parts = {"pbp": spine}
    if participation is not None:
        part = known_at("participation", participation, cal)
        part = _season(standard.participation(part), cal)
        part = _own_columns(_keyed(part), spine.drop("season", "known_at"), "participation")
        parts["participation"] = on_spine(part, spine, PLAY_KEYS, "play.participation")
    if ftn is not None:
        f = known_at("ftn_charting", ftn, cal).drop(FTN_DROP)
        f = f.rename({"nflverse_game_id": "game_id", "nflverse_play_id": "play_id"})
        f = _own_columns(_keyed(_season(f, cal)), spine.drop("season", "known_at"), "ftn")
        parts["ftn"] = on_spine(f, spine, PLAY_KEYS, "play.ftn")
    return parts


def player_play_parts(
    pbp: pl.DataFrame,
    participation: pl.DataFrame,
    labels: pl.DataFrame,
    rosters: pl.DataFrame,
    cal: Calendar,
) -> dict[str, pl.DataFrame]:
    """Raw play-by-play and participation, `depth_labels` and `standard.weekly_rosters` → the
    `player_play` part `on_field`: one row per listed player per run or pass play, with side,
    team, slot, position, position_label and label_source."""
    players = slot_labels(players_on_play(plays_with_players(pbp, participation)), labels, rosters)
    season_end = known_at(
        "participation", players.select(nflverse_game_id="game_id").unique(), cal
    ).rename({"nflverse_game_id": "game_id"})
    on_field = players.join(season_end, on="game_id", how="left").with_columns(
        pl.col("season").cast(pl.Int32)
    )
    return {"on_field": on_field.drop("week", "season_type")}
