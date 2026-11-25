"""The build's runner (decision 0047): a shipped variant's validation through the harness (the
backtest, its baselines, the shuffled refits, the leakage suite and the scorecard, tracked in
MLflow), and the walks of every variant on one saved feature history.

    python -m pcf.experts.availability.run forecast --variant next_logit --shuffles 100
    python -m pcf.experts.availability.run walks                      # every variant, cached

Reports go to `projects/availability/build/`; tables to `interim/availability/build/`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pcf.core.log import get_logger

log = get_logger(__name__)
ID = "availability"
# each shipped variant's baselines (they share its features, so the harness reuses them)
BASELINES = {
    "next_logit": ("next_table",),
    "next_lasso": ("next_table", "next_logit"),
    "next3_chain": ("next3_table", "next3_two"),
    "rest_chain": ("rest_table", "rest_two"),
    "next3_two": ("next3_table",),
    "rest_two": ("rest_table",),
}


def report_dir() -> Path:
    path = Path(__file__).resolve().parents[4] / "projects" / ID / "build"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write(name: str, lines: list[str]) -> None:
    text = "\n".join(lines)
    (report_dir() / f"{name}.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


def forecast(variant: str, shuffles: int, cutoffs: int | None, seasons: list[int] | None) -> str:
    """`pcf backtest` for one variant with its baselines. Returns the MLflow run id."""
    from pcf.core import tracking
    from pcf.core.contract import check_expert
    from pcf.experts.availability import checks as K
    from pcf.experts.availability.experts import VARIANTS
    from pcf.validation import leakage
    from pcf.validation.validate import record, validate

    cls = VARIANTS[variant]
    check_expert(cls)
    baselines = [VARIANTS[b]() for b in BASELINES.get(variant, ())]
    v = validate(cls(), seasons=seasons or K.SEASONS, baselines=baselines, shuffles=shuffles,
                 refit=K.REFIT, n_cutoffs=leakage.CUTOFFS if cutoffs is None else cutoffs)  # fmt: skip
    train_end = v.bt.history["train_end"].max()
    with tracking.attempt(ID, train_end=train_end, name=f"backtest {variant}", variant=variant):
        path = record(v)
        run_id = tracking.active_run_id()
    lines = [f"{cls.label()} run {run_id}", f"scorecard: {path}"]
    for ch in v.checks:
        mark = "pass" if ch.passed else ("FLAG" if not ch.blocking else "FAIL")
        lines.append(f"{ch.number:>2} {ch.name:<20} {mark:<5} {ch.detail}")
    if v.signal is not None:
        lines.append(f"signal: beat {v.signal.beaten} of {v.signal.n} shuffled refits")
    for name, comp in v.comparisons.items():
        lines.append(f"against {name}: {comp}")
    for k, val in v.calibration.items():
        if not hasattr(val, "shape"):
            lines.append(f"calibration {k}: {val}")
    write(f"forecast_{variant}", lines)
    return run_id


def walks(variants: list[str]) -> None:
    """Every variant's walk on the saved features (build them first with checks.build_features),
    each history cached as hist_<variant>.parquet."""
    import time

    from pcf.experts.availability import checks as K
    from pcf.experts.availability.experts import VARIANTS

    cache: dict = {}
    for v in variants or list(VARIANTS):
        out = K.cache_dir() / f"hist_{v}.parquet"
        if out.exists():
            continue
        family = VARIANTS[v].family
        if family not in cache:
            cache.clear()
            cache[family] = K.family_rows(family)
        f, t = cache[family]
        t0 = time.time()
        K.walk(v, f, t).write_parquet(out)
        log.info("%s walked in %.0fs", v, time.time() - t0)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="availability.run")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("forecast")
    f.add_argument("--variant", required=True)
    f.add_argument("--shuffles", type=int, default=100)
    f.add_argument("--cutoffs", type=int)
    f.add_argument("--seasons", nargs="+", type=int)
    w = sub.add_parser("walks")
    w.add_argument("variants", nargs="*")
    a = p.parse_args(argv)
    if a.command == "forecast":
        forecast(a.variant, a.shuffles, a.cutoffs, a.seasons)
    else:
        walks(a.variants)


if __name__ == "__main__":
    main(sys.argv[1:])
