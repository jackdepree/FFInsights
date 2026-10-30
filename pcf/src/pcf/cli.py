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

    args = parser.parse_args(argv)
    if args.command == "info":
        info()
        return 0
    if args.command == "refresh":
        refresh(args)
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
