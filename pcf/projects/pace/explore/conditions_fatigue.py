"""pace exploration, follow-up (the CEO, 2026-11-10): H24 and H25 by condition.

As h24_h25_fatigue.py, per defense-game, with the defense's first-half snaps faced as early pace
(the measure that showed anything there), and the outcome split by condition:
- H24: the defense's second-half injuries per 100 snaps on runs, on passes, in close moments (win
  chance 20-80%), and not close; each beside the same split in the first half (the placebo: an
  effect there too means it's the game, not fatigue building up).
- H25: the defense's EPA allowed per play in the fourth quarter on runs, on passes, on 3rd down,
  when close and when not; the third quarter beside it.
Season means removed; 90% intervals from resampling whole weeks; strengths held for H25.

Run from pcf/projects/pace/explore: PYTHONUTF8=1 ../../../.venv/Scripts/python.exe conditions_fatigue.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from common import boot, plays

c = pl.col
COND = {
    "runs": c("rush") == 1,
    "passes": c("pass") == 1,
    "3rd down": c("down") == 3,
    "close (20-80%)": c("wp").is_between(0.2, 0.8),
    "not close": ~c("wp").is_between(0.2, 0.8),
}


def coef(d: pl.DataFrame, y: str, xs: list[str]) -> float:
    d = d.drop_nulls([y, *xs])
    X = np.column_stack([np.ones(d.height), *[d[x] for x in xs]])
    return float(np.linalg.lstsq(X, d[y].to_numpy(), rcond=None)[0][1]) * 10


def main() -> None:
    p = plays().filter((c("qtr") <= 4) & c("scrimmage")).with_columns(half=pl.when(c("qtr") <= 2).then(1).otherwise(2))
    aggs = [(c("half") == 1).sum().alias("faced1"), c("epa").mean().alias("epa_all")]
    for name, cond in COND.items():
        for h in (1, 2):
            m = cond & (c("half") == h)
            aggs.append(pl.when(m.sum() > 0).then(c("inj_def").filter(m).sum() / m.sum() * 100).alias(f"inj{h}|{name}"))
        for q in (3, 4):
            m = cond & (c("qtr") == q)
            aggs.append(c("epa").filter(m).mean().alias(f"q{q}|{name}"))
    t = p.group_by("game_id", "season", "week", team=c("defteam"), opp=c("posteam")).agg(aggs)
    t = t.with_columns(pl.col(pl.Float64).fill_nan(None))
    t = t.with_columns(def_str=(c("epa_all").sum().over("team", "season") - c("epa_all")) / (c("epa_all").count().over("team", "season") - 1))
    off = t.select("game_id", "season", team=c("opp"), e=c("epa_all")).with_columns(
        off_str=(c("e").sum().over("team", "season") - c("e")) / (c("e").count().over("team", "season") - 1))
    t = t.join(off.select("game_id", opp=c("team"), off_str="off_str"), on=["game_id", "opp"], how="left")
    num = [x for x in t.columns if "|" in x] + ["faced1", "def_str", "off_str"]
    t = t.with_columns([(c(x) - c(x).mean().over("season")).alias(x) for x in num]).with_columns(wk=c("season").cast(pl.Utf8) + "-" + c("week").cast(pl.Utf8))
    print(f"{t.height} defense-games, 2006-2024")
    print("\n=== H24 by condition: defensive injuries per 100 snaps, per +10 first-half snaps faced (90%)")
    for name in COND:
        r = {h: boot(t, lambda d, h=h: coef(d, f"inj{h}|{name}", ["faced1", "def_str"]), by="wk", n=150) for h in (1, 2)}
        print(f"{name}: second half {r[2][0]:+.3f} ({r[2][1]:+.3f} to {r[2][2]:+.3f}) | first half (placebo) {r[1][0]:+.3f} ({r[1][1]:+.3f} to {r[1][2]:+.3f})")
    print("\n=== H25 by condition: EPA allowed per play, per +10 first-half snaps faced, strengths held (90%)")
    for name in COND:
        r = {q: boot(t, lambda d, q=q: coef(d, f"q{q}|{name}", ["faced1", "off_str", "def_str"]), by="wk", n=150) for q in (3, 4)}
        print(f"{name}: Q4 {r[4][0]:+.4f} ({r[4][1]:+.4f} to {r[4][2]:+.4f}) | Q3 {r[3][0]:+.4f} ({r[3][1]:+.4f} to {r[3][2]:+.4f})")


if __name__ == "__main__":
    main()
