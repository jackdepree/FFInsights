"""Light exploration for tag-tables: can each seed tag be built from the tables, and how often
does it fire? Prototype rules only; the package versions get written and tested in the build.

    uv run python projects/tag-tables/explore/prototype_tags.py

Needs the built tables (`pcf tables build`). Prints each tag's level, when it's known, and the
share of rows it fires on in 2023–2024, plus a few agreement checks between alternatives.
"""

import polars as pl

from pcf.data.tables import load

SEASONS = [2023, 2024]
pl.Config.set_tbl_rows(80)
pl.Config.set_fmt_str_lengths(60)

c = pl.col
scrimmage = c("play_type").is_in(["run", "pass"])
lead = c("score_differential")  # the offense's lead before the snap
q4_late = (c("qtr") == 4) & (c("game_seconds_remaining") <= 240)

# name: (family, known, rule). Families: measured, situation, lore. Known: before_snap, after_play.
PLAY = {
    "successful": ("measured", "after_play", c("success") == 1),
    "positive_cpoe": ("measured", "after_play", c("cpoe") > 0),
    "explosive": (
        "measured",
        "after_play",
        ((c("play_type") == "run") & (c("yards_gained") >= 10))
        | ((c("play_type") == "pass") & (c("yards_gained") >= 20)),
    ),
    "stuffed_run": ("measured", "after_play", (c("play_type") == "run") & (c("yards_gained") <= 0)),
    "negative_play": ("measured", "after_play", c("yards_gained") < 0),
    "first_down_gained": ("measured", "after_play", c("first_down") == 1),
    "added_win_probability": ("measured", "after_play", c("wpa") > 0),
    "high_leverage": ("measured", "after_play", c("wpa").abs() >= 0.05),
    "turnover": ("measured", "after_play", (c("interception") == 1) | (c("fumble_lost") == 1)),
    "low_percentage_throw": ("measured", "after_play", c("cp") < 0.40),
    "garbage_time_wp": (
        "situation",
        "before_snap",
        ((c("wp") < 0.10) | (c("wp") > 0.90)) & (c("qtr") >= 3),
    ),
    "garbage_time_score": (
        "situation",
        "before_snap",
        ((c("qtr") == 4) & (lead.abs() >= 17)) | ((c("qtr") == 3) & (lead.abs() >= 28)),
    ),
    "neutral_script": (
        "situation",
        "before_snap",
        c("wp").is_between(0.20, 0.80) & (c("half_seconds_remaining") > 120) & (c("qtr") <= 4),
    ),
    "red_zone": ("situation", "before_snap", c("yardline_100") <= 20),
    "goal_to_go": ("situation", "before_snap", c("goal_to_go") == 1),
    "backed_up": ("situation", "before_snap", c("yardline_100") >= 90),
    "money_down": ("situation", "before_snap", c("down") == 3),
    "fourth_down_attempt": ("situation", "before_snap", c("down") == 4),
    "obvious_pass_down": (
        "situation",
        "before_snap",
        ((c("down") == 2) & (c("ydstogo") >= 8)) | (c("down").is_in([3.0, 4.0]) & (c("ydstogo") >= 5)),
    ),
    "short_yardage": ("situation", "before_snap", c("down").is_in([3.0, 4.0]) & (c("ydstogo") <= 2)),
    "two_minute_drill": (
        "situation",
        "before_snap",
        c("qtr").is_in([2.0, 4.0]) & (c("half_seconds_remaining") <= 120) & (lead <= 8),
    ),
    "four_minute_offense": ("situation", "before_snap", q4_late & lead.is_between(1, 16)),
    "middle_eight": (
        "situation",
        "before_snap",
        ((c("qtr") == 2) & (c("half_seconds_remaining") <= 240))
        | ((c("qtr") == 3) & (c("half_seconds_remaining") >= 1560)),
    ),
    "hero_ball": ("lore", "after_play", (c("cp") < 0.35) & (c("air_yards") >= 15)),
    "check_down": (
        "lore",
        "after_play",
        (c("play_type") == "pass") & (c("air_yards") < 2) & (c("qb_scramble") == 0),
    ),
    "scramble_drill": ("lore", "after_play", c("qb_scramble") == 1),
    "coverage_sack": ("lore", "after_season", (c("sack") == 1) & (c("time_to_throw") >= 3.5)),
    "momentum_swing": ("lore", "after_play", (c("wpa").abs() >= 0.10) | (c("turnover_") == 1)),
}

plays = (
    load("play", seasons=SEASONS)
    .filter(scrimmage)
    .with_columns(turnover_=((c("interception") == 1) | (c("fumble_lost") == 1)).cast(pl.Int8))
)
print(f"{plays.height:,} run and pass plays in {SEASONS}")

# Plays that depend on the previous drive or the drive's order.
drives = (
    plays.group_by("game_id", "fixed_drive", "posteam")
    .agg(
        first_play=c("play_id").min(),
        n=pl.len(),
        result=c("fixed_drive_result").first(),
        first_downs=c("first_down").sum(),
        start_qtr=c("qtr").first(),
        end_half_seconds=c("half_seconds_remaining").min(),
        end_qtr=c("qtr").last(),
        goal_inside_5=((c("goal_to_go") == 1) & (c("yardline_100") <= 5) & (c("down") == 1)).any(),
        secs=(c("game_seconds_remaining").max() - c("game_seconds_remaining").min()),
    )
    .sort("game_id", "fixed_drive")
    .with_columns(
        prev_result=c("result").shift(1).over("game_id"),
        prev_team=c("posteam").shift(1).over("game_id"),
    )
)
DRIVE = {
    "scoring_drive": ("measured", c("result").is_in(["Touchdown", "Field goal"])),
    "three_and_out": ("lore", (c("result") == "Punt") & (c("first_downs") == 0)),
    "methodical_drive": ("lore", (c("n") >= 10)),
    "quick_strike": ("lore", (c("result") == "Touchdown") & ((c("n") <= 4) | (c("secs") <= 90))),
    "answer_drive": (
        "lore",
        (c("result") == "Touchdown")
        & (c("prev_result") == "Touchdown")
        & (c("prev_team") != c("posteam")),
    ),
    "sudden_change": ("situation", c("prev_result").is_in(["Turnover", "Opp touchdown"])),
    "goal_line_stand": ("lore", c("goal_inside_5") & (c("result") != "Touchdown")),
    "backbreaker": (
        "lore",
        c("result").is_in(["Touchdown", "Field goal"])
        & (c("end_qtr") == 2)
        & (c("end_half_seconds") <= 120),
    ),
}

opening = plays.with_columns(n_play=pl.int_range(1, pl.len() + 1).over("game_id", "posteam"))

rows = []
for name, (family, known, rule) in PLAY.items():
    applies = plays.select(rule.alias("t"))["t"]
    rows.append((name, "play", family, known, applies.mean(), applies.null_count() / len(applies)))
rows.append(
    ("opening_script", "play", "lore", "before_snap", (opening["n_play"] <= 15).mean(), 0.0)
)
stat_pad = plays.select(
    (PLAY["garbage_time_score"][2] & (lead < 0) & (c("yards_gained") > 0)).alias("t")
)["t"]
rows.append(("stat_padding", "play", "lore", "after_play", stat_pad.mean(), 0.0))
for name, (family, rule) in DRIVE.items():
    applies = drives.select(rule.alias("t"))["t"]
    known = "before_snap" if family == "situation" else "after_play"
    rows.append((name, "drive", family, known, applies.mean(), applies.null_count() / len(applies)))

tg = load("team_game", seasons=SEASONS, parts=["schedule", "pregame", "result"]).filter(
    c("game_type") == "REG"
)
game = load("game", seasons=SEASONS).filter(c("game_type") == "REG").select("game_id", "temp", "wind", "roof")
tg = tg.join(game, on="game_id").sort("team", "kickoff")
tg = tg.with_columns(
    et_hour=c("kickoff").dt.convert_time_zone("America/New_York").dt.hour(),
    next_opp_div=c("div_game").shift(-1).over("team", "season"),
    usual_qb=c("qb_id").mode().first().over("team", "season"),  # prototype only: uses the future
)
TEAM_GAME = {
    "primetime": ("situation", "before_game", c("et_hour") >= 19),
    "short_week": ("situation", "before_game", c("rest") <= 4),
    "off_bye": ("situation", "before_game", c("rest") >= 13),
    "divisional": ("situation", "before_game", c("div_game") == 1),
    "home_underdog": ("situation", "before_game", (c("home") == 1) & (c("spread") > 0)),
    "big_favorite": ("situation", "before_game", c("spread") <= -10),
    "trap_game": ("lore", "before_game", (c("spread") <= -7) & (c("next_opp_div") == 1)),
    "weather_game": (
        "situation",
        "after_game",
        (c("roof").is_in(["outdoors", "open"])) & ((c("temp") <= 32) | (c("wind") >= 15)),
    ),
    "backup_qb_start": ("lore", "before_game", c("qb_id") != c("usual_qb")),
}
for name, (family, known, rule) in TEAM_GAME.items():
    applies = tg.select(rule.alias("t"))["t"]
    rows.append(
        (name, "team_game", family, known, applies.mean(), applies.null_count() / len(applies))
    )

pg = load("player_game", seasons=[2022, *SEASONS]).sort("gsis_id", "season", "week")
prev_team = (
    pg.group_by("gsis_id", "season")
    .agg(last_team=c("team").last())
    .with_columns(season=c("season") + 1)
)
former = pg.select("gsis_id", "season", former=c("team")).unique()
pg = (
    pg.join(prev_team, on=["gsis_id", "season"], how="left")
    .with_columns(prev_status=c("report_status").shift(1).over("gsis_id", "season"))
    .filter(c("season").is_in(SEASONS))
)
revenge = (
    pg.join(former, on="gsis_id", suffix="_f")
    .filter((c("season_f") < c("season")) & (c("former") == c("opponent")) & (c("former") != c("team")))
    .select("gsis_id", "game_id")
    .unique()
)
pg = pg.join(revenge.with_columns(revenge=pl.lit(True)), on=["gsis_id", "game_id"], how="left")
active = c("status") == "ACT"
PLAYER_GAME = {
    "rookie": ("situation", "before_game", c("season") == c("rookie_year")),
    "new_team": ("situation", "before_game", c("last_team").is_not_null() & (c("last_team") != c("team"))),
    "first_game_back": ("situation", "before_game", active & (c("prev_status") == "Out")),
    "active_while_questionable": (
        "situation",
        "before_game",
        active & (c("report_status") == "Questionable"),
    ),
    "revenge_game": ("lore", "before_game", c("revenge").fill_null(False)),
}
for name, (family, known, rule) in PLAYER_GAME.items():
    applies = pg.select(rule.alias("t"))["t"]
    rows.append(
        (name, "player_game", family, known, applies.mean(), applies.null_count() / len(applies))
    )

out = pl.DataFrame(
    rows, schema=["tag", "level", "family", "known", "share", "null_share"], orient="row"
)
print(out.with_columns(c("share", "null_share").round(4)))
print(out.group_by("family").len().sort("family"))

# Two definitions of garbage time: how often do they agree?
g = plays.select(
    wp=PLAY["garbage_time_wp"][2].fill_null(False),
    score=PLAY["garbage_time_score"][2].fill_null(False),
)
print("garbage time, WP rule vs score rule:", g.group_by("wp", "score").len().sort("wp", "score"))
