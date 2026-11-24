"""Roles exploration, third look: I124, a pooled defensive space (pre-registered in EXPLORATION.md).

One PCA across DL, OLB, ILB, CB and S (snap share, adj_, oo_, defensive usage; no measurables, no position
label), fit 2016-2020, 6 components. Counted: components with split-half r 0.5+ (pooled, and centred within
position); how well the coordinates recover the position; season r and movers' season r. Forecasting stress
test: next season's tackles per snap and rushes per pass snap from the coordinates against the position labels.

Run from pcf/projects/roles-archetypes/explore: PYTHONIOENCODING=utf-8 <venv python> i124_defense_pooled.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import roles_common as rc
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

c = pl.col
RNG = np.random.default_rng(rc.CFG.seed)
B = 2000
K = 6
DEF = ["DL", "OLB", "ILB", "CB", "S"]
FEATS = rc.full_set("DL")

d = rc.load(halves=True).filter(c("group").is_in(DEF))
fit = d.filter((c("half") == "all") & (c("season") <= 2020))
sc = StandardScaler().fit(fit.select(FEATS).to_numpy())
pca = PCA(K, random_state=0).fit(sc.transform(fit.select(FEATS).to_numpy()))
Z = pca.transform(sc.transform(d.select(FEATS).to_numpy()))
zc = [f"dz{i}" for i in range(K)]
d = d.with_columns([pl.Series(z, Z[:, i]) for i, z in enumerate(zc)])

print(f"pooled defensive PCA (DL, OLB, ILB, CB, S together; fit 2016-2020): explained {np.round(pca.explained_variance_ratio_, 2).tolist()}")
for i in range(K):
    ld = pca.components_[i]
    top = np.argsort(-np.abs(ld))[:4]
    print(f"  dz{i}: " + ", ".join(f"{FEATS[j]}{'+' if ld[j] > 0 else '-'}" for j in top))
a = d.filter(c("half") == "all")
print("  position means of each coordinate:")
print(a.group_by("group").agg([c(z).mean().round(2) for z in zc]).sort("group"))

# split-half, pooled and centred within position
od = d.filter(c("half") == "odd").select("gsis_id", "team", "season", "group", *[c(z).alias(z + "_o") for z in zc])
ev = d.filter(c("half") == "even").select("gsis_id", "team", "season", *[c(z).alias(z + "_e") for z in zc])
sh = od.join(ev, on=["gsis_id", "team", "season"])
pooled_r = [float(np.corrcoef(sh[z + "_o"], sh[z + "_e"])[0, 1]) for z in zc]
shc = sh.with_columns([(c(z + h) - c(z + h).mean().over("group")) for z in zc for h in ("_o", "_e")])
within_r = [float(np.corrcoef(shc[z + "_o"], shc[z + "_e"])[0, 1]) for z in zc]
print(f"\nsplit-half r, pooled:               {np.round(pooled_r, 2).tolist()}  (0.5+: {sum(r >= 0.5 for r in pooled_r)} of 6)")
print(f"split-half r, centred in position:  {np.round(within_r, 2).tolist()}  (0.5+: {sum(r >= 0.5 for r in within_r)} of 6)")
print("  (per-position M2, the first look: DL 1, OLB 2, ILB 2, CB 1, S 2 of 6)")
for g in DEF:
    s_ = sh.filter(c("group") == g)
    print(f"    within {g:3} (n {s_.height}): " + str([round(float(np.corrcoef(s_[z + "_o"], s_[z + "_e"])[0, 1]), 2) for z in zc]))

a1 = a.sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
nx = a1.select("gsis_id", season=c("season") - 1, team_next=c("team"), group_next=c("group"), **{z + "_n": c(z) for z in zc})
pairs = a1.join(nx, on=["gsis_id", "season"])
mv = pairs.filter(c("team") != c("team_next"))
print(f"\nseason r ({pairs.height} pairs): {[round(float(np.corrcoef(pairs[z], pairs[z + '_n'])[0, 1]), 2) for z in zc]}")
print(f"season r, movers ({mv.height}):  {[round(float(np.corrcoef(mv[z], mv[z + '_n'])[0, 1]), 2) for z in zc]}")
chg = pairs.filter(c("group") != c("group_next"))
print(f"players whose listed position changed between seasons: {chg.height} ({chg.height / pairs.height:.1%}); their season r: "
      f"{[round(float(np.corrcoef(chg[z], chg[z + '_n'])[0, 1]), 2) for z in zc] if chg.height > 20 else 'too few'}")

# do the positions blur?
X, y = a.select(zc).to_numpy(), a["group"].to_numpy()
pred = np.empty(len(y), dtype=object)
for tr, te in GroupKFold(5).split(X, y, a["gsis_id"].to_numpy()):
    pred[te] = LogisticRegression(max_iter=5000).fit(X[tr], y[tr]).predict(X[te])
acc = (pred == y).mean()
print(f"\nthe position recovered from the 6 coordinates alone: {acc:.1%} (the majority share {max((y == g).mean() for g in DEF):.1%}; offense 98.2%)")
cm = confusion_matrix(y, pred, labels=DEF)
print("  confusion (rows: listed position; columns: the coordinates' guess), share of each row:")
print("        " + "  ".join(f"{g:>5}" for g in DEF))
for g, row in zip(DEF, cm, strict=True):
    print(f"  {g:5} " + "  ".join(f"{v / row.sum():5.0%}" for v in row))
print("  -> I124:", "HELD" if sum(r >= 0.5 for r in pooled_r) >= 3 else "FAILED", "| within position:", "3+" if sum(r >= 0.5 for r in within_r) >= 3 else "under 3",
      "| positions blur (<85%):", acc < 0.85)

# forecasting stress test
cnt = pl.read_parquet(rc.O / "counts.parquet").filter((c("half") == "all") & c("group").is_in(DEF))
tot = cnt.group_by("gsis_id", "season").agg(c("tackles").sum(), c("rush").sum(), c("snaps").sum(), c("pass_snaps").sum()).with_columns(
    tps=c("tackles") / c("snaps"), rps=c("rush") / c("pass_snaps").clip(1))
h = pairs.join(tot.select("gsis_id", season=c("season") - 1, tps_n=c("tps"), rps_n=c("rps")), on=["gsis_id", "season"])
P = np.column_stack([(h["group"] == g).cast(pl.Float64).to_numpy() for g in DEF[1:]])
Zm = h.select(zc).to_numpy()
seas, pid = h["season"].to_numpy(), h["gsis_id"].to_numpy()
u, inv = np.unique(pid, return_inverse=True)
W = RNG.poisson(1.0, size=(B, len(u)))[:, inv].astype(float)


def cv(X, y):
    p = np.zeros(len(y))
    for s in np.unique(seas):
        tr, te = seas != s, seas == s
        s_ = StandardScaler().fit(X[tr])
        p[te] = Ridge(alpha=1.0).fit(s_.transform(X[tr]), y[tr]).predict(s_.transform(X[te]))
    return p


print(f"\nforecasting stress test: {h.height:,} pairs; next season's rate from the coordinates (Z) against the position labels (P)")
ok = []
for tgt, nm in (("tps_n", "tackles per snap"), ("rps_n", "rushes per pass snap")):
    yv = h[tgt].to_numpy()
    p0, p1 = cv(P, yv), cv(Zm, yv)
    g = (yv - p0) ** 2 - (yv - p1) ** 2
    bs = (W @ g) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    m0 = ((yv - p0) ** 2).mean()
    print(f"  {nm}: gain {g.mean() / m0:+.1%} of the labels' error (90% {lo / m0:+.1%} to {hi / m0:+.1%})")
    ok.append(lo > 0)
    p2 = cv(np.column_stack([P, Zm]), yv)
    g2 = (yv - p0) ** 2 - (yv - p2) ** 2
    bs2 = (W @ g2) / W.sum(1)
    lo2, hi2 = np.percentile(bs2, [5, 95])
    print(f"    labels + coordinates against labels: {g2.mean() / m0:+.1%} (90% {lo2 / m0:+.1%} to {hi2 / m0:+.1%})")
print("  -> side bet (coordinates beat labels on both, Claude 60%):", all(ok))

# the obvious-input check (the charter; added after the pre-registration, reported, not a verdict):
# beyond the labels, his own last-season rate and snap share
print("\nthe obvious-input check (added after the pre-registration; not a verdict): base = labels + his last-season rate + snap share")
cur = tot.select("gsis_id", "season", tps_now=c("tps"), rps_now=c("rps"))
h2 = h.join(cur, on=["gsis_id", "season"])
assert h2.height == h.height
for tgt, own, nm in (("tps_n", "tps_now", "tackles per snap"), ("rps_n", "rps_now", "rushes per pass snap")):
    yv = h2[tgt].to_numpy()
    base = np.column_stack([P, h2[own].to_numpy(), h2["snap_share"].to_numpy()])
    p0, p1 = cv(base, yv), cv(np.column_stack([base, Zm]), yv)
    g = (yv - p0) ** 2 - (yv - p1) ** 2
    bs = (W @ g) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    m0 = ((yv - p0) ** 2).mean()
    print(f"  {nm}: base + coordinates against base {g.mean() / m0:+.1%} (90% {lo / m0:+.1%} to {hi / m0:+.1%})")
