"""Roles exploration: H101, like-for-like substitutes (pre-registered in EXPLORATION.md).

A regular (50%+ snap share in his group over his earlier games that season, 2+ games) misses a team
game. The replacement is the teammate in his group whose snap share rose most above his own earlier
average. The pool: teammates in the group who played that game, weren't regulars, and have a prior-season
role. Statistic: the replacement's distance rank to the absent player within the pool (0 closest, 1
farthest), on M2's prior-season components (known before the season); chance 0.5.

Run from pcf/projects/roles-archetypes/explore: PYTHONIOENCODING=utf-8 <venv python> h101_substitutes.py
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

g = pl.read_parquet(rc.O / "games.parquet").with_columns(share=c("snaps") / c("team_plays"))
team_games = g.select("team", "side", "season", "game_id", "week").unique()
lat = pl.read_parquet(rc.O / "latent.parquet").filter(c("half") == "all")
cnt = pl.read_parquet(rc.O / "counts.parquet").filter(c("half") == "all").select("gsis_id", "team", "season", "snaps")
lat = lat.join(cnt, on=["gsis_id", "team", "season"]).sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
prior = {}
for pre in ("m2", "m2ns"):
    cols = [f"{pre}_z{i}" for i in range(K)]
    prior[pre] = lat.select("gsis_id", "group", season=c("season") + 1, **{f"p{i}": c(col) for i, col in enumerate(cols)})

# each player's season-to-date average share before each team game
g = g.sort("gsis_id", "team", "season", "week")
g = g.with_columns(n_before=c("week").cum_count().over("gsis_id", "team", "season") - 1,
                   avg_before=((c("share").cum_sum() - c("share")) / (c("week").cum_count() - 1).clip(1)).over("gsis_id", "team", "season"))
# a regular's absences: team games after his 2nd game played with no snap from him
reg = g.filter(c("n_before") >= 2).select("gsis_id", "team", "side", "season", "group", "week", "avg_before")
# his status going into each later team game: his last average before it
pl_games = g.select("gsis_id", "team", "side", "season", "group").unique()
cand = pl_games.join(team_games, on=["team", "side", "season"])
played = g.select("gsis_id", "team", "season", "game_id", pl.lit(1).alias("p"))
cand = cand.join(played, on=["gsis_id", "team", "season", "game_id"], how="left").filter(c("p").is_null())
last = g.select("gsis_id", "team", "season", "week", "n_before", "share", "avg_before").with_columns(
    avg_incl=((c("avg_before") * c("n_before") + c("share")) / (c("n_before") + 1)), n_incl=c("n_before") + 1)
cand = cand.sort("week").join_asof(last.sort("week").rename({"week": "wk_last"}), left_on="week", right_on="wk_last", by=["gsis_id", "team", "season"], strategy="backward")
absent = cand.filter((c("n_incl") >= 2) & (c("avg_incl") >= 0.5)).select("gsis_id", "team", "side", "season", "group", "game_id", "week")
print(f"regulars' absences: {absent.height:,}")

# who played that game: rise over own earlier average; regular status going in
mates = g.select("gsis_id", "team", "season", "group", "game_id", "share", "avg_before", "n_before").with_columns(
    rise=c("share") - pl.when(c("n_before") > 0).then(c("avg_before")).otherwise(0.0), was_regular=(c("n_before") >= 2) & (c("avg_before") >= 0.5))
ev = absent.join(mates.rename({"gsis_id": "mate"}), on=["team", "season", "group", "game_id"])


def run(pre, label):
    pr = prior[pre]
    e = ev.join(pr.rename({f"p{i}": f"a{i}" for i in range(K)}).drop("group"), on=["gsis_id", "season"], how="inner")
    e = e.join(pr.rename({"gsis_id": "mate"}).drop("group"), on=["mate", "season"], how="left")
    rep = e.sort("rise", descending=True).unique(["gsis_id", "game_id"], keep="first").select("gsis_id", "game_id", rep=c("mate"), rep_reg=c("was_regular"))
    e = e.join(rep, on=["gsis_id", "game_id"]).filter(~c("rep_reg") & ~c("was_regular") & c("p0").is_not_null())
    e = e.with_columns(dist=pl.sum_horizontal([(c(f"a{i}") - c(f"p{i}")) ** 2 for i in range(K)]).sqrt())
    grp = e.group_by("gsis_id", "game_id", "team", "season", "group")
    stats = grp.agg(n=pl.len(), has_rep=(c("mate") == c("rep")).any(),
                    d_rep=c("dist").filter(c("mate") == c("rep")).first(), dists=c("dist"))
    stats = stats.filter(c("has_rep") & (c("n") >= 2))
    ranks = []
    for d_rep, ds in zip(stats["d_rep"].to_list(), stats["dists"].to_list(), strict=True):
        ds = np.array(ds)
        less, ties = (ds < d_rep).sum(), (ds == d_rep).sum() - 1
        ranks.append((less + 0.5 * ties) / (len(ds) - 1))
    stats = stats.with_columns(rank=pl.Series(ranks), ts=pl.concat_str([c("team"), c("season").cast(pl.Utf8)]))
    u, inv = np.unique(stats["ts"].to_numpy(), return_inverse=True)
    W = RNG.poisson(1.0, size=(B, len(u)))[:, inv].astype(float)
    rk = stats["rank"].to_numpy()
    est, bs = rk.mean(), (W @ rk) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    print(f"\n{label}: events {stats.height:,} (pool of 2+ non-regular teammates with a prior-season role); mean rank {est:.3f} (90% {lo:.3f} to {hi:.3f}); chance 0.5")
    print("  closest in the pool: " + f"{(rk == 0).mean():.0%}" + f" (chance about {np.mean(1 / stats['n'].to_numpy()):.0%})")
    for gg in rc.GROUPS:
        s_ = stats.filter(c("group") == gg)
        if s_.height >= 20:
            print(f"  {gg:4} events {s_.height:5d}  mean rank {s_['rank'].mean():.3f}")
    return est, lo, hi


est, lo, hi = run("m2", "H101 (M2's prior-season components, the pre-registered test)")
print("  -> H101 (like-for-like):", "HELD" if hi < 0.5 else "FAILED")
run("m2ns", "Sensitivity: components refitted without snap share (playing time)")
