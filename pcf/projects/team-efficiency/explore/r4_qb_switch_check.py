"""team-efficiency round four check (2026-11-13): the weight cut on real mid-season QB changes,
against d = 0 (a = 0.5), 2007-2024. Writes r4_qb_switch_check.txt.
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r4_qb_switch_check.py
"""

# ruff: noqa: B905, E401, E402, E501, E702, F401, I001
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import warnings

warnings.filterwarnings("ignore")
import numpy as np, polars as pl
import common as C, r2_prior as R, r4_qb_switch as Q

c = pl.col
p = C.plays()
sched = C.schedule()
tg = C.team_games(p, sched)
ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
starters, cur = Q.qb_frames()
st = starters.join(sched, on=["game_id", "team"]).drop_nulls("starter")
mq = (
    st.group_by("season", "team", "starter")
    .agg(n=pl.len(), lw=c("week").max())
    .sort("n", "lw", descending=True)
    .group_by("season", "team", maintain_order=True)
    .first()
)
last_qb = {
    int(s) + 1: dict(zip(x["team"], x["starter"]))
    for (s,), x in mq.partition_by("season", as_dict=True).items()
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
lines = []


def say(t):
    print(t, flush=True)
    lines.append(t)


def score(r):
    return {
        h: C.fit_score(C.predict_frame(r, ufs[h]), ["own", "opp", "home"]).filter(
            c("side") == "off"
        )
        for h in ufs
    }


base = score(Q.walk_qb(s, sched, starters, cur, last_qb, coach, 0.0, 0.5))
# a real change: this week's QB started fewer than half the team's games so far this season, and at least 2 games were played
g = starters.join(sched, on=["game_id", "team"])
e = cur.join(g.select("season", "team", "week", "starter"), on=["season", "team"]).filter(
    c("week") < c("w")
)
sw = e.group_by("season", "w", "team").agg(share=(c("starter") == c("qb")).mean(), n=pl.len())
for d in (0.25, 0.5, 1.0):
    m = score(Q.walk_qb(s, sched, starters, cur, last_qb, coach, d, 0.5))
    for h in ufs:
        mt = m[h].join(sw, on=["season", "w", "team"], how="left")
        real = mt.filter((c("share") < 0.5) & (c("n") >= 2))
        newqb = mt.filter((c("share") == 0) & (c("n") >= 2))
        say(
            f"d={d} {h}: all {C.fmt(C.skill(m[h], base[h], seasons=C.SEASONS[1:]))} | QB started <half so far ({real.filter(c('season') >= 2007).height} rows) {C.fmt(C.skill(real, base[h], seasons=C.SEASONS[1:]))} | QB started none ({newqb.filter(c('season') >= 2007).height}) {C.fmt(C.skill(newqb, base[h], seasons=C.SEASONS[1:]))}"
        )
Path(__file__).with_suffix(".txt").write_text("\n".join(lines), encoding="utf-8")
