"""pace exploration, follow-up (the CEO, 2026-11-10: "Are we correctly measuring pass rate over
expected?").

1. Calibration of nflverse's expected pass chance (`xpass`): the actual pass rate minus the mean
   xpass, by season and by situation, 2006-2019 (in-sample, tag-tables#F4) and 2020-2024.
2. Our own expected pass chance, walk-forward: for each season 2010-2024, gradient-boosted trees
   fit only on earlier seasons, from the situation alone (down, distance, field position, quarter,
   time left in the half and game, score, win chance, the pre-game line's win chance). No team
   choices (shotgun, no-huddle) go in, or the team's lean would hide inside "expected". Against
   xpass: log loss, and whether teams' PROE changes (r across team-seasons, and its consistency).

Run from pcf/projects/pace/explore: PYTHONUTF8=1 ../../../.venv/Scripts/python.exe proe_check.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from common import plays
from h19_h21_pass import slices
from sklearn.ensemble import HistGradientBoostingClassifier

from pcf.validation.consistency import consistency

c = pl.col
X_COLS = ["down", "ydstogo", "yardline_100", "qtr", "half_seconds_remaining", "game_seconds_remaining", "score_differential", "wp", "vegas_wp"]


def ll(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def main() -> None:
    p = plays().filter(c("scrimmage") & (c("qtr") <= 4)).drop_nulls(X_COLS)
    print("=== 1. xpass calibration by season: actual pass rate minus mean xpass (points)")
    by = p.group_by("season").agg(gap=(c("pass").mean() - c("xpass").mean()) * 100).sort("season")
    print(" ".join(f"{s}:{g:+.1f}" for s, g in by.iter_rows()))
    print("\nby situation, 2006-2019 | 2020-2024 (points)")
    for fam, expr in slices(p).items():
        x = p.with_columns(sl=expr).drop_nulls("sl")
        t = x.group_by("sl").agg(
            early=((c("pass") - c("xpass")).filter(c("season") < 2020).mean() * 100),
            late=((c("pass") - c("xpass")).filter(c("season") >= 2020).mean() * 100),
        ).sort("sl")
        print(fam + ": " + "; ".join(f"{a} {e:+.1f} | {lt:+.1f}" for a, e, lt in t.iter_rows()))

    print("\n=== 2. our own walk-forward expected pass chance against xpass")
    own = []
    for s in range(2010, 2025):
        tr = p.filter(c("season") < s)
        te = p.filter(c("season") == s)
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.1, max_leaf_nodes=63, random_state=0)
        m.fit(tr.select(X_COLS).to_numpy(), tr["pass"].to_numpy())
        pr = m.predict_proba(te.select(X_COLS).to_numpy())[:, 1]
        y = te["pass"].to_numpy()
        print(f"{s}: log loss ours {ll(y, pr):.4f}, xpass {ll(y, te['xpass'].to_numpy()):.4f}; calibration ours {(y.mean() - pr.mean()) * 100:+.1f} pts", flush=True)
        own.append(te.select("game_id", "play_id").with_columns(xpass_own=pl.Series(pr)))
    own = pl.concat(own)
    q = p.join(own, on=["game_id", "play_id"]).with_columns(proe_own=c("pass") - c("xpass_own"))
    tg = q.group_by("game_id", "season", "week", "team").agg(proe_nflverse=c("pass_oe").mean(), proe_own=c("proe_own").mean(),
        proe_nflverse_neutral=c("pass_oe").filter(c("neutral")).mean(), proe_own_neutral=c("proe_own").filter(c("neutral")).mean())
    ts = tg.group_by("team", "season").agg(c("proe_nflverse", "proe_own").mean())
    print(f"\nteam-season PROE, ours against nflverse's (2010-2024, {ts.height} team-seasons): r {np.corrcoef(ts['proe_nflverse'], ts['proe_own'])[0, 1]:.3f}; "
          f"mean absolute difference {(ts['proe_nflverse'] - ts['proe_own']).abs().mean() * 100:.2f} pts; sd of team-season PROE {ts['proe_nflverse'].std() * 100:.2f} pts")
    for lab, d in (("2010-2019", tg.filter(c("season") < 2020)), ("2020-2024", tg.filter(c("season") >= 2020))):
        with pl.Config(float_precision=2):
            print(lab)
            print(consistency(d, ["proe_nflverse", "proe_own", "proe_nflverse_neutral", "proe_own_neutral"]).select("measure", "week_r", "week_lo", "season_r", "verdict"))


if __name__ == "__main__":
    main()
