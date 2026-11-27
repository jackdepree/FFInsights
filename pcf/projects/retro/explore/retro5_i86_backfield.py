# ruff: noqa: E501
"""Retro 5, the quick group: I86, the backfield split is the coach's (retro 2, from I53 and the CEO's I20).

The split: the lead back's share of his team's running-back carries in a regular season (lead = most carries). If the
split is the coach's, it repeats from one season to the next under the same head coach even when the lead back
changes, and stops repeating when the coach changes; and it travels with a coach who moves teams.
Seasons 2006-2024 (pairs 2006-07 to 2023-24); the 2025 vault is never read. Discovery only.

Odds, written before any test: Claude, 2026-11-20: 55% that it repeats at r 0.3+ under the same coach with a new
back and under 0.15 when the coach changes; 35% that it travels with a moving coach (few moves). Retro 3, 2026-11-23:
the first moved to 35% (H78: the coach's past split lost to who is in the room). Scored: the 35% and the 35%.
Pass rules (written now, before the run): the first holds if r for same coach, new lead back is 0.3+ with its 90%
interval above 0.1, and r when the coach changed is under 0.15; the second if the moving coaches' r is above 0 with
its interval above 0.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro5_i86_backfield.py > projects/retro/explore/retro5_i86_backfield.txt
"""

import os
from pathlib import Path

import numpy as np
import polars as pl

c = pl.col
T = Path(os.environ["PCF_DATA_DIR"]) / "tables"
S = range(2006, 2025)
rng = np.random.default_rng(86)


def rd(p, cols):
    return pl.concat([pl.read_parquet(T / p / f"season={s}" / "data.parquet", columns=cols) for s in S], how="diagonal_relaxed")


sch = rd("team_game/schedule", ["game_id", "season", "team", "game_type"]).filter(c("game_type") == "REG")
ros = rd("player_game/roster", ["gsis_id", "game_id", "team", "position"]).filter(c("position").is_in(["RB", "FB"]))
st = rd("player_game/stats", ["gsis_id", "game_id", "carries"])
coach = rd("team_game/opening_coach", ["game_id", "team", "season", "opening_coach"])
g = ros.join(st, on=["gsis_id", "game_id"]).join(sch, on=["game_id", "team"])
ts = g.group_by("team", "season", "gsis_id").agg(car=c("carries").fill_null(0).sum())
lead = ts.sort("car", descending=True).group_by("team", "season").agg(lead=c("gsis_id").first(), top=c("car").first(), tot=c("car").sum())
lead = lead.with_columns(split=c("top") / c("tot"))
hc = coach.join(sch.select("game_id", "team"), on=["game_id", "team"]).group_by("team", "season").agg(coach=c("opening_coach").mode().first())
lead = lead.join(hc, on=["team", "season"], how="left")
print(f"team-seasons {lead.height}; the split: mean {lead['split'].mean():.3f}, sd {lead['split'].std():.3f}")

nxt = lead.with_columns(season=c("season") - 1).rename({"lead": "lead2", "split": "split2", "coach": "coach2", "top": "top2", "tot": "tot2"})
pr = lead.join(nxt, on=["team", "season"], how="inner").with_columns(same_coach=c("coach") == c("coach2"), same_back=c("lead") == c("lead2"))


def r_ci(x, y, n=2000):
    x, y = np.asarray(x), np.asarray(y)
    est = np.corrcoef(x, y)[0, 1]
    idx = rng.integers(0, len(x), (n, len(x)))
    v = [np.corrcoef(x[i], y[i])[0, 1] for i in idx]
    lo, hi = np.percentile(v, [5, 95])
    return est, lo, hi


print("\n== season-to-season r of the split (90% interval, pairs resampled)")
res = {}
for name, m in (
    ("all pairs", pl.lit(True)),
    ("same coach, same lead back", c("same_coach") & c("same_back")),
    ("same coach, new lead back", c("same_coach") & ~c("same_back")),
    ("new coach, same lead back", ~c("same_coach") & c("same_back")),
    ("new coach, new lead back", ~c("same_coach") & ~c("same_back")),
    ("new coach (any back)", ~c("same_coach")),
):
    sub = pr.filter(m)
    est, lo, hi = r_ci(sub["split"], sub["split2"])
    res[name] = (est, lo, hi)
    print(f"  {name:<28} pairs {sub.height:>4}: r {est:+.2f} ({lo:+.2f} to {hi:+.2f})")

# the coach-move test: a coach's last season at team A against his first at team B
cs = lead.select("team", "season", "coach", "split").drop_nulls()
moves = cs.join(cs.rename({"team": "team2", "season": "season2", "split": "split2"}), on="coach").filter(
    (c("team2") != c("team")) & (c("season2") > c("season")) & (c("season2") <= c("season") + 3)
)
moves = moves.sort("season", descending=True).group_by("coach", "team2", "season2").agg(c("split").first(), c("split2").first(), c("team").first())
first_at_new = cs.group_by("coach", "team").agg(first=c("season").min())
moves = moves.join(first_at_new.rename({"team": "team2"}), on=["coach", "team2"]).filter(c("season2") == c("first"))
est, lo, hi = r_ci(moves["split"], moves["split2"])
print(f"\n== a moving coach (his last split at the old team, his first at the new; within 3 seasons): {moves.height} moves, r {est:+.2f} ({lo:+.2f} to {hi:+.2f})")
# the comparison the coach must beat: the new team's own split the season before he arrived
prev = lead.select("team", c("season") + 1, c("split").alias("team_prev")).rename({"team": "team2", "season": "season2"})
mv = moves.join(prev, on=["team2", "season2"], how="left").drop_nulls("team_prev")
e2, l2, h2 = r_ci(mv["team_prev"], mv["split2"])
print(f"   the new team's own split the season before he came: r {e2:+.2f} ({l2:+.2f} to {h2:+.2f}) on {mv.height}")
X = np.column_stack([np.ones(mv.height), mv["split"].to_numpy(), mv["team_prev"].to_numpy()])
b = np.linalg.lstsq(X, mv["split2"].to_numpy(), rcond=None)[0]
print(f"   both together (OLS): the coach's old split {b[1]:+.2f}, the team's own {b[2]:+.2f}")

sc, nb = res["same coach, new lead back"], res["new coach (any back)"]
print(f"\n== verdicts: first bet (r 0.3+ with interval above 0.1 for same coach, new back; under 0.15 with a new coach): {'held' if sc[0] >= 0.3 and sc[1] > 0.1 and nb[0] < 0.15 else 'failed'}")
print(f"   second bet (a moving coach's r above 0 with its interval above 0): {'held' if lo > 0 else 'failed'}")
