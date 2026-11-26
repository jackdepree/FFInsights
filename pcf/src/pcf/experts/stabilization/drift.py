"""The in-season local-level filter (the agreed brief, rung 4; decision 0052, call 6).

His true rate (centred by last season's class mean) takes a random step each game (variance q)
and a larger one each offseason (q_s), and each game shows it with noise. The noise of a game
with n attempts is `phi * sigma2 / n + omega`: phi = 1 and omega = 0 is the brief's filter;
phi is I154's game-noise factor and omega I182's fixed per-game extra.

q, q_s (and phi or omega where asked) are chosen on a grid by the likelihood of training games
only (seasons before the test season). The filter itself is causal: its state after a game uses
that game and earlier ones only, so running it over every season and reading the test season's
states is point-in-time once the parameters are fit on earlier seasons.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

c = pl.col
Q_GRID = (0.0, 0.001, 0.003, 0.01, 0.03, 0.1)  # q as a share of the true spread, per game
QS_GRID = (0.0, 0.03, 0.1, 0.3, 1.0)  # q_s, per offseason
PHI_GRID = (1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5)  # I154
OMEGA_GRID = (0.0, 0.1, 0.3, 1.0, 3.0, 10.0)  # I182, as a share of the true spread


@dataclass
class Padded:
    """Entity-by-game arrays (games in time order, padded): d (centred rate), n (attempts),
    new_season, real, the row map."""

    rows: pl.DataFrame
    D: np.ndarray
    N: np.ndarray
    NS: np.ndarray
    REAL: np.ndarray
    SEASON: np.ndarray


def pad(df: pl.DataFrame, ent: str) -> Padded:
    """`df`: one row per entity-game (ent, season, week, d, n, ...), any order."""
    df = df.sort(ent, "season", "week").with_columns(
        j=pl.int_range(pl.len()).over(ent),
        e=c(ent).rank("dense") - 1,
        new_season=(c("season") != c("season").shift(1).over(ent)).fill_null(False),
    )
    P_, J = int(df["e"].max()) + 1, int(df["j"].max()) + 1
    e, j = df["e"].to_numpy(), df["j"].to_numpy()
    D, N = np.zeros((P_, J)), np.zeros((P_, J))
    NS, REAL = np.zeros((P_, J), bool), np.zeros((P_, J), bool)
    SEASON = np.zeros((P_, J), np.int32)
    D[e, j], N[e, j] = df["d"].to_numpy(), df["n"].to_numpy()
    NS[e, j], REAL[e, j] = df["new_season"].to_numpy(), True
    SEASON[e, j] = df["season"].to_numpy()
    return Padded(df, D, N, NS, REAL, SEASON)


def run(
    L: Padded,
    q: float,
    qs: float,
    sigma2: float,
    tau2: float,
    phi: float = 1.0,
    omega: float = 0.0,
    train_before: int | None = None,
):
    """The filter over every entity at once. Returns (m, P, z2, loglik): the post-game level and
    its variance at each cell, each game's squared standardized surprise, and the log-likelihood
    of the games before season `train_before` (all games if None)."""
    P_, J = L.D.shape
    m, P = np.zeros(P_), np.full(P_, tau2)
    mp, pp, zz = np.zeros((P_, J)), np.zeros((P_, J)), np.zeros((P_, J))
    ll = 0.0
    for j in range(J):
        r = L.REAL[:, j]
        P = P + np.where(r, np.where(L.NS[:, j], qs, q), 0.0)
        R = np.where(r, phi * sigma2 / np.maximum(L.N[:, j], 1e-9) + omega, np.inf)
        S = P + R
        v = L.D[:, j] - m
        t = r if train_before is None else r & (L.SEASON[:, j] < train_before)
        ll += float(np.sum(-0.5 * (np.log(S[t]) + v[t] ** 2 / S[t])))
        zz[:, j] = np.where(r, v**2 / S, 0.0)
        K = np.where(r, P / S, 0.0)
        m = m + K * np.where(r, v, 0.0)
        P = P * (1 - K)
        mp[:, j], pp[:, j] = m, P
    return mp, pp, zz, ll


def fit(L: Padded, sigma2: float, tau2: float, train_before: int, noise: str = "plain") -> dict:
    """q and q_s (and phi for noise="factor", omega for noise="fixed") by training likelihood.
    The noise parameter is found by coordinate search: q and q_s on their grid at phi = 1 (omega
    = 0), then the noise grid, then q and q_s again."""

    def best_qq(phi, omega):
        out = None
        for a in Q_GRID:
            for b in QS_GRID:
                ll = run(L, a * tau2, b * tau2, sigma2, tau2, phi, omega * tau2, train_before)[3]
                if out is None or ll > out[0]:
                    out = (ll, a, b)
        return out

    ll, a, b = best_qq(1.0, 0.0)
    phi, omega = 1.0, 0.0
    if noise != "plain":
        grid = PHI_GRID if noise == "factor" else OMEGA_GRID
        best = (ll, phi if noise == "factor" else omega)
        for g in grid:
            p_, o_ = (g, 0.0) if noise == "factor" else (1.0, g)
            l2 = run(L, a * tau2, b * tau2, sigma2, tau2, p_, o_ * tau2, train_before)[3]
            if l2 > best[0]:
                best = (l2, g)
        phi, omega = (best[1], 0.0) if noise == "factor" else (1.0, best[1])
        ll, a, b = best_qq(phi, omega)
    return {
        "q": a * tau2,
        "qs": b * tau2,
        "q_share": a,
        "qs_share": b,
        "phi": phi,
        "omega": omega * tau2,
        "omega_share": omega,
        "loglik": ll,
    }


def states(L: Padded, par: dict, sigma2: float, tau2: float) -> pl.DataFrame:
    """The padded rows with the filter's post-game level `m`, its variance `P` and each game's
    squared surprise `z2`."""
    mp, pp, zz, _ = run(L, par["q"], par["qs"], sigma2, tau2, par["phi"], par["omega"])
    e, j = L.rows["e"].to_numpy(), L.rows["j"].to_numpy()
    return L.rows.with_columns(m=pl.Series(mp[e, j]), P=pl.Series(pp[e, j]), z2=pl.Series(zz[e, j]))
