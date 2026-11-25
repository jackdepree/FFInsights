"""The availability parts (availability's build, decision 0047): who is on a reserve list each
week, and the in-game injuries the play-by-play names.

- `roster_week.status` (a new table, its spine): every player on a team's 53-man roster or on a
  reserve list for injury, illness or non-football injury, for each of the team's games, 2016 on
  (weekly roster statuses start in 2016: grain-tables#F11). `player_game`'s spine leaves the
  reserve lists out, so without this an injured-reserve stint can't be seen. Known at the start
  of the week, like `player_game`'s spine. Its `status` is ACT, INA or a reserve status; read
  ACT against INA from `player_game.game_status`, which is known only an hour before kickoff.
- `player_game.injured`: one row per player-game with an in-game injury named in the
  play-by-play ("BAL-71-J.James was injured during the play"), matched to a player by team,
  jersey and last name (decision 0044, call 1). Known the day after the game, like the
  play-by-play.

Both builders are pure: `build.build_roster_week` reads their inputs and writes the parts.
"""

from __future__ import annotations

import re

import polars as pl

from pcf.data.clean import standard

c = pl.col
FIRST_SEASON = 2016  # weekly roster statuses (grain-tables#F11)
FIRST_INJURED = 2013  # the exploration's first season of named injuries
# Reserve lists that are about health: injured reserve (with its designated-to-return code),
# physically unable to perform, and non-football injury (decision 0047). A retired player's
# reserve code (R02) isn't health.
RESERVE = ("RES", "PUP", "RSN")
NOT_HEALTH_CODES = ("R02",)
ON_ROSTER = ("ACT", "INA", *RESERVE)
STATUS_ORDER = {s: i for i, s in enumerate(ON_ROSTER)}  # a player listed twice: active first
INJURED = re.compile(r"([A-Z]{2,3})-(\d+)-([A-Za-z\.'\- ]+?) was injured during the play")
PBP_COLUMNS = ["game_id", "play_id", "season", "week", "season_type", "play_type", "desc"]


def roster_week_rows(rosters: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    """Weekly rosters (cleaned by `standard.weekly_rosters`, with `known_at`) → one row per player
    and team-game: gsis_id, game_id, season, week, team, position, status, status_code, reserve,
    known_at. `games` is one row per team and game (`frames.team_games`)."""
    keep = rosters.filter(
        c("gsis_id").is_not_null()
        & c("status").is_in(list(ON_ROSTER))
        & ~c("status_description_abbr").fill_null("").is_in(list(NOT_HEALTH_CODES))
    )
    keep = keep.with_columns(c("season").cast(pl.Int32), c("week").cast(pl.Int32))
    out = keep.join(games.select("game_id", "season", "week", "team"), on=["season", "week", "team"])
    return (
        out.with_columns(order=c("status").replace_strict(STATUS_ORDER, return_dtype=pl.Int32))
        .sort("order")
        .unique(["gsis_id", "game_id"], keep="first")
        .select(
            "gsis_id", "game_id", "season", "week", "team", "position", "status",
            status_code="status_description_abbr",
            reserve=c("status").is_in(list(RESERVE)),
            known_at="known_at",
        )  # fmt: skip
        .sort("season", "week", "team", "gsis_id")
    )


def _last_name(e: pl.Expr) -> pl.Expr:
    return e.str.split(" ").list.last().str.to_lowercase().str.replace_all(r"[^a-z\-']", "")


def injured_rows(pbp: pl.DataFrame, roster: pl.DataFrame) -> pl.DataFrame:
    """The play-by-play (PBP_COLUMNS, regular and post season) and `player_game.roster` → one
    row per player-game with a named in-game injury: gsis_id, game_id, season, injured_play
    (the first such play), injured_play_type, n_injured (named plays that game). The match is
    by team, jersey and last name; unmatched names are dropped (1.2% in the exploration)."""
    named = pbp.filter(c("desc").str.contains("was injured during the play"))
    recs = []
    for g, pid, s, pt, d in named.select("game_id", "play_id", "season", "play_type", "desc").iter_rows():
        for m in INJURED.finditer(d or ""):
            recs.append((g, int(pid), int(s), pt, m.group(1), int(m.group(2)),
                         m.group(3).split(".")[-1].strip()))  # fmt: skip
    schema = {"game_id": pl.String, "play_id": pl.Int64, "season": pl.Int32,
              "play_type": pl.String, "team": pl.String, "jersey": pl.Int64, "last": pl.String}  # fmt: skip
    ev = pl.DataFrame(recs, schema=schema, orient="row")
    ev = standard.standard_teams(ev, "team").with_columns(last=_last_name(c("last")))
    ro = roster.select(
        "gsis_id", "game_id", "team",
        jersey=c("jersey_number").cast(pl.Int64, strict=False),
        last=_last_name(c("full_name")),
    )  # fmt: skip
    ev = ev.join(ro, on=["game_id", "team", "jersey", "last"], how="inner")
    return (
        ev.sort("play_id")
        .group_by("gsis_id", "game_id")
        .agg(
            c("season").first(),
            injured_play=c("play_id").first(),
            injured_play_type=c("play_type").first(),
            n_injured=pl.len().cast(pl.Int32),
        )
        .sort("season", "game_id", "gsis_id")
    )
