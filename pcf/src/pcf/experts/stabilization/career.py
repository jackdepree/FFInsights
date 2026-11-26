"""The side horizon: the rest of a career (the agreed brief, "rest of career: a side report";
decision 0052, call 19).

Rows: a player at the end of season S (2010-2018) with MIN_DEN+ attempts that season and attempts
later. Target: his pooled rate over every later season through 2024, each season centred by its
own position mean, weighted by those attempts (careers still running are cut at 2024). Unlike the
exploration (fit once before 2011), k and the true rate's season r are fit walk-forward, on
seasons up to S. Forecasts:
- `raw` his career rate so far; `avg` 0;
- `m1` the career rate pulled by k (N / (N + k));
- `m1_drift`: the drift folded in: older seasons discounted by rho^age, and the forecast pulled by
  rho^h averaged over his later attempts (the pull grows with the horizon).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.experts.stabilization import evaluate as E
from pcf.experts.stabilization import rates as R
from pcf.experts.stabilization import walks as W

c = pl.col
PBP = ("adot", "catch_oe", "yac_oe", "hitsack", "sack", "scramble", "qb_adot", "cpoe")
ENDS = tuple(range(2010, 2019))


def frame(inp: W.Inputs, measure: str) -> pl.DataFrame:
    rows, games = inp.rows[measure], inp.games[measure]
    d = R.centred(rows).select("gsis_id", "season", "den", dev=c("x") * c("den"))
    all_d = rows.join(R.class_means(rows), on=["pos", "season"]).select(
        "gsis_id", "season", "den", dev=c("num") - c("mu") * c("den")
    )
    out = []
    for S in ENDS:
        f = R.fit_k(rows, games, S)
        k = f["k"]
        p = W.N.pairs(inp.sm(measure).filter(c("season") < S), rows)
        nxt = R.centred(rows).select("gsis_id", season=c("season") - 1, x2="x")
        p = p.join(nxt, on=["gsis_id", "season"]).with_columns(y=c("x2"))
        rho = float(np.clip(R.season_r(p, k), 0, 1))
        past = all_d.filter(c("season") <= S)
        cur = d.filter(c("season") == S).select("gsis_id")
        car = (
            past.join(cur, on="gsis_id")
            .with_columns(age=S - c("season"))
            .group_by("gsis_id")
            .agg(
                N=c("den").sum(),
                Dv=c("dev").sum(),
                Nd=(c("den") * pl.lit(rho) ** c("age")).sum(),
                Dd=(c("dev") * pl.lit(rho) ** c("age")).sum(),
            )
        )
        fut = (
            all_d.filter(c("season") > S)
            .with_columns(h=c("season") - S)
            .group_by("gsis_id")
            .agg(
                W=c("den").sum(),
                Y=c("dev").sum(),
                rh=(c("den") * pl.lit(rho) ** c("h")).sum(),
                seasons=pl.len(),
            )
        )
        x = car.join(fut, on="gsis_id").filter(c("W") > 0)
        out.append(
            x.with_columns(
                y=c("Y") / c("W"),
                w=c("W"),
                raw=c("Dv") / c("N"),
                avg=pl.lit(0.0),
                m1=c("Dv") / (c("N") + k),
                m1_drift=c("Dd") / (c("Nd") + k) * c("rh") / c("W"),
                season=pl.lit(S),
                k=pl.lit(k),
                rho=pl.lit(rho),
            )
        )
    return pl.concat(out)


def report(inp: W.Inputs, out, seed: int) -> dict:
    out(
        "",
        "== The rest of a career (side report): players at the end of 2010-2018, the target "
        "pooled through 2024; k and the true rate's season r fit on seasons up to the end season",
        "",
        "| Measure | k (mean) | rho (mean) | Rows | Players | M1 vs raw | M1 vs average | "
        "Drift folded in vs M1 |",
        "|---|---|---|---|---|---|---|---|",
    )
    res = {}
    for m in PBP:
        f = frame(inp, m)
        g = {
            "m1_raw": E.gain(f, "m1", "raw", seed=seed),
            "m1_avg": E.gain(f, "m1", "avg", seed=seed),
            "drift_m1": E.gain(f, "m1_drift", "m1", seed=seed),
        }
        out(
            f"| {m} | {f['k'].mean():.0f} | {f['rho'].mean():.2f} | {f.height} | "
            f"{f['gsis_id'].n_unique()} | {g['m1_raw'].fmt()} | {g['m1_avg'].fmt()} | "
            f"{g['drift_m1'].fmt()} |"
        )
        res[m] = g
    return res
