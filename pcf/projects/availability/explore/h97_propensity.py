"""Availability exploration: H97, the per-play injury propensity (pre-registered in EXPLORATION.md).

1. Rate ratios at the play level (any injury on the play), within play type, for (a) more than
   one tackler, (b) a tackle behind the line, (c) a long play (game clock over 5 s on incomplete
   passes; time to throw over 3.5 s). Intervals resample games (Poisson bootstrap).
2. The same by position group, at the player-play level.
3. A per-play model: logistic on cells of the play features x position group, then gradient-
   boosted trees (3 seeds), walk-forward 2017-2024, against position group x play type alone.
   Claude's side check (I29): the player's snaps so far in the game and the defense's play
   number in the drive.
4. Writes each player-play's risk (from a model fitted on earlier seasons only) for H96 and H98.

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
import time

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from pcf.config import get_config

c = pl.col
CFG = get_config()
O = CFG.zone("interim") / "availability"
T = CFG.zone("tables")
RNG = np.random.default_rng(CFG.seed)
B = 2000
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, file=sys.stderr, flush=True)


pp = pl.read_parquet(O / "player_plays.parquet").filter(c("group").is_not_null() & c("play_type").is_in(["run", "pass"]))
# time to throw (participation, 2016 on) and drive numbers
ttt = pl.concat([pl.read_parquet(T / "play" / "participation" / f"season={s}" / "data.parquet", columns=["game_id", "play_id", "time_to_throw"]) for s in range(2016, 2025)])
ttt = ttt.with_columns(c("play_id").cast(pl.Int64), c("time_to_throw").cast(pl.Float64, strict=False))
drv = pl.concat([pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=["game_id", "play_id", "fixed_drive", "season_type"]) for s in range(2016, 2025)])
drv = drv.filter(c("season_type") == "REG").select("game_id", c("play_id").cast(pl.Int64), "fixed_drive")
pp = pp.join(ttt, on=["game_id", "play_id"], how="left").join(drv, on=["game_id", "play_id"], how="left")
pp = pp.sort("game_id", "play_id").with_columns(
    game_snap=c("play_id").rank("ordinal").over("game_id", "gsis_id"),
    drive_play=c("play_id").rank("dense").over("game_id", "fixed_drive"),
)
log("player-plays", pp.height)

plays = pp.group_by("game_id", "play_id").agg(
    c("season").first(), c("play_type").first(), c("n_tacklers").first(), c("tfl").first(), c("sack").first(),
    c("incomplete_pass").first(), c("clock_len").first(), c("time_to_throw").first(), inj=c("injured").sum(),
)
plays = plays.with_columns(any_inj=(c("inj") > 0).cast(pl.Int32))
log("plays", plays.height, "with an injury", int(plays["any_inj"].sum()))
games = plays["game_id"].unique().sort()
gidx = {g: i for i, g in enumerate(games.to_list())}
W = RNG.poisson(1.0, size=(B, len(gidx))).astype(np.float32)  # Poisson bootstrap weights per game


def rr_within_type(d: pl.DataFrame, flag: str, y: str = "any_inj", strata=("play_type",)):
    """Standardized rate ratio: injuries with the flag over what plays with the flag would show at the
    rate of plays without it, within strata. Returns the estimate and the bootstrap interval."""
    d = d.with_columns(gi=c("game_id").replace_strict(gidx, return_dtype=pl.Int64))
    cells = d.group_by("gi", *strata, flag).agg(n=pl.len(), x=c(y).sum())
    st = cells.with_columns(s=pl.concat_str([c(s).cast(pl.Utf8) for s in strata], separator="|"))
    keys = st["s"].unique().sort().to_list()
    out = []
    for w in [np.ones(len(gidx), np.float32), *W]:
        ww = w[st["gi"].to_numpy()]
        n, x = st["n"].to_numpy() * ww, st["x"].to_numpy() * ww
        f, s = st[flag].to_numpy().astype(bool), st["s"].to_numpy()
        obs = exp = 0.0
        for k in keys:
            m = s == k
            n1, x1, n0, x0 = n[m & f].sum(), x[m & f].sum(), n[m & ~f].sum(), x[m & ~f].sum()
            if n0 > 0 and n1 > 0:
                obs += x1
                exp += n1 * x0 / n0
        out.append(obs / exp if exp > 0 else np.nan)
    est, bs = out[0], np.array(out[1:])
    lo, hi = np.nanpercentile(bs, [5, 95])
    return est, lo, hi


def line(name, d, flag, **kw):
    est, lo, hi = rr_within_type(d, flag, **kw)
    n1 = int(d[flag].sum())
    verdict = "above 1" if lo > 1 else "below 1" if hi < 1 else "covers 1"
    print(f"  {name:62} rate ratio {est:5.2f} ({lo:4.2f} to {hi:4.2f})  {verdict:8}  plays with it: {n1:,}")
    return lo > 1


print("=" * 90, "\n1. Play level, any injury on the play, within play type (the pre-registered test)")
plays = plays.with_columns(
    multi=(c("n_tacklers") > 1).cast(pl.Int8),
    behind=(c("tfl") == 1).cast(pl.Int8),
    long_clock=(c("clock_len") > 5).cast(pl.Int8),
    long_ttt=(c("time_to_throw") > 3.5).cast(pl.Int8),
)
held = {}
held["a"] = line("(a) more than one tackler", plays, "multi")
held["b"] = line("(b) a tackle behind the line (tackle for loss or sack)", plays, "behind")
inc = plays.filter((c("incomplete_pass") == 1) & c("clock_len").is_not_null() & (c("clock_len") >= 0) & (c("clock_len") <= 20))
held["c_clock"] = line("(c) over 5 s of game clock, incomplete passes", inc, "long_clock")
tt = plays.filter(c("time_to_throw").is_not_null() & (c("play_type") == "pass"))
held["c_ttt"] = line("(c') time to throw over 3.5 s, passes", tt, "long_ttt")
n_held = int(held["a"]) + int(held["b"]) + int(held["c_clock"] or held["c_ttt"])
print(f"  -> features above 1: {n_held} of 3 ((c) counts if either stand-in is above 1)")
print(f"  incomplete passes with a clock length: {inc.height:,}; median {inc['clock_len'].median()} s; share over 5 s {inc['long_clock'].mean():.3f}")

print("\n  Checks beside the test (not the pass rule):")
tk = plays.filter(c("n_tacklers") >= 1)
line("(a) among tackled plays only: 2+ tacklers against 1", tk, "multi")
for k in (2, 3):
    plays = plays.with_columns(**{f"t{k}": (c("n_tacklers") >= k).cast(pl.Int8)})
line("    3+ tacklers against fewer", plays, "t3")

print("=" * 90, "\n2. Player level, by position group (rate ratio within play type, the player injured)")
pp = pp.with_columns(
    multi=(c("n_tacklers") > 1).cast(pl.Int8), behind=(c("tfl") == 1).cast(pl.Int8),
    long_clock=(c("clock_len") > 5).cast(pl.Int8), long_ttt=(c("time_to_throw") > 3.5).cast(pl.Int8),
)
for g in ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]:
    d = pp.filter(c("group") == g)
    print(f" {g}: {d.height:,} player-plays, {int(d['injured'].sum())} injured")
    line("   (a) more than one tackler", d, "multi", y="injured")
    line("   (b) a tackle behind the line", d, "behind", y="injured")
    di = d.filter((c("incomplete_pass") == 1) & c("clock_len").is_between(0, 20))
    line("   (c) over 5 s, incomplete passes", di, "long_clock", y="injured")
    dt = d.filter(c("time_to_throw").is_not_null() & (c("play_type") == "pass"))
    line("   (c') time to throw over 3.5 s", dt, "long_ttt", y="injured")

print("=" * 90, "\n3. Per-play models, walk-forward 2017-2024 (held-out log loss per player-play)")
pp = pp.with_columns(
    tk=pl.when(c("n_tacklers") >= 3).then(3).otherwise(c("n_tacklers")).cast(pl.Int8),
    yb=pl.when(c("yards_gained") < 0).then(-1).when(c("yards_gained") < 5).then(0).when(c("yards_gained") < 10).then(1).when(c("yards_gained") < 20).then(2).otherwise(3).cast(pl.Int8),
    lc=pl.when(c("clock_len").is_null() | (c("incomplete_pass") != 1)).then(0).when(c("clock_len") > 5).then(2).otherwise(1).cast(pl.Int8),
    tb=pl.when(c("time_to_throw").is_null()).then(0).when(c("time_to_throw") > 3.5).then(2).otherwise(1).cast(pl.Int8),
    gs=pl.when(c("game_snap") <= 15).then(0).when(c("game_snap") <= 35).then(1).when(c("game_snap") <= 55).then(2).otherwise(3).cast(pl.Int8),
    dp=pl.when(c("drive_play") <= 3).then(0).when(c("drive_play") <= 6).then(1).when(c("drive_play") <= 9).then(2).otherwise(3).cast(pl.Int8),
    defense=(c("side") == "defense").cast(pl.Int8),
    pas=(c("play_type") == "pass").cast(pl.Int8),
    fum=c("fumble").fill_null(0).cast(pl.Int8), qbh=c("qb_hit").fill_null(0).cast(pl.Int8),
)
GROUPS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]
pp = pp.with_columns(gid=c("group").replace_strict({g: i for i, g in enumerate(GROUPS)}, return_dtype=pl.Int8))
FEATS = {
    "base": ["gid", "pas"],
    "play": ["gid", "pas", "tk", "behind", "yb", "lc", "tb", "fum", "qbh"],
    "play+fatigue": ["gid", "pas", "tk", "behind", "yb", "lc", "tb", "fum", "qbh", "gs", "dp"],
}


def cells(d, feats):
    return d.group_by(feats).agg(n=pl.len(), x=c("injured").sum())


def design(cl, feats, kind):
    X = cl.select(feats).to_numpy().astype(np.float32)
    if kind == "logit":
        # one-hot of each feature, plus each play feature x group
        cols = []
        for j, f in enumerate(feats):
            for v in np.unique(X[:, j]):
                cols.append((X[:, j] == v).astype(np.float32))
        g = X[:, 0]
        for j, f in enumerate(feats[1:], start=1):
            for gv in np.unique(g):
                for v in np.unique(X[:, j])[1:]:
                    cols.append(((g == gv) & (X[:, j] == v)).astype(np.float32))
        return np.column_stack(cols)
    return X


def fit_predict(tr, te, feats, kind, seed=0):
    ct = cells(tr, feats)
    allc = pl.concat([ct.select(feats), te.select(feats).unique()]).unique()
    Xa = design(allc, feats, kind)
    key = {tuple(r): i for i, r in enumerate(allc.iter_rows())}
    it = np.array([key[tuple(r)] for r in ct.select(feats).iter_rows()])
    Xtr = np.vstack([Xa[it], Xa[it]])
    ytr = np.r_[np.ones(len(it)), np.zeros(len(it))]
    wtr = np.r_[ct["x"].to_numpy(), (ct["n"] - ct["x"]).to_numpy()].astype(float)
    if kind == "logit":
        m = LogisticRegression(C=1.0, max_iter=2000)
    else:
        m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200, l2_regularization=1.0, random_state=seed)
    m.fit(Xtr, ytr, sample_weight=wtr)
    pa = m.predict_proba(Xa)[:, 1]
    ie = np.array([key[tuple(r)] for r in te.select(feats).iter_rows()])
    return pa[ie]


def ll(y, p):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


res = {k: [] for k in ["base", "play", "play+fatigue", "trees play+fatigue s0", "trees play+fatigue s1", "trees play+fatigue s2"]}
ys, gws = [], []
risk_out = []
for s in range(2016, 2025):
    tr = pp.filter(c("season") < s) if s > 2016 else pp.filter(c("season") == 2016)
    te = pp.filter(c("season") == s)
    # the risk written for H96/H98: the logistic 'play' model fitted on earlier seasons only (2016: itself)
    pr = fit_predict(tr, te, FEATS["play"], "logit")
    risk_out.append(te.select("gsis_id", "game_id", "play_id", "season", "week", "injured").with_columns(risk=pl.Series(pr)))
    if s == 2016:
        continue
    y = te["injured"].to_numpy().astype(float)
    ys.append(y)
    gws.append(te.select(gw=pl.concat_str([c("season").cast(pl.Utf8), c("week").cast(pl.Utf8), c("team")], separator="-"))["gw"].to_numpy())
    res["play"].append(ll(y, pr))
    res["base"].append(ll(y, fit_predict(tr, te, FEATS["base"], "logit")))
    res["play+fatigue"].append(ll(y, fit_predict(tr, te, FEATS["play+fatigue"], "logit")))
    for sd in range(3):
        res[f"trees play+fatigue s{sd}"].append(ll(y, fit_predict(tr, te, FEATS["play+fatigue"], "trees", seed=sd)))
    log("season", s)
pl.concat(risk_out).write_parquet(O / "player_play_risk.parquet")

y = np.concatenate(ys)
gw = np.concatenate(gws)
u, inv = np.unique(gw, return_inverse=True)
Wg = RNG.poisson(1.0, size=(B, len(u))).astype(np.float32)
L = {k: np.concatenate(v) for k, v in res.items()}
base_sum = np.bincount(inv, weights=L["base"])
cnt = np.bincount(inv)
print(f"  scored player-plays {len(y):,}; injuries {int(y.sum()):,}; base log loss per play {L['base'].mean():.6f}")
for k in [k for k in res if k != "base"]:
    d = np.bincount(inv, weights=L["base"] - L[k])
    est = d.sum() / base_sum.sum()
    bs = (Wg @ d) / (Wg @ base_sum)
    lo, hi = np.percentile(bs, [5, 95])
    print(f"  {k:26} log loss removed against position x play type: {100 * est:+.2f}% ({100 * lo:+.2f} to {100 * hi:+.2f})")
d = np.bincount(inv, weights=L["play"] - L["play+fatigue"])
bs = (Wg @ d) / (Wg @ base_sum)
print(f"  I29 side check: the fatigue bins (game snap, drive play) beside the play features: {100 * d.sum() / base_sum.sum():+.2f}% ({100 * np.percentile(bs, 5):+.2f} to {100 * np.percentile(bs, 95):+.2f})")
sp = [100 * (L["base"] - L[f"trees play+fatigue s{i}"]).sum() / L["base"].sum() for i in range(3)]
print(f"  trees' seed spread: {min(sp):+.3f}% to {max(sp):+.3f}%")

print("\n  The logistic 'play' model's injury rate by fatigue bin (per 1,000 player-plays, all seasons):")
for f, lab in (("gs", "his snaps so far in the game (<=15, 16-35, 36-55, 56+)"), ("dp", "play number in the drive (1-3, 4-6, 7-9, 10+)")):
    t = pp.group_by("defense", f).agg(n=pl.len(), r=c("injured").mean() * 1000).sort("defense", f)
    print(f"   {lab}:")
    for side in (0, 1):
        tt_ = t.filter(c("defense") == side)
        print(f"     {'defense' if side else 'offense'}: " + ", ".join(f"{r:.2f}" for r in tt_["r"].to_list()))
