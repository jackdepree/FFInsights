"""The build's inputs, read once through the gateway and cached (decision 0050, call 1).

- `player_games()`: one row per player-team-game he played (any snap on his side) in the five
  groups, regular season 2013-2024: snaps, snap share (0-1), targets, carries, his team's targets
  and carries that game (every player), target and carry share. Known the day after the game.
- `team_games()`: every regular-season team-game: game_id, team, season, week, kickoff, and the
  head coach at kickoff (`opening_coach`).
- `report()`: the final injury report's game status per player-game (known by the Saturday run).
- `on_roster()`: who was on each team's 53 or a reserve list that week (`roster_week`, 2016 on;
  known at the start of the week).
- `chances()`: availability's walk-forward chance he plays next game (1 - p_health_absent, the
  pinned `next_logit` history, 2017 on), with its `as_of`.
- `participation()` / `opportunity()`: participation's next-game share if he plays (trees_week's
  if_nonzero_mean) and opportunity-quality's next-game expected points (eff_trees), for the
  obvious-input check; both pinned walk-forward histories.

The 2025 vault stays closed: nothing here reads a season after `LAST`.
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.vacated_opportunity import common as K

c = pl.col
SEASONS = tuple(range(K.FIRST, K.LAST + 1))
UPSTREAM = {
    "availability/next_logit": 1,
    "participation/trees_week": 1,
    "opportunity-quality/eff_trees": 1,
    "participation/lasso_rest": 1,
    "opportunity-quality/eff_rest": 1,
    "roles-archetypes": 1,
}


def _view(seasons: Sequence[int], inputs: dict):
    return Gateway(TableSource(seasons=list(seasons))).view(END_OF_TIME, "retrospective", inputs)


def _cached(name: str, build, refresh: bool = False) -> pl.DataFrame:
    path = K.cache_dir() / f"{name}.parquet"
    if refresh or not path.exists():
        df = build()
        df.write_parquet(path)
        return df
    return pl.read_parquet(path)


def _build_team_games() -> pl.DataFrame:
    v = _view(SEASONS, {"team_game": ("schedule", "opening_coach")})
    tg = v.table("team_game", seasons=SEASONS)
    return (
        tg.filter(c("game_type") == "REG")
        .select("game_id", "team", "season", "week", "kickoff", coach="opening_coach")
        .unique(["game_id", "team"])
        .sort("team", "season", "week")
    )


def team_games(refresh: bool = False) -> pl.DataFrame:
    return _cached("team_games", _build_team_games, refresh)


def _build_player_games() -> pl.DataFrame:
    reg = team_games().select("game_id", "team")
    out = []
    for s in SEASONS:
        v = _view([s], {"player_game": ("roster", "snaps", "stats")})
        pg = v.table("player_game", seasons=[s])
        pg = pg.join(reg, on=["game_id", "team"], how="semi")
        tt = pg.group_by("game_id", "team").agg(
            team_targets=c("targets").fill_null(0).sum(),
            team_carries=c("carries").fill_null(0).sum(),
        )
        g = pg.with_columns(group=c("position").replace_strict(K.GROUP, default=None)).filter(
            c("group").is_not_null()
        )
        off = c("group").is_in(list(K.OFFENSE))
        g = g.with_columns(
            snaps=pl.when(off).then(c("offense_snaps")).otherwise(c("defense_snaps")).fill_null(0),
            share=pl.when(off).then(c("offense_pct")).otherwise(c("defense_pct")).fill_null(0.0),
            targets=c("targets").fill_null(0),
            carries=c("carries").fill_null(0),
        ).filter(c("snaps") > 0)
        g = g.join(tt, on=["game_id", "team"], how="left")
        out.append(
            g.select(
                "gsis_id", "game_id", "season", "week", "team", "group", "draft_number",
                "entry_year", c("snaps").cast(pl.Float64), c("share").cast(pl.Float64),
                c("targets").cast(pl.Float64), c("carries").cast(pl.Float64),
                c("team_targets").cast(pl.Float64), c("team_carries").cast(pl.Float64),
            ).unique(["gsis_id", "game_id"])
        )  # fmt: skip
    g = pl.concat(out, how="diagonal_relaxed")
    if g["share"].max() > 1.5:  # PFR's percent
        g = g.with_columns(share=c("share") / 100)
    g = g.with_columns(
        tgt_share=c("targets") / c("team_targets").clip(1),
        car_share=c("carries") / c("team_carries").clip(1),
    )
    return g.sort("team", "season", "week", "gsis_id")


def player_games(refresh: bool = False) -> pl.DataFrame:
    return _cached("player_games", _build_player_games, refresh)


def _build_report() -> pl.DataFrame:
    out = []
    for s in SEASONS:
        v = _view([s], {"player_game": ("roster", "injury")})
        pg = v.table("player_game", seasons=[s])
        out.append(
            pg.select("gsis_id", "game_id", "team", status="report_status").drop_nulls("status")
        )
    return pl.concat(out).unique(["gsis_id", "game_id"])


def report(refresh: bool = False) -> pl.DataFrame:
    return _cached("report", _build_report, refresh)


def _build_on_roster() -> pl.DataFrame:
    seasons = [s for s in SEASONS if s >= 2016]
    v = _view(seasons, {"roster_week": ("status",)})
    rw = v.table("roster_week", seasons=seasons)
    return rw.select("gsis_id", "team", "season", "week", "status", "reserve").unique(
        ["gsis_id", "team", "season", "week"]
    )


def on_roster(refresh: bool = False) -> pl.DataFrame:
    return _cached("on_roster", _build_on_roster, refresh)


def _output(name: str) -> pl.DataFrame:
    return _view(SEASONS, {name: UPSTREAM[name]}).output(name)


def chances(refresh: bool = False) -> pl.DataFrame:
    def build():
        h = _output("availability/next_logit").filter(c("quantity") == "p_health_absent")
        return h.select("gsis_id", "game_id", "as_of", p_play=1 - c("mean"))

    return _cached("chances", build, refresh)


def participation(refresh: bool = False) -> pl.DataFrame:
    def build():
        h = _output("participation/trees_week").filter(c("quantity") == "snap_share")
        return h.select("gsis_id", "game_id", "as_of", part_if=c("if_nonzero_mean"),
                        part_mean=c("mean"))  # fmt: skip

    return _cached("participation", build, refresh)


def opportunity(refresh: bool = False) -> pl.DataFrame:
    def build():
        h = _output("opportunity-quality/eff_trees")
        return h.select("gsis_id", "game_id", "as_of", oq_if=c("if_nonzero_mean"))

    return _cached("opportunity", build, refresh)


def season_incumbents(refresh: bool = False) -> pl.DataFrame:
    """Participation's rest-of-season share (lasso_rest) and opportunity-quality's rest-of-season
    expected points (eff_rest) at each player's first game window of a season (the offseason
    expert's obvious inputs)."""

    def build():
        p = (
            _output("participation/lasso_rest")
            .filter(c("quantity").str.contains("share"))
            .select("gsis_id", "game_id", part_rest="mean")
        )
        o = _output("opportunity-quality/eff_rest").select("gsis_id", "game_id", oq_rest="mean")
        return p.join(o, on=["gsis_id", "game_id"], how="full", coalesce=True)

    return _cached("season_incumbents", build, refresh)


def roles(refresh: bool = False) -> pl.DataFrame:
    """Roles' walk-forward role table per offensive player-team-season (t0-t5), standardized
    within season."""

    def build():
        h = (
            _view(SEASONS, {"roles-archetypes": 1})
            .output("roles-archetypes")
            .filter(c("side") == "offense")
        )
        cols = [
            "t0_snap_share",
            "t1_tgt_per_pass",
            "t2_car_per_run",
            "t3_adot",
            "t4_adj_run",
            "t5_adj_p11",
        ]
        h = h.select("gsis_id", "team", "season", *cols)
        return h.with_columns([((c(x) - c(x).mean().over("season")) / c(x).std().over("season")).fill_null(0.0)
                               for x in cols])  # fmt: skip

    return _cached("roles", build, refresh)
