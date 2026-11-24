# ruff: noqa: E501
"""The second test for the batch's new player measures (CLAUDE.md, "Two tests for every new
measure"): does it repeat week to week and season to season?

- I48: garbage-time yards per game and the share of his yards that came in garbage time
  (passing, rushing, receiving), per player-game, regular season 2016-2024, players with any
  yards that game.
- I60: the games-played forecast's error isn't a measure; its input, the share of his team's games
  he played, is measured per player-season (season to season only).

Run from pcf/ (PCF_DATA_DIR set):
    python projects/crude-forecaster/explore/yardstick_batch/consistency_i48_i60.py > projects/crude-forecaster/explore/yardstick_batch/consistency.txt
"""

from __future__ import annotations

import polars as pl

from pcf.baselines.crude import inputs as I
from pcf.validation.consistency import consistency

c = pl.col
SEASONS = list(range(2016, 2025))


def main() -> None:
    print("I48: garbage-time yards, per player-game (regular season 2016-2024, games with any of that kind of yards). Week r: odd against even weeks; season r: one season's average against the next.")
    for target in ("passing", "rushing", "receiving"):
        g = I.player_game_garbage(target, SEASONS)
        g = g.filter((c("gt") + c("rest")) != 0).with_columns(
            share=c("gt") / (c("gt") + c("rest")).abs(),
            week=c("game_id").str.slice(5, 2).cast(pl.Int32),
        )
        t = consistency(g, ["gt", "share"], unit="gsis_id")
        for r in t.iter_rows(named=True):
            print(f"  {target:<10} {r['measure']:<6} week r {r['week_r']:+.2f} ({r['week_lo']:+.2f} to {r['week_hi']:+.2f}); season r {r['season_r']:+.2f} ({r['season_lo']:+.2f} to {r['season_hi']:+.2f}); {r['unit_seasons']} player-seasons; mean |x| {r['mean_abs']:.2f}; {r['verdict']}")
        print(f"  {target:<10} garbage time's share of all these yards: {100 * g['gt'].sum() / (g['gt'].sum() + g['rest'].sum()):.1f}%")
    pg, sched = I._played(None, SEASONS)
    games = sched.group_by("team", "season").agg(n=pl.len())
    rate = pg.with_columns(snap=(c("offense_snaps").fill_null(0) > 0).cast(pl.Float64)).group_by("gsis_id", "season").agg(
        played=c("snap").sum(), team=c("team").mode().first()).join(games, on=["team", "season"]).with_columns(
        rate=c("played") / c("n"), week=pl.lit(1))
    rate = rate.filter(c("played") > 0)
    two = rate.vstack(rate.with_columns(week=pl.lit(2)))
    t = consistency(two, ["rate"], unit="gsis_id")
    r = t.row(0, named=True)
    print(f"\nI60: share of his team's games he played (QB, RB, WR, TE with a snap that season): season r {r['season_r']:+.2f} ({r['season_lo']:+.2f} to {r['season_hi']:+.2f}), {r['season_pairs']} pairs; mean {r['mean_abs']:.2f}")


if __name__ == "__main__":
    main()
