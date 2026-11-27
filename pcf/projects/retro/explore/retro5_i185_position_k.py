# ruff: noqa: E501
"""Retro 5, the quick group: I185, a k per position (stabilization's case against).

Stabilization's M1 pulls a player's centred rate by n / (n + k), with one k per rate pooled over positions (each
position centred by its own season mean first). Here: the same, but k fit within each position (on seasons up to the
input season, as the shipped k is), against the pooled k, on next season's rate. Stabilization's cached inputs (the
shipped run's player games, with I180's correction), targets 2018-2024 (its test seasons); the 2025 vault is never
read. Score: the share of the pooled M1's weighted squared error (weights: next season's attempts) removed, 90%
interval from 2,000 resamples of players. Rule k: the pooled k is the simpler side, so the per-position k counts only
with an interval above 0. Positions with fewer than 60 player-seasons in a fit keep the pooled k.

Odds, written before any test (Claude, 2026-11-26, IDEAS.md): 30% clear for 2+ of 20 rates (F37 is the case
against); 0.5-2% where it is.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro5_i185_position_k.py > projects/retro/explore/retro5_i185_position_k.txt
"""

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import nextseason as N
from pcf.experts.stabilization import rates as R
from pcf.experts.stabilization import walks as W
from pcf.validation import stabilize as S

c = pl.col
rng = np.random.default_rng(185)
MIN_ROWS = 60


def season_m1_by_pos(rows, games, pooled):
    """season_m1 with k fit within each position (pooled k where a position is thin)."""
    out = []
    for s in range(int(rows["season"].min()), K.LAST + 1):
        a = R.centred(rows.filter(c("season") == s), "pos")
        if a.height == 0:
            continue
        kp = pooled.filter(c("season") == s)["k"]
        k_pool = float(kp[0]) if kp.len() else float("nan")
        ks = {}
        for pos in a["pos"].unique().to_list():
            rp = rows.filter((c("pos") == pos) & (c("season") <= s))
            if R.centred(rp, "pos").height < MIN_ROWS:
                ks[pos] = k_pool
                continue
            gp = games.filter(c("gsis_id").is_in(rp["gsis_id"].unique().implode()))
            f = R.fit_k(rp, gp, s)
            ks[pos] = f["k"] if np.isfinite(f["k"]) and f["k"] > 0 else k_pool
        out.append(a.with_columns(n=c("den"), k=c("pos").replace_strict(ks, return_dtype=pl.Float64)).with_columns(m1=S.shrink_expr("x", "n", "k")))
    return pl.concat(out)


inp = W.Inputs()
print(f"{'rate':<30}{'pairs':>7}  {'gain (90%)':<28} k pooled (2024) -> by position (2024)")
clear = 0
for m in K.MEASURES:
    rows, games = inp.rows[m.name], inp.games[m.name]
    sm = inp.sm(m.name)
    sp = season_m1_by_pos(rows, games, sm)
    p0 = N.pairs(sm, rows).filter(c("target").is_between(2018, 2024))
    p1 = N.pairs(sp, rows).filter(c("target").is_between(2018, 2024))
    j = p0.select("gsis_id", "season", "y", "w", m0="m1").join(p1.select("gsis_id", "season", m1="m1"), on=["gsis_id", "season"])
    e0 = (j["w"] * (j["y"] - j["m0"]) ** 2).to_numpy()
    e1 = (j["w"] * (j["y"] - j["m1"]) ** 2).to_numpy()
    ids = j["gsis_id"].to_numpy()
    u, inv = np.unique(ids, return_inverse=True)
    s0, s1 = np.bincount(inv, e0), np.bincount(inv, e1)
    est = 1 - s1.sum() / s0.sum()
    v = []
    for _ in range(2000):
        pick = rng.integers(0, len(u), len(u))
        v.append(1 - s1[pick].sum() / s0[pick].sum())
    lo, hi = np.percentile(v, [5, 95])
    clear += lo > 0
    k24 = sp.filter(c("season") == 2023).group_by("pos").agg(k=c("k").first(), n=pl.len()).sort("n", descending=True)
    kp = sm.filter(c("season") == 2023)["k"][0]
    print(f"{m.label:<30}{j.height:>7}  {100 * est:+.2f}% ({100 * lo:+.2f}% to {100 * hi:+.2f}%){'  clear' if lo > 0 else ('  worse' if hi < 0 else '')}   {kp:.0f} -> " + ", ".join(f"{r['pos']} {r['k']:.0f}" for r in k24.iter_rows(named=True)))
print(f"\n== the per-position k is clearly better for {clear} of {len(K.MEASURES)} rates (the bet: 2+)")
