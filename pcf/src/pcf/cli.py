"""The `pcf` command. Later projects add subcommands (refresh, run, backtest, check, status)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from pcf import __version__
from pcf.config import (
    DATA_ZONES,
    ENV_FILE,
    KNOWN_SECRET_NAMES,
    get_config,
    get_secret,
    read_env_file,
)


def _folder_size_mb(path) -> float:
    if not path.exists():
        return 0.0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def info() -> None:
    """Show the resolved config. Key names are listed, never their values."""
    cfg = get_config()
    s = cfg.seasons
    print(f"pcf {__version__}")
    print(f"pcf folder:   {cfg.pcf_dir}")
    print(f"config file:  {cfg.config_file}")
    print(f"data folder:  {cfg.data_dir}{'' if cfg.data_dir.exists() else '  (not created yet)'}")
    for zone in DATA_ZONES:
        path = cfg.zone(zone)
        if path.exists():
            print(f"  {zone:<9} {_folder_size_mb(path):>10,.1f} MB")
    print(
        f"seasons:      train from {s.first_train}, report from {s.first_report}, "
        f"vault {s.vault}, live {s.live}"
    )
    print(f"random seed:  {cfg.seed}")
    from pcf.data.sources.nflverse import data_version

    print(f"data version: nflverse {data_version()}")
    names = sorted(set(read_env_file()) | set(KNOWN_SECRET_NAMES))
    set_names = [n for n in names if get_secret(n) is not None]
    print(f".env file:    {ENV_FILE}{'' if ENV_FILE.exists() else '  (missing)'}")
    print(f"keys set:     {', '.join(set_names) or 'none'}")


def refresh(args: argparse.Namespace) -> None:
    """Download new or changed nflverse files and print what happened."""
    from pcf.data.sources.nflverse import refresh as run

    summary = run(
        args.datasets,
        args.seasons,
        dry_run=args.dry_run,
        force=args.force,
        snapshots_only=args.snapshots_only,
    )
    print(summary.text())


def tables(args: argparse.Namespace) -> None:
    """Build tables from the raw copy."""
    from pcf.data.tables import build

    build(args.tables or None, args.seasons)


def ui(args: argparse.Namespace) -> None:
    """Open MLflow's browser view on PCF's store. Runs until stopped (Ctrl+C)."""
    import os
    import subprocess
    import webbrowser

    from pcf.core.tracking import use_store

    uri = use_store()
    url = f"http://127.0.0.1:{args.port}"
    print(f"MLflow store: {uri}")
    print(f"Opening {url} (Ctrl+C to stop)")
    env = {**os.environ, "MLFLOW_DISABLE_TELEMETRY": "true", "MLFLOW_DISABLE_AGENT_HINT": "1"}
    server = subprocess.Popen(
        [sys.executable, "-m", "mlflow", "ui", "--backend-store-uri", uri]
        + ["--host", "127.0.0.1", "--port", str(args.port)],
        env=env,
    )
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.wait()
    except KeyboardInterrupt:
        server.terminate()


def champions(args: argparse.Namespace) -> None:
    """Copy the champion versions in registry.yaml to MLflow's `champion` aliases (main only)."""
    from pcf.core.tracking import model_name, sync_champions

    synced = sync_champions()
    if not synced:
        print("no champions in registry.yaml yet")
    for project_id, version in synced.items():
        print(f"{model_name(project_id)}: champion = version {version}")


def backtest(args: argparse.Namespace) -> None:
    """Validate one model: walk-forward backtest, baselines, signal test, calibration, leakage
    checks and the scorecard, recorded as an MLflow attempt."""
    from pcf.core import tracking
    from pcf.core.contract import check_expert, find, find_all
    from pcf.validation.validate import record, validate

    classes = [find(args.project, args.variant)] if args.variant else find_all(args.project)
    for cls in classes:
        check_expert(cls)
        expert = cls()
        baselines = [b() for b in getattr(cls, "baselines", lambda: [])()]
        v = validate(
            expert,
            seasons=args.seasons,
            open_vault=args.open_vault,
            baselines=baselines,
            shuffles=args.shuffles,
            refit=args.refit,
        )
        train_end = v.bt.history["train_end"].max()
        name = f"backtest {cls.variant}".strip()
        variant = cls.variant or None
        with tracking.attempt(args.project, train_end=train_end, name=name, variant=variant):
            path = record(v)
        print(cls.label())
        for ch in v.checks:
            mark = "pass" if ch.passed else ("FLAG" if not ch.blocking else "FAIL")
            print(f"{ch.number:>2} {ch.name:<20} {mark:<5} {ch.detail}")
        print(f"scorecard: {path}")


def misses(args: argparse.Namespace) -> None:
    """Where a saved run misses, by today's dated lens list: misses.parquet and misses.html next
    to its history (the latest run unless --run)."""
    import polars as pl

    from pcf.config import get_config
    from pcf.core.contract import find
    from pcf.data.gateway import Gateway
    from pcf.validation.misses import from_history, save
    from pcf.validation.scorecard import render_misses

    cls = find(args.project, args.variant)
    folder = get_config().zone("outputs") / args.project / (cls.variant or "")
    runs = sorted(
        (p for p in folder.iterdir() if (p / "history.parquet").exists()),
        key=lambda p: p.stat().st_mtime,
    )
    run = folder / args.run if args.run else runs[-1]
    m = from_history(pl.read_parquet(run / "history.parquet"), cls(), Gateway())
    save(m, run, run.name)
    page = run / "misses.html"
    page.write_text(render_misses(m, cls.label()), encoding="utf-8")
    cols = ["lens", "when", "bias_share", "spread_share", "top_group", "avg_miss"]
    with pl.Config(tbl_rows=20, float_precision=3, tbl_hide_dataframe_shape=True):
        print(f"{cls.label()} (run {run.name}, lens list {m.lens_list})")
        print(m.lenses.select(cols))
        if not m.flagged.is_empty():
            print(m.flagged.select(cols))
    print(f"report: {page}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pcf", description="PCF: Principal Component Football")
    parser.add_argument("--version", action="version", version=f"pcf {__version__}")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("info", help="show the resolved paths and settings")
    r = commands.add_parser("refresh", help="download new or changed nflverse files")
    r.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        metavar="NAME",
        help="only this dataset (repeatable); default: all",
    )
    r.add_argument("--seasons", nargs="+", type=int, help="only these seasons")
    r.add_argument(
        "--dry-run", action="store_true", help="show what would change, download nothing"
    )
    r.add_argument("--force", action="store_true", help="download even if unchanged upstream")
    r.add_argument(
        "--snapshots-only",
        action="store_true",
        help="only update the change logs of state files (the pcf-data job)",
    )

    t = commands.add_parser("tables", help="build the tables at each level of detail")
    t_commands = t.add_subparsers(dest="tables_command", required=True)
    b = t_commands.add_parser("build", help="build tables from the raw copy")
    b.add_argument("tables", nargs="*", metavar="TABLE", help="tables to build; default: all")
    b.add_argument("--seasons", nargs="+", type=int, help="only these seasons")

    u = commands.add_parser("ui", help="open MLflow's browser view of every run and model")
    u.add_argument("--port", type=int, default=5000, help="local port (default 5000)")
    u.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    commands.add_parser(
        "champions", help="set MLflow's champion aliases from registry.yaml (on main only)"
    )

    bt = commands.add_parser("backtest", help="validate a model and write its scorecard")
    bt.add_argument("project", help="the model's registry id")
    bt.add_argument("--variant", help="one variant of the project (default: all of them)")
    bt.add_argument(
        "--seasons", nargs="+", type=int, help="test seasons (default: 2016 to vault-1)"
    )
    bt.add_argument("--shuffles", type=int, default=100, help="signal-test refits (100, or 20)")
    bt.add_argument("--refit", choices=["step", "season"], default="step", help="refit every")
    bt.add_argument(
        "--open-vault", action="store_true", help="include the vault season (once, logged)"
    )

    ms = commands.add_parser("misses", help="where a saved model run misses, by the lens list")
    ms.add_argument("project", help="the model's registry id")
    ms.add_argument("--variant", help="the variant (for projects with several)")
    ms.add_argument("--run", help="the run id (default: the latest)")

    args = parser.parse_args(argv)
    if args.command == "misses":
        misses(args)
        return 0
    if args.command == "backtest":
        backtest(args)
        return 0
    if args.command == "info":
        info()
        return 0
    if args.command == "refresh":
        refresh(args)
        return 0
    if args.command == "tables":
        tables(args)
        return 0
    if args.command == "ui":
        ui(args)
        return 0
    if args.command == "champions":
        champions(args)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
