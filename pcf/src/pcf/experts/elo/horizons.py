"""The long horizon (elo brief, goal 1; exploration F26): a team's wins over its next 3 games and
over the rest of the regular season, from its next game on, at the same moment as the game
forecasts.

- **Elo's expected wins:** each game left is scored with the ratings as they stand: the rating gap
  plus home field (minus it away), turned into a win chance with a normal curve (`SPREAD` points
  wide), and summed. No future injuries, no rating changes along the way.
- **The yardstick** (the brief's): the team's win rate so far this season, pulled toward .500 as
  if it had played `PULL_GAMES` more games at .500 (8, chosen on 2002-2015 in the exploration),
  times the games left.
- **The fit:** wins = b1 x Elo's expected wins + b2 x games left, weighted least squares in each
  training window. Ranges come from training misses, per number of games left, kept inside 0 and
  the games left.

Ties count half a win. Rows are regular-season team-games only; a row is scored once every game
in its window has a result, and the 3-game horizon needs 3 games left.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import PREDICTION, Expert
from pcf.experts.elo.features import results
from pcf.experts.elo.ratings import DEFAULT, Settings, Walk, season_priors

c = pl.col
SPREAD = 13.5  # the sd of NFL margins around a forecast, in points (exploration: 13.3-13.8)
PULL_GAMES = 8
NEXT3, REST = 3, None
BY = ("left",)


def _outcomes(game: pl.DataFrame) -> pl.DataFrame:
    """Each regular-season team-game, with its opponent, side, when the game was on the schedule
    (`listed_at`) and (if played) its win: 1, 0 or 0.5."""
    reg = game.filter(c("game_type") == "REG")
    m = c("home_score") - c("away_score")
    played = c("result_known_at").is_not_null() & c("home_score").is_not_null()
    win = pl.when(~played).then(None).when(m == 0).then(0.5)
    return pl.concat(
        reg.select(
            "game_id",
            "season",
            "week",
            "kickoff",
            team=c(side),
            opp=c(other),
            side=pl.when(c("location") == "Neutral").then(0).otherwise(sign),
            win=win.when(m * sign > 0).then(1.0).otherwise(0.0),
            known_at=pl.when(played).then(c("result_known_at")),
            listed_at="known_at",
        )  # fmt: skip
        for side, other, sign in (("home_team", "away_team", 1), ("away_team", "home_team", -1))
    ).sort("season", "team", "week")


def _win_chance(edge: float) -> float:
    return 0.5 * (1 + math.erf(edge / SPREAD / math.sqrt(2)))


def _rows(
    game: pl.DataFrame, targets: pl.DataFrame, horizon: int | None, settings: Settings
) -> pl.DataFrame:
    """One row per team per target game (game_id, moment): its window's games, Elo's expected
    wins over them and the yardstick, from the results known at the moment."""
    res = results(game)
    out_cols = {"game_id": pl.String, "team": pl.String, "season": pl.Int32, "left": pl.Int32,
                "elo_wins": pl.Float64, "yard_wins": pl.Float64, "won": pl.Float64,
                "played": pl.Int32}  # fmt: skip
    sides = _outcomes(game)
    targets = targets.join(sides.select("game_id", "team", "season", "week", "kickoff"),
                           on="game_id")  # fmt: skip
    if targets.is_empty():
        return pl.DataFrame(schema=out_cols)
    by_team = {k: g for k, g in sides.partition_by(["season", "team"], as_dict=True).items()}
    walk = Walk(season_priors(res, settings), settings)
    res_rows = res.to_dicts()
    i, out = 0, []
    for t in targets.sort("moment", "kickoff", "game_id", "team").iter_rows(named=True):
        while i < len(res_rows) and res_rows[i]["known_at"] <= t["moment"]:
            walk.add(res_rows[i])
            i += 1
        walk.roll_to(t["season"])
        # only games on the schedule by the moment (a bulk view also holds later ones)
        season = by_team[(t["season"], t["team"])].filter(c("listed_at") <= t["moment"])
        done = season.filter((c("week") < t["week"]) & (c("known_at") <= t["moment"]))
        window = season.filter(c("week") >= t["week"])
        if horizon is not REST:
            window = window.head(horizon)
        hfa = walk.hfa(t["season"], False)
        expected = sum(
            _win_chance(walk.r[t["team"]] - walk.r[g["opp"]] + g["side"] * hfa)
            for g in window.iter_rows(named=True)
        )
        won, played = float(done["win"].sum()), done.height
        rate = (won + 0.5 * PULL_GAMES) / (played + PULL_GAMES)
        out.append({"game_id": t["game_id"], "team": t["team"], "season": t["season"],
                    "left": window.height, "elo_wins": expected,
                    "yard_wins": rate * window.height, "won": won, "played": played})  # fmt: skip
    return pl.DataFrame(out, schema=out_cols).sort("game_id", "team")


def window_wins(game: pl.DataFrame, horizon: int | None) -> pl.DataFrame:
    """game_id, team, y (wins over the window from this game on) and known_at (the window's last
    result). Complete windows only; the 3-game horizon needs 3 games."""
    sides = _outcomes(game)
    seq = sides.with_columns(n=c("week").rank("ordinal").over("season", "team"))
    pairs = seq.select("game_id", "team", "season", start="n").join(
        seq.select("season", "team", "n", "win", "known_at"), on=["season", "team"]
    ).filter(c("n") >= c("start"))  # fmt: skip
    if horizon is not REST:
        pairs = pairs.filter(c("n") < c("start") + horizon)
    need = horizon if horizon is not REST else 1
    return (
        pairs.group_by("game_id", "team")
        .agg(
            y=c("win").sum(),
            games=pl.len(),
            unknown=c("win").null_count(),
            known_at=c("known_at").max(),
        )  # fmt: skip
        .filter((c("unknown") == 0) & (c("games") >= need))
        .select("game_id", "team", "y", "known_at")
    )


class _Horizon(Expert):
    id = "elo"
    cadence = "in_season"
    grain = "team_game"
    inputs = {"game": ("schedule", "result")}
    run = "saturday"
    groups = BY
    settings: ClassVar[Settings] = DEFAULT
    horizon: ClassVar[int | None]

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        targets = games.select("game_id").with_columns(
            moment=pl.lit(view.at).cast(pl.Datetime("us", "UTC"))
        )
        return _rows(view.table("game"), targets, self.horizon, self.settings)

    def features_history(self, view, moments: pl.DataFrame) -> pl.DataFrame:
        return _rows(view.table("game"), moments.select("game_id", "moment"), self.horizon,
                     self.settings)  # fmt: skip

    def target(self, view) -> pl.DataFrame:
        return window_wins(view.table("game"), self.horizon)

    def point(self, model: dict[str, Any], rows: pl.DataFrame) -> np.ndarray:
        raise NotImplementedError

    def fit_point(self, train: pl.DataFrame) -> dict[str, Any]:
        return {}

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        model = self.fit_point(train)
        resid = train.select(*BY, "weight").with_columns(
            resid=pl.Series(train["y"].to_numpy() - self.point(model, train))
        )
        return model | {"offsets": fit_offsets(resid, BY)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        out = rows.select("game_id", "team", *BY).with_columns(
            mean=pl.Series(self.point(model, rows))
        )
        top = c("left").cast(pl.Float64)
        return with_ranges(out, model["offsets"], BY).select(
            "game_id", "team", *[c(p).clip(0.0, top) for p in PREDICTION]
        )


class _Yardstick(_Horizon):
    """The win rate so far, pulled toward .500 by 8 games, times the games left."""

    def point(self, model, rows):
        return rows["yard_wins"].to_numpy()


class _EloWins(_Horizon):
    """Elo's expected wins and the games left, refit in each training window."""

    def fit_point(self, train):
        x = train.select("elo_wins", "left").to_numpy().astype(float)
        sw = np.sqrt(train["weight"].to_numpy())
        beta = np.linalg.lstsq(x * sw[:, None], train["y"].to_numpy() * sw, rcond=None)[0]
        return {"beta": beta}

    def point(self, model, rows):
        return rows.select("elo_wins", "left").to_numpy().astype(float) @ model["beta"]

    def explain(self, model):
        return {"coefficients": dict(zip(("elo_wins", "left"), map(float, model["beta"]),
                                         strict=True))}  # fmt: skip


class YardstickNext3(_Yardstick):
    variant = "wins_next3_yardstick"
    quantity = "wins_next3"
    horizon = NEXT3


class EloNext3(_EloWins):
    """Wins over the team's next 3 games."""

    variant = "wins_next3"
    quantity = "wins_next3"
    horizon = NEXT3

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [YardstickNext3]


class YardstickRest(_Yardstick):
    variant = "wins_rest_yardstick"
    quantity = "wins_rest"
    horizon = REST


class EloRest(_EloWins):
    """Wins over the rest of the regular season, from the team's next game on."""

    variant = "wins_rest"
    quantity = "wins_rest"
    horizon = REST

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [YardstickRest]
