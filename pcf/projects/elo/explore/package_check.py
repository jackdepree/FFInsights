"""Does the package (`pcf.experts.elo`) give what the exploration found, through the harness?

1. Per-moment features equal the bulk `features_history` on a sample of steps.
2. The walk-forward backtest (bulk features, 2016-2024) of each variant: mean miss against the
   close on the same games, coverage, log loss; the fitted coefficients of the last step.

Run from pcf/:
.venv/Scripts/python.exe projects/elo/explore/package_check.py
"""

# ruff: noqa: E501
from __future__ import annotations

import time

import polars as pl
from polars.testing import assert_frame_equal

from pcf.baselines.market import no_vig_home
from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.elo.model import EloMargin, EloTotal, EloWin
from pcf.validation import backtest
from pcf.validation.splits import steps

c = pl.col


def per_moment_matches(gw: Gateway) -> None:
    every = steps(gw.calendar, "in_season", range(2006, 2025), "saturday")
    sample = [
        s for s in every if (s.season, s.week) in {(2016, 1), (2019, 9), (2023, 2), (2024, 17)}
    ]
    ex = EloMargin()
    view = gw.view(END_OF_TIME, ex.cadence, ex.inputs)
    moments = pl.concat([s.games for s in every])
    bulk = ex.features_history(view, moments)
    for s in sample:
        for (moment,), frame in s.games.group_by("moment", maintain_order=True):
            one = ex.features(gw.view(moment, ex.cadence, ex.inputs), frame.drop("moment"))
            other = bulk.filter(c("game_id").is_in(one["game_id"].implode()))
            assert_frame_equal(
                one.sort("game_id"), other.sort("game_id"), check_exact=False, rel_tol=1e-9
            )
        print(f"  {s.season} week {s.week}: per moment = bulk ({s.games.height} games)")


def main() -> None:
    gw = Gateway()
    print("1. per-moment features against bulk")
    per_moment_matches(gw)
    lines = gw.source.part("game", "pregame").select(
        "game_id", "spread_line", "total_line", "home_moneyline", "away_moneyline"
    )
    print("\n2. backtests 2016-2024 (bulk features)")
    for ex in (EloMargin(), EloTotal(), EloWin()):
        t = time.perf_counter()
        bt = backtest.run(ex, gateway=gw, bulk=True)
        h = bt.scored.join(lines, on="game_id", how="left")
        if ex.kind == "amount":
            line = "spread_line" if ex.variant == "margin" else "total_line"
            print(
                f"  {ex.label():11s} miss {float((h['y'] - h['mean']).abs().mean()):.3f}, close "
                f"{float((h['y'] - h[line]).abs().mean()):.3f}, q10-q90 coverage "
                f"{float(h.select(((c('y') >= c('q10')) & (c('y') <= c('q90'))).mean()).item()):.1%}, "
                f"{h.height} games, {time.perf_counter() - t:.0f} s"
            )
        else:
            h = h.with_columns(m=no_vig_home(c("home_moneyline"), c("away_moneyline"))).drop_nulls(
                "m"
            )
            ll = lambda p, h=h: float(  # noqa: E731
                -(h["y"] * p.log() + (1 - h["y"]) * (1 - p).log()).mean()
            )
            print(
                f"  {ex.label():11s} log loss {ll(h['mean']):.4f}, close {ll(h['m']):.4f}, "
                f"{h.height} games, {time.perf_counter() - t:.0f} s"
            )
        last = max(bt.test)
        rows = bt.features.filter(c("step") < last)
        model, _ = backtest.fit_at(ex, rows.join(bt.targets, on="game_id"), bt.steps[last].at, 2024)
        print(f"    last step's fit: {ex.explain(model)['coefficients']}")


if __name__ == "__main__":
    main()
