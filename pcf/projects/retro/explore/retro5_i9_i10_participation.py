# ruff: noqa: E501
"""Retro 5, the quick group (the CEO, 2026-11-26: "We can leave quick ideas missed by a build to be tested by the retro"):
I9 and I10 on participation's champion (trees_week, the pinned run 2abc96bc), 2016-2024. Discovery only; the 2025
vault is never read.

I10 (no depth-chart slot): players with no row on this game's depth chart were over-projected for snaps by 3.3 points
of share (participation's first models). The champion already reads an `unlisted` flag, so the bet is that it's gone.
I9 (movers' first games): a mover's first 4 games for his new team were over-projected (-0.9 points, 2026-11-15).
The test vacated's build wrote and didn't run: his new group's offseason unclaimed share (vacated-offseason's
`departed_share`, the share the group's departed players held) as a walk-forward correction.

Odds, written before this script was run (2026-11-26):
- I10: 40% the champion still over-forecasts no-slot rows by 1+ point of share (mean miss below -0.01 with its 90%
  interval below 0); 20% a walk-forward shift on those rows lowers the champion's squared error over all rows with an
  interval above 0; size under 0.2% overall if so.
- I9: 40% (vacated's PREREG, 2026-11-25) the unclaimed share lowers participation's squared error on movers' first 4
  games with an interval above 0, about 0.2-0.5 points of share; 50% the champion's mean miss on those games is still
  below 0 with its interval below 0.

Intervals: 2,000 resamples of whole season-weeks. Run from pcf/:
    PCF_DATA_DIR=... python projects/retro/explore/retro5_i9_i10_participation.py > projects/retro/explore/retro5_i9_i10_participation.txt
"""

import os
from pathlib import Path

import numpy as np
import polars as pl

c = pl.col
D = Path(os.environ["PCF_DATA_DIR"])
T = D / "tables"
S = range(2015, 2025)
rng = np.random.default_rng(20261126)


def rd(p, cols):
    return pl.concat([pl.read_parquet(T / p / f"season={s}" / "data.parquet", columns=cols) for s in S], how="diagonal_relaxed")


h = pl.read_parquet(D / "outputs/participation/trees_week/2abc96bcab5047f5b7d505416f538b0f/history.parquet", columns=["gsis_id", "game_id", "mean"])
ros = rd("player_game/roster", ["gsis_id", "game_id", "season", "week", "team", "position"])
snaps = rd("player_game/snaps", ["gsis_id", "game_id", "offense_pct"])
depth = rd("player_game/depth", ["gsis_id", "game_id"]).unique().with_columns(slot=pl.lit(True))
scale = 100.0 if snaps["offense_pct"].max() > 1.5 else 1.0
df = (
    h.join(ros, on=["gsis_id", "game_id"], how="inner")
    .join(snaps, on=["gsis_id", "game_id"], how="left")
    .join(depth, on=["gsis_id", "game_id"], how="left")
    .with_columns(y=(c("offense_pct").fill_null(0.0) / scale), slot=c("slot").fill_null(False))
    .with_columns(r=c("y") - c("mean"), blk=c("season") * 100 + c("week"))
)
print(f"rows {df.height}, seasons {df['season'].min()}-{df['season'].max()}, no slot {(~df['slot']).sum()} ({(~df['slot']).mean():.1%})")


def boot(frame, stat, n=2000):
    """stat(frame) and a 90% interval from resampled season-weeks."""
    blks = frame["blk"].unique().to_numpy()
    parts = {b: g for (b,), g in frame.group_by("blk")}
    est = stat(frame)
    vals = []
    for _ in range(n):
        pick = rng.choice(blks, len(blks))
        vals.append(stat(pl.concat([parts[b] for b in pick])))
    lo, hi = np.percentile(vals, [5, 95])
    return est, lo, hi


def mean_r(f):
    return float(f["r"].mean())


# ---------------------------------------------------------------- I10
print("\n== I10: the champion's mean miss (actual less forecast, share points), by depth-chart slot")
for flag in (False, True):
    sub = df.filter(c("slot") == flag)
    est, lo, hi = boot(sub, mean_r, 1000)
    print(f"  {'listed' if flag else 'no slot':<8} rows {sub.height:>6}: {100 * est:+.2f} ({100 * lo:+.2f} to {100 * hi:+.2f})")
print("  no slot, by season:", {s: round(100 * float(g["r"].mean()), 2) for (s,), g in sorted(df.filter(~c("slot")).group_by("season"))})
print("  no slot, by position (top 6):")
print(df.filter(~c("slot")).group_by("position").agg(rows=pl.len(), miss=(c("r").mean() * 100).round(2)).sort("rows", descending=True).head(6))

# walk-forward shift on no-slot rows, from earlier seasons
shift = {s: float(df.filter((~c("slot")) & (c("season") < s))["r"].mean()) for s in range(2017, 2025)}
print("  walk-forward shift by season (points):", {s: round(100 * v, 2) for s, v in shift.items()})
sc = df.filter(c("season") >= 2017).with_columns(
    f2=pl.when(~c("slot")).then((c("mean") + c("season").replace_strict(shift, return_dtype=pl.Float64)).clip(0, 1)).otherwise(c("mean"))
).with_columns(e0=(c("y") - c("mean")) ** 2, e1=(c("y") - c("f2")) ** 2)


def gain(f):
    return 1 - float(f["e1"].sum()) / float(f["e0"].sum())


for name, sub in (("all rows", sc), ("no-slot rows", sc.filter(~c("slot")))):
    est, lo, hi = boot(sub, gain, 1000)
    print(f"  the shift's gain, {name}: {100 * est:+.3f}% of squared error ({100 * lo:+.3f}% to {100 * hi:+.3f}%)")

# ---------------------------------------------------------------- I9
GROUP = {"WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB", "T": "OL", "G": "OL", "C": "OL", "OL": "OL", "OT": "OL", "OG": "OL"}
last_team = (
    ros.sort("week").group_by("gsis_id", "season").agg(last_team=c("team").last())
    .with_columns(season=c("season") + 1)
)
first = (
    ros.sort("week").with_columns(k=pl.int_range(pl.len()).over("gsis_id", "season", "team"))
    .join(last_team, on=["gsis_id", "season"], how="inner")
    .filter((c("team") != c("last_team")) & (c("k") < 4))
    .select("gsis_id", "game_id", "k")
)
vo = pl.read_parquet(next((D / "outputs/vacated-offseason").glob("*/history.parquet")))
dep = vo.filter(c("quantity") == "snap_share").group_by("team", "season", "group").agg(dep=c("departed_share").first())
mv = (
    df.join(first, on=["gsis_id", "game_id"], how="inner")
    .with_columns(group=c("position").replace_strict(GROUP, default=None))
    .filter(c("group").is_not_null())
    .join(dep, on=["team", "season", "group"], how="left")
)
print(f"\n== I9: movers' first 4 games with a new team: {mv.height} rows, {mv['gsis_id'].n_unique()} players; with an unclaimed share {mv['dep'].is_not_null().sum()}")
est, lo, hi = boot(mv, mean_r, 1000)
print(f"  the champion's mean miss: {100 * est:+.2f} points of share ({100 * lo:+.2f} to {100 * hi:+.2f})")
print(mv.group_by("group").agg(rows=pl.len(), miss=(c("r").mean() * 100).round(2), dep=c("dep").mean().round(3)).sort("group"))
mvd = mv.filter(c("dep").is_not_null())
print(f"  in-sample slope of the miss on the unclaimed share: {np.polyfit(mvd['dep'].to_numpy(), mvd['r'].to_numpy(), 1).round(4).tolist()} (slope, intercept)")

# walk-forward: r ~ a + b * dep, fit on earlier seasons' movers, per group pooled; the champion where dep is missing
rows = []
for s in range(2018, 2025):
    tr = mvd.filter(c("season") < s)
    te = mv.filter(c("season") == s)
    b, a = np.polyfit(tr["dep"].to_numpy(), tr["r"].to_numpy(), 1)
    rows.append(te.with_columns(f2=pl.when(c("dep").is_not_null()).then((c("mean") + a + b * c("dep")).clip(0, 1)).otherwise(c("mean"))))
    print(f"  {s}: slope {b:+.3f}, intercept {a:+.3f} (fit on {tr.height} rows)")
wf = pl.concat(rows).with_columns(e0=(c("y") - c("mean")) ** 2, e1=(c("y") - c("f2")) ** 2)
est, lo, hi = boot(wf, gain, 2000)
print(f"  the correction's gain on movers' first 4 games: {100 * est:+.2f}% of squared error ({100 * lo:+.2f}% to {100 * hi:+.2f}%)")
print(f"  root squared error, points of share: champion {100 * np.sqrt(wf['e0'].mean()):.2f}, corrected {100 * np.sqrt(wf['e1'].mean()):.2f}")
# the intercept alone (a plain movers' shift), to separate the unclaimed share from a constant
rows = []
for s in range(2018, 2025):
    a = float(mv.filter(c("season") < s)["r"].mean())
    rows.append(mv.filter(c("season") == s).with_columns(f2=(c("mean") + a).clip(0, 1)))
wc = pl.concat(rows).with_columns(e0=(c("y") - c("mean")) ** 2, e1=(c("y") - c("f2")) ** 2)
est, lo, hi = boot(wc, gain, 2000)
print(f"  a constant movers' shift alone: {100 * est:+.2f}% ({100 * lo:+.2f}% to {100 * hi:+.2f}%)")
