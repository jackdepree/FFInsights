"""Availability build: the team output on the yardstick (BUILD.md A16; the brief's test 5c, I115's
test).

The forecast of snap-weighted games lost over the rest of the season, per team-game and side:
the sum over the team's roster and reserve rows of each player's expected games of health
absence (the rest-of-season champion's saved walk-forward history) times his weight going into
the game (`measures.weights`, earlier games only), per game left. Beside it, the tally to date
(this season's snap-weighted games lost per game before this one).

Scored on the team rest-of-season board (team yards), 2019-2024, beside Elo, and beside Elo with
I60's starters' games forecast (`tav_qb`, `tav_skill`) in the base, each against 19 copies
shuffled within each week. The board's training rows start in 2017 (availability's history).

Run from pcf/: <venv python> projects/availability/build/team_run.py <rest variant>
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

from pcf.baselines.crude import inputs as I
from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.availability import checks as K
from pcf.experts.availability.common import INPUTS, schedule, timeline
from pcf.experts.availability.measures import agl_forecast, weights

c = pl.col
REST = sys.argv[1] if len(sys.argv) > 1 else "rest_chain"
OUT = Path(__file__).with_name(f"team_{REST}.txt")
COPIES = 19
lines: list[str] = []


def log(*parts) -> None:
    s = " ".join(str(p) for p in parts)
    print(s, flush=True)
    lines.append(s)


def share(g) -> str:
    return f"{100 * g.share:+.2f}% ({100 * g.lo:+.2f} to {100 * g.hi:+.2f}); range score {100 * g.range_share:+.2f}% ({100 * g.range_lo:+.2f} to {100 * g.range_hi:+.2f})"


gw = Gateway()
inputs = {k: v for k, v in INPUTS.items() if not k.startswith("participation")}
view = gw.view(END_OF_TIME, "in_season", inputs)
sched = schedule(view, range(2013, 2025))
tl = timeline(view, 2024, sched)
w = weights(tl)
hist = pl.read_parquet(K.cache_dir() / f"hist_{REST}.parquet")
fc = agl_forecast(hist, w).join(sched.select("game_id", "team", "season", "week", "gi", "n_games"), on=["game_id", "team"])
fc = fc.with_columns(rate=c("agl_hat") / (c("n_games") - c("gi")).clip(1))
fc = fc.pivot(on="side", index=["game_id", "team", "season", "week"], values="rate").rename({"off": "agl_off_hat", "def": "agl_def_hat"})
made = hist.group_by("game_id").agg(h_as_of=c("as_of").max())
fc = fc.join(made, on="game_id", how="left")
# the tally to date: per game before this one, this season
a = pl.read_parquet(K.cache_dir() / "agl.parquet").pivot(on="side", index=["game_id", "team", "season", "week"], values="agl")
a = a.sort("team", "season", "week").with_columns(
    agl_off_s=((c("off").cum_sum() - c("off")) / pl.int_range(pl.len())).over("team", "season"),
    agl_def_s=((c("def").cum_sum() - c("def")) / pl.int_range(pl.len())).over("team", "season"),
).select("game_id", "team", "agl_off_s", "agl_def_s")

board = Y.load_board("team", "rest")
f = board.features.filter(c("step_season") >= 2017)
keys = board.keys
j = f.select(*keys, "as_of").join(fc.drop("season", "week"), on=["game_id", "team"], how="left")
j = j.filter(c("h_as_of").is_null() | (c("h_as_of") <= c("as_of"))).join(a, on=["game_id", "team"], how="left")
tav = I.team_availability(f.select(*keys, "season", "week", "as_of"))
f = f.join(j.select(*keys, "agl_off_hat", "agl_def_hat", "agl_off_s", "agl_def_s"), on=keys, how="left").join(tav, on=["game_id", "team"], how="left")
cols = ["agl_off_hat", "agl_def_hat", "agl_off_s", "agl_def_s", "tav_qb", "tav_skill"]
f = f.with_columns(pl.when(c(x).is_finite()).then(c(x)).alias(x) for x in cols).with_columns(c(x).fill_null(c(x).median()) for x in cols)
log(f"TEAM: the snap-weighted games-lost forecast ({REST}) on the team rest-of-season board (team yards), 2019-2024")
log(f"  rows with a forecast: {j.filter(c('agl_off_hat').is_not_null()).height} of {f.height}")
for base_name, base_extra in (("Elo", []), ("Elo + I60's starters' forecast", ["tav_qb", "tav_skill"])):
    base = board.forecast(("elo",), extra=base_extra, feats=f)
    for name, new in (("forecast (off, def)", ["agl_off_hat", "agl_def_hat"]), ("to date (off, def)", ["agl_off_s", "agl_def_s"]),
                      ("forecast + to date", ["agl_off_hat", "agl_def_hat", "agl_off_s", "agl_def_s"])):
        g = Y.gain(board.forecast(("elo",), extra=[*base_extra, *new], feats=f), base, keys)
        null = []
        for k in range(1, COPIES + 1):
            sh = Y.shuffle_within_weeks(f, new, seed=get_config().seed + 1000 + k)
            null.append(Y.gain(board.forecast(("elo",), extra=[*base_extra, *new], feats=sh), base, keys).share)
        log(f"  beside {base_name:<32} {name:<20} rows {g.rows}: {share(g)}; copies' max {100 * max(null):+.2f}%; counts: {g.lo > 0 and g.share > max(null)}")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
