"""IDEAS I148 (retro 4's dream, 2026-11-25): fast traits as a change alarm.

Discovery only. Saved walk-forward histories, 2016-2024 (the 2025 vault is left out).

A team's fast traits (schemes-v2's shotgun and tempo, pace's pass rate over expected and
no-huddle rate) each have a forecast and an actual per game. Their misses, standardized, are
averaged over the team's last two games; a big two-game shift in the same direction is the alarm
(the top 5% of team-games). The question: is team-efficiency's next forecast (EPA a play over the
next 3 games, offense and defense) off by more after an alarm, outside the changes we already
know (a new or changed head coach or starting QB, games 1-4; I47's flags)?

- The gap: squared miss after an alarm against the same week's other rows, weeks resampled.
- Claude's odds, written before the run (IDEAS.md, I148): 45% flagged weeks miss more; 25% a
  shorter memory after a flag pays (not tested here: it needs a re-walk of team-efficiency).

Run from pcf/:  python projects/retro/explore/retro4_i148_change_alarm.py > projects/retro/explore/retro4_i148_change_alarm.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from i47_change_lens import history, team_events  # noqa: E402

from pcf.data.gateway import Gateway  # noqa: E402

c = pl.col
DRAWS = 4000
TOP = 0.05
RNG = np.random.default_rng(148)
FAST = [("schemes-v2", "shotgun_shrunk"), ("schemes-v2", "tempo_shrunk"),
        ("pace", "proe_shrunk"), ("pace", "no_huddle_shrunk")]  # fmt: skip
EFF = [("team-efficiency", "off_next3_ridge"), ("team-efficiency", "def_next3_ridge")]
KNOWN = ["new head coach, games 1-4", "new starting QB at season start, games 1-4",
         "starting QB changed in season, games 1-4 after", "head coach changed in season, games 1-4 after"]  # fmt: skip


def gap(d, rng):
    """Flagged rows' squared miss less the same week's others, weeks resampled."""
    d = d.with_columns(wk=c("game_id").str.slice(0, 7), sq=c("miss") ** 2)
    d = d.with_columns(dev=c("sq") - c("sq").mean().over("wk"))
    w = d.group_by("wk").agg(s=(c("dev") * c("alarm")).sum(), n=c("alarm").sum())
    s, n = w["s"].to_numpy(), w["n"].to_numpy().astype(float)
    draws = rng.integers(0, len(s), (DRAWS, len(s)))
    g = s[draws].sum(1) / n[draws].sum(1)
    base = float(d["sq"].mean())
    return s.sum() / n.sum() / base, np.quantile(g, 0.05) / base, np.quantile(g, 0.95) / base, int(n.sum())


def main() -> None:
    gw = Gateway()
    te = team_events(gw.source)
    order = gw.source.part("team_game", "schedule").select("game_id", "team", "season", "week")
    z = order
    for proj, var in FAST:
        h = history(proj, var, gw).filter(c("game_id") < "2025")
        sd = float(h["miss"].std())
        z = z.join(h.select("game_id", "team", (c("miss") / sd).alias(var)), on=["game_id", "team"], how="left")
    names = [v for _, v in FAST]
    z = z.filter(pl.all_horizontal(c(n).is_not_null() for n in names)).sort("team", "season", "week")
    z = z.with_columns(
        [((c(n) + c(n).shift(1).over("team", "season")) / np.sqrt(2)).alias(f"two_{n}") for n in names]
    ).with_columns(D=pl.mean_horizontal([c(f"two_{n}").abs() for n in names])).drop_nulls("D")
    cut = float(z["D"].quantile(1 - TOP))
    z = z.with_columns(alarm=c("D") >= cut, next_game=c("game_id").shift(-1).over("team", "season"))
    print(f"team-games with all four fast traits and a game before: {z.height:,}; alarms (top 5%, D >= {cut:.2f}): {z['alarm'].sum():,}")
    known = te.select("game_id", "team", known=pl.any_horizontal([c(k).fill_null(False) for k in KNOWN]))
    al = z.drop_nulls("next_game").select(c("next_game").alias("game_id"), "team", "alarm", "D")
    al = al.join(known, on=["game_id", "team"], how="left").with_columns(c("known").fill_null(False))
    print(f"alarms whose next game is inside a known change's first 4 games: {al.filter(c('alarm') & c('known')).height:,} (left out below); share of all next games inside one {al['known'].mean():.1%}, of alarms' {al.filter(c('alarm'))['known'].mean():.1%}\n")

    for proj, var in EFF:
        h = history(proj, var, gw).filter(c("game_id") < "2025")
        d = h.join(al, on=["game_id", "team"]).filter(~c("known"))
        share, lo, hi, n = gap(d, RNG)
        print(f"{var}: after an alarm the squared miss is {share:+.1%} of the average ({lo:+.1%} to {hi:+.1%}); {n:,} alarm rows of {d.height:,}")
        # the miss's direction: does the forecast lag the shift?
        a = d.filter(c("alarm"))
        print(f"    mean miss after an alarm {a['miss'].mean():+.4f} EPA a play (others {d.filter(~c('alarm'))['miss'].mean():+.4f})")
        by = (d.with_columns(season=c("game_id").str.slice(0, 4))
              .group_by("season").agg(gap=(c("miss") ** 2).filter(c("alarm")).mean() - (c("miss") ** 2).filter(~c("alarm")).mean())
              .sort("season"))  # fmt: skip
        print("    by season (alarm less others, squared miss): " + ", ".join(f"{r['season']} {r['gap']:+.4f}" for r in by.iter_rows(named=True)))
        # with the known changes kept in, for comparison
        d2 = h.join(al, on=["game_id", "team"])
        share2, lo2, hi2, n2 = gap(d2, RNG)
        print(f"    with known changes kept in: {share2:+.1%} ({lo2:+.1%} to {hi2:+.1%}); {n2:,} alarm rows\n")


if __name__ == "__main__":
    main()
