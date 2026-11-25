"""The build's walks (decision 0047): every variant scored on one saved feature history.

`build_features` runs the harness's per-moment features once (every roster_week row, 2016-2024,
each from a view at its own Saturday or Thursday run) and the outcomes of every family, and
saves them. `family_rows` turns the saved rows into one family's rows exactly as that family's
`features` does at a moment (the same filters; participation's columns from its pinned saved
history, which is what the gateway would show). `walk` fits and predicts one variant with the
harness's own `backtest.walk`, and `versus` compares two on their shared rows (VALIDATION §4).
The harness's full validation (`run forecast`) is kept for the shipped variants.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway, stored_outputs
from pcf.experts.availability import experts as X
from pcf.experts.availability import targets as T
from pcf.experts.availability.common import FIRST_TRAIN, INPUTS, SKILL
from pcf.validation import backtest, scores
from pcf.validation.compare import Comparison, compare
from pcf.validation.splits import steps

c = pl.col
SEASONS = list(range(2017, 2025))
REFIT = "season"
KEYS = ["gsis_id", "game_id"]


def cache_dir() -> Path:
    path = get_config().zone("interim") / "availability" / "build"
    path.mkdir(parents=True, exist_ok=True)
    return path


def all_steps(gateway: Gateway, last: int = 2024):
    return steps(gateway.calendar, "in_season", range(FIRST_TRAIN, last + 1), "saturday")


def build_features(last: int = 2024) -> None:
    """The per-moment features and every family's outcomes, saved in the cache."""
    import time

    t0 = time.time()
    gw = Gateway()
    every = all_steps(gw, last)
    feats = backtest.feature_history(X.RestTable(), gw, every)
    print(f"features {feats.shape} in {time.time() - t0:.0f}s", flush=True)
    view = gw.view(END_OF_TIME, "in_season", {**INPUTS, "player_game": INPUTS["player_game"]})
    for name, frame in {
        "next": T.next_absent(view),
        "next3": T.window_absent(view, 3),
        "rest": T.window_absent(view, None),
        "active": T.active(view),
        "kept": T.side_share(view),
    }.items():
        backtest.save_features(SimpleNamespace(features=feats, targets=frame), cache_dir() / name)


def _history(name: str) -> pl.DataFrame:
    project, _, variant = name.partition("/")
    del project, variant
    return stored_outputs(name, 1)


def family_rows(family: str) -> tuple[pl.DataFrame, pl.DataFrame]:
    """A family's features and outcomes from the saved history."""
    f, t = backtest.load_features(cache_dir() / family)
    if family == "next":
        f = f.filter(~c("reserve"))
    elif family == "next3":
        f = f.with_columns(n_window=pl.min_horizontal(c("left"), pl.lit(3.0)))
    elif family == "rest":
        f = f.with_columns(n_window=c("left"))
    elif family == "active":
        pa = _history("participation/active").select(*KEYS, pa_as_of="as_of", pa="mean")
        f = f.filter(c("position").is_in(list(SKILL)) & ~c("reserve")).join(
            pa, on=KEYS, how="inner"
        ).filter(c("pa_as_of") <= c("as_of")).drop("pa_as_of")
        f = f.with_columns(logit_pa=pl.Series(X._logit(f["pa"].to_numpy())))
    elif family == "kept":
        tw = _history("participation/trees_week").select(
            *KEYS, ps_as_of="as_of", ps="if_nonzero_mean", ps10="if_nonzero_q10", ps50="if_nonzero_q50",
            ps90="if_nonzero_q90",
        )  # fmt: skip
        f = f.filter(c("position").is_in(list(SKILL)) & c("state").is_in(["l", "o"])).join(
            tw, on=KEYS, how="inner"
        ).filter(c("ps_as_of") <= c("as_of")).drop("ps_as_of")
    return f, t


def walk(variant: str, feats: pl.DataFrame, targets: pl.DataFrame,
         seasons: list[int] = SEASONS, train_transform=None) -> pl.DataFrame:  # fmt: skip
    """One variant's walk-forward history on saved rows, scored row by row."""
    cls = X.VARIANTS[variant]
    expert = cls()
    gw = Gateway()
    every = all_steps(gw, max(seasons))
    test = [s.index for s in every if s.season in seasons]
    pred = backtest.walk(expert, feats, targets, every, test, REFIT, backtest.HALF_LIFE,
                         train_transform)  # fmt: skip
    hist = backtest.standard(expert, pred).join(targets.select(*KEYS, "y"), on=KEYS, how="left")
    hist = scores.row_losses(hist, expert.kind)
    keep = [*KEYS, "step", "as_of", "mean", "q10", "q50", "q90", "y", "loss", "readable"]
    if expert.spike:
        keep += list(X.SPIKE)
    return hist.select(keep).join(
        feats.select(*KEYS, "grp", "state", "position", "season", "n_window" if "n_window" in feats.columns else "left"),
        on=KEYS, how="left",
    )  # fmt: skip


def versus(a: pl.DataFrame, b: pl.DataFrame, names: tuple[str, str],
           rows: pl.DataFrame | None = None) -> Comparison:  # fmt: skip
    """a against b on their shared scored rows (optionally only `rows`' keys)."""
    if rows is not None:
        a = a.join(rows.select(KEYS), on=KEYS, how="semi")
    return compare(a.filter(c("y").is_not_null()), b.filter(c("y").is_not_null()), KEYS,
                   "step", names)  # fmt: skip


def pct(cmp: Comparison, base_loss: float) -> str:
    """A comparison as a share of the second model's loss removed (positive: a is better)."""
    f = lambda v: -100 * v / base_loss  # noqa: E731
    return f"{f(cmp.diff):+.2f}% ({f(cmp.hi):+.2f} to {f(cmp.lo):+.2f}) {cmp.verdict} [{cmp.rows} rows]"


def calibration_slope(p: np.ndarray, y: np.ndarray) -> float:
    """The slope of y on logit(p) (1 is calibrated; under 1 overconfident)."""
    from sklearn.linear_model import LogisticRegression

    lp = X._logit(p).reshape(-1, 1)
    m = LogisticRegression(C=1e6, max_iter=2000).fit(lp, y.astype(int))
    return float(m.coef_[0, 0])


def calibration_error(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """The average gap between predicted and actual rates over 10 bins of prediction, in
    points, weighted by rows (VALIDATION §7)."""
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, bins - 1)
    gap = 0.0
    for b in range(bins):
        on = idx == b
        if on.any():
            gap += on.sum() * abs(p[on].mean() - y[on].mean())
    return 100 * gap / len(p)
