"""team-efficiency exploration, step 6: the checks around the main test.

1. **Consistency** (CLAUDE.md's second test for every new measure, `pcf.validation.consistency`):
   each per-game measure, raw and opponent-adjusted (less what the opponent allows or gains in its
   other games that season), for offenses and defenses, 2006-2024.
2. **Is "all plays" winning only because the target counts all plays?** The main test again, with
   the future counted on the usual rule's plays only (garbage time left out of the target too).
3. **The side targets** (the CEO's 1d): the next game's points scored and allowed, dropbacks and
   runs, each relative to the league that week, predicted from each variant's ratings plus the
   opponent's, against the league average and against the bar.

Reads the ratings the earlier steps cached. Writes checks.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/checks.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

from pcf.validation.consistency import consistency  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"
PTS = {"Touchdown": 7.0, "Field goal": 3.0}


def per_game(p: pl.DataFrame, w: pl.DataFrame) -> pl.DataFrame:
    """Per game and offense: every measure."""
    q = p.join(w, on=["game_id", "play_id"], how="left")
    plays = q.group_by("game_id", "posteam").agg(
        epa_play=c("epa").mean(),
        epa_usual=c("epa").filter(c("usual")).mean(),
        epa_weighted_off=(c("w_off") * c("y_rel")).mean(),
        epa_weighted_def=(c("w_def") * c("y_rel")).mean(),
        wpa_play=c("wpa").mean(),
        epa_pass=c("epa").filter(c("is_pass") == 1).mean(),
        epa_run=c("epa").filter(c("is_pass") == 0).mean(),
        success=c("success").mean(),
    )
    ser = p.group_by("game_id", "posteam", "series_key").agg(e=c("epa").sum(), wp=c("wpa").sum(), s=c("series_success").first()).group_by("game_id", "posteam").agg(epa_series=c("e").mean(), wpa_series=c("wp").mean(), series_success=c("s").mean())
    drv = p.group_by("game_id", "posteam", "drive_key").agg(pts=c("fixed_drive_result").first().replace_strict(PTS, default=0.0)).group_by("game_id", "posteam").agg(points_drive=c("pts").mean())
    return plays.join(ser, on=["game_id", "posteam"]).join(drv, on=["game_id", "posteam"]).rename({"posteam": "team"})


def adjusted(g: pl.DataFrame, sched: pl.DataFrame, cols: list[str]) -> dict[str, pl.DataFrame]:
    """Offense rows (a team's value as the offense) and defense rows (the value its opponents'
    offenses got against it), raw and opponent-adjusted: less the opponent's mean in its *other*
    games that season (this game left out), plus the league's season mean."""
    x = sched.join(g, on=["game_id", "team"])
    off = x.select("game_id", "season", "week", "team", "opponent", *cols)
    dfn = x.select("game_id", "season", "week", c("opponent").alias("team"), c("team").alias("opponent"), *cols)
    out = {}
    for side, own, other in (("off", off, dfn), ("def", dfn, off)):
        oth = other.group_by("season", "team").agg(*[c(k).sum().alias(f"{k}_s") for k in cols], n=pl.len())
        lg = own.group_by("season").agg(*[c(k).mean().alias(f"{k}_lg") for k in cols])
        o = own.join(oth.rename({"team": "opponent"}), on=["season", "opponent"], how="left").join(lg, on="season")
        o = o.with_columns(*[(c(k) - ((c(f"{k}_s") - c(k)) / (c("n") - 1) - c(f"{k}_lg"))).alias(f"{k}_adj") for k in cols])
        out[side] = o
    return out


def main() -> None:
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    p = C.plays()
    sched = C.schedule()
    w = pl.read_parquet(CACHE / "weights_h44a.parquet").select("game_id", "play_id", "w_off", "w_def")

    # 1. Consistency
    cols = ["epa_play", "epa_usual", "epa_weighted_off", "epa_weighted_def", "wpa_play", "epa_pass", "epa_run", "success", "epa_series", "wpa_series", "series_success", "points_drive"]
    g = per_game(p, w)
    sides = adjusted(g, sched, cols)
    say("1. Consistency, 2006-2024 regular season (week to week: odd against even weeks; season to season), per team")
    for side, rows in sides.items():
        meas = [k for k in cols if not (side == "off" and k == "epa_weighted_def") and not (side == "def" and k == "epa_weighted_off")]
        t = consistency(rows, [*meas, *[f"{k}_adj" for k in meas]])
        say(f"  {'offense' if side == 'off' else 'defense'}:")
        for r in t.iter_rows(named=True):
            say(f"    {r['measure']:24s} week {r['week_r']:.2f} ({r['week_lo']:.2f}-{r['week_hi']:.2f})  season {r['season_r']:.2f} ({r['season_lo']:.2f}-{r['season_hi']:.2f})  {r['verdict']}")

    # 2. The target without garbage time
    say("")
    say("2. The main test with the future counted on the usual rule's plays only (2016-2024):")
    ufs_ng = {h: C.unit_frame(C.team_games(p.filter(c("usual")), sched), h) for h in ("next3", "rest")}
    rat = {
        "bar (usual rule)": pl.read_parquet(CACHE / "bar_ratings.parquet"),
        "all plays, equal": pl.read_parquet(CACHE / "equal_ratings.parquet"),
        "H41+H44a weights": pl.read_parquet(CACHE / "ratings_h44a.parquet"),
    }
    for name in ("ratings_dml_state", "ratings_dml_nostate"):
        if (CACHE / f"{name}.parquet").exists():
            rat[name.replace("ratings_", "").replace("_", ", ")] = pl.read_parquet(CACHE / f"{name}.parquet")
    sc = {k: C.score_ratings(r, ufs_ng) for k, r in rat.items()}
    for h in ("next3", "rest"):
        for k, v in sc.items():
            if k != "bar (usual rule)":
                say(f"  {h:5s} {k:20s} against the bar {C.fmt(C.skill(v[h], sc['bar (usual rule)'][h]))}")

    # 3. Side targets: next game
    say("")
    say("3. The side targets, next game (2016-2024): skill against the league average, then against the bar")
    res = C.results()
    pg = p.group_by("game_id", "posteam").agg(dropbacks=c("is_pass").sum().cast(pl.Float64), runs=(1 - c("is_pass")).sum().cast(pl.Float64)).rename({"posteam": "team"})
    base = sched.join(res, on=["game_id", "team"]).join(pg, on=["game_id", "team"])
    for tgt, col in (("points scored (offense) / allowed (defense)", "points_for"), ("dropbacks (offense) / faced (defense)", "dropbacks"), ("runs (offense) / faced (defense)", "runs")):
        tgf = base.with_columns(v=c(col).cast(pl.Float64))
        lgm = tgf.group_by("season", "week").agg(lv=c("v").mean())
        tgf = tgf.join(lgm, on=["season", "week"]).with_columns(ysum=c("v") - c("lv"), n=pl.lit(1, pl.UInt32))
        uf = {"next1": C.unit_frame(tgf, "next1")}
        sc = {k: C.score_ratings(r, uf)["next1"] for k, r in rat.items()}
        z = C.zero_pred(sc["bar (usual rule)"])
        say(f"  {tgt}:")
        for k, v in sc.items():
            say(f"    {k:20s} vs league average {C.fmt(C.skill(v, z))}; vs bar {C.fmt(C.skill(v, sc['bar (usual rule)']))}")
    (HERE / "checks.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
