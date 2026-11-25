"""Availability: backlog ideas I128 and I129 (REVIEW.md section 3, written before this ran).

I128, a team's habit of listing players Questionable: each team's earlier Questionable listings
(every position on the 53, every earlier week from 2016) and how often those players were
health-absent, shrunk to the league's earlier rate with 30 listings. On Questionable QB/RB/WR/TE
rows, a walk-forward logistic (by season, 2018-2024) of active on participation's `active`
log-odds plus the habit's gap (its log-odds minus the league's), against the same without it.

I129, the healthy rate counts releases: the healthy share (games played over games not
health-absent, rest of season) fit walk-forward by season with a weighted logistic on his
record; games played = that rate x the chain's share not absent; scored like test 2 (the
receiving board's rest-of-season rows, 2019-2024) against I60 and the shipped composite.

Run from pcf/: <venv python> projects/availability/build/ideas_run.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

from pcf.baselines.crude import inputs as I
from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config
from pcf.experts.availability import checks as K
from pcf.experts.availability import experts as X
from pcf.experts.availability import games as G
from pcf.validation import backtest

c = pl.col
CFG = get_config()
OUT = Path(__file__).with_name("ideas.txt")
KEYS = K.KEYS
lines: list[str] = []


def log(*parts) -> None:
    s = " ".join(str(p) for p in parts)
    print(s, flush=True)
    lines.append(s)


def ll(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def paired(la: np.ndarray, lb: np.ndarray, steps: np.ndarray, seed: int = 0):
    """Share of b's loss that a removes, with a 90% interval from resampled weeks."""
    u, g = np.unique(steps, return_inverse=True)
    da, db = np.bincount(g, lb - la), np.bincount(g, lb)
    draws = np.random.default_rng(seed).multinomial(len(u), np.full(len(u), 1 / len(u)), size=2000)
    boot = (draws @ da) / (draws @ db)
    return da.sum() / db.sum(), *np.quantile(boot, [0.05, 0.95])


# ================================================================ I128
log("I128: a team's habit of listing players Questionable, beside participation's `active`, on Questionable QB/RB/WR/TE rows")
f, t = backtest.load_features(K.cache_dir() / "next")
q = f.filter(~c("reserve") & (c("status") == 1)).select(*KEYS, "team", "step").join(t.select(*KEYS, "y"), on=KEYS, how="inner")
per = q.group_by("team", "step").agg(n=pl.len(), a=c("y").sum()).sort("team", "step")
per = per.with_columns(n_before=(c("n").cum_sum() - c("n")).over("team"), a_before=(c("a").cum_sum() - c("a")).over("team"))
lg = q.group_by("step").agg(n=pl.len(), a=c("y").sum()).sort("step").with_columns(
    lg_rate=((c("a").cum_sum() - c("a")) / (c("n").cum_sum() - c("n")).clip(1)))
per = per.join(lg.select("step", "lg_rate"), on="step").with_columns(
    habit=((c("a_before") + 30 * c("lg_rate")) / (c("n_before") + 30)).clip(0.01, 0.99), lg=c("lg_rate").clip(0.01, 0.99))
per = per.with_columns(gap=pl.Series(X._logit(per["habit"].to_numpy()) - X._logit(per["lg"].to_numpy())))
log(f"  Questionable listings 2016-2024 (every position): {q.height:,}; health-absent {q['y'].mean():.3f}; the habit's spread across teams in 2024 week 1: {per.filter(c('step') == per['step'].max())['habit'].std():.3f}")
act = pl.read_parquet(K.cache_dir() / "hist_active_part.parquet").filter(c("y").is_not_null())
fa, _ = backtest.load_features(K.cache_dir() / "active")
act = act.drop("season", strict=False).join(fa.select(*KEYS, "team", "status", "season"), on=KEYS, how="inner").filter(c("status") == 1)
act = act.join(per.select("team", "step", "gap"), on=["team", "step"], how="left").with_columns(c("gap").fill_null(0.0))
act = act.with_columns(lp=pl.Series(X._logit(act["mean"].to_numpy())))
log(f"  Questionable QB/RB/WR/TE rows with participation's `active`: {act.height:,} (seasons {act['season'].min()}-{act['season'].max()}); active {act['y'].mean():.3f}")


def walk(df: pl.DataFrame, cols: list[str]) -> np.ndarray:
    p = np.full(df.height, np.nan)
    s, xa, ya = df["season"].to_numpy(), df.select(cols).to_numpy().astype(float), df["y"].to_numpy().astype(int)
    for season in range(2018, 2025):
        tr, te = s < season, s == season
        if tr.sum() and te.sum():
            p[te] = LogisticRegression(C=1e4, max_iter=2000).fit(xa[tr], ya[tr]).predict_proba(xa[te])[:, 1]
    return p


sc = act["season"].to_numpy() >= 2018
y = act["y"].to_numpy().astype(int)
st = act["step"].to_numpy()
raw = act["mean"].to_numpy()
base = walk(act, ["lp"])
new = walk(act, ["lp", "gap"])
for name, p in (("participation's active, raw", raw), ("recalibrated on Questionable rows", base), ("recalibrated + the team's habit", new)):
    log(f"  {name:<36} log loss {ll(p[sc], y[sc]).mean():.4f}, slope {K.calibration_slope(p[sc], y[sc]):.3f}, calibration error {K.calibration_error(p[sc], y[sc]):.2f} pts [{sc.sum():,} rows, 2018-2024]")
r, lo, hi = paired(ll(new, y)[sc], ll(base, y)[sc], st[sc])
null = [paired(ll(walk(act.with_columns(c("gap").shuffle(seed=CFG.seed + k).over("step")), ["lp", "gap"]), y)[sc], ll(base, y)[sc], st[sc])[0] for k in range(1, 20)]
log(f"  the habit beside recalibrated `active`: {100 * r:+.2f}% of the log loss ({100 * lo:+.2f} to {100 * hi:+.2f}); copies' max {100 * max(null):+.2f}%; counts: {lo > 0 and r > max(null)}")
r2, lo2, hi2 = paired(ll(new, y)[sc], ll(raw, y)[sc], st[sc])
log(f"  against raw `active`: {100 * r2:+.2f}% ({100 * lo2:+.2f} to {100 * hi2:+.2f})")
coef = LogisticRegression(C=1e4, max_iter=2000).fit(act.select("lp", "gap").to_numpy(), y).coef_[0]
log(f"  fit on every row: log-odds slope on `active` {coef[0]:.3f}, on the habit's gap {coef[1]:+.3f} (a team whose Questionable players sit more often: negative)")

# ================================================================ I129
log("\nI129: the healthy rate fit on his record (releases, benchings), games played scored like test 2 (2019-2024)")
hist = pl.read_parquet(K.cache_dir() / "hist_rest_chain.parquet")
feats = pl.read_parquet(K.cache_dir() / "features.parquet").select(
    *KEYS, "played_s", "games_s", "absent_s", "position", "last_share", "log_snaps_s", "age", "credibility", "last_played", "state")
av = G.games_played(hist.drop("season", "position", "state", strict=False).join(feats, on=KEYS, how="left")).select(
    *KEYS, "gp", "hrate", "ha_share", "position", "last_share", "log_snaps_s", "age", "games_s", "last_played", "state",
    h_as_of="as_of", ha="mean", hy="y", n="n_window")
board = Y.load_board("receiving", "rest")
rows = board.features.filter(c("step_season") >= 2017)
fc = I.availability(rows.select(*board.keys, "team", "season", "week", "as_of", "y_s"))
hs = I.availability(rows.select(*board.keys, "team", "season", "week", "as_of", "y_s"), hindsight=True)
b = rows.select(*board.keys, "as_of").join(av, on=KEYS, how="left").filter(c("h_as_of").is_null() | (c("h_as_of") <= c("as_of")))
b = b.sort("h_as_of").unique(board.keys, keep="last")
j = b.join(fc.select(*KEYS, "av_rate"), on=KEYS).join(hs.select(*KEYS, "av_true"), on=KEYS)
j = j.join(rows.select(*KEYS, "step", "season"), on=KEYS).drop_nulls(["gp", "av_rate", "av_true", "hy"])
j = j.with_columns(healthy_n=(c("n") - c("hy")).clip(0)).with_columns(
    hshare=pl.when(c("healthy_n") > 0).then((c("av_true") * c("n") / c("healthy_n")).clip(0, 1)))
POS = ["QB", "RB", "WR", "TE"]
j = j.with_columns(lh=pl.Series(X._logit(j["hrate"].clip(0.02, 0.98).to_numpy())), ls=c("last_share").fill_null(0.0), lss=c("log_snaps_s").fill_null(0.0),
                   ag=c("age").fill_null(26.0), gs=c("games_s").fill_null(0.0), lp=c("last_played").cast(pl.Float64).fill_null(0.0),
                   **{f"p_{p}": (c("position") == p).cast(pl.Float64) for p in POS[1:]})
COLS = ["lh", "ls", "lss", "ag", "gs", "lp", "p_RB", "p_WR", "p_TE"]
log(f"  rows {j.height:,} ({j['season'].min()}-{j['season'].max()}); healthy share mean {j['hshare'].mean():.3f}, the shrunk healthy rate's mean {j['hrate'].mean():.3f}")
pred = np.full(j.height, np.nan)
s_ = j["season"].to_numpy()
xa = j.select(COLS).to_numpy().astype(float)
for season in range(2019, 2025):
    tr = (s_ < season) & j["hshare"].is_not_null().to_numpy()
    te = s_ == season
    hsh, wt = j["hshare"].to_numpy()[tr], j["healthy_n"].to_numpy()[tr]
    x2 = np.vstack([xa[tr], xa[tr]])
    y2 = np.r_[np.ones(tr.sum()), np.zeros(tr.sum())]
    w2 = np.r_[hsh * wt, (1 - hsh) * wt]
    m = LogisticRegression(C=1.0, max_iter=3000).fit(x2, y2, sample_weight=w2)
    pred[te] = m.predict_proba(xa[te])[:, 1]
j = j.with_columns(hrate_fit=pl.Series(pred)).with_columns(gp_fit=c("hrate_fit") * (1 - c("ha_share")))
# the simpler rung (rule k): the shipped composite times one factor, the earlier seasons' outcome over composite
full = j.select("season", "gp", "av_true")
k_by = {s: full.filter(c("season") < s).select(c("av_true").sum() / c("gp").sum()).item() for s in range(2019, 2025)}
j = j.filter(c("season") >= 2019).with_columns(gp_scaled=(c("gp") * c("season").replace_strict(k_by, return_dtype=pl.Float64)).clip(0, 1))
log("  the simpler rung's factor by season: " + ", ".join(f"{s} {v:.3f}" for s, v in k_by.items()))
j = j.with_columns(se_i60=(c("av_rate") - c("av_true")) ** 2, se_gp=(c("gp") - c("av_true")) ** 2, se_fit=(c("gp_fit") - c("av_true")) ** 2,
                   se_scaled=(c("gp_scaled") - c("av_true")) ** 2)
stp = j["step"].to_numpy()
for name, col, m in (("shipped composite", "se_gp", "gp"), ("the composite rescaled", "se_scaled", "gp_scaled"), ("the fitted healthy rate", "se_fit", "gp_fit")):
    r, lo, hi = paired(j[col].to_numpy(), j["se_i60"].to_numpy(), stp)
    log(f"  {name:<26} mean {j[m].mean():.3f} (outcome {j['av_true'].mean():.3f}); removes {100 * r:+.2f}% of I60's squared error ({100 * lo:+.2f} to {100 * hi:+.2f})")
for a_, b_ in (("se_fit", "se_gp"), ("se_scaled", "se_gp"), ("se_fit", "se_scaled")):
    r, lo, hi = paired(j[a_].to_numpy(), j[b_].to_numpy(), stp)
    log(f"  {a_[3:]} against {b_[3:]}: {100 * r:+.2f}% of its squared error ({100 * lo:+.2f} to {100 * hi:+.2f})")
rg = G.walk_ranges(pl.concat([j.select("season", gp="gp_fit", y="av_true")]).with_columns(), list(range(2020, 2025)))
cover = rg.select(((c("y") >= c("gp10") - 1e-9) & (c("y") <= c("gp90") + 1e-9)).mean()).item()
log(f"  its range (earlier seasons' misses, 2020-2024): q10-q90 holds {100 * cover:.1f}%")
for p in POS:
    sub = j.filter(c("position") == p)
    if sub.is_empty():
        continue
    log(f"    {p}: rows {sub.height:,}, I60 {sub['se_i60'].mean():.4f}, shipped {sub['se_gp'].mean():.4f}, rescaled {sub['se_scaled'].mean():.4f}, fitted {sub['se_fit'].mean():.4f}")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
