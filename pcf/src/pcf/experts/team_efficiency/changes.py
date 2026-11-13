"""Season-start changes for P3, the weaker pull (team-efficiency#F16; IDEAS I36, I38; the CEO's
pick, 2026-11-13): did a team start the season with a new quarterback or a new head coach?

- **New QB:** the QB1 on the depth chart for the team's first regular-season game isn't the QB
  who started most of its regular-season games last season (`team_game.pregame.qb_id`; ties go
  to the later start). Round two used last season's main passer by dropbacks from play-by-play;
  starts say the same thing from a team-game part.
- **New coach:** the head coach for the first regular-season game (`team_game.opening_coach`)
  isn't the coach of last season's final regular-season game (a mid-season hire who stays is
  not new).
- **Known at:** when both this season's facts are known: the opening coach (the start of week 1)
  and the week-1 depth chart (the start of its week). Last season's starts and coaches are known
  long before. A missing side counts as no change, as in round two.

Only the experts' inputs are read (the gateway's views). A later project on in-season QB changes
(IDEAS I37) could lift this into the shared package.
"""

from __future__ import annotations

import polars as pl

c = pl.col
INPUTS = {
    "team_game": ("schedule", "pregame", "opening_coach"),
    "player_game": ("roster", "depth"),
}
COLUMNS = ["season", "team", "new_qb", "new_coach", "known_at"]


def _last_season(tg: pl.DataFrame) -> pl.DataFrame:
    """Per team and following season: last season's most-started QB and its final coach."""
    reg = tg.filter((c("game_type") == "REG") & c("pregame_known_at").is_not_null())
    starts = (
        reg.drop_nulls("qb_id")
        .group_by("season", "team", "qb_id")
        .agg(n=pl.len(), last=c("week").max())
        .sort("n", "last", descending=True)
        .group_by("season", "team", maintain_order=True)
        .first()
        .select("season", "team", last_qb="qb_id")
    )
    coach = (
        reg.drop_nulls("coach")
        .sort("week")
        .group_by("season", "team")
        .last()
        .select("season", "team", last_coach="coach")
    )
    return starts.join(coach, on=["season", "team"], how="full", coalesce=True).with_columns(
        c("season") + 1
    )


def _opening_qb(tg: pl.DataFrame, pg: pl.DataFrame) -> pl.DataFrame:
    """Per season and team: QB1 on the depth chart for its first regular-season game."""
    reg = tg.filter(c("game_type") == "REG").select("game_id", "season", "team", "week")
    opener = reg.group_by("season", "team").agg(c("week").min())
    first = reg.join(opener, on=["season", "team", "week"])
    qbs = pg.filter((c("depth_position") == "QB") & c("depth_known_at").is_not_null()).select(
        "gsis_id", "game_id", "team", "depth", "depth_mean", "depth_known_at"
    )
    return (
        first.join(qbs, on=["game_id", "team"])
        .sort("depth", "depth_mean", "gsis_id")
        .group_by("season", "team", maintain_order=True)
        .first()
        .select("season", "team", qb1="gsis_id", qb_known_at="depth_known_at")
    )


def season_changes(tg: pl.DataFrame, pg: pl.DataFrame) -> pl.DataFrame:
    """season, team, new_qb, new_coach (0/1) and known_at, for every season with an opening coach.
    `tg`: a team_game view with schedule, pregame, opening_coach; `pg`: player_game with roster
    and depth."""
    opening = (
        tg.filter(c("opening_coach").is_not_null())
        .select("season", "team", "opening_coach", coach_known_at="opening_coach_known_at")
        .unique(["season", "team"])
    )
    x = opening.join(_last_season(tg), on=["season", "team"], how="left").join(
        _opening_qb(tg, pg), on=["season", "team"], how="left"
    )
    return x.select(
        c("season").cast(pl.Int32),
        "team",
        new_qb=(c("qb1") != c("last_qb")).fill_null(False).cast(pl.Float64),
        new_coach=(c("opening_coach") != c("last_coach")).fill_null(False).cast(pl.Float64),
        known_at=pl.max_horizontal("coach_known_at", "qb_known_at"),
    ).sort("season", "team")
