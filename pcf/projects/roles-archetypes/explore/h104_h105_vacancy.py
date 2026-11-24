"""Roles exploration: H104 (vacancies are filled in kind) and H105 (teams target the departed player's role),
pre-registered in EXPLORATION.md.

Departures: his team's top 2 WRs, top TE or top RB by snaps in season s, with no snaps for that team in s+1.
Newcomers: players in that group on the team in s+1 with 200+ snaps who weren't on it in s.
H104: forecast the newcomer's M2 coordinates with the team in s+1 from (a) the group's average that season,
(b) the departed player's coordinates (the mean when two left), (c) the team's average coordinates in that
group in s. Squared distance; 90% team bootstrap of (a) minus (b) and (a) minus (c). Side bet: newcomers
sit closer to their own team's departed player than to other teams' (rank among the group's departures).
H105: veteran movers only (200+ snaps elsewhere in s): his season-s coordinates against the departed player's,
ranked among every veteran mover in his group that offseason.

Run from pcf/projects/roles-archetypes/explore: PYTHONIOENCODING=utf-8 <venv python> h104_h105_vacancy.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import roles_common as rc

c = pl.col
RNG = np.random.default_rng(rc.CFG.seed)
B = 2000
K = 6
TOP = {"WR": 2, "TE": 1, "RB": 1}

cnt = pl.read_parquet(rc.O / "counts.parquet").filter((c("half") == "all") & c("group").is_in(list(TOP))).select("gsis_id", "team", "season", "group", "snaps")
lat_all = pl.read_parquet(rc.O / "latent.parquet").filter((c("half") == "all") & c("group").is_in(list(TOP)))


def run(pre: str, label: str):
    zc = [f"{pre}_z{i}" for i in range(K)]
    lat = lat_all.select("gsis_id", "team", "season", "group", *zc)
    # departures
    top = cnt.with_columns(rk=c("snaps").rank("ordinal", descending=True).over("team", "season", "group")).join(
        pl.DataFrame({"group": list(TOP), "top": list(TOP.values())}), on="group").filter(c("rk") <= c("top"))
    nxt = cnt.select("gsis_id", "team", season=c("season") - 1).with_columns(stays=pl.lit(True))
    dep = top.join(nxt, on=["gsis_id", "team", "season"], how="left").filter(c("stays").is_null() & (c("season") < 2024))
    dep = dep.join(lat, on=["gsis_id", "team", "season", "group"], how="inner")  # 200+ snaps rows carry coordinates
    dep_xy = dep.group_by("team", "season", "group").agg([c(z).mean().alias(f"d{i}") for i, z in enumerate(zc)], n_dep=pl.len())
    # newcomers with the team in s+1
    was = cnt.select("gsis_id", "team", season=c("season") + 1).with_columns(was=pl.lit(True))
    new = lat.join(was, on=["gsis_id", "team", "season"], how="left").filter(c("was").is_null()).with_columns(season_dep=c("season") - 1)
    ev = new.join(dep_xy.rename({"season": "season_dep"}), on=["team", "season_dep", "group"], how="inner")
    # (a) the group's average in s+1 (every team), (c) the team's average in s
    gavg = lat.group_by("season", "group").agg([c(z).mean().alias(f"g{i}") for i, z in enumerate(zc)])
    tavg = lat.group_by("team", "season", "group").agg([c(z).mean().alias(f"t{i}") for i, z in enumerate(zc)]).rename({"season": "season_dep"})
    ev = ev.join(gavg, on=["season", "group"]).join(tavg, on=["team", "season_dep", "group"])
    Z = ev.select(zc).to_numpy()
    err = {k: ((Z - ev.select([f"{k}{i}" for i in range(K)]).to_numpy()) ** 2).sum(1) for k in ("g", "d", "t")}
    u, inv = np.unique(ev["team"].to_numpy(), return_inverse=True)
    W = RNG.poisson(1.0, size=(B, len(u)))[:, inv].astype(float)
    print(f"\n{label}: newcomers {ev.height} (filling {ev.select('team', 'season_dep', 'group').unique().height} vacancies)")
    print(f"  mean squared distance: (a) group average {err['g'].mean():.3f}; (b) the departed player {err['d'].mean():.3f}; (c) the team's usual role {err['t'].mean():.3f}")
    out = {}
    for k, nm in (("d", "(b) departed"), ("t", "(c) team's usual")):
        gain = err["g"] - err[k]
        bs = (W @ gain) / W.sum(1)
        lo, hi = np.percentile(bs, [5, 95])
        out[k] = lo
        print(f"  {nm} beats the group average by {gain.mean():+.3f} (90% {lo:+.3f} to {hi:+.3f})")
    for gg in TOP:
        ig = (ev["group"] == gg).to_numpy()
        print(f"    {gg}: n {ig.sum():3d}  (a) {err['g'][ig].mean():.3f}  (b) {err['d'][ig].mean():.3f}  (c) {err['t'][ig].mean():.3f}")
    held = out["d"] > 0 or out["t"] > 0
    # side bet: closer to his own team's departed player than to other teams' departed players (same group, same offseason)
    D = dep_xy.select("team", "season", "group", *[f"d{i}" for i in range(K)])
    ranks = []
    for row in ev.select("team", "season_dep", "group", *zc).iter_rows(named=True):
        pool = D.filter((c("season") == row["season_dep"]) & (c("group") == row["group"]))
        P = pool.select([f"d{i}" for i in range(K)]).to_numpy()
        z = np.array([row[x] for x in zc])
        ds = ((P - z) ** 2).sum(1)
        own = ds[(pool["team"] == row["team"]).to_numpy()][0]
        others = ds[(pool["team"] != row["team"]).to_numpy()]
        ranks.append(((others < own).sum() + 0.5 * (others == own).sum()) / max(len(others), 1))
    ranks = np.array(ranks)
    bs = (W @ ranks) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    print(f"  side bet: his own team's departed player ranks {ranks.mean():.3f} among all departures in his group (90% {lo:.3f} to {hi:.3f}; chance 0.5)")

    # H105: veteran movers, their season-s coordinates (old team)
    old = lat.rename({"team": "old_team", "season": "season_dep"}).rename({z: f"o{i}" for i, z in enumerate(zc)})
    mv = ev.join(old, on=["gsis_id", "season_dep", "group"], how="inner").filter(c("old_team") != c("team"))
    mv = mv.sort("o0").unique(["gsis_id", "season"], keep="first")
    ranks5 = []
    for (s, gg), grp in mv.group_by(["season_dep", "group"]):
        O = grp.select([f"o{i}" for i in range(K)]).to_numpy()
        Dd = grp.select([f"d{i}" for i in range(K)]).to_numpy()
        for j in range(grp.height):
            if grp.height < 3:
                continue
            ds = ((O - Dd[j]) ** 2).sum(1)
            others = np.delete(ds, j)
            ranks5.append((grp["team"][j], ((others < ds[j]).sum() + 0.5 * (others == ds[j]).sum()) / len(others)))
    tm = np.array([t for t, _ in ranks5])
    r5 = np.array([r for _, r in ranks5])
    u5, inv5 = np.unique(tm, return_inverse=True)
    W5 = RNG.poisson(1.0, size=(B, len(u5)))[:, inv5].astype(float)
    bs5 = (W5 @ r5) / W5.sum(1)
    lo5, hi5 = np.percentile(bs5, [5, 95])
    print(f"  H105: veteran movers {len(r5)}; his pre-arrival role's rank against the departed player, among that offseason's movers in his group: {r5.mean():.3f} (90% {lo5:.3f} to {hi5:.3f}; chance 0.5)")
    return held, hi5 < 0.5


h104, h105 = run("m2", "H104/H105 on M2's components (pre-registered)")
print("\n  -> H104:", "HELD" if h104 else "FAILED", "| H105:", "HELD" if h105 else "FAILED")
run("m2ns", "Sensitivity: components refitted without snap share")
