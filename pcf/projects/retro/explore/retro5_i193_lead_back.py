# ruff: noqa: E501
"""Retro 5, group A: I193, does a lead back carry his split? (from I86: the backfield split follows the lead back,
r 0.28-0.30 when he stays, under a new coach too, and 0.04 when he changes under the same coach).

The split, as in I86: the lead back's share of his team's running-back carries in a regular season (lead = most
carries). A lead back who moves: the lead at team A in season s who plays for team B (not A) in season s+1. The test:
team B's split in s+1 on his old split (A's in s) and on B's own last split (B's in s), OLS, 90% intervals from 2,000
resamples of moves. Primary: moves where he is B's lead again (the split is then his own share). Also all moves (B's
split, whoever leads), and his own share of B's carries.
Seasons 2006-2024; the 2025 vault is never read. Discovery only.

Odds, written before any test (Claude, 2026-11-26, IDEAS.md I193): 35% his old split adds with an interval above 0
(few moves, about 40); r about 0.2 if so. Pass rule (written now, before the run): on the primary moves, the old
split's OLS slope beside B's own last split has a 90% interval above 0.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro5_i193_lead_back.py > projects/retro/explore/retro5_i193_lead_back.txt
"""

import os
from pathlib import Path

import numpy as np
import polars as pl

c = pl.col
T = Path(os.environ["PCF_DATA_DIR"]) / "tables"
S = range(2006, 2025)
rng = np.random.default_rng(193)


def rd(p, cols):
    return pl.concat([pl.read_parquet(T / p / f"season={s}" / "data.parquet", columns=cols) for s in S], how="diagonal_relaxed")


sch = rd("team_game/schedule", ["game_id", "season", "team", "game_type"]).filter(c("game_type") == "REG")
ros = rd("player_game/roster", ["gsis_id", "game_id", "team", "position"]).filter(c("position").is_in(["RB", "FB"]))
st = rd("player_game/stats", ["gsis_id", "game_id", "carries"])
g = ros.join(st, on=["gsis_id", "game_id"]).join(sch, on=["game_id", "team"])
ts = g.group_by("team", "season", "gsis_id").agg(car=c("carries").fill_null(0).sum())
tot = ts.group_by("team", "season").agg(tot=c("car").sum())
lead = ts.sort("car", descending=True).group_by("team", "season").agg(lead=c("gsis_id").first(), top=c("car").first()).join(tot, on=["team", "season"])
lead = lead.with_columns(split=c("top") / c("tot"))
own = ts.join(tot, on=["team", "season"]).with_columns(share=c("car") / c("tot"))
# his teams in s+1 (most carries there if more than one)
nxt = own.sort("car", descending=True).group_by("gsis_id", "season").agg(team2=c("team").first(), share2=c("share").first(), car2=c("car").first())
nxt = nxt.with_columns(season=c("season") - 1)
mv = (
    lead.rename({"lead": "gsis_id"}).join(nxt, on=["gsis_id", "season"], how="inner").filter(c("team2") != c("team"))
    .join(lead.select(c("team").alias("team2"), (c("season") - 1).alias("season"), c("split").alias("b_next"), c("lead").alias("b_lead_next")), on=["team2", "season"])
    .join(lead.select(c("team").alias("team2"), "season", c("split").alias("b_prev")), on=["team2", "season"])
    .with_columns(lead_again=c("b_lead_next") == c("gsis_id"))
)
print(f"lead backs who moved (2006-07 to 2023-24): {mv.height}; lead again at the new team {mv['lead_again'].sum()}; median carries at the new team {mv['car2'].median():.0f}")


def ols_ci(x1, x2, y, n=2000):
    X = np.column_stack([np.ones(len(y)), x1, x2])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    v = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        v.append(np.linalg.lstsq(X[i], y[i], rcond=None)[0])
    v = np.array(v)
    return b, np.percentile(v, 5, axis=0), np.percentile(v, 95, axis=0)


def r_ci(x, y, n=2000):
    est = np.corrcoef(x, y)[0, 1]
    idx = rng.integers(0, len(x), (n, len(x)))
    v = [np.corrcoef(x[i], y[i])[0, 1] for i in idx]
    return est, *np.percentile(v, [5, 95])


out = {}
for name, sub, ycol in (
    ("primary: lead again at the new team (B's split)", mv.filter(c("lead_again")), "b_next"),
    ("all moves: B's split, whoever leads", mv, "b_next"),
    ("all moves: his own share of B's carries", mv, "share2"),
):
    a, b, y = sub["split"].to_numpy(), sub["b_prev"].to_numpy(), sub[ycol].to_numpy()
    ra, rb = r_ci(a, y), r_ci(b, y)
    coef, lo, hi = ols_ci(a, b, y)
    out[name] = (coef[1], lo[1], hi[1])
    print(f"\n== {name}: {sub.height} moves")
    print(f"  r with his old split {ra[0]:+.2f} ({ra[1]:+.2f} to {ra[2]:+.2f}); with B's own last split {rb[0]:+.2f} ({rb[1]:+.2f} to {rb[2]:+.2f})")
    print(f"  OLS: his old split {coef[1]:+.2f} ({lo[1]:+.2f} to {hi[1]:+.2f}), B's own {coef[2]:+.2f} ({lo[2]:+.2f} to {hi[2]:+.2f})")
p = out["primary: lead again at the new team (B's split)"]
print(f"\n== verdict (primary: his old split's slope beside B's own, interval above 0): {'held' if p[1] > 0 else 'failed'}")
