"""The build's runner (decision 0041): the forecast's validation with its feature history saved,
and the checks the harness doesn't do for this expert.

    python -m pcf.experts.opportunity_quality.run forecast --variant eff   # backtest + features
    python -m pcf.experts.opportunity_quality.run facts                    # data checks
    python -m pcf.experts.opportunity_quality.run regression               # the regression measure
    python -m pcf.experts.opportunity_quality.run downstream               # no-noise, yardstick

Each command writes a text report to `projects/opportunity-quality/build/` and its tables to
`interim/opportunity_quality/`. A progress line per stage goes to the log.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.core.log import get_logger

log = get_logger(__name__)
c = pl.col
ID = "opportunity-quality"


def cache_dir() -> Path:
    path = get_config().zone("interim") / "opportunity_quality"
    path.mkdir(parents=True, exist_ok=True)
    return path


def report_dir() -> Path:
    path = Path(__file__).resolve().parents[4] / "projects" / ID / "build"
    path.mkdir(parents=True, exist_ok=True)
    return path


def forecast(variant: str, seasons: list[int] | None, open_vault: bool, shuffles: int,
             refit: str, tag: str = "") -> str:  # fmt: skip
    """`pcf backtest` for one variant, plus its feature history saved for the downstream checks.
    Returns the MLflow run id."""
    from pcf.core import tracking
    from pcf.core.contract import check_expert, find
    from pcf.validation.validate import record, validate

    cls = find(ID, variant)
    check_expert(cls)
    baselines = [b() for b in cls.baselines()]
    v = validate(cls(), seasons=seasons, open_vault=open_vault, baselines=baselines,
                 shuffles=shuffles, refit=refit)  # fmt: skip
    train_end = v.bt.history["train_end"].max()
    name = f"backtest {variant}{' ' + tag if tag else ''}"
    with tracking.attempt(ID, train_end=train_end, name=name, variant=variant):
        path = record(v)
        run_id = tracking.active_run_id()
    from pcf.experts.opportunity_quality.downstream import saved_dir
    from pcf.validation.backtest import save_features

    save_features(v.bt, saved_dir(variant, tag))
    lines = [f"{cls.label()} run {run_id}", f"scorecard: {path}"]
    for ch in v.checks:
        mark = "pass" if ch.passed else ("FLAG" if not ch.blocking else "FAIL")
        lines.append(f"{ch.number:>2} {ch.name:<20} {mark:<5} {ch.detail}")
    if v.signal is not None:
        lines.append(f"signal: beat {v.signal.beaten} of {v.signal.n} shuffled refits")
    for name_, comp in v.comparisons.items():
        lines.append(f"against {name_}: {comp}")
    text = "\n".join(lines)
    (report_dir() / f"forecast_{variant}{'_' + tag if tag else ''}.txt").write_text(
        text + "\n", encoding="utf-8"
    )
    print(text)
    return run_id


def _write(name: str, lines: list[str]) -> None:
    text = "\n".join(lines)
    (report_dir() / f"{name}.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


def facts_command() -> None:
    from pcf.experts.opportunity_quality import checks

    _write("facts", checks.facts())


def regression_command(seasons: list[int], vault: bool, shuffles: int) -> None:
    """The regression measure walk forward; its history saved to outputs (standard schema)."""
    from pcf.experts.opportunity_quality import checks
    from pcf.validation.backtest import check_seasons

    check_seasons(seasons, vault)
    hist = checks.regression_history(seasons)
    tag = "vault" if vault else "backtest"
    lines = checks.regression_report(hist, shuffles) + [""] + checks.regression_params(seasons)
    _write(f"regression_{tag}", lines)
    hist.write_parquet(cache_dir() / f"regression_{tag}.parquet")
    path = get_config().zone("outputs") / ID / "regression" / tag / "history.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    checks.regression_output(hist, f"regression-{tag}").write_parquet(path)
    log.info("the regression measure's history: %s", path)


def downstream_command(variant: str) -> None:
    """No-noise, kinds, the ladder, the yardstick and fitting noise on a validated run's saved
    features; the extra variants' walk-forward histories saved in the standard schema."""
    from pcf.core.contract import find
    from pcf.experts.opportunity_quality import downstream
    from pcf.validation.backtest import standard

    lines, walks = downstream.run_all(variant)
    _write(f"downstream_{variant}", lines)
    root = get_config().zone("outputs") / ID
    for name, pred in walks.items():
        if name == variant:
            continue
        expert = find(ID, name)()
        path = root / name / "saved-features" / "history.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        out = standard(expert, pred, run_id="saved-features")
        out.join(pred.select("gsis_id", "game_id", "y", "loss", "readable"),
                 on=["gsis_id", "game_id"]).write_parquet(path)  # fmt: skip
        log.info("%s: %d rows saved to %s", name, out.height, path)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="opportunity_quality.run")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("forecast")
    f.add_argument("--variant", required=True)
    f.add_argument("--seasons", nargs="+", type=int)
    f.add_argument("--open-vault", action="store_true")
    f.add_argument("--shuffles", type=int, default=100)
    f.add_argument("--refit", choices=["step", "season"], default="season")
    f.add_argument("--tag", default="")
    sub.add_parser("facts")
    r = sub.add_parser("regression")
    r.add_argument("--seasons", nargs="+", type=int, default=list(range(2016, 2025)))
    r.add_argument("--open-vault", action="store_true")
    r.add_argument("--shuffles", type=int, default=100)
    d = sub.add_parser("downstream")
    d.add_argument("--variant", default="eff")
    sub.add_parser("horizons")
    args = p.parse_args(argv)
    if args.command == "facts":
        facts_command()
    elif args.command == "regression":
        regression_command(args.seasons, args.open_vault, args.shuffles)
    elif args.command == "horizons":
        from pcf.experts.opportunity_quality import downstream

        _write("horizons", downstream.horizons_check())
    elif args.command == "downstream":
        downstream_command(args.variant)
    elif args.command == "forecast":
        forecast(args.variant, args.seasons, args.open_vault, args.shuffles, args.refit, args.tag)


if __name__ == "__main__":
    main(sys.argv[1:])
