"""Scoring the ladder (decision 0051, calls 9-14).

- **Gain:** the share of a base's squared error (weighted by next season's chances) a forecast
  removes, on the same rows; 90% interval from resampling players (2,000 draws).
- **Counts** (the build's bar): the interval clears zero **and** the gain beats every one of 20
  shuffled copies (the piece the rung adds moved to another player of the same season and
  group, the walk refit). The signal test (VALIDATION §5) is the same with every input shuffled,
  against the position's average.
- **Ranges:** each forecast's 80% range for next season's rate is normal, mean the forecast,
  variance v + sigma2 / w (v: the true rate's spread left around the forecast, fit on earlier
  pairs; sigma2 / w: next season's noise at its chances). Coverage and the range score (the
  mean pinball loss over q10, q50, q90).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl

from pcf.experts.skill_over_expected import traits as T

c = pl.col
DRAWS = 2000
COPIES = 20
Z80 = 1.2815515655446004


@dataclass
class Gain:
    share: float
    lo: float
    hi: float
    rows: int

    def clear(self) -> bool:
        return self.lo > 0


def gain(p: pl.DataFrame, new: str, base: str, seed: int = 0, draws: int = DRAWS) -> Gain:
    q = p.drop_nulls([new, base])
    e = q.with_columns(en=c("w") * (c("y") - c(new)) ** 2, eb=c("w") * (c("y") - c(base)) ** 2)
    g = e.group_by("gsis_id").agg(c("en").sum(), c("eb").sum())
    en, eb = g["en"].to_numpy(), g["eb"].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(en), (draws, len(en)))
    d = 1 - en[idx].sum(1) / eb[idx].sum(1)
    return Gain(float(1 - en.sum() / eb.sum()), float(np.quantile(d, 0.05)),
                float(np.quantile(d, 0.95)), q.height)  # fmt: skip


def scored(p: pl.DataFrame) -> pl.DataFrame:
    """The rows every rung can score (rung 3's first fittable target season on)."""
    return p.filter(c("split").is_not_null())


def copies_best(rows: pl.DataFrame, games: pl.DataFrame, new: str, base: str,
                shuffle: tuple[str, ...], n: int = COPIES, seed: int = 0,
                keep: pl.DataFrame | None = None) -> list[float]:  # fmt: skip
    """The gains of `n` shuffled copies (the walk rerun with `shuffle` moved within season and
    group), on the real walk's scored rows (`keep`: gsis_id, season)."""
    out = []
    for i in range(n):
        q = T.walk(rows, games, shuffle_seed=seed + 7000 + i, shuffle=shuffle)
        q = scored(q)
        if keep is not None:
            q = q.join(keep, on=["gsis_id", "season"], how="semi")
        out.append(gain(q, new, base, draws=10).share)
    return out


def ranges(p: pl.DataFrame, mean: str) -> pl.DataFrame:
    """q10, q90 for each scored row from `mean`: v fit on earlier target seasons."""
    s = p["season"].to_numpy()
    y, w, m = p["y"].to_numpy(), p["w"].to_numpy(), p[mean].to_numpy()
    s2 = p["sigma2"].to_numpy()
    v = np.full(p.height, np.nan)
    for t in np.unique(s):
        tr = (s < t) & np.isfinite(m)
        if tr.sum() < 30:
            continue
        resid = (y[tr] - m[tr]) ** 2 - s2[tr] / w[tr]
        v[s == t] = max(float(np.average(resid, weights=w[tr])), 1e-12)
    sd = np.sqrt(v + s2 / w)
    return p.with_columns(q10=pl.Series(m - Z80 * sd), q50=pl.Series(m),
                          q90=pl.Series(m + Z80 * sd))  # fmt: skip


def pinball(y: np.ndarray, q10: np.ndarray, q50: np.ndarray, q90: np.ndarray) -> np.ndarray:
    def one(q, tau):
        d = y - q
        return np.maximum(tau * d, (tau - 1) * d)

    return (one(q10, 0.1) + one(q50, 0.5) + one(q90, 0.9)) / 3


def range_report(p: pl.DataFrame, mean: str, base: str = "avg") -> dict:
    """Coverage of the 80% range, by thirds of chances too, and the range score against the
    position average's range (the same recipe)."""
    a = ranges(p, mean).drop_nulls(["q10"])
    b = ranges(p, base).drop_nulls(["q10"]).join(a.select("gsis_id", "season"),
                                                on=["gsis_id", "season"], how="semi")  # fmt: skip
    a = a.join(b.select("gsis_id", "season"), on=["gsis_id", "season"], how="semi")
    y = a["y"].to_numpy()
    inside = (y >= a["q10"].to_numpy()) & (y <= a["q90"].to_numpy())
    n = a["n"].to_numpy()
    cuts = np.quantile(n, [1 / 3, 2 / 3])
    third = np.digitize(n, cuts)
    pa = pinball(y, a["q10"].to_numpy(), a["q50"].to_numpy(), a["q90"].to_numpy())
    pb = pinball(b["y"].to_numpy(), b["q10"].to_numpy(), b["q50"].to_numpy(),
                 b["q90"].to_numpy())  # fmt: skip
    return {"coverage": float(inside.mean()),
            "by_third": [float(inside[third == i].mean()) for i in range(3)],
            "range_gain": float(1 - pa.sum() / pb.sum()), "rows": a.height}  # fmt: skip


def kept_label(share: float) -> str:
    return "player" if np.isfinite(share) and share >= 0.5 else "team"


def seasons_won(p: pl.DataFrame, new: str, base: str) -> tuple[int, int]:
    """Target seasons (input season + 1) where `new` has the lower weighted error (I147)."""
    won, total = 0, 0
    for _, g in p.drop_nulls([new, base]).group_by("season"):
        en = float((g["w"] * (g["y"] - g[new]) ** 2).sum())
        eb = float((g["w"] * (g["y"] - g[base]) ** 2).sum())
        won += en < eb
        total += 1
    return won, total


def fmt(g: Gain) -> str:
    return f"{100 * g.share:+.1f}% ({100 * g.lo:+.1f} to {100 * g.hi:+.1f})"


def gains(p: pl.DataFrame, pairs: Sequence[tuple[str, str]], seed: int = 0) -> dict:
    return {(a, b): gain(p, a, b, seed) for a, b in pairs}
