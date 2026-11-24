"""What the touchdown models share: a view's known player-games and team-games, from the
`touchdowns` parts.

- A rostered QB, RB, WR or TE in a game with play-by-play has a row; no chances means 0.
- **Played:** he had a chance, a throw or an offensive snap. Next game's forecasts assume he plays
  (the brief: whether he does is participation's), so only games he played have an outcome.
- A team's touchdowns are its rushing and receiving touchdowns, by any player (nearly every
  offensive touchdown; a fumble recovered in the end zone isn't a chance).
"""

from __future__ import annotations

import polars as pl

c = pl.col
POSITIONS = ("QB", "RB", "WR", "TE")
FIRST_SEASON = 2013  # participation's feature code starts with the snap counts (2013)
FIRST_XTD = 2012  # the first season with expected touchdowns (the touchdown parts)
KNOWN = "touchdowns_known_at"


def _f(name: str) -> pl.Expr:
    return c(name).fill_null(0).cast(pl.Float64)


def known_player_games(pg: pl.DataFrame) -> pl.DataFrame:
    """A view's QB, RB, WR and TE player-games with known touchdown parts, oldest first: keys,
    season, week, team, position, his touchdowns and expected touchdowns (rushing + receiving:
    `td`, `xtd`, `var`; thrown: `thrown_*`), chances by kind and near the goal line, yards,
    snaps, and whether he played."""
    return (
        pg.filter(c(KNOWN).is_not_null() & c("position").is_in(POSITIONS))
        .select(
            "gsis_id", "game_id", "season", "week", "team", "position",
            td=_f("tdx_td"), xtd=_f("tdx_xtd"), var=_f("tdx_var"),
            rush_td=_f("tdx_rush_td"), rec_td=_f("tdx_rec_td"),
            rush_xtd=_f("tdx_rush_xtd"), rec_xtd=_f("tdx_rec_xtd"),
            carries=_f("tdx_carries"), targets=_f("tdx_targets"),
            chances=_f("tdx_carries") + _f("tdx_targets"),
            rz=_f("tdx_rz_carries") + _f("tdx_rz_targets"),
            i10=_f("tdx_i10_carries") + _f("tdx_i10_targets"),
            gl=_f("tdx_gl_carries"), ez=_f("tdx_ez_targets"), rz_carries=_f("tdx_rz_carries"),
            throws=_f("tdx_throws"), thrown_td=_f("tdx_thrown_td"),
            thrown_xtd=_f("tdx_thrown_xtd"), thrown_var=_f("tdx_thrown_var"),
            rz_throws=_f("tdx_rz_throws"),
            yards=_f("rushing_yards") + _f("receiving_yards"), pass_yards=_f("passing_yards"),
            snaps=_f("offense_snaps"),
            known_at=KNOWN,
        )  # fmt: skip
        .with_columns(played=(c("chances") > 0) | (c("throws") > 0) | (c("snaps") > 0))
        .sort("gsis_id", "season", "week")
    )


def known_team_games(tg: pl.DataFrame) -> pl.DataFrame:
    """A view's team-games with known touchdown parts, oldest first: keys, season, week, team,
    opponent, its touchdowns, expected touchdowns, drive-aware hindsight, red-zone trips, drives,
    calling inside the 10, and its offense's EPA a play (`team_game.efficiency`)."""
    return (
        tg.filter(c(KNOWN).is_not_null())
        .select(
            "game_id", "team", "season", "week", "opponent",
            td=_f("tdx_tds"), xtd=_f("tdx_xtd"), var=_f("tdx_var"),
            hind=_f("tdx_hind"), hind_var=_f("tdx_hind_var"),
            rz_trips=_f("tdx_rz_trips"), drives=_f("tdx_drives"), chances=_f("tdx_chances"),
            i10_targets=_f("tdx_i10_targets"), i10_carries=_f("tdx_i10_carries"),
            rec_td=_f("tdx_rec_td"), near_miss=_f("tdx_near_miss"),
            fg_drives=_f("tdx_fg_drives"),
            epa=_f("eff_epa"), plays=_f("eff_plays"),
            pass_oe=c("neutral_pass_oe").cast(pl.Float64),
            known_at=KNOWN,
        )  # fmt: skip
        .sort("team", "season", "week")
    )
