# ruff: noqa: E501
"""Retro 3 (2026-11-23): calibration of the CEO's and Claude's odds since retro 2, from HUNCHES.md and IDEAS.md.

Each entry: (row, stated probability, 1 if it came true, kind). "Held in part" counts as 1 for the CEO's
first number. Unclear verdicts (H84, I94) and bets never scored (the 55% of I90) are left out.
kind: "claim" (a football claim: what is true and whose it is) or "method" (a way to model or measure),
sorted by Claude (W2 was rejected at retro 2, so Claude sorts at each retro).
Run from pcf/:  python projects/retro/explore/retro3_calibration.py > projects/retro/explore/retro3_calibration.txt
"""

import numpy as np

# The CEO's first number, written before the test.
ceo = [
    ("H78 a moving back's share from who is in his new backfield", 0.30, 0, "claim"),
    ("H79 a receiver's plain catch rate repeats and travels", 0.40, 1, "claim"),
    ("H80 two kinds of outside linebacker (the roles exist)", 0.90, 1, "claim"),
    ("H81 coverage numbers repeat and travel", 0.50, 1, "claim"),
    ("H82 sacks are the QB's", 0.60, 1, "claim"),
    ("H83 how a runner is brought down follows the runner", 0.60, 1, "claim"),
    ("H85 a diffusion model uncovers more signal", 0.25, 0, "method"),
    ("H86 conditioning on a play's own pressure", 0.75, 1, "claim"),
    ("H87 play action and quick passing are strategy", 0.75, 1, "claim"),
    ("H88 near-exponential gains downstream", 0.50, 0, "method"),
    ("H89 success as VOE's outcome", 0.75, 0, "method"),
    ("H90 VOE trained on predictable plays", 0.40, 0, "method"),
    ("H91 a below-average counterexample", 0.20, 0, "method"),
    ("H92 a simple net for interactions", 0.50, 0, "method"),
]
# Claude's number for the CEO's claim as worded (W6), written before the test.
claude_main = [
    ("H78", 0.45, 0, "claim"),
    ("H79", 0.60, 1, "claim"),
    ("H80 (as worded, incl. outside roles move with the coordinator)", 0.35, 0, "claim"),
    ("H81", 0.25, 1, "claim"),
    ("H82", 0.70, 1, "claim"),
    ("H83", 0.55, 1, "claim"),
    ("H85", 0.15, 0, "method"),
    ("H86", 0.90, 1, "claim"),
    ("H87", 0.75, 1, "claim"),
    ("H88", 0.10, 0, "method"),
    ("H89 (as defined, both yardsticks)", 0.30, 0, "method"),
    ("H90 (before the snap)", 0.20, 0, "method"),
    ("H91", 0.05, 0, "method"),
    ("H92", 0.15, 0, "method"),
]
# Claude's side bets and its own ideas, scored where the result answers them.
claude_side = [
    ("H78 the remaining backs' shares alone beat the past split", 0.70, 1),
    ("H78 how well everyone ran adds beyond the shares", 0.30, 0),
    ("H80 the role split is clear", 0.85, 1),
    ("H80 within rushers, movers keep 75%+ of pressure rate", 0.65, 0),
    ("H80 an outside linebacker's role moves more than an inside one's", 0.60, 0),
    ("H81 throw depth against repeats 0.3+", 0.45, 1),
    ("H81 passes defensed per target 0.2+", 0.45, 0),
    ("H81 catch rate allowed 0.2+", 0.25, 1),
    ("H81 interceptions 0.2+", 0.10, 1),
    ("H83 broken tackles per carry repeat 0.3+", 0.60, 0),
    ("H83 tacklers needed after the line repeat 0.2+", 0.35, 1),
    ("H84 the repeat goes up for most measures", 0.25, 0),
    ("H84 movers keep more for most measures", 0.60, 1),
    ("H85 matches the trees within the fitting noise on most outcomes", 0.50, 0),
    ("H86 sack's share of error to 10%+ given pressure", 0.80, 1),
    ("H88 downstream gains real but shrinking", 0.60, 0),
    ("H89 the repeat rises 0.05+", 0.50, 0),
    ("H90 weighting raises the held-out play fit", 0.60, 0),
    ("H91 the gap to absence costs halves", 0.55, 0),
    ("H92 named interactions beat the lasso", 0.20, 0),
    ("I80 receiving yards", 0.85, 1),
    ("I80 rushing yards", 0.70, 1),
    ("I89 time to throw is the QB's", 0.70, 0),
    ("I89 target depth the QB's more than the receivers'", 0.60, 0),
    ("I89 the line owns either", 0.35, 0),
    ("I95 quick-pass rate adds to next game's sacks", 0.45, 0),
    ("I100 B's tight-end rows stop losing", 0.55, 0),
    ("I101 the 200-400 gap halves", 0.60, 0),
    ("I101 B then beats A on the vault", 0.35, 0),
]


def show(name, rows):
    p = np.array([r[1] for r in rows])
    y = np.array([r[2] for r in rows])
    brier = np.mean((p - y) ** 2)
    print(f"\n== {name}: {len(rows)} bets, {y.sum()} came true ({y.mean():.0%}), average stated {p.mean():.0%}; Brier {brier:.3f} (always saying 50%: 0.250)")
    for lo, hi in ((0, 0.35), (0.35, 0.55), (0.55, 0.75), (0.75, 1.01)):
        m = (p >= lo) & (p < hi)
        if m.any():
            print(f"   stated {lo:.0%}-{min(hi, 1):.0%}: {m.sum()} bets, average stated {p[m].mean():.0%}, came true {y[m].mean():.0%}")
    if len(rows[0]) == 4:
        for k in ("claim", "method"):
            m = np.array([r[3] == k for r in rows])
            print(f"   {k}s: {y[m].sum()} of {m.sum()} came true, average stated {p[m].mean():.0%}")
    for r in rows:
        print(f"     {r[1]:.0%}  {'yes' if r[2] else 'no '}  {r[0]}")


show("THE CEO, FIRST NUMBER", ceo)
show("CLAUDE, ON THE CEO'S CLAIM AS WORDED", claude_main)
show("CLAUDE, SIDE BETS AND IDEAS", claude_side)
