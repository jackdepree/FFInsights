"""Availability build: games played for any reason, and the yardstick (BUILD.md A7-A9, A13, I121;
the brief's tests 2 and 4).

Games played (any reason), the composite the brief names: his rate of playing when healthy times
the share of the window he isn't health-absent, from the rest-of-season champion's saved
walk-forward history (rule e):
    gp = hrate x (1 - E[health absences] / n)
    hrate = (games played this season + 4 x 0.9) / (games not health-absent this season + 4)
(the healthy rate's prior, 0.9, and its weight, 4 games, as I60's, decision 0047 call 12). Its
range: hrate x (1 - the health count's q90 / n) to hrate x (1 - q10 / n).

Scored on the yardstick's rest-of-season rows (participation's chance of a snap 50%+, QB/RB/WR/
TE), 2019-2024, against I60's crude forecast (`av_rate`); the outcome is I60's hindsight, the
share of the window's games he took a snap in.

The yardstick: beside I60's crude forecast and participation (both in the base), what
availability's columns add on the receiving, rushing and passing rest-of-season boards, against
19 copies shuffled within each week. The board's training rows start in 2017 here (availability's
history starts there), for the base and the new forecast alike.

Run from pcf/: <venv python> projects/availability/build/games_played_run.py <rest variant> [fitted] [yardstick]
(`fitted`: I129's fitted healthy rate, games.walk_healthy, in place of the shrunk one)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

from pcf.baselines.crude import inputs as I
from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config
from pcf.experts.availability import checks as K
from pcf.experts.availability import games as G
from pcf.validation.compare import block_interval

c = pl.col
REST = sys.argv[1] if len(sys.argv) > 1 else "rest_chain"
FITTED = "fitted" in sys.argv  # I129: the fitted healthy rate (games.walk_healthy) in place of the shrunk one
TAG = f"{REST}_fitted" if FITTED else REST
OUT = Path(__file__).with_name(f"games_played_{TAG}.txt" if "yardstick" not in sys.argv else f"yardstick_{TAG}.txt")
COPIES = 19
lines: list[str] = []
KEYS = K.KEYS


def log(*parts) -> None:
    s = " ".join(str(p) for p in parts)
    print(s, flush=True)
    lines.append(s)


def share(g) -> str:
    return f"{100 * g.share:+.2f}% ({100 * g.lo:+.2f} to {100 * g.hi:+.2f}); range score {100 * g.range_share:+.2f}% ({100 * g.range_lo:+.2f} to {100 * g.range_hi:+.2f})"


hist = pl.read_parquet(K.cache_dir() / f"hist_{REST}.parquet")
feats = pl.read_parquet(K.cache_dir() / "features.parquet").select(
    *KEYS, "played_s", "games_s", "absent_s", "proneness", "credibility", "n_games", "left",
    "position", "last_share", "log_snaps_s", "age", "last_played")
av = G.games_played(hist.drop("season", "position", strict=False).join(feats, on=KEYS, how="left")).select(
    *KEYS, "gp", "hrate", "ha_share", "position", "last_share", "log_snaps_s", "age", "games_s", "last_played",
    h_as_of="as_of", ha="mean", ha10="q10", ha90="q90", ha_p="p_nonzero", n="n_window", hy="y", proneness="proneness")


def fitted(rows: pl.DataFrame) -> pl.DataFrame:
    """I129: gp from the fitted healthy rate, each season from a fit on the seasons before it
    (2018 on; `rows` carry season and av_true); 2017, with no season before it, keeps the shrunk."""
    w = G.walk_healthy(rows.with_columns(y=c("av_true")), list(range(2018, 2025)))
    out = rows.join(w.select(*KEYS, "gp_fit"), on=KEYS, how="left")
    return out.with_columns(gp=pl.coalesce("gp_fit", "gp")).drop("gp_fit")


def lined(board: Y.Board) -> pl.DataFrame:
    """Availability's columns on the board's rows: the latest made by each row's moment."""
    rows = board.features.select(*board.keys, "as_of", "y_s")
    j = rows.join(av, on=KEYS, how="left").filter(c("h_as_of").is_null() | (c("h_as_of") <= c("as_of")))
    return j.sort("h_as_of").unique(board.keys, keep="last")


# ---------------------------------------------------------------- test 2: games played
log(f"TEST 2: games played (any reason) over the rest of the season, from {REST}, on the receiving board's rows (QB/RB/WR/TE, participation's chance of a snap 50%+), 2019-2024")
board = Y.load_board("receiving", "rest")
rows = board.features.filter(c("step_season") >= 2017)
fc = I.availability(rows.select(*board.keys, "team", "season", "week", "as_of", "y_s"))
hs = I.availability(rows.select(*board.keys, "team", "season", "week", "as_of", "y_s"), hindsight=True)
j = lined(board).join(fc.select(*KEYS, "av_rate"), on=KEYS).join(hs.select(*KEYS, "av_true"), on=KEYS)
j = j.join(rows.select(*KEYS, "step", "season"), on=KEYS).drop_nulls(["gp", "av_rate", "av_true"])
if FITTED:
    j = fitted(j.drop_nulls("hy"))
j = G.walk_ranges(j.with_columns(y=c("av_true")), list(range(2019, 2025)))
j = j.with_columns(se_av=(c("gp") - c("av_true")) ** 2, se_i60=(c("av_rate") - c("av_true")) ** 2)
per = j.group_by("step").agg(d=(c("se_i60") - c("se_av")).sum(), n=pl.len(), b=c("se_i60").sum())
lo, hi = block_interval(per["d"].to_numpy().astype(float), per["n"].to_numpy().astype(float), 2000, 0)
base = j["se_i60"].mean()
diff = j["se_i60"].mean() - j["se_av"].mean()
log(f"  rows {j.height}, weeks {per.height}; outcome (share played) mean {j['av_true'].mean():.3f}; composite mean {j['gp'].mean():.3f}; I60 mean {j['av_rate'].mean():.3f}")
log(f"  squared error: I60 {base:.5f}, availability's composite {j['se_av'].mean():.5f}")
log(f"  A7: the composite removes {100 * diff / base:+.2f}% of I60's squared error ({100 * lo / base:+.2f} to {100 * hi / base:+.2f}), {'better' if lo > 0 else 'worse' if hi < 0 else 'tie'}")
for name, sub in (("healthy at the run (health share under 10%)", j.filter(c("ha_share") < 0.1)), ("a health absence expected (10%+)", j.filter(c("ha_share") >= 0.1))):
    log(f"    {name}: rows {sub.height}, I60 {sub['se_i60'].mean():.5f}, composite {sub['se_av'].mean():.5f}")
for s_ in range(2019, 2025):
    sub = j.filter(c("season") == s_)
    log(f"    {s_}: rows {sub.height}, I60 {sub['se_i60'].mean():.5f}, composite {sub['se_av'].mean():.5f} ({100 * (sub['se_i60'].mean() - sub['se_av'].mean()) / sub['se_i60'].mean():+.1f}%)")
cover = j.select(((c("av_true") >= c("gp10") - 1e-9) & (c("av_true") <= c("gp90") + 1e-9)).mean()).item()
below = j.select((c("av_true") < c("gp10") - 1e-9).mean()).item()
above = j.select((c("av_true") > c("gp90") + 1e-9).mean()).item()
log(f"  A8/A9: the range (earlier seasons' misses by size of forecast, games.py): q10-q90 coverage {100 * cover:.1f}%, below q10 {100 * below:.1f}%, above q90 {100 * above:.1f}%")
pin = lambda col, tau: pl.max_horizontal(tau * (c("av_true") - c(col)), (tau - 1) * (c("av_true") - c(col)))  # noqa: E731
log(f"  range score (share of the window, q10/q50/q90): composite {j.select(((pin('gp10', 0.1) + pin('gp50', 0.5) + pin('gp90', 0.9)) / 3).mean()).item():.4f}")
hcov = hist.filter(c("y").is_not_null()).select(
    cover=((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean(), below=(c("y") < c("q10")).mean())
log(f"  the health count itself ({REST}, every roster row): coverage {100 * hcov['cover'][0]:.1f}%, below q10 {100 * hcov['below'][0]:.1f}%")
j.select(*KEYS, "season", "step", "gp", "gp10", "gp50", "gp90", "av_rate", "av_true").write_parquet(K.cache_dir() / f"games_played_{TAG}.parquet")
if "yardstick" not in sys.argv:
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.exit(0)

# ---------------------------------------------------------------- test 4: the yardstick
log("\nTEST 4: the yardstick, rest of season: beside I60's crude forecast and participation, what availability adds (19 shuffled copies)")
COLS = {"av_gp": "gp", "av_gp_y": None, "av_ha_share": "ha_share", "av_ha_p": "ha_p"}
results = []
for target in ("receiving", "rushing", "passing"):
    board = Y.load_board(target, "rest")
    f = board.features.filter(c("step_season") >= 2017)
    i60 = I.availability(f.select(*board.keys, "team", "season", "week", "as_of", "y_s"))
    a = lined(board)
    if FITTED:
        hs_ = I.availability(f.select(*board.keys, "team", "season", "week", "as_of", "y_s"), hindsight=True)
        a = a.join(hs_.select(*board.keys, "av_true"), on=board.keys, how="left").join(f.select(*board.keys, "season"), on=board.keys)
        a = fitted(a.filter(c("gp").is_not_null()))
    a = a.select(*board.keys, "y_s", av_gp="gp", av_ha_share="ha_share", av_ha_p="ha_p", av_prone="proneness")
    a = a.with_columns(av_gp_y=c("y_s") * c("av_gp")).drop("y_s")
    f = f.join(i60, on=board.keys, how="left").join(a, on=board.keys, how="left")
    i60_cols = ["av_rate", "av_y", "av_q", "av_dnp", "av_out_s"]
    new = ["av_gp", "av_gp_y", "av_ha_share", "av_ha_p"]
    f = f.with_columns(c(x).fill_null(c(x).median()) for x in [*i60_cols, *new, "av_prone"])
    beside = ("participation",)
    base = board.forecast(beside, extra=i60_cols, feats=f)
    for name, cols in (("availability (4 columns)", new), ("games played alone", ["av_gp", "av_gp_y"]), ("I121: proneness", ["av_prone"])):
        pred = board.forecast(beside, extra=[*i60_cols, *cols], feats=f)
        g = Y.gain(pred, base, board.keys)
        null = []
        for k in range(1, COPIES + 1):
            sh = Y.shuffle_within_weeks(f, cols, seed=get_config().seed + 1000 + k)
            null.append(Y.gain(board.forecast(beside, extra=[*i60_cols, *cols], feats=sh), base, board.keys).share)
        counts = g.lo > 0 and g.share > max(null)
        log(f"  {target:<10} {name:<26} rows {g.rows}: {share(g)}; copies' max {100 * max(null):+.2f}%; counts: {counts}")
        results.append({"target": target, "input": name, "share": g.share, "lo": g.lo, "hi": g.hi, "range": g.range_share,
                        "copies_max": max(null), "counts": counts, "rows": g.rows})
    # the ceiling beside the same base: the share he did play
    hs = I.availability(f.select(*board.keys, "team", "season", "week", "as_of", "y_s"), hindsight=True)
    f2 = f.join(hs, on=board.keys, how="left").with_columns(c("av_true", "av_true_y").fill_null(c("av_true").median()))
    g = Y.gain(board.forecast(beside, extra=[*i60_cols, "av_true", "av_true_y"], feats=f2), base, board.keys)
    log(f"  {target:<10} {'hindsight (the ceiling)':<26} rows {g.rows}: {share(g)}")
pl.DataFrame(results).write_csv(Path(__file__).with_name(f"yardstick_{TAG}.csv"))
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
