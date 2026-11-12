"""Shared loaders for the participation-live exploration (2026-11-11). Discovery only: 2016-2024;
the 2025 vault and 2026 are never read.

- `plays()`: every regular-season scrimmage snap (pass, run, no-play, kneel, spike) whose true
  lineup has 11 a side, with its situation and the play's order within the team's game.
- `lineups()`: who was on the field on each of those plays (`player_play.on_field`, the answer
  key, post-season data), one row per player, play and side.
- `named()`: the players the play-by-play names on each play (passer, rusher, receiver, tacklers,
  pass defenders, sackers, hitters, penalised players), with their side from the roster.
- `snaps()`: each player-game's offensive and defensive snap counts (known the morning after),
  his team and roster position.

Cached in `interim/participation_live/`.
"""

# ruff: noqa: E501
from __future__ import annotations

import polars as pl

from pcf.config import get_config
from pcf.data.clean import standard

c = pl.col
SEASONS = list(range(2016, 2025))
CACHE = get_config().zone("interim") / "participation_live"
TABLES = get_config().zone("tables")
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
EITHER = ["penalty_player_id", "fumbled_1_player_id", "fumbled_2_player_id"]
SITUATION = [
    "posteam", "defteam", "week", "fixed_drive", "qtr", "down", "ydstogo", "yardline_100",
    "score_differential", "game_seconds_remaining", "half_seconds_remaining", "no_huddle",
    "shotgun", "play_type", "pass", "rush", "yards_gained", "penalty", "order_sequence",
]  # fmt: skip


def _part(table: str, part: str, seasons=SEASONS, columns=None) -> pl.DataFrame:
    files = [TABLES / table / part / f"season={s}" / "data.parquet" for s in seasons]
    lf = pl.scan_parquet(
        [f for f in files if f.exists()], extra_columns="ignore", missing_columns="insert"
    )
    return (lf.select(columns) if columns else lf).collect()


def _cached(name: str, build, rebuild: bool):
    path = CACHE / f"{name}.parquet"
    if path.exists() and not rebuild:
        return pl.read_parquet(path)
    CACHE.mkdir(parents=True, exist_ok=True)
    df = build()
    df.write_parquet(path)
    return df


def _plays() -> pl.DataFrame:
    pbp = _part(
        "play", "pbp", SEASONS,
        ["game_id", "play_id", "season", "season_type", "special_teams_play", *SITUATION,
         *OFFENSE_ROLES, *DEFENSE_ROLES, *EITHER],
    ).with_columns(c("play_id").cast(pl.Int64))  # fmt: skip
    pbp = pbp.filter(
        (c("season_type") == "REG") & c("play_type").is_in(SCRIMMAGE) & (c("special_teams_play") != 1)
    )
    pbp = standard.standard_teams(pbp, "posteam").pipe(standard.standard_teams, "defteam")
    on = _part("player_play", "on_field", SEASONS, ["game_id", "play_id", "side"])
    full = (
        on.group_by("game_id", "play_id")
        .agg(n_off=(c("side") == "offense").sum(), n_def=(c("side") == "defense").sum())
        .filter((c("n_off") == 11) & (c("n_def") == 11))
        .select("game_id", "play_id")
    )
    out = pbp.join(full, on=["game_id", "play_id"], how="semi").sort("game_id", "order_sequence", "play_id")
    return out.with_columns(
        n=pl.int_range(pl.len()).over("game_id", "posteam"),  # the offense's snap number in the game
        drive_n=pl.int_range(pl.len()).over("game_id", "fixed_drive"),  # snap number in the drive
    )


def plays(rebuild: bool = False) -> pl.DataFrame:
    return _cached("plays", _plays, rebuild)


def _lineups() -> pl.DataFrame:
    p = plays().select("game_id", "play_id", "season", "posteam", "defteam")
    on = _part("player_play", "on_field", SEASONS, ["game_id", "play_id", "side", "gsis_id", "position"])
    out = on.join(p, on=["game_id", "play_id"])
    return out.with_columns(team=pl.when(c("side") == "offense").then(c("posteam")).otherwise(c("defteam"))).drop(
        "posteam", "defteam"
    )


def lineups(rebuild: bool = False) -> pl.DataFrame:
    return _cached("lineups", _lineups, rebuild)


def _snaps() -> pl.DataFrame:
    s = _part("player_game", "snaps", SEASONS, ["gsis_id", "game_id", "season", "offense_snaps", "defense_snaps"])
    r = _part("player_game", "roster", SEASONS, ["gsis_id", "game_id", "team", "position", "years_exp"])
    r = standard.standard_teams(r, "team")
    return s.join(r, on=["gsis_id", "game_id"], how="left")


def snaps(rebuild: bool = False) -> pl.DataFrame:
    return _cached("snaps", _snaps, rebuild)


def _named() -> pl.DataFrame:
    p = plays()
    cols = [*OFFENSE_ROLES, *DEFENSE_ROLES, *EITHER]
    long = p.select("game_id", "play_id", "posteam", "defteam", *cols).unpivot(
        index=["game_id", "play_id", "posteam", "defteam"], on=cols, variable_name="role", value_name="gsis_id"
    ).drop_nulls("gsis_id")
    team = snaps().select("gsis_id", "game_id", "team").drop_nulls()
    long = long.join(team, on=["gsis_id", "game_id"], how="inner")
    long = long.with_columns(
        side=pl.when(c("team") == c("posteam")).then(pl.lit("offense"))
        .when(c("team") == c("defteam")).then(pl.lit("defense"))
    ).drop_nulls("side")  # fmt: skip
    return long.group_by("game_id", "play_id", "side", "gsis_id").agg(roles=c("role").unique())


def named(rebuild: bool = False) -> pl.DataFrame:
    return _cached("named", _named, rebuild)


def _pairs() -> pl.DataFrame:
    """Each pair of consecutive snaps in the same drive, per side: how many of the 11 changed
    (`changes`), and the second play's situation (`next_*`) and the first play's result."""
    p = plays().sort("game_id", "posteam", "n")
    nxt = p.select(
        "game_id", "posteam", "fixed_drive", "play_id", "yards_gained", "pass", "rush",
        next_play_id=c("play_id").shift(-1).over("game_id", "posteam"),
        next_drive=c("fixed_drive").shift(-1).over("game_id", "posteam"),
    ).filter(c("next_drive") == c("fixed_drive"))  # fmt: skip
    sit = p.select(
        "game_id", c("play_id").alias("next_play_id"), "season", "week", "defteam",
        next_down="down", next_ydstogo="ydstogo", next_qtr="qtr", next_yardline="yardline_100",
        next_half_secs="half_seconds_remaining", next_score="score_differential",
        next_no_huddle="no_huddle", next_shotgun="shotgun", next_pass="pass", next_drive_n="drive_n",
    )  # fmt: skip
    pairs = nxt.join(sit, on=["game_id", "next_play_id"])
    L = lineups().select("game_id", "play_id", "side", "gsis_id")
    a = L.join(pairs.select("game_id", "play_id", "next_play_id"), on=["game_id", "play_id"])
    b = L.rename({"play_id": "next_play_id"}).with_columns(kept=pl.lit(1))
    kept = (
        a.join(b, on=["game_id", "next_play_id", "side", "gsis_id"], how="left")
        .group_by("game_id", "play_id", "side")
        .agg(kept=c("kept").fill_null(0).sum())
    )
    out = pairs.join(kept, on=["game_id", "play_id"])
    return out.with_columns(
        changes=11 - c("kept"),
        team=pl.when(c("side") == "offense").then(c("posteam")).otherwise(c("defteam")),
    )


def pairs(rebuild: bool = False) -> pl.DataFrame:
    return _cached("pairs", _pairs, rebuild)


def coaches() -> pl.DataFrame:
    pg = _part("team_game", "pregame", SEASONS, ["game_id", "team", "coach"])
    return standard.standard_teams(pg, "team")


GROUP = {"QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE", "T": "OL", "G": "OL", "C": "OL", "OL": "OL",
         "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "OLB": "LB", "ILB": "LB", "MLB": "LB", "LB": "LB",
         "CB": "DB", "SS": "DB", "FS": "DB", "S": "DB", "DB": "DB"}  # fmt: skip


def _panel() -> pl.DataFrame:
    """One row per part-timer (on some but not all of his side's snaps in the game) and team snap:
    on or off, his touches, his streaks, and the next snaps (`on_k`, `drive_k`, `nx_*`)."""
    P = plays()
    L = lineups().select("game_id", "play_id", "side", "team", "gsis_id", "position")
    cp = _part("play", "pbp", SEASONS, ["game_id", "play_id", "complete_pass"]).with_columns(c("play_id").cast(pl.Int64))
    P = P.join(cp, on=["game_id", "play_id"], how="left")

    # part-timers: on some but not all of the side's snaps in the game
    team_plays = pl.concat([
        P.with_columns(side=pl.lit("offense"), team=c("posteam")),
        P.with_columns(side=pl.lit("defense"), team=c("defteam")),
    ])  # fmt: skip
    n_team = team_plays.group_by("game_id", "side", "team").agg(n_team=pl.len())
    pg = L.group_by("game_id", "side", "team", "gsis_id").agg(n_on=pl.len(), position=c("position").mode().first())
    pg = pg.join(n_team, on=["game_id", "side", "team"]).with_columns(share=c("n_on") / c("n_team"))
    pg = pg.filter(c("share") < 0.999).with_columns(group=c("position").replace_strict(GROUP, default=None)).drop_nulls("group")

    cols = ["game_id", "play_id", "side", "team", "season", "week", "fixed_drive", "n", "drive_n", "down", "ydstogo",
            "qtr", "yardline_100", "half_seconds_remaining", "score_differential", "no_huddle", "shotgun",
            "yards_gained", "pass", "rush", "complete_pass"]  # fmt: skip
    X = pg.select("game_id", "side", "team", "gsis_id", "group", "share").join(team_plays.select(cols), on=["game_id", "side", "team"])
    X = X.join(L.select("game_id", "play_id", "side", "gsis_id").with_columns(on=pl.lit(1)), on=["game_id", "play_id", "side", "gsis_id"], how="left")
    N = named()
    X = X.join(N.select("game_id", "play_id", "side", "gsis_id", "roles"), on=["game_id", "play_id", "side", "gsis_id"], how="left")
    X = X.with_columns(
        on=c("on").fill_null(0),
        carry=c("roles").list.contains("rusher_player_id").fill_null(False),
        target=c("roles").list.contains("receiver_player_id").fill_null(False),
        involved=c("roles").list.len().fill_null(0) > 0,
    ).with_columns(
        reception=c("target") & (c("complete_pass") == 1),
        touch=pl.when(c("side") == "offense").then(c("carry") | c("target")).otherwise(c("involved")),
        big=(c("yards_gained") >= 20) & (c("on") == 1),
    ).drop("roles")

    # sequences within the player's game: streaks, the next plays, same drive or not
    key = ["game_id", "side", "gsis_id"]
    X = X.sort(*key, "n").with_columns(
        run=(c("on") != c("on").shift(1)).fill_null(True).cum_sum().over(key),
        trun=(c("touch") != c("touch").shift(1)).fill_null(True).cum_sum().over(key),
    )
    X = X.with_columns(
        streak=pl.when(c("on") == 1).then(pl.int_range(1, pl.len() + 1).over(*key, "run")).otherwise(0),
        touch_streak=pl.when(c("touch")).then(pl.int_range(1, pl.len() + 1).over(*key, "trun")).otherwise(0),
        drive_on=c("on").cum_sum().over(*key, "fixed_drive"),  # his snaps in this drive so far, this one included
        prev_on=c("on").shift(1).over(key),
        prev2_on=c("on").shift(2).over(key),
        prev_drive=c("fixed_drive").shift(1).over(key),
        **{f"on_{k}": c("on").shift(-k).over(key) for k in (1, 2, 3)},
        **{f"drive_{k}": c("fixed_drive").shift(-k).over(key) for k in (1, 2, 3)},
        **{f"nx_{s}": c(s).shift(-1).over(key) for s in ("down", "ydstogo", "qtr", "yardline_100", "half_seconds_remaining", "score_differential", "no_huddle", "shotgun", "drive_n")},
    )
    X = X.drop("run", "trun")
    return X


def panel(rebuild: bool = False) -> pl.DataFrame:
    return _cached("panel", _panel, rebuild)
