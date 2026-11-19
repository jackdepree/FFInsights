"""The play table: the situation, both sides' call fields and the outcomes, one row per scrimmage
play (decision 0036).

Inputs come from an in-season view (`INPUTS`): the play-by-play and FTN's charting (known about
14 days after kickoff), plus last season's charted traits (`team_season.charted`, schemes-v2,
known the day after the Super Bowl). Pressure and time to throw are outcomes from the
after-the-season participation data, read from a retrospective view (`TARGETS`) for training and
scoring only, never as inputs.
"""

from __future__ import annotations

import polars as pl

c = pl.col
KEYS = ["game_id", "play_id"]
INPUTS = {"play": ("pbp", "ftn"), "team_season": ("charted",)}
TARGETS = {"play": ("participation",)}
FIRST_SEASON = 2022  # FTN's charting starts here (EXPLORATION F1)
# The participation data changed provider in 2023: pressure is charted on 29% of 2022's dropbacks
# and 15% after, time to throw 2.79 s against 2.65 s. Those outcomes start in 2023.
FIRST_PARTICIPATION = 2023

# The situation: what public expected-points models use (BRIEF, "Terms").
SITUATION = [
    "down", "ydstogo", "yardline_100", "goal_to_go", "qtr", "half_seconds_remaining",
    "game_seconds_remaining", "score_differential", "posteam_timeouts_remaining",
    "defteam_timeouts_remaining", "home",
]  # fmt: skip
# The live call fields (in-season: the play-by-play and FTN). Screens and play action count as
# calls (the CEO's call 3).
OFFENSE_CALLS = [
    "shotgun", "no_huddle", "qb_location", "n_offense_backfield", "is_motion", "is_play_action",
    "is_screen_pass", "is_rpo", "is_trick_play", "is_qb_sneak", "starting_hash",
]  # fmt: skip
DEFENSE_CALLS = ["n_defense_box", "n_blitzers", "n_pass_rushers"]
CALLS = OFFENSE_CALLS + DEFENSE_CALLS
CATEGORICAL = ["qb_location", "starting_hash"]
# How a team plays, not how well (the CEO's call 5): last season's charted traits over expected
# (schemes-v2#R13: the raw rates shift with the charting by season, so the _oe columns).
OFFENSE_TRAITS = [
    "off_11_rate_oe", "off_12_rate_oe", "off_21_rate_oe", "off_heavy_rate_oe", "off_pistol_rate_oe",
    "off_time_to_throw_oe",
]  # fmt: skip
DEFENSE_TRAITS = [
    "def_box_oe", "def_man_rate_oe", "def_two_high_rate_oe", "def_blitz_rate_oe", "def_rushers_oe",
    "def_nickel_rate_oe", "def_dime_rate_oe",
]  # fmt: skip
TRAITS = OFFENSE_TRAITS + DEFENSE_TRAITS
FIELD_SETS = {
    "situation": SITUATION,
    "offense": SITUATION + OFFENSE_CALLS,
    "defense": SITUATION + DEFENSE_CALLS,
    "live": SITUATION + CALLS,
    "traits": SITUATION + CALLS + TRAITS,
}
POPULATIONS = ("run", "dropback", "attempt", "snap")
# FTN writes "0" for a location or hash it didn't chart.
NOT_CHARTED = "0"

PBP_COLUMNS = [
    "game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "home_team",
    "play_type", "two_point_attempt", "down", "ydstogo", "yardline_100", "goal_to_go", "qtr",
    "half_seconds_remaining", "game_seconds_remaining", "score_differential",
    "posteam_timeouts_remaining", "defteam_timeouts_remaining", "shotgun", "no_huddle",
    "rush_attempt", "pass_attempt", "qb_dropback", "qb_scramble", "sack", "complete_pass",
    "first_down", "pass_touchdown", "rush_touchdown", "penalty", "success", "yards_gained",
    "air_yards", "known_at",
]  # fmt: skip
FTN_COLUMNS = [x for x in CALLS if x not in ("shotgun", "no_huddle")]


def _flag(name: str) -> pl.Expr:
    return c(name).cast(pl.Float64).fill_null(0.0)


def frame(play: pl.DataFrame) -> pl.DataFrame:
    """Scrimmage plays with a down (runs, passes and plays wiped out by a penalty; no two-point
    tries), every season type, with the situation, the call fields and the outcomes. `play` is a
    view's `play` table with its `pbp` and `ftn` parts. `known_at` is the latest of the two parts'
    (FTN's when it charted the play, else the play-by-play's)."""
    missing = sorted(set(PBP_COLUMNS) - set(play.columns))
    if missing:
        raise ValueError(f"the play table is missing {missing}")
    d = play.filter(
        c("play_type").is_in(["run", "pass", "no_play"]),
        c("two_point_attempt").fill_null(0) == 0,
        c("down").is_not_null(),
        c("posteam").is_not_null(),
    )
    # The gateway joins a part's columns only where its row was known; FTN's are empty before.
    if "ftn_known_at" in d.columns:
        d = d.with_columns(known_at=pl.max_horizontal("known_at", "ftn_known_at"))
    else:
        d = d.with_columns([pl.lit(None, pl.Float64).alias(x) for x in FTN_COLUMNS])
    scrimmage = c("play_type") != "no_play"
    run = scrimmage & (c("rush_attempt") == 1) & (c("qb_dropback") == 0)
    dropback = scrimmage & (c("qb_dropback") == 1)
    attempt = dropback & (c("pass_attempt") == 1) & (c("sack") == 0) & (c("qb_scramble") == 0)
    blank = {
        x: pl.when(c(x).cast(pl.String) == NOT_CHARTED).then(None).otherwise(c(x))
        for x in CATEGORICAL
    }
    out = d.with_columns(
        season=c("season").cast(pl.Int32),
        play_id=c("play_id").cast(pl.Int64),
        population=pl.when(run).then(pl.lit("run")).when(attempt).then(pl.lit("attempt"))
        .when(dropback).then(pl.lit("dropback")).otherwise(pl.lit("snap")),
        is_run=run,
        is_dropback=dropback,
        is_attempt=attempt,
        home=(c("posteam") == c("home_team")).cast(pl.Float64),
        **{x: e.cast(pl.String) for x, e in blank.items()},
    )  # fmt: skip
    numeric = [x for x in SITUATION + CALLS if x not in CATEGORICAL]
    out = out.with_columns([c(x).cast(pl.Float64) for x in numeric])
    out = out.with_columns(**_outcome_columns())
    return out.select(
        *KEYS, "season", "season_type", "week", "posteam", "defteam", "known_at", "population",
        "is_run", "is_dropback", "is_attempt", *SITUATION, *CALLS, *OUTCOME_COLUMNS,
    )  # fmt: skip


OUTCOME_COLUMNS = [
    "yards", "stuffed", "explosive_run", "explosive_pass", "success_y", "first_down_y", "td",
    "sack_y", "complete_y", "air_yards_y", "penalty_y",
]  # fmt: skip


def _outcome_columns() -> dict[str, pl.Expr]:
    y = c("yards_gained").cast(pl.Float64)
    return {
        "yards": y,
        "stuffed": (y <= 0).cast(pl.Float64),
        "explosive_run": (y >= 10).cast(pl.Float64),
        "explosive_pass": (y >= 20).cast(pl.Float64),
        "success_y": c("success").cast(pl.Float64),
        "first_down_y": c("first_down").cast(pl.Float64),
        "td": (_flag("pass_touchdown") + _flag("rush_touchdown")).clip(0, 1),
        "sack_y": c("sack").cast(pl.Float64),
        "complete_y": c("complete_pass").cast(pl.Float64),
        "air_yards_y": c("air_yards").cast(pl.Float64),
        "penalty_y": c("penalty").cast(pl.Float64),
    }


def participation_targets(participation: pl.DataFrame) -> pl.DataFrame:
    """Pressure and time to throw per play, from the after-the-season participation part (a
    retrospective view's `play` table, or the part itself), from `FIRST_PARTICIPATION` on."""
    return participation.filter(c("season") >= FIRST_PARTICIPATION).select(
        c("game_id"),
        c("play_id").cast(pl.Int64),
        pressure_y=c("was_pressure").cast(pl.Float64),
        time_to_throw_y=c("time_to_throw").cast(pl.Float64),
        known_at_targets=c("participation_known_at")
        if "participation_known_at" in participation.columns
        else c("known_at"),
    )


def traits(charted: pl.DataFrame) -> pl.DataFrame:
    """Each team's charted traits for the season they're a prior for (`prior_for`): one row per
    team and season, with the offense's and the defense's columns."""
    missing = sorted(set(TRAITS) - set(charted.columns))
    if missing:
        raise ValueError(f"team_season.charted is missing {missing}")
    return charted.select("team", *TRAITS, season=c("prior_for").cast(pl.Int32))


def with_traits(plays: pl.DataFrame, table: pl.DataFrame) -> pl.DataFrame:
    """The offense's offensive traits and the defense's defensive traits on each play; missing
    for a team with no prior season."""
    off = table.select("team", "season", *OFFENSE_TRAITS).rename({"team": "posteam"})
    dfn = table.select("team", "season", *DEFENSE_TRAITS).rename({"team": "defteam"})
    out = plays.join(off, on=["posteam", "season"], how="left").join(
        dfn, on=["defteam", "season"], how="left"
    )
    if out.height != plays.height:
        raise ValueError("a team has two trait rows for one season")
    return out


def build(view, season: int, target_view=None) -> pl.DataFrame:
    """One season's play table from an in-season inputs view (and, given a retrospective
    `target_view`, with pressure and time to throw)."""
    play = view.table("play", seasons=[season])
    out = frame(play)
    charted = view.table("team_season", seasons=[season - 1])
    out = with_traits(out, traits(charted))
    if target_view is not None:
        part = target_view.table("play", seasons=[season])
        out = out.join(participation_targets(part), on=KEYS, how="left")
    else:
        out = out.with_columns(
            pressure_y=pl.lit(None, pl.Float64),
            time_to_throw_y=pl.lit(None, pl.Float64),
            known_at_targets=pl.lit(None, pl.Datetime("us", "UTC")),
        )
    return out
