"""Spot-check of player-pace#R1: proe_shrunk against proe_group for backs, receivers and tight
ends, 2018-2024. Where the 15% comes from, whether it's just role (playing time), and named rows."""

import numpy as np
import polars as pl

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.data.gateway import Gateway, TableSource
from pcf.experts.player_pace_retro.model import VARIANTS
from pcf.validation import backtest, scores
from pcf.validation.compare import compare

c = pl.col
K = ["gsis_id", "season"]
SKILL = ["RB", "WR", "TE"]
g = Gateway()
shr, grp = (backtest.run(VARIANTS[v](), g, None) for v in ("proe_shrunk", "proe_group"))
ps = TableSource().part("player_season", "on_field_pace")
prev = ps.select(
    "gsis_id", season=c("season") + 1, prev_team="onf_team",
    ppg=c("onf_plays") / c("onf_games"),
)  # fmt: skip
now = ps.select(*K, team="onf_team", w_out="onf_w_proe", plays_out="onf_plays")
feat = shr.features.select(*K, "group", "seasons_seen", "proe_w", "proe_last", "proe_last_w")
A = (
    shr.scored.join(feat, on=K)
    .join(prev, on=K, how="left")
    .join(now, on=K, how="left")
    .filter(c("group").is_in(SKILL))
)
B = grp.scored.select(*K, "mean", "loss").rename({"mean": "g_mean", "loss": "g_loss"})
A = A.join(B, on=K)
print(f"rows {A.height}; shrunk {A['loss'].mean():.5f}, group {A['g_loss'].mean():.5f}, "
      f"{A['loss'].mean() / A['g_loss'].mean() - 1:+.1%}")


def cmp_line(name, rows):
    if rows.height < 30:
        print(f"  {name:28s} n={rows.height} (too few)")
        return
    a = rows.select(*K, "step", "loss")
    b = rows.select(*K, loss=c("g_loss"))
    r = compare(a, b, K, "step", ("shrunk", "group"))
    print(f"  {name:28s} n={r.rows:5d} {r.diff / rows['g_loss'].mean():+6.1%}  "
          f"[{r.lo:+.5f}, {r.hi:+.5f}]")


print("\nBy group"); [cmp_line(x, A.filter(c("group") == x)) for x in SKILL]
print("\nBy season"); [cmp_line(str(s), A.filter(c("season") == s)) for s in sorted(A["season"].unique())]
A = A.with_columns(
    wb=pl.when(c("w_out") < 50).then(pl.lit("a 20-50")).when(c("w_out") < 150).then(pl.lit("b 50-150"))
    .otherwise(pl.lit("c 150+")),
    hb=pl.when(c("proe_w") < 50).then(pl.lit("a <50")).when(c("proe_w") < 200).then(pl.lit("b 50-200"))
    .otherwise(pl.lit("c 200+")),
    mover=(c("team") != c("prev_team")).fill_null(False),
)  # fmt: skip
print("\nBy how much the outcome season measures him (weight)")
[cmp_line(x, A.filter(c("wb") == x)) for x in sorted(A["wb"].unique())]
print("\nBy how much history he brings (decayed weight)")
[cmp_line(x, A.filter(c("hb") == x)) for x in sorted(A["hb"].unique())]
print("\nMovers (new main team) and stayers")
cmp_line("stayed", A.filter(~c("mover"))); cmp_line("moved", A.filter(c("mover")))

# Does the forecast's lean come true? Bins of (shrunk - group): average actual - group
A = A.with_columns(lean=c("mean") - c("g_mean"), got=c("y") - c("g_mean"))
A = A.with_columns(bin=c("lean").qcut(5, labels=[f"q{i}" for i in range(1, 6)]))
print("\nLean (shrunk - group) in fifths: average lean, average actual gap from group")
print(A.group_by("bin").agg(n=pl.len(), lean=c("lean").mean(), actual=c("got").mean()).sort("bin"))

# The alternative: role (last season's plays per game) instead of plus-minus history.
# Walk forward: each test season's yardstick is training seasons' average y per group x role bucket.
pool = shr.features.select(*K, "group").join(prev, on=K, how="left").join(
    shr.targets.select(*K, "y"), on=K
).filter(c("group").is_in(SKILL)).with_columns(
    role=pl.when(c("ppg").is_null()).then(pl.lit("none")).when(c("ppg") < 20).then(pl.lit("low"))
    .when(c("ppg") < 40).then(pl.lit("mid")).otherwise(pl.lit("high"))
)  # fmt: skip
outs = []
for s in sorted(A["season"].unique()):
    train = pool.filter(c("season") < s)
    test = pool.filter(c("season") == s)
    m = train.group_by("group", "role").agg(mean=c("y").mean())
    tr = train.join(m, on=["group", "role"]).with_columns(resid=c("y") - c("mean"), weight=pl.lit(1.0))
    off = fit_offsets(tr.select("group", "weight", "resid"), ["group"])
    te = test.join(m, on=["group", "role"], how="left").with_columns(c("mean").fill_null(0.0))
    outs.append(with_ranges(te.select(*K, "group", "y", "mean"), off, ["group"]))
role = scores.row_losses(pl.concat(outs), "amount").select(*K, r_loss="loss")
A = A.join(role, on=K, how="left")
print("\nAgainst a role yardstick (group x last season's plays per game: <20, 20-40, 40+)")
r = compare(A.select(*K, "step", "loss"), A.select(*K, loss=c("r_loss")), K, "step")
print(f"  shrunk vs role: {r.diff / A['r_loss'].mean():+.1%} [{r.lo:+.5f}, {r.hi:+.5f}]; "
      f"role vs group: {A['r_loss'].mean() / A['g_loss'].mean() - 1:+.1%}")
for x in SKILL:
    s = A.filter(c("group") == x)
    r = compare(s.select(*K, "step", "loss"), s.select(*K, loss=c("r_loss")), K, "step")
    print(f"  {x}: shrunk vs role {r.diff / s['r_loss'].mean():+.1%} [{r.lo:+.5f}, {r.hi:+.5f}]")

# Named rows: 2024's highest and lowest forecasts
names = (
    TableSource().part("player_game", "roster").sort("season", "week")
    .group_by("gsis_id").agg(name=c("full_name").drop_nulls().last())
)  # fmt: skip
show = A.filter(c("season") == 2024).join(names, on="gsis_id", how="left").select(
    "name", "group", "team", "proe_last", "proe_w", "seasons_seen", "g_mean", "mean", "y",
)
pct = lambda e: (e * 100).round(1)  # noqa: E731
show = show.with_columns(pct(c("proe_last")), pct(c("g_mean")), pct(c("mean")), pct(c("y")), c("proe_w").round(0))
with pl.Config(tbl_rows=30, tbl_width_chars=160):
    print("\n2024, highest forecasts (points of PROE)"); print(show.sort("mean", descending=True).head(8))
    print("2024, lowest forecasts"); print(show.sort("mean").head(8))
print("\ncorr(forecast lean, actual gap), skill rows:", np.corrcoef(A["lean"], A["got"])[0, 1].round(3))
