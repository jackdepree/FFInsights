"""How close the live stand-ins are to participation's exact counts (the agreed brief, "Live
stand-ins"; decision 0052, calls 20-21), and I180's corrected stand-in.

For each measure whose attempts are a stand-in (routes, run snaps, pass snaps on defense), the
same rows are rebuilt with participation's exact attempts (2016-2024; post-season, read through a
retrospective view only here). Reported per measure:
- the season attempts' correlation and their ratio (exact over stand-in);
- **the season rate's correlation** (player-seasons with 100+ exact attempts; the pre-registered
  "close" bar is 0.95);
- **the forecast test:** next season's M1 forecast of the **exact** rate (targets 2018-2024), from
  the stand-in rows against from the exact rows. "Too poor" (pre-registered) = the stand-in's
  forecast clearly worse by more than 5% of the error.
- **I180:** each player's stand-in corrected by his ratio last season (a completed season's
  participation, allowed in season as a prior: rule m), shrunk toward his position's ratio with
  200 attempts' weight.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import data as D
from pcf.experts.stabilization import evaluate as E
from pcf.experts.stabilization import nextseason as N
from pcf.experts.stabilization import rates as R
from pcf.experts.stabilization import walks as W
from pcf.validation import stabilize as S

c = pl.col
EXACT_COL = {"tprr": "routes", "yprr": "routes", "car_per_run": "run_snaps",
             "hits_per_snap": "pass_snaps", "press_per_snap": "pass_snaps",
             "tgt_per_cov": "pass_snaps"}  # fmt: skip
PRIOR = 200.0  # I180: attempts of weight on the position's ratio


def exact_games(inp: W.Inputs, measure: str, ex: pl.DataFrame) -> pl.DataFrame:
    g = inp.games[measure].filter(c("season") >= 2016)
    col = EXACT_COL[measure]
    return g.join(ex.select("gsis_id", "game_id", exact=col), on=["gsis_id", "game_id"],
                  how="left").with_columns(standin=c("den"))  # fmt: skip


def corrected(g: pl.DataFrame) -> pl.DataFrame:
    """I180: the stand-in times his ratio (exact over stand-in) last season, shrunk toward his
    position's ratio last season with PRIOR attempts' weight; his position's ratio alone if he
    has no last season."""
    s = g.group_by("gsis_id", "season", "pos").agg(E_=c("exact").fill_null(0).sum(),
                                                   S_=c("standin").sum())  # fmt: skip
    ps = s.group_by("pos", "season").agg(rho_pos=c("E_").sum() / c("S_").sum())
    s = s.join(ps, on=["pos", "season"]).with_columns(
        ratio=(c("E_") + PRIOR * c("rho_pos")) / (c("S_") + PRIOR)
    )
    last = s.select("gsis_id", season=c("season") + 1, ratio_last="ratio")
    lastpos = ps.select("pos", season=c("season") + 1, rho_last="rho_pos")
    return g.join(last, on=["gsis_id", "season"], how="left").join(
        lastpos, on=["pos", "season"], how="left"
    ).with_columns(corr=c("standin") * pl.coalesce("ratio_last", "rho_last", pl.lit(1.0)))


def calibrated(f: pl.DataFrame) -> pl.DataFrame:
    """A diagnostic beside the pre-registered test: each version's forecast rescaled to the exact
    rate's level (intercept and slope per position, fit on earlier targets only), so a stand-in
    whose scale is off but whose ordering is right isn't charged for the scale."""
    out = []
    for pos in sorted(f["pos"].unique().to_list()):
        a = f.filter(c("pos") == pos).sort("target")
        y, w, t = a["y"].to_numpy(), a["w"].to_numpy(), a["target"].to_numpy()
        cols = {}
        for ver in ("standin", "exact"):
            X = np.column_stack([np.ones(a.height), a[ver].to_numpy()])
            cols[f"{ver}_cal"], _ = S.walk_slopes(X, y, w, t)
        out.append(a.with_columns(**{k: pl.Series(v) for k, v in cols.items()}))
    return pl.concat(out).with_columns(c("standin_cal", "exact_cal").fill_nan(None))


def report(inp: W.Inputs, out, seed: int) -> dict:
    ex = D.exact()
    out("", "== The live stand-ins against participation's exact counts (2016-2024)", "",
        "| Measure | Attempts | Season attempts r | Exact over stand-in | Season rate r "
        "(100+ exact) | I180 corrected: rate r | k stand-in, exact | M1 forecast of the exact "
        "rate: stand-in vs exact | I180 vs stand-in | Both rescaled to the exact rate's level "
        "(walk-forward, per position): stand-in vs exact | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|")  # fmt: skip
    res = {}
    for m in K.STANDIN:
        g = corrected(exact_games(inp, m, ex).filter(c("exact").is_not_null()
                                                     & (c("exact") > 0)))  # fmt: skip
        s = g.group_by("gsis_id", "season", "pos").agg(
            num=c("num").sum(), sd=c("standin").sum(), ed=c("exact").sum(), cd=c("corr").sum()
        )
        r_att = float(np.corrcoef(s["sd"], s["ed"])[0, 1])
        ratio = float(s["ed"].sum() / s["sd"].sum())
        big = s.filter(c("ed") >= 100)
        r_rate = float(np.corrcoef(big["num"] / big["sd"], big["num"] / big["ed"])[0, 1])
        b17 = big.filter(c("season") >= 2017)
        r_corr = float(np.corrcoef(b17["num"] / b17["cd"], b17["num"] / b17["ed"])[0, 1])
        r_plain17 = float(np.corrcoef(b17["num"] / b17["sd"], b17["num"] / b17["ed"])[0, 1])
        # the forecast test: each version's own M1, scored on the exact rate next season
        fc = {}
        for ver, col in (("standin", "standin"), ("exact", "exact"), ("corr", "corr")):
            gg = g.with_columns(den=c(col))
            if ver == "standin":  # the live version also has 2013-2015
                gg = pl.concat([inp.games[m].filter(c("season") < 2016), gg.select(
                    inp.games[m].columns)], how="diagonal_relaxed")  # fmt: skip
            rows = R.season_rows(gg)
            sm = N.season_m1(rows, gg)
            fc[ver] = sm.select("gsis_id", "season", **{f"f_{ver}": c("mu") + c("m1")})
            if ver == "exact":
                kx = float(sm.filter(c("season") == K.LAST)["k"][0])
                target = rows.select("gsis_id", season=c("season") - 1,
                                     y_raw=c("num") / c("den"), w="den")  # fmt: skip
                mu_x = sm.select("gsis_id", "season", "mu", "pos")
            else:
                if ver == "standin":
                    ks = float(sm.filter(c("season") == K.LAST)["k"][0])
        f = target.join(mu_x, on=["gsis_id", "season"])
        for ver in fc:
            f = f.join(fc[ver], on=["gsis_id", "season"], how="left")
        f = f.drop_nulls().with_columns(
            y=c("y_raw") - c("mu"), target=c("season") + 1,
            standin=c("f_standin") - c("mu"), exact=c("f_exact") - c("mu"),
            corr=c("f_corr") - c("mu"),
        )
        f = calibrated(f).filter(c("target").is_in(list(K.TEST)))
        g_se = E.gain(f, "standin", "exact", seed=seed)
        g_ce = E.gain(f, "corr", "standin", seed=seed)
        g_cal = E.gain(f, "standin_cal", "exact_cal", seed=seed)
        poor = g_se.hi < -0.05
        verdict = "too poor" if poor else ("close" if r_rate >= 0.95 else "usable, not close")
        out(f"| {m} | {EXACT_COL[m]} | {r_att:.3f} | {ratio:.2f} | {r_rate:.3f} | {r_corr:.3f} "
            f"(plain {r_plain17:.3f}, 2017+) | {ks:.0f}, {kx:.0f} | {g_se.fmt()} | "
            f"{g_ce.fmt()} | {g_cal.fmt()} | {verdict} |")
        res[m] = {"r_att": r_att, "ratio": ratio, "r_rate": r_rate, "r_corr": r_corr,
                  "r_plain17": r_plain17, "k_standin": ks, "k_exact": kx, "forecast": g_se,
                  "i180": g_ce, "calibrated": g_cal, "verdict": verdict}  # fmt: skip
    return res
