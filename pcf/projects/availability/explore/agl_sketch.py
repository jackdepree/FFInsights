"""Availability exploration: a first version of Football Outsiders' adjusted games lost (the CEO's
direction, pre-registered in EXPLORATION.md). A description, not a bet.

Starters: per team-season, the 11 offensive and 11 defensive players with the most snaps in weeks
1-4 (a stand-in for FO's starters). A game is lost when a starter doesn't play and is listed Out
or Doubtful, or is on no team's active roster that week (reserve lists; a release also lands here,
a known flaw). 0.5 for a game he played while listed Questionable (FO's partial weight), reported
both ways. Its two tests: the season-to-season repeat, and how the season's tally tracks the
team's change in net EPA per play from the season before.

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.clean import standard

c = pl.col
CFG = get_config()
O = CFG.zone("interim") / "availability"
T = CFG.zone("tables")
RNG = np.random.default_rng(CFG.seed)

pg = pl.read_parquet(O / "player_games.parquet")
wk = pg.select("team", "season", "week", "gi").unique()
anyw = pg.group_by("gsis_id", "season", "week").agg(played=c("played").max(), rostered=pl.lit(1), status=c("report_status").first())
early = pg.filter(c("week") <= 4).group_by("gsis_id", "season", "team").agg(o=c("offense_snaps").sum(), d=c("defense_snaps").sum())
st = pl.concat([
    early.sort("o", descending=True).group_by("team", "season").head(11).select("gsis_id", "season", "team", side=pl.lit("offense")),
    early.sort("d", descending=True).group_by("team", "season").head(11).select("gsis_id", "season", "team", side=pl.lit("defense")),
]).unique(["gsis_id", "season", "team"])
x = st.join(wk, on=["team", "season"]).join(anyw, on=["gsis_id", "season", "week"], how="left").with_columns(
    c("played").fill_null(0), c("rostered").fill_null(0))
x = x.with_columns(
    lost=pl.when((c("played") == 0) & (c("status").is_in(["Out", "Doubtful"]) | (c("rostered") == 0))).then(1.0)
    .when((c("played") == 1) & (c("status") == "Questionable")).then(0.5).otherwise(0.0),
)
x = x.with_columns(lost_full=pl.when(c("lost") == 1.0).then(1.0).otherwise(0.0))
agl = x.group_by("team", "season").agg(agl=c("lost").sum(), agl_full=c("lost_full").sum(),
                                       agl_off=c("lost").filter(c("side") == "offense").sum(), agl_def=c("lost").filter(c("side") == "defense").sum())
print(f"team-seasons {agl.height}; starters' games lost per team-season: mean {agl['agl'].mean():.1f}, SD {agl['agl'].std():.1f}, range {agl['agl'].min():.0f} to {agl['agl'].max():.0f} (FO's published AGL runs roughly 20 to 140, with a fuller roster and real weights)")

# net EPA per play by team-season
cols = ["season", "season_type", "posteam", "defteam", "epa", "play_type"]
p = pl.concat([pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=cols) for s in range(2013, 2025)])
p = p.filter((c("season_type") == "REG") & c("play_type").is_in(["run", "pass"]) & c("epa").is_not_null())
p = standard.standard_teams(p, "posteam").pipe(standard.standard_teams, "defteam")
off = p.group_by("season", team=c("posteam")).agg(off=c("epa").mean())
de = p.group_by("season", team=c("defteam")).agg(dfn=c("epa").mean())
net = off.join(de, on=["season", "team"]).with_columns(net=c("off") - c("dfn"))
a = agl.join(net, on=["team", "season"])
prev = a.select("team", season=c("season") + 1, agl_prev=c("agl"), agl_full_prev=c("agl_full"), net_prev=c("net"), off_prev=c("off"), dfn_prev=c("dfn"),
                agl_off_prev=c("agl_off"), agl_def_prev=c("agl_def"))
a = a.join(prev, on=["team", "season"]).with_columns(dnet=c("net") - c("net_prev"), doff=c("off") - c("off_prev"), ddef=c("dfn") - c("dfn_prev"))


def r_ci(u, v):
    u, v = np.asarray(u, float), np.asarray(v, float)
    r = np.corrcoef(u, v)[0, 1]
    bs = []
    for _ in range(2000):
        i = RNG.integers(0, len(u), len(u))
        bs.append(np.corrcoef(u[i], v[i])[0, 1])
    lo, hi = np.percentile(bs, [5, 95])
    return f"{r:+.2f} ({lo:+.2f} to {hi:+.2f}, n {len(u)})"


print("\nConsistency: this season's tally against last season's (team-seasons 2014-2024)")
print("  with the Questionable half-games:", r_ci(a["agl_prev"], a["agl"]))
print("  full games only:                 ", r_ci(a["agl_full_prev"], a["agl_full"]))
print("  offense:", r_ci(a["agl_off_prev"], a["agl_off"]), " defense:", r_ci(a["agl_def_prev"], a["agl_def"]))
print("Does it help: the same season's tally against the change in net EPA per play from the season before")
print("  all starters vs change in net EPA/play:     ", r_ci(a["agl"], a["dnet"]))
print("  offense's tally vs change in offense EPA/play:", r_ci(a["agl_off"], a["doff"]))
print("  defense's tally vs change in EPA allowed/play:", r_ci(a["agl_def"], a["ddef"]))
b = np.polyfit(a["agl"].to_numpy(), a["dnet"].to_numpy(), 1)[0]
print(f"  slope: each 10 starter games lost moves net EPA per play by {10 * b:+.4f} (a team's net EPA per play has SD {a['net'].std():.3f})")
print("  last season's tally vs this season's change in net EPA/play (the forecasting use):", r_ci(a["agl_prev"], a["dnet"]))
a.select("team", "season", "agl", "agl_full", "agl_off", "agl_def").write_parquet(O / "agl_first_version.parquet")
top = a.sort("agl", descending=True).head(5).select("team", "season", "agl")
print("most games lost:", ", ".join(f"{t} {s} ({v:.0f})" for t, s, v in top.iter_rows()))
