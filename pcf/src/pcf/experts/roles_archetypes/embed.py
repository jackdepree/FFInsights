"""The exploratory method (brief, method 3): a small autoencoder per side, on the same standardized
features as the pooled PCA, with a 6-number middle layer (decision 0048).

p -> 16 -> 6 -> 16 -> p, tanh between, linear in and out of the middle; full-batch Adam with a
little weight decay, a fixed number of epochs. Its codes are standardized on the fit rows and
rotated to the PCA's coordinates on the same rows (orthogonal Procrustes), so axis i reads like
PCA's axis i where it can and the two are compared like for like. Seeds measure its fitting noise.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl
import torch
from scipy.linalg import orthogonal_procrustes

from pcf.experts.roles_archetypes.space import MIN_SNAPS, PAIR, Space, _fit_rows

c = pl.col
HIDDEN = 16
EPOCHS = 1500
LR = 0.01
DECAY = 1e-4


@dataclass
class Embedding:
    """One side's fitted autoencoder: the PCA space it borrows standardization and axes from."""

    space: Space
    encoder: torch.nn.Module
    code_mean: np.ndarray
    code_scale: np.ndarray
    rotation: np.ndarray
    seed: int
    loss: float

    @property
    def axes(self) -> list[str]:
        return [f"{self.space.side[0]}e{i}" for i in range(self.rotation.shape[0])]

    def project(self, frame: pl.DataFrame) -> np.ndarray:
        sp = self.space
        x = (frame.select(sp.features).to_numpy().astype(float) - sp.mean) / sp.scale
        with torch.no_grad():
            h = self.encoder(torch.tensor(x, dtype=torch.float32)).numpy().astype(float)
        return ((h - self.code_mean) / self.code_scale) @ self.rotation


def _nets(p: int, k: int) -> tuple[torch.nn.Module, torch.nn.Module]:
    enc = torch.nn.Sequential(
        torch.nn.Linear(p, HIDDEN), torch.nn.Tanh(), torch.nn.Linear(HIDDEN, k)
    )
    dec = torch.nn.Sequential(
        torch.nn.Linear(k, HIDDEN), torch.nn.Tanh(), torch.nn.Linear(HIDDEN, p)
    )
    return enc, dec


def fit_embedding(feats: pl.DataFrame, sp: Space, seed: int = 0) -> Embedding:
    """An autoencoder on `sp`'s fit rows and features (same standardization), aligned to `sp`."""
    rows = _fit_rows(feats, sp.side, sp.seasons)
    x = (rows.select(sp.features).to_numpy().astype(float) - sp.mean) / sp.scale
    xt = torch.tensor(x, dtype=torch.float32)
    torch.manual_seed(seed)
    k = sp.loadings.shape[0]
    enc, dec = _nets(x.shape[1], k)
    opt = torch.optim.Adam([*enc.parameters(), *dec.parameters()], lr=LR, weight_decay=DECAY)
    loss = torch.tensor(0.0)
    for _ in range(EPOCHS):
        opt.zero_grad()
        loss = ((dec(enc(xt)) - xt) ** 2).mean()
        loss.backward()
        opt.step()
    enc.eval()
    with torch.no_grad():
        h = enc(xt).numpy().astype(float)
    mu, sd = h.mean(0), h.std(0)
    sd[sd == 0] = 1.0
    z_pca = sp.project(rows)
    target = (z_pca - z_pca.mean(0)) / z_pca.std(0)
    rot, _ = orthogonal_procrustes((h - mu) / sd, target)
    return Embedding(sp, enc, mu, sd, rot, seed, float(loss.detach()))


def explained(emb: Embedding) -> float:
    """Share of the fit rows' standardized variance the autoencoder reconstructs (1 - its final
    mean squared error, the total being 1 per feature)."""
    return 1.0 - emb.loss


def place(emb: Embedding, feats: pl.DataFrame) -> pl.DataFrame:
    """Every row's codes (keys, `half`, `snaps` kept), shrunk under `MIN_SNAPS` like the PCA's."""
    z = emb.project(feats)
    n = feats["snaps"].to_numpy().astype(float)
    w = np.where(n >= MIN_SNAPS, 1.0, n / (n + MIN_SNAPS))
    fit = _fit_rows(feats, emb.space.side, emb.space.seasons)
    gm = {}
    if fit.height:
        zf = emb.project(fit)
        g = fit["group"].to_numpy()
        gm = {k: zf[g == k].mean(0) for k in np.unique(g)}
    m = np.vstack([gm.get(g, np.zeros(z.shape[1])) for g in feats["group"]])
    zs = w[:, None] * z + (1 - w[:, None]) * m
    return feats.select(*PAIR, "half", "snaps").with_columns(
        pl.Series(a, zs[:, i]) for i, a in enumerate(emb.axes)
    )


def walk(feats: pl.DataFrame, fits: dict[int, Space], seeds: Sequence[int] = (0,)) -> pl.DataFrame:
    """The walk-forward codes: season s's rows from autoencoders fit with PCA's fit for s (each
    rotated to that fit's coordinates, which are rotated to the fit before), averaged over seeds
    after alignment."""
    out = []
    for s, sp in sorted(fits.items()):
        rows = feats.filter((c("side") == sp.side) & (c("season") == s))
        placed = [place(fit_embedding(feats, sp, seed), rows) for seed in seeds]
        first = placed[0]
        axes = [a for a in first.columns if a[1:2] == "e" and a[2:].isdigit()]
        mean = np.mean([p.select(axes).to_numpy() for p in placed], axis=0)
        out.append(first.with_columns(pl.Series(a, mean[:, i]) for i, a in enumerate(axes)))
    return pl.concat(out)
