"""One validation run (docs/VALIDATION.md): the backtest, the baselines, the signal test, the
calibration and coverage, the leakage suite and the sanity rules, gathered for the scorecard.

    v = validate(Expert(), baselines=[Baseline()])
    record(v)   # inside tracking.attempt(...): metrics, checks, history and the scorecard

`pcf backtest <id>` does both.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.core.contract import Expert
from pcf.core.log import get_logger
from pcf.data.gateway import Gateway
from pcf.validation import backtest, calibration, leakage, nulls, sanity, scores
from pcf.validation.compare import Comparison, compare

log = get_logger(__name__)
c = pl.col
SCORECARD = "scorecard.html"


@dataclass
class Validation:
    bt: backtest.Backtest
    baselines: dict[str, pl.DataFrame]
    comparisons: dict[str, Comparison]
    signal: nulls.SignalTest | None
    no_noise: tuple[str, Comparison] | None
    calibration: dict
    checks: list[leakage.Check]
    sanity: pl.DataFrame
    review: tuple[pl.DataFrame, pl.DataFrame]
    seasons: list[int]
    vault_opened: bool
    versions_tried: int | None = None
    made: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def passed(self) -> bool:
        """Every blocking check passed (what `tracking.register` requires)."""
        return all(ch.passed for ch in self.checks if ch.blocking)


def baseline_history(bt: backtest.Backtest, baseline: Expert, gateway: Gateway) -> pl.DataFrame:
    """A baseline's scored predictions on the same steps. One that only changes `fit` and
    `predict` reuses the expert's features."""
    same = type(baseline).features is type(bt.expert).features
    if same:
        pred = backtest.walk(
            baseline, bt.features, bt.targets, bt.steps, bt.test, bt.refit, bt.half_life
        )
        hist = backtest.standard(baseline, pred).join(
            bt.targets.select(*baseline.keys(), "y"), on=baseline.keys(), how="left"
        )
        return scores.row_losses(hist, baseline.kind)
    seasons = sorted({s.season for s in bt.steps if s.index in bt.test})
    return backtest.run(baseline, gateway, seasons, open_vault=True).history


def validate(
    expert: Expert,
    gateway: Gateway | None = None,
    seasons: Sequence[int] | None = None,
    open_vault: bool = False,
    baselines: Sequence[Expert] = (),
    shuffles: int = nulls.SHUFFLES,
    n_cutoffs: int = leakage.CUTOFFS,
    refit: str = "step",
    rules: Sequence[sanity.Rule] = (),
    seed: int | None = None,
) -> Validation:
    seed = get_config().seed if seed is None else seed
    gateway = gateway or Gateway()
    bt = backtest.run(expert, gateway, seasons, open_vault=open_vault, refit=refit)
    tested = sorted({s.season for s in bt.steps if s.index in bt.test})
    keys = expert.keys()
    scored = bt.scored
    base_hist, comps = {}, {}
    for b in baselines:
        name = type(b).__name__
        base_hist[name] = baseline_history(bt, b, gateway)
        comps[name] = compare(scored, base_hist[name], keys, "step", (expert.id, name), seed=seed)
    signal = nulls.signal_test(bt, shuffles, seed) if shuffles else None
    groups = scored.join(
        bt.features.select(*keys, *expert.groups, "step_season"), on=keys, how="left"
    ).rename({"step_season": "season"})
    if expert.kind == "amount":
        calib = calibration.coverage(groups, [*expert.groups, "season"])
    else:
        calib = calibration.probability_report(scored)
    checks = leakage.run_checks(bt, gateway, signal, n_cutoffs, seed)
    rules_df = sanity.run_rules(bt.history, [*sanity.shared(expert.kind), *rules])
    show = [*keys, *[g for g in expert.groups]]
    review = sanity.review_lists(
        bt.history.join(bt.features.select(*keys, *expert.groups), on=keys, how="left"), show
    )
    return Validation(
        bt, base_hist, comps, signal, None, calib, checks, rules_df, review, tested, open_vault
    )


def record(v: Validation, out_dir: Path | None = None) -> Path:
    """Log the validation on the active MLflow run: metrics, the checks (which gate
    registration), the vault, the walk-forward history and the scorecard. Returns the
    scorecard's local path."""
    from pcf.core import tracking
    from pcf.validation.scorecard import render

    run_id = tracking.active_run_id()
    project_id = v.bt.expert.id
    if v.vault_opened:
        tracking.mark_vault_opened(project_id, run_id)
    v.versions_tried = tracking.versions_tried(project_id)
    metrics = scores.summary(v.bt.scored, v.bt.expert.kind)
    metrics |= {f"vs_{name}_diff": comp.diff for name, comp in v.comparisons.items()}
    if v.signal is not None:
        metrics["signal_beaten"] = v.signal.beaten
    tracking.log_metrics(metrics, run_id)
    tracking.log_checks(leakage.results(v.checks), run_id)
    history = backtest.write_history(v.bt, run_id, out_dir)
    html = render(v)
    tracking.log_text(html, SCORECARD, run_id)
    path = history.parent / SCORECARD
    path.write_text(html, encoding="utf-8")
    log.info("%s: scorecard at %s", project_id, path)
    return path
