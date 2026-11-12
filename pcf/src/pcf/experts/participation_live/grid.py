"""The grid: for each team-game-side, its scrimmage snaps in order (rows) by the players with
snaps for that side (columns), with what's known about each cell by the morning after.

- **Snaps** (`side_plays`): every scrimmage play (pass, run, no-play, kneel, spike; no special
  teams) from the play-by-play, once per side, numbered in the team's game (`n`) and drive
  (`drive_n`), with the situation flags and the sequence flags the chain needs (`sd`: same drive
  as the snap before; `sd2`: the two before too; `start`, `start2`: the game's first two snaps).
  It never reads the answer key, so a live game gets the same grid as a past one.
- **Candidates** (`candidates`): each player-game-side with snaps (snap counts, the morning
  after), his position group, his snap target (snaps scaled so the side's targets add to 11 a
  snap) and `full` (on every snap: his snaps are the side's most).
- **Named** (`named`): players the play-by-play names on a play, with their side from the roster.
  Every one is in the true lineup (participation-live#F1).
- **Truth** (`truth`): the answer key, `player_play.on_field`, for training and scoring only.
"""

from __future__ import annotations

import polars as pl

from pcf.data.clean import standard

c = pl.col
SCRIMMAGE = ["pass", "run", "no_play", "qb_kneel", "qb_spike"]
OFFENSE_ROLES = [
    "passer_player_id", "receiver_player_id", "rusher_player_id", "lateral_receiver_player_id",
    "lateral_rusher_player_id",
]  # fmt: skip
DEFENSE_ROLES = [
    "interception_player_id", "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id",
    "qb_hit_1_player_id", "qb_hit_2_player_id", "tackle_for_loss_1_player_id",
    "tackle_for_loss_2_player_id", "solo_tackle_1_player_id", "solo_tackle_2_player_id",
    "assist_tackle_1_player_id", "assist_tackle_2_player_id", "assist_tackle_3_player_id",
    "assist_tackle_4_player_id", "tackle_with_assist_1_player_id",
    "tackle_with_assist_2_player_id", "pass_defense_1_player_id", "pass_defense_2_player_id",
    "forced_fumble_player_1_player_id", "forced_fumble_player_2_player_id",
]  # fmt: skip
EITHER_ROLES = ["penalty_player_id", "fumbled_1_player_id", "fumbled_2_player_id"]
ROLES = [*OFFENSE_ROLES, *DEFENSE_ROLES, *EITHER_ROLES]
SITUATION = [
    "posteam", "defteam", "season_type", "week", "fixed_drive", "qtr", "down", "ydstogo",
    "yardline_100", "score_differential", "half_seconds_remaining", "no_huddle", "shotgun",
    "play_type", "pass", "order_sequence",
]  # fmt: skip
PBP_COLUMNS = ["game_id", "play_id", "season", "special_teams_play", *SITUATION, *ROLES]
GROUP = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "T": "OL", "G": "OL", "C": "OL",
    "OL": "OL", "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "OLB": "LB", "ILB": "LB",
    "MLB": "LB", "LB": "LB", "CB": "DB", "SS": "DB", "FS": "DB", "S": "DB", "DB": "DB",
}  # fmt: skip
# Situation flags (H32, H33): each player's and team's habits are measured in these.
FLAGS: dict[str, pl.Expr] = {
    "third": c("down") == 3,
    "fourth": c("down") == 4,
    "short": (c("ydstogo") <= 2) & (c("down") >= 2),
    "long": (c("ydstogo") >= 8) & (c("down") >= 2),
    "red": c("yardline_100") <= 20,
    "goal": c("yardline_100") <= 5,
    "twomin": c("half_seconds_remaining") <= 120,
    "garbage": (c("qtr") == 4) & (c("score_differential").abs() >= 17),
    "q4": c("qtr") == 4,
    "shotgun": c("shotgun") == 1,
    "no_huddle": c("no_huddle") == 1,
    "first_snap": c("drive_n") == 0,
    "pass": c("pass") == 1,
}
FLAG_COLUMNS = [f"f_{k}" for k in FLAGS]
SIDE_KEYS = ["game_id", "side", "team"]
CELL_KEYS = ["game_id", "play_id", "side", "gsis_id"]


def scrimmage(pbp: pl.DataFrame) -> pl.DataFrame:
    """Every scrimmage snap, teams standardised, in the game's order."""
    pbp = pbp.select([x for x in PBP_COLUMNS if x in pbp.columns]).with_columns(
        c("play_id").cast(pl.Int64)
    )
    pbp = pbp.filter(
        c("play_type").is_in(SCRIMMAGE)
        & (c("special_teams_play").fill_null(0) != 1)
        & c("posteam").is_not_null()
        & c("defteam").is_not_null()
    )
    pbp = standard.standard_teams(pbp, "posteam").pipe(standard.standard_teams, "defteam")
    return pbp.sort("game_id", "order_sequence", "play_id")


def side_plays(plays: pl.DataFrame) -> pl.DataFrame:
    """Each snap once per side: `team` is that side's team, `n` the team's snap number for the
    side in the game, `drive_n` the snap number in the drive, and the flags."""
    both = pl.concat(
        [
            plays.with_columns(side=pl.lit("offense"), team=c("posteam")),
            plays.with_columns(side=pl.lit("defense"), team=c("defteam")),
        ]
    ).sort("game_id", "side", "team", "order_sequence", "play_id")
    both = both.with_columns(
        n=pl.int_range(pl.len()).over(SIDE_KEYS).cast(pl.Int32),
        drive_n=pl.int_range(pl.len()).over(*SIDE_KEYS, "fixed_drive").cast(pl.Int32),
    )
    prev_drive = c("fixed_drive").shift(1).over(SIDE_KEYS)
    prev2_drive = c("fixed_drive").shift(2).over(SIDE_KEYS)
    both = both.with_columns(
        sd=(c("fixed_drive") == prev_drive).fill_null(False),
        sd2=((c("fixed_drive") == prev_drive) & (c("fixed_drive") == prev2_drive)).fill_null(False),
        start=c("n") == 0,
        start2=c("n") == 1,
        **{f"f_{k}": v.fill_null(False) for k, v in FLAGS.items()},
    )
    keep = [
        "game_id", "play_id", "season", "season_type", "week", "side", "team", "n", "drive_n",
        "fixed_drive", "pass", "sd", "sd2", "start", "start2", *FLAG_COLUMNS,
    ]  # fmt: skip
    return both.select(keep)


def candidates(player_game: pl.DataFrame) -> pl.DataFrame:
    """Each player-game-side with snaps: team, position, group, snaps, `target` (his snaps scaled
    so the side's targets add to 11 a snap, per snap of the side: a share up to 1) and `full`."""
    pg = standard.standard_teams(player_game.drop_nulls("team"), "team")
    out = []
    for side, col in (("offense", "offense_snaps"), ("defense", "defense_snaps")):
        out.append(
            pg.filter(c(col).fill_null(0) > 0).select(
                "game_id",
                "team",
                "gsis_id",
                "position",
                side=pl.lit(side),
                snaps=c(col).cast(pl.Float64),
            )
        )
    cand = pl.concat(out)
    cand = cand.with_columns(
        group=c("position").replace_strict(GROUP, default="OTHER"),
        total=c("snaps").sum().over(SIDE_KEYS),
        most=c("snaps").max().over(SIDE_KEYS),
    )
    return cand.with_columns(
        share=(c("snaps") * 11 / c("total")).clip(0, 1),
        full=c("snaps") >= c("most"),
    ).drop("total", "most")


def named(plays: pl.DataFrame, cand: pl.DataFrame) -> pl.DataFrame:
    """The players the play-by-play names on each snap, with their side from the candidates."""
    roles = [r for r in ROLES if r in plays.columns]
    long = (
        plays.select("game_id", "play_id", "posteam", "defteam", *roles)
        .unpivot(
            index=["game_id", "play_id", "posteam", "defteam"],
            on=roles,
            variable_name="role",
            value_name="gsis_id",
        )
        .drop_nulls("gsis_id")
    )
    sides = cand.select("game_id", "team", "gsis_id", "side")
    long = long.join(sides, on=["game_id", "gsis_id"], how="inner").filter(
        ((c("side") == "offense") & (c("team") == c("posteam")))
        | ((c("side") == "defense") & (c("team") == c("defteam")))
    )
    return long.select(CELL_KEYS).unique().with_columns(named=pl.lit(True))


def grid(pbp: pl.DataFrame, player_game: pl.DataFrame) -> pl.DataFrame:
    """One row per candidate and snap of his side: the cell keys, the snap's columns, his
    `share`, `full`, `named`, and `pinned` (named or full: on for certain)."""
    plays = scrimmage(pbp)
    sp = side_plays(plays)
    cand = candidates(player_game)
    g = cand.select(*SIDE_KEYS, "gsis_id", "position", "group", "snaps", "share", "full").join(
        sp, on=SIDE_KEYS
    )
    g = g.join(named(plays, cand), on=CELL_KEYS, how="left").with_columns(
        c("named").fill_null(False)
    )
    g = g.with_columns(
        n_plays=pl.len().over(*SIDE_KEYS, "gsis_id"),
        pinned=c("named") | c("full"),
    )
    return g.sort(*SIDE_KEYS, "gsis_id", "n")


def truth(player_play: pl.DataFrame) -> pl.DataFrame:
    """The answer key: (game, play, side, player) on the field, and each play-side's count."""
    on = player_play.select("game_id", c("play_id").cast(pl.Int64), "side", "gsis_id")
    return on.unique().with_columns(on=pl.lit(1, pl.Int8))


def with_truth(g: pl.DataFrame, on: pl.DataFrame) -> pl.DataFrame:
    """The grid with `on` (1 if on the field) and `full_truth` (the play-side's true lineup has
    11: the plays that are scored)."""
    g = g.join(on, on=CELL_KEYS, how="left").with_columns(c("on").fill_null(0))
    counts = on.group_by("game_id", "play_id", "side").agg(n_true=pl.len())
    g = g.join(counts, on=["game_id", "play_id", "side"], how="left")
    return g.with_columns(full_truth=(c("n_true") == 11).fill_null(False)).drop("n_true")
