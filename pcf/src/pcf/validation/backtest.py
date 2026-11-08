"""The walk-forward backtest (docs/VALIDATION.md §1-2): one expert, every step in time order.

1. **Features:** for every step from the first training season on, the expert's features at each
   prediction moment, from a view at that moment (or its bulk `features_history`, if it has one
   and it has passed the leakage checks).
2. **Outcomes:** `expert.target` once, each with its `known_at`.
3. **Walk:** for each test step, fit on rows predicted before the step whose outcomes were known
   by then (recency-weighted), and predict the step's rows.

The features don't depend on the outcomes, so the signal test and the label check re-run only
step 3 (`walk`).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from pcf.config import get_config
from pcf.core.contract import OUTPUT_SCHEMA, SPIKE_PARTS, Expert, check_output
from pcf.core.log import get_logger
from pcf.data.gateway import END_OF_TIME, HISTORY, Gateway
from pcf.validation import scores
from pcf.validation.splits import Step, assert_walk_forward, step_table, steps

log = get_logger(__name__)
c = pl.col
HALF_LIFE = 4.0  # seasons (VALIDATION.md §1); None means no recency weighting
REFITS = ("step", "season")


class VaultClosed(PermissionError):
    """The backtest would score the vault season without opening it (VALIDATION.md §1)."""


@dataclass
class Backtest:
    """One backtest's pieces. `history` is the standard output plus `y`, `loss` and `readable`
    for the test steps; `features` and `targets` are kept for the nulls and the leakage checks."""

    expert: Expert
    steps: list[Step]
    test: list[int]
    features: pl.DataFrame
    targets: pl.DataFrame
    history: pl.DataFrame
    refit: str = "step"
    half_life: float | None = HALF_LIFE
    seconds: dict[str, float] = field(default_factory=dict)

    @property
    def scored(self) -> pl.DataFrame:
        return self.history.filter(c("y").is_not_null())


def test_seasons(open_vault: bool = False) -> list[int]:
    """The reported backtest's seasons (2016-2024 as of 2026), plus the vault if opened."""
    s = get_config().seasons
    last = s.vault if open_vault else s.vault - 1
    return list(range(s.first_report, last + 1))


def check_seasons(seasons: Sequence[int], open_vault: bool) -> None:
    s = get_config().seasons
    if any(x >= s.live for x in seasons):
        raise ValueError(f"season {s.live}+ is live: its test is the prediction ledger")
    if s.vault in seasons and not open_vault:
        raise VaultClosed(
            f"{s.vault} is the vault: pass open_vault=True once, at validation (it's logged)"
        )


def feature_history(
    expert: Expert, gateway: Gateway, all_steps: Sequence[Step], bulk: bool = False
) -> pl.DataFrame:
    """The expert's features for every step's rows, each from its own prediction moment, with
    `step` and `as_of`. `bulk` uses the expert's `features_history` instead."""
    games = step_table(all_steps)
    if bulk:
        view = gateway.view(END_OF_TIME, expert.cadence, expert.inputs)
        moments = pl.concat([s.games for s in all_steps])
        rows = expert.features_history(view, moments)  # type: ignore[attr-defined]
        return _with_steps(rows, games)
    out = []
    for step in all_steps:
        for (moment,), frame in step.games.group_by("moment", maintain_order=True):
            view = gateway.view(moment, expert.cadence, expert.inputs)
            out.append(expert.features(view, frame.drop("moment")))
    out = [f for f in out if f.height]
    if not out:
        raise ValueError(f"{expert.id}: no feature rows in any step")
    return _with_steps(pl.concat(out, how="diagonal_relaxed"), games)


def _with_steps(rows: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    rows = rows.drop([c_ for c_ in ("step", "as_of") if c_ in rows.columns])
    return rows.join(games, on="game_id", how="inner")


def targets(expert: Expert, gateway: Gateway) -> pl.DataFrame:
    """Every outcome known so far, with its `known_at`."""
    view = gateway.view(END_OF_TIME, expert.cadence, expert.inputs)
    out = expert.target(view)
    missing = {*expert.keys(), "y", "known_at"} - set(out.columns)
    if missing:
        raise ValueError(f"{expert.id}.target is missing {sorted(missing)}")
    return out.select(*expert.keys(), "y", "known_at").filter(c("y").is_not_null())


def shuffle_within_steps(pool: pl.DataFrame, seed: int) -> pl.DataFrame:
    """Outcomes shuffled within each step (week or season), keeping the data's structure: the
    signal test's null (VALIDATION.md §5)."""
    return pool.with_columns(y=c("y").shuffle(seed=seed).over("step"))


def fit_at(
    expert: Expert,
    pool: pl.DataFrame,
    at: datetime,
    season: int,
    half_life: float | None = HALF_LIFE,
) -> tuple[Any, datetime]:
    """Fit on the pool's rows predicted before `at` whose outcomes were known by then, weighted by
    age in seasons from `season`. Returns the model and its training cutoff (the latest outcome it
    saw). The walk and the live run (`pcf.validation.live`) both fit here."""
    moment = pl.lit(at).cast(pl.Datetime("us", "UTC"))
    # In a fixed order, so a refit on the same rows gives the same model to the last digit
    train = pool.filter((c("as_of") < moment) & (c("known_at") <= moment)).sort(
        "as_of", *expert.keys()
    )
    if train.is_empty():
        raise ValueError(f"{expert.id}: no training rows before {at}")
    assert_walk_forward(train, at)
    if half_life:
        age = season - c("step_season")
        train = train.with_columns(weight=0.5 ** (age / half_life))
    else:
        train = train.with_columns(weight=pl.lit(1.0))
    return expert.fit(train), train["known_at"].max()


def walk(
    expert: Expert,
    feats: pl.DataFrame,
    outcomes: pl.DataFrame,
    all_steps: Sequence[Step],
    test: Sequence[int],
    refit: str = "step",
    half_life: float | None = HALF_LIFE,
    train_transform: Callable[[pl.DataFrame], pl.DataFrame] | None = None,
) -> pl.DataFrame:
    """Fit and predict each test step. Returns the predictions (keys, mean, q10-q90, as_of, step,
    train_end). `train_transform` changes the training pool (the signal test shuffles it)."""
    if refit not in REFITS:
        raise ValueError(f"refit must be one of {REFITS}")
    keys = expert.keys()
    pool = feats.join(outcomes, on=keys, how="inner")
    if train_transform is not None:
        pool = train_transform(pool)
    by_index = {s.index: s for s in all_steps}
    out = []
    model: Any = None
    season_fit: int | None = None
    for index in test:
        step = by_index[index]
        if refit == "step" or season_fit != step.season:
            model, train_end = fit_at(expert, pool, step.at, step.season, half_life)
            season_fit = step.season
        rows = feats.filter(c("step") == index).sort(*keys)
        if rows.is_empty():
            continue
        pred = expert.predict(model, rows)
        out.append(
            pred.join(rows.select(*keys, "as_of", "step"), on=keys, how="left").with_columns(
                train_end=pl.lit(train_end).cast(pl.Datetime("us", "UTC"))
            )
        )
    return pl.concat(out, how="diagonal_relaxed")


def standard(
    expert: Expert, pred: pl.DataFrame, run_id: str = "", version: str = "backtest"
) -> pl.DataFrame:
    """Predictions in the standard output schema (the expert's keys first)."""
    out = pred.with_columns(
        quantity=pl.lit(expert.quantity),
        model=pl.lit(expert.label()),
        model_version=pl.lit(version),
        run_id=pl.lit(run_id),
        cadence=pl.lit(expert.cadence),
        **{q: c(q) if q in pred.columns else pl.lit(None) for q in ("q10", "q50", "q90")},
    )
    extra = SPIKE_PARTS if expert.spike else {}
    out = out.select(
        *expert.keys(),
        *(pl.col(k).cast(v) for k, v in {**OUTPUT_SCHEMA, **extra}.items()),
        "step",
    )
    check_output(out.drop("step"), expert.keys(), expert.kind)
    return out


def run(
    expert: Expert,
    gateway: Gateway | None = None,
    seasons: Sequence[int] | None = None,
    open_vault: bool = False,
    refit: str = "step",
    half_life: float | None = HALF_LIFE,
    bulk: bool = False,
    run_id: str = "",
) -> Backtest:
    """The expert's walk-forward backtest over `seasons` (default: the reported seasons after
    its first training season), training from `first_train` on (config's, or the expert's own
    if later)."""
    first = max(get_config().seasons.first_train, expert.first_train or 0)
    seasons = list(seasons or [s for s in test_seasons(open_vault) if s > first])
    check_seasons(seasons, open_vault)
    gateway = gateway or Gateway()
    every = steps(
        gateway.calendar,
        expert.cadence,
        range(min(first, min(seasons)), max(seasons) + 1),
        expert.run,
        expert.event,
    )
    test = [s.index for s in every if s.season in seasons]
    timing = {}
    start = time.perf_counter()
    feats = feature_history(expert, gateway, every, bulk=bulk)
    timing["features"] = time.perf_counter() - start
    start = time.perf_counter()
    outcomes = targets(expert, gateway)
    pred = walk(expert, feats, outcomes, every, test, refit, half_life)
    timing["walk"] = time.perf_counter() - start
    history = standard(expert, pred, run_id=run_id).join(
        outcomes.select(*expert.keys(), "y"), on=expert.keys(), how="left"
    )
    if expert.publishes:
        history = history.join(
            feats.select(*expert.keys(), *expert.publishes), on=expert.keys(), how="left"
        )
    history = scores.row_losses(history, expert.kind)
    log.info(
        "%s backtest: %d steps (%d tested), %d predictions; features %.1f s, walk %.1f s",
        expert.label(),
        len(every),
        len(test),
        history.height,
        timing["features"],
        timing["walk"],
    )
    return Backtest(expert, every, test, feats, outcomes, history, refit, half_life, timing)


def write_history(bt: Backtest, run_id: str, root: Path | None = None) -> Path:
    """Save the walk-forward history in the standard schema, with the expert's published features:
    outputs/<id>/<run_id>/history.parquet (the gateway reads registered versions from here), or
    outputs/<id>/<variant>/<run_id>/."""
    root = root or get_config().zone("outputs")
    path = root / bt.expert.id / bt.expert.variant / run_id / HISTORY
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = [*bt.expert.keys(), *OUTPUT_SCHEMA, *(SPIKE_PARTS if bt.expert.spike else ()),
            *bt.expert.publishes]  # fmt: skip
    bt.history.select(cols).with_columns(run_id=pl.lit(run_id)).write_parquet(path)
    return path
