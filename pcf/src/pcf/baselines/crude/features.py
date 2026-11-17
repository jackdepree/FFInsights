"""The crude forecaster's inputs (crude-forecaster brief): simple, visible numbers from earlier
games, plus each finished expert's saved walk-forward forecast for the same game.

Crude inputs, per unit (a player; a team's offense; a team's defense), from games known before
the moment: the average of yards, attempts, first downs and touchdowns this season, over the last
4 games and last season; the season's running total of yards; last 4 minus the season (the CEO's
"difference in trends"); the game-to-game spread of yards; yards per attempt; games so far.

Expert inputs come from the experts' pinned histories through the gateway (rule e), all made at
the Saturday run (Thursday games at the Thursday run), the forecaster's own moment.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import polars as pl

c = pl.col


# Which stats make each target (CEO's design: five targets; team yards allowed is the mirror of
# yards gained, `allowed`). Positions are the exploration's: rushing is RBs' (QB rushing is
# a separate idea, I67), receiving WRs', TEs' and RBs'.
@dataclass(frozen=True)
class Target:
    name: str
    yards: str
    volume: str
    first_downs: str
    tds: str
    positions: tuple[str, ...] = ()


PASSING = Target(
    "passing", "passing_yards", "attempts", "passing_first_downs", "passing_tds", ("QB",)
)
RUSHING = Target(
    "rushing", "rushing_yards", "carries", "rushing_first_downs", "rushing_tds", ("RB",)
)
RECEIVING = Target(
    "receiving", "receiving_yards", "targets", "receiving_first_downs", "receiving_tds",
    ("WR", "TE", "RB"),
)  # fmt: skip
# A team's yards gained: passing plus rushing yards (sack yards not taken off, as in the
# exploration); volume is its plays (attempts, carries, sacks).
TEAM = Target("team", "yards", "plays", "first_downs", "tds")
PLAYER_TARGETS = {t.name: t for t in (PASSING, RUSHING, RECEIVING)}

STATS = ("y", "vol", "fd", "td")
# Every crude input a unit gets, named without the unit's prefix.
CRUDE = [
    *[f"{s}_{w}" for s in STATS for w in ("s", "l4", "ls")],
    "y_cum", "y_trend", "y_sd", "y_ls_sd", "ypa_s", "ypa_ls", "n_games", "has_ls", "no_history",
]  # fmt: skip
# What a unit with no earlier games gets for a missing average: nothing seen is 0 yards, with
# `no_history` and `has_ls` saying so (a rookie's first game).
NO_HISTORY = 0.0
LAST = 4  # games in the recent average


def crude_inputs(games: pl.DataFrame, unit: str, season: int) -> pl.DataFrame:
    """One row per unit with its crude inputs at the moment. `games`: the unit's known games
    (one row each) of `season` and the season before, with columns unit, season, week and the
    stats y, vol, fd, td. Pure: a frame in, a frame out."""
    g = games.sort(unit, "season", "week").with_columns(c(*STATS).cast(pl.Float64).fill_null(0.0))
    this, last = c("season") == season, c("season") == season - 1
    agg = g.group_by(unit).agg(
        *[c(s).filter(this).mean().alias(f"{s}_s") for s in STATS],
        *[c(s).tail(LAST).mean().alias(f"{s}_l4") for s in STATS],
        *[c(s).filter(last).mean().alias(f"{s}_ls") for s in STATS],
        y_cum=c("y").filter(this).sum(),
        y_sd=c("y").filter(this).std(),
        y_ls_sd=c("y").filter(last).std(),
        ypa_s=c("y").filter(this).sum() / c("vol").filter(this).sum(),
        ypa_ls=c("y").filter(last).sum() / c("vol").filter(last).sum(),
        n_games=this.sum().cast(pl.Float64),
        n_last=last.sum(),
    )
    # Week 1 (no games this season yet): the season so far is last season (the exploration's).
    fill = [c(f"{s}_s").fill_null(c(f"{s}_ls")) for s in STATS]
    agg = agg.with_columns(
        *fill,
        c("y_sd").fill_null(c("y_ls_sd")),
        c("ypa_s").fill_nan(None).fill_null(c("ypa_ls").fill_nan(None)),
        c("ypa_ls").fill_nan(None),
        has_ls=(c("n_last") > 0).cast(pl.Float64),
        no_history=pl.lit(0.0),
    ).with_columns(y_trend=c("y_l4") - c("y_s"))
    return agg.select(unit, *CRUDE)


def with_crude(
    rows: pl.DataFrame, crude: pl.DataFrame, on: str, unit: str, prefix: str = ""
) -> pl.DataFrame:
    """Rows joined on their column `on` to the crude inputs of `unit` (`prefix` on every column);
    a unit with no known games gets `NO_HISTORY` and `no_history` = 1."""
    named = crude.rename({unit: on, **{k: f"{prefix}{k}" for k in CRUDE}})
    out = rows.join(named, on=on, how="left")
    unseen = c(f"{prefix}n_games").is_null()
    return out.with_columns(
        pl.when(unseen).then(1.0).otherwise(c(f"{prefix}no_history")).alias(f"{prefix}no_history")
    ).with_columns(c(f"{prefix}{k}").fill_null(NO_HISTORY) for k in CRUDE if k != "no_history")


# ---------------------------------------------------------------- the experts' saved forecasts
# Each finished expert as the yardstick reads it: its pinned variants (registry `history_runs`)
# and the columns it gives a row. Own side and opponent are from the forecast row's team.
EXPERT_INPUTS: dict[str, int] = {
    "participation/trees_week": 1,
    "participation/lasso_h3": 1,
    "participation/lasso_rest": 1,
    "elo/margin": 1,
    "elo/total": 1,
    "team-efficiency/off_next3_change": 1,
    "pace/plays_full": 1,
    "pace/dropbacks_full": 1,
    "pace/runs_full": 1,
    "pace/proe_shrunk": 1,
    "pace/pace_oe_shrunk": 1,
    "schemes-v2/pass_oe_rung2": 1,
    "schemes-v2/shotgun_rung2": 1,
    "schemes-v2/depth_rung2": 1,
    "schemes-v2/tempo_shrunk": 1,
}
HORIZON_SHARE = {"next3": "part_h3", "rest": "part_rest"}
TEAM_EXPERTS: dict[str, list[str]] = {
    "elo": ["elo_own", "elo_opp", "elo_own_off", "elo_opp_def", "elo_margin", "elo_total"],
    "efficiency": ["te_off", "te_off_pass", "te_off_run", "te_opp_def", "te_opp_def_pass",
                   "te_opp_def_run"],
    "pace": ["pace_plays", "pace_dropbacks", "pace_runs", "pace_proe", "pace_oe",
             "pace_opp_plays"],
    "schemes": ["sch_pass_oe", "sch_shotgun", "sch_depth", "sch_tempo"],
}  # fmt: skip
PLAYER_EXPERTS = ["part_share", "part_play", "part_share_if"]
# The row rule (the CEO's call 3, Claude's reading): a player counts when participation's saved
# chance of taking a snap is at least this, known before kickoff.
EXPECTED_TO_PLAY = 0.5


def experts(horizon: str, players: bool) -> dict[str, list[str]]:
    """The expert groups and their columns for a target: participation (players only; plus its
    horizon's share forecast), then the four team experts."""
    out = {}
    if players:
        out["participation"] = PLAYER_EXPERTS + (
            [HORIZON_SHARE[horizon]] if horizon in HORIZON_SHARE else []
        )
    return out | TEAM_EXPERTS


def _for_games(view, key: str, ids: pl.Series) -> pl.DataFrame:
    """One output's rows for these games, the latest made by the moment (one per key)."""
    df = view.output(key).filter(c("game_id").is_in(ids.implode()))
    keys = [k for k in ("gsis_id", "game_id", "team") if k in df.columns]
    return df.sort("as_of").unique(keys, keep="last")


def team_expert_inputs(view, sides: pl.DataFrame) -> pl.DataFrame:
    """`sides` (game_id, team, opponent, home) with every team expert's columns, own and
    opponent's, at the view's moment."""
    ids = sides["game_id"].unique()
    m = _for_games(view, "elo/margin", ids)
    t = _for_games(view, "elo/total", ids).select("game_id", elo_total="mean")
    m = m.join(t, on="game_id", how="left")
    is_home = c("home")
    elo = sides.select("game_id", "team", "home").join(m, on="game_id", how="left").select(
        "game_id", "team",
        elo_own=pl.when(is_home).then(c("home_rating")).otherwise(c("away_rating")),
        elo_opp=pl.when(is_home).then(c("away_rating")).otherwise(c("home_rating")),
        elo_own_off=pl.when(is_home).then(c("home_offense")).otherwise(c("away_offense")),
        elo_opp_def=pl.when(is_home).then(c("away_defense")).otherwise(c("home_defense")),
        elo_margin=pl.when(is_home).then(c("mean")).otherwise(-c("mean")),
        elo_total="elo_total",
    )  # fmt: skip
    te = _for_games(view, "team-efficiency/off_next3_change", ids)
    own = te.select("game_id", "team", te_off="off_rating", te_off_pass="off_pass",
                    te_off_run="off_run")  # fmt: skip
    opp = te.select("game_id", opponent="team", te_opp_def="def_rating",
                    te_opp_def_pass="def_pass", te_opp_def_run="def_run")  # fmt: skip
    out = sides.join(elo, on=["game_id", "team"], how="left")
    out = out.join(own, on=["game_id", "team"], how="left")
    out = out.join(opp, on=["game_id", "opponent"], how="left")
    pace = {"plays_full": "pace_plays", "dropbacks_full": "pace_dropbacks",
            "runs_full": "pace_runs", "proe_shrunk": "pace_proe",
            "pace_oe_shrunk": "pace_oe"}  # fmt: skip
    for variant, col in pace.items():
        h = _for_games(view, f"pace/{variant}", ids).select("game_id", "team", c("mean").alias(col))
        out = out.join(h, on=["game_id", "team"], how="left")
    h = _for_games(view, "pace/plays_full", ids).select("game_id", opponent="team",
                                                         pace_opp_plays="mean")  # fmt: skip
    out = out.join(h, on=["game_id", "opponent"], how="left")
    schemes = {"pass_oe_rung2": "sch_pass_oe", "shotgun_rung2": "sch_shotgun",
               "depth_rung2": "sch_depth", "tempo_shrunk": "sch_tempo"}  # fmt: skip
    for variant, col in schemes.items():
        h = _for_games(view, f"schemes-v2/{variant}", ids).select(
            "game_id", "team", c("mean").alias(col)
        )
        out = out.join(h, on=["game_id", "team"], how="left")
    return out


def player_expert_inputs(view, rows: pl.DataFrame) -> pl.DataFrame:
    """Participation's saved forecasts for the rows (gsis_id, game_id): the next game's snap
    share, the chance of a snap and the share if he plays, and the 3-game and rest-of-season
    shares. Rows participation didn't forecast are dropped: the row rule needs its chance."""
    ids = rows["game_id"].unique()
    week = _for_games(view, "participation/trees_week", ids).select(
        "gsis_id", "game_id", part_share="mean", part_play="p_nonzero",
        part_share_if="if_nonzero_mean",
    )  # fmt: skip
    out = rows.join(week, on=["gsis_id", "game_id"], how="inner")
    for key, col in (
        ("participation/lasso_h3", "part_h3"),
        ("participation/lasso_rest", "part_rest"),
    ):
        h = _for_games(view, key, ids).select("gsis_id", "game_id", c("mean").alias(col))
        out = out.join(h, on=["gsis_id", "game_id"], how="left")
    return out


# A missing expert value (a game an expert didn't forecast) gets the median of the moment's rows,
# so a row is never dropped for it; more than this share missing on a moment is an error.
MISSING_LIMIT = 0.02


def fill_missing(rows: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Expert columns with a missing value filled by the moment's median; raises if a column is
    missing on more than `MISSING_LIMIT` of the rows (an input that didn't arrive)."""
    if rows.is_empty():
        return rows
    for col in cols:
        share = rows[col].null_count() / rows.height
        if share > MISSING_LIMIT:
            raise ValueError(
                f"crude-forecaster: {col} is missing on {share:.1%} of a moment's rows"
            )
    return rows.with_columns(c(col).fill_null(c(col).median()).fill_null(0.0) for col in cols)


def unit_games(stats: pl.DataFrame, target: Target, unit: str = "gsis_id") -> pl.DataFrame:
    """A table's known games in the crude stats' names: unit, season, week, y, vol, fd, td."""
    return stats.select(
        unit, "season", "week",
        y=c(target.yards), vol=c(target.volume), fd=c(target.first_downs), td=c(target.tds),
    )  # fmt: skip


def team_stats(tg: pl.DataFrame) -> pl.DataFrame:
    """Team-game box scores in the team target's names, known rows only."""
    return tg.filter(c("stats_known_at").is_not_null()).select(
        "game_id", "team", "opponent", "season", "week",
        yards=(c("passing_yards") + c("rushing_yards")).cast(pl.Float64),
        plays=(c("attempts") + c("carries") + c("sacks_suffered")).cast(pl.Float64),
        first_downs=(c("passing_first_downs") + c("rushing_first_downs")).cast(pl.Float64),
        tds=(c("passing_tds") + c("rushing_tds")).cast(pl.Float64),
        known_at="stats_known_at",
    )  # fmt: skip


def columns(kind: Mapping[str, list[str]]) -> list[str]:
    return [col for cols in kind.values() for col in cols]
