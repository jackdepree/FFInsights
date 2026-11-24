"""Availability exploration: H96 (risk-weighted snaps beat snap counts) and H98 (fatigue as a
recency-weighted sum of risky plays), pre-registered in EXPLORATION.md.

Rows: player-games where he played, 2017-2024 scored walk-forward (history from 2016).
Target: an in-game injury that game. Each past play's risk is H97's logistic play model, fitted
only on earlier seasons (`player_play_risk.parquet`). Logistic models; intervals resample
team-weeks (2,000 Poisson-bootstrap draws).

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from pcf.config import get_config

c = pl.col
CFG = get_config()
O = CFG.zone("interim") / "availability"
RNG = np.random.default_rng(CFG.seed)
B = 2000
GROUPS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]

risk = pl.read_parquet(O / "player_play_risk.parquet").group_by("gsis_id", "game_id").agg(plays=pl.len(), wsum=c("risk").sum())
pg = pl.read_parquet(O / "player_games.parquet").filter((c("season") >= 2016) & c("position").is_in(GROUPS))
pg = pg.join(risk, on=["gsis_id", "game_id"], how="left").with_columns(c("plays").fill_null(0), c("wsum").fill_null(0.0)).sort("gsis_id", "season", "week")
HL = (1, 2, 4, 8)
pg = pg.with_columns(
    last_plays=c("plays").shift(1).over("gsis_id", "season").fill_null(0),
    cnt4=c("plays").shift(1).rolling_sum(4, min_samples=1).over("gsis_id", "season").fill_null(0),
    cntS=(c("plays").cum_sum() - c("plays")).over("gsis_id", "season"),
    w4=c("wsum").shift(1).rolling_sum(4, min_samples=1).over("gsis_id", "season").fill_null(0),
    wS=(c("wsum").cum_sum() - c("wsum")).over("gsis_id", "season"),
    **{f"ew{h}": c("wsum").shift(1).ewm_mean(half_life=h, adjust=True).over("gsis_id").fill_null(0) for h in HL},
    # the trait check: his career-long average risk per game and his past injuries, with no recency
    wcar=((c("wsum").cum_sum() - c("wsum")) / (c("wsum").cum_count() - 1).clip(1)).over("gsis_id").fill_null(0),
    inj_car=(c("hurt").cum_sum() - c("hurt")).over("gsis_id"),
)
d = pg.filter((c("played") == 1) & (c("season") >= 2017)).with_columns(
    gw=pl.concat_str([c("season").cast(pl.Utf8), c("week").cast(pl.Utf8), c("team")], separator="-"))
print(f"rows (played, 2017-2024): {d.height:,}; injuries {int(d['hurt'].sum()):,}")
G = np.column_stack([(d["position"] == g).to_numpy() for g in GROUPS[1:]]).astype(float)


def X(cols):
    return np.column_stack([G] + [d[k].to_numpy().astype(float)[:, None] for k in cols])


SETS = {
    "base": ["last_plays"],
    "counts": ["last_plays", "cnt4", "cntS"],
    "weighted": ["last_plays", "w4", "wS"],
    "h98 base": ["last_plays", "cnt4", "cntS", "wS"],
    # the exposure check (after the fact, not a forecast): this game's own snaps in the base
    "x base": ["plays", "last_plays", "cnt4", "cntS", "wS"],
}
y = d["hurt"].to_numpy().astype(float)
season = d["season"].to_numpy()
L = {k: np.zeros(len(y)) for k in [*SETS, "h98"]}
chosen = []
for s in range(2017, 2025):
    tr, te = season < s, season == s
    if tr.sum() == 0:
        tr = season == 2017  # 2017 has no earlier season of rows: fit on itself (reported)
    for k, cols in SETS.items():
        Xa = X(cols)
        sc = StandardScaler().fit(Xa[tr])
        m = LogisticRegression(C=1.0, max_iter=3000).fit(sc.transform(Xa[tr]), y[tr])
        p = np.clip(m.predict_proba(sc.transform(Xa[te]))[:, 1], 1e-7, 1 - 1e-7)
        L[k][te] = -(y[te] * np.log(p) + (1 - y[te]) * np.log(1 - p))
    # H98: the half-life chosen inside the training seasons (the last training season held out)
    inner_tr, inner_te = (season < s - 1), (season == s - 1)
    best_h, best = HL[0], np.inf
    if inner_tr.sum() > 0:
        for h in HL:
            Xa = X(SETS["h98 base"] + [f"ew{h}"])
            sc = StandardScaler().fit(Xa[inner_tr])
            m = LogisticRegression(C=1.0, max_iter=3000).fit(sc.transform(Xa[inner_tr]), y[inner_tr])
            p = np.clip(m.predict_proba(sc.transform(Xa[inner_te]))[:, 1], 1e-7, 1 - 1e-7)
            e = -(y[inner_te] * np.log(p) + (1 - y[inner_te]) * np.log(1 - p)).mean()
            if e < best:
                best, best_h = e, h
    chosen.append(best_h)
    Xa = X(SETS["h98 base"] + [f"ew{best_h}"])
    sc = StandardScaler().fit(Xa[tr])
    m = LogisticRegression(C=1.0, max_iter=3000).fit(sc.transform(Xa[tr]), y[tr])
    p = np.clip(m.predict_proba(sc.transform(Xa[te]))[:, 1], 1e-7, 1 - 1e-7)
    L["h98"][te] = -(y[te] * np.log(p) + (1 - y[te]) * np.log(1 - p))
# the exposure check for H98: this game's snaps in, at each season's chosen half-life
L["x h98"] = np.zeros(len(y))
for s, h_ in zip(range(2017, 2025), chosen):
    tr, te = season < s, season == s
    if tr.sum() == 0:
        tr = season == 2017
    Xa = X(SETS["x base"] + [f"ew{h_}"])
    sc = StandardScaler().fit(Xa[tr])
    m = LogisticRegression(C=1.0, max_iter=3000).fit(sc.transform(Xa[tr]), y[tr])
    p = np.clip(m.predict_proba(sc.transform(Xa[te]))[:, 1], 1e-7, 1 - 1e-7)
    L["x h98"][te] = -(y[te] * np.log(p) + (1 - y[te]) * np.log(1 - p))
print("H98 half-life (games) chosen per season 2017-2024:", chosen, "(2017 and 2018 fall back to the first, with no inner season)")

u, inv = np.unique(d["gw"].to_numpy(), return_inverse=True)
W = RNG.poisson(1.0, size=(B, len(u))).astype(np.float32)


def gain(a, b, label, ref="base"):
    dd, base = np.bincount(inv, weights=L[a] - L[b]), np.bincount(inv, weights=L[ref])
    est = dd.sum() / base.sum()
    bs = (W @ dd) / (W @ base)
    lo, hi = np.percentile(bs, [5, 95])
    print(f"  {label:70} {100 * est:+.3f}% ({100 * lo:+.3f} to {100 * hi:+.3f}) of the base's log loss")
    return est, lo, hi


print("=" * 100)
print(f"base log loss per player-game {L['base'].mean():.5f}")
gain("base", "counts", "counts (last 4, season to date) beside the base")
gain("base", "weighted", "weighted (the same windows, risk-weighted) beside the base")
est, lo, hi = gain("counts", "weighted", "H96: weighted against counts (positive = weighted better)")
print("  -> H96:", "HELD" if lo > 0 else "FAILED" if (hi < 0 or est < 0.001) else "UNCLEAR")
est, lo, hi = gain("h98 base", "h98", "H98: the recency-weighted sum beside counts and the season's weighted sum")
print("  -> H98:", "HELD" if lo > 0 else "FAILED" if (lo < 0 and est < 0.001) else "UNCLEAR")
print("Exposure check (after the fact; this game's own snaps in both models, so the gain is per snap, not more snaps):")
gain("x base", "x h98", "  H98's sum beside this game's snaps, counts and the season's weighted sum")
L["x counts"] = np.zeros(len(y))
L["x weighted"] = np.zeros(len(y))
for s in range(2017, 2025):
    tr, te = season < s, season == s
    if tr.sum() == 0:
        tr = season == 2017
    for k, cols in (("x counts", ["plays", "last_plays", "cnt4", "cntS"]), ("x weighted", ["plays", "last_plays", "w4", "wS"])):
        Xa = X(cols)
        sc = StandardScaler().fit(Xa[tr])
        m = LogisticRegression(C=1.0, max_iter=3000).fit(sc.transform(Xa[tr]), y[tr])
        p = np.clip(m.predict_proba(sc.transform(Xa[te]))[:, 1], 1e-7, 1 - 1e-7)
        L[k][te] = -(y[te] * np.log(p) + (1 - y[te]) * np.log(1 - p))
gain("x counts", "x weighted", "  H96 with this game's snaps in: weighted against counts", ref="x base")
print("Trait check (is H98's gain recency, or who he is?): the career-long average risk per game and past injuries in the base")
L["t base"] = np.zeros(len(y))
L["t h98"] = np.zeros(len(y))
for s, h_ in zip(range(2017, 2025), chosen):
    tr, te = season < s, season == s
    if tr.sum() == 0:
        tr = season == 2017
    for k, cols in (("t base", SETS["h98 base"] + ["wcar", "inj_car"]), ("t h98", SETS["h98 base"] + ["wcar", "inj_car", f"ew{h_}"])):
        Xa = X(cols)
        sc = StandardScaler().fit(Xa[tr])
        m = LogisticRegression(C=1.0, max_iter=3000).fit(sc.transform(Xa[tr]), y[tr])
        p = np.clip(m.predict_proba(sc.transform(Xa[te]))[:, 1], 1e-7, 1 - 1e-7)
        L[k][te] = -(y[te] * np.log(p) + (1 - y[te]) * np.log(1 - p))
gain("h98 base", "t base", "  the trait terms alone beside H98's base")
gain("t base", "t h98", "  H98's recency-weighted sum beside the trait terms")

# description: injury rate per 1,000 games by this game's... last-4 workload quintile, within group
print("\nDescription: injuries per 100 games played, by quintile of the last 4 games' risk-weighted snaps (within position group)")
dq = d.with_columns(q=c("w4").rank("ordinal").over("position") * 5 // (pl.len().over("position") + 1))
t = dq.group_by("q").agg(n=pl.len(), r=c("hurt").mean() * 100, plays=c("plays").mean()).sort("q")
for q, n, r, p in t.iter_rows():
    print(f"  quintile {q + 1}: {n:6d} games, {r:.2f} injuries per 100 games, {p:.0f} snaps that game on average")
dq = dq.with_columns(rate=c("hurt") / pl.max_horizontal(c("plays"), 1) * 1000)
t = dq.filter(c("plays") >= 20).group_by("q").agg(r=c("hurt").sum() / c("plays").sum() * 1000).sort("q")
print("  per 1,000 snaps that game (games with 20+ snaps):", ", ".join(f"{r:.2f}" for r in t["r"].to_list()))
