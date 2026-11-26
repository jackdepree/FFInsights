"""Scores for stabilization's ladder (decision 0052): the gain of one forecast over another, with a
90% interval from resampling players (teams for team measures), the shuffled-player copies, the
range score and coverage.

Every frame scored here has `y` (the target rate less the pull target, last season's position
mean), `w` (the target's attempts), an entity column and one column per forecast, all centred the
same way, so the position's average is 0.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K

c = pl.col


@dataclass(frozen=True)
class Gain:
    gain: float
    lo: float
    hi: float
    rows: int

    @property
    def clear(self) -> bool:
        return self.lo > 0

    @property
    def worse(self) -> bool:
        return self.hi < 0

    def fmt(self) -> str:
        return f"{100 * self.gain:+.1f}% ({100 * self.lo:+.1f} to {100 * self.hi:+.1f})"


def _per_entity(f: pl.DataFrame, a: str, b: str, ent: str) -> tuple[np.ndarray, np.ndarray]:
    e = f.drop_nulls([a, b]).with_columns(
        ea=c("w") * (c("y") - c(a)) ** 2, eb=c("w") * (c("y") - c(b)) ** 2
    )
    p = e.group_by(ent).agg(ea=c("ea").sum(), eb=c("eb").sum()).sort(ent)
    return p["ea"].to_numpy(), p["eb"].to_numpy()


def gain(f: pl.DataFrame, new: str, base: str, ent: str = "gsis_id", seed: int = 0,
         draws: int = K.DRAWS) -> Gain:  # fmt: skip
    """The share of `base`'s weighted squared error that `new` removes; entities resampled
    (sorted first, so the interval doesn't move with row order)."""
    ea, eb = _per_entity(f, new, base, ent)
    if len(ea) == 0 or eb.sum() == 0:
        return Gain(float("nan"), float("nan"), float("nan"), 0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ea), (draws, len(ea)))
    g = 1 - ea[idx].sum(1) / eb[idx].sum(1)
    rows = f.drop_nulls([new, base]).height
    return Gain(float(1 - ea.sum() / eb.sum()), float(np.quantile(g, 0.05)),
                float(np.quantile(g, 0.95)), rows)  # fmt: skip


def sse_gain(f: pl.DataFrame, new: str, base: str) -> float:
    e = f.drop_nulls([new, base])
    a = (e["w"] * (e["y"] - e[new]) ** 2).sum()
    b = (e["w"] * (e["y"] - e[base]) ** 2).sum()
    return float(1 - a / b) if b else float("nan")


def shuffled(f: pl.DataFrame, cols: Sequence[str], by: Sequence[str], seed: int) -> pl.DataFrame:
    """`cols` moved together to another row of the same `by` group (a shuffled copy)."""
    rng = np.random.default_rng(seed)
    key = f.select(pl.concat_str([c(b).cast(pl.String) for b in by], separator="|")).to_series()
    key = key.to_numpy()
    order = np.arange(f.height)
    for kk in np.unique(key):
        idx = np.flatnonzero(key == kk)
        order[idx] = idx[rng.permutation(len(idx))]
    return f.with_columns(f.select(cols)[order])


def interval_score(y: np.ndarray, lo: np.ndarray, hi: np.ndarray, alpha: float = 0.2) -> np.ndarray:
    """The range score for an 80% range (lower is better): its width plus 2 / alpha times how
    far the result falls outside it."""
    return (hi - lo) + (2 / alpha) * np.maximum(lo - y, 0) + (2 / alpha) * np.maximum(y - hi, 0)


def range_gain(f: pl.DataFrame, new_v: str, base_v: str, mean: str, ent: str = "gsis_id",
               seed: int = 0, draws: int = K.DRAWS) -> Gain:  # fmt: skip
    """How much of `base_v`'s range score (`w`-weighted) the variance `new_v` removes, both 80%
    normal ranges around `mean`; entities resampled."""
    e = f.drop_nulls([mean, new_v, base_v])
    y, m, w = e["y"].to_numpy(), e[mean].to_numpy(), e["w"].to_numpy()
    sa = interval_score(y, m - K.Z80 * np.sqrt(e[new_v].to_numpy()),
                        m + K.Z80 * np.sqrt(e[new_v].to_numpy()))  # fmt: skip
    sb = interval_score(y, m - K.Z80 * np.sqrt(e[base_v].to_numpy()),
                        m + K.Z80 * np.sqrt(e[base_v].to_numpy()))  # fmt: skip
    p = e.select(ent).with_columns(sa=pl.Series(w * sa), sb=pl.Series(w * sb))
    p = p.group_by(ent).agg(c("sa").sum(), c("sb").sum()).sort(ent)
    a, b = p["sa"].to_numpy(), p["sb"].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(a), (draws, len(a)))
    g = 1 - a[idx].sum(1) / b[idx].sum(1)
    return Gain(float(1 - a.sum() / b.sum()), float(np.quantile(g, 0.05)),
                float(np.quantile(g, 0.95)), e.height)  # fmt: skip


def coverage(f: pl.DataFrame, mean: str, var: str) -> float:
    e = f.drop_nulls([mean, var])
    inside = (e["y"] - e[mean]).abs() <= K.Z80 * e[var].sqrt()
    return float(inside.mean()) if e.height else float("nan")


def coverage_by_thirds(f: pl.DataFrame, mean: str, var: str, by: str) -> list[float]:
    e = f.drop_nulls([mean, var, by])
    if e.height < 30:
        return [float("nan")] * 3
    q = np.quantile(e[by].to_numpy(), [1 / 3, 2 / 3])
    out = []
    for lo, hi in ((-np.inf, q[0]), (q[0], q[1]), (q[1], np.inf)):
        b = e.filter((c(by) > lo) & (c(by) <= hi))
        out.append(coverage(b, mean, var))
    return out


def conformal_scale(train: pl.DataFrame, mean: str, var: str) -> float:
    """The scale that makes an 80% normal range hold on earlier rows (VALIDATION §7's conformal
    step): the 80th percentile of their standardized misses over 1.2816."""
    e = train.drop_nulls([mean, var])
    if e.height < 30:
        return 1.0
    z = ((e["y"] - e[mean]).abs() / e[var].sqrt()).to_numpy()
    return float(np.quantile(z, 0.8) / K.Z80)


def seasons_won(f: pl.DataFrame, new: str, base: str) -> tuple[int, int]:
    """I147's count: the test seasons in which `new` has the lower weighted squared error."""
    won = tot = 0
    for s in sorted(f["season"].unique().to_list()):
        g = sse_gain(f.filter(c("season") == s), new, base)
        if np.isfinite(g):
            tot += 1
            won += g > 0
    return won, tot


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%" if np.isfinite(x) else "n/a"
