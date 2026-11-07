"""H1: is it the same team this week? (elo exploration F14, F15.)

Per team per game, from the team's previous games this season:
- a player's **usual share** is their average offense and defense snap share over the team's last
  (up to) 4 games whose snap counts were known at the moment;
- they're **missing** if they aren't on this game's roster, or the injury report known at the
  moment lists them Out or Doubtful;
- **same-team share:** the usual shares of the available players over all usual shares, offense and
  defense averaged (1 when there's no history: week 1, or seasons before snap counts);
- **usual QB missing:** the QB with the highest usual offense share (ties by gsis_id) is missing,
  if that share is above 0.

Rows are filtered by their own `known_at` against each game's moment here, so one call over the
whole history (the bulk features) gives what each moment's view would.
"""

from __future__ import annotations

import polars as pl

c = pl.col
USUAL_GAMES = 4
OUT = ("Out", "Doubtful")
NEED = (
    "gsis_id", "game_id", "season", "week", "team", "position", "known_at",
    "offense_pct", "defense_pct", "snaps_known_at", "report_status", "injury_known_at",
)  # fmt: skip


def same_team(pg: pl.DataFrame, kickoffs: pl.DataFrame, targets: pl.DataFrame) -> pl.DataFrame:
    """`pg`: player-game rows (roster spine with snaps and injury parts, `NEED`). `kickoffs`:
    game_id and kickoff for every game in `pg`. `targets`: the games to describe, with game_id
    and `moment`. Returns game_id, team, share and qb_out for both teams of every target."""
    # the team-games of these seasons, numbered in kickoff order
    tg = (
        pg.select("game_id", "season", "team")
        .unique()
        .join(kickoffs.select("game_id", "kickoff"), on="game_id", how="left")
    )
    if tg["kickoff"].null_count():
        raise ValueError("same_team: every player-game's game needs a kickoff")
    tg = tg.with_columns(n=c("kickoff").rank("ordinal").over("season", "team").cast(pl.Int32))
    targets = (
        targets.select("game_id", "moment")
        .join(tg, on="game_id")
        .select("game_id", "season", "team", "n", "moment")
    )
    rows = pg.join(tg.select("game_id", "team", "n"), on=["game_id", "team"])

    # usual shares: each target's previous games, snap counts known by its moment
    hist = (
        targets.join(
            rows.select(
                "season",
                "team",
                "gsis_id",
                "position",
                "offense_pct",
                "defense_pct",
                "snaps_known_at",
                past="n",
            ),
            on=["season", "team"],
        )  # fmt: skip
        .filter(
            c("past").is_between(c("n") - USUAL_GAMES, c("n") - 1)
            & c("snaps_known_at").is_not_null()
            & (c("snaps_known_at") <= c("moment"))
        )
        .with_columns(c("offense_pct", "defense_pct").fill_null(0.0))
    )
    k = hist.group_by("game_id", "team").agg(k=c("past").n_unique())
    usual = (
        hist.group_by("game_id", "team", "gsis_id")
        .agg(
            off=c("offense_pct").sum(), de=c("defense_pct").sum(), qb=(c("position") == "QB").any()
        )
        .join(k, on=["game_id", "team"])
        .with_columns(off=c("off") / c("k"), de=c("de") / c("k"))
    )
    # this game: on the roster (known by the moment) and not ruled out by a known report
    now = (
        rows.join(targets.select("game_id", "team", "moment"), on=["game_id", "team"])
        .filter(c("known_at") <= c("moment"))
        .with_columns(
            out=c("report_status").is_in(list(OUT)).fill_null(False)
            & c("injury_known_at").is_not_null()
            & (c("injury_known_at") <= c("moment"))
        )
        .group_by("game_id", "team", "gsis_id")
        .agg(out=c("out").any())
    )
    u = usual.join(now, on=["game_id", "team", "gsis_id"], how="left").with_columns(
        avail=~c("out").fill_null(True)  # not on this game's roster: missing
    )
    share = u.group_by("game_id", "team").agg(
        off_all=c("off").sum(),
        off_av=(c("off") * c("avail")).sum(),
        de_all=c("de").sum(),
        de_av=(c("de") * c("avail")).sum(),
    )
    qb = (
        u.filter(c("qb"))
        .sort(["off", "gsis_id"], descending=[True, False])
        .group_by("game_id", "team", maintain_order=True)
        .first()
        .select("game_id", "team", qb_out=((c("off") > 0) & ~c("avail")).cast(pl.Float64))
    )
    part = lambda a, b: pl.when(c(a) > 0).then(c(b) / c(a)).otherwise(1.0)  # noqa: E731
    return (
        targets.select("game_id", "team")
        .join(share, on=["game_id", "team"], how="left")
        .join(qb, on=["game_id", "team"], how="left")
        .select(
            "game_id",
            "team",
            share=((part("off_all", "off_av") + part("de_all", "de_av")) / 2).fill_null(1.0),
            qb_out=c("qb_out").fill_null(0.0),
        )
        .sort("game_id", "team")
    )
