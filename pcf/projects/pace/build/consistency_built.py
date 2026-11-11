"""Consistency of the built team_game.pace measures against the neutral ones (tendencies),
regular season 2006-2024 (2025 left out, as in the exploration)."""

import polars as pl

from pcf.data.tables.store import read_part
from pcf.validation.consistency import consistency

c = pl.col
SEASONS = list(range(2006, 2025))
sched = read_part("team_game", "schedule", seasons=SEASONS).select(
    "game_id", "team", "season", "week", "game_type"
).collect()
pace = read_part("team_game", "pace", seasons=SEASONS).drop("season", "known_at").collect()
tend = read_part("team_game", "tendencies", seasons=SEASONS).select(
    "game_id", "team", "tempo_seconds", "neutral_pass_oe", "no_huddle_rate"
).collect()
rows = (
    sched.filter(c("game_type") == "REG")
    .join(pace, on=["game_id", "team"])
    .join(tend, on=["game_id", "team"], how="left")
)
measures = [
    "pace_oe", "tempo_seconds", "proe", "neutral_pass_oe", "proe_1st", "proe_2nd", "proe_3rd",
    "no_huddle", "plays", "dropbacks", "runs", "drives", "plays_per_drive", "epa_per_play",
    "def_plays", "def_proe", "def_pace_oe",
]  # fmt: skip
# each measure as a gap from its season's league level: a level shared by every team (pace over
# expected drifts in the early seasons) would otherwise read as teams repeating
rows = rows.with_columns((c(m) - c(m).mean().over("season")).alias(m) for m in measures)
with pl.Config(tbl_rows=40, tbl_cols=20, tbl_width_chars=200):
    print(consistency(rows, measures))
