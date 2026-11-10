"""The learned matchup term as a feature in the strength model (I26; the CEO, 2026-11-09: "Try it
as a feature in the team-strength model").

The strength model in use is Elo (the team-strength composite is still an idea). The test is Elo's
own no-noise test (VALIDATION.md §5; projects/elo/explore/no_noise.py), with the matchup term added:
- **Feature:** each game's term = the home offense's matchup part less the away offense's, from F26's
  walk-forward (that season's earlier games only, k 2, λ 1, from week 6; 0 before week 6). It's a
  walk-forward history by construction (rule e).
- **A, the strength model:** next game's margin from a + b x Elo's forecast, against a + b x Elo +
  c x the term. Elo's forecasts are its own walk-forward history from 2010.
- **B, the close:** a + b x the close, against a + b x the close + c x the term.
- Both blends train from 2010, refit each week, and are scored 2016-2024 by the harness's range
  score; compared by whole weeks (VALIDATION.md §4). Weeks 6+ (where the term can act) are reported
  apart.
- **Signal:** the same term built from shuffled pairings (defenses swapped within the week), 20
  times, through the same blend; the real term must beat all 20.
- **Expected before running:** neutral. +0.37 points per sd (F26) is tiny next to a margin's spread
  (sd about 13), so the change should be a few hundredths of a point at most.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/feature_test.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "elo" / "explore"))
from no_noise import _LineBlend  # noqa: E402
from rematch import load  # noqa: E402
from walkforward import run as walk_terms  # noqa: E402

from pcf.baselines.market import MarketMargin  # noqa: E402
from pcf.data.gateway import Gateway  # noqa: E402
from pcf.data.tables.store import read_part  # noqa: E402
from pcf.experts.elo.model import EloMargin  # noqa: E402
from pcf.validation import backtest  # noqa: E402
from pcf.validation.nulls import no_noise  # noqa: E402

c = pl.col
FIRST = 2010
REPORT = list(range(2016, 2025))
SHUFFLES = int(sys.argv[1]) if len(sys.argv) > 1 else 20  # a smaller number only for a smoke test
KEYS = ["game_id"]


def terms(parts: pl.DataFrame) -> pl.DataFrame:
    """Per game: home offense's part less the away offense's (0 where either isn't forecast)."""
    sch = read_part("game", "schedule").select("game_id", "home_team", "away_team").collect()
    g = sch.join(parts.select("game_id", home_team="off", ph="part"), on=["game_id", "home_team"], how="left").join(
        parts.select("game_id", away_team="off", pa="part"), on=["game_id", "away_team"], how="left")  # fmt: skip
    return g.select("game_id", term=(c("ph") - c("pa")).fill_null(0.0))


def blend(line: str, with_term: bool, feats: pl.DataFrame):
    cols = (line, "term") if with_term else (line,)
    cls = type(f"B_{line}_{int(with_term)}", (_LineBlend, MarketMargin), {
        "variant": f"margin_{line}_{int(with_term)}", "cols": cols, "first_train": FIRST, "__module__": __name__})  # fmt: skip
    cls.elo = feats
    return cls


def week(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(wk=c("game_id").str.split("_").list.get(1).cast(pl.Int32))


def main() -> None:
    gw = Gateway()
    rng = np.random.default_rng(20261119)
    s = load()
    seasons = range(FIRST, 2025)
    real = terms(walk_terms(s, seasons, rng))
    fakes = [terms(walk_terms(s, seasons, rng, shuffle=True)) for _ in range(SHUFFLES)]
    elo = backtest.run(EloMargin(), gw, list(seasons), bulk=True).history.select(
        "game_id", elo=c("mean")
    )
    print(
        f"terms: {real.filter(c('term') != 0).height:,} games with a term; Elo history {elo.height:,} games"
    )
    for name, line in (("A. Elo", "elo"), ("B. the close", "spread_line")):
        feats = elo.join(real, on="game_id", how="inner")
        runs = {k: backtest.run(blend(line, k, feats)(), gw, REPORT) for k in (False, True)}
        sc = {k: v.scored for k, v in runs.items()}
        common = sc[False].select(KEYS).join(sc[True].select(KEYS), on=KEYS)
        sc = {k: week(v.join(common, on=KEYS)) for k, v in sc.items()}
        print(
            f"\n== {name}: next game's margin with and without the matchup term, {REPORT[0]}-{REPORT[-1]}, {common.height:,} games"
        )
        for lab, f in (("all weeks", pl.lit(True)), ("weeks 6+", c("wk") >= 6)):
            a, b = sc[True].filter(f), sc[False].filter(f)
            verdict, comp = no_noise(a, b, KEYS)
            print(
                f"   {lab}: loss without {b['loss'].mean():.4f}, with {a['loss'].mean():.4f}; change {comp.diff:+.4f} ({comp.lo:+.4f} to {comp.hi:+.4f}), {comp.blocks} weeks: {verdict}"
            )
        last = runs[True]
        model = backtest.fit_at(
            last.expert,
            last.features.join(last.targets, on="game_id"),
            last.steps[max(last.test)].at,
            2024,
        )[0]
        print(f"   last window's blend (a, b, c per unit of term): {last.expert.explain(model)}")
        real_loss = sc[True]["loss"].mean()
        null = []
        for fk in fakes:
            ff = elo.join(fk, on="game_id", how="inner")
            bt = backtest.run(blend(line, True, ff)(), gw, REPORT).scored.join(common, on=KEYS)
            null.append(bt["loss"].mean())
        null = np.array(null)
        print(
            f"   signal: real term's loss {real_loss:.4f}; shuffled-pairing terms mean {null.mean():.4f} (best {null.min():.4f}); real beats {np.sum(real_loss < null)} of {SHUFFLES}"
        )


if __name__ == "__main__":
    main()
