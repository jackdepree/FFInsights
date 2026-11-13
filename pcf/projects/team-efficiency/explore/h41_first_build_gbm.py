"""FIRST BUILD (kept as a record; it failed as a method): play-by-play gradient-boosted weights fit noise. See h41_h44.py for the second build.
(The original docstring: H41, a model decides which plays count, and H44, mesh EPA and WPA.)

- **H41, representativeness weights:** per play, how much plays like it predict the team's later
  games that season (E[y F | situation] / E[y^2 | situation], two gradient-boosted models on
  2006-2015 only), separately for what a play says about the offense and about the defense.
  Situation: win chance, score, quarter, clock, down, distance, field, pass or run.
- **H44a:** the same with the EPA-WPA gap (and its size) added to the situation.
- **H44b:** WPA per play as its own rating, and EPA and WPA ratings together.

Every variant is scored on the main test against the bar (the usual garbage-time rule) and
against all plays counting equally. Writes h41_h44.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/h41_h44.py
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
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    p = C.plays()
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    fut = C.future(tg)
    p = p.join(fut.select("game_id", posteam="team", F_off="F_off"), on=["game_id", "posteam"], how="left").join(
        fut.select("game_id", defteam="team", F_def="F_def"), on=["game_id", "defteam"], how="left"
    )
    p = p.with_columns(abs_gap=c("gap").abs())
    bar = {h: pl.read_parquet(CACHE / f"bar_{h}.parquet") for h in ("next3", "rest")}

    # The equal-weight reference, tuned (rung1 tuned it too; recomputed here to have its ratings).
    prm_eq, eq = C.tune(C.sides(p, "epa"), sched, ufs)
    say(f"all plays, equal: settings {prm_eq} ({time.time() - t0:.0f}s)")

    feats = {"H41 situation": C.SITUATION, "H41+H44a situation + gap": C.SITUATION + ["gap", "abs_gap"]}
    results = {"all plays, equal": eq}
    weights = {}
    for name, fs in feats.items():
        w_off, _ = C.learn_weights(p, fs, "F_off")
        w_def, _ = C.learn_weights(p, fs, "F_def")
        q = p.with_columns(w_off=pl.Series(w_off), w_def=pl.Series(w_def))
        weights[name] = q.select("season", "wp", "qtr", "half_seconds_remaining", "score_differential", "is_pass", "down", "gap", "usual", "w_off", "w_def")
        prm, r, out = C.tune_split(C.sides(q, "epa", "w_off"), C.sides(q, "epa", "w_def"), sched, ufs)
        results[name] = out | {"_ratings": r}
        say(f"{name}: settings offense {prm[0]}, defense {prm[1]} ({time.time() - t0:.0f}s)")
        r.write_parquet(CACHE / f"ratings_{name.split()[0].replace('+', '_')}.parquet")
        q.select("game_id", "play_id", "w_off", "w_def").write_parquet(CACHE / f"weights_{name.split()[0].replace('+', '_')}.parquet")

    # H44b: WPA as a rating, and EPA with WPA.
    prm_w, wpa = C.tune(C.sides(p, "wpa"), sched, ufs)
    say(f"WPA per play: settings {prm_w} ({time.time() - t0:.0f}s)")
    results["H44b WPA per play"] = wpa
    both = C.score_ratings(eq["_ratings"], ufs, extra={"wpa": wpa["_ratings"]}, feats=["own", "opp", "own_wpa", "opp_wpa", "home"])
    results["H44b EPA and WPA together"] = both

    say("")
    say("The main test, 2016-2024: skill against the bar (usual garbage-time rule) and against all plays equal")
    for h in ("next3", "rest"):
        for k, v in results.items():
            say(f"  {h:5s} {k:28s} vs bar {C.fmt(C.skill(v[h], bar[h]))} | vs equal {C.fmt(C.skill(v[h], eq[h]))} | off {C.fmt(C.skill(v[h], eq[h], side='off'))} def {C.fmt(C.skill(v[h], eq[h], side='def'))}")
    say("")
    say("2020-2024 only, against all plays equal:")
    for h in ("next3", "rest"):
        for k, v in results.items():
            if k == "all plays, equal":
                continue
            say(f"  {h:5s} {k:28s} {C.fmt(C.skill(v[h], eq[h], seasons=list(range(2020, 2025))))}")

    say("")
    say("What the weights learned (mean weight, 2016-2024 plays; 1 = an average play):")
    for name, wq in weights.items():
        x = wq.filter(c("season") >= 2016)
        say(f"  {name}:")
        wpb = x.with_columns(b=(c("wp") * 10).floor().clip(0, 9)).group_by("b").agg(c("w_off").mean(), c("w_def").mean(), pl.len()).sort("b")
        say("    by win chance (offense's), tenths:      off " + " ".join(f"{v:.2f}" for v in wpb["w_off"]) + " | def " + " ".join(f"{v:.2f}" for v in wpb["w_def"]))
        q4 = x.group_by("qtr").agg(c("w_off").mean(), c("w_def").mean()).sort("qtr")
        say("    by quarter (1-4, OT):                   off " + " ".join(f"{v:.2f}" for v in q4["w_off"]) + " | def " + " ".join(f"{v:.2f}" for v in q4["w_def"]))
        pr = x.group_by("is_pass").agg(c("w_off").mean(), c("w_def").mean()).sort("is_pass")
        say(f"    run / pass:                             off {pr['w_off'][0]:.2f} / {pr['w_off'][1]:.2f} | def {pr['w_def'][0]:.2f} / {pr['w_def'][1]:.2f}")
        u = x.group_by("usual").agg(c("w_off").mean(), c("w_def").mean(), pl.len()).sort("usual")
        say(f"    garbage time by the usual rule / not:   off {u['w_off'][0]:.2f} / {u['w_off'][1]:.2f} | def {u['w_def'][0]:.2f} / {u['w_def'][1]:.2f} (share of plays in garbage time {u['len'][0] / x.height:.1%})")
        say(f"    share of plays with weight 0:           off {(x['w_off'] == 0).mean():.1%} | def {(x['w_def'] == 0).mean():.1%}")
        if "gap" in name:
            g = x.with_columns(b=pl.col("gap").qcut(10, labels=[str(i) for i in range(10)], allow_duplicates=True)).group_by("b").agg(c("w_off").mean(), c("w_def").mean(), c("gap").mean()).sort("gap")
            say("    by EPA-WPA gap (tenths, low to high): off " + " ".join(f"{v:.2f}" for v in g["w_off"]) + " | def " + " ".join(f"{v:.2f}" for v in g["w_def"]))
    (HERE / "h41_first_build_gbm.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
