"""Aging, a follow-up to method 2 (2026-11-27, before the brief): does mileage still add once a longer history is held?

The exploration's case against: "Mileage is career usage. The obvious-input check shrinks its gain by about 40% for usage
and makes efficiency's unclear. Some of what's left may be the history the check didn't hold: three seasons back, or
his peak." Here H (age, his last two seasons' pulled rate, years in the league) gets two more inputs: his pulled rate
three seasons back, and his career peak of that rate through this season (HL). Then mileage on top (HLB against HL).
Same rows, walk and scores as m2_load.py (careers from 1999, targets 2010-2024, players resampled within position,
positions weighing the same). Discovery only; the 2025 vault is closed.

Odds, written before the run (Claude, 2026-11-27):
- Mileage's usage gain stays clear beside the longer history (HLB against HL, interval above 0): 55%. Size: about
  +0.8% of usage's error, 80% between +0.2% and +1.4%.
- Mileage's efficiency gain stays unclear: 75%.
- The longer history itself adds clearly to H for usage: 60%; about +0.5%, 80% between 0 and +1.5%.

Run from pcf/:  python projects/aging/explore/m2_history_check.py   (writes m2_history_check.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import m2_load as M  # noqa: E402
from aging_common import OFF, Say, pairs  # noqa: E402

c = pl.col
say = Say(Path(__file__).with_suffix(".txt"))
_feats = M.feats


def feats(x, spec, roles_cols):
    X = _feats(x, [s for s in spec if s != "long"], roles_cols)
    if "long" in spec:
        X = np.column_stack([X, x["l3"].fill_null(0).to_numpy(), x["l3"].is_null().to_numpy().astype(float), x["peak"].to_numpy()]).astype(float)
    return X


M.feats = feats


def rows(d, pos, kind):
    x = M.rows(d, pos, kind)
    lag = "pe" if kind == "e" else "pu"
    L = d.select("gsis_id", "season", lag).unique(["gsis_id", "season"]).sort("season")
    L = L.with_columns(peak=c(lag).cum_max().over("gsis_id"))
    x = x.join(L.select("gsis_id", season=c("season") + 3, l3=lag), on=["gsis_id", "season"], how="left")
    return x.join(L.select("gsis_id", "season", "peak"), on=["gsis_id", "season"], how="left").with_columns(c("peak").fill_null(c("x")))


def main() -> None:
    d = pairs().filter(c("entry") >= 1999).with_columns(cm_risk=pl.lit(0.0))
    specs = {"H": ["age", "hist"], "HB": ["age", "hist", "mil"], "HL": ["age", "hist", "long"], "HLB": ["age", "hist", "long", "mil"]}
    F = {(k, p): M.walk(rows(d, p, k), specs, 2010, logit=(k == "g")) for k in ("u", "e", "g") for p in OFF}
    say("# Mileage beside a longer history (2026-11-27)", "", f"Pairs from careers starting 1999+: {d.height:,}.", "",
        "| Comparison | Usage (0 if he left) | Efficiency | Still playing (log loss) |", "|---|---|---|---|")
    res = {}
    for new, old, label in (("HB", "H", "H + mileage against H (the exploration's row)"), ("HL", "H", "HL (H + three seasons back + career peak) against H"),
                            ("HLB", "HL", "HL + mileage against HL")):
        r = [M.pooled({p: F[(k, p)] for p in OFF}, new, old, logit=(k == "g")) for k in ("u", "e", "g")]
        res[(new, old)] = r
        say(f"| {label} | {M.fmt(r[0])} | {M.fmt(r[1])} | {M.fmt(r[2])} |")
    say("", "By position, HL + mileage against HL (usage; efficiency; still playing):", "")
    for p in OFF:
        say(f"- {p}: " + "; ".join(M.fmt(res[('HLB', 'HL')][i][3][p]) for i in range(3)))
    u, e = res[("HLB", "HL")][0], res[("HLB", "HL")][1]
    say("", f"Bets: mileage's usage gain clear beside the longer history: {'held' if u[1] > 0 else 'failed'} ({M.fmt(u)}); "
        f"efficiency stays unclear: {'held' if not (e[1] > 0) else 'failed'}; the longer history adds to H for usage: {'held' if res[('HL', 'H')][0][1] > 0 else 'failed'}.")
    say.save()


if __name__ == "__main__":
    main()
