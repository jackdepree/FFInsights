"""team-efficiency exploration, round two (2026-11-13), idea 4 continued: P3, a weaker pull after
a change, tuned on the forecast itself.

r2_prior.py's P2 learned (on 2007-2015) that a new starting QB cuts how much of last season's
offense carries over by about a third, and a new head coach by about a quarter. But it learned that
from a side model of season-final ratings, and the main test then didn't pick it on 2007-2015.
The direct version: keep the usual prior, but each team's pull is
    pull x (1 - a x new QB - b x new coach)   (offense; defense: pull x (1 - b x new coach)),
with a and b tuned together with the half-life, strength and pull on 2007-2015, on the main test's
own error, per side. Scored on 2016-2024 against the usual prior.
Writes r2_prior_pull.txt. PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r2_prior_pull.py
"""

# ruff: noqa: E501
from __future__ import annotations

import itertools
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402
import r2_prior as R  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"
SHRINK = (0.0, 0.25, 0.5, 0.75)


def walk_change(s: pl.DataFrame, prm: C.Params, sched: pl.DataFrame, qb: dict, coach: dict, a: float, b: float) -> pl.DataFrame:
    """common.walk with a per-team pull: pull x (1 - a x new QB - b x new coach) on offense,
    pull x (1 - b x new coach) on defense. qb/coach: season -> array over TEAMS (0/1)."""
    g = sched.join(s, on=["game_id", "team"], how="inner").with_columns(aa=c("team").replace_strict(C.TIX), bb=c("opponent").replace_strict(C.TIX))
    wscale = float(g["W"].mean())
    out = []
    po, pdf = np.zeros(C.NT), np.zeros(C.NT)
    fo, fd = None, None
    for season in C.SEASONS:
        if fo is not None:
            q, k = qb.get(season, np.zeros(C.NT)), coach.get(season, np.zeros(C.NT))
            po = prm.pull * np.clip(1 - a * q - b * k, 0, 1) * fo
            pdf = prm.pull * np.clip(1 - b * k, 0, 1) * fd
        gs = g.filter(c("season") == season)
        rows = gs.select("week", "aa", "bb", "home", "W", "WY").to_numpy().astype(float)
        last = int(gs["week"].max())
        for w in range(1, last + 1):
            o, d = C._fit(rows[rows[:, 0] < w], w, po, pdf, prm, wscale)
            out.append(pl.DataFrame({"season": season, "week": w, "team": C.TEAMS, "o": o, "d": d}))
        o, d = C._fit(rows, last + 1, po, pdf, prm, wscale)
        fo, fd = o - o.mean(), d - d.mean()
    return pl.concat(out)


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
    ch = R.changes()
    qb, coach = {}, {}
    for season in C.SEASONS:
        x = pl.DataFrame({"team": C.TEAMS}).join(ch.filter(c("season") == season), on="team", how="left").fill_null(0.0)
        qb[season] = x["qb_new"].to_numpy()
        coach[season] = x["coach_new"].to_numpy()
    s = C.sides(p, "epa")
    best = {"off": (np.inf, None, None), "def": (np.inf, None, None)}
    n = 0
    for prm in C.GRID:
        for a, b in itertools.product(SHRINK, SHRINK):
            n += 1
            r = walk_change(s, prm, sched, qb, coach, a, b)
            pf = C.fit_score(C.predict_frame(r, ufs["next3"]), ["own", "opp", "home"])
            for side in ("off", "def"):
                v = C.mse(pf.filter(c("side") == side), C.TUNE)
                if v < best[side][0]:
                    best[side] = (v, (prm, a, b), r)
    say(f"Tuned on 2007-2015 ({n} versions, {time.time() - t0:.0f}s): offense {best['off'][1]}; defense {best['def'][1]} (a = new QB, b = new coach)")
    r = C.combine(best["off"][2], best["def"][2])
    r.write_parquet(CACHE / "ratings_prior_pull.parquet")
    out = C.score_ratings(r, ufs)
    say("")
    say("P3 against the usual prior (all plays equal), 2016-2024:")
    for h in ("next3", "rest"):
        say(f"  {h:5s} all weeks {C.fmt(C.skill(out[h], eq[h]))} | weeks 1-4 {C.fmt(C.skill(out[h].filter(c('w') <= 4), eq[h]))} | weeks 5-9 {C.fmt(C.skill(out[h].filter(c('w').is_between(5, 9)), eq[h]))} | off {C.fmt(C.skill(out[h], eq[h], side='off'))} def {C.fmt(C.skill(out[h], eq[h], side='def'))} | 2020-24 {C.fmt(C.skill(out[h], eq[h], seasons=list(range(2020, 2025))))}")
    say("")
    say("Offense, by whether the team had a new QB that season (next 3 games, weeks 1-4), against the usual prior:")
    o = out["next3"].filter((c("side") == "off") & (c("w") <= 4)).join(ch.select("season", "team", "qb_new"), on=["season", "team"], how="left")
    e = eq["next3"].filter((c("side") == "off") & (c("w") <= 4))
    for nm, v in (("new QB", 1.0), ("same QB", 0.0)):
        say(f"  {nm:8s} {C.fmt(C.skill(o.filter(c('qb_new') == v), e))}")
    (HERE / "r2_prior_pull.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
