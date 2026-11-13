"""team-efficiency build: every variant's latest validated history, scored the exploration's way.

Skill = 1 - squared error / a reference's squared error, on the rows both scored, with a 90%
interval from resampling whole season-weeks (as explore/common.py `skill`). Each rung is shown
against the league level and against the rung below; then weeks 1-4, offense against defense
apart, 2020-2024 alone, and the q10-q90 coverage. Test seasons 2016-2024; the vault isn't read.
Writes summary.txt beside this file. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/build/summary.py
"""

from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.tables.store import load, read_part
from pcf.experts.team_efficiency import features as F

c = pl.col
HERE = Path(__file__).parent
SIDES = ("off", "def")
HORIZONS = ("next3", "rest")
LADDER = ("league", "usual", "ridge", "dml", "combo")
COLS = ("game_id", "team", "season", "week", "y", "mean", "q10", "q90")
BELOW = {"usual": "league", "ridge": "usual", "dml": "ridge", "combo": "dml"}


def latest(variant: str) -> pl.DataFrame | None:
    root = get_config().zone("outputs") / "team-efficiency" / variant
    runs = sorted(glob.glob(str(root / "*" / "history.parquet")), key=os.path.getmtime)
    return pl.read_parquet(runs[-1]) if runs else None


def skill(a: pl.DataFrame, ref: pl.DataFrame, n: int = 1000, seed: int = 0) -> tuple:
    k = ["game_id", "team"]
    j = a.select(*k, "season", "week", "y", "mean").join(
        ref.select(*k, ref="mean"), on=k, how="inner"
    )
    if j.is_empty():
        return (np.nan, np.nan, np.nan, 0)
    m = j.group_by("season", "week").agg(
        se=((c("y") - c("mean")) ** 2).sum(), sr=((c("y") - c("ref")) ** 2).sum()
    )
    se, sr = m["se"].to_numpy(), m["sr"].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(se), size=(n, len(se)))
    boots = 1 - se[idx].sum(1) / sr[idx].sum(1)
    lo, hi = np.percentile(boots, [5, 95])
    return (1 - se.sum() / sr.sum(), lo, hi, j.height)


def fmt(t: tuple) -> str:
    e, lo, hi, _ = t
    if np.isnan(e):
        return "      n/a"
    return f"{100 * e:+5.1f}% ({100 * lo:+.1f} to {100 * hi:+.1f})"


def main() -> None:
    weeks = (
        read_part("team_game", "schedule", seasons=list(range(2016, 2025)))
        .select("game_id", "team", "week")
        .collect()
    )
    tg = load("team_game", parts=["schedule", "efficiency"])
    hist = {}
    for s in SIDES:
        for h in HORIZONS:
            y = F.targets(tg, s, h).select("game_id", "team", "y")
            for r in LADDER:
                x = latest(f"{s}_{h}_{r}")
                if x is not None:
                    x = x.join(y, on=["game_id", "team"], how="inner")
                    x = x.join(weeks, on=["game_id", "team"], how="left")
                    # a season's games run into the next January: the season is the schedule's
                    x = x.with_columns(season=c("game_id").str.slice(0, 4).cast(pl.Int32))
                    hist[(s, h, r)] = x
    lines = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    say("Skill (share of squared error removed), 2016-2024, 90% interval from resampling weeks")
    for h in HORIZONS:
        for s in SIDES:
            say("")
            say(f"{s} {h}: rung | vs league | vs the rung below | weeks 1-4 vs below | "
                f"2020-24 vs below | q10-q90 holds | rows")  # fmt: skip
            for r in LADDER:
                a = hist.get((s, h, r))
                if a is None:
                    say(f"  {r:7s} not run yet")
                    continue
                lg = hist.get((s, h, "league"))
                below = hist.get((s, h, BELOW.get(r, "")))
                vs_lg = skill(a, lg) if lg is not None and r != "league" else (np.nan,) * 4
                if below is not None:
                    vb = skill(a, below)
                    w14 = skill(a.filter(c("week") <= 4), below)
                    late = skill(a.filter(c("season") >= 2020), below)
                else:
                    vb = w14 = late = (np.nan,) * 4
                cover = a.select(((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()).item()
                say(f"  {r:7s} {fmt(vs_lg)} | {fmt(vb)} | {fmt(w14)} | {fmt(late)} | "
                    f"{cover:.1%} | {a.height:,}")  # fmt: skip
    say("")
    say("Offense and defense pooled, the combination against all plays equal (ridge):")
    for h in HORIZONS:
        a = [hist.get((s, h, "combo")) for s in SIDES]
        b = [hist.get((s, h, "ridge")) for s in SIDES]
        if all(x is not None for x in a + b):
            pa = pl.concat(
                [x.select(*COLS).with_columns(team=c("team") + f"|{s}") for x, s in zip(a, SIDES)]
            )
            pb = pl.concat(
                [x.select(*COLS).with_columns(team=c("team") + f"|{s}") for x, s in zip(b, SIDES)]
            )
            say(f"  {h:5s} {fmt(skill(pa, pb))} | weeks 1-4 "
                f"{fmt(skill(pa.filter(c('week') <= 4), pb))} | 2020-24 "
                f"{fmt(skill(pa.filter(c('season') >= 2020), pb))}")  # fmt: skip
    (HERE / "summary.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
