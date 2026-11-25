"""Round 2, I135's yardstick half: the 4-feature role table (no targets per pass snap, no carries
per run snap) on the receiving and rushing rest-of-season boards, beside participation, against 19
copies shuffled within season and group (test 4's design). The 6-feature table again for
reference.

Run from pcf/: .venv/Scripts/python.exe projects/roles-archetypes/explore/build2_yardstick.py
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
T6 = bc.T_OFF
T4 = [x for x in T6 if x not in ("t1_tgt_per_pass", "t2_car_per_run")]
say("Round 2, I135: the role table without his own target rates, on the yardstick (19 copies each)")
for target in ("receiving", "rushing"):
    board = Y.load_board(target, "rest")
    keys = board.keys
    rows = board.features.select(*keys, "season")
    crude = board.forecast(("participation",))

    def gain(cols, pr):
        frame = rows.join(pr.select("gsis_id", "season", *cols), on=["gsis_id", "season"], how="left").drop("season")
        feats = board.features.join(frame, on=keys, how="left").with_columns(c(x).fill_null(c(x).median()) for x in cols)
        return Y.gain(board.forecast(("participation",), extra=list(cols), feats=feats), crude, keys)

    say(f"\n== {target} ({board.features.height:,} rows)")
    for name, cols in (("6-feature table", T6), ("4-feature table (I135)", T4)):
        g = gain(cols, prior)
        cps = np.array([gain(cols, bc.shuffled(prior, cols, 11000 + k)).share for k in range(19)])
        counts = g.lo > 0 and g.share > cps.max()
        say(f"  {name:24}: {100 * g.share:+.2f}% (90% {100 * g.lo:+.2f} to {100 * g.hi:+.2f}); copies mean {100 * cps.mean():+.2f}%, best {100 * cps.max():+.2f}%; counts: {counts}")
say.save()
