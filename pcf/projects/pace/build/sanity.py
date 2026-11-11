"""The brief's football sanity tests, on the finished backtests and the built table:
the volume models' weights (fit once on 2010-2024 rows, for reading only), the range of game
totals forecast, and whether a coach change moves a team's pace more than no change."""

import glob
import os

import numpy as np
import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.data.tables.store import read_part
from pcf.data.timeline.moments import RUNS  # noqa: F401
from pcf.experts.pace.model import VARIANTS
from pcf.validation.splits import steps

c = pl.col
gw = Gateway()
ex = VARIANTS["plays_full"]()
every = steps(gw.calendar, ex.cadence, list(range(2010, 2025)), ex.run)
view = gw.view(END_OF_TIME, ex.cadence, ex.inputs)
feats = ex.features_history(view, pl.concat([s.games for s in every]))
for v in ("plays", "dropbacks", "runs"):
    for kind in ("full", "neutral"):
        m = VARIANTS[f"{v}_{kind}"]()
        y = m.target(view)
        train = feats.join(y.select("game_id", "team", "y"), on=["game_id", "team"]).with_columns(
            weight=pl.lit(1.0)
        )
        coef = m.explain(m.fit(train))["coefficients"]
        sd = {n: float(train.select(e).to_series().std() or 1.0) for n, e in m._columns()}
        print(f"\n{v}_{kind}: per sd of each input (spread and total per point)")
        for n, b in coef.items():
            unit = 1.0 if n in ("spread", "total_line", "intercept") else sd[n]
            print(f"  {n:<22} {b * unit:+.2f}")

# forecast game totals (both teams), 2016-2024
runs = sorted(glob.glob("data/outputs/pace/plays_full/*/history.parquet"), key=os.path.getmtime)
h = pl.read_parquet(runs[-1]).filter(c("as_of").dt.year() >= 2016)
g = h.group_by("game_id").agg(c("mean").sum(), pl.len()).filter(c("len") == 2)["mean"]
print("\ngame totals forecast: 1%", round(g.quantile(0.01), 1), "median", round(g.median(), 1),
      "99%", round(g.quantile(0.99), 1), "min", round(g.min(), 1), "max", round(g.max(), 1))

# coach changes: a team's season pace over expected (gap from the league) against last season's
s = list(range(2006, 2025))
sched = (
    read_part("team_game", "schedule", seasons=s).select("game_id", "team", "season", "game_type")
    .join(read_part("team_game", "pregame", seasons=s).select("game_id", "team", "coach"), on=["game_id", "team"])
    .collect()
)
pace = read_part("team_game", "pace", seasons=s).select("game_id", "team", "pace_oe", "proe").collect()
t = (
    sched.filter(c("game_type") == "REG").join(pace, on=["game_id", "team"])
    .with_columns((c(x) - c(x).mean().over("season")).alias(x) for x in ("pace_oe", "proe"))
    .group_by("team", "season").agg(c("pace_oe").mean(), c("proe").mean(), c("coach").mode().first())
    .sort("team", "season")
    .with_columns(
        prev_coach=c("coach").shift().over("team"), prev_pace=c("pace_oe").shift().over("team"),
        prev_proe=c("proe").shift().over("team"), prev_season=c("season").shift().over("team"),
    )
    .filter(c("prev_season") == c("season") - 1)
    .with_columns(new=c("coach") != c("prev_coach"))
)
for x in ("pace", "proe"):
    col = "pace_oe" if x == "pace" else "proe"
    out = t.group_by("new").agg(
        pl.len(), (c(col) - c(f"prev_{x}")).abs().mean().alias("abs_change"),
        pl.corr(col, f"prev_{x}").alias("r_with_last_season"),
    ).sort("new")
    print(f"\n{x} over expected, season to season, by coach change:\n{out}")
