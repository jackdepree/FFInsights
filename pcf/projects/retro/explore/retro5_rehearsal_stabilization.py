# ruff: noqa: E501
"""Retro 5, rehearsal (step 5): stabilization's next-season ladder re-scored on seasons it never scored.

F121 (M1 beats the raw rate and the position's average), F122 (the second pull clears M1 for 11 of 20) and F124 (the
trend clears the ridge for 16 of 20, and ships as rung 4) were all read on targets 2018-2024, and F124's trend was
chosen there. The walk itself starts earlier (targets 2007 on), fit only on earlier pairs at every step, so its
forecasts for targets 2010-2017 exist and were never looked at. Rates with play-by-play from 2006 (8 of 20) have
them; the stand-in and PFR rates start in 2013 and 2018 and don't. Same code, same gains (entities resampled).
The 2025 vault is never read.

Odds, written before this script was run (Claude, 2026-11-26):
- F121: M1 beats the position's average clearly for 6+ of the 8 rates: 80%; beats the raw rate for 8 of 8: 85%.
- F122: the second pull clears M1 for 3+ of 8: 55% (it did for 11 of 20 on 2018-2024).
- F124: the trend clears the ridge for 4+ of 8: 55% (16 of 20 on 2018-2024, but found there); for 6+ of 8: 30%.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro5_rehearsal_stabilization.py > projects/retro/explore/retro5_rehearsal_stabilization.txt
"""

import polars as pl

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import evaluate as E
from pcf.experts.stabilization import walks as W

c = pl.col
import os
EARLY = list(range(2018, 2025)) if os.environ.get("REHEARSE") == "test" else list(range(2010, 2018))
inp = W.Inputs()
tally = {"m1_avg": 0, "m1_raw": 0, "pull_m1": 0, "trend_ridge": 0}
n = 0
print(f"{'rate':<28}{'pairs':>6}  {'M1 v average':<22}{'M1 v raw':<22}{'pull v M1':<22}{'trend v ridge':<22}")
for m in K.MEASURES:
    if m.first > 2009:
        continue
    n += 1
    p, oth, cc, ks = W.next_frame(inp, m)
    f = W.next_rungs(p, oth, cc, ks).filter(c("target").is_in(EARLY))
    gs = {
        "m1_avg": E.gain(f, "m1", "avg", seed=1), "m1_raw": E.gain(f, "m1", "raw", seed=1),
        "pull_m1": E.gain(f, "pull", "m1", seed=1), "trend_ridge": E.gain(f, "ridge_trend", "ridge", seed=1),
    }
    cells = []
    for k, g in gs.items():
        tally[k] += bool(g.clear)
        cells.append(f"{100 * g.gain:+.1f}% ({100 * g.lo:+.1f}, {100 * g.hi:+.1f}){'*' if g.clear else ' '}")
    print(f"{m.label:<28}{f.drop_nulls('ridge').height:>6}  " + "".join(f"{x:<22}" for x in cells))
print(f"\n== clear (* = interval above 0), of {n} rates on targets {EARLY[0]}-{EARLY[-1]}: M1 v average {tally['m1_avg']}, M1 v raw {tally['m1_raw']}, pull v M1 {tally['pull_m1']}, trend v ridge {tally['trend_ridge']}")
