"""IDEAS I151 (retro 4's dream, 2026-11-25): hidden injuries read from usage.

Discovery only. Saved walk-forward histories, 2016-2024 (the 2025 vault is left out):
participation's `trees_week` (snap share next game) and availability's `next_logit` (the chance
of a health absence next game, read from the report, his history, proneness and exposure).

A game is flagged when a player played (snap share 5%+) but far below participation's forecast:
his miss is in the bottom 2.5% of played rows' misses with a similar forecast (forecast tenths).
The question: is his next game's absence higher than `next_logit` says?

- The gap: flagged rows' (absent minus forecast) against all other rows', whole weeks resampled.
- Pays: a walk-forward recalibration of `next_logit` (logistic on its own logit) with and
  without the flag, by season; the log loss gained, weeks resampled.

Claude's odds, written before the run (IDEAS.md, I151): 50% the absence rate beats the chain's
forecast clearly; 30% it pays on games played. (This run uses the next-game logistic, the
champion for next game; the chain's next-3 forecast is the bet's wording, checked as a side.)

Run from pcf/:  python projects/retro/explore/retro4_i151_hidden_injuries.py > projects/retro/explore/retro4_i151_hidden_injuries.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

from pcf.config import get_config
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.validation.backtest import targets

c = pl.col
LAST = "2025"
DRAWS = 2000
RNG = np.random.default_rng(151)


def history(project, variant, gateway):
    expert = find(project, variant)()
    folder = get_config().zone("outputs") / project / variant
    runs = sorted((p for p in folder.iterdir() if (p / "history.parquet").exists()),
                  key=lambda p: p.stat().st_mtime)  # fmt: skip
    for run in reversed(runs):
        h = pl.read_parquet(run / "history.parquet")
        if h["game_id"].min() < "2024":
            break
    keys = list(expert.keys())
    y = targets(expert, gateway).select(*keys, "y")
    return h.filter(c("game_id") < LAST).join(y, on=keys).select(*keys, "mean", "y")


def boot_gap(week, flag, resid):
    _, wk = np.unique(week, return_inverse=True)
    n = wk.max() + 1
    s1 = np.bincount(wk, resid * flag, n)
    n1 = np.bincount(wk, flag.astype(float), n)
    s0 = np.bincount(wk, resid * ~flag, n)
    n0 = np.bincount(wk, (~flag).astype(float), n)
    d = RNG.integers(0, n, (DRAWS, n))
    g = s1[d].sum(1) / n1[d].sum(1) - s0[d].sum(1) / n0[d].sum(1)
    point = s1.sum() / n1.sum() - s0.sum() / n0.sum()
    return point, np.quantile(g, 0.05), np.quantile(g, 0.95)


def main() -> None:
    gw = Gateway()
    part = history("participation", "trees_week", gw).rename({"mean": "snap_f", "y": "snap"})
    nxt = history("availability", "next_logit", gw).rename({"mean": "p_abs", "y": "absent"})
    print(f"participation rows {part.height:,}; availability rows {nxt.height:,}")

    part = part.with_columns(miss=c("snap") - c("snap_f"),
                             tenth=(c("snap_f").rank() / pl.len() * 10).floor().clip(0, 9))  # fmt: skip
    cut = part.filter(c("snap") >= 0.05).group_by("tenth").agg(cut=c("miss").quantile(0.025))
    part = part.join(cut, on="tenth").with_columns(
        flag=(c("snap") >= 0.05) & (c("miss") <= c("cut"))
    )
    print(f"flagged games: {part['flag'].sum():,} of {part.filter(c('snap') >= 0.05).height:,} played")

    # each player's next game on availability's rows
    nxt = nxt.sort("gsis_id", "game_id").with_columns(prev_game=c("game_id").shift(1).over("gsis_id"))
    d = nxt.join(part.select("gsis_id", c("game_id").alias("prev_game"), "flag", "snap", "snap_f"),
                 on=["gsis_id", "prev_game"], how="inner")  # fmt: skip
    d = d.with_columns(season=c("game_id").str.slice(0, 4).cast(pl.Int32),
                       week=c("game_id").str.slice(0, 7), resid=c("absent") - c("p_abs"))  # fmt: skip
    f = d["flag"].to_numpy()
    print(f"rows with a previous game on participation's rows: {d.height:,}; flagged {f.sum():,}\n")

    fl, ot = d.filter(c("flag")), d.filter(~c("flag"))
    print("Next game's health absence:")
    print(f"  flagged: absent {fl['absent'].mean():.2%}, forecast {fl['p_abs'].mean():.2%}")
    print(f"  others:  absent {ot['absent'].mean():.2%}, forecast {ot['p_abs'].mean():.2%}")
    pt, lo, hi = boot_gap(d["week"].to_numpy(), f, d["resid"].to_numpy())
    print(f"  gap (flagged's miss less the others'): {pt:+.2%} ({lo:+.2%} to {hi:+.2%}), points of absence chance")

    # by how far below: the bottom 1% and the 1-2.5% band
    d = d.with_columns(deep=c("snap") - c("snap_f"))
    print("\nBy season (flagged: absent less forecast):")
    for s, g in sorted(d.filter(c("flag")).group_by("season"), key=lambda t: t[0][0]):
        print(f"  {s[0]}: {g['resid'].mean():+.2%} on {g.height:,} rows")

    # pays: walk-forward logistic recalibration with and without the flag
    logit = np.log(np.clip(d["p_abs"].to_numpy(), 1e-5, 1 - 1e-5) / (1 - np.clip(d["p_abs"].to_numpy(), 1e-5, 1 - 1e-5)))
    y = d["absent"].to_numpy().astype(int)
    season = d["season"].to_numpy()
    seasons = np.unique(season)
    ll0 = np.zeros(len(y))
    ll1 = np.zeros(len(y))
    llr = np.zeros(len(y))
    p_raw = np.clip(d["p_abs"].to_numpy(), 1e-5, 1 - 1e-5)
    test = np.isin(season, seasons[2:])
    for s in seasons[2:]:
        tr, te = season < s, season == s
        for x, out in ((logit[:, None], ll0), (np.column_stack([logit, f]), ll1)):
            m = LogisticRegression(C=1e6, max_iter=1000).fit(x[tr], y[tr])
            p = np.clip(m.predict_proba(x[te])[:, 1], 1e-6, 1 - 1e-6)
            out[te] = -(y[te] * np.log(p) + (1 - y[te]) * np.log(1 - p))
        llr[te] = -(y[te] * np.log(p_raw[te]) + (1 - y[te]) * np.log(1 - p_raw[te]))
    _, wk = np.unique(d["week"].to_numpy()[test], return_inverse=True)
    n = wk.max() + 1
    a0 = np.bincount(wk, ll0[test], n)
    a1 = np.bincount(wk, ll1[test], n)
    dr = RNG.integers(0, n, (DRAWS, n))
    g = 1 - a1[dr].sum(1) / a0[dr].sum(1)
    print(f"\nPays (walk-forward, {seasons[2]}-{seasons[-1]}, {test.sum():,} rows): the flag beside next_logit's own logit")
    print(f"  log loss: recalibrated alone {ll0[test].mean():.5f}; with the flag {ll1[test].mean():.5f}; raw {llr[test].mean():.5f}")
    print(f"  gain: {1 - a1.sum() / a0.sum():+.3%} of the log loss ({np.quantile(g, 0.05):+.3%} to {np.quantile(g, 0.95):+.3%})")
    print(f"  on flagged rows only: {1 - ll1[test & f].sum() / ll0[test & f].sum():+.2%}")


if __name__ == "__main__":
    main()
