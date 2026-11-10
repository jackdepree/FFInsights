"""Scheme against scheme, option C (CEO, 2026-11-09): matchup traits learned from results.

The Netflix approach. Within a season, every offense gets a few hidden numbers (u) and every
defense a few (v), learned only from results, so that an offense's EPA per play against a defense
is the league mean + the offense's strength + the defense's + u · v. The u · v part is the matchup:
"offenses that do well against defense B also do well against defense B'" defines B and B' as alike,
whatever their charted styles. F20 says a within-season matchup part exists (about 9% of what
strength leaves); F21-F23 say charted styles don't find it. This asks whether results can.

- **Held out within each season:** sides are split into 10 folds; the model (strengths and k hidden
  numbers each, ridge penalty λ) is fitted on 9 and predicts the 10th. So the learned matchup part
  uses the season's other games, like the F20 ceiling (it is not a forecast).
- **Measure:** r between the held-out matchup part (u · v) and what the strength-only model (k = 0,
  same folds) misses. Split into sides whose pair met in the training folds (a rematch) and sides
  whose pair didn't (only the shared structure can help there).
- **No peeking:** k and λ are chosen on 2006-2014 and applied once to 2015-2024.
- **Null:** the same on 2015-2024 with each side's defense swapped among sides in the same week
  (50 times): this keeps every unit's schedule size and strength, and breaks real pairings.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/latent.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from rematch import load

c = pl.col
RNG = np.random.default_rng(20261113)
FOLDS = 10
ITERS = 30
SHUFFLES = 50
GRID = [(k, lam) for k in (1, 2, 3) for lam in (0.5, 1, 2, 4, 8)]
BIAS_LAM = 2.0  # ridge on strengths, in games' weight


def als(o, d, y, no, nd, k, lam, rng):
    """Biases and k factors by alternating ridge least squares on observed (o, d, y)."""
    mu = y.mean()
    a, b = np.zeros(no), np.zeros(nd)
    U = rng.normal(0, 0.01, (no, k)) if k else np.zeros((no, 0))
    V = rng.normal(0, 0.01, (nd, k)) if k else np.zeros((nd, 0))
    obs_o = [np.flatnonzero(o == i) for i in range(no)]
    obs_d = [np.flatnonzero(d == j) for j in range(nd)]
    for _ in range(ITERS if k else 5):
        inter = (U[o] * V[d]).sum(1) if k else 0.0
        r = y - mu - b[d] - inter
        a = np.array([r[ix].sum() / (len(ix) + BIAS_LAM) if len(ix) else 0.0 for ix in obs_o])
        r = y - mu - a[o] - inter
        b = np.array([r[ix].sum() / (len(ix) + BIAS_LAM) if len(ix) else 0.0 for ix in obs_d])
        if not k:
            continue
        r = y - mu - a[o] - b[d]
        for i, ix in enumerate(obs_o):
            if len(ix):
                Vi = V[d[ix]]
                U[i] = np.linalg.solve(Vi.T @ Vi + lam * np.eye(k), Vi.T @ r[ix])
        for j, ix in enumerate(obs_d):
            if len(ix):
                Uj = U[o[ix]]
                V[j] = np.linalg.solve(Uj.T @ Uj + lam * np.eye(k), Uj.T @ r[ix])
    return mu, a, b, U, V


def season_preds(t: pl.DataFrame, configs, rng, dfn_override=None):
    """Held-out strength-only miss and matchup parts for each config, for one season."""
    teams = sorted(set(t["off"].to_list()) | set(t["dfn"].to_list()))
    ix = {x: i for i, x in enumerate(teams)}
    o = np.array([ix[x] for x in t["off"].to_list()])
    d = np.array(
        [ix[x] for x in (dfn_override if dfn_override is not None else t["dfn"].to_list())]
    )
    y = t["y"].to_numpy()
    n = len(y)
    fold = rng.permutation(n) % FOLDS
    miss = np.zeros(n)
    parts = {cfg: np.zeros(n) for cfg in configs}
    seen = np.zeros(n, bool)
    pair = o * 100 + d
    for f in range(FOLDS):
        tr, te = fold != f, fold == f
        mu, a, b, _, _ = als(o[tr], d[tr], y[tr], len(teams), len(teams), 0, 0, rng)
        miss[te] = y[te] - (mu + a[o[te]] + b[d[te]])
        seen[te] = np.isin(pair[te], pair[tr])
        for k, lam in configs:
            _, _, _, U, V = als(o[tr], d[tr], y[tr], len(teams), len(teams), k, lam, rng)
            parts[(k, lam)][te] = (U[o[te]] * V[d[te]]).sum(1)
    return miss, parts, seen


def collect(s: pl.DataFrame, seasons, configs, rng, shuffle=False):
    miss, seen = [], []
    parts = {cfg: [] for cfg in configs}
    for yr in seasons:
        t = s.filter(c("season") == yr).sort("week", "game_id", "off")
        dfn = None
        if shuffle:
            dfn = t["dfn"].to_list()
            wk = t["week"].to_numpy()
            for w in np.unique(wk):
                i = np.flatnonzero(wk == w)
                p = rng.permutation(i)
                for a_, b_ in zip(i, p, strict=True):
                    dfn[a_] = t["dfn"][int(b_)]
            # an offense can't face itself; drop those rows from scoring by keeping them (rare) as is
        m, p, sn = season_preds(t, configs, rng, dfn)
        miss.append(m)
        seen.append(sn)
        for cfg in configs:
            parts[cfg].append(p[cfg])
    return (
        np.concatenate(miss),
        {k: np.concatenate(v) for k, v in parts.items()},
        np.concatenate(seen),
    )


def r(x, y):
    return float(np.corrcoef(x, y)[0, 1])


def main() -> None:
    s = load()
    print(f"sides {s.height:,}, 2006-2024 regular season")
    dev = range(2006, 2015)
    test = range(2015, 2025)
    miss, parts, seen = collect(s, dev, GRID, RNG)
    print(
        "\n== 1. Choosing k (hidden numbers per unit) and λ (ridge) on 2006-2014: r between the held-out matchup part and what strength misses"
    )
    best = max(GRID, key=lambda cfg: r(parts[cfg], miss))
    for cfg in GRID:
        print(
            f"   k {cfg[0]}, λ {cfg[1]:>4}: r {r(parts[cfg], miss):+.4f}{'   ← chosen' if cfg == best else ''}"
        )
    miss, parts, seen = collect(s, test, [best], RNG)
    rr = r(parts[best], miss)
    rs, ru = r(parts[best][seen], miss[seen]), r(parts[best][~seen], miss[~seen])
    nulls = []
    for _ in range(SHUFFLES):
        m0, p0, s0 = collect(s, test, [best], RNG, shuffle=True)
        nulls.append((r(p0[best], m0), r(p0[best][s0], m0[s0]), r(p0[best][~s0], m0[~s0])))
    nulls = np.array(nulls)
    print(
        f"\n== 2. Applied once to 2015-2024 (k {best[0]}, λ {best[1]}): {len(miss):,} held-out sides"
    )
    print(
        f"   all sides: r {rr:+.4f}; shuffled pairings at or above {np.mean(nulls[:, 0] >= rr):.0%} (95th {np.quantile(nulls[:, 0], 0.95):+.4f}); share of F20's ceiling (9.2%): {max(rr, 0) ** 2 / 0.092:.1%}"
    )
    print(
        f"   pair met in training folds ({seen.sum():,}): r {rs:+.4f}; shuffled at or above {np.mean(nulls[:, 1] >= rs):.0%}"
    )
    print(
        f"   pair not met ({(~seen).sum():,}): r {ru:+.4f}; shuffled at or above {np.mean(nulls[:, 2] >= ru):.0%}"
    )
    slope = np.polyfit(parts[best] / parts[best].std(), miss, 1)[0]
    print(f"   size: {slope:+.4f} EPA per play per sd of the matchup part")


if __name__ == "__main__":
    main()
