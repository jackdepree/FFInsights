"""team-efficiency exploration, step 3 (second build, shrunk toward equal weights): H41 (a model decides which plays count) and
H44 (mesh EPA and WPA; the EPA-WPA gap as a feature for that model).

The first build (h41_first_build_gbm.py) learned a weight per play with gradient boosting and fit
noise: the signal in one play about a team's future is far smaller than the play's own spread.
This build learns at the team level, where the noise averages out:

- **H41, representativeness weights by kind of play:** every play gets a kind (win-chance band x
  pass or run, and the last two minutes of a half). Across team-seasons of 2006-2015, a regression
  says how much one play of each kind moves the team's EPA per play in its *other* games (odd weeks
  predict even weeks and back). That slope is the play's weight, separately for what it says about
  the offense and about the defense. The weights are shrunk toward equal, by a strength picked by
  leaving one season out (unshrunk, they were jumpy and lost to equal weights by 1-2%).
- **H44a:** the same, with the plays at the extremes of the EPA-WPA gap (top and bottom 5%) as
  kinds of their own.
- **H44b:** WPA per play as its own rating, and EPA and WPA ratings together.

Every variant is scored on the main test against the bar (the usual garbage-time rule) and against
all plays counting equally. Writes h41_h44.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/h41_h44.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
import time
from pathlib import Path

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
    bar = {h: pl.read_parquet(CACHE / f"bar_{h}.parquet") for h in ("next3", "rest")}

    prm_eq, eq = C.tune(C.sides(p, "epa"), sched, ufs)
    eq["_ratings"].write_parquet(CACHE / "equal_ratings.parquet")
    for h in ("next3", "rest"):
        eq[h].write_parquet(CACHE / f"equal_{h}.parquet")
    say(f"all plays, equal: settings {prm_eq} ({time.time() - t0:.0f}s)")
    results = {"all plays, equal": eq}

    for name, gap in (("H41 kinds of play", False), ("H41+H44a kinds + gap extremes", True)):
        q = C.play_classes(p, gap=gap)
        wo, lo, cvo = C.class_weights_shrunk(q, "off")
        wd, ld, cvd = C.class_weights_shrunk(q, "def")
        say("")
        say(f"{name}: weight per play by kind, shrunk toward equal (1 = the average play's weight; share of 2006-2015 plays)")
        say(f"  shrinkage picked by leaving one season out: offense {lo} (CV error {100 * (cvo[lo] / cvo[1e4] - 1):+.2f}% against equal), defense {ld} ({100 * (cvd[ld] / cvd[1e4] - 1):+.2f}%)")
        both = wo.rename({"beta": "b_off"}).join(wd.select("kind", b_def="beta"), on="kind")
        mo = float((both["b_off"] * both["share"]).sum())
        md = float((both["b_def"] * both["share"]).sum())
        for r in both.sort("kind").iter_rows(named=True):
            say(f"  {r['kind']:22s} share {r['share']:6.1%}  offense {r['b_off'] / mo:5.2f}  defense {r['b_def'] / md:5.2f}")
        q = q.join(wo.select("kind", w_off=c("beta").clip(0, None) / mo), on="kind").join(wd.select("kind", w_def=c("beta").clip(0, None) / md), on="kind")
        prm, r, out = C.tune_split(C.sides_sum(q, "y_rel", "w_off"), C.sides_sum(q, "y_rel", "w_def"), sched, ufs)
        results[name] = out
        say(f"  settings offense {prm[0]}, defense {prm[1]} ({time.time() - t0:.0f}s)")
        tag = "h41" if not gap else "h44a"
        r.write_parquet(CACHE / f"ratings_{tag}.parquet")
        q.select("game_id", "play_id", "kind", "w_off", "w_def").write_parquet(CACHE / f"weights_{tag}.parquet")

    prm_w, wpa = C.tune(C.sides(p, "wpa"), sched, ufs)
    wpa["_ratings"].write_parquet(CACHE / "wpa_ratings.parquet")
    say("")
    say(f"WPA per play: settings {prm_w} ({time.time() - t0:.0f}s)")
    results["H44b WPA per play"] = wpa
    results["H44b EPA and WPA together"] = C.score_ratings(eq["_ratings"], ufs, extra={"wpa": wpa["_ratings"]}, feats=["own", "opp", "own_wpa", "opp_wpa", "home"])

    say("")
    say("The main test, 2016-2024: skill against the bar (usual garbage-time rule) and against all plays equal")
    for h in ("next3", "rest"):
        for k, v in results.items():
            say(f"  {h:5s} {k:30s} vs bar {C.fmt(C.skill(v[h], bar[h]))} | vs equal {C.fmt(C.skill(v[h], eq[h]))} | off {C.fmt(C.skill(v[h], eq[h], side='off'))} def {C.fmt(C.skill(v[h], eq[h], side='def'))}")
    say("")
    say("2020-2024 only, against all plays equal:")
    for h in ("next3", "rest"):
        for k, v in results.items():
            if k != "all plays, equal":
                say(f"  {h:5s} {k:30s} {C.fmt(C.skill(v[h], eq[h], seasons=list(range(2020, 2025))))}")
    (HERE / "h41_h44.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
