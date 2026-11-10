"""The CEO's spot-check of F20 (2026-11-09): the rematch ceiling, in depth.

The worry: F22 found that two games of one unit against *different* opponents agree at r +0.04 to
+0.05, while F20's nulls (the 3 games nearest the rematch's week) were near zero. If the right
baseline is +0.04 on each side, F20's matchup part could vanish. So:
1. Baselines from *all* the unit's other games, under F20's exclusions (first meeting leaves out
   both meetings; the other game leaves out itself and the first meeting) and under F22's (both
   games of a pair leave out both).
2. The expectation with home field added.
3. Strength removed in full (offense EPA + defense EPA allowed - league), not with the fitted
   weights below 1, which leave part of each unit's strength in the residual.
4. The pairs behind it, by name.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/spot_f20.py
"""

# ruff: noqa: E501
from __future__ import annotations

from collections import defaultdict

import numpy as np
import polars as pl
from rematch import Strength, load

c = pl.col
RNG = np.random.default_rng(20261115)
DRAWS = 1000


def model(s: pl.DataFrame, st: Strength, kind: str):
    """Return expect(row, skip) for the three expectations."""
    home = {
        r["game_id"]: r["game_id"].split("_")[-1]
        for r in s.select("game_id").unique().iter_rows(named=True)
    }
    league = {yr: float(v) for yr, v in s.group_by("season").agg(c("y").mean()).iter_rows()}
    X, y = [], []
    for r in s.iter_rows(named=True):
        so, sd = st.pair(r["season"], r["off"], r["dfn"], {r["game_id"]})
        if np.isfinite(so) and np.isfinite(sd):
            X.append((1.0, so, sd, float(home[r["game_id"]] == r["off"])))
            y.append(r["y"])
    X, y = np.array(X), np.array(y)
    if kind == "base":
        b = np.r_[np.linalg.lstsq(X[:, :3], y, rcond=None)[0], 0.0]
    elif kind == "home":
        b = np.linalg.lstsq(X, y, rcond=None)[0]
    else:
        b = None

    def expect(r, skip):
        so, sd = st.pair(r["season"], r["off"], r["dfn"], skip)
        if kind == "full":
            return so + sd - league[r["season"]]
        return b[0] + b[1] * so + b[2] * sd + b[3] * float(home[r["game_id"]] == r["off"])

    return expect, b


def rematches(s: pl.DataFrame):
    rows = s.to_dicts()
    by_off, by_dfn = defaultdict(list), defaultdict(list)
    for r in rows:
        by_off[(r["season"], r["off"])].append(r)
        by_dfn[(r["season"], r["dfn"])].append(r)
    out = []
    for (season, off), games in by_off.items():
        seen = defaultdict(list)
        for r in sorted(games, key=lambda r: r["week"]):
            seen[r["dfn"]].append(r)
        for dfn, meet in seen.items():
            if len(meet) == 2:
                g1, g2 = meet
                oth_o = [r for r in games if r["dfn"] != dfn]
                oth_d = [r for r in by_dfn[(season, dfn)] if r["off"] != off]
                out.append((season, off, dfn, g1, g2, oth_o, oth_d))
    return out


def run(s, st, kind):
    expect, b = model(s, st, kind)

    def res(r, skip):
        return r["y"] - expect(r, skip)

    real, base_o20, base_d20, base_o22, base_d22, cl, names = [], [], [], [], [], [], []
    for season, off, dfn, g1, g2, oth_o, oth_d in rematches(s):
        a = res(g1, {g1["game_id"], g2["game_id"]})
        e2 = res(g2, {g1["game_id"], g2["game_id"]})
        if not (np.isfinite(a) and np.isfinite(e2)) or not oth_o or not oth_d:
            continue
        # F20's scheme: first meeting fixed (skip both meetings), the other game skips itself and the first meeting
        po = np.mean([a * res(r, {g1["game_id"], r["game_id"]}) for r in oth_o])
        pd_ = np.mean([a * res(r, {g1["game_id"], r["game_id"]}) for r in oth_d])
        # F22's scheme: each pair's two games both skip both
        qo = np.mean(
            [
                res(g1, {g1["game_id"], r["game_id"]}) * res(r, {g1["game_id"], r["game_id"]})
                for r in oth_o
            ]
        )
        qd = np.mean(
            [
                res(g1, {g1["game_id"], r["game_id"]}) * res(r, {g1["game_id"], r["game_id"]})
                for r in oth_d
            ]
        )
        real.append(a * e2)
        base_o20.append(po)
        base_d20.append(pd_)
        base_o22.append(qo)
        base_d22.append(qd)
        cl.append((season, *sorted((off, dfn))))
        names.append((season, off, dfn, g1["week"], g2["week"], a, e2))
    real, base_o20, base_d20, base_o22, base_d22 = map(
        np.array, (real, base_o20, base_d20, base_o22, base_d22)
    )
    # residual variance from all sides under this expectation (each game leaving out itself)
    allres = np.array([res(r, {r["game_id"]}) for r in s.iter_rows(named=True)])
    v = float(np.nanvar(allres))
    groups = defaultdict(list)
    for k, g in enumerate(cl):
        groups[g].append(k)
    keys = list(groups)
    boots = []
    for _ in range(DRAWS):
        idx = np.concatenate([groups[keys[p]] for p in RNG.choice(len(keys), len(keys))])
        boots.append((real[idx].mean() - base_o20[idx].mean() - base_d20[idx].mean()) / v)
    m20 = (real.mean() - base_o20.mean() - base_d20.mean()) / v
    m22 = (real.mean() - base_o22.mean() - base_d22.mean()) / v
    lo, hi = np.quantile(boots, [0.05, 0.95])
    label = {
        "base": "F20's expectation (fitted weights)",
        "home": "plus home field",
        "full": "strength removed in full",
    }[kind]
    w = "" if b is None else f" (weights: offense {b[1]:.2f}, defense {b[2]:.2f}, home {b[3]:+.3f})"
    print(f"\n== {label}{w}: {len(real):,} rematches; residual sd {np.sqrt(v):.3f}")
    print(f"   rematch r {real.mean() / v:+.3f}")
    print(
        f"   baselines from ALL other games, F20's exclusions: offense {base_o20.mean() / v:+.3f}, defense {base_d20.mean() / v:+.3f} → pairing's share {m20:+.1%} (90% {lo:+.1%} to {hi:+.1%})"
    )
    print(
        f"   baselines from ALL other games, F22's exclusions: offense {base_o22.mean() / v:+.3f}, defense {base_d22.mean() / v:+.3f} → pairing's share {m22:+.1%}"
    )
    return names, v


def main() -> None:
    s = load()
    st = Strength(s)
    names = None
    for kind in ("base", "home", "full"):
        n, v = run(s, st, kind)
        if kind == "base":
            names, vb = n, v
    sd = np.sqrt(vb)
    print("\n== 4. The pairs behind it (F20's expectation): both meetings beyond strength, in sd")
    both = sorted(names, key=lambda x: -(x[5] * x[6]))
    print("   Largest repeats, same direction (offense against defense, season, weeks):")
    for season, off, dfn, w1, w2, a, e2 in [x for x in both if x[5] > 0][:8]:
        print(
            f"      {season} {off} offense vs {dfn} defense, weeks {w1} and {w2}: {a / sd:+.1f} and {e2 / sd:+.1f}"
        )
    for season, off, dfn, w1, w2, a, e2 in [x for x in both if x[5] < 0][:5]:
        print(
            f"      {season} {off} offense vs {dfn} defense, weeks {w1} and {w2}: {a / sd:+.1f} and {e2 / sd:+.1f}"
        )
    x = np.array([n[5] for n in names]) / sd
    y = np.array([n[6] for n in names]) / sd
    for lo, hi, lab in (
        (1.0, 9, "first meeting +1 sd or more"),
        (-9, -1.0, "first meeting −1 sd or less"),
        (-1.0, 1.0, "in between"),
    ):
        w = (x >= lo) & (x < hi)
        print(f"   {lab}: {w.sum()} rematches; the rematch averages {y[w].mean():+.2f} sd")


if __name__ == "__main__":
    main()
