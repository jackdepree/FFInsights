"""team-efficiency, round three (2026-11-13), IDEAS I40 (the CEO's pick): a stronger pull for
teams that kept their QB and coach.

P3 (r2_prior_pull.py, built as the `change` rung) cuts the offense's pull after a new QB or a new
head coach: pull x (1 - a x new QB - b x new coach). In the build, teams with neither change lost
0.8% early in the rest-of-season forecast (team-efficiency R13). This adds a keep factor K for
teams with neither change:
    offense pull = 0.7 x (K if no change else 1 - a x new QB - b x new coach), capped at 1.
K, a and b are tuned together on 2007-2015 on the next-3-games error (round two's rule), with the
walk's other settings fixed at the champion's (half-life 16, strength 5, pull 0.7). Defense keeps
the plain pull. Scored on 2016-2024 against P3 (K = 1, a = b = 0.25) and the plain pull.
Writes r3_keep_pull.txt. PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r3_keep_pull.py
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
PRM = C.Params(16.0, 5.0, 0.7)
KEEP = (1.0, 1.1, 1.2, 1.3, 1.0 / 0.7)
SHRINK = (0.0, 0.25, 0.5)


def walk_keep(s, sched, qb, coach, k, a, b) -> pl.DataFrame:
    """common.walk with the offense's per-team pull: K for no change, else 1 - a x QB - b x coach."""
    g = sched.join(s, on=["game_id", "team"], how="inner").with_columns(
        aa=c("team").replace_strict(C.TIX), bb=c("opponent").replace_strict(C.TIX)
    )
    wscale = float(g["W"].mean())
    out = []
    po, pdf = np.zeros(C.NT), np.zeros(C.NT)
    fo, fd = None, None
    for season in C.SEASONS:
        if fo is not None:
            q, h = qb.get(season, np.zeros(C.NT)), coach.get(season, np.zeros(C.NT))
            f = np.where((q == 0) & (h == 0), k, 1 - a * q - b * h)
            po = PRM.pull * np.clip(f, 0, 1 / PRM.pull) * fo
            pdf = PRM.pull * fd
        gs = g.filter(c("season") == season)
        rows = gs.select("week", "aa", "bb", "home", "W", "WY").to_numpy().astype(float)
        last = int(gs["week"].max())
        for w in range(1, last + 1):
            o, d = C._fit(rows[rows[:, 0] < w], w, po, pdf, PRM, wscale)
            out.append(pl.DataFrame({"season": season, "week": w, "team": C.TEAMS, "o": o, "d": d}))
        o, d = C._fit(rows, last + 1, po, pdf, PRM, wscale)
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
    ch = R.changes()
    qb, coach = {}, {}
    for season in C.SEASONS:
        x = (
            pl.DataFrame({"team": C.TEAMS})
            .join(ch.filter(c("season") == season), on="team", how="left")
            .fill_null(0.0)
        )
        qb[season], coach[season] = x["qb_new"].to_numpy(), x["coach_new"].to_numpy()
    s = C.sides(p, "epa")
    say(
        "Offense error on 2007-2015 (mean squared error; lower is better), K = keep factor for no change, a = new QB cut, b = new coach cut:"
    )
    say(f"  {'K':>5s} {'a':>5s} {'b':>5s}  {'next 3':>8s}  {'rest':>8s}")
    res = {}
    for k, a, b in itertools.product(KEEP, SHRINK, SHRINK):
        r = walk_keep(s, sched, qb, coach, k, a, b)
        e = {}
        for h in ("next3", "rest"):
            pf = C.fit_score(C.predict_frame(r, ufs[h]), ["own", "opp", "home"]).filter(
                c("side") == "off"
            )
            e[h] = (C.mse(pf, C.TUNE), pf)
        res[(k, a, b)] = e
        say(f"  {k:5.2f} {a:5.2f} {b:5.2f}  {e['next3'][0]:8.5f}  {e['rest'][0]:8.5f}")
    best = min(res, key=lambda t: res[t]["next3"][0])
    best_rest = min(res, key=lambda t: res[t]["rest"][0])
    p3, plain = (1.0, 0.25, 0.25), (1.0, 0.0, 0.0)
    say("")
    say(
        f"Tuned on 2007-2015 ({len(res)} versions, {time.time() - t0:.0f}s): next 3 picks K={best[0]:.2f}, a={best[1]}, b={best[2]}; rest of season alone would pick K={best_rest[0]:.2f}, a={best_rest[1]}, b={best_rest[2]}"
    )
    flags = ch.select("season", "team", "qb_new", "coach_new")
    say("")
    say(
        "Offense, 2016-2024 (skill: 1 - squared error / the reference's; 90% interval by season-weeks):"
    )
    for nm, ref in (("vs P3", p3), ("vs the plain pull", plain)):
        for h in ("next3", "rest"):
            a_, r_ = res[best][h][1], res[ref][h][1]
            row = f"  {nm:18s} {h:5s} all {C.fmt(C.skill(a_, r_))} | weeks 1-4 {C.fmt(C.skill(a_.filter(c('w') <= 4), r_))} | 2020-24 {C.fmt(C.skill(a_, r_, seasons=list(range(2020, 2025))))}"
            say(row)
    say("")
    say("By flag, rest of season, weeks 1-4, against P3:")

    def tag(pf):
        return pf.join(flags, on=["season", "team"], how="left").with_columns(
            c("qb_new", "coach_new").fill_null(0.0)
        )

    groups = (
        ("neither", (c("qb_new") == 0) & (c("coach_new") == 0)),
        ("new QB", c("qb_new") == 1),
        ("new coach", c("coach_new") == 1),
    )
    a_, r_ = tag(res[best]["rest"][1]), res[p3]["rest"][1]
    for nm, f in groups:
        say(f"  {nm:10s} {C.fmt(C.skill(a_.filter(f & (c('w') <= 4)), r_))}")

    # R13 put the unchanged teams' loss in the forecast map (one slope for full and cut priors).
    # Second try: P3's ratings, with the map's slope on the own rating free to differ for teams
    # with neither change (own x neither; the flags are known from week 1, as P3's).
    say("")
    say(
        "Second try: P3's ratings with a separate map slope for unchanged teams (own x neither), offense:"
    )
    r = walk_keep(s, sched, qb, coach, *p3)
    for h in ("next3", "rest"):
        pf = tag(C.predict_frame(r, ufs[h])).with_columns(
            own_n=c("own") * ((c("qb_new") == 0) & (c("coach_new") == 0)).cast(pl.Float64)
        )
        m = C.fit_score(pf, ["own", "opp", "home", "own_n"]).filter(c("side") == "off")
        ref = res[p3][h][1]
        say(
            f"  {h:5s} tune 2007-15 error {C.mse(m, C.TUNE):.5f} (P3 {res[p3][h][0]:.5f}) | 2016-24 vs P3 all {C.fmt(C.skill(m, ref))} | weeks 1-4 {C.fmt(C.skill(m.filter(c('w') <= 4), ref))}"
        )
        for nm, f in groups:
            say(f"        {nm:10s} weeks 1-4 {C.fmt(C.skill(m.filter(f & (c('w') <= 4)), ref))}")
    (HERE / "r3_keep_pull.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
