"""Availability's outcomes, from the view at the end of time (decision 0047).

- `next_absent`: whether each 53-man roster player-game was a health absence (no snap while
  listed), known when the game's snap counts are.
- `window_absent`: health absences over a window of the team's games starting with this one
  (the next 3, or the rest of the regular season), for every roster_week row, counted by week
  on any team (a traded player is followed); a week on no roster counts 0 (participation's).
  Known the day after the window's last game.
- `active`: participation's own outcome (active on game day; before 2019, a snap-count row), for
  the head-to-head with participation's `active` (the brief's test 1).
- `side_share`: his snap share on his side when he played (the kept-share outcome).
"""

from __future__ import annotations

import polars as pl

from pcf.experts.availability.common import FIRST_HISTORY, FIRST_TRAIN, schedule, timeline

c = pl.col
ONE_DAY = pl.duration(days=1)


def _seasons(view) -> list[int]:
    tg = view.table("team_game")
    return sorted(s for s in tg["season"].unique().to_list() if s >= FIRST_HISTORY)


def _record(view) -> tuple[pl.DataFrame, pl.DataFrame]:
    seasons = _seasons(view)
    sched = schedule(view, seasons)
    tl = timeline(view, max(seasons), sched)
    return tl.filter(c("season") >= FIRST_TRAIN), sched


def next_absent(view) -> pl.DataFrame:
    tl, sched = _record(view)
    known = sched.select("game_id", "team", known_at=c("kickoff") + ONE_DAY)
    return (
        tl.filter(~c("reserve"))
        .join(known, on=["game_id", "team"])
        .select("gsis_id", "game_id", y=c("absent").cast(pl.Float64), known_at="known_at")
    )


def window_absent(view, n: int | None) -> pl.DataFrame:
    """`n` games from this one (None: the rest of the season)."""
    tl, sched = _record(view)
    weekly = tl.group_by("gsis_id", "season", "week").agg(c("absent").any().cast(pl.Float64))
    rw = view.table("roster_week").filter(c("season") >= FIRST_TRAIN)
    rows = rw.join(sched.select("game_id", "team", "gi", "n_games"), on=["game_id", "team"])
    rows = rows.select("gsis_id", "game_id", "team", "season", "gi", "n_games")
    games = sched.select("team", "season", w_gi="gi", w_week="week", w_kick="kickoff")
    win = rows.join(games, on=["team", "season"]).filter(
        (c("w_gi") >= c("gi")) & ((c("w_gi") < c("gi") + n) if n else pl.lit(True))
    )
    win = win.join(
        weekly.rename({"week": "w_week"}), on=["gsis_id", "season", "w_week"], how="left"
    )
    out = win.group_by("gsis_id", "game_id").agg(
        y=c("absent").fill_null(0.0).sum(),
        n_window=pl.len(),
        known_at=c("w_kick").max() + ONE_DAY,
    )
    return out.select("gsis_id", "game_id", "y", "known_at")


def active(view) -> pl.DataFrame:
    """Participation's outcome on its rows (QB, RB, WR, TE)."""
    pg = view.table("player_game").filter(c("season") >= FIRST_TRAIN)
    pg = pg.with_columns(k=c("snaps_known_at").max().over("game_id")).filter(c("k").is_not_null())
    act = (
        pl.when(c("status").is_not_null())
        .then(c("status") != "INA")
        .otherwise(c("offense_snaps").is_not_null())
    )
    return pg.filter(c("position").is_in(["QB", "RB", "WR", "TE"])).select(
        "gsis_id", "game_id", y=act.cast(pl.Float64), known_at="k"
    )


def side_share(view) -> pl.DataFrame:
    """His offensive share when he took an offensive snap (QB, RB, WR, TE): the kept share's
    outcome, in participation's unit."""
    pg = view.table("player_game").filter(c("season") >= FIRST_TRAIN)
    pg = pg.with_columns(k=c("snaps_known_at").max().over("game_id")).filter(c("k").is_not_null())
    return pg.filter(
        c("position").is_in(["QB", "RB", "WR", "TE"]) & (c("offense_snaps").fill_null(0) > 0)
    ).select("gsis_id", "game_id", y=c("offense_pct").cast(pl.Float64), known_at="k")
