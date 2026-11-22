"""Longer horizons (the CEO's call 2): a player's average expected points per game over his team's
next 3 regular-season games, and over the rest of its regular season, from the same moment and the
same inputs as next game's. One direct model per horizon (participation's reason: injuries and
role changes pile up over a window, and repeating the next-game forecast makes the ranges too
narrow).

A window counts the games of the team he is on at the moment, by week. A week he has no row (cut,
or on another roster without a game) counts 0, so players who lose their job stay in the outcome.
A row is scored only once its whole window is known; the 3-game horizon needs 3 games left.

| Variant | Inputs | Rung |
|---|---|---|
| `counts_h3`, `counts_rest` | `model.Counts`' | 1 |
| `eff_h3`, `eff_rest` | `model.Eff`'s | 1 |
| `goal_h3`, `goal_rest` | `eff` + past goal-line, red-zone, end-zone, deep chances, xTDs | 1 |
"""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.core.contract import Expert
from pcf.experts.opportunity_quality import features as F
from pcf.experts.opportunity_quality.common import known_games
from pcf.experts.opportunity_quality.model import _Base, _fit_amount, _predict_amount

c = pl.col
REST = None  # the rest of the regular season
BY = ("position", "size")
SIZE_CUTS = (2.0, 5.0, 9.0)  # sizes of forecast, expected points a game


def window_mean(
    rows: pl.DataFrame, schedule: pl.DataFrame, keys: list[str], horizon: int | None
) -> pl.DataFrame:
    """`rows` (keys, season, week, team, value, known_at: every known player-game) → keys, y (the
    average value a game over the window from this game on) and known_at (when the window's last
    game was known). Regular-season games only."""
    reg = schedule.filter(c("game_type") == "REG")
    teams = pl.concat(
        reg.select("season", "week", window_game="game_id", team=c(side))
        for side in ("home_team", "away_team")
    )
    start = rows.join(reg.select("game_id"), on="game_id").select(
        *keys, "season", "team", start="week"
    )
    window = start.join(teams, on=["season", "team"]).filter(c("week") >= c("start"))
    window = window.with_columns(n=c("week").rank("ordinal").over(keys)).with_columns(
        left=c("n").max().over(keys)
    )
    if horizon is not REST:
        window = window.filter((c("n") <= horizon) & (c("left") >= horizon))
    weeks = rows.select("gsis_id", "season", "week", w_value="value").unique(
        ["gsis_id", "season", "week"]
    )
    game_known = rows.group_by("game_id").agg(g_known=c("known_at").max())
    window = window.join(weeks, on=["gsis_id", "season", "week"], how="left").join(
        game_known, left_on="window_game", right_on="game_id", how="left"
    )
    return (
        window.group_by(keys)
        .agg(
            y=c("w_value").fill_null(0.0).mean(),
            complete=c("g_known").is_not_null().all(),
            known_at=c("g_known").max(),
        )
        .filter(c("complete"))
        .drop("complete")
    )


class _Horizon(_Base):
    """A window's average expected points a game: a lasso, ranges from the latest 20%'s misses by
    position and size of forecast, kept at 0 or above."""

    inputs = {**F.INPUTS, "game": ("schedule",)}
    horizon: ClassVar[int | None]
    quantity = "xfp_ppr_per_game"

    def features(self, view, games: pl.DataFrame) -> pl.DataFrame:
        reg = view.table("game", seasons=[int(games["season"].max())]).filter(
            c("game_type") == "REG"
        )
        games = games.filter(c("game_id").is_in(reg["game_id"].implode()))
        if games.is_empty():
            return pl.DataFrame(schema={k: pl.String for k in self.keys()})
        return F.features(view, games, self.keys(), self.scoring)

    def target(self, view) -> pl.DataFrame:
        known = known_games(view.table("player_game"), self.scoring).select(
            *self.keys(), "season", "week", "team", value=self.outcome, known_at="known_at"
        )
        return window_mean(known, view.table("game"), self.keys(), self.horizon)

    def _sized(self, rows: pl.DataFrame, mean: np.ndarray) -> pl.DataFrame:
        return rows.select(*self.keys(), "position").with_columns(
            mean=pl.Series(mean),
            size=pl.Series(np.digitize(mean, SIZE_CUTS).astype(np.int64)),
        )

    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        x = train.select(self.columns).to_numpy().astype(float)
        y = train["y"].to_numpy().astype(float)
        w = train["weight"].to_numpy().astype(float)
        cut = int(len(y) * 0.8)
        early = _fit_amount(x[:cut], y[:cut], w[:cut], "lasso")
        late = self._sized(train[cut:], _predict_amount(early, x[cut:]))
        resid = late.with_columns(resid=pl.Series(y[cut:]) - c("mean"), weight=pl.Series(w[cut:]))
        return {"amount": _fit_amount(x, y, w, "lasso"), "offsets": fit_offsets(resid, BY)}

    def predict(self, model: dict[str, Any], rows: pl.DataFrame) -> pl.DataFrame:
        mean = np.maximum(
            _predict_amount(model["amount"], rows.select(self.columns).to_numpy().astype(float)),
            0.0,
        )
        out = with_ranges(self._sized(rows, mean), model["offsets"], BY)
        return out.select(*self.keys(), "mean", *[c(q).clip(0.0) for q in ("q10", "q50", "q90")])

    @classmethod
    def baselines(cls) -> list[type[Expert]]:
        return []


def _make(name: str, horizon: int | None, columns: list[str], base: str | None) -> type[_Horizon]:
    attrs = {"variant": name, "horizon": horizon, "columns": columns, "__module__": __name__}
    cls = type(f"Horizon_{name}", (_Horizon,), attrs)
    if base is not None:
        cls.baselines = classmethod(lambda k, b=base: [HORIZONS[b]])  # type: ignore[method-assign]
    return cls


HORIZONS: dict[str, type[_Horizon]] = {}
for _h, _tag in ((3, "h3"), (REST, "rest")):
    HORIZONS[f"counts_{_tag}"] = _make(f"counts_{_tag}", _h, F.COUNTS, None)
    HORIZONS[f"eff_{_tag}"] = _make(f"eff_{_tag}", _h, F.EFF, f"counts_{_tag}")
    HORIZONS[f"goal_{_tag}"] = _make(f"goal_{_tag}", _h, F.GOAL_LINE, f"eff_{_tag}")
globals().update({cls.__name__: cls for cls in HORIZONS.values()})
