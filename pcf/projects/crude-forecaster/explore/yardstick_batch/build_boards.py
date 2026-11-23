"""The yardstick batch: the new boards it needs (I67's QB rushing; I70's depth-chart rows).

Run from pcf/ (PCF_DATA_DIR set), detached; progress in data/logs/yardstick-batch-progress.txt:
    python projects/crude-forecaster/explore/yardstick_batch/build_boards.py [names...]
"""

from __future__ import annotations

import sys
import time

from pcf.baselines.crude import yardstick as Y
from pcf.config import get_config

BOARDS = {
    "qb_rushing_next": ("qb_rushing", "next", "participation"),
    "qb_rushing_next3": ("qb_rushing", "next3", "participation"),
    "passing_next_depth": ("passing", "next", "depth"),
    "rushing_next_depth": ("rushing", "next", "depth"),
    "receiving_next_depth": ("receiving", "next", "depth"),
    "qb_rushing_next_depth": ("qb_rushing", "next", "depth"),
}
PROGRESS = get_config().zone("logs") / "yardstick-batch-progress.txt"
START = time.time()


def log(*parts) -> None:
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(f"[{time.time() - START:7.0f}s] boards " + " ".join(str(p) for p in parts) + "\n")


def main(names: list[str]) -> None:
    for name in names or list(BOARDS):
        target, horizon, rows = BOARDS[name]
        log(name, "start")
        b = Y.build_board(target, horizon, rows=rows)
        log(name, "done", b.features.shape)
    log("all done")


if __name__ == "__main__":
    main(sys.argv[1:])
