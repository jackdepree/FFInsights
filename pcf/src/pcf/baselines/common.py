"""What the fantasy baselines share: scoring formats, a player's known games, and ranges from
training residuals by group (baselines brief, D2 and D7)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

c = pl.col
POSITIONS = ("QB", "RB", "WR", "TE")
# Fantasy points in each scoring format, from nflverse's player stats (D2). Half-PPR is halfway.
SCORING: dict[str, pl.Expr] = {
    "ppr": c("fantasy_points_ppr"),
    "half": (c("fantasy_points") + c("fantasy_points_ppr")) / 2,
    "standard": c("fantasy_points"),
}
QUANTILE_LEVELS = (0.1, 0.5, 0.9)
OFFSETS = ("o10", "o50", "o90")


def points(scoring: str) -> pl.Expr:
    if scoring not in SCORING:
        raise ValueError(f"no scoring {scoring!r}. Scorings: {', '.join(SCORING)}")
    return SCORING[scoring].alias("points")


def known_games(pg: pl.DataFrame, scoring: str, extra: Sequence[str] = ()) -> pl.DataFrame:
    """A view's player-games whose stats are known, oldest first: gsis_id, season, week, points
    and the `extra` stat columns."""
    return (
        pg.filter(c("stats_known_at").is_not_null() & c("fantasy_points").is_not_null())
        .select("gsis_id", "season", "week", points(scoring), *extra)
        .sort("gsis_id", "season", "week")
    )


def target_points(pg: pl.DataFrame, scoring: str, keys: Sequence[str]) -> pl.DataFrame:
    """The outcome: each player-game's fantasy points, known when the stats are."""
    return pg.filter(c("stats_known_at").is_not_null() & c("fantasy_points").is_not_null()).select(
        *keys, y=SCORING[scoring], known_at="stats_known_at"
    )


def predicted_rows(pg: pl.DataFrame, games: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """The offensive skill players on the spine for this moment's games: keys and position."""
    return pg.filter(
        c("game_id").is_in(games["game_id"].implode()) & c("position").is_in(POSITIONS)
    ).select(*keys, "position")


def fit_offsets(residual: pl.DataFrame, by: Sequence[str] = ()) -> pl.DataFrame:
    """Weighted q10, q50 and q90 of `resid` (y minus the point prediction) in each group, plus an
    overall row (the group columns null) for groups training hasn't seen."""
    rows = []
    groups = list(residual.partition_by(list(by), as_dict=True).items()) if by else []
    for key, g in [*groups, (tuple(None for _ in by), residual)]:
        q = weighted_quantiles(g["resid"].to_numpy(), g["weight"].to_numpy(), QUANTILE_LEVELS)
        rows.append({**dict(zip(by, key, strict=True)), **dict(zip(OFFSETS, q, strict=True))})
    schema = {**{b: residual.schema[b] for b in by}, **dict.fromkeys(OFFSETS, pl.Float64)}
    return pl.DataFrame(rows, schema=schema)


def with_ranges(rows: pl.DataFrame, offsets: pl.DataFrame, by: Sequence[str] = ()) -> pl.DataFrame:
    """`mean` plus each group's offsets → q10, q50, q90 (ordered), falling back to the overall
    offsets for an unseen group."""
    overall = offsets.filter(pl.all_horizontal(c(b).is_null() for b in by)) if by else offsets
    out = rows.join(offsets.drop_nulls(list(by)), on=list(by), how="left") if by else rows
    out = out.with_columns(
        (c(o).fill_null(overall[o][0]) if o in out.columns else pl.lit(overall[o][0])).alias(o)
        for o in OFFSETS
    )
    q = [c("mean") + c(o) for o in OFFSETS]
    return out.with_columns(
        q10=pl.min_horizontal(q[0], q[1]),
        q50=q[1],
        q90=pl.max_horizontal(q[1], q[2]),
    ).drop(OFFSETS)


def weighted_quantiles(x: np.ndarray, w: np.ndarray, levels: Sequence[float]) -> list[float]:
    """Quantiles of `x` with weights `w` (the recency weights): the smallest value whose
    cumulative weight reaches each level."""
    order = np.argsort(x, kind="stable")
    x, w = x[order], w[order]
    cum = np.cumsum(w) / w.sum()
    return [float(x[min(np.searchsorted(cum, q), len(x) - 1)]) for q in levels]
