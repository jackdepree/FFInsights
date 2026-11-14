"""team-efficiency exploration, step 4: H40 (efficiency is EPA and WPA per series) and H43 (the
same model at several grains: plays, drives, quarters, game situations).

Measures, each turned into ratings by the same walk (settings tuned on 2007-2015):
- **per play:** EPA per play (the equal-weight reference).
- **H40:** EPA per series, WPA per series, series success rate (nflverse's `series_success`: the
  series made a first down or a touchdown).
- **H43, other grains with equal weights:** EPA per drive, points per drive (touchdown 7, field
  goal 3), EPA per quarter (a team's EPA summed per quarter).
- **H43, the representativeness weights at other grains:** every play takes the kind of its drive
  (the drive's starting win-chance band and half) or of its quarter (the quarter and the score at
  its start), weights learned and shrunk toward equal as in step 3.

Two targets: the main test (EPA per play over the next 3 games and the rest of the season), and,
for the series measures, the same future counted per series, so H40 is also judged in its own unit.
Then stacking: does each measure add to EPA per play when both go into the prediction?
Writes h40_h43.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/h40_h43.py
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
PTS = {"Touchdown": 7.0, "Field goal": 3.0}


def target_from_sides(s: pl.DataFrame, sched: pl.DataFrame) -> pl.DataFrame:
    """A team-games frame (ysum, n) for any measure: its value relative to the league that week."""
    g = sched.join(s, on=["game_id", "team"], how="inner")
    lg = g.group_by("season", "week").agg(lv=c("WY").sum() / c("W").sum())
    return g.join(lg, on=["season", "week"]).with_columns(ysum=c("WY") - c("W") * c("lv"), n=c("W"))


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
    eq = {h: pl.read_parquet(CACHE / f"equal_{h}.parquet") for h in ("next3", "rest")}
    eq_r = pl.read_parquet(CACHE / "equal_ratings.parquet")

    ser = p.group_by("game_id", "posteam", "series_key").agg(epa=c("epa").sum(), wpa=c("wpa").sum(), succ=c("series_success").first().cast(pl.Float64))
    drv = p.group_by("game_id", "posteam", "drive_key").agg(epa=c("epa").sum(), pts=c("fixed_drive_result").first().replace_strict(PTS, default=0.0))
    qtr = p.group_by("game_id", "posteam", "qtr").agg(epa=c("epa").sum())
    measures = {
        "H40 EPA per series": C.sides(ser, "epa"),
        "H40 WPA per series": C.sides(ser, "wpa"),
        "H40 series success rate": C.sides(ser, "succ"),
        "H43 EPA per drive": C.sides(drv, "epa"),
        "H43 points per drive": C.sides(drv, "pts"),
        "H43 EPA per quarter": C.sides(qtr, "epa"),
    }

    # H43: representativeness weights by the kind of drive or quarter a play is in.
    start = p.sort("game_id", "play_id")
    dk = start.group_by("drive_key").agg(wp0=c("wp").first(), half0=(c("qtr").first() > 2).cast(pl.Int8))
    qk = start.group_by("game_id", "posteam", "qtr").agg(sd0=c("score_differential").first())
    pk = p.join(dk, on="drive_key").join(qk, on=["game_id", "posteam", "qtr"])
    band = lambda x: pl.when(x < 0.1).then(pl.lit("<.10")).when(x < 0.25).then(pl.lit(".10-.25")).when(x < 0.4).then(pl.lit(".25-.40")).when(x < 0.6).then(pl.lit(".40-.60")).when(x < 0.75).then(pl.lit(".60-.75")).when(x < 0.9).then(pl.lit(".75-.90")).otherwise(pl.lit(">.90"))  # noqa: E731
    sdb = pl.when(c("sd0") <= -15).then(pl.lit("down15+")).when(c("sd0") <= -8).then(pl.lit("down8-14")).when(c("sd0") < 0).then(pl.lit("down1-7")).when(c("sd0") == 0).then(pl.lit("tied")).when(c("sd0") < 8).then(pl.lit("up1-7")).when(c("sd0") < 15).then(pl.lit("up8-14")).otherwise(pl.lit("up15+"))
    kinds = {
        "H43 weights by kind of drive": pk.with_columns(kind=pl.concat_str(pl.lit("drive wp0 "), band(c("wp0")), pl.lit(" half"), c("half0").cast(pl.Utf8))),
        "H43 weights by kind of quarter": pk.with_columns(kind=pl.concat_str(pl.lit("q"), c("qtr").clip(1, 5).cast(pl.Utf8), pl.lit(" "), sdb)),
    }
    results = {}
    for name, s in measures.items():
        prm, out = C.tune(s, sched, ufs)
        results[name] = out
        say(f"{name}: settings {prm} ({time.time() - t0:.0f}s)")
    for name, q in kinds.items():
        wo, lo, cvo = C.class_weights_shrunk(q, "off")
        wd, ld, cvd = C.class_weights_shrunk(q, "def")
        mo = float((wo["beta"] * wo["share"]).sum())
        md = float((wd["beta"] * wd["share"]).sum())
        say(f"{name}: shrinkage offense {lo} (CV {100 * (cvo[lo] / cvo[1e4] - 1):+.2f}% against equal), defense {ld} ({100 * (cvd[ld] / cvd[1e4] - 1):+.2f}%)")
        tab = wo.select("kind", "share", off=c("beta") / mo).join(wd.select("kind", dfn=c("beta") / md), on="kind").sort("kind")
        say("   " + "; ".join(f"{r['kind']} ({r['share']:.0%}) {r['off']:.2f}/{r['dfn']:.2f}" for r in tab.iter_rows(named=True)))
        qq = q.join(wo.select("kind", w_off=c("beta").clip(0, None) / mo), on="kind").join(wd.select("kind", w_def=c("beta").clip(0, None) / md), on="kind")
        prm, r, out = C.tune_split(C.sides_sum(qq, "y_rel", "w_off"), C.sides_sum(qq, "y_rel", "w_def"), sched, ufs)
        results[name] = out | {"_ratings": r}
        say(f"   settings offense {prm[0]}, defense {prm[1]} ({time.time() - t0:.0f}s)")

    say("")
    say("The main test (EPA per play, all plays), 2016-2024, skill against EPA per play (all plays equal):")
    for h in ("next3", "rest"):
        for k, v in results.items():
            say(f"  {h:5s} {k:32s} {C.fmt(C.skill(v[h], eq[h]))} | off {C.fmt(C.skill(v[h], eq[h], side='off'))} def {C.fmt(C.skill(v[h], eq[h], side='def'))}")

    say("")
    say("H40 in its own unit: the future counted per series (EPA per series over the horizon), 2016-2024:")
    tgs = target_from_sides(measures["H40 EPA per series"], sched)
    ufs_s = {h: C.unit_frame(tgs, h) for h in ("next3", "rest")}
    per_play_on_series = C.score_ratings(eq_r, ufs_s)
    per_series_on_series = C.score_ratings(results["H40 EPA per series"]["_ratings"], ufs_s)
    for h in ("next3", "rest"):
        say(f"  {h:5s} EPA per series against EPA per play, both predicting future EPA per series: {C.fmt(C.skill(per_series_on_series[h], per_play_on_series[h]))}")

    say("")
    say("Stacking: EPA per play plus each measure in the same prediction, against EPA per play alone (2016-2024):")
    for k, v in results.items():
        st = C.score_ratings(eq_r, ufs, extra={"x": v["_ratings"]}, feats=["own", "opp", "own_x", "opp_x", "home"])
        say(f"  {k:32s} next3 {C.fmt(C.skill(st['next3'], eq['next3']))}; rest {C.fmt(C.skill(st['rest'], eq['rest']))}")
    (HERE / "h40_h43.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
