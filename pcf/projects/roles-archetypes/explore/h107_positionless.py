"""Roles exploration, second look: the pooled positionless space and H107 (pre-registered in EXPLORATION.md).

One PCA across WR, TE and RB (M2's features, no measurables, no position label), fit 2016-2020, 6 components.
H107: next season's targets per snap and carries per snap, from the three position labels (P) against the 6
coordinates (Z); ridge, leave-one-target-season-out, 90% player bootstrap. Side bets on next season's yards
per game beyond P + last season's volume: adding Z, and Z against a 6-feature role table.
Writes <interim>/roles/pooled.parquet (every player-team-season-half's pooled coordinates) for H108.

Run from pcf/projects/roles-archetypes/explore: PYTHONIOENCODING=utf-8 <venv python> h107_positionless.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import roles_common as rc
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

c = pl.col
T = rc.CFG.zone("tables")
RNG = np.random.default_rng(rc.CFG.seed)
B = 2000
K = 6
OFF = ["WR", "TE", "RB"]
FEATS = rc.full_set("WR")  # the offensive set: snap share, adj_, oo_, offensive usage
TABLE = ["snap_share", "tgt_per_pass", "car_per_run", "adot", "adj_run", "adj_p11"]

d = rc.load(halves=True).filter(c("group").is_in(OFF))
fit = d.filter((c("half") == "all") & (c("season") <= 2020))
sc = StandardScaler().fit(fit.select(FEATS).to_numpy())
pca = PCA(K, random_state=0).fit(sc.transform(fit.select(FEATS).to_numpy()))
Z = pca.transform(sc.transform(d.select(FEATS).to_numpy()))
d = d.with_columns([pl.Series(f"pz{i}", Z[:, i]) for i in range(K)])
zc = [f"pz{i}" for i in range(K)]
d.select("gsis_id", "team", "season", "half", "group", *zc).write_parquet(rc.O / "pooled.parquet")

print("pooled positionless PCA (WR, TE, RB together; fit 2016-2020):", f"explained {np.round(pca.explained_variance_ratio_, 2).tolist()}")
for i in range(K):
    load = pca.components_[i]
    top = np.argsort(-np.abs(load))[:4]
    print(f"  pz{i}: " + ", ".join(f"{FEATS[j]}{'+' if load[j] > 0 else '-'}" for j in top))
a = d.filter(c("half") == "all")
print("  group means of each coordinate:")
print(a.group_by("group").agg([c(z).mean().round(2) for z in zc]).sort("group"))

# consistency: split-half and season r
od = d.filter(c("half") == "odd").select("gsis_id", "team", "season", *[c(z).alias(z + "_o") for z in zc])
ev = d.filter(c("half") == "even").select("gsis_id", "team", "season", *[c(z).alias(z + "_e") for z in zc])
sh = od.join(ev, on=["gsis_id", "team", "season"])
a1 = a.sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
nx = a1.select("gsis_id", season=c("season") - 1, team_next=c("team"), **{z + "_n": c(z) for z in zc})
pairs = a1.join(nx, on=["gsis_id", "season"])
print("  split-half r:", [round(float(np.corrcoef(sh[z + "_o"], sh[z + "_e"])[0, 1]), 2) for z in zc])
print("  season r:    ", [round(float(np.corrcoef(pairs[z], pairs[z + "_n"])[0, 1]), 2) for z in zc])
mv = pairs.filter(c("team") != c("team_next"))
print(f"  season r, movers ({mv.height}):", [round(float(np.corrcoef(mv[z], mv[z + "_n"])[0, 1]), 2) for z in zc])
# does it still sort the positions?
X, y = a.select(zc).to_numpy(), a["group"].to_numpy()
acc = []
for tr, te in GroupKFold(5).split(X, y, a["gsis_id"].to_numpy()):
    m = LogisticRegression(max_iter=5000).fit(X[tr], y[tr])
    acc.append((m.predict(X[te]) == y[te]).mean())
print(f"  the position recovered from the 6 coordinates alone: {np.mean(acc):.1%} (the majority share {pd_ if (pd_ := max((y == g).mean() for g in OFF)) else 0:.1%})")

# --- H107
pbp = pl.concat([pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=[
    "season", "season_type", "play_type", "receiver_player_id", "rusher_player_id", "complete_pass", "yards_gained", "two_point_attempt"])
    for s in range(2016, 2025)]).filter((c("season_type") == "REG") & c("play_type").is_in(["pass", "run"]) & (c("two_point_attempt") != 1))
yds = pl.concat([
    pbp.filter(c("complete_pass") == 1).select("season", gsis_id=c("receiver_player_id"), y=c("yards_gained")),
    pbp.filter(c("play_type") == "run").select("season", gsis_id=c("rusher_player_id"), y=c("yards_gained")),
]).drop_nulls().group_by("gsis_id", "season").agg(yards=c("y").sum())
cnt = pl.read_parquet(rc.O / "counts.parquet").filter((c("half") == "all") & c("group").is_in(OFF))
tot = cnt.group_by("gsis_id", "season").agg(c("targets").sum(), c("carries").sum(), c("snaps").sum(), c("games").sum()).join(yds, on=["gsis_id", "season"], how="left").with_columns(c("yards").fill_null(0))
tot = tot.with_columns(tps=c("targets") / c("snaps"), cps=c("carries") / c("snaps"), tpg=c("targets") / c("games"), cpg=c("carries") / c("games"), ypg=c("yards") / c("games"))
cur = a1.join(tot.select("gsis_id", "season", "tpg", "cpg", "ypg"), on=["gsis_id", "season"])
nxt = tot.select("gsis_id", season=c("season") - 1, tps_n=c("tps"), cps_n=c("cps"), ypg_n=c("ypg"))
h = cur.join(nxt, on=["gsis_id", "season"]).join(pairs.select("gsis_id", "season"), on=["gsis_id", "season"], how="semi")
print(f"\nH107: {h.height:,} consecutive-season pairs (200+ snaps both seasons)")
P = np.column_stack([(h["group"] == g).cast(pl.Float64).to_numpy() for g in OFF[1:]])
Zm = h.select(zc).to_numpy()
base = np.column_stack([P, h.select("tpg", "cpg", "ypg", "snap_share").to_numpy()])
table = h.select(TABLE).to_numpy()
seas = h["season"].to_numpy()
pid = h["gsis_id"].to_numpy()


def cv(X, y):
    p = np.zeros(len(y))
    for s in np.unique(seas):
        tr, te = seas != s, seas == s
        s_ = StandardScaler().fit(X[tr])
        p[te] = Ridge(alpha=1.0).fit(s_.transform(X[tr]), y[tr]).predict(s_.transform(X[te]))
    return p


u, inv = np.unique(pid, return_inverse=True)
W = RNG.poisson(1.0, size=(B, len(u)))[:, inv].astype(float)


def gain(y, p0, p1, name):
    g = (y - p0) ** 2 - (y - p1) ** 2
    bs = (W @ g) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    mse0 = ((y - p0) ** 2).mean()
    print(f"  {name}: error {mse0:.5g} -> {((y - p1) ** 2).mean():.5g}; gain {g.mean() / mse0:+.1%} (90% {lo / mse0:+.1%} to {hi / mse0:+.1%})")
    return lo > 0


ok = []
for tgt in ("tps_n", "cps_n"):
    y = h[tgt].to_numpy()
    ok.append(gain(y, cv(P, y), cv(Zm, y), f"{tgt}: P (position labels) against Z (6 coordinates)"))
print("  -> H107:", "HELD" if all(ok) else "HELD IN PART" if any(ok) else "FAILED")
y = h["ypg_n"].to_numpy()
pb = cv(base, y)
print("side bets, next season's yards per game:")
gain(y, pb, cv(np.column_stack([base, Zm]), y), "base (P + last season's volume, yards, snap share) against base + Z (Claude 45%)")
pt = cv(np.column_stack([base, table]), y)
gain(y, pb, pt, "base against base + the role table")
gain(y, pt, cv(np.column_stack([base, Zm]), y), "base + role table against base + Z (Claude 30%; a tie goes to the table)")
for g in OFF:
    ig = (h["group"] == g).to_numpy()
    print(f"    {g}: n {ig.sum()}")
