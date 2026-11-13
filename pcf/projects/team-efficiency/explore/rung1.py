"""team-efficiency exploration, step 2: the bar (rung 1) and its checks.

- **The bar:** ridge offense + defense + home on EPA per play, with the usual garbage-time rule
  (win chance 10-90%, not the last two minutes of a half), a recency weight and last season as the
  prior. Settings tuned on 2007-2015.
- **All plays, equal weights:** the same without the rule (H41's "equal" side).
- **Shuffled:** plays' EPA shuffled within each season-week, then the bar's pipeline: the
  signal-free version of the bar.
- **The league average:** predicting 0 (the target is relative to the league).

Writes rung1.txt and caches the bar's predictions for the other steps. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/rung1.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"


def main() -> None:
    t0 = time.time()
    p = C.plays()
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    variants = {
        "bar (usual rule)": C.sides(p, "epa", "usual"),
        "all plays, equal": C.sides(p, "epa"),
    }
    # Shuffle EPA within each season-week: position k of a block (in play order) gets the EPA of
    # a random play of the same block.
    rng = np.random.default_rng(0)
    order = p.with_row_index("i").sort("season", "week").with_columns(r=pl.Series(rng.random(p.height)))
    base = order["i"].to_numpy()
    perm = order.sort("season", "week", "r")["i"].to_numpy()
    e = p["epa"].to_numpy()
    e_sh = e.copy()
    e_sh[base] = e[perm]
    sh = p.with_columns(epa=pl.Series(e_sh))
    variants["shuffled bar"] = C.sides(sh, "epa", "usual")

    out = {}
    for name, s in variants.items():
        prm, o = C.tune(s, sched, ufs)
        out[name] = o
        say(f"{name}: settings {prm} ({time.time() - t0:.0f}s)")
    bar = out["bar (usual rule)"]
    for h in ("next3", "rest"):
        bar[h].write_parquet(CACHE / f"bar_{h}.parquet")
    bar["_ratings"].write_parquet(CACHE / "bar_ratings.parquet")

    say("")
    say("Squared error on 2016-2024 (EPA per play relative to the league, per team and moment):")
    for h in ("next3", "rest"):
        z = C.zero_pred(bar[h])
        say(f"  {h}: league average {C.mse(z, C.SCORE):.5f}; " + "; ".join(f"{k} {C.mse(v[h], C.SCORE):.5f}" for k, v in out.items()))
    say("")
    say("Skill against the league average (share of its squared error removed), 2016-2024, by side:")
    for h in ("next3", "rest"):
        z = C.zero_pred(bar[h])
        for k, v in out.items():
            say(f"  {h:5s} {k:18s} offense {C.fmt(C.skill(v[h], z, side='off'))}; defense {C.fmt(C.skill(v[h], z, side='def'))}")
    say("")
    say("Skill against the bar, 2016-2024 (positive = better than the bar):")
    for h in ("next3", "rest"):
        for k, v in out.items():
            if k.startswith("bar"):
                continue
            say(f"  {h:5s} {k:18s} pooled {C.fmt(C.skill(v[h], bar[h]))}; offense {C.fmt(C.skill(v[h], bar[h], side='off'))}; defense {C.fmt(C.skill(v[h], bar[h], side='def'))}")
    say("")
    say("2020-2024 only (nflverse's EPA isn't fitted on these seasons, tag-tables#F4):")
    for h in ("next3", "rest"):
        z = C.zero_pred(bar[h])
        say(f"  {h:5s} bar against the league average {C.fmt(C.skill(bar[h], z, seasons=list(range(2020, 2025))))}; all plays against the bar {C.fmt(C.skill(out['all plays, equal'][h], bar[h], seasons=list(range(2020, 2025))))}")
    (HERE / "rung1.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
