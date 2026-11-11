"""pace exploration, follow-up (the CEO, 2026-11-10): for each hunch, which conditions hold?
And how consistent are PROE and pace over expected within each condition?

Conditions are the H19 slices: downs, score, win chance, field position, quarter, the clock.
For each slice, per team-game, PROE and pace over expected (clock-aware, refit out of fold):
- **Consistency (H23):** `pcf.validation.consistency` within the slice: week to week and season
  to season.
- **One habit? (H19 for PROE, the same for pace, H22):** the slice's team-season mean against
  the team's mean on all *other* plays, divided by the most each side's noise allows
  (split-half reliability, odd against even weeks). 1.0 = the same habit.
- **H20:** the slice's pass rate and PROE in a game against the pre-game win chance (the close),
  beyond the team's season-to-date PROE: change per +10 points of win chance.
- **H21:** the slice's PROE next game against opponent-adjusted pass success so far (season to
  date), beyond the team's own PROE history (overall season to date, last 4, and the slice's
  own season to date): change per sd.
- **H24, H25 by condition** (run plays or passes; close or not), as in h24_h25_fatigue.py.
Intervals are 90%, from resampling whole weeks. With about 100 tests, about 10 will exclude
zero by chance alone, so a single slice is a lead, not a finding.

Run from pcf/projects/pace/explore: PYTHONUTF8=1 ../../../.venv/Scripts/python.exe conditions.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from common import boot, plays
from h19_h21_pass import slices
from h22_h23_pace import CLOCK, expected

from pcf.config import get_config
from pcf.validation.consistency import consistency

c = pl.col


def sl_coef(d: pl.DataFrame, y: str, xs: list[str], k: int) -> float:
    X = np.column_stack([np.ones(d.height), *[d[x] for x in xs]])
    return float(np.linalg.lstsq(X, d[y].to_numpy(), rcond=None)[0][1 + k])


def reliability(rows: pl.DataFrame, v: str) -> float:
    h = rows.group_by("team", "season", odd=c("week") % 2 == 1).agg(c(v).mean()).pivot(on="odd", index=["team", "season"], values=v).drop_nulls()
    r = np.corrcoef(h["true"], h["false"])[0, 1]
    return 2 * r / (1 + r) if r > 0 else np.nan


def main() -> None:
    p = plays().filter((c("qtr") <= 4) & c("scrimmage"))
    s = p.filter(c("gap").is_not_null() & c("wp").is_not_null() & c("ep").is_not_null())
    s = expected(s, CLOCK, "clock").with_columns(oe=c("gap") - c("exp_clock")).select("game_id", "play_id", "oe")
    p = p.join(s, on=["game_id", "play_id"], how="left")
    tg = pl.read_parquet(get_config().zone("interim") / "pace" / "team_games.parquet").select(
        "game_id", "team", "win_close", "proe_prior", "proe_last4", "epa_db_adj_prior")
    sd = tg["epa_db_adj_prior"].std()
    tg = tg.with_columns(succ=(c("epa_db_adj_prior") - tg["epa_db_adj_prior"].mean()) / sd)

    cons, link, h20, h21 = [], [], [], []
    for fam, expr in slices(p).items():
        x = p.with_columns(sl=expr).drop_nulls("sl")
        for sl in x["sl"].unique().sort().to_list():
            inn = x.filter(c("sl") == sl)
            out = x.filter(c("sl") != sl)
            g_in = inn.group_by("game_id", "season", "week", "team").agg(proe=c("pass_oe").mean(), pace=c("oe").mean(), pass_rate=c("pass").mean(), n=pl.len())
            g_out = out.group_by("game_id", "season", "week", "team").agg(proe=c("pass_oe").mean(), pace=c("oe").mean())
            # consistency within the slice
            cc = consistency(g_in, ["proe", "pace"])
            for r in cc.iter_rows(named=True):
                cons.append({"family": fam, "slice": sl, "measure": r["measure"], "week_r": r["week_r"], "season_r": r["season_r"], "verdict": r["verdict"], "plays_per_game": round(g_in["n"].mean(), 1)})
            # one habit with the rest of the team's plays?
            for v in ("proe", "pace"):
                a = g_in.group_by("team", "season").agg(c(v).mean())
                b = g_out.group_by("team", "season").agg(c(v).mean())
                j = a.join(b, on=["team", "season"], suffix="_rest").drop_nulls()
                r = np.corrcoef(j[v], j[f"{v}_rest"])[0, 1]
                ra, rb = reliability(g_in, v), reliability(g_out, v)
                link.append({"family": fam, "slice": sl, "measure": v, "r": r, "disattenuated": r / np.sqrt(ra * rb) if ra > 0 and rb > 0 else np.nan})
            # H20: the slice's pass rate and PROE against pre-game win chance
            d = g_in.join(tg, on=["game_id", "team"]).drop_nulls(["win_close", "proe_prior"]).with_columns(wk=c("season").cast(pl.Utf8) + "-" + c("week").cast(pl.Utf8))
            for y in ("pass_rate", "proe"):
                est, lo, hi = boot(d, lambda dd, y=y: sl_coef(dd, y, ["win_close", "proe_prior"], 0) * 0.1, by="wk", n=100)
                h20.append({"family": fam, "slice": sl, "outcome": y, "per_10pts": est * 100, "lo": lo * 100, "hi": hi * 100})
            # H21: next game's slice PROE against pass success so far, beyond PROE history
            g_in = g_in.sort("team", "season", "week").with_columns(proe_slice_prior=c("proe").shift(1).cum_sum().over("team", "season") / c("proe").shift(1).cum_count().over("team", "season"))
            d = g_in.join(tg, on=["game_id", "team"]).drop_nulls(["succ", "proe_prior", "proe_last4", "proe_slice_prior", "proe"]).with_columns(wk=c("season").cast(pl.Utf8) + "-" + c("week").cast(pl.Utf8))
            est, lo, hi = boot(d, lambda dd: sl_coef(dd, "proe", ["succ", "proe_prior", "proe_last4", "proe_slice_prior"], 0), by="wk", n=100)
            h21.append({"family": fam, "slice": sl, "per_sd": est * 100, "lo": lo * 100, "hi": hi * 100})
            print(fam, sl, "done", flush=True)

    with pl.Config(tbl_rows=80, tbl_width_chars=200, float_precision=2):
        print("\n=== consistency within each condition (H23)")
        print(pl.DataFrame(cons).pivot(on="measure", index=["family", "slice", "plays_per_game"], values=["week_r", "season_r"]))
        print("\n=== one habit with the team's other plays? disattenuated r (H19 for PROE, H22 for pace)")
        print(pl.DataFrame(link).pivot(on="measure", index=["family", "slice"], values=["r", "disattenuated"]))
        print("\n=== H20 by condition: change per +10 pts of pre-game win chance, points (90%)")
        print(pl.DataFrame(h20).pivot(on="outcome", index=["family", "slice"], values=["per_10pts", "lo", "hi"]))
        print("\n=== H21 by condition: next game's PROE in the slice per sd of pass success so far, points (90%)")
        print(pl.DataFrame(h21))
    pl.DataFrame(cons).write_parquet(get_config().zone("interim") / "pace" / "cond_consistency.parquet")
    pl.DataFrame(link).write_parquet(get_config().zone("interim") / "pace" / "cond_link.parquet")
    pl.DataFrame(h20).write_parquet(get_config().zone("interim") / "pace" / "cond_h20.parquet")
    pl.DataFrame(h21).write_parquet(get_config().zone("interim") / "pace" / "cond_h21.parquet")


if __name__ == "__main__":
    main()
