"""Stabilization, the side horizon (EXPLORATION.md): the rest of a career. Measures from play-by-play
alone (2006+); players at the end of seasons 2010-2018 who play later; the target is his pooled rate
over every later season through 2024 (careers still running are cut off there). k and the true
rate's season-to-season correlation are fit on seasons through 2010, before any target season.
Discovery only; the 2025 vault is closed.

Run from pcf/:  python projects/stabilization/explore/m4_career.py   (writes m4_career.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from stab_common import Say, boot_gain, fit_m1, player_seasons, wls_r  # noqa: E402

c = pl.col
RNG = np.random.default_rng(1)
FIT_BEFORE = 2011
say = Say(Path(__file__).with_suffix(".txt"))
PBP = ["adot", "catch_oe", "yac_oe", "hitsack", "sack", "scramble", "qb_adot", "cpoe"]


def main() -> None:
    s, game = player_seasons()
    psm = (s.filter((c("den") >= 10) & c("pos").is_not_null()).group_by("measure", "pos", "season")
           .agg(mu=c("num").sum() / c("den").sum(), m=pl.len()).filter(c("m") >= 20).drop("m"))  # fmt: skip
    say("# The side horizon: the rest of a career (2026-11-25)", "",
        "Rows: a player at the end of a season S (2010-2018) with 10+ attempts that season and attempts in a later one. Target: his pooled rate over every season after S",
        "through 2024, each season centred by its position's mean (league rates shift), weighted by those later attempts. Forecasts, all centred the same way:",
        "- **raw:** his pooled rate over every season through S; **position average:** 0;",
        "- **M1, career:** that pooled rate pulled back by k (N/(N + k)); **M1, last season:** season S alone pulled back;",
        "- **M1 with drift:** M1, career, times the true rate's season-to-season correlation raised to each later season's distance, averaged over his later attempts",
        "  (the pull grows with the horizon), with the older seasons' share of the career discounted the same way (a first look, not a fitted model).",
        f"k and the correlation are fit on seasons before {FIT_BEFORE}. Players resampled.", "",
        "| Measure | k | True rate's season r | Rows | Players | Later seasons (median) | M1 career against raw | M1 career against the position average | M1 last season against M1 career | M1 with drift against M1 career | 90% interval | Clear |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|")
    for m in PBP:
        mus, s2, t2, k = fit_m1(s, game, m, FIT_BEFORE)
        d = s.filter(c("measure") == m).join(psm.filter(c("measure") == m).drop("measure"), on=["pos", "season"])
        d = d.select("gsis_id", "season", "den", dev=c("num") - c("mu") * c("den"))
        # the true rate's season-to-season correlation, on pairs before FIT_BEFORE
        a = d.filter(c("season") < FIT_BEFORE).with_columns(x=c("dev") / c("den"))
        pr = a.join(a.with_columns(c("season") - 1), on=["gsis_id", "season"], suffix="2").filter((c("den") >= 10) & (c("den2") >= 10))
        n1, n2 = pr["den"].to_numpy(), pr["den2"].to_numpy()
        w = 1 / (1 / n1 + 1 / n2)
        rho = float(np.clip(wls_r(pr["x"].to_numpy(), pr["x2"].to_numpy(), w) / np.sqrt(np.average(n1 / (n1 + k), weights=w) * np.average(n2 / (n2 + k), weights=w)), 0, 1))
        rows = []
        for S in range(2010, 2019):
            past = d.filter(c("season") <= S)
            cur = past.filter(c("season") == S).filter(c("den") >= 10).select("gsis_id", ln="den", ld="dev")
            car = past.join(cur.select("gsis_id"), on="gsis_id").with_columns(age=S - c("season")).group_by("gsis_id").agg(
                N=c("den").sum(), D=c("dev").sum(),
                Nd=(c("den") * pl.lit(rho) ** c("age")).sum(), Dd=(c("dev") * pl.lit(rho) ** c("age")).sum())
            fut = d.filter(c("season") > S).with_columns(h=c("season") - S).group_by("gsis_id").agg(
                W=c("den").sum(), Y=c("dev").sum(), rh=(c("den") * pl.lit(rho) ** c("h")).sum(), seasons=pl.len())
            x = cur.join(car, on="gsis_id").join(fut, on="gsis_id").filter(c("W") > 0)
            x = x.with_columns(y=c("Y") / c("W"), w=c("W"), raw=c("D") / c("N"), pos_avg=pl.lit(0.0),
                               m1=c("D") / (c("N") + k), m1_last=c("ld") / (c("ln") + k),
                               m1_drift=c("Dd") / (c("Nd") + k) * c("rh") / c("W"), S=pl.lit(S))  # fmt: skip
            rows.append(x)
        R = pl.concat(rows)
        g_raw, g_pos = boot_gain(R, "m1", "raw", RNG), boot_gain(R, "m1", "pos_avg", RNG)
        g_last, g_dr = boot_gain(R, "m1_last", "m1", RNG), boot_gain(R, "m1_drift", "m1", RNG)
        say(f"| {m} | {k:.0f} | {rho:.2f} | {R.height} | {R['gsis_id'].n_unique()} | {R['seasons'].median():.0f} | {g_raw[0]:+.1%} | {g_pos[0]:+.1%} ({g_pos[1]:+.1%} to {g_pos[2]:+.1%}) | "
            f"{g_last[0]:+.1%} | {g_dr[0]:+.1%} | {g_dr[1]:+.1%} to {g_dr[2]:+.1%} | {'yes' if g_dr[1] > 0 else 'no'} |")
    say.save()


if __name__ == "__main__":
    main()
