"""team-efficiency, round four (2026-11-13), IDEAS I37 (the CEO's go): mid-season QB changes.

P3 cuts the offense's pull when the season opens with a new QB. Mid-season, a team's QB changes
too (injury, benching), and the games its old QB started say less about the offense now.

**This week's QB** (known at the Saturday run): last game's starter (`team_game.pregame.qb_id`),
unless the week's injury report lists him Out or Doubtful (`player_game.injury`, from 2009), then
the top QB on the week's depth chart not so listed. In week 1, the top healthy depth-chart QB.
It names the actual starter 92.5% of the time, 2009-2024 (last starter alone 90.4%, depth chart
QB1 89.9%; scratchpad check).

**Two changes to the offense walk**, on top of P3's coach cut (b = 0.25):
- a game started by another QB counts (1 - d) as much in this week's fit;
- the prior is cut by a when this week's QB isn't last season's most-started QB (P3's QB flag,
  updated every week instead of fixed at week 1).
d and a are tuned on 2007-2015 on the next-3-games error (rounds two and three's rule); the walk's
other settings are the champion's. Scored on 2016-2024 against P3 (d = 0, week-1 flag, a = 0.25).
Writes r4_qb_switch.txt. PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r4_qb_switch.py
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

from pcf.data.clean import standard  # noqa: E402
from pcf.data.tables.store import read_part  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
PRM = C.Params(16.0, 5.0, 0.7)
DROP = (0.0, 0.25, 0.5, 0.75, 1.0)
CUT = (0.0, 0.25, 0.5)
B = 0.25  # P3's coach cut


def qb_frames() -> tuple[pl.DataFrame, pl.DataFrame]:
    """starters: game_id, team, starter. current: season, w, team, qb (this week's QB, by the rule)."""
    s = C.SEASONS
    ros = standard.standard_teams(
        read_part("player_game", "roster", seasons=s)
        .select("gsis_id", "game_id", "team")
        .collect(),
        "team",
    )
    dep = (
        read_part("player_game", "depth", seasons=s)
        .filter(c("depth_position") == "QB")
        .collect()
        .join(ros, on=["gsis_id", "game_id"])
    )
    inj = (
        read_part("player_game", "injury", seasons=s)
        .select("gsis_id", "game_id", "report_status")
        .collect()
        .join(ros, on=["gsis_id", "game_id"])
    )
    out = (
        inj.filter(c("report_status").is_in(["Out", "Doubtful"]))
        .select("game_id", "team", "gsis_id", out=pl.lit(True))
        .unique()
    )
    healthy = (
        dep.join(out, on=["game_id", "team", "gsis_id"], how="left").filter(c("out").is_null())
        .sort("depth", "depth_mean", "gsis_id").group_by("game_id", "team").first().select("game_id", "team", healthy1="gsis_id")
    )  # fmt: skip
    pre = standard.standard_teams(
        read_part("team_game", "pregame", seasons=s).select("game_id", "team", "qb_id").collect(),
        "team",
    )
    sched = C.schedule()
    g = sched.join(pre, on=["game_id", "team"], how="left").sort("team", "season", "week")
    g = g.with_columns(prev=c("qb_id").shift(1).over("team", "season"))
    g = g.join(healthy, on=["game_id", "team"], how="left").join(
        out.rename({"gsis_id": "prev", "out": "prev_out"}),
        on=["game_id", "team", "prev"],
        how="left",
    )
    g = g.with_columns(
        qb=pl.when(c("prev").is_null() | c("prev_out").fill_null(False))
        .then(pl.coalesce("healthy1", "prev"))
        .otherwise(c("prev"))
    )
    starters = g.select("game_id", "team", starter="qb_id")
    # every moment w of the season, for every team: its game's rule, or (bye) its last starter
    weeks = sched.group_by("season").agg(last=c("week").max())
    moments = (
        weeks.with_columns(w=pl.int_ranges(1, c("last") + 1)).explode("w").select("season", "w")
    )
    teams = sched.select("season", "team").unique()
    grid = moments.join(teams, on="season")
    at = g.select("season", w="week", team="team", qb_game="qb")
    started = g.select("season", "team", "week", "qb_id").sort("week")
    cur = grid.join(at, on=["season", "w", "team"], how="left").sort("w")
    last_start = cur.join_asof(
        started.rename({"week": "w0"}).with_columns(w_key=c("w0") + 1).sort("w_key"),
        left_on="w", right_on="w_key", by=["season", "team"], strategy="backward",
    )  # fmt: skip
    cur = last_start.select("season", "w", "team", qb=pl.coalesce("qb_game", "qb_id"))
    return starters, cur


def walk_qb(s, sched, starters, cur, last_qb, coach, d, a, dynamic=True) -> pl.DataFrame:
    """Offense ratings with this week's QB: other QBs' games weighted (1 - d); prior cut a for a QB
    who isn't last season's main QB (`dynamic`: this week's QB; else week 1's, as P3)."""
    g = sched.join(s, on=["game_id", "team"], how="inner").join(
        starters, on=["game_id", "team"], how="left"
    )
    g = g.with_columns(aa=c("team").replace_strict(C.TIX), bb=c("opponent").replace_strict(C.TIX))
    wscale = float(g["W"].mean())
    out = []
    fo, fd = None, None
    for season in C.SEASONS:
        gs = g.filter(c("season") == season)
        last = int(gs["week"].max())
        cs = cur.filter(c("season") == season)
        q = {
            w: dict(zip(x["team"], x["qb"], strict=True))
            for (w,), x in cs.partition_by("w", as_dict=True).items()
        }
        lq = last_qb.get(season, {})
        k = coach.get(season, np.zeros(C.NT))
        rows = gs.select("week", "aa", "bb", "home", "W", "WY").to_numpy().astype(float)
        st = gs["starter"].to_list()
        tm = gs["team"].to_list()
        for w in range(1, last + 2):
            qw = q.get(min(w, last), {})
            q1 = q.get(1, {}) if not dynamic else qw
            if fo is not None:
                new = np.array(
                    [
                        1.0 if (t in lq and q1.get(t) is not None and q1.get(t) != lq[t]) else 0.0
                        for t in C.TEAMS
                    ]
                )
                po = PRM.pull * np.clip(1 - a * new - B * k, 0, 1) * fo
                pdf = PRM.pull * fd
            else:
                po, pdf = np.zeros(C.NT), np.zeros(C.NT)
            r = rows.copy()
            if d > 0:
                other = np.array(
                    [
                        (qw.get(t) is not None and x is not None and x != qw.get(t))
                        for t, x in zip(tm, st, strict=True)
                    ]
                )
                r[other, 4:6] *= 1 - d
            sel = r[:, 0] < w
            o, dd = C._fit(r[sel], w, po, pdf, PRM, wscale)
            if w <= last:
                out.append(
                    pl.DataFrame({"season": season, "week": w, "team": C.TEAMS, "o": o, "d": dd})
                )
            else:
                plain = C._fit(rows, last + 1, po, pdf, PRM, wscale)  # the final: every game counts
                fo, fd = plain[0] - plain[0].mean(), plain[1] - plain[1].mean()
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
    starters, cur = qb_frames()
    # last season's most-started QB per team (ties: the later start), keyed to the next season
    st = starters.join(sched, on=["game_id", "team"]).drop_nulls("starter")
    main_qb = (
        st.group_by("season", "team", "starter").agg(n=pl.len(), lw=c("week").max())
        .sort("n", "lw", descending=True).group_by("season", "team", maintain_order=True).first()
    )  # fmt: skip
    last_qb = {
        int(s) + 1: dict(zip(x["team"], x["starter"], strict=True))
        for (s,), x in main_qb.partition_by("season", as_dict=True).items()
    }
    ch = R.changes()
    coach = {}
    for season in C.SEASONS:
        x = (
            pl.DataFrame({"team": C.TEAMS})
            .join(ch.filter(c("season") == season), on="team", how="left")
            .fill_null(0.0)
        )
        coach[season] = x["coach_new"].to_numpy()
    s = C.sides(p, "epa")

    def score(r):
        return {
            h: C.fit_score(C.predict_frame(r, ufs[h]), ["own", "opp", "home"]).filter(
                c("side") == "off"
            )
            for h in ufs
        }

    p3 = score(  # P3 with this script's flags
        walk_qb(s, sched, starters, cur, last_qb, coach, 0.0, 0.25, dynamic=False)
    )
    say(
        "Offense error on 2007-2015 (mean squared error), d = weight cut for another QB's games, a = prior cut for a QB who isn't last season's:"
    )
    say(
        f"  P3 (week-1 flag, a = 0.25, d = 0): next 3 {C.mse(p3['next3'], C.TUNE):.5f}  rest {C.mse(p3['rest'], C.TUNE):.5f}"
    )
    res = {}
    for d, a in itertools.product(DROP, CUT):
        res[(d, a)] = score(walk_qb(s, sched, starters, cur, last_qb, coach, d, a))
        say(
            f"  d={d:4.2f} a={a:4.2f}: next 3 {C.mse(res[(d, a)]['next3'], C.TUNE):.5f}  rest {C.mse(res[(d, a)]['rest'], C.TUNE):.5f}"
        )
    best = min(res, key=lambda t: C.mse(res[t]["next3"], C.TUNE))
    say("")
    say(
        f"Tuned on 2007-2015 ({len(res)} versions, {time.time() - t0:.0f}s): d = {best[0]}, a = {best[1]}"
    )

    # team-weeks after a switch: this week's QB differs from a starter of an earlier game this season
    g = starters.join(sched, on=["game_id", "team"])
    earlier = cur.join(g.select("season", "team", "week", "starter"), on=["season", "team"]).filter(
        c("week") < c("w")
    )
    sw = earlier.group_by("season", "w", "team").agg(switched=(c("starter") != c("qb")).any())
    say("")
    say(
        "Offense, 2016-2024, against P3 (skill: 1 - squared error / P3's; 90% interval by season-weeks):"
    )
    for h in ("next3", "rest"):
        m, ref = res[best][h], p3[h]
        mt = m.join(sw, on=["season", "w", "team"], how="left").with_columns(
            c("switched").fill_null(False)
        )
        n_sw = mt.filter(c("season") >= 2016)["switched"].mean()
        say(
            f"  {h:5s} all {C.fmt(C.skill(m, ref))} | weeks 1-4 {C.fmt(C.skill(m.filter(c('w') <= 4), ref))} | 2020-24 {C.fmt(C.skill(m, ref, seasons=list(range(2020, 2025))))}"
        )
        say(
            f"        after a switch ({100 * n_sw:.0f}% of team-weeks) {C.fmt(C.skill(mt.filter(c('switched')), ref))} | no switch {C.fmt(C.skill(mt.filter(~c('switched')), ref))}"
        )
    say("")
    say("Each change alone, 2016-2024, against P3:")
    for nm, key in (
        ("weight cut only (a = 0.25, weekly flag)", (best[0], 0.25)),
        ("weekly flag only (d = 0)", (0.0, best[1])),
    ):
        if key in res:
            say(
                f"  {nm}: next 3 {C.fmt(C.skill(res[key]['next3'], p3['next3']))} | rest {C.fmt(C.skill(res[key]['rest'], p3['rest']))}"
            )
    (HERE / "r4_qb_switch.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
