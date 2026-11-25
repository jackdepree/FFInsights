# ruff: noqa: E501, B023
"""Retro 4, group A: I137, the yardstick's rushing floor (the CEO, 2026-11-25: "Keep i137 for the next retro").

I137 (Claude, roles' build, 2026-11-25; odds before any test: 55% that the copies' cost falls under -0.15%; 70% that
no input already counted loses its verdict): on the rushing rest-of-season board, 19 signal-free copies of six
player-constant inputs cost about -0.5% on average (receiving about -0.1%). Guess: the lasso's penalty, picked on the
latest 20% of each training window.

What the first look found (before this script): the penalty grid is np.geomspace(1, 1e-3) on standardized features,
but the target isn't standardized (rest-of-season rushing yards per game, SD about 27), so the largest penalty is
small and the picks land between 0.016 and 0.63: nearly ordinary least squares, where every noise column gets a weight.

Three penalty rules, each applied to both the base (crude + participation) and the forecast with the input:
- **now:** the yardstick's rule (the grid as is, the lowest error on the latest 20%);
- **scaled:** the same grid times the target's SD in the window (the same as standardizing y);
- **scaled, one SE:** the scaled grid, the largest penalty within one standard error of the lowest holdout error.
For each: the five inputs roles' spot-check scored (build2_rushing_copies.py), each with 19 copies shuffled within
season and group. "Counts" = interval above 0 and beats all 19 copies (test 4's rule).
The vault (2025) isn't read. Exploration only: the yardstick isn't changed here.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro4_i137_floor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parents[2] / "roles-archetypes" / "explore"))
import build2_common as bc  # noqa: E402

from pcf.baselines.crude import fitting as F  # noqa: E402
from pcf.baselines.crude import yardstick as Y  # noqa: E402
from pcf.baselines.lasso import ALPHAS, fit_lasso, predict_lasso, weighted_mse  # noqa: E402

c = pl.col
OUT = Path(__file__).with_suffix(".txt")
lines: list[str] = []


def say(*t):
    s = " ".join(str(x) for x in t)
    print(s, flush=True)
    lines.append(s)


ORIG = F.pick_alpha
PICKS: list[float] = []


def scaled(x, y, w, cut, one_se=False):
    grid = ALPHAS * float(np.std(y))
    early = fit_lasso(x[:cut], y[:cut], w[:cut], grid)
    errs, ses = [], []
    for m in early:
        e = (predict_lasso(m, x[cut:]) - y[cut:]) ** 2
        ww = w[cut:] / w[cut:].sum()
        mu = float((e * ww).sum())
        errs.append(mu)
        ses.append(float(np.sqrt(((e - mu) ** 2 * ww).sum() / len(e))))
    i = int(np.argmin(errs))
    if one_se:
        ok = [k for k in range(len(grid)) if errs[k] <= errs[i] + ses[i]]
        i = min(ok, key=lambda k: -grid[k])  # the largest penalty inside one SE
    return float(grid[i])


RULES = {
    "now": lambda x, y, w, cut: ORIG(x, y, w, cut),
    "scaled": lambda x, y, w, cut: scaled(x, y, w, cut),
    "scaled, one SE": lambda x, y, w, cut: scaled(x, y, w, cut, one_se=True),
}
assert weighted_mse  # the yardstick's own scorer, imported so the rule matches its definition

prior = bc.offense_prior()
Z, T = bc.Z, bc.T_OFF
prior = prior.with_columns(
    is_early=(c("role") == "early-down back").cast(pl.Float64), is_pdown=(c("role") == "passing-down back").cast(pl.Float64),
    **{f"b{z}": pl.when(c("coarse") != "back").then(None).otherwise(c(z)) for z in Z})
INPUTS = {"coordinates": Z, "role table": T, "coordinates, non-backs' prior missing": [f"b{z}" for z in Z],
          "fine back roles as 2 dummies": ["is_early", "is_pdown"], "carries per run snap alone": ["t2_car_per_run"]}


def logged(rule):
    def f(x, y, w, cut):
        a = rule(x, y, w, cut)
        PICKS.append(a / float(np.std(y)))
        return a
    return f


for target in ("rushing", "receiving"):
    board = Y.load_board(target, "rest")
    keys = board.keys
    rows = board.features.select(*keys, "season")
    say(f"\n== {target} rest-of-season board, beside participation ({board.features.height:,} rows)")
    for rname, rule in RULES.items():
        F.pick_alpha = logged(rule)
        board.preds.clear()
        PICKS.clear()
        crude = board.forecast(("participation",))
        say(f"  -- rule: {rname}; the base's penalties over the target's SD by season: " + ", ".join(f"{p:.4f}" for p in PICKS))

        def gain(cols, pr):
            frame = rows.join(pr.select("gsis_id", "season", *cols), on=["gsis_id", "season"], how="left").drop("season")
            feats = board.features.join(frame, on=keys, how="left").with_columns(c(x).fill_null(c(x).median()) for x in cols)
            return Y.gain(board.forecast(("participation",), extra=list(cols), feats=feats), crude, keys)

        for name, cols in INPUTS.items():
            g = gain(cols, prior)
            cps = np.array([gain(cols, bc.shuffled(prior, cols, 9000 + k)).share for k in range(19)])
            counts = g.lo > 0 and g.share > cps.max()
            say(f"    {name:40}: {100 * g.share:+.2f}% (90% {100 * g.lo:+.2f} to {100 * g.hi:+.2f}); copies mean {100 * cps.mean():+.2f}% "
                f"({100 * cps.min():+.2f} to {100 * cps.max():+.2f}); beats {int((g.share > cps).sum())} of 19; counts: {counts}")
F.pick_alpha = ORIG
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
