"""Availability exploration: H93, given an in-game injury, past injuries, recovery rate and age
forecast the time missed (pre-registered in EXPLORATION.md).

Rows: in-game injuries 2013-2024 (history from 2013), scored walk-forward 2016-2024.
Target: games missed within the season. The pre-registered score is squared error on
log(1 + games) against the position's average; also reported: Poisson deviance (a Poisson
regression against the position's mean) and log loss for missing at least one game.
Intervals resample team-weeks of the injuries (2,000 Poisson-bootstrap draws).

Claude's side bet: the same three beside the after-the-fact ceiling (next week's report status
and body part, known only after the injury).

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LinearRegression, LogisticRegression, PoissonRegressor

from pcf.config import get_config

c = pl.col
CFG = get_config()
O = CFG.zone("interim") / "availability"
RNG = np.random.default_rng(CFG.seed)
B = 2000

pg = pl.read_parquet(O / "player_games.parquet").sort("gsis_id", "season", "week")
pg = pg.with_columns(snaps=c("offense_snaps") + c("defense_snaps") + c("st_snaps"))
# career-so-far totals before each game (since 2013)
pg = pg.with_columns(
    snaps_before=(c("snaps").cum_sum() - c("snaps")).over("gsis_id"),
    n_past=(c("hurt").cum_sum() - c("hurt")).over("gsis_id"),
    miss_past=(c("missed").fill_null(0).cum_sum() - c("missed").fill_null(0)).over("gsis_id"),
)
rost = pg.select("gsis_id", "season", "team", gi=c("gi") - 1, next_rostered=pl.lit(1))
h = pg.filter(c("hurt") == 1).join(rost, on=["gsis_id", "season", "team", "gi"], how="left").with_columns(c("next_rostered").fill_null(0))
h = h.filter(c("age").is_not_null())
POS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]
h = h.with_columns(pos=pl.when(c("position").is_in(POS)).then(c("position")).otherwise(pl.lit("other")))
top = h.filter(c("nr_part").is_not_null())["nr_part"].value_counts().sort("count", descending=True).head(12)["nr_part"].to_list()
h = h.with_columns(
    y=(c("missed").cast(pl.Float64) + 1).log(),
    any_miss=(c("missed") >= 1).cast(pl.Int8),
    rate=c("n_past") / (c("snaps_before") / 1000 + 1),
    part=pl.when(c("nr_part").is_in(top)).then(c("nr_part")).when(c("nr_part").is_not_null()).then(pl.lit("other part")).otherwise(pl.lit("none")),
    stat=pl.when(c("next_rostered") == 0).then(pl.lit("not rostered")).otherwise(c("nr_status").fill_null("not listed")),
    gw=pl.concat_str([c("season").cast(pl.Utf8), c("week").cast(pl.Utf8), c("team")], separator="-"),
)
print(f"injuries with age: {h.height:,}; scored 2016-2024: {h.filter(c('season') >= 2016).height:,}; with 1+ past injury: {(h['n_past'] > 0).mean():.3f}")


def onehot(d, col, levels):
    return np.column_stack([(d[col] == v).to_numpy().astype(float) for v in levels[1:]])


def X_of(d, kind, k, pos_mean, levels):
    cols = [onehot(d, "pos", levels["pos"])]
    if kind in ("hist", "ceiling+hist"):
        rec = ((d["miss_past"].to_numpy() + k * pos_mean) / (d["n_past"].to_numpy() + k))
        a = d["age"].to_numpy()
        cols += [np.log1p(d["n_past"].to_numpy())[:, None], d["rate"].to_numpy()[:, None], np.log1p(rec)[:, None], (a - 27)[:, None], ((a - 27) ** 2)[:, None]]
    if kind in ("ceiling", "ceiling+hist"):
        d2 = d.with_columns(sp=pl.concat_str([c("stat"), c("part")], separator="|"))
        cols += [onehot(d2, "sp", levels["sp"])]
    return np.column_stack(cols)


rows = []
for s in range(2016, 2025):
    tr, te = h.filter(c("season") < s), h.filter(c("season") == s)
    levels = {"pos": sorted(h["pos"].unique().to_list()),
              "sp": sorted(tr.with_columns(sp=pl.concat_str([c("stat"), c("part")], separator="|"))["sp"].unique().to_list())}
    te = te.with_columns(sp=pl.concat_str([c("stat"), c("part")], separator="|")).with_columns(
        stat=pl.when(c("sp").is_in(levels["sp"])).then(c("stat")).otherwise(pl.lit("not listed")),
        part=pl.when(c("sp").is_in(levels["sp"])).then(c("part")).otherwise(pl.lit("none"))).drop("sp")
    # recovery-rate shrinkage k, chosen inside the training seasons (last training season held out)
    pm_tr = float(tr["missed"].mean())
    inner_tr, inner_te = tr.filter(c("season") < s - 1), tr.filter(c("season") == s - 1)
    best_k, best = 1.0, np.inf
    if inner_tr.height > 500:
        for k in (0.5, 1, 2, 4, 8):
            m = LinearRegression().fit(X_of(inner_tr, "hist", k, pm_tr, levels), inner_tr["y"].to_numpy())
            e = ((inner_te["y"].to_numpy() - m.predict(X_of(inner_te, "hist", k, pm_tr, levels))) ** 2).mean()
            if e < best:
                best, best_k = e, k
    out = {"season": s, "k": best_k}
    yte, ytr = te["y"].to_numpy(), tr["y"].to_numpy()
    for kind in ("pos", "hist", "ceiling", "ceiling+hist"):
        Xtr, Xte = X_of(tr, kind, best_k, pm_tr, levels), X_of(te, kind, best_k, pm_tr, levels)
        out[f"se_{kind}"] = (yte - LinearRegression().fit(Xtr, ytr).predict(Xte)) ** 2
        if kind in ("pos", "hist"):
            pr = PoissonRegressor(alpha=1e-4, max_iter=1000).fit(Xtr, tr["missed"].to_numpy()).predict(Xte)
            yy = te["missed"].to_numpy().astype(float)
            out[f"dev_{kind}"] = 2 * (np.where(yy > 0, yy * np.log(np.maximum(yy, 1e-9) / pr), 0) - (yy - pr))
            pa = LogisticRegression(C=1.0, max_iter=2000).fit(Xtr, tr["any_miss"].to_numpy()).predict_proba(Xte)[:, 1]
            ya = te["any_miss"].to_numpy()
            out[f"ll_{kind}"] = -(ya * np.log(pa) + (1 - ya) * np.log(1 - pa))
    out["gw"] = te["gw"].to_numpy()
    rows.append(out)
print("shrinkage k chosen per season:", [r["k"] for r in rows])

gw = np.concatenate([r["gw"] for r in rows])
u, inv = np.unique(gw, return_inverse=True)
W = RNG.poisson(1.0, size=(B, len(u))).astype(np.float32)


def gain(a, b, label):
    A = np.concatenate([r[a] for r in rows])
    Bv = np.concatenate([r[b] for r in rows])
    d, base = np.bincount(inv, weights=A - Bv), np.bincount(inv, weights=A)
    est = d.sum() / base.sum()
    bs = (W @ d) / (W @ base)
    lo, hi = np.percentile(bs, [5, 95])
    print(f"  {label:78} {100 * est:+.2f}% ({100 * lo:+.2f} to {100 * hi:+.2f})")
    return lo > 0


print("=" * 100, "\nH93, walk-forward 2016-2024: share of the error removed")
held = gain("se_pos", "se_hist", "pre-registered: past injuries, recovery rate, age vs position average (log(1+games))")
gain("dev_pos", "dev_hist", "the same, Poisson regression, Poisson deviance")
gain("ll_pos", "ll_hist", "the same, chance of missing 1+ game, log loss")
print("  -> H93 as worded:", "HELD" if held else "not held")
print("Claude's side bet: beside the after-the-fact ceiling (next week's status x body part)")
gain("se_pos", "se_ceiling", "the ceiling alone vs position average (log(1+games))")
gain("se_ceiling", "se_ceiling+hist", "the three, added beside the ceiling")

# what the history says, fitted on all seasons (a description, not a test)
X = X_of(h, "hist", 2.0, float(h["missed"].mean()), {"pos": sorted(h["pos"].unique().to_list()), "sp": []})
m = LinearRegression().fit(X, h["y"].to_numpy())
names = [f"pos={p}" for p in sorted(h["pos"].unique().to_list())[1:]] + ["log(1+past injuries)", "past injuries per 1,000 snaps", "log(1+shrunk recovery, games)", "age-27", "(age-27)^2"]
print("\nDescription, all seasons (log(1+games) per unit):")
for n_, b_ in zip(names, m.coef_):
    if not n_.startswith("pos="):
        print(f"  {n_:34} {b_:+.4f}")
for lo_, hi_ in ((20, 24), (25, 27), (28, 30), (31, 40)):
    d = h.filter(c("age").is_between(lo_, hi_ + 0.999))
    print(f"  age {lo_}-{hi_}: {d.height:5d} injuries, mean games missed {d['missed'].mean():.2f}, share missing 1+ {d['any_miss'].mean():.3f}")
for lo_, hi_, lab in ((0, 0, "0"), (1, 1, "1"), (2, 3, "2-3"), (4, 99, "4+")):
    d = h.filter(c("n_past").is_between(lo_, hi_))
    print(f"  past in-game injuries {lab:4}: {d.height:5d} injuries, mean games missed {d['missed'].mean():.2f}, share missing 1+ {d['any_miss'].mean():.3f}")
