"""The no-noise test (VALIDATION.md §5) for Elo: the closing line, with and without Elo's forecast.

The downstream target is the one the sides, totals and win products will use: the close, with
Elo blended in. It's the hardest place for Elo to add anything, since the market already knows
everything public. Expectation (written before running): neutral. Elo is 0.3 points behind the
close and mostly agrees with it, so its weight in a blend should be small and the change within
a few hundredths of a point either way.

- **Without:** the close as it is (`baselines` market variants).
- **Recalibrated close:** a + b x the close, fit in each training window. Shows how much of any
  gain is only recalibrating the line, not Elo.
- **With:** a + b x the close + c x Elo's forecast (win: a logistic curve on both log-odds).

Elo's forecasts come from its own walk-forward history (rule e), made here from 2010 so the blend
has training rows; every row was predicted by a model trained only on earlier weeks. All three
train from 2010 and are scored 2016-2024, compared by whole weeks.

Run from pcf/: .venv/Scripts/python.exe projects/elo/explore/no_noise.py
"""

# ruff: noqa: E501
from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

from pcf.baselines.common import fit_offsets, with_ranges
from pcf.baselines.market import MarketMargin, MarketTotal, MarketWin, no_vig_home
from pcf.data.gateway import Gateway
from pcf.experts.elo.model import EloMargin, EloTotal, EloWin
from pcf.validation import backtest
from pcf.validation.nulls import no_noise

c = pl.col
FIRST = 2010
REPORT = list(range(2016, 2025))
KEYS = ["game_id"]


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


class _Blend:
    """Mixed into a market variant: its line plus (optionally) Elo's forecast, refit per window."""

    first_train = FIRST
    elo: ClassVar[pl.DataFrame | None] = None  # game_id, elo
    cols: ClassVar[tuple[str, ...]]

    def features(self, view, games):
        rows = super().features(view, games)
        if self.elo is not None:
            rows = rows.join(self.elo, on="game_id", how="inner")
        return rows

    def _x(self, rows: pl.DataFrame) -> np.ndarray:
        x = rows.select(self.cols).to_numpy().astype(float)
        return np.column_stack([np.ones(len(x)), x])


class _LineBlend(_Blend):
    def fit(self, train: pl.DataFrame) -> dict[str, Any]:
        train = train.drop_nulls([*self.cols, "y"])
        x, y, w = self._x(train), train["y"].to_numpy(), train["weight"].to_numpy()
        sw = np.sqrt(w)
        beta = np.linalg.lstsq(x * sw[:, None], y * sw, rcond=None)[0]
        resid = train.select("weight").with_columns(resid=pl.Series(y - x @ beta))
        return {"beta": beta, "offsets": fit_offsets(resid)}

    def predict(self, model, rows):
        rows = rows.drop_nulls(list(self.cols))
        out = rows.select("game_id").with_columns(mean=pl.Series(self._x(rows) @ model["beta"]))
        return with_ranges(out, model["offsets"])

    def explain(self, model):
        return {"beta": [round(float(b), 3) for b in model["beta"]]}


class _WinBlend(_Blend):
    def _frame(self, rows):
        rows = rows.drop_nulls(["home_moneyline", "away_moneyline"])
        rows = rows.with_columns(close=no_vig_home(c("home_moneyline"), c("away_moneyline")))
        x = [_logit(rows["close"].to_numpy())]
        if "elo" in self.cols:
            x.append(_logit(rows["elo"].to_numpy()))
        return rows, np.column_stack(x)

    def fit(self, train):
        train = train.drop_nulls("y")
        train, x = self._frame(train)
        return LogisticRegression(C=1e6, max_iter=1000).fit(
            x, train["y"].to_numpy().astype(int), sample_weight=train["weight"].to_numpy()
        )

    def predict(self, model, rows):
        rows, x = self._frame(rows)
        return rows.select("game_id").with_columns(mean=pl.Series(model.predict_proba(x)[:, 1]))

    def explain(self, model):
        return {"intercept": float(model.intercept_[0]), "coef": model.coef_[0].round(3).tolist()}


def _variants(market, blend, line: str):
    base = type(f"Recal{market.__name__}", (blend, market), {
        "variant": f"{market.variant}_recal", "cols": (line,), "__module__": __name__})  # fmt: skip
    plus = type(f"Elo{market.__name__}", (blend, market), {
        "variant": f"{market.variant}_elo", "cols": (line, "elo"), "__module__": __name__})  # fmt: skip
    plain = type(f"Plain{market.__name__}", (market,), {"first_train": FIRST, "__module__": __name__})
    return plain, base, plus


def main() -> None:
    gw = Gateway()
    cases = [
        (EloMargin, MarketMargin, _LineBlend, "spread_line"),
        (EloTotal, MarketTotal, _LineBlend, "total_line"),
        (EloWin, MarketWin, _WinBlend, "close"),
    ]
    for expert, market, blend, line in cases:
        hist = backtest.run(expert(), gw, list(range(FIRST, 2025)), bulk=True).history
        elo = hist.select("game_id", elo=c("mean"))
        plain, recal, plus = _variants(market, blend, line)
        plus.elo = elo
        recal.elo = elo  # the same games as `plus`
        runs = {}
        for cls in (plain, recal, plus):
            bt = backtest.run(cls(), gw, REPORT)
            runs[cls.__name__] = bt
        last = backtest.fit_at(plus(), runs[plus.__name__].features.join(
            runs[plus.__name__].targets, on="game_id"), runs[plus.__name__].steps[max(runs[plus.__name__].test)].at, 2024)[0]  # fmt: skip
        s = {k: v.scored for k, v in runs.items()}
        common = s[plain.__name__].select(KEYS).join(s[plus.__name__].select(KEYS), on=KEYS)
        s = {k: v.join(common, on=KEYS) for k, v in s.items()}
        print(f"\n== {expert.variant}: the close with and without Elo, {REPORT[0]}-{REPORT[-1]}, {common.height:,} games")
        for k, v in s.items():
            print(f"   {k:<22} loss {v['loss'].mean():.4f}, readable {v['readable'].mean():.4f}")
        verdict, comp = no_noise(s[plus.__name__], s[plain.__name__], KEYS)
        print(f"   with Elo - the close: {comp.diff:+.4f} ({comp.lo:+.4f} to {comp.hi:+.4f}), {comp.blocks} weeks: {verdict}")
        verdict2, comp2 = no_noise(s[plus.__name__], s[recal.__name__], KEYS)
        print(f"   with Elo - recalibrated close: {comp2.diff:+.4f} ({comp2.lo:+.4f} to {comp2.hi:+.4f}): {verdict2}")
        print(f"   last window's blend: {plus().explain(last)}")


if __name__ == "__main__":
    main()
