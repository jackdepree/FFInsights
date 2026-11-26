"""The ladder's forecasts from a walk (`live.walk`), every choice made walk-forward, and the ranges.

Rungs (the brief): 1 no change (`f0`); 2 the pooled part (`f_pool`); 3 plus the pair part
(`f_pair`, its penalty chosen on earlier seasons); 4 structured, team or head-coach rates
(`f_team`, `f_coach`); 5 trees on rung 3's residual (`f_trees`). Each with the Saturday run's
knowledge, and the hindsight ceiling beside (`_h`). Forecasts clipped to [0, 1].

**Scored rows** (`scored`): the absent player's group-mates, the brief's no-noise target: rows
with a top player of his group absent that game (snap share); for target and carry share, any top
WR, TE or RB absent (they're one pool). `flagged`: a top pool-mate whose chance of playing was
0.5 or less on Saturday, whether or not he sat (the false alarms are in it).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.experts.vacated_opportunity import common as K
from pcf.experts.vacated_opportunity import rates as R

c = pl.col
TREE_FEATURES = ("base", "td", "sd", "n", "rank", "top", "n_with", "e_same", "e_cross",
                 "d_pool", "d_pair", "is_WR", "is_TE", "is_RB", "is_OL", "is_DL")  # fmt: skip
SWING_K = 20.0  # games' weight on the group's swing (I14's shrinkage)


def scored(w: pl.DataFrame) -> pl.Expr:
    m = w["measure"][0]
    return (c("absent_same") if m == "snap" else c("absent_pool")) & c("played")


def _sse(y: np.ndarray, f: np.ndarray) -> float:
    return float(((y - f) ** 2).sum())


def choose_pair(w: pl.DataFrame, grid=R.GRID, first: int = 2015) -> pl.DataFrame:
    """The pair part's penalty per season, chosen on earlier seasons' scored rows (Saturday)."""
    sc = w.filter(scored(w))
    chosen = {}
    for s in sorted(w["season"].unique().to_list()):
        prior = sc.filter((c("season") < s) & (c("season") >= first - 1))
        if prior.height == 0:
            chosen[s] = 1.0
            continue
        y = prior["y"].to_numpy()
        errs = {a: _sse(y, prior.select((c("base") + c("d_pool") + c(f"d_pair_{a}")).clip(0, 1)).to_series().to_numpy())
                for a in grid}  # fmt: skip
        chosen[s] = min(errs, key=errs.get)
    w = w.with_columns(pair_alpha=c("season").replace_strict(chosen, return_dtype=pl.Float64))
    pick = pl.lit(0.0)
    pick_h = pl.lit(0.0)
    for a in grid:
        pick = pl.when(c("pair_alpha") == a).then(c(f"d_pair_{a}")).otherwise(pick)
        pick_h = pl.when(c("pair_alpha") == a).then(c(f"d_pairh_{a}")).otherwise(pick_h)
    return w.with_columns(d_pair=pick, d_pair_h=pick_h)


def forecasts(w: pl.DataFrame) -> pl.DataFrame:
    td = next(col for col in ("share_td", "tgt_td", "car_td") if col in w.columns)
    w = choose_pair(w).with_columns(td=c(td))
    cl = lambda e: e.clip(0, 1)  # noqa: E731
    out = w.with_columns(
        f0=cl(c("base")),
        f_pool=cl(c("base") + c("d_pool")),
        f_pair=cl(c("base") + c("d_pool") + c("d_pair")),
        f_pool_h=cl(c("base") + c("d_pool_h")),
        f_pair_h=cl(c("base") + c("d_pool_h") + c("d_pair_h")),
    )
    if "d_team" in w.columns:
        out = out.with_columns(
            f_team=cl(c("base") + c("d_team") + c("d_pair")),
            f_coach=cl(c("base") + c("d_coach") + c("d_pair")),
        )
    return out.with_columns([(c("group") == g).cast(pl.Float64).alias(f"is_{g}") for g in K.GROUPS])


def add_trees(w: pl.DataFrame, seasons: Sequence[int], base: str = "f_pair") -> pl.DataFrame:
    """Rung 5: gradient-boosted trees on rung 3's residual, fit on earlier seasons' rows with an
    expected or real absence in the pool (walk-forward, a refit each season), applied where the
    Saturday run expects an absence in the pool."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    w = w.with_columns(c("top").cast(pl.Float64))
    fit_rows = w.filter(((c("e_pool") > 0.01) | scored(w)) & c("played"))
    parts = []
    for s in seasons:
        tr = fit_rows.filter(c("season") < s)
        te = w.filter(c("season") == s)
        X = tr.select(TREE_FEATURES).to_numpy()
        m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
                                          min_samples_leaf=50, random_state=0)  # fmt: skip
        m.fit(X, (tr["y"] - tr[base]).to_numpy())
        adj = m.predict(te.select(TREE_FEATURES).to_numpy())
        active = (te["e_pool"] > 0.01).to_numpy()  # Saturday knowledge only
        parts.append(te.with_columns(f_trees=pl.Series((te[base].to_numpy() + adj * active).clip(0, 1))))
    return pl.concat(parts)


def swing(w: pl.DataFrame) -> pl.Expr:
    """His own swing to date, shrunk toward his group's with `SWING_K` games' weight (I14)."""
    g = c("sd").median().over("group", "season")
    return (((c("n") * c("sd") ** 2) + SWING_K * g**2) / (c("n") + SWING_K)).sqrt().clip(0.01)


def add_ranges(w: pl.DataFrame, fcol: str, seasons: Sequence[int], by_swing: bool = False,
               prefix: str = "") -> pl.DataFrame:  # fmt: skip
    """q10, q50, q90 around a forecast from earlier seasons' residuals, per cell (group, whether
    an absence is expected in the pool, base tercile); `by_swing` scales each residual by his own
    swing first (I14). Clipped to [0, 1]."""
    w = w.with_columns(
        cell=c("group") + "|" + (c("e_pool") > 0.02).cast(pl.Utf8) + "|"
        + c("base").cut([0.33, 0.66], labels=["l", "m", "h"]).cast(pl.Utf8),
        sw=swing(w) if by_swing else pl.lit(1.0),
    )  # fmt: skip
    w = w.with_columns(z=(c("y") - c(fcol)) / c("sw"))
    parts = []
    for s in seasons:
        prior = w.filter((c("season") < s) & c("played"))
        qs = prior.group_by("cell").agg(
            z10=c("z").quantile(0.1), z50=c("z").quantile(0.5), z90=c("z").quantile(0.9), nz=pl.len())
        allq = prior.select(z10=c("z").quantile(0.1), z50=c("z").quantile(0.5), z90=c("z").quantile(0.9))
        te = w.filter(c("season") == s).join(qs, on="cell", how="left")
        te = te.with_columns([pl.when(c("nz") >= 50).then(c(z)).otherwise(allq[z][0]).alias(z)
                              for z in ("z10", "z50", "z90")])  # fmt: skip
        te = te.with_columns(
            (c(fcol) + c("z10") * c("sw")).clip(0, 1).alias(prefix + "q10"),
            (c(fcol) + c("z50") * c("sw")).clip(0, 1).alias(prefix + "q50"),
            (c(fcol) + c("z90") * c("sw")).clip(0, 1).alias(prefix + "q90"),
        )
        parts.append(te.drop("z10", "z50", "z90", "nz"))
    return pl.concat(parts).drop("cell", "z", "sw")


def range_score(y: np.ndarray, q10: np.ndarray, q50: np.ndarray, q90: np.ndarray) -> float:
    """The range score (pinball loss averaged over q10, q50, q90), in share points x 100."""
    def pb(q, lv):
        d = y - q
        return np.maximum(lv * d, (lv - 1) * d)

    return float(100 * np.mean((pb(q10, 0.1) + pb(q50, 0.5) + pb(q90, 0.9)) / 3))


def slope(y: np.ndarray, base: np.ndarray, f: np.ndarray) -> float:
    """The calibration slope: the actual change on the forecast change."""
    x = f - base
    v = float(((x - x.mean()) ** 2).sum())
    return float(((x - x.mean()) * (y - base - (y - base).mean())).sum() / v) if v > 0 else float("nan")
