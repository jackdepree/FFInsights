# ruff: noqa: E501
"""Retro 4, group A: I28, a playoff flag for schemes-v2's traits.

I28 (Claude, 2026-11-10; odds 2026-11-15: medium, about 75%, that it holds at about the stated sizes on playoff
rows only): playoff teams pass more over expected, use the shotgun more and play slower than their regular-season
forecast. In-sample sizes (schemes-v2 RESULTS, Where it misses): +0.013 pass rate over expected, +0.015 shotgun,
+0.47 seconds a snap.

The test, walk-forward: for each season s from 2017, the flag is the mean playoff miss (actual less schemes-v2's
saved forecast) over playoff games of seasons before s; it's added to season s's playoff forecasts. Scored on
playoff rows (the schedule's game_type, not the week number) by squared error, flag against no flag, with a 90%
bootstrap over playoff rounds (season-week). Holds if the interval is above 0 for a trait.
Also: the same teams' last three regular-season games (a placebo: is it the playoffs, or late season, or good teams?).
The vault (2025) isn't read.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro4_i28_playoffs.py > projects/retro/explore/retro4_i28_playoffs.txt
"""

import glob
import os

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.tables import load

c = pl.col
OUT = get_config().zone("outputs") / "schemes-v2"
KEYS = ["game_id", "team"]
VARIANTS = {"pass_oe_rung2": "pass rate over expected", "shotgun_rung2": "shotgun rate", "tempo_shrunk": "seconds a snap"}


def history(variant):
    runs = glob.glob(str(OUT / variant / "*" / "history.parquet"))
    for f in sorted(runs, key=os.path.getmtime, reverse=True):
        h = pl.read_parquet(f)
        if not h["game_id"].str.starts_with("2025").all():
            return h.filter(~c("game_id").str.starts_with("2025"))
    raise FileNotFoundError(variant)


tg = load("team_game", parts=["pregame", "tendencies"])
sch = pl.concat([pl.read_parquet(f) for f in glob.glob(str(get_config().zone("tables") / "team_game" / "schedule" / "*" / "*.parquet"))], how="diagonal_relaxed")
sch = sch.select(*KEYS, "season", "week", "game_type")
post = sch.filter(c("game_type") != "REG").select("team", "season").unique()
last_reg = sch.filter(c("game_type") == "REG").join(post, on=["team", "season"], how="semi").sort("week").group_by("team", "season").tail(3).select(KEYS)
rng = np.random.default_rng(4)

for v, lab in VARIANTS.items():
    h = history(v)
    q = h["quantity"][0]
    d = h.select(*KEYS, "mean").join(tg.select(*KEYS, y=c(q).cast(pl.Float64)), on=KEYS).drop_nulls("y").join(sch, on=KEYS)
    d = d.with_columns(miss=c("y") - c("mean"), po=c("game_type") != "REG")
    p = d.filter(c("po"))
    rows = []
    for s in range(2017, 2025):
        prior = p.filter(c("season") < s)["miss"].mean()
        rows.append(p.filter(c("season") == s).with_columns(flag=pl.lit(prior)))
    r = pl.concat(rows).with_columns(e0=c("miss") ** 2, e1=(c("miss") - c("flag")) ** 2, rnd=c("season") * 100 + c("week"))
    g = r.group_by("rnd").agg(e0=c("e0").sum(), e1=c("e1").sum())
    e0, e1 = g["e0"].to_numpy(), g["e1"].to_numpy()
    gain = 1 - e1.sum() / e0.sum()
    bs = []
    for _ in range(2000):
        i = rng.integers(0, len(g), len(g))
        bs.append(1 - e1[i].sum() / e0[i].sum())
    lo, hi = np.percentile(bs, [5, 95])
    lr = d.join(last_reg, on=KEYS, how="semi")
    print(f"\n== {lab} ({v})")
    print(f"  playoff rows 2016-2024: {p.height}; mean miss {p['miss'].mean():+.4f}; by season: " + ", ".join(f"{s} {x:+.3f}" for s, x in p.group_by("season").agg(m=c("miss").mean()).sort("season").iter_rows()))
    print(f"  the walk-forward flag (2017-2024, {r.height} rows): squared error {1 - gain:.3f} of the unflagged; gain {gain:+.1%} (90% {lo:+.1%} to {hi:+.1%}) -> {'holds' if lo > 0 else 'not clear'}")
    print(f"  the flag's size in 2024: {rows[-1]['flag'][0]:+.4f}")
    print(f"  placebo, the same teams' last 3 regular-season games: {lr.height} rows, mean miss {lr['miss'].mean():+.4f}; all other regular-season rows {d.filter(~c('po')).join(last_reg, on=KEYS, how='anti')['miss'].mean():+.4f}")
