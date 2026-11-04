"""Longer horizons (brief D9): a player's average share over the next 3 team games, and over the
rest of the regular season, predicted at the same moment from the same inputs. One direct model
per horizon: repeating the next-game forecast would miss how injuries and role changes pile up
over a window, and the ranges would come out far too narrow.

A window counts the games of the team the player is on at the moment of prediction, by week. A
week the player has no row, on any team, counts as 0, so cut players stay in the outcome (F8's
caveat). A row is scored only once its whole window is known, and the 3-game horizon needs 3
regular-season games left.
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.baselines.lasso import ALPHAS, fit_lasso, predict_lasso, weighted_mse
from pcf.core.contract import PREDICTION, Expert
from pcf.experts.participation.common import FIRST_SEASON, known_shares
from pcf.experts.participation.features import BACK, CAREER, EXTRA, FEATURES, INPUTS, features
from pcf.experts.participation.twopart import HOLDOUT, TREES

c = pl.col
REST = None  # the rest of the regular season
HORIZON_INPUTS = {**INPUTS, "game": ("schedule",)}
BY = ("position",)


def window_share(
    pg: pl.DataFrame, schedule: pl.DataFrame, keys: list[str], horizon: int | None
) -> pl.DataFrame:
    """Keys, y (the average share over the window from this game on) and known_at (when the
    window's last game's snap counts were known). Regular-season rows only."""
    known = known_shares(pg, ["team"])
    reg = schedule.filter(c("game_type") == "REG").select("game_id", "season", "week")
    teams = pl.concat(
        schedule.filter(c("game_type") == "REG").select("game_id", "season", "week", team=c(side))
        for side in ("home_team", "away_team")
    )
    rows = known.join(reg.select("game_id"), on="game_id").select(
        *keys, "season", "team", start="week"
    )
    # Each row against every later game of the player's team that season
    window = rows.join(
        teams.select("season", "team", week="week", window_game="game_id"),
        on=["season", "team"],
    ).filter(c("week") >= c("start"))
    window = window.with_columns(n=c("week").rank("ordinal").over(keys)).with_columns(
        left=c("n").max().over(keys)
    )
    if horizon is not REST:
        window = window.filter((c("n") <= horizon) & (c("left") >= horizon))
    # The player's share that week, on whichever team; none means 0
    done = known.select("game_id").unique()
    weeks = known.select("gsis_id", "season", "week", "share", "known_at").unique(
        ["gsis_id", "season", "week"]
    )
    window = window.join(
        weeks.rename({"share": "w_share", "known_at": "w_known"}),
        on=["gsis_id", "season", "week"],
        how="left",
    ).with_columns(game_known=c("window_game").is_in(done["game_id"].implode()))
    game_known = known.group_by("game_id").agg(g_known=c("known_at").max())
    window = window.join(game_known, left_on="window_game", right_on="game_id", how="left")
    return (
        window.group_by(keys)
        .agg(
            y=c("w_share").fill_null(0.0).mean(),
            complete=c("game_known").all(),
            known_at=c("g_known").max(),
        )
        .filter(c("complete"))
        .drop("complete")
    )


class _Horizon(Expert):
    """One forecast of a window's average share, regular-season rows only."""

    id = "participation"
    cadence = "in_season"
    grain = "player_game"
    inputs = HORIZON_INPUTS
    kind = "amount"
    run = "saturday"
    groups = ("position", "played_recently")
    first_train = FIRST_SEASON
    horizon: ClassVar[int | None]
    columns: ClassVar[list[str]] = FEATURES

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        reg = view.table("game", seasons=[int(games["season"].max())]).filter(
            c("game_type") == "REG"
        )
        games = games.filter(c("game_id").is_in(reg["game_id"].implode()))
        if games.is_empty():
            return pl.DataFrame(schema={k: pl.String for k in self.keys()})
        return features(view, games, self.keys())

    def target(self, view) -> pl.DataFrame:
        return window_share(
            view.table("player_game"), view.table("game"), self.keys(), self.horizon
        )

    def predict_mean(self, model: dict[str, Any], rows: pl.DataFrame) -> np.ndarray:
        raise NotImplementedError

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        mean = pl.Series(self.predict_mean(model, rows))
        out = rows.select(*self.keys(), *BY).with_columns(mean=mean)
        return with_ranges(out, model["offsets"], BY).select(
            *self.keys(), *[c(p).clip(0.0, 1.0) for p in PREDICTION]
        )


class _SeasonAverage(_Horizon):
    """Rung 0: the player's share so far this season."""

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        resid = train.select(*BY, "weight", resid=c("y") - c("season_avg"))
        return {"offsets": fit_offsets(resid, BY)}

    def predict_mean(self, model, rows):
        return rows["season_avg"].to_numpy()


class _PerPosition(_Horizon):
    """A model per position; ranges from residuals on the latest 20% of the training window."""

    def fit_one(self, x, y, w) -> Any:
        raise NotImplementedError

    def predict_one(self, part, x) -> np.ndarray:
        raise NotImplementedError

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        parts, resid = {}, []
        for pos, g in train.partition_by("position", as_dict=True).items():
            x = g.select(self.columns).to_numpy().astype(float)
            y = g["y"].to_numpy().astype(float)
            w = g["weight"].to_numpy().astype(float)
            cut = int(len(y) * (1 - HOLDOUT))
            early = self.fit_one(x[:cut], y[:cut], w[:cut])
            r = y[cut:] - self.predict_one(early, x[cut:]).clip(0, 1)
            resid.append(g[cut:].select(*BY, "weight").with_columns(resid=pl.Series(r)))
            parts[pos[0]] = self.fit_one(x, y, w)
        return {"parts": parts, "offsets": fit_offsets(pl.concat(resid), BY)}

    def predict_mean(self, model, rows):
        mean = np.zeros(rows.height)
        pos = rows["position"].to_numpy()
        x = rows.select(self.columns).to_numpy().astype(float)
        for name, part in model["parts"].items():
            i = pos == name
            if i.any():
                mean[i] = self.predict_one(part, x[i]).clip(0, 1)
        return mean


class _LassoHorizon(_PerPosition):
    columns = [*FEATURES, *CAREER, *EXTRA, *BACK]

    def fit_one(self, x, y, w):
        cut = int(len(y) * (1 - HOLDOUT))
        early = fit_lasso(x[:cut], y[:cut], w[:cut], ALPHAS)
        errors = [weighted_mse(predict_lasso(m, x[cut:]), y[cut:], w[cut:]) for m in early]
        (model,) = fit_lasso(x, y, w, [float(ALPHAS[int(np.argmin(errors))])])
        return model

    def predict_one(self, part, x):
        return predict_lasso(part, x)


class _TreesHorizon(_PerPosition):
    columns = [*FEATURES, *CAREER]

    def fit_one(self, x, y, w):
        return HistGradientBoostingRegressor(**TREES).fit(x, y, sample_weight=w)

    def predict_one(self, part, x):
        return part.predict(x)


class SeasonH3(_SeasonAverage):
    variant = "season_h3"
    quantity = "snap_share_next3"
    horizon = 3


class LassoH3(_LassoHorizon):
    variant = "lasso_h3"
    quantity = "snap_share_next3"
    horizon = 3

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [SeasonH3]


class TreesH3(_TreesHorizon):
    variant = "trees_h3"
    quantity = "snap_share_next3"
    horizon = 3

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [SeasonH3, LassoH3]


class SeasonRest(_SeasonAverage):
    variant = "season_rest"
    quantity = "snap_share_rest"
    horizon = REST


class LassoRest(_LassoHorizon):
    variant = "lasso_rest"
    quantity = "snap_share_rest"
    horizon = REST

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [SeasonRest]


class TreesRest(_TreesHorizon):
    variant = "trees_rest"
    quantity = "snap_share_rest"
    horizon = REST

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return [SeasonRest, LassoRest]
