"""The pooled role spaces: one PCA per side of the ball, fit across its positions together, with no
position label and no measurables (brief, method 2; decision 0048).

- **Fit** on full-season rows with `MIN_SNAPS`+ snaps in the fit's seasons: features standardized
  on those rows, `K` components.
- **Refits** after every completed season, on all completed seasons. The new axes are rotated to
  the previous fit's (orthogonal Procrustes on the loadings), so a coordinate keeps its meaning
  across versions. `walk` gives the walk-forward history: season s's coordinates from the fit on
  seasons up to s.
- **Intervals:** each axis's sampling noise from the fit seasons' split halves. With halves of
  n1 and n2 snaps, var(z_odd - z_even) ~ a (1/n1 + 1/n2), so a full season of n snaps has
  sd sqrt(a / n); the 90% interval is the coordinate +/- 1.645 sd.
- **Shrinkage:** players under `MIN_SNAPS` are placed in the space and pulled toward their
  group's mean (on the fit rows) by w = snaps / (snaps + MIN_SNAPS); w = 1 from `MIN_SNAPS` on.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import polars as pl
from scipy.linalg import orthogonal_procrustes

c = pl.col
K = 6
MIN_SNAPS = 200
Z90 = 1.6449
PAIR = ["gsis_id", "team", "season", "side", "group"]


@dataclass
class Space:
    """One side's fitted space: standardization, rotated loadings, group means and axis noise."""

    side: str
    features: list[str]
    mean: np.ndarray
    scale: np.ndarray
    loadings: np.ndarray  # K x p, rows orthonormal
    explained: np.ndarray  # share of the fit rows' variance on each axis
    seasons: tuple[int, ...]
    group_means: dict[str, np.ndarray] = field(default_factory=dict)
    noise: np.ndarray | None = None  # a per axis: sd of a season of n snaps = sqrt(a / n)

    @property
    def version(self) -> int:
        """A version is named for the last season its fit saw."""
        return max(self.seasons)

    @property
    def axes(self) -> list[str]:
        return [f"{self.side[0]}z{i}" for i in range(self.loadings.shape[0])]

    def project(self, frame: pl.DataFrame) -> np.ndarray:
        x = frame.select(self.features).to_numpy().astype(float)
        return ((x - self.mean) / self.scale) @ self.loadings.T


def _fit_rows(feats: pl.DataFrame, side: str, seasons: Sequence[int]) -> pl.DataFrame:
    return feats.filter(
        (c("side") == side) & (c("half") == "all") & (c("snaps") >= MIN_SNAPS)
        & c("season").is_in(list(seasons))
    )  # fmt: skip


def _pca(x: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Principal axes (k x p) of the centred matrix, signs fixed so each axis's largest loading is
    positive, and each axis's share of the variance."""
    _, s, vt = np.linalg.svd(x - x.mean(0), full_matrices=False)
    vt = vt[:k]
    vt *= np.sign(vt[np.arange(k), np.abs(vt).argmax(1)])[:, None]
    return vt, (s[:k] ** 2) / (s**2).sum()


def align(loadings: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """`loadings` rotated (within their span) to be closest to `ref`'s (orthogonal Procrustes)."""
    r, _ = orthogonal_procrustes(loadings.T, ref.T)
    return (loadings.T @ r).T


def fit_space(
    feats: pl.DataFrame,
    side: str,
    features: Sequence[str],
    seasons: Sequence[int],
    ref: Space | None = None,
    k: int = K,
) -> Space:
    """One side's space fit on `seasons` (rows from `features.features`, all halves), rotated to
    `ref`'s axes when given."""
    rows = _fit_rows(feats, side, seasons)
    x = rows.select(features).to_numpy().astype(float)
    mean, scale = x.mean(0), x.std(0)
    scale[scale == 0] = 1.0
    xs = (x - mean) / scale
    load, _ = _pca(xs, k)
    if ref is not None:
        load = align(load, ref.loadings)
    z = xs @ load.T
    explained = z.var(0) / xs.var(0).sum()
    sp = Space(side, list(features), mean, scale, load, explained, tuple(sorted(seasons)))
    groups = rows["group"].to_numpy()
    sp.group_means = {g: z[groups == g].mean(0) for g in np.unique(groups)}
    sp.noise = _noise(sp, feats, rows)
    return sp


def _noise(sp: Space, feats: pl.DataFrame, rows: pl.DataFrame) -> np.ndarray:
    """a per axis from the fit rows' split halves (module docstring)."""
    halves = feats.join(rows.select(PAIR), on=PAIR, how="semi")
    od, ev = halves.filter(c("half") == "odd"), halves.filter(c("half") == "even")
    both = od.select(PAIR).join(ev.select(PAIR), on=PAIR)
    od = both.join(od, on=PAIR, how="left")
    ev = both.join(ev, on=PAIR, how="left")
    ok = (od["snaps"] > 0).to_numpy() & (ev["snaps"] > 0).to_numpy()
    d = sp.project(od)[ok] - sp.project(ev)[ok]
    inv = (1 / od["snaps"].to_numpy()[ok] + 1 / ev["snaps"].to_numpy()[ok])[:, None]
    return (d**2).sum(0) / inv.sum(0)


def place(sp: Space, feats: pl.DataFrame) -> pl.DataFrame:
    """Every row's coordinates in `sp` (raw), the shrinkage weight, the shrunk coordinates and
    their 90% intervals. Keys, `half` and `snaps` kept."""
    z = sp.project(feats)
    n = feats["snaps"].to_numpy().astype(float)
    w = np.where(n >= MIN_SNAPS, 1.0, n / (n + MIN_SNAPS))
    gm = np.vstack([sp.group_means.get(g, np.zeros(len(sp.axes))) for g in feats["group"]])
    zs = w[:, None] * z + (1 - w[:, None]) * gm
    sd = w[:, None] * np.sqrt(sp.noise[None, :] / np.maximum(n, 1)[:, None])
    cols = {}
    for i, a in enumerate(sp.axes):
        cols[f"{a}_raw"] = z[:, i]
        cols[a] = zs[:, i]
        cols[f"{a}_lo"] = zs[:, i] - Z90 * sd[:, i]
        cols[f"{a}_hi"] = zs[:, i] + Z90 * sd[:, i]
    return pl.concat(
        [feats.select(*PAIR, "half", "snaps"),
         pl.DataFrame(cols).with_columns(shrink_w=pl.Series(w), version=pl.lit(sp.version))],
        how="horizontal",
    )  # fmt: skip


def walk(
    feats: pl.DataFrame, side: str, features: Sequence[str], seasons: Sequence[int],
    first_fit: int | None = None,
) -> tuple[pl.DataFrame, dict[int, Space]]:  # fmt: skip
    """The walk-forward history: season s's rows placed by the fit on seasons up to s, each fit
    rotated to the one before. `first_fit`: the first season to publish (its fit sees every
    season from the first). Returns the placed rows and the fits by version."""
    seasons = sorted(seasons)
    first_fit = first_fit or seasons[0]
    fits: dict[int, Space] = {}
    out, ref = [], None
    for s in seasons:
        if s < first_fit:
            continue
        sp = fit_space(feats, side, features, [x for x in seasons if x <= s], ref)
        fits[s] = sp
        ref = sp
        out.append(place(sp, feats.filter((c("side") == side) & (c("season") == s))))
    return pl.concat(out), fits
