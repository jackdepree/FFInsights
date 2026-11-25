"""Vacated opportunity exploration: H111, roles' coordinates against position labels for who receives vacated
targets and carries (pre-registered in EXPLORATION.md). Ridge, leave-one-season-out, 90% team bootstrap.

Technical call: the role distance is Euclidean over roles' 6 pooled coordinates, scaled by its median before the
exp(-d), so "close" means closer than a typical pair.

Run from pcf/projects/vacated-opportunity/explore: PYTHONIOENCODING=utf-8 <venv python> h111_role_distance.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import vo_common as vc
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

c = pl.col
RNG = np.random.default_rng(vc.CFG.seed)
B = 2000
zc = [f"pz{i}" for i in range(6)]

pg, tg, ps = vc.load()
teams = sorted(tg["team"].unique().to_list())
TIX = {t: i for i, t in enumerate(teams)}
WB = RNG.poisson(1.0, size=(B, len(teams))).astype(float)
pooled = pl.read_parquet(vc.CFG.zone("interim") / "roles" / "pooled.parquet").filter(c("half") == "all").unique(["gsis_id", "team", "season"], keep="first").select("gsis_id", "team", "season", *zc)
pooled = pooled.with_columns(c("season").cast(ps["season"].dtype))

dep = vc.departures(ps).filter(c("group").is_in(vc.SKILL)).select("team", "season", j="gsis_id", group_j="group", vt="tgt_share", vc_="car_share")
dep = dep.join(pooled.rename({"gsis_id": "j", **{z: z + "_j" for z in zc}}), on=["j", "team", "season"], how="left")
bad = dep.filter(c("pz0_j").is_null()).select("team", "season").unique()
print(f"skill departures 2016-2023: {dep.height}; without roles' coordinates {dep['pz0_j'].null_count()} (their team-seasons dropped: {bad.height})")
dep = dep.join(bad, on=["team", "season"], how="anti")
sk = ps.filter(c("group").is_in(vc.SKILL))
nxt = sk.select("gsis_id", "team", season=c("season") - 1, tgt_n="tgt_share", car_n="car_share")
st = sk.filter(c("season") <= 2023).join(nxt, on=["gsis_id", "team", "season"]).join(dep.select("team", "season").unique(), on=["team", "season"], how="semi")
st = st.join(pooled, on=["gsis_id", "team", "season"], how="inner")
x = st.select("gsis_id", "team", "season", "group", *zc).join(dep, on=["team", "season"])
x = x.with_columns(d=np.sqrt(sum((c(z) - c(z + "_j")) ** 2 for z in zc)))
med = float(x["d"].median())
x = x.with_columns(k=(-c("d") / med).exp(), same=(c("group") == c("group_j")).cast(pl.Float64))
agg = x.group_by("gsis_id", "team", "season").agg(
    Vt=c("vt").sum(), Vc=c("vc_").sum(), Vt_same=(c("vt") * c("same")).sum(), Vc_same=(c("vc_") * c("same")).sum(),
    Vt_k=(c("vt") * c("k")).sum(), Vc_k=(c("vc_") * c("k")).sum(), dmin=c("d").min())
h = st.join(agg, on=["gsis_id", "team", "season"]).with_columns(dt=c("tgt_n") - c("tgt_share"), dc=c("car_n") - c("car_share"))
print(f"stayers with coordinates (WR, TE, RB) on teams with a skill departure: {h.height}; median role distance {med:.2f}")
print("  the departed's group by the stayer's group, mean exp(-d):", x.group_by("group", "group_j").agg(k=c("k").mean().round(2), n=pl.len()).sort("group", "group_j").to_dicts())
gd = np.column_stack([(h["group"] == g).cast(pl.Float64).to_numpy() for g in ["TE", "RB"]])
seas = h["season"].to_numpy()
ti = np.array([TIX[t] for t in h["team"].to_list()])


def cv(X, y):
    p = np.zeros(len(y))
    for s in np.unique(seas):
        tr, te = seas != s, seas == s
        sc = StandardScaler().fit(X[tr])
        p[te] = Ridge(alpha=1.0).fit(sc.transform(X[tr]), y[tr]).predict(sc.transform(X[te]))
    return p


def gain(y, p0, p1, label):
    g = (y - p0) ** 2 - (y - p1) ** 2
    W = WB[:, ti]
    bs = (W @ g) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    m0 = ((y - p0) ** 2).mean()
    print(f"  {label}: gain {g.mean() / m0:+.1%} of the first's error (90% {lo / m0:+.1%} to {hi / m0:+.1%})")
    return lo > 0


ok = []
for tgt, V, Vs, Vk, own, nm in (("dt", "Vt", "Vt_same", "Vt_k", "tgt_share", "target share change"), ("dc", "Vc", "Vc_same", "Vc_k", "car_share", "carry share change")):
    y = h[tgt].to_numpy()
    P = np.column_stack([h[V].to_numpy(), h[Vs].to_numpy(), gd])
    Z = np.column_stack([h[V].to_numpy(), h[Vk].to_numpy(), h["dmin"].to_numpy(), gd])
    print(f"{nm}: SD {y.std():.3f}; the vacated share's mean {h[V].mean():.3f}")
    ok.append(gain(y, cv(P, y), cv(Z, y), "P (position labels) against Z (roles' coordinates)"))
    gain(y, cv(P, y), cv(np.column_stack([P, h[Vk].to_numpy(), h["dmin"].to_numpy()]), y), "P against P + Z's terms (reported)")
    gain(y, np.full(len(y), y.mean()), cv(P, y), "the mean against P (reported: does the vacated share help at all?)")
print("  -> H111:", "HELD" if all(ok) else "HELD IN PART" if any(ok) else "FAILED")
y = h["dt"].to_numpy()
base = np.column_stack([h["Vt"].to_numpy(), h["Vt_same"].to_numpy(), gd, h["tgt_share"].to_numpy(), (h["Vt"] * h["tgt_share"]).to_numpy()])
sb = gain(y, cv(base, y), cv(np.column_stack([base, h["Vt_k"].to_numpy(), h["dmin"].to_numpy()]), y), "side bet (35%): P + his share + V x his share, against that + Z's terms, on target share")
print("  -> side bet:", sb)
