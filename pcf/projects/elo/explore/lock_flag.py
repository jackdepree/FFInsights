"""I19, the CEO's seed-locked flag (2026-11-07): does "seed locked going into the final week"
explain Elo's final-week misses?

Expectation (written before running): locked teams rest starters, so they score several points
below Elo's forecast, and a size fitted on 2002-2015 cuts a good part of the 1.32-point final-week
gap on 2016-2024. Eliminated teams: nothing (F11's out-of-it group showed nothing).

1. Per team in the final week, 2002-2024: points against Elo's rating-only forecast, by locked,
   eliminated, and neither.
2. The size: final-week home margin minus the rating-only forecast, regressed on
   (away locked - home locked) and (away eliminated - home eliminated), 2002-2015.
3. Applied to the validated forecasts of 2016-2024 (the margin history, pull 0.4): the final
   week's gap to the close, before and after.
4. Against the close: do locked teams also beat or miss the close? (A betting question.)

Run from pcf/: .venv/Scripts/python.exe projects/elo/explore/lock_flag.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import carryover as C  # noqa: E402
import final_week as FW  # noqa: E402

from pcf.data import standings as S  # noqa: E402

c = pl.col


def all_locks(g: pl.DataFrame) -> pl.DataFrame:
    out = []
    for season in range(2002, C.LAST + 1):
        reg = g.filter((c("season") == season) & (c("game_type") == "REG"))
        moment = reg.filter(c("week") == reg["week"].max())["kickoff"].min()
        out.append(S.final_week_locks(g, season, moment))
    return pl.concat(out)


def main() -> None:
    g = C.games()
    lk = all_locks(g)
    pre, _ = C.walk_all(g)
    last = g.filter(c("game_type") == "REG").group_by("season").agg(last=c("week").max())
    fin = pre.join(last, on="season").filter((c("week") == c("last")) & (c("game_type") == "REG"))
    h = lk.rename({"team": "home_team", "seed_locked": "h_lock", "eliminated": "h_elim"})
    a = lk.rename({"team": "away_team", "seed_locked": "a_lock", "eliminated": "a_elim"})
    fin = fin.with_columns(c("season").cast(pl.Int32)).join(h, on=["season", "home_team"]).join(a, on=["season", "away_team"])
    fin = fin.with_columns(res=c("margin") - c("fc"))

    side = pl.concat([
        fin.select("season", lock="h_lock", elim="h_elim", pts="res"),
        fin.select("season", lock="a_lock", elim="a_elim", pts=-c("res")),
    ])  # fmt: skip
    print("== 1. Final week, 2002-2024: the team's points against Elo's rating-only forecast (+ = did better)")
    for name, f in (("seed locked", c("lock") == 1), ("eliminated", c("elim") == 1), ("neither", (c("lock") == 0) & (c("elim") == 0))):
        e = side.filter(f)["pts"].to_numpy()
        m, lo, hi = FW.interval(e)
        print(f"   {name:<12}{len(e):>5} team-games  {m:+5.1f} points ({lo:+.1f} to {hi:+.1f})")

    tr = fin.filter(c("season") <= 2015)
    x = tr.select(lock=c("a_lock") - c("h_lock"), elim=c("a_elim") - c("h_elim")).to_numpy()
    b = np.linalg.lstsq(x, tr["res"].to_numpy(), rcond=None)[0]
    print(f"\n== 2. Size on 2002-2015 ({tr.height} games): a locked opponent is worth {b[0]:+.1f} points to the other team; an eliminated one {b[1]:+.1f}")

    d, _ = FW.frame()
    v = d.filter(c("part") == "final week").with_columns(c("season").cast(pl.Int32)).join(h, on=["season", "home_team"]).join(a, on=["season", "away_team"])
    v = v.with_columns(adj=c("elo") + b[0] * (c("a_lock") - c("h_lock")) + b[1] * (c("a_elim") - c("h_elim")))
    v = v.with_columns(e_adj=(c("y") - c("adj")).abs(), gap_adj=(c("y") - c("adj")).abs() - c("e_close"))
    print("\n== 3. The validated forecasts, final week 2016-2024, with the 2002-2015 size added")
    FW.head()
    FW.row("Elo as validated", v)
    FW.row("Elo + the lock flag", v.with_columns(e_elo="e_adj", gap="gap_adj"))
    any_lock = v.filter((c("h_lock") == 1) | (c("a_lock") == 1))
    FW.row("  games with a locked team, as validated", any_lock)
    FW.row("  the same games, with the flag", any_lock.with_columns(e_elo="e_adj", gap="gap_adj"))

    print("\n== 4. Locked teams against the close, 2016-2024 (+ = did better than the line)")
    side_close = pl.concat([
        v.filter(c("h_lock") == 1).select(pts=c("y") - c("spread_line")),
        v.filter(c("a_lock") == 1).select(pts=-(c("y") - c("spread_line"))),
    ])["pts"].to_numpy()  # fmt: skip
    m, lo, hi = FW.interval(side_close)
    print(f"   {len(side_close)} locked team-games: {m:+.1f} points against the close ({lo:+.1f} to {hi:+.1f})")


if __name__ == "__main__":
    main()
