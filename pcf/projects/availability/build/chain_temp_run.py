"""Availability: backlog idea I130, a narrower chain (REVIEW.md section 3, written before this ran).

First the doubt: is 91-94% coverage what a calibrated whole-number forecast with a spike at 0
must show? Read from the champions' saved histories: the share above q90 and below q10 (a
calibrated forecast: each at most 10%), and the chance of 1+ against the share with 1+.

Then the test as written: the chain with a temperature on its move chances (each row's chances
raised to 1/tau and renormalized), tau chosen on the last training season from GRID by range
score (the chain fit on the seasons before it), then the chain refit on every training season
with that tau; walked 2017-2024 on the saved features exactly like the champions (checks.walk).

Run from pcf/: <venv python> projects/availability/build/chain_temp_run.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.data.gateway import Gateway
from pcf.experts.availability import checks as K
from pcf.experts.availability import experts as X
from pcf.experts.availability import models as M
from pcf.validation import backtest, scores

c = pl.col
OUT = Path(__file__).with_name("chain_temp.txt")
GRID = (0.7, 0.85, 1.0, 1.2, 1.5)
KEYS = K.KEYS
lines: list[str] = []


def log(*parts) -> None:
    s = " ".join(str(p) for p in parts)
    print(s, flush=True)
    lines.append(s)


class TempChain(M.Chain):
    tau: float = 1.0

    def _move_probs(self, rows, s, d):
        p = super()._move_probs(rows, s, d)
        if self.tau != 1.0:
            p = np.power(p, 1.0 / self.tau)
            p = p / np.clip(p.sum(axis=1, keepdims=True), 1e-12, None)
        return p


def range_score(summary: dict, y: np.ndarray) -> float:
    total = 0.0
    for name, tau in (("q10", 0.1), ("q50", 0.5), ("q90", 0.9)):
        e = y - summary[name]
        total += np.maximum(tau * e, (tau - 1) * e).mean()
    return total / 3


def expert_for(horizon: str, chosen: list):
    base = X.WINDOWS[f"{horizon}_chain"]

    def fit(self, train):
        last = int(train["step_season"].max())
        inner = TempChain(X.NEXT_COLS, X.TRAITS).fit(train.filter(c("step_season") < last))
        held = train.filter((c("step_season") == last) & c("y").is_not_null())
        y = held["y"].to_numpy().astype(float)
        scored = {}
        for tau in GRID:
            inner.tau = tau
            scored[tau] = range_score(M.distribution_summary(inner.distribution(held)), y)
        best = min(scored, key=scored.get)
        chosen.append((last + 1, best, scored))
        full = TempChain(X.NEXT_COLS, X.TRAITS).fit(train)
        full.tau = best
        return full

    return type(f"{horizon.title()}ChainTemp", (base,), {"fit": fit, "variant": f"{horizon}_chain_temp", "__module__": __name__})()


def walk(expert, f, t) -> pl.DataFrame:
    gw = Gateway()
    every = K.all_steps(gw, max(K.SEASONS))
    test = [s.index for s in every if s.season in K.SEASONS]
    pred = backtest.walk(expert, f, t, every, test, K.REFIT, backtest.HALF_LIFE)
    hist = backtest.standard(expert, pred).join(t.select(*KEYS, "y"), on=KEYS, how="left")
    return scores.row_losses(hist, expert.kind)


def describe(name: str, d: pl.DataFrame) -> None:
    d = d.filter(c("y").is_not_null())
    r = d.select(
        loss=c("loss").mean(), cover=((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean(),
        below=(c("y") < c("q10")).mean(), above=(c("y") > c("q90")).mean(),
        q10_zero=(c("q10") == 0).mean(), p1=c("p_nonzero").mean(), y1=(c("y") > 0).mean(),
    ).row(0, named=True)
    log(f"  {name:<20} rows {d.height:,}  range score {r['loss']:.4f}  coverage {100 * r['cover']:.1f}%  below q10 {100 * r['below']:.1f}%  above q90 {100 * r['above']:.1f}%  "
        f"q10 = 0 on {100 * r['q10_zero']:.0f}%  chance of 1+ {100 * r['p1']:.1f}% vs actual {100 * r['y1']:.1f}%")


for horizon in ("next3", "rest"):
    champ = pl.read_parquet(K.cache_dir() / f"hist_{horizon}_chain.parquet")
    log(f"\n{horizon.upper()}: the doubt, from the champion's saved history (a calibrated forecast: below q10 and above q90 each at most 10%)")
    describe(f"{horizon}_chain", champ)
    f, t = K.family_rows(horizon)
    chosen: list = []
    hist = walk(expert_for(horizon, chosen), f, t)
    hist.write_parquet(K.cache_dir() / f"hist_{horizon}_chain_temp.parquet")
    log("  the temperature chosen each season (range score on the last training season by tau):")
    for season, best, sc in chosen:
        log(f"    {season}: tau {best} ({', '.join(f'{k}: {v:.4f}' for k, v in sc.items())})")
    describe(f"{horizon}_chain_temp", hist)
    cmp = K.versus(hist, champ, (f"{horizon}_chain_temp", f"{horizon}_chain"))
    log(f"  against the champion (range score): {K.pct(cmp, champ.filter(c('y').is_not_null())['loss'].mean())}")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
