"""The Elo features at a moment: the rating walk over every result known by then, and H1's
same-team measures for the moment's games. `features` is the per-moment version the contract
defines; `features_history` computes every game's in one pass and must give the same rows
(the leakage checks compare them)."""

from __future__ import annotations

from datetime import datetime

import polars as pl

from pcf.experts.elo.ratings import DEFAULT, Settings, Walk, result_order, season_priors
from pcf.experts.elo.same_team import NEED, same_team

c = pl.col
FEATURES = (
    "gap", "hfa", "od_margin", "od_total",
    "qb_diff", "share_diff", "qb_sum", "share_missing",
)  # fmt: skip


def results(games: pl.DataFrame) -> pl.DataFrame:
    """Finished games from a view of `game` (schedule and result): what the walk folds in."""
    return result_order(
        games.filter(c("result_known_at").is_not_null() & c("home_score").is_not_null()).select(
            "game_id",
            "season",
            "home_team",
            "away_team",
            "kickoff",
            neutral=c("location") == "Neutral",
            home_pts=c("home_score").cast(pl.Float64),
            away_pts=c("away_score").cast(pl.Float64),
            margin=(c("home_score") - c("away_score")).cast(pl.Float64),
            total=(c("home_score") + c("away_score")).cast(pl.Float64),
            known_at="result_known_at",
        )  # fmt: skip
    )


def _schedule(game: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    return games.select("game_id", "moment").join(
        game.select(
            "game_id",
            "season",
            "week",
            "kickoff",
            "home_team",
            "away_team",
            neutral=c("location") == "Neutral",
        ),  # fmt: skip
        on="game_id",
    )


def _ratings(res: pl.DataFrame, sched: pl.DataFrame, settings: Settings) -> pl.DataFrame:
    """Walk the results in order, and give each scheduled game its numbers at its moment."""
    walk = Walk(season_priors(res, settings), settings)
    res_rows = res.to_dicts()
    i, out = 0, []
    for g in sched.sort("moment", "kickoff", "game_id").iter_rows(named=True):
        while i < len(res_rows) and res_rows[i]["known_at"] <= g["moment"]:
            walk.add(res_rows[i])
            i += 1
        out.append(
            {"game_id": g["game_id"]}
            | walk.edges(g["season"], g["home_team"], g["away_team"], g["neutral"])
        )
    return pl.DataFrame(out)


def _with_same_team(rated: pl.DataFrame, st: pl.DataFrame, sched: pl.DataFrame) -> pl.DataFrame:
    home = st.rename({"team": "home_team", "share": "h_share", "qb_out": "h_qb"})
    away = st.rename({"team": "away_team", "share": "a_share", "qb_out": "a_qb"})
    return (
        sched.drop("moment")
        .join(rated, on="game_id")
        .join(home, on=["game_id", "home_team"], how="left")
        .join(away, on=["game_id", "away_team"], how="left")
        .with_columns(c("h_share", "a_share").fill_null(1.0), c("h_qb", "a_qb").fill_null(0.0))
        .with_columns(
            qb_diff=c("a_qb") - c("h_qb"),
            share_diff=c("h_share") - c("a_share"),
            qb_sum=c("h_qb") + c("a_qb"),
            share_missing=(1 - c("h_share")) + (1 - c("a_share")),
        )
        .select(
            "game_id",
            "season",
            "week",
            "home_team",
            "away_team",
            "neutral",
            *FEATURES,
            "h_share",
            "a_share",
            "h_qb",
            "a_qb",
        )  # fmt: skip
        .sort("game_id")
    )


def player_rows(view, seasons: list[int]) -> pl.DataFrame:
    return view.table("player_game", seasons=seasons).select(NEED)


def at_moment(view, games: pl.DataFrame, settings: Settings = DEFAULT) -> pl.DataFrame:
    """The per-moment features: the moment's `games` (game_id, season, week, kickoff), from a
    view at `view.at`."""
    moment: datetime = view.at
    game = view.table("game")
    sched = _schedule(
        game, games.with_columns(moment=pl.lit(moment).cast(pl.Datetime("us", "UTC")))
    )
    rated = _ratings(results(game), sched, settings)
    seasons = sched["season"].unique().to_list()
    pg = player_rows(view, seasons)
    kick = game.filter(c("season").is_in(seasons)).select("game_id", "kickoff")
    st = same_team(pg, kick, sched.select("game_id", "moment"))
    return _with_same_team(rated, st, sched)


def history(view, moments: pl.DataFrame, settings: Settings = DEFAULT) -> pl.DataFrame:
    """Every game in `moments` (game_id, season, week, kickoff, moment) at its own moment, in one
    pass, from a view that sees everything."""
    game = view.table("game")
    sched = _schedule(game, moments)
    rated = _ratings(results(game), sched, settings)
    seasons = sched["season"].unique().to_list()
    pg = player_rows(view, seasons)
    kick = game.filter(c("season").is_in(seasons)).select("game_id", "kickoff")
    st = same_team(pg, kick, sched.select("game_id", "moment"))
    return _with_same_team(rated, st, sched)
