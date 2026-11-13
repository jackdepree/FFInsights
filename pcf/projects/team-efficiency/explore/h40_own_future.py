"""team-efficiency exploration, step 8: H40 judged on series success's own future.

Series success rate is the most consistent measure in checks.txt, yet it forecasts future EPA per
play worse than EPA per play does (h40_h43.txt). Does it at least forecast its *own* future (the
share of series that make a first down or a touchdown over the next 3 games / rest of the season)
better than EPA per play does? Writes h40_own_future.txt.
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/h40_own_future.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402
import h40_h43 as G  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"


def main() -> None:
    p = C.plays()
    sched = C.schedule()
    ser = p.group_by("game_id", "posteam", "series_key").agg(succ=c("series_success").first().cast(pl.Float64), epa=c("epa").sum())
    s_succ = C.sides(ser, "succ")
    tg = G.target_from_sides(s_succ, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    _, succ = C.tune(s_succ, sched, ufs)
    eq_r = pl.read_parquet(CACHE / "equal_ratings.parquet")
    by_play = C.score_ratings(eq_r, ufs)
    both = C.score_ratings(eq_r, ufs, extra={"s": succ["_ratings"]}, feats=["own", "opp", "own_s", "opp_s", "home"])
    lines = ["Future series success rate (share of series with a first down or touchdown), 2016-2024:"]
    for h in ("next3", "rest"):
        z = C.zero_pred(by_play[h])
        lines.append(f"  {h:5s} EPA per play against the league average {C.fmt(C.skill(by_play[h], z))}; series success rate against EPA per play {C.fmt(C.skill(succ[h], by_play[h]))}; both against EPA per play {C.fmt(C.skill(both[h], by_play[h]))}")
    print("\n".join(lines))
    (HERE / "h40_own_future.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
