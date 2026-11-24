"""Availability exploration: H95, roles differ in injury risk and speedsters get hurt more
(pre-registered in EXPLORATION.md).

Rows: player-seasons, WR, RB and TE, 2016-2024, 200+ offensive scrimmage snaps.
A Poisson regression of in-game injuries (on scrimmage plays) with snaps as the exposure (rate
y / snaps, weighted by snaps: the same fit as an offset), within position. Base: touches per
snap (the obvious-input check). Role measures, standardized within position:
- the SD of yards per touch (the CEO's "yardage variance per play"),
- average target depth (WR, TE),
- the share of touches that are catches (RB).
Intervals: 1,000 bootstrap draws resampling players. Coefficients are rate ratios per SD.

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import PoissonRegressor

from pcf.config import get_config

c = pl.col
CFG = get_config()
O = CFG.zone("interim") / "availability"
T = CFG.zone("tables")
RNG = np.random.default_rng(CFG.seed)
B = 1000

pp = pl.read_parquet(O / "player_plays.parquet", columns=["gsis_id", "season", "group", "side", "injured"]).filter(c("group").is_in(["WR", "RB", "TE"]) & (c("side") == "offense"))
ex = pp.group_by("gsis_id", "season").agg(group=c("group").mode().first(), snaps=pl.len(), inj=c("injured").sum())
cols = ["season", "season_type", "play_type", "rusher_player_id", "receiver_player_id", "complete_pass", "yards_gained", "air_yards", "two_point_attempt"]
p = pl.concat([pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=cols) for s in range(2016, 2025)])
p = p.filter((c("season_type") == "REG") & (c("two_point_attempt") == 0))
ru = p.filter((c("play_type") == "run") & c("rusher_player_id").is_not_null()).select("season", gsis_id=c("rusher_player_id"), y=c("yards_gained"), catch=pl.lit(0))
rc = p.filter((c("play_type") == "pass") & (c("complete_pass") == 1) & c("receiver_player_id").is_not_null()).select("season", gsis_id=c("receiver_player_id"), y=c("yards_gained"), catch=pl.lit(1))
tg = p.filter((c("play_type") == "pass") & c("receiver_player_id").is_not_null() & c("air_yards").is_not_null()).group_by("season", gsis_id=c("receiver_player_id")).agg(adot=c("air_yards").mean(), targets=pl.len())
to = pl.concat([ru, rc]).group_by("gsis_id", "season").agg(touches=pl.len(), ysd=c("y").std(), ymean=c("y").mean(), catch_share=c("catch").mean())
d = ex.join(to, on=["gsis_id", "season"], how="left").join(tg, on=["gsis_id", "season"], how="left")
d = d.filter((c("snaps") >= 200) & (c("touches") >= 10)).with_columns(tps=c("touches") / c("snaps"))
print(f"player-seasons: {d.height:,}; injuries {int(d['inj'].sum())}")

ROLES = {"WR": ["ysd", "adot"], "TE": ["ysd", "adot"], "RB": ["ysd", "catch_share"]}


def fit(df, feats):
    X = df.select(feats).to_numpy().astype(float)
    X = (X - X.mean(0)) / X.std(0)
    n = df["snaps"].to_numpy().astype(float)
    y = df["inj"].to_numpy().astype(float)
    m = PoissonRegressor(alpha=0.0, max_iter=10000, tol=1e-10).fit(X, y / n, sample_weight=n)
    return m.coef_


roles_differ = False
speed_up = []
for g, roles in ROLES.items():
    df = d.filter((c("group") == g) & pl.all_horizontal([c(r).is_not_null() for r in roles]))
    feats = ["tps", *roles]
    est = fit(df, feats)
    pids = df["gsis_id"].unique().to_list()
    pi = {p_: i for i, p_ in enumerate(pids)}
    idx = np.array([pi[p_] for p_ in df["gsis_id"].to_list()])
    bs = []
    for _ in range(B):
        w = RNG.poisson(1.0, size=len(pids))[idx]
        sel = np.repeat(np.arange(df.height), w)
        bs.append(fit(df[sel], feats))
    bs = np.array(bs)
    print(f"\n{g}: {df.height} player-seasons, {int(df['inj'].sum())} injuries, {df['inj'].sum() / df['snaps'].sum() * 1000:.2f} per 1,000 snaps")
    for j, f in enumerate(feats):
        lo, hi = np.percentile(bs[:, j], [5, 95])
        tag = "clear" if (lo > 0 or hi < 0) else "covers 0"
        print(f"  {f:12} rate ratio per SD {np.exp(est[j]):.3f} ({np.exp(lo):.3f} to {np.exp(hi):.3f})  {tag}")
        if f in roles and (lo > 0 or hi < 0):
            roles_differ = True
        if f == "ysd":
            speed_up.append(lo > 0)
    # description: injuries per 1,000 snaps by tercile of the yards-per-touch SD
    q = df.with_columns(t=c("ysd").rank("ordinal") * 3 // (df.height + 1))
    tt = q.group_by("t").agg(r=c("inj").sum() / c("snaps").sum() * 1000, sd=c("ysd").mean()).sort("t")
    print("  per 1,000 snaps by yards-per-touch SD tercile (low, mid, high): " + ", ".join(f"{r:.2f} (SD {s:.1f})" for _, r, s in tt.iter_rows()))
speed = any(speed_up)
verdict = "HELD" if (roles_differ and speed) else "HELD IN PART" if roles_differ else "FAILED"
print(f"\n-> roles differ: {roles_differ}; speedsters (yards-per-touch SD) clearly higher in any position: {speed}; H95: {verdict}")
