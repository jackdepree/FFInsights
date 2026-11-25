"""Availability: the CEO's spot-check of R8, the team gain beside Elo (REVIEW.md section 2, bets
S1-S7 written before this ran).

Rebuilds team_run.py's inputs exactly (the snap-weighted games-lost forecast from rest_chain's
saved walk-forward history, per game left, offense and defense; I60's starters' forecast), then:
S1 what a column's weekly average alone adds beside Elo (what a copy shuffled within the week
keeps); S2/S3 the real columns beside Elo (and I60's starters) plus those weekly averages; S4 the
forecast split by who is missing (QB, RB/WR/TE, line, defense); S5 offense and defense apart;
S6 per season and the overlap with I60's starters; S7 the leak audit's numbers.

Run from pcf/: <venv python> projects/availability/build/spot_r8_run.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.baselines.crude import inputs as I
from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.availability import checks as K
from pcf.experts.availability.common import INPUTS, schedule, timeline
from pcf.experts.availability.measures import agl_forecast, weights

c = pl.col
OUT = Path(__file__).with_name("spot_r8.txt")
COPIES = 19
lines: list[str] = []


def log(*parts) -> None:
    s = " ".join(str(p) for p in parts)
    print(s, flush=True)
    lines.append(s)


gw = Gateway()
inputs = {k: v for k, v in INPUTS.items() if not k.startswith("participation")}
view = gw.view(END_OF_TIME, "in_season", inputs)
sched = schedule(view, range(2013, 2025))
tl = timeline(view, 2024, sched)
w = weights(tl)
hist = pl.read_parquet(K.cache_dir() / "hist_rest_chain.parquet")
left = sched.select("game_id", "team", "season", "week", "gi", "n_games")


def rate(wsub: pl.DataFrame, name: str, side: str) -> pl.DataFrame:
    fc = agl_forecast(hist, wsub).filter(c("side") == side).join(left, on=["game_id", "team"])
    return fc.select("game_id", "team", (c("agl_hat") / (c("n_games") - c("gi")).clip(1)).alias(name))


GROUPS = {"qb": ["QB"], "sk": ["RB", "WR", "TE"], "ol": ["OL"]}
fc = rate(w, "agl_off_hat", "off").join(rate(w, "agl_def_hat", "def"), on=["game_id", "team"], how="full", coalesce=True)
for g, pos in GROUPS.items():
    fc = fc.join(rate(w.filter(c("position").is_in(pos)), f"agl_{g}", "off"), on=["game_id", "team"], how="left")
made = hist.group_by("game_id").agg(h_as_of=c("as_of").max())
fc = fc.join(made, on="game_id", how="left")
a = pl.read_parquet(K.cache_dir() / "agl.parquet").pivot(on="side", index=["game_id", "team", "season", "week"], values="agl")
a = a.sort("team", "season", "week").with_columns(
    agl_off_s=((c("off").cum_sum() - c("off")) / pl.int_range(pl.len())).over("team", "season"),
    agl_def_s=((c("def").cum_sum() - c("def")) / pl.int_range(pl.len())).over("team", "season"),
).select("game_id", "team", "agl_off_s", "agl_def_s")

board = Y.load_board("team", "rest")
f = board.features.filter(c("step_season") >= 2017)
keys = board.keys
j = f.select(*keys, "as_of").join(fc, on=["game_id", "team"], how="left")
late = j.filter(c("h_as_of") > c("as_of")).height
j = j.filter(c("h_as_of").is_null() | (c("h_as_of") <= c("as_of"))).join(a, on=["game_id", "team"], how="left")
tav = I.team_availability(f.select(*keys, "season", "week", "as_of"))
AGL = ["agl_off_hat", "agl_def_hat", "agl_qb", "agl_sk", "agl_ol", "agl_off_s", "agl_def_s"]
f = f.join(j.select(*keys, *AGL), on=keys, how="left").join(tav, on=["game_id", "team"], how="left")
cols = [*AGL, "tav_qb", "tav_skill"]
nulls = {x: f.filter(~c(x).is_finite() | c(x).is_null()).height for x in cols}
f = f.with_columns(pl.when(c(x).is_finite()).then(c(x)).alias(x) for x in cols).with_columns(c(x).fill_null(c(x).median()) for x in cols)
# what a copy shuffled within the week keeps: each column's average that week
WM = {x: f"wm_{x}" for x in AGL}
f = f.with_columns(c(x).mean().over("step").alias(WM[x]) for x in AGL)

log("SPOT-CHECK R8: the snap-weighted games-lost forecast (rest_chain) on the team rest-of-season board, team yards per game, scored 2019-2024 (trained from 2017)")
log(f"  rows {f.height}; scored rows are the board's 2019-2024 test weeks. Forecasts made after the board's moment, dropped: {late}")
log("  missing or non-finite values filled with the column's median (all seasons): " + ", ".join(f"{k} {v}" for k, v in nulls.items()))

cache: dict = {}


def fc_with(extra: list[str], feats=None) -> pl.DataFrame:
    key = tuple(extra)
    if feats is None and key in cache:
        return cache[key]
    out = board.forecast(("elo",), extra=extra, feats=f if feats is None else feats)
    if feats is None:
        cache[key] = out
    return out


def trial(label: str, base_extra: list[str], new: list[str], copies: bool = True) -> Y.Gain:
    base = fc_with(base_extra)
    g = Y.gain(fc_with([*base_extra, *new]), base, keys)
    txt = f"{100 * g.share:+.2f}% ({100 * g.lo:+.2f} to {100 * g.hi:+.2f}); range score {100 * g.range_share:+.2f}% ({100 * g.range_lo:+.2f} to {100 * g.range_hi:+.2f})"
    if copies:
        null = []
        for k in range(1, COPIES + 1):
            sh = Y.shuffle_within_weeks(f, new, seed=get_config().seed + 1000 + k)
            null.append(Y.gain(fc_with([*base_extra, *new], feats=sh), base, keys).share)
        null = np.array(null)
        txt += f"; copies mean {100 * null.mean():+.2f}%, max {100 * null.max():+.2f}%; counts: {g.lo > 0 and g.share > null.max()}"
    log(f"  {label:<70} {txt}")
    return g


E, S, W = [], ["tav_qb", "tav_skill"], [WM["agl_off_hat"], WM["agl_def_hat"]]
FC = ["agl_off_hat", "agl_def_hat"]
log("\nR8 as published (beside Elo; beside Elo + I60's starters)")
trial("beside Elo: forecast (off, def)", E, FC)
trial("beside Elo + I60's starters: forecast (off, def)", S, FC)

log("\nS1: what the copies keep, each column's weekly average, added alone")
trial("beside Elo: the weekly averages of the forecast (off, def)", E, W, copies=False)
trial("beside Elo + I60's starters: the weekly averages", S, W, copies=False)
trial("beside Elo: the week number (step_week) instead", E, ["step_week"], copies=False)

log("\nS2/S3: the real columns beside the weekly averages")
trial("beside Elo + weekly averages: forecast (off, def)", W, FC)
trial("beside Elo + I60's starters + weekly averages: forecast (off, def)", [*S, *W], FC)
trial("beside Elo + weekly averages: I60's starters (for scale)", W, S)

log("\nS4: who is missing (offense split: QB, RB/WR/TE, line), beside Elo + weekly averages")
WQ = [WM["agl_qb"], WM["agl_sk"], WM["agl_ol"], WM["agl_def_hat"]]
trial("beside Elo + weekly averages: QB part", WQ, ["agl_qb"])
trial("beside Elo + weekly averages: RB/WR/TE part", WQ, ["agl_sk"])
trial("beside Elo + weekly averages: line part", WQ, ["agl_ol"])
trial("beside Elo + weekly averages: all three offense parts", WQ, ["agl_qb", "agl_sk", "agl_ol"])
trial("beside Elo + I60's starters + weekly averages: line part", [*S, *WQ], ["agl_ol"])
trial("beside Elo + I60's starters + weekly averages: QB + RB/WR/TE parts", [*S, *WQ], ["agl_qb", "agl_sk"])

log("\nS5: offense and defense apart, beside Elo + weekly averages")
trial("offense's forecast only", W, ["agl_off_hat"])
trial("defense's forecast only", W, ["agl_def_hat"])

log("\nS6: per season (beside Elo + weekly averages: forecast (off, def)), and the overlap with I60's starters")
base = fc_with(W)
new = fc_with([*W, *FC])
for s_ in range(2019, 2025):
    rows = f.filter(c("season") == s_).select(keys)
    g = Y.gain(new, base, keys, rows=rows)
    log(f"  {s_}: {100 * g.share:+.2f}% ({100 * g.lo:+.2f} to {100 * g.hi:+.2f}), rows {g.rows}")
log("  the published comparisons by season, and without 2021:")
for label, base_extra, add in (("beside Elo: forecast (off, def)", E, FC), ("beside Elo + I60's starters: forecast (off, def)", S, FC),
                               ("beside Elo: QB part only", E, ["agl_qb"]), ("beside Elo + I60's starters: QB part only", S, ["agl_qb"])):
    base_, new_ = fc_with(base_extra), fc_with([*base_extra, *add])
    per_s = []
    for s_ in range(2019, 2025):
        g = Y.gain(new_, base_, keys, rows=f.filter(c("season") == s_).select(keys))
        per_s.append(f"{s_} {100 * g.share:+.1f}%")
    g = Y.gain(new_, base_, keys, rows=f.filter(c("season") != 2021).select(keys))
    log(f"    {label:<48} {', '.join(per_s)}; without 2021 {100 * g.share:+.2f}% ({100 * g.lo:+.2f} to {100 * g.hi:+.2f})")
log("  S8: 2021 by part of the season (the Reserve/COVID-19 list, code R59, held 601 players that year, most in December):")
for label, base_extra in (("beside Elo", E), ("beside Elo + I60's starters", S)):
    base_, new_ = fc_with(base_extra), fc_with([*base_extra, *FC])
    parts = []
    for lo_w, hi_w in ((1, 8), (9, 13), (14, 18)):
        rows = f.filter((c("season") == 2021) & c("week").is_between(lo_w, hi_w)).select(keys)
        g = Y.gain(new_, base_, keys, rows=rows)
        parts.append(f"weeks {lo_w}-{hi_w} {100 * g.share:+.1f}% ({g.rows} rows)")
    log(f"    {label:<30} {'; '.join(parts)}")
sc = f.filter(c("step_season") >= 2019)
for x, y_ in (("agl_off_hat", "tav_qb"), ("agl_off_hat", "tav_skill"), ("agl_qb", "tav_qb"), ("agl_sk", "tav_skill"), ("agl_ol", "tav_skill"), ("agl_off_hat", "agl_def_hat")):
    log(f"  correlation {x} with {y_}: {np.corrcoef(sc[x].to_numpy(), sc[y_].to_numpy())[0, 1]:+.2f}")
log(f"  the forecast's within-week share of its spread: offense {1 - sc.select((c('agl_off_hat') - c(WM['agl_off_hat'])).var()).item() / sc['agl_off_hat'].var():.2f} of the variance is between weeks")

log("\nS7: leak audit")
wk = tl.filter(c("season") == 2023).select("gsis_id", "season", "week").unique().height
log(f"  weights: this season's share uses only earlier games (cum_sum minus the game), else last season's, else the position's last season (measures.weights); timeline rows checked in 2023: {wk}")
log(f"  forecast moment: every player row's as_of is its game's Saturday run; team rows whose forecast was made after the board's as_of: {late}")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
