"""The build's cached inputs: the on-field counts and game rows (read once through the gateway),
the features, and the measurables kept beside the space."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.roles_archetypes import counts as C
from pcf.experts.roles_archetypes import features as F

c = pl.col
SEASONS = tuple(range(2016, 2025))  # participation's span; the 2025 vault untouched
FIT = tuple(range(2016, 2021))  # the frozen fit (named-role rules, test 1)
SCORED = tuple(range(2021, 2025))


def cache_dir() -> Path:
    path = get_config().zone("interim") / "roles_archetypes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def counts(refresh: bool = False) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Counts and game rows for `SEASONS` (cached after the first read)."""
    a, b = cache_dir() / "counts.parquet", cache_dir() / "games.parquet"
    if refresh or not (a.exists() and b.exists()):
        cnt, games = C.build(SEASONS)
        cnt.write_parquet(a)
        games.write_parquet(b)
    return pl.read_parquet(a), pl.read_parquet(b)


def walk_features(cnt: pl.DataFrame) -> pl.DataFrame:
    """Every season's features with its usage rates shrunk toward priors from seasons up to it
    (the walk-forward way: season s's rows never read a later season)."""
    out = []
    for s in SEASONS:
        prior = F.priors(cnt.filter(c("season") <= s))
        out.append(F.features(cnt.filter(c("season") == s), prior))
    return pl.concat(out)


def measurables() -> pl.DataFrame:
    """Height, weight and draft slot per player-season, from the roster (beside the space, never
    in it). The 40 isn't in the tables yet (the combine is a raw file only): decision 0048."""
    out = []
    for s in SEASONS:
        view = Gateway(TableSource(seasons=[s])).view(
            END_OF_TIME, "retrospective", {"player_game": ("roster",)}
        )
        pg = view.table("player_game", seasons=[s])
        out.append(pg.group_by("gsis_id", "season").agg(
            c("height").drop_nulls().last().cast(pl.Float64),
            c("weight").drop_nulls().last().cast(pl.Float64),
            c("draft_number").drop_nulls().last().cast(pl.Float64),
        ))  # fmt: skip
    return pl.concat(out)
