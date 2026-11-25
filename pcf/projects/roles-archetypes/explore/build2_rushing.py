"""Round 2, the CEO's spot-check: why do the coordinates add noise on the yardstick's rushing board
(-0.90%) where the role table counts (+0.74%)? I133 and spot-check bets S1-S5 (BUILD.md, round 2,
odds written before this ran).

Reads the build's saved history (run 696a3f0b) as the prior, exactly as test 4 did (each
player-season's main-team row, as a prior for the next season; missing: the column's median), and
the crude forecaster's saved rushing rest-of-season board, beside participation.

Run from pcf/: .venv/Scripts/python.exe projects/roles-archetypes/explore/build2_rushing.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import build2_common as bc  # noqa: E402

from pcf.baselines.crude import yardstick as Y  # noqa: E402

c = pl.col
say = bc.Say(Path(__file__).with_suffix(".txt"))
prior = bc.offense_prior()
Z, T = bc.Z, bc.T_OFF
board = Y.load_board("rushing", "rest")
keys = board.keys
rows = board.features.select(*keys, "season")
crude = board.forecast(("participation",))


def forecast(cols, pr=prior):
    frame = rows.join(pr.select("gsis_id", "season", *cols), on=["gsis_id", "season"], how="left").drop("season")
    feats = board.features.join(frame, on=keys, how="left").with_columns(c(x).fill_null(c(x).median()) for x in cols)
    return board.forecast(("participation",), extra=list(cols), feats=feats)


def line(name, new, sub=None):
    g = Y.gain(new, crude, keys, sub)
    say(f"  {name:52}: {100 * g.share:+.2f}% (90% {100 * g.lo:+.2f} to {100 * g.hi:+.2f}) [{g.rows} rows]")
    return g


say("Round 2 spot-check: the coordinates on the rushing rest-of-season board (beside participation)")
say(f"board: {board.features.height:,} rows, positions {board.features['position'].unique().to_list()}; scored steps 2019-2024")
pz = forecast(Z)
pt = forecast(T)
say("\n1. Reproduced from the saved history (test 4 said -0.90% and +0.74%):")
line("coordinates, all 6", pz)
line("role table, 6", pt)

# per-row view: each scored row's squared error with and without the coordinates
d = (crude.select(*keys, "season", "y", m0=c("mean")).join(pz.select(*keys, m1=c("mean")), on=keys)
     .join(pt.select(*keys, m2=c("mean")), on=keys)
     .join(board.features.select(*keys, "week", "team"), on=keys)
     .join(prior.select("gsis_id", "season", "role", "coarse", "snaps", *Z, *T), on=["gsis_id", "season"], how="left")
     .with_columns(dz=(c("y") - c("m1")) ** 2 - (c("y") - c("m0")) ** 2,
                   dt=(c("y") - c("m2")) ** 2 - (c("y") - c("m0")) ** 2,
                   base=(c("y") - c("m0")) ** 2,
                   kind=pl.when(c("role").is_null()).then(pl.lit("no prior (rookie or new)"))
                   .otherwise(c("role"))))
d = d.filter(c("season").is_between(2019, 2024))
tot_base = d["base"].sum()
loss = d["dz"].sum()
say(f"\n2. Where the loss sits: the coordinates' extra squared error is {100 * loss / tot_base:+.2f}% of the crude error (positive = worse)")
say("  by target season (share of the total extra error; the coordinates' and the table's change as % of that season's crude error):")
for r in d.group_by("season").agg(dz=c("dz").sum(), dt=c("dt").sum(), b=c("base").sum(), n=pl.len()).sort("season").iter_rows(named=True):
    say(f"    {r['season']}: {r['dz'] / loss:6.0%} of the loss; coordinates {100 * r['dz'] / r['b']:+.2f}%, table {100 * r['dt'] / r['b']:+.2f}% ({r['n']} rows)")
say("  by the back's prior role (last season's named role):")
for r in d.group_by("kind").agg(dz=c("dz").sum(), dt=c("dt").sum(), b=c("base").sum(), n=pl.len()).sort("n", descending=True).iter_rows(named=True):
    say(f"    {r['kind']:26}: {r['dz'] / loss:6.0%} of the loss; coordinates {100 * r['dz'] / r['b']:+.2f}%, table {100 * r['dt'] / r['b']:+.2f}% ({r['n']} rows)")
say("  by the prior season's snaps:")
d = d.with_columns(snapband=pl.when(c("snaps").is_null()).then(pl.lit("none")).when(c("snaps") < 200).then(pl.lit("under 200")).when(c("snaps") < 500).then(pl.lit("200-499")).otherwise(pl.lit("500+")))
for r in d.group_by("snapband").agg(dz=c("dz").sum(), dt=c("dt").sum(), b=c("base").sum(), n=pl.len()).sort("n", descending=True).iter_rows(named=True):
    say(f"    {r['snapband']:10}: {r['dz'] / loss:6.0%} of the loss; coordinates {100 * r['dz'] / r['b']:+.2f}%, table {100 * r['dt'] / r['b']:+.2f}% ({r['n']} rows)")
pp = d.group_by("gsis_id", "season").agg(dz=c("dz").sum(), n=pl.len()).sort("dz", descending=True)
top = pp.head(10)["dz"].sum()
say(f"  by player-season: {pp.height} player-seasons; the 10 worst carry {top / loss:.0%} of the net loss, the 50 worst {pp.head(50)['dz'].sum() / loss:.0%}; "
    f"{(pp['dz'] > 0).mean():.0%} of player-seasons are hurt")
names = bc.names()
w10 = pp.head(10).join(names, on="gsis_id", how="left").join(prior.select("gsis_id", "season", "role", "snaps", *Z), on=["gsis_id", "season"], how="left")
for r in w10.iter_rows(named=True):
    zs = " ".join(f"{r[z]:+.1f}" if r[z] is not None else "  na" for z in Z)
    say(f"    {r['name']} {r['season']} ({r['role']}, {r['snaps']} prior snaps): {100 * r['dz'] / tot_base:+.3f}% ; prior z {zs}")

# the error of the forecast's level: does the coordinates' forecast run too high or too low?
say("\n3. Bias: the average forecast minus the outcome (rest-of-season yards), crude and with the coordinates, by prior role:")
for r in d.group_by("kind").agg(b0=(c("m0") - c("y")).mean(), b1=(c("m1") - c("y")).mean(), b2=(c("m2") - c("y")).mean(), n=pl.len()).sort("n", descending=True).iter_rows(named=True):
    say(f"    {r['kind']:26}: crude {r['b0']:+6.1f}, coordinates {r['b1']:+6.1f}, table {r['b2']:+6.1f} ({r['n']} rows)")

say("\n4. Single axes and subsets (oz1 alone +0.03%, z4-z5 +0.06% and z0-z3 -0.81% from the build's follow-up):")
for i in (0, 2, 3):
    line(f"z{i} alone", forecast([f"z{i}"]))
line("z0 + z1", forecast(["z0", "z1"]))

say("\n5. I133: the fullbacks (non-carriers by last season's named role) taken out")
nfb = prior.with_columns([pl.when(c("coarse") != "back").then(None).otherwise(c(z)).alias(z) for z in Z])
say(f"  prior rows on the board's players that aren't backs: {d.filter(c('coarse').is_not_null() & (c('coarse') != 'back')).select('gsis_id', 'season').unique().height} player-seasons, "
    f"{d.filter(c('coarse').is_not_null() & (c('coarse') != 'back')).height} rows")
line("(a) coordinates, non-backs' prior set missing", forecast(Z, nfb))
backs = d.filter(c("coarse") == "back").select(keys)
line("(b) coordinates, scored on last season's backs only", pz, backs)
line("    the table, on the same rows", pt, backs)
line("(c) coordinates + carries per run snap", forecast([*Z, "t2_car_per_run"]))
line("    carries per run snap alone", forecast(["t2_car_per_run"]))

say("\n6. S5: the coarse and fine roles as dummies (the step, not a line)")
dm = prior.with_columns(
    is_back=(c("coarse") == "back").cast(pl.Float64), is_early=(c("role") == "early-down back").cast(pl.Float64),
    is_pdown=(c("role") == "passing-down back").cast(pl.Float64))
line("is a back (coarse)", forecast(["is_back"], dm))
line("early-down back, passing-down back (fine)", forecast(["is_early", "is_pdown"], dm))

say("\n7. Overfitting check: the coordinates' fit on the training seasons vs held out")
say("  (a lasso on player-constant columns can fit a player's own residual when one back appears in many training weeks)")
# the copies: 5 copies shuffled within season and group, as test 4's (its 19 copies' best was -0.09%)
cps = []
for k in range(5):
    sh = bc.shuffled(prior, Z, 7000 + k)
    cps.append(Y.gain(forecast(Z, sh), crude, keys).share)
say(f"  5 shuffled copies of the coordinates: mean {100 * np.mean(cps):+.2f}%, worst {100 * min(cps):+.2f}%, best {100 * max(cps):+.2f}%")
# within-back coordinates: centred by group (removes the RB/TE/WR level, keeps who is what among backs)
say.save()
