"""The build's runner (decision 0043): a forecast's validation through the harness with its feature
history saved, and the build's own checks on saved features.

    python -m pcf.experts.td_expert.run forecast --variant skill_next_chances   # backtest + features
    python -m pcf.experts.td_expert.run walks --family skill --horizon next     # the other rungs
    python -m pcf.experts.td_expert.run facts                                   # facts, ceilings
    python -m pcf.experts.td_expert.run regression                              # the measure

Each command writes a text report to `projects/td-expert/build/` and its tables to
`interim/td_expert/`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pcf.config import get_config
from pcf.core.log import get_logger

log = get_logger(__name__)
ID = "td-expert"


def cache_dir() -> Path:
    path = get_config().zone("interim") / "td_expert"
    path.mkdir(parents=True, exist_ok=True)
    return path


def saved_dir(family: str, horizon: str, tag: str = "") -> Path:
    """Where `forecast` saves a validated run's feature history and outcomes (one per family and
    horizon: every rung of a family reads the same features)."""
    return cache_dir() / f"saved_{family}_{horizon}{'_' + tag if tag else ''}"


def report_dir() -> Path:
    path = Path(__file__).resolve().parents[4] / "projects" / ID / "build"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write(name: str, lines: list[str]) -> None:
    text = "\n".join(lines)
    (report_dir() / f"{name}.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


def forecast(variant: str, seasons: list[int] | None, open_vault: bool, shuffles: int,
             refit: str, cutoffs: int | None, tag: str = "") -> str:  # fmt: skip
    """`pcf backtest` for one variant (with its baselines), plus its feature history saved for
    the walks. Returns the MLflow run id."""
    from pcf.core import tracking
    from pcf.core.contract import check_expert, find
    from pcf.validation import leakage
    from pcf.validation.backtest import save_features
    from pcf.validation.validate import record, validate

    cls = find(ID, variant)
    check_expert(cls)
    baselines = [b() for b in cls.baselines()]
    v = validate(cls(), seasons=seasons, open_vault=open_vault, baselines=baselines,
                 shuffles=shuffles, refit=refit,
                 n_cutoffs=leakage.CUTOFFS if cutoffs is None else cutoffs)  # fmt: skip
    train_end = v.bt.history["train_end"].max()
    name = f"backtest {variant}{' ' + tag if tag else ''}"
    with tracking.attempt(ID, train_end=train_end, name=name, variant=variant):
        path = record(v)
        run_id = tracking.active_run_id()
    save_features(v.bt, saved_dir(cls.family, cls.horizon, tag))
    lines = [f"{cls.label()} run {run_id}", f"scorecard: {path}"]
    for ch in v.checks:
        mark = "pass" if ch.passed else ("FLAG" if not ch.blocking else "FAIL")
        lines.append(f"{ch.number:>2} {ch.name:<20} {mark:<5} {ch.detail}")
    if v.signal is not None:
        lines.append(f"signal: beat {v.signal.beaten} of {v.signal.n} shuffled refits")
    for name_, comp in v.comparisons.items():
        lines.append(f"against {name_}: {comp}")
    cal = v.calibration
    if cal.get("count"):
        for k in ("one", "two"):
            lines.append(f"chance of {k}+: error {cal[k]['error']:.2f} points, "
                         f"slope {cal[k]['slope']:.2f}, passed {cal[k]['passed']}")  # fmt: skip
        lines.append(f"Poisson q10-q90 holds {cal['range']['inside']:.1%} (reported)")
    write(f"forecast_{variant}{'_' + tag if tag else ''}", lines)
    return run_id


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="td_expert.run")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("forecast")
    f.add_argument("--variant", required=True)
    f.add_argument("--seasons", nargs="+", type=int)
    f.add_argument("--open-vault", action="store_true")
    f.add_argument("--shuffles", type=int, default=100)
    f.add_argument("--refit", choices=["step", "season"], default="season")
    f.add_argument("--cutoffs", type=int)
    f.add_argument("--tag", default="")
    w = sub.add_parser("walks")
    w.add_argument("--family", required=True)
    w.add_argument("--horizon", required=True)
    w.add_argument("--tag", default="")
    w.add_argument("--shuffles", type=int, default=20)
    sub.add_parser("facts")
    r = sub.add_parser("regression")
    r.add_argument("--seasons", nargs="+", type=int, default=list(range(2016, 2025)))
    r.add_argument("--open-vault", action="store_true")
    sub.add_parser("ideas")
    args = p.parse_args(argv)
    if args.command == "forecast":
        forecast(args.variant, args.seasons, args.open_vault, args.shuffles, args.refit,
                 args.cutoffs, args.tag)  # fmt: skip
    elif args.command == "walks":
        from pcf.experts.td_expert import checks

        write(f"walks_{args.family}_{args.horizon}{'_' + args.tag if args.tag else ''}",
              checks.walks(args.family, args.horizon, args.tag, args.shuffles))  # fmt: skip
    elif args.command == "facts":
        from pcf.experts.td_expert import checks

        write("facts", checks.facts())
    elif args.command == "regression":
        from pcf.experts.td_expert import regression
        from pcf.validation.backtest import check_seasons

        check_seasons(args.seasons, args.open_vault)
        tag = "vault" if args.open_vault else "backtest"
        write(f"regression_{tag}", regression.report(args.seasons))
    elif args.command == "ideas":
        from pcf.experts.td_expert import checks

        write("ideas", checks.ideas())


if __name__ == "__main__":
    main(sys.argv[1:])
