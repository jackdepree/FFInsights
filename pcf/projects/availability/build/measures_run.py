"""Availability build: the measures' tests (BUILD.md A14, A15, A18; the brief's test 5a-b).

- Snap-weighted adjusted games lost (`measures.agl`): consistency (week to week and season to
  season, `pcf.validation.consistency`), and the same season's tally against the change in net
  EPA per play from the season before (the exploration's test, decision 0044).
- Proneness: named in-game injuries per scrimmage snap, its consistency.

Run from pcf/: <venv python> projects/availability/build/measures_run.py
Writes projects/availability/build/measures.txt and the team-game tally to the build cache.
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.availability import checks as K
from pcf.experts.availability.common import INPUTS, schedule, timeline
from pcf.experts.availability.measures import agl
from pcf.validation.consistency import consistency

c = pl.col
OUT = Path(__file__).with_name("measures.txt")
RNG = np.random.default_rng(get_config().seed)
lines: list[str] = []


def log(*parts) -> None:
    s = " ".join(str(p) for p in parts)
    print(s, flush=True)
    lines.append(s)


def r_ci(u, v) -> str:
    u, v = np.asarray(u, float), np.asarray(v, float)
    ok = ~(np.isnan(u) | np.isnan(v))
    u, v = u[ok], v[ok]
    r = np.corrcoef(u, v)[0, 1]
    bs = [np.corrcoef(u[i], v[i])[0, 1] for i in (RNG.integers(0, len(u), len(u)) for _ in range(2000))]
    lo, hi = np.percentile(bs, [5, 95])
    return f"{r:+.3f} ({lo:+.3f} to {hi:+.3f}, n {len(u)})"


gw = Gateway()
inputs = {k: v for k, v in INPUTS.items() if not k.startswith("participation")}
view = gw.view(END_OF_TIME, "in_season", {**inputs, "team_game": ("schedule", "pace")})
sched = schedule(view, range(2013, 2025))
tl = timeline(view, 2024, sched)
a = agl(tl)
a.write_parquet(K.cache_dir() / "agl.parquet")

wide = a.pivot(on="side", index=["game_id", "team", "season", "week"], values=["agl", "starters_out"])
wide = wide.with_columns(pl.selectors.starts_with("agl_", "starters_out_").fill_null(0.0))
wide = wide.with_columns(agl_total=c("agl_off") + c("agl_def"))
log("Snap-weighted adjusted games lost (AGL), per team-game, 2016-2024")
log(f"  team-games {wide.height}; per game: offense {wide['agl_off'].mean():.2f}, defense {wide['agl_def'].mean():.2f}, total {wide['agl_total'].mean():.2f} (SD {wide['agl_total'].std():.2f})")
season = wide.group_by("team", "season").agg(c("agl_off", "agl_def", "agl_total", "starters_out_off", "starters_out_def").sum())
season = season.with_columns(starters_out=c("starters_out_off") + c("starters_out_def"))
log(f"  per team-season: total {season['agl_total'].mean():.1f} (SD {season['agl_total'].std():.1f}, {season['agl_total'].min():.1f} to {season['agl_total'].max():.1f})")
top = season.sort("agl_total", descending=True).head(6)
log("  the most: " + ", ".join(f"{r['team']} {r['season']} ({r['agl_total']:.1f})" for r in top.iter_rows(named=True)))
bot = season.sort("agl_total").head(4)
log("  the least: " + ", ".join(f"{r['team']} {r['season']} ({r['agl_total']:.1f})" for r in bot.iter_rows(named=True)))

log("\nA14, consistency (pcf.validation.consistency: odd against even weeks, and season to season)")
cons = consistency(wide, ["agl_total", "agl_off", "agl_def", "starters_out_off", "starters_out_def"], unit="team")
with pl.Config(tbl_cols=-1, tbl_width_chars=200, tbl_rows=20):
    log(str(cons))
prev = season.select("team", season=c("season") + 1, p_total=c("agl_total"), p_off=c("agl_off"), p_def=c("agl_def"))
s2 = season.join(prev, on=["team", "season"])
log(f"  season to season, bootstrap over team-seasons: total {r_ci(s2['p_total'], s2['agl_total'])}; offense {r_ci(s2['p_off'], s2['agl_off'])}; defense {r_ci(s2['p_def'], s2['agl_def'])}")

log("\nA15, the same season's tally against the change in net EPA per play from the season before")
tg = view.table("team_game", seasons=list(range(2015, 2025))).filter(c("game_type") == "REG")
tg = tg.select("team", "season", "plays", "epa_per_play", "def_plays", "def_epa_per_play").drop_nulls()
net = tg.group_by("team", "season").agg(
    off=(c("epa_per_play") * c("plays")).sum() / c("plays").sum(),
    dfn=(c("def_epa_per_play") * c("def_plays")).sum() / c("def_plays").sum(),
).with_columns(net=c("off") - c("dfn"))
netp = net.select("team", season=c("season") + 1, off_p="off", dfn_p="dfn", net_p="net")
e = season.join(net, on=["team", "season"]).join(netp, on=["team", "season"]).with_columns(
    dnet=c("net") - c("net_p"), doff=c("off") - c("off_p"), ddef=c("dfn") - c("dfn_p"))
log(f"  total AGL vs change in net EPA/play:         {r_ci(e['agl_total'], e['dnet'])}")
log(f"  offense AGL vs change in offense EPA/play:   {r_ci(e['agl_off'], e['doff'])}")
log(f"  defense AGL vs change in EPA allowed/play:   {r_ci(e['agl_def'], e['ddef'])}")
log(f"  plain starters' count (weight 0.5+) vs change in net EPA/play: {r_ci(e['starters_out'], e['dnet'])}")
b = np.polyfit(e["agl_total"].to_numpy(), e["dnet"].to_numpy(), 1)[0]
log(f"  slope: each 10 snap-weighted games lost moves net EPA per play by {10 * b:+.4f} (SD of net EPA/play {e['net'].std():.3f})")
ep = e.join(prev, on=["team", "season"])
log(f"  last season's tally vs this season's change (the forecasting use): {r_ci(ep['p_total'], ep['dnet'])}")

log("\nA18, proneness: named in-game injuries per 100 scrimmage snaps, games with 10+ snaps")
pr = tl.filter((c("snaps") >= 10) & (c("season") >= 2013)).with_columns(
    named_100=100 * c("named").cast(pl.Float64) / c("snaps"))
cons_p = consistency(pr, ["named_100"], unit="gsis_id")
with pl.Config(tbl_cols=-1, tbl_width_chars=200):
    log(str(cons_p))
ps = pr.group_by("gsis_id", "season", "position").agg(n=c("named").sum(), snaps=c("snaps").sum()).filter(c("snaps") >= 300)
ps = ps.with_columns(rate=1000 * c("n") / c("snaps"))
psp = ps.select("gsis_id", season=c("season") + 1, rate_p="rate")
pj = ps.join(psp, on=["gsis_id", "season"])
log(f"  player-seasons with 300+ snaps, per 1,000 snaps, season to season: {r_ci(pj['rate_p'], pj['rate'])}")
for g in ("RB", "WR", "TE", "QB"):
    x = pj.filter(c("position") == g)
    log(f"    {g}: {r_ci(x['rate_p'], x['rate'])}")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
