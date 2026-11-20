# ruff: noqa: E501
"""IDEAS I83 (retro 2's backlog, 2026-11-20): does the closing spread share our experts' blind
spots after a change?

Discovery only, 2006-2024 (the 2025 vault and 2026 are left out). I47 found team-efficiency off
in the games after a change; the direction of each bet is fixed from I47 before this run:
  - a new head coach, games 1-4: the team does worse than forecast (its defense allows more), so
    bet against it;
  - a starting QB changed in season, games 1-4 after: worse, bet against;
  - a starting QB changed in season, games 5 on after: better, bet on it.
The rest of I47's flags are shown too, with no direction fixed (two-sided).

For each flag: the line's average miss (margin minus the line's expected margin) on flagged
team-games minus the same weeks' other team-games, an interval from resampling whole weeks, and
the cover rate of the pre-registered side (pushes left out), against 52.4% (the break-even at
-110) and against 400 shuffles of the flag among the same week's team-games.

Run from pcf/:  python projects/retro/explore/retro2_i83_line.py > projects/retro/explore/retro2_i83_line.txt
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
FIRST, LAST = 2006, 2024
DRAWS, SHUFFLES = 4000, 400
# +1: bet on the flagged team; -1: against it; 0: no direction fixed before the run
SIDE = {
    "new head coach, games 1-4": -1,
    "starting QB changed in season, games 1-4 after": -1,
    "starting QB changed in season, games 5 on after": 1,
}

spec = importlib.util.spec_from_file_location("i47", Path(__file__).with_name("i47_change_lens.py"))
i47 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i47)


def frame(src) -> tuple[pl.DataFrame, list[str]]:
    te = i47.team_events(src)
    flags = [k for k in te.columns if k not in ("game_id", "team", "season", "week", "home")]
    line = src.part("team_game", "pregame").select("game_id", "team", "spread")
    res = src.part("team_game", "result").select("game_id", "team", "margin")
    typ = src.part("game", "schedule").select("game_id", "game_type")
    d = (
        te.join(line, on=["game_id", "team"])
        .join(res, on=["game_id", "team"])
        .join(typ, on="game_id")
        .filter(c("season").is_between(FIRST, LAST) & (c("game_type") == "REG"))
        .drop_nulls(["spread", "margin"])
        .with_columns(c(f).fill_null(False) for f in flags)
        # the team's spread is its handicap: expected margin = -spread
        .with_columns(miss=c("margin") + c("spread"))
        .with_columns(cover=pl.when(c("miss") > 0).then(1.0).when(c("miss") < 0).then(0.0))
    )
    return d, flags


def gap(d: pl.DataFrame, flag: str, rng: np.random.Generator) -> dict:
    w = (
        d.group_by("season", "week")
        .agg(
            sg=c("miss").filter(c(flag)).sum(),
            ng=c(flag).sum(),
            mr=c("miss").filter(~c(flag)).mean(),
        )
        .filter((c("ng") > 0) & c("mr").is_not_null())
    )
    sg, ng = w["sg"].to_numpy(), w["ng"].to_numpy().astype(float)
    base = ng * w["mr"].to_numpy()
    est = (sg.sum() - base.sum()) / ng.sum()
    draws = rng.multinomial(len(sg), np.full(len(sg), 1 / len(sg)), size=DRAWS)
    boot = (draws @ sg - draws @ base) / np.maximum(draws @ ng, 1)
    lo, hi = np.quantile(boot, [0.05, 0.95])
    per = (
        d.filter(c(flag))
        .group_by("season")
        .agg(m=c("miss").mean())
        .join(d.filter(~c(flag)).group_by("season").agg(o=c("miss").mean()), on="season")
    )
    same = int((np.sign((per["m"] - per["o"]).to_numpy()) == np.sign(est)).sum())
    return {"games": int(ng.sum()), "line_miss": est, "lo90": lo, "hi90": hi,
            "seasons_same_sign": f"{same} of {per.height}"}  # fmt: skip


def cover(d: pl.DataFrame, flag: str, side: int, rng: np.random.Generator) -> dict:
    """The pre-registered side's cover rate, and where it falls among shuffled flags."""
    x = d.drop_nulls("cover")
    y = x["cover"].to_numpy()
    f = x[flag].to_numpy()
    rate = float(y[f].mean()) if side > 0 else float(1 - y[f].mean())
    # shuffle the flag within each week, keeping how many games each week has
    wk = (x["season"] * 100 + x["week"]).to_numpy()
    order = np.argsort(wk, kind="stable")
    bounds = np.flatnonzero(np.diff(wk[order])) + 1
    groups = np.split(order, bounds)
    null = []
    for _ in range(SHUFFLES):
        g = f.copy()
        for idx in groups:
            g[idx] = rng.permutation(f[idx])
        r = y[g].mean()
        null.append(r if side > 0 else 1 - r)
    null = np.array(null)
    half = x.with_columns(early=c("season") <= 2015)
    halves = {}
    for name, part in (
        ("2006-2015", half.filter(c("early"))),
        ("2016-2024", half.filter(~c("early"))),
    ):
        yy = part.filter(c(flag))["cover"].to_numpy()
        halves[name] = float(yy.mean() if side > 0 else 1 - yy.mean()) if len(yy) else float("nan")
    return {"side": "on" if side > 0 else "against", "decided": int(f.sum()), "cover": rate,
            "beats_524": rate > 0.524, "shuffles_beaten": f"{(null < rate).mean():.0%}",
            "cover_2006_2015": halves["2006-2015"], "cover_2016_2024": halves["2016-2024"]}  # fmt: skip


def main() -> None:
    src = Gateway().source
    d, flags = frame(src)
    rng = np.random.default_rng(get_config().seed)
    pl.Config.set_tbl_rows(50)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(240)
    pl.Config.set_fmt_str_lengths(60)
    pl.Config.set_float_precision(3)
    print(f"team-games {FIRST}-{LAST}, regular season, with a closing line: {d.height}")
    print(
        f"the line's average miss overall: {d['miss'].mean():+.3f} points; cover rate {d['cover'].mean():.3f}\n"
    )
    print("== the line's miss after each change (margin minus the line's expected margin, points),")
    print("   flagged team-games minus the same weeks' others; 90% interval from resampling weeks")
    print(pl.DataFrame([{"change": f, **gap(d, f, rng)} for f in flags]))
    print("\n== the pre-registered bets (direction fixed from I47 before this run)")
    print(pl.DataFrame([{"change": f, **cover(d, f, s, rng)} for f, s in SIDE.items()]))
    # after the run, not pre-registered: the in-season QB change split by whether a backup starts
    tags = src.part("team_game", "tags").select("game_id", "team", "tag_backup_qb_start")
    e = d.join(tags, on=["game_id", "team"], how="left").with_columns(
        backup=c("tag_backup_qb_start").fill_null(False)
    )
    q = "starting QB changed in season, games 1-4 after"
    e = e.with_columns(
        **{
            "QB change 1-4, a backup starting": c(q) & c("backup"),
            "QB change 1-4, not a backup (e.g. the starter back)": c(q) & ~c("backup"),
        }
    )
    print("\n== after the run (not pre-registered): the in-season QB change, by who starts")
    split = [
        "QB change 1-4, a backup starting",
        "QB change 1-4, not a backup (e.g. the starter back)",
    ]
    print(pl.DataFrame([{"change": f, **gap(e, f, rng)} for f in split]))
    print(pl.DataFrame([{"change": f, **cover(e, f, -1, rng)} for f in split]))


if __name__ == "__main__":
    main()
