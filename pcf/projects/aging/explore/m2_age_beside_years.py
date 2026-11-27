"""Aging, a check before the brief (2026-11-27): does age still add once years in the league are held?

The exploration's "age against no age" (method 1) used a baseline with no years in the league, and its obvious-input
check (H) added history and years to a model that already had age. So nothing yet says whether age adds beside years
in the league. The linemen-and-specialists look (m4) found age adds nothing for OL there. Here, for every position the
exploration measured: NH (his pulled rate, his last two seasons, years in the league: no age) against H (NH plus the
cubic in age), and HB (H plus mileage) against NHB (NH plus mileage) for offense. Same rows, walk and scores as
m2_load.py, but all careers (not only those from 1999) for the age rows; mileage rows keep the 1999 rule.
Discovery only; the 2025 vault is closed.

Odds, written before the run (Claude, 2026-11-27):
- Age adds clearly to usage beside years in the league at 3+ of the 4 offensive positions: 45%; about +1% where it
  does, 80% between 0 and +3%.
- On defense (DL, LB, DB), at 2+ of 3: 40%.
- To still playing, pooled over offense: 50%.

Run from pcf/:  python projects/aging/explore/m2_age_beside_years.py   (writes m2_age_beside_years.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import m2_load as M  # noqa: E402
from aging_common import DEF, OFF, Say, pairs  # noqa: E402

c = pl.col
say = Say(Path(__file__).with_suffix(".txt"))
_feats = M.feats


def feats(x, spec, roles_cols):
    X = _feats(x, [s for s in spec if s != "noage"], roles_cols)
    if "noage" in spec:
        X = np.delete(X, [2, 3, 4], axis=1)  # the cubic in age sits right after the intercept and his rate
    return X


M.feats = feats


def main() -> None:
    d_all = pairs().with_columns(c("entry").fill_null(c("season")), cm_risk=pl.lit(0.0))
    d99 = d_all.filter(c("entry") >= 1999)
    say("# Age beside years in the league (2026-11-27)", "")
    specs = {"NH": ["noage", "hist"], "H": ["hist"]}
    say("| Position | Usage (0 if he left): age beside history and years | Still playing (log loss) |", "|---|---|---|")
    clear_off, clear_def = 0, 0
    Fu, Fg = {}, {}
    for pos in OFF + DEF:
        fu = M.walk(M.rows(d_all, pos, "u"), specs, 2010)
        fg = M.walk(M.rows(d_all, pos, "g"), specs, 2010, logit=True)
        Fu[pos], Fg[pos] = fu, fg
        ru = M.pooled({pos: fu}, "H", "NH")
        rg = M.pooled({pos: fg}, "H", "NH", logit=True)
        say(f"| {pos} | {M.fmt(ru)} | {M.fmt(rg)} |")
        if ru[1] > 0:
            if pos in OFF:
                clear_off += 1
            else:
                clear_def += 1
    po = M.pooled({p: Fg[p] for p in OFF}, "H", "NH", logit=True)
    say("", f"Pooled over offense: usage {M.fmt(M.pooled({p: Fu[p] for p in OFF}, 'H', 'NH'))}; still playing {M.fmt(po)}.",
        f"Pooled over defense: usage {M.fmt(M.pooled({p: Fu[p] for p in DEF}, 'H', 'NH'))}; still playing {M.fmt(M.pooled({p: Fg[p] for p in DEF}, 'H', 'NH', logit=True))}.", "")
    # with mileage in both (careers from 1999), offense
    specs2 = {"NHB": ["noage", "hist", "mil"], "HB": ["hist", "mil"]}
    say("With mileage in both (careers from 1999), offense:", "")
    for pos in OFF:
        fu = M.walk(M.rows(d99, pos, "u"), specs2, 2010)
        fg = M.walk(M.rows(d99, pos, "g"), specs2, 2010, logit=True)
        say(f"- {pos}: usage {M.fmt(M.pooled({pos: fu}, 'HB', 'NHB'))}; still playing {M.fmt(M.pooled({pos: fg}, 'HB', 'NHB', logit=True))}")
    say("", f"Bets: offense 3+ of 4: {'held' if clear_off >= 3 else 'failed'} ({clear_off}); defense 2+ of 3: {'held' if clear_def >= 2 else 'failed'} ({clear_def}); "
        f"still playing pooled over offense: {'held' if po[1] > 0 else 'failed'}.")
    say.save()


if __name__ == "__main__":
    main()
