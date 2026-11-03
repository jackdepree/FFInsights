"""Planted leaks: deliberately leaky versions of the toy expert, one per check, with honest twins.

Every blocking check must catch its planted leak and pass the honest twin, so a check that
silently stops working fails the tests.
"""

import numpy as np
import polars as pl

from pcf.data.tables.store import assemble, chosen_parts
from pcf.validation.toy import POINTS, RecentPoints

c = pl.col


def _bulk(view, games: pl.DataFrame, known_by) -> pl.DataFrame:
    """Toy features for every game at once. `known_by(rows)` says which past games each row may
    use: a boolean expression over the joined row (as_of, kickoff) and past game (h_*)."""
    pg = view.table("player_game")
    rows = pg.filter(
        c("game_id").is_in(games["game_id"].implode())
        & c("position").is_in(["QB", "RB", "WR", "TE"])
    ).join(games.select("game_id", "moment", "kickoff"), on="game_id")  # fmt: skip
    hist = pg.filter(c(POINTS).is_not_null()).select(
        "gsis_id", h_season="season", h_week="week", h_points=POINTS, h_known="stats_known_at",
        h_game="game_id",
    )  # fmt: skip
    pairs = rows.select(
        "gsis_id", "game_id", "season", "week", "moment", "kickoff", "position"
    ).join(
        hist, on="gsis_id"
    )  # fmt: skip
    pairs = pairs.filter(known_by & c("h_season").is_between(c("season") - 1, c("season")))
    pairs = pairs.sort("gsis_id", "game_id", "h_season", "h_week")
    feats = pairs.group_by("gsis_id", "game_id", "position").agg(
        last4=c("h_points").tail(4).mean(),
        games=c("h_points").len().cast(pl.Int32),
        season_avg=c("h_points").filter(c("h_season") == c("season")).mean(),
    )
    return feats.with_columns(season_avg=c("season_avg").fill_null(c("last4")))


class HonestBulk(RecentPoints):
    """Honest twin for checks 3 and 4: bulk features from games known at each row's moment."""

    def features_history(self, view, games):
        return _bulk(view, games, c("h_known") <= c("moment"))


class CurrentGameBulk(RecentPoints):
    """Planted leak (checks 3, 4): the row's own game is in its average (cleaning-port#F8)."""

    def features_history(self, view, games):
        return _bulk(view, games, (c("h_season") < c("season")) | (c("h_week") <= c("week")))


class EarlierGamesBulk(RecentPoints):
    """Planted leak (checks 3, 4): "earlier games", which at a Tuesday moment includes Monday
    night's, not known until Tuesday night (validation-harness#F2)."""

    def features_history(self, view, games):
        return _bulk(view, games, (c("h_season") < c("season")) | (c("h_week") < c("week")))


class AroundTheView(RecentPoints):
    """Planted leak (checks 3, 4): per-moment features that read the source behind the view."""

    def features(self, view, games):
        out = super().features(view, games)
        source = view._gateway.source  # reaching around the gateway
        frames = {
            p: source.part("player_game", p).lazy() for p in chosen_parts("player_game", ["stats"])
        }
        whole = assemble("player_game", frames)
        later = whole.group_by("gsis_id").agg(future=c(POINTS).mean())
        return out.join(later, on="gsis_id", how="left").with_columns(
            last4=c("last4") + 0 * c("future").fill_null(0) + c("future").fill_null(0) * 1e-3
        ).drop("future")  # fmt: skip


class CachedOutcomes(RecentPoints):
    """Planted leak (check 8): keeps every outcome it was ever shown and centres on their mean,
    test games included."""

    def target(self, view):
        out = super().target(view)
        self._all = out["y"].drop_nulls().mean()
        return out

    def predict(self, model, rows):
        out = super().predict(model, rows)
        shift = getattr(self, "_all", 0.0) * 1e-3
        return out.with_columns(c("mean", "q10", "q50", "q90") + shift)


class Peeks(RecentPoints):
    """Planted leak (check 10): a feature that is nearly the outcome."""

    def features(self, view, games):
        out = super().features(view, games)
        source = view._gateway.source
        y = source.part("player_game", "stats").select("gsis_id", "game_id", peek=c(POINTS))
        return out.join(y, on=["gsis_id", "game_id"], how="left").with_columns(
            c("peek").fill_null(0.0)
        )


class OnField(RecentPoints):
    """Reads post-season-only data (on-field players) in season: allowed only for finished
    seasons (check 5)."""

    inputs = {"player_game": ("stats",), "player_play": ("on_field",)}


GATEWAY_LEAK = """
import polars as pl
from pcf.data.tables import load

def features(view, games):
    old = pl.read_parquet("data/tables/player_game/stats/season=2024/data.parquet")
    return load("player_game")
"""
GATEWAY_HONEST = """
import polars as pl

def features(view, games):
    return view.table("player_game").filter(pl.col("game_id").is_in(games["game_id"]))
"""
SPLITTER_LEAK = """
from sklearn.model_selection import KFold, train_test_split

def fit(train):
    a, b = train_test_split(train)
"""
SPLITTER_HONEST = """
from sklearn.linear_model import LinearRegression

def fit(train):
    return LinearRegression().fit(train[["x"]], train["y"])
"""


def rng_points(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(10, 5, n)
