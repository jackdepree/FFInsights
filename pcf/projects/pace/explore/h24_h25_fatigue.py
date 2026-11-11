"""pace exploration (2026-11-10): H24 (high early pace, more injuries later) and H25 (high early
pace tires the defense later). Discovery for `injury-fatigue`, not this expert's forecast.

Early pace, per game and per side, from the first half: scrimmage snaps, and the clock-aware pace
over expected (h22_h23_pace.py's `clock` model, refit here out of fold). Injuries: snaps whose
description says a player "was injured during the play", by side (offense, defense).

H24: second-half injuries, per game and per second-half snap, against first-half pace. More
snaps is more exposure, so the per-snap rate is the fatigue test. Every comparison is within a
season (season means removed), and the 90% interval comes from resampling whole weeks.

H25: a defense's fourth-quarter EPA allowed per play (Q4 plays at win chance 5-95%, so garbage
time doesn't decide it) against its first-half snaps faced and the opposing offense's first-half
pace, beyond both teams' strength: the offense's and the defense's season EPA per play in their
other games (this game left out). The third quarter is the comparison.

Run from pcf/projects/pace/explore: PYTHONUTF8=1 ../../../.venv/Scripts/python.exe h24_h25_fatigue.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from common import boot, plays
from h22_h23_pace import CLOCK, expected

c = pl.col


def demean(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    return df.with_columns([(c(x) - c(x).mean().over("season")).alias(x) for x in cols])


def slope(df: pl.DataFrame, y: str, xs: list[str], k: int = 0) -> float:
    d = df.drop_nulls([y, *xs])
    X = np.column_stack([np.ones(d.height), *[d[x] for x in xs]])
    return float(np.linalg.lstsq(X, d[y].to_numpy(), rcond=None)[0][1 + k])


def report(df, y, xs, k, scale, label):
    est, lo, hi = boot(df, lambda d: slope(d, y, xs, k) * scale, by="wk", n=200)
    print(f"{label}: {est:+.4f} (90% {lo:+.4f} to {hi:+.4f})")


def main() -> None:
    p = plays().filter((c("qtr") <= 4))
    s = p.filter(c("gap").is_not_null() & c("wp").is_not_null() & c("ep").is_not_null())
    s = expected(s, CLOCK, "clock").with_columns(oe=c("gap") - c("exp_clock")).select("game_id", "play_id", "oe")
    p = p.join(s, on=["game_id", "play_id"], how="left").with_columns(half=pl.when(c("qtr") <= 2).then(1).otherwise(2))
    sc = p.filter(c("scrimmage"))

    # ---- H24, per game (both teams)
    g = sc.group_by("game_id", "season", "week").agg(
        snaps1=(c("half") == 1).sum(), snaps2=(c("half") == 2).sum(),
        oe1=c("oe").filter(c("half") == 1).mean(),
        inj1=c("inj_any").filter(c("half") == 1).sum(), inj2=c("inj_any").filter(c("half") == 2).sum(),
    ).with_columns(rate2=c("inj2") / c("snaps2") * 100, rate1=c("inj1") / c("snaps1") * 100, wk=c("season").cast(pl.Utf8) + "-" + c("week").cast(pl.Utf8))
    print(f"=== H24: {g.height} games; injuries per game: first half {g['inj1'].mean():.2f}, second half {g['inj2'].mean():.2f}; per 100 snaps {g['rate1'].mean():.2f} and {g['rate2'].mean():.2f}")
    gd = demean(g, ["snaps1", "snaps2", "oe1", "inj2", "rate2", "rate1"])
    report(gd, "inj2", ["snaps1"], 0, 10, "second-half injuries per +10 first-half snaps (exposure not held)")
    report(gd, "inj2", ["snaps1", "snaps2"], 0, 10, "second-half injuries per +10 first-half snaps, second-half snaps held")
    report(gd, "rate2", ["snaps1"], 0, 10, "second-half injuries per 100 snaps, per +10 first-half snaps (fatigue)")
    report(gd, "rate2", ["oe1"], 0, -1, "second-half injuries per 100 snaps, per 1 s faster first-half pace over expected (fatigue)")
    report(gd, "rate1", ["oe1"], 0, -1, "placebo: first-half injuries per 100 snaps, per 1 s faster first-half pace")
    q = g.with_columns(qq=c("snaps1").qcut(4, labels=["fewest", "2", "3", "most"])).group_by("qq").agg(
        snaps1=c("snaps1").mean(), rate2=c("rate2").mean(), inj2=c("inj2").mean(), n=pl.len()).sort("snaps1")
    print(q)

    # ---- H24 by side and H25, per defense
    t = sc.group_by("game_id", "season", "week", team=c("defteam"), opp=c("posteam")).agg(
        faced1=(c("half") == 1).sum(), faced2=(c("half") == 2).sum(),
        opp_oe1=c("oe").filter(c("half") == 1).mean(),
        def_inj2=c("inj_def").filter(c("half") == 2).sum(),
        epa_q4=c("epa").filter((c("qtr") == 4) & c("wp").is_between(0.05, 0.95)).mean(),
        n_q4=((c("qtr") == 4) & c("wp").is_between(0.05, 0.95)).sum(),
        epa_q3=c("epa").filter((c("qtr") == 3) & c("wp").is_between(0.05, 0.95)).mean(),
        epa_all=c("epa").mean(),
    ).with_columns(def_rate2=c("def_inj2") / c("faced2") * 100, wk=c("season").cast(pl.Utf8) + "-" + c("week").cast(pl.Utf8))
    # strength in other games: offense's EPA per play and defense's EPA allowed per play, this game left out
    off = t.select("game_id", "season", team=c("opp"), e=c("epa_all"))
    off = off.with_columns(off_str=(c("e").sum().over("team", "season") - c("e")) / (c("e").count().over("team", "season") - 1))
    dfn = t.with_columns(def_str=(c("epa_all").sum().over("team", "season") - c("epa_all")) / (c("epa_all").count().over("team", "season") - 1))
    t = dfn.join(off.select("game_id", opp=c("team"), off_str="off_str"), on=["game_id", "opp"], how="left")
    t = t.filter(c("n_q4") >= 8)
    print(f"\n=== H24 by side: defensive injuries in the second half, {t.height} defense-games")
    td = demean(t, ["faced1", "faced2", "opp_oe1", "def_inj2", "def_rate2", "epa_q4", "epa_q3", "off_str", "def_str"])
    report(td, "def_rate2", ["faced1"], 0, 10, "defense's second-half injuries per 100 snaps, per +10 first-half snaps faced")
    report(td, "def_rate2", ["opp_oe1"], 0, -1, "defense's second-half injuries per 100 snaps, per 1 s faster opposing first-half pace")

    print(f"\n=== H25: fourth-quarter EPA allowed per play (higher = defense worse), {t.height} defense-games")
    xs = ["faced1", "off_str", "def_str"]
    report(td, "epa_q4", xs, 0, 10, "Q4 EPA allowed per play, per +10 first-half snaps faced, strengths held")
    report(td, "epa_q3", xs, 0, 10, "comparison, Q3")
    report(td, "epa_q4", ["opp_oe1", "off_str", "def_str"], 0, -1, "Q4 EPA allowed per play, per 1 s faster opposing first-half pace, strengths held")
    report(td, "epa_q3", ["opp_oe1", "off_str", "def_str"], 0, -1, "comparison, Q3")
    print("typical sizes: sd of first-half snaps faced", round(t["faced1"].std(), 1), "| sd of Q4 EPA per play", round(t["epa_q4"].std(), 3), "| sd of opposing first-half pace over expected", round(t["opp_oe1"].std(), 2))


if __name__ == "__main__":
    main()
