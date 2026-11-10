"""The CEO's spot-check of F28 (2026-11-10): the matchup term as a feature in Elo's margin forecast.

Walks through:
1. **Reconcile with F26:** the same term on the same games, as a plain correlation with the margin's
   miss against the close and against Elo. If it's about F26's +0.029, the pipeline is the same.
2. **The weight over time:** c (points per unit of term) in each season's first window.
3. **Other scores:** the means' absolute and squared misses, with and without the term (the range
   score judges the whole range; the term might move only the middle).
4. **The alternative:** blends trained from 2015, the era where F26's signal lives, not 2010.
5. **The rows:** the games where the term moved Elo's forecast most, and the margin's miss by fifth
   of the term.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/spot_f28.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from feature_test import FIRST, KEYS, REPORT, _LineBlend, terms, walk_terms, week
from rematch import load

from pcf.baselines.market import MarketMargin
from pcf.data.gateway import Gateway
from pcf.experts.elo.model import EloMargin
from pcf.validation import backtest
from pcf.validation.nulls import no_noise

c = pl.col


def blend(line: str, with_term: bool, feats: pl.DataFrame, first: int):
    cols = (line, "term") if with_term else (line,)
    cls = type(f"S_{line}_{int(with_term)}_{first}", (_LineBlend, MarketMargin), {
        "variant": f"spot_{line}_{int(with_term)}_{first}", "cols": cols, "first_train": first, "__module__": __name__})  # fmt: skip
    cls.elo = feats
    return cls


def scored_means(bt) -> pl.DataFrame:
    return bt.history.select("game_id", "mean").join(
        bt.targets.select("game_id", "y"), on="game_id"
    )


def main() -> None:
    gw = Gateway()
    rng = np.random.default_rng(20261119)  # the same seed as F28, so the same term
    real = terms(walk_terms(load(), range(FIRST, 2025), rng))
    elo = backtest.run(EloMargin(), gw, list(range(FIRST, 2025)), bulk=True).history.select(
        "game_id", elo=c("mean")
    )
    feats = elo.join(real, on="game_id", how="inner")

    runs = {
        (k, f): backtest.run(blend("elo", k, feats, f)(), gw, REPORT)
        for k in (False, True)
        for f in (FIRST, 2015)
    }
    t = (week(scored_means(runs[(False, FIRST)])).rename({"mean": "m0"})
         .join(scored_means(runs[(True, FIRST)]).select("game_id", m1="mean"), on="game_id")
         .join(feats, on="game_id"))  # fmt: skip
    pre = backtest.run(MarketMargin(), gw, REPORT).features.select("game_id", "spread_line")
    t = t.join(pre, on="game_id", how="left")
    on = t.filter(c("term") != 0)

    print("== 1. Reconcile with F26 (games with a term, 2016-2024)")
    for lab, base in (
        ("the close", "spread_line"),
        ("Elo", "elo"),
        ("the Elo blend (no term)", "m0"),
    ):
        x = on.drop_nulls(base)
        print(
            f"   r(term, margin less {lab}): {np.corrcoef(x['term'], x['y'] - x[base])[0, 1]:+.4f} ({x.height:,} games)"
        )

    print("\n== 2. The weight on the term (points per unit), first window of each season")
    bt = runs[(True, FIRST)]
    pool = bt.features.join(bt.targets, on="game_id")
    sd = on["term"].std()
    for yr in REPORT:
        step = next(s for s in bt.steps if s.season == yr)
        model = backtest.fit_at(bt.expert, pool, step.at, yr)[0]
        cc = model["beta"][2]
        print(f"   {yr}: c {cc:+.1f} (so {cc * sd:+.2f} points per sd of the term)")

    print("\n== 3. The means' misses, with and without the term (2016-2024)")
    for lab, f in (("all weeks", pl.lit(True)), ("weeks 6+", c("wk") >= 6)):
        x = t.filter(f)
        e0, e1 = x["y"] - x["m0"], x["y"] - x["m1"]
        print(
            f"   {lab}: absolute {e0.abs().mean():.3f} to {e1.abs().mean():.3f}; squared {np.mean(e0.to_numpy() ** 2):.2f} to {np.mean(e1.to_numpy() ** 2):.2f}"
        )

    print("\n== 4. The alternative: blends trained from 2015, not 2010")
    sc = {k: runs[(k, 2015)].scored for k in (False, True)}
    common = sc[False].select(KEYS).join(sc[True].select(KEYS), on=KEYS)
    sc = {k: week(v.join(common, on=KEYS)) for k, v in sc.items()}
    for lab, f in (("all weeks", pl.lit(True)), ("weeks 6+", c("wk") >= 6)):
        a, b = sc[True].filter(f), sc[False].filter(f)
        verdict, comp = no_noise(a, b, KEYS)
        print(
            f"   {lab}: range score without {b['loss'].mean():.4f}, with {a['loss'].mean():.4f}; change {comp.diff:+.4f} ({comp.lo:+.4f} to {comp.hi:+.4f}): {verdict}"
        )

    print("\n== 5. The rows")
    rows = t.with_columns(move=c("m1") - c("m0"), miss0=c("y") - c("m0")).sort(
        c("move").abs(), descending=True
    )
    print("   the 12 games where the term moved Elo's blend most (points; + favours home):")
    for r in rows.head(12).iter_rows(named=True):
        better = abs(r["y"] - r["m1"]) < abs(r["y"] - r["m0"])
        print(
            f"      {r['game_id']}: blend {r['m0']:+.1f}, term moves it {r['move']:+.1f}; result {r['y']:+.0f} -> {'closer' if better else 'further'}"
        )
    closer = (
        rows.head(100).select(((c("y") - c("m1")).abs() < (c("y") - c("m0")).abs()).mean()).item()
    )
    print(f"   of the 100 biggest moves, closer to the result: {closer:.0%}")
    q = on.with_columns(fifth=c("term").qcut(5, labels=[str(i) for i in range(1, 6)]))
    by = (
        q.group_by("fifth")
        .agg(n=pl.len(), miss=(c("y") - c("m0")).mean(), close=(c("y") - c("spread_line")).mean())
        .sort("fifth")
    )
    print(
        "   by fifth of the term (1 favours away most, 5 home most): margin less the no-term blend, and less the close"
    )
    for r in by.iter_rows(named=True):
        print(f"      {r['fifth']}: {r['n']} games, {r['miss']:+.2f} and {r['close']:+.2f}")


if __name__ == "__main__":
    main()
