# ruff: noqa: E501
"""Retro 2's backlog (2026-11-20), the incentive group: IDEAS I46 (the final week only) and I17.

Discovery only, 2016-2024. Final-week standings from `pcf.data.standings.final_week_locks` at the
moment just before the final week's first kickoff (the same rule Elo's seed lock uses).

- I46, the final week: teams already eliminated. Elo's margin miss (Elo's margin already knows
  seed locks, I19) for them against the week's other teams; participation's snap-share miss
  for their young players (first or second season) against young players on other teams.
  The last three weeks, and clinched-but-not-seeded teams, need standings the brute-force lock
  can't reach (more than 12 games left per conference), so they stay open.
- I17: a player whose team was seed-locked in the final week (rested starters), in his team's
  first playoff game: participation's snap-share miss against other players' first playoff game.

Gaps are flagged rows minus the same week's other rows, with a 90% interval from resampling
seasons (the rows are few).

Run from pcf/:  python projects/retro/explore/retro2_incentives.py > projects/retro/explore/retro2_incentives.txt
"""

from __future__ import annotations

import importlib.util
from datetime import timedelta
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway
from pcf.data.standings import final_week_locks

c = pl.col
FIRST, LAST = 2016, 2024
spec = importlib.util.spec_from_file_location("i47", Path(__file__).with_name("i47_change_lens.py"))
i47 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i47)


def locks(src) -> pl.DataFrame:
    sch = src.part("game", "schedule")
    res = src.part("game", "result").select(
        "game_id", "home_score", "away_score", result_known_at="known_at"
    )
    game = sch.join(res, on="game_id", how="left")
    out = []
    for s in range(FIRST, LAST + 1):
        reg = game.filter((c("season") == s) & (c("game_type") == "REG"))
        last = reg["week"].max()
        moment = reg.filter(c("week") == last)["kickoff"].min() - timedelta(minutes=1)
        lk = final_week_locks(game, s, moment)
        out.append(lk.with_columns(week=pl.lit(last, pl.Int32)))
    return pl.concat(out)


def gap(d: pl.DataFrame, flag: str, rng) -> dict:
    """Flagged rows' mean miss minus the other rows', seasons resampled."""
    per = (
        d.group_by("season")
        .agg(
            sf=c("miss").filter(c(flag)).sum(),
            nf=c(flag).sum(),
            mo=c("miss").filter(~c(flag)).mean(),
        )
        .filter(c("nf") > 0)
    )
    sf, nf, mo = (per[k].to_numpy().astype(float) for k in ("sf", "nf", "mo"))
    est = (sf.sum() - (nf * mo).sum()) / nf.sum()
    draws = rng.multinomial(len(sf), np.full(len(sf), 1 / len(sf)), size=4000)
    boot = (draws @ sf - draws @ (nf * mo)) / np.maximum(draws @ nf, 1)
    lo, hi = np.quantile(boot, [0.05, 0.95])
    same = int((np.sign(sf / nf - mo) == np.sign(est)).sum())
    return {"rows": int(nf.sum()), "gap": est, "lo90": lo, "hi90": hi,
            "seasons_same_sign": f"{same} of {len(sf)}"}  # fmt: skip


def main() -> None:
    gw = Gateway()
    src = gw.source
    rng = np.random.default_rng(get_config().seed)
    lk = locks(src)
    sch = src.part("game", "schedule").select(
        "game_id", "season", "week", "game_type", "home_team", "away_team"
    )
    rows = []

    # I46: Elo's margin, one row per side, the final week
    e = i47.history("elo", "margin", gw).join(sch, on="game_id")
    sides = pl.concat([
        e.select("game_id", "season", "week", team="home_team", miss=c("miss")),
        e.select("game_id", "season", "week", team="away_team", miss=-c("miss")),
    ])  # fmt: skip
    fw = sides.join(lk, on=["season", "week", "team"]).filter(c("seed_locked") == 0)
    fw = fw.with_columns(elim=c("eliminated") == 1)
    rows.append({"test": "I46: Elo margin miss, eliminated teams, final week (points; locked teams left out)",
                 **gap(fw, "elim", rng)})  # fmt: skip

    # I46: participation, young players on eliminated teams, final week
    h = i47.history("participation", "trees_week", gw)
    ro = src.part("player_game", "roster").select(
        "gsis_id", "game_id", "team", "years_exp", "position"
    )
    p = h.join(ro, on=["gsis_id", "game_id"]).join(
        sch.select("game_id", "season", "week", "game_type"), on="game_id"
    )
    p = p.filter(c("season").is_between(FIRST, LAST))
    pf = p.join(lk, on=["season", "week", "team"]).filter(c("years_exp") <= 1)
    pf = pf.with_columns(elim=c("eliminated") == 1)
    rows.append({"test": "I46: participation snap-share miss, players in their first two seasons, eliminated teams, final week",
                 **gap(pf, "elim", rng)})  # fmt: skip
    pf2 = (
        p.join(lk, on=["season", "week", "team"])
        .filter(c("years_exp") > 1)
        .with_columns(elim=c("eliminated") == 1)
    )
    rows.append({"test": "I46 (for scale): the same, veterans", **gap(pf2, "elim", rng)})

    # I17: the first playoff game of players whose team was seed-locked in the final week
    po = p.filter(c("game_type") != "REG").sort("week")
    first = po.group_by("gsis_id", "season", maintain_order=True).first()
    locked = lk.filter(c("seed_locked") == 1).select("season", "team", locked=pl.lit(True))
    first = first.join(locked, on=["season", "team"], how="left").with_columns(
        c("locked").fill_null(False)
    )
    rows.append({"test": "I17: participation snap-share miss, first playoff game, team seed-locked in the final week",
                 **gap(first, "locked", rng)})  # fmt: skip
    # starters only: the player's share before the final week was 0.6+
    reg = p.filter(c("game_type") == "REG")
    lastwk = reg.group_by("season").agg(lw=c("week").max())
    pre = (
        reg.join(lastwk, on="season")
        .filter(c("week") < c("lw"))
        .sort("week")
        .group_by("gsis_id", "season")
        .agg(pre=c("y").tail(4).mean())
    )
    fs = first.join(pre, on=["gsis_id", "season"], how="left")
    for name, cond in (
        ("regulars (0.6+ before the final week)", c("pre") >= 0.6),
        ("fill-ins (under 0.3 before)", c("pre") < 0.3),
    ):
        rows.append({"test": f"I17: the same, {name}", **gap(fs.filter(cond), "locked", rng)})
    pl.Config.set_tbl_rows(50)
    pl.Config.set_tbl_width_chars(240)
    pl.Config.set_fmt_str_lengths(110)
    pl.Config.set_float_precision(3)
    print(
        f"Seasons {FIRST}-{LAST}. Teams eliminated before the final week: "
        f"{int(lk['eliminated'].sum())}; seed-locked: {int(lk['seed_locked'].sum())}"
    )
    print(
        "miss = result minus forecast; gap = flagged rows minus the others; snap share in points of 1.0\n"
    )
    print(pl.DataFrame(rows))


if __name__ == "__main__":
    main()
