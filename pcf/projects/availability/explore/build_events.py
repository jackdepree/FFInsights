"""Availability exploration: the shared tables every look reads.

Builds three frames in `<interim>/availability/` (gitignored), 2013-2024 regular seasons only
(the 2025 vault is never read):

- `injuries.parquet`: one row per in-game injury named in the play-by-play ("TEAM-NN-F.Last
  was injured during the play"), matched to a player by team, jersey and last name.
- `player_plays.parquet` (2016-2024, scrimmage plays with who was on the field): one row per
  player-play with the play's features and whether this player was injured on it.
- `player_games.parquet`: one row per rostered player-game (2013-2024), with snaps, whether he
  played, an in-game injury that game, the next week's injury report, age, and the time he
  missed after an injury (games of his team before his next game with a snap, censored at the
  season's end).

Run from pcf/ (the main checkout's venv):
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import re
import sys
import time

import polars as pl

from pcf.config import get_config
from pcf.data.clean import standard

c = pl.col
CFG = get_config()
T = CFG.zone("tables")
OUT = CFG.zone("interim") / "availability"
OUT.mkdir(parents=True, exist_ok=True)
SEASONS = list(range(2013, 2025))
PLAY_SEASONS = list(range(2016, 2025))
T0 = time.time()
INJ = re.compile(r"([A-Z]{2,3})-(\d+)-([A-Za-z\.'\- ]+?) was injured during the play")
TACKLERS = [
    "solo_tackle_1_player_id", "solo_tackle_2_player_id",
    "assist_tackle_1_player_id", "assist_tackle_2_player_id", "assist_tackle_3_player_id", "assist_tackle_4_player_id",
    "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id",
]  # fmt: skip


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, file=sys.stderr, flush=True)


def part(table, name, seasons, cols=None):
    out = []
    for s in seasons:
        f = T / table / name / f"season={s}" / "data.parquet"
        if f.exists():
            out.append(pl.scan_parquet(str(f)).select(cols or pl.all()).collect())
    return pl.concat(out, how="diagonal_relaxed")


def last_name(e):
    return e.str.split(" ").list.last().str.to_lowercase().str.replace_all(r"[^a-z\-']", "")


# ---------------------------------------------------------------- plays
cols = ["game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "play_type", "desc",
        "yards_gained", "pass", "rush", "sack", "qb_hit", "tackled_for_loss", "fumble", "qb_scramble",
        "incomplete_pass", "out_of_bounds", "yards_after_catch", "air_yards", "game_seconds_remaining", "qtr",
        "score_differential", "wp", "yardline_100", "down", *TACKLERS]  # fmt: skip
p = part("play", "pbp", SEASONS, cols).filter(c("season_type") == "REG").drop("season_type")
p = p.with_columns(c("play_id").cast(pl.Int64))
p = standard.standard_teams(p, "posteam").pipe(standard.standard_teams, "defteam")
p = p.sort("game_id", "play_id").with_columns(
    n_tacklers=pl.sum_horizontal([c(x).is_not_null().cast(pl.Int32) for x in TACKLERS]),
    tfl=((c("tackled_for_loss") == 1) | (c("sack") == 1)).cast(pl.Int8),
    # play length on incomplete passes: the clock stops at the play's end and restarts at the next snap
    next_gsr=c("game_seconds_remaining").shift(-1).over("game_id", "qtr"),
)
p = p.with_columns(
    clock_len=pl.when((c("incomplete_pass") == 1) & (c("sack") == 0))
    .then(c("game_seconds_remaining") - c("next_gsr"))
    .otherwise(None)
).drop("next_gsr", *TACKLERS)
log("plays", p.height)

# ---------------------------------------------------------------- in-game injuries
ev = p.filter(c("desc").str.contains("was injured during the play")).select("game_id", "play_id", "season", "week", "play_type", "posteam", "defteam", "desc")
recs = []
for g, pid, s, w, pt, pos, de, d in ev.iter_rows():
    for m in INJ.finditer(d):
        recs.append((g, pid, s, w, pt, m.group(1), int(m.group(2)), m.group(3).split(".")[-1].strip()))
ev = pl.DataFrame(recs, schema=["game_id", "play_id", "season", "week", "play_type", "inj_team", "jersey", "last"], orient="row")
ev = standard.standard_teams(ev, "inj_team").with_columns(last=last_name(c("last")))
n_named = ev.height
ro = part("player_game", "roster", SEASONS, ["gsis_id", "game_id", "season", "week", "team", "position", "jersey_number", "full_name", "birth_date"])
ro = ro.with_columns(jersey=c("jersey_number").cast(pl.Int64, strict=False), last=last_name(c("full_name")))
ev = ev.join(
    ro.select("gsis_id", "game_id", "team", "jersey", "last", "position"),
    left_on=["game_id", "inj_team", "jersey", "last"], right_on=["game_id", "team", "jersey", "last"], how="left",
)
log("injuries named", n_named, "matched", ev.filter(c("gsis_id").is_not_null()).height)
by_season = ev.group_by("season").agg(named=pl.len(), matched=c("gsis_id").is_not_null().sum()).sort("season")
print(by_season)
ev = ev.filter(c("gsis_id").is_not_null()).unique(["game_id", "gsis_id"], keep="first").rename({"inj_team": "team"})
ev.write_parquet(OUT / "injuries.parquet")

# ---------------------------------------------------------------- player-plays (2016 on)
on = part("player_play", "on_field", PLAY_SEASONS, ["game_id", "play_id", "side", "team", "gsis_id"]).unique(["game_id", "play_id", "gsis_id"])
on = standard.standard_teams(on, "team").with_columns(c("play_id").cast(pl.Int64))
pp = on.join(p.drop("desc"), on=["game_id", "play_id"], how="inner")
pp = pp.join(ev.select("game_id", "play_id", "gsis_id", injured=pl.lit(1, pl.Int8)), on=["game_id", "play_id", "gsis_id"], how="left").with_columns(c("injured").fill_null(0))
pp = pp.join(ro.select("gsis_id", "game_id", "position", "birth_date"), on=["gsis_id", "game_id"], how="left")
pp = pp.with_columns(group=pl.when(c("position").is_in(["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"])).then(c("position")).otherwise(None))
pp.write_parquet(OUT / "player_plays.parquet")
log("player-plays", pp.height, "injured", int(pp["injured"].sum()), "of", ev.filter(c("season") >= 2016).height)

# ---------------------------------------------------------------- player-games
sn = part("player_game", "snaps", SEASONS, ["gsis_id", "game_id", "offense_snaps", "defense_snaps", "st_snaps"])
inj = part("player_game", "injury", SEASONS, ["gsis_id", "game_id", "report_primary_injury", "report_status", "practice_status"])
sched = ro.select("game_id", "season", "week", "team").unique().sort("team", "season", "week")
sched = sched.with_columns(gi=c("week").rank("ordinal").over("team", "season").cast(pl.Int32), n_games=pl.len().over("team", "season").cast(pl.Int32))
pg = ro.select("gsis_id", "game_id", "season", "week", "team", "position", "birth_date").join(sched.select("game_id", "team", "gi", "n_games"), on=["game_id", "team"])
pg = pg.join(sn, on=["gsis_id", "game_id"], how="left").with_columns([c(x).fill_null(0) for x in ["offense_snaps", "defense_snaps", "st_snaps"]])
pg = pg.with_columns(played=((c("offense_snaps") + c("defense_snaps") + c("st_snaps")) > 0).cast(pl.Int8))
pg = pg.join(inj, on=["gsis_id", "game_id"], how="left")
pg = pg.join(ev.select("gsis_id", "game_id", inj_play=c("play_id"), inj_type=c("play_type")), on=["gsis_id", "game_id"], how="left").with_columns(hurt=c("inj_play").is_not_null().cast(pl.Int8))
pg = pg.with_columns(age=((pl.date(c("season"), 9, 1) - c("birth_date").cast(pl.Date)).dt.total_days() / 365.25))

# Time missed: games of his team after the injury game before his next game with a snap (any team), within the season.
played = pg.filter(c("played") == 1).select("gsis_id", "season", "week").sort("gsis_id", "season", "week")
hurt = pg.filter(c("hurt") == 1).select("gsis_id", "game_id", "season", "week", "team", "gi", "n_games")
nxt = hurt.join(played.rename({"week": "pw"}), on=["gsis_id", "season"], how="left").filter(c("pw") > c("week")).group_by("gsis_id", "game_id").agg(next_week=c("pw").min())
hurt = hurt.join(nxt, on=["gsis_id", "game_id"], how="left")
hurt = hurt.join(sched.select("team", "season", "week", gi_next=c("gi")), left_on=["team", "season", "next_week"], right_on=["team", "season", "week"], how="left")
hurt = hurt.with_columns(
    censored=c("next_week").is_null(),
    # if he returned with another team in a week his old team didn't play, count by weeks
    missed=pl.when(c("next_week").is_null()).then(c("n_games") - c("gi"))
    .when(c("gi_next").is_not_null()).then(c("gi_next") - c("gi") - 1)
    .otherwise(c("next_week") - c("week") - 1),
)
pg = pg.join(hurt.select("gsis_id", "game_id", "missed", "censored"), on=["gsis_id", "game_id"], how="left")
# the next game's report for the injured (body part, status), from his next team-game
rep = pg.select("gsis_id", "season", "team", "gi", nr_part=c("report_primary_injury"), nr_status=c("report_status"))
pg = pg.join(rep.with_columns(gi=c("gi") - 1), on=["gsis_id", "season", "team", "gi"], how="left")
pg.write_parquet(OUT / "player_games.parquet")
log("player-games", pg.height, "hurt", int(pg["hurt"].sum()))
print(pg.filter(c("hurt") == 1).group_by("position").agg(n=pl.len(), missed_mean=c("missed").mean(), missed_med=c("missed").median(), cens=c("censored").mean(), zero=(c("missed") == 0).mean()).sort("n", descending=True))
print(pg.filter(c("hurt") == 1)["nr_part"].value_counts().sort("count", descending=True).head(15))
