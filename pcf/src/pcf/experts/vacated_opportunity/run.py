"""The build's runner (decision 0050). Reports go to `projects/vacated-opportunity/build/`, cached
walks to `interim/vacated_build/`.

    python -m pcf.experts.vacated_opportunity.run walks          # the three measures' walks
    python -m pcf.experts.vacated_opportunity.run ladder         # vacated-live's ladder and ranges
    python -m pcf.experts.vacated_opportunity.run shuffles --copies 19
    python -m pcf.experts.vacated_opportunity.run checks         # obvious input, I55, I143
    python -m pcf.experts.vacated_opportunity.run yardstick
    python -m pcf.experts.vacated_opportunity.run choice
    python -m pcf.experts.vacated_opportunity.run offseason
    python -m pcf.experts.vacated_opportunity.run history        # the saved outputs + MLflow
    python -m pcf.experts.vacated_opportunity.run spot           # the CEO's spot-check: the target shrink
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import polars as pl

from pcf.experts.vacated_opportunity import common as K

c = pl.col
WALKED = tuple(range(2014, K.LAST + 1))


def walk_path(measure: str, tag: str = "") -> object:
    return K.cache_dir() / f"walk_{measure}{tag}.parquet"


def walks(refresh: bool = False) -> dict[str, pl.DataFrame]:
    from pcf.experts.vacated_opportunity import live as L

    out = {}
    inp = None
    for m in K.MEASURES:
        p = walk_path(m)
        if p.exists() and not refresh:
            out[m] = pl.read_parquet(p)
            continue
        inp = inp or L.Inputs()
        t0 = time.time()
        w = L.walk(inp, m, WALKED, structured=True)
        w.write_parquet(p)
        print(f"walked {m}: {w.height} rows in {time.time() - t0:.0f}s", flush=True)
        out[m] = w
    return out


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="vacated_opportunity.run")
    sub = p.add_subparsers(dest="command", required=True)
    w = sub.add_parser("walks")
    w.add_argument("--refresh", action="store_true")
    sub.add_parser("ladder")
    s = sub.add_parser("shuffles")
    s.add_argument("--copies", type=int, default=19)
    for name in ("checks", "ideas", "yardstick", "choice", "offseason", "history", "spot"):
        sub.add_parser(name)
    a = p.parse_args(argv)
    if a.command == "walks":
        walks(a.refresh)
        return
    from pcf.experts.vacated_opportunity import report as Rep

    if a.command == "ladder":
        Rep.ladder(walks())
    elif a.command == "shuffles":
        Rep.shuffles(walks(), a.copies)
    elif a.command == "checks":
        Rep.checks(walks())
    elif a.command == "ideas":
        Rep.ideas(walks())
    elif a.command == "yardstick":
        Rep.yardstick(walks())
    elif a.command == "choice":
        Rep.choice(walks())
    elif a.command == "offseason":
        Rep.offseason()
    elif a.command == "history":
        Rep.history(walks())
    elif a.command == "spot":
        Rep.spot_target_shrink()


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
