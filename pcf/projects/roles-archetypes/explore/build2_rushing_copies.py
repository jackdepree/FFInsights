"""Round 2 spot-check, part 2: the shuffled copies' full spread on the rushing board (test 4 printed
only their best), for the coordinates, the role table, the fixed coordinates (non-backs' prior
missing, I133) and the fine back roles as dummies (S5's side result). 19 copies each, shuffled
within season and group (test 4's design). Counts = interval above 0 and beats all 19.

Run from pcf/: .venv/Scripts/python.exe projects/roles-archetypes/explore/build2_rushing_copies.py
"""

# ruff: noqa: E501, B023
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import build2_common as bc  # noqa: E402

from pcf.baselines.crude import yardstick as Y  # noqa: E402

c = pl.col
say = bc.Say(Path(__file__).with_suffix(".txt"))
prior = bc.offense_prior()
Z, T = bc.Z, bc.T_OFF
prior = prior.with_columns(
    is_early=(c("role") == "early-down back").cast(pl.Float64), is_pdown=(c("role") == "passing-down back").cast(pl.Float64),
    **{f"b{z}": pl.when(c("coarse") != "back").then(None).otherwise(c(z)) for z in Z})
BZ = [f"b{z}" for z in Z]


def run(target: str) -> None:
    board = Y.load_board(target, "rest")
    keys = board.keys
    rows = board.features.select(*keys, "season")
    crude = board.forecast(("participation",))

    def gain(cols, pr):
        frame = rows.join(pr.select("gsis_id", "season", *cols), on=["gsis_id", "season"], how="left").drop("season")
        feats = board.features.join(frame, on=keys, how="left").with_columns(c(x).fill_null(c(x).median()) for x in cols)
        return Y.gain(board.forecast(("participation",), extra=list(cols), feats=feats), crude, keys)

    say(f"\n== {target} rest-of-season board, beside participation ({board.features.height:,} rows)")
    for name, cols in (("coordinates", Z), ("role table", T), ("coordinates, non-backs' prior missing (I133 a)", BZ),
                       ("fine back roles as 2 dummies", ["is_early", "is_pdown"]), ("carries per run snap alone", ["t2_car_per_run"])):
        g = gain(cols, prior)
        cps = np.array([gain(cols, bc.shuffled(prior, cols, 9000 + k)).share for k in range(19)])
        counts = g.lo > 0 and g.share > cps.max()
        beaten = int((g.share > cps).sum())
        say(f"  {name:48}: {100 * g.share:+.2f}% (90% {100 * g.lo:+.2f} to {100 * g.hi:+.2f}); 19 copies: mean {100 * cps.mean():+.2f}%, "
            f"from {100 * cps.min():+.2f} to {100 * cps.max():+.2f}; beats {beaten} of 19; real minus the copies' mean {100 * (g.share - cps.mean()):+.2f}; counts: {counts}")


say("Round 2 spot-check, part 2: the shuffled copies' spread (19 each, within season and group)")
run("rushing")
run("receiving")
say.save()
