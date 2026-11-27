# ruff: noqa: E501
"""Retro 5, group A (the CEO, 2026-11-27: "Run group a now please"): I187, misses that don't shift should widen.

Participation's champion (trees_week, the pinned run 2abc96bc) is biased on three rare kinds of rows where a mean
shift didn't pay (retro 5, I9, I10, I4): no depth-chart slot, a mover's first 4 games with his new team, and a
Questionable listing on this game's report. If the miss there is mostly spread, the 80% range (q10 to q90) should
cover less than 80% on those rows, and widening it there should improve the range score.
Seasons 2016-2024 (the champion's walk); the 2025 vault is never read. Discovery only.

1. Coverage: the share of rows whose snap share lands inside q10-q90, by kind, and which side the misses fall on.
2. Widening, walk-forward: for each kind, a scale a on the range's two arms around q50 (q10' = q50 - a(q50 - q10),
   q90' = q50 + a(q90 - q50), clipped to 0-1), a picked from a grid (0.8 to 3.0) by the range score on that kind's
   rows in earlier seasons; scored on 2018-2024. The range score is the pinball loss averaged over q10, q50 and q90
   (the q50 doesn't move, so only the arms change). Gain: the share of the champion's range score removed, over all
   rows, 90% interval from 2,000 resamples of season-weeks. Rows of none of the kinds keep the champion's range.

Odds, written before any test (Claude, 2026-11-26, IDEAS.md I187): 60% coverage on at least two of the three kinds is
under 75%; 35% the widening improves the range score over all rows with an interval above 0.
Pass rules (written now, before the run): the first holds if 2+ kinds have coverage under 75%; the second if the
overall gain's 90% interval is above 0.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro5_i187_widen.py > projects/retro/explore/retro5_i187_widen.txt
"""

import os
from pathlib import Path

import numpy as np
import polars as pl

c = pl.col
D = Path(os.environ["PCF_DATA_DIR"])
T = D / "tables"
S = range(2015, 2025)
rng = np.random.default_rng(187)
GRID = np.round(np.arange(0.8, 3.01, 0.1), 2)


def rd(p, cols):
    return pl.concat([pl.read_parquet(T / p / f"season={s}" / "data.parquet", columns=cols) for s in S], how="diagonal_relaxed")


h = pl.read_parquet(D / "outputs/participation/trees_week/2abc96bcab5047f5b7d505416f538b0f/history.parquet", columns=["gsis_id", "game_id", "mean", "q10", "q50", "q90"])
ros = rd("player_game/roster", ["gsis_id", "game_id", "season", "week", "team", "position"])
snaps = rd("player_game/snaps", ["gsis_id", "game_id", "offense_pct"])
depth = rd("player_game/depth", ["gsis_id", "game_id"]).unique().with_columns(slot=pl.lit(True))
inj = rd("player_game/injury", ["gsis_id", "game_id", "report_status"]).filter(c("report_status") == "Questionable").select("gsis_id", "game_id").unique().with_columns(ques=pl.lit(True))
scale = 100.0 if snaps["offense_pct"].max() > 1.5 else 1.0
last_team = ros.sort("week").group_by("gsis_id", "season").agg(last_team=c("team").last()).with_columns(season=c("season") + 1)
first = (
    ros.sort("week").with_columns(k=pl.int_range(pl.len()).over("gsis_id", "season", "team"))
    .join(last_team, on=["gsis_id", "season"], how="inner")
    .filter((c("team") != c("last_team")) & (c("k") < 4))
    .select("gsis_id", "game_id").unique().with_columns(mover=pl.lit(True))
)
df = (
    h.join(ros, on=["gsis_id", "game_id"], how="inner")
    .join(snaps, on=["gsis_id", "game_id"], how="left")
    .join(depth, on=["gsis_id", "game_id"], how="left")
    .join(inj, on=["gsis_id", "game_id"], how="left")
    .join(first, on=["gsis_id", "game_id"], how="left")
    .with_columns(
        y=(c("offense_pct").fill_null(0.0) / scale), noslot=~c("slot").fill_null(False),
        ques=c("ques").fill_null(False), mover=c("mover").fill_null(False), blk=c("season") * 100 + c("week"),
    )
)
KINDS = ["noslot", "mover", "ques"]
NAMES = {"noslot": "no depth-chart slot", "mover": "a mover's first 4 games", "ques": "Questionable"}
df = df.with_columns(none=~pl.any_horizontal(KINDS))
print(f"rows {df.height}, seasons {df['season'].min()}-{df['season'].max()}: " + ", ".join(f"{NAMES[k]} {df[k].sum()}" for k in KINDS))


def pb(y, q, lv):
    d = y - q
    return np.maximum(lv * d, (lv - 1) * d)


def rs(y, q10, q50, q90):
    """The range score of each row (pinball averaged over q10, q50, q90)."""
    return (pb(y, q10, 0.1) + pb(y, q50, 0.5) + pb(y, q90, 0.9)) / 3


def widen(f, a):
    q50 = f["q50"].to_numpy()
    return np.clip(q50 - a * (q50 - f["q10"].to_numpy()), 0, 1), np.clip(q50 + a * (f["q90"].to_numpy() - q50), 0, 1)


print("\n== 1. coverage of the 80% range (q10 to q90), 2016-2024")
cov = {}
for k in KINDS + ["none"]:
    sub = df.filter(c(k))
    y, lo, hi = sub["y"].to_numpy(), sub["q10"].to_numpy(), sub["q90"].to_numpy()
    inside = ((y >= lo) & (y <= hi)).mean()
    cov[k] = inside
    zero = (y == 0).mean()
    print(f"  {NAMES.get(k, 'none of the three'):<26} rows {sub.height:>6}: inside {inside:.1%}, below q10 {(y < lo).mean():.1%}, above q90 {(y > hi).mean():.1%}; played 0 snaps {zero:.1%}; mean miss {100 * (y - sub['mean'].to_numpy()).mean():+.2f} points")

print("\n== 2. widening by kind, walk-forward (a picked on earlier seasons' rows of that kind)")
parts = []
picked = {k: {} for k in KINDS}
for s in range(2018, 2025):
    te = df.filter(c("season") == s)
    lo, hi = te["q10"].to_numpy().copy(), te["q90"].to_numpy().copy()
    # a row of two kinds takes the larger scale
    best_a = np.ones(te.height)
    for k in KINDS:
        tr = df.filter((c("season") < s) & c(k))
        y = tr["y"].to_numpy()
        sc = [rs(y, *(lambda w: (w[0], tr["q50"].to_numpy(), w[1]))(widen(tr, a))).mean() for a in GRID]
        a = float(GRID[int(np.argmin(sc))])
        picked[k][s] = a
        m = te[k].to_numpy()
        best_a = np.where(m, np.maximum(best_a, a), best_a)
    q50 = te["q50"].to_numpy()
    lo2, hi2 = np.clip(q50 - best_a * (q50 - lo), 0, 1), np.clip(q50 + best_a * (hi - q50), 0, 1)
    y = te["y"].to_numpy()
    parts.append(te.select("blk", *KINDS, "none").with_columns(e0=pl.Series(rs(y, lo, q50, hi)), e1=pl.Series(rs(y, lo2, q50, hi2)), in1=pl.Series((y >= lo2) & (y <= hi2))))
for k in KINDS:
    print(f"  {NAMES[k]:<26} scale by season: {picked[k]}")
o = pl.concat(parts)


def boot_gain(f, n=2000):
    blks = f["blk"].unique().to_numpy()
    idx = {b: g for (b,), g in f.group_by("blk")}
    s0 = {b: float(g["e0"].sum()) for b, g in idx.items()}
    s1 = {b: float(g["e1"].sum()) for b, g in idx.items()}
    est = 1 - sum(s1.values()) / sum(s0.values())
    v = []
    for _ in range(n):
        pick = rng.choice(blks, len(blks))
        v.append(1 - sum(s1[b] for b in pick) / sum(s0[b] for b in pick))
    return est, *np.percentile(v, [5, 95])


res = {}
for name, sub in [("all rows", o)] + [(NAMES[k], o.filter(c(k))) for k in KINDS]:
    est, lo, hi = boot_gain(sub)
    res[name] = (est, lo, hi)
    print(f"  {name:<26} rows {sub.height:>6}: range score {100 * est:+.3f}% better ({100 * lo:+.3f}% to {100 * hi:+.3f}%)" + (f"; coverage after {sub['in1'].mean():.1%}" if name != "all rows" else ""))

n_under = sum(cov[k] < 0.75 for k in KINDS)
print(f"\n== verdicts: coverage under 75% for {n_under} of 3 kinds (the bet: 2+): {'held' if n_under >= 2 else 'failed'}; "
      f"the widening's overall gain has an interval above 0: {'held' if res['all rows'][1] > 0 else 'failed'}")
