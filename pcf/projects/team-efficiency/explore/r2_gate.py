"""team-efficiency exploration, round two (2026-11-13), idea 3 continued: a hard gate chosen on
2007-2015.

r2_stack.py's week-gated stack helped in weeks 1-4 and gave some of it back later. A gate that
*chooses*, per part of the season (weeks 1-4, 5-9, 10+), side and horizon, between the stack and
the EPA rating alone, by their 2007-2015 error. The stack's 2007-2015 error is leave-one-season-out
(no in-sample optimism); the EPA rating's map has only three numbers, so its in-sample error is used.
Nothing from 2016-2024 is looked at to choose. Writes r2_gate.txt.
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r2_gate.py
"""

# ruff: noqa: E501
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402
import r2_stack as S  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"
K = ["season", "w", "team", "side"]


def main() -> None:
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    p = C.plays()
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    eq = {h: pl.read_parquet(CACHE / f"equal_{h}.parquet") for h in ("next3", "rest")}
    r_epa = pl.read_parquet(CACHE / "ratings_combo.parquet")
    ref = C.score_ratings(r_epa, ufs)
    ser = p.group_by("game_id", "posteam", "series_key").agg(succ=c("series_success").first().cast(pl.Float64))
    rats = {
        "ssr": S.tuned(C.sides(ser, "succ"), sched, ufs),
        "sr": S.tuned(C.sides(p.with_columns(sv=c("success").cast(pl.Float64)), "sv"), sched, ufs),
        "pass": S.tuned(C.sides(p.filter(c("is_pass") == 1), "epa"), sched, ufs),
        "run": S.tuned(C.sides(p.filter(c("is_pass") == 0), "epa"), sched, ufs),
        "season": S.tuned(C.sides(p, "epa"), sched, ufs, [C.Params(h, l, 0.0) for h, l in itertools.product((4.0, 8.0, 16.0, 1000.0), (0.5, 1.0, 2.0, 5.0, 10.0))]),
    }
    er = pl.read_parquet(CACHE / "equal_ratings.parquet")
    rats["prior"] = er.filter(c("week") == 1).select("season", "team", "o", "d").join(er.select("season", "week", "team"), on=["season", "team"])
    for k, r in rats.items():
        r.write_parquet(CACHE / f"ratings_measure_{k}.parquet")
    names = list(rats)
    feats = ["own"] + [f"own_{n}" for n in names] + ["opp"] + [f"opp_{n}" for n in names] + ["home"]
    say("Gate picks (2007-2015 squared error, stack leave-one-season-out against the EPA rating alone):")
    gated = {}
    for h in ("next3", "rest"):
        st, _ = S.stack_score(C.predict_frame(r_epa, ufs[h], rats), feats, True)
        j = st.select(*K, "y", "pred", "pred_cv").join(ref[h].select(*K, pred_ref="pred"), on=K)
        parts = []
        for side in ("off", "def"):
            for lo, hi in S.BUCKETS:
                x = j.filter((c("side") == side) & c("w").is_between(lo, hi))
                t = x.filter(c("season").is_in(C.TUNE))
                e_st = float(((t["y"] - t["pred_cv"]) ** 2).mean())
                e_ref = float(((t["y"] - t["pred_ref"]) ** 2).mean())
                use = e_st < e_ref
                say(f"  {h:5s} {side} weeks {lo}-{hi if hi < 99 else '+'}: stack {e_st:.6f} vs EPA alone {e_ref:.6f} -> {'stack' if use else 'EPA alone'}")
                parts.append(x.with_columns(pred=c("pred") if use else c("pred_ref")))
        gated[h] = pl.concat(parts)
    say("")
    say("The hard gate on 2016-2024, against the EPA rating alone (F8's combination), then against all plays equal:")
    for h in ("next3", "rest"):
        g = gated[h]
        say(f"  {h:5s} {C.fmt(C.skill(g, ref[h]))} | weeks 1-4 {C.fmt(C.skill(g.filter(c('w') <= 4), ref[h]))} | off {C.fmt(C.skill(g, ref[h], side='off'))} def {C.fmt(C.skill(g, ref[h], side='def'))} | 2020-24 {C.fmt(C.skill(g, ref[h], seasons=list(range(2020, 2025))))} | vs all plays {C.fmt(C.skill(g, eq[h]))}")
    say("")
    say("Versions tried in this step: 1 (the gate's choices are made on 2007-2015)")
    (HERE / "r2_gate.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
