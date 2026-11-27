# ruff: noqa: E501
"""Retro 5 (2026-11-26): calibration of the CEO's and Claude's odds since retro 4, from HUNCHES.md, IDEAS.md, the
three builds' RESULTS and PREREG files, their spot-checks, and the stabilization and aging explorations.

Each entry: (row, stated probability, 1 if it came true, ...). As at retros 3 and 4: "held in part" counts as 1,
bets the tests never answered are left out (I9's 40%, never run; I76's 70%, unreadable for QBs; I148's 45%, unclear;
I79's second and third bets, which had no number of their own), and a "held by its rule" result counts as 1 for the
bet as written.

Aging's hunches (H115-H122) are on the unmerged `pcf/aging` branch, with verdicts proposed and not yet closed by the
CEO. They are scored apart, on the proposed verdicts, and flagged provisional. H117's told-apart half and H119's real
half pass their written rules but are proposed failed (both are the pull-back); the proposed verdict is scored, and the
last section shows what changes if the written rule is scored instead.

kind: "claim" or "method", sorted by Claude after the results (W2 was rejected), as before.
Run from pcf/:  python projects/retro/explore/retro5_calibration.py > projects/retro/explore/retro5_calibration.txt
"""

import numpy as np

# The CEO's first number, written before the test: (row, odds, held, kind, pays)
ceo_closed = [
    ("H113 teammates prop a player's rates up or down (held, narrowly)", 0.25, 1, "claim", 1),
    ("H114 a consistent measure sets where the others regress to (held, by chance's margin)", 0.25, 1, "method", 1),
]
ceo_aging = [  # provisional: proposed verdicts, the CEO hasn't closed them
    ("H115 mileage split by kind beats age alone (held by its rule)", 0.30, 1, "claim", 1),
    ("H116 roles add to mileage and age", 0.30, 0, "method", 0),
    ("H117 two ways to decline, told apart (proposed failed)", 0.45, 0, "claim", 0),
    ("H118 risk-weighted mileage beats age alone (held by its rule)", 0.50, 1, "method", 1),
    ("H120 stars age differently", 0.60, 1, "claim", 1),
    ("H121 positions and roles age differently", 0.95, 1, "claim", 1),
    ("H122 usage shows aging better than efficiency", 0.80, 1, "claim", 1),
]
# Claude's number for the CEO's claim as worded (W6)
claude_main = [
    ("H113 (real)", 0.70, 1, "claim"),
    ("H114 (1+ rate)", 0.45, 1, "method"),
]
claude_main_aging = [
    ("H115 (both kinds)", 0.25, 1, "claim"),
    ("H116 (both kinds)", 0.30, 0, "method"),
    ("H117 (real)", 0.65, 0, "claim"),
    ("H118", 0.25, 1, "method"),
    ("H119 (real; the rule passes by a hair, proposed failed)", 0.20, 0, "claim"),
    ("H120", 0.60, 1, "claim"),
    ("H121", 0.90, 1, "claim"),
    ("H122", 0.70, 1, "claim"),
]
# Claude's side bets, ideas and build odds: (row, odds, came true, size bet?, source)
claude_side = [
    # stabilization's exploration
    ("H113 pays", 0.25, 1, 0, "stab-explore"),
    ("H114 most rates", 0.30, 0, 0, "stab-explore"),
    ("Drift: the filter beats static for half the measures", 0.40, 0, 0, "stab-explore"),
    ("Ranges hold 75-85%", 0.60, 1, 0, "stab-explore"),
    ("New level within 0.1 in every bin", 0.50, 0, 0, "stab-explore"),
    ("Twin beats M1 for 1+ rate", 0.55, 1, 0, "stab-explore"),
    ("Diffusion beats the twin", 0.15, 0, 0, "stab-explore"),
    ("Diffusion's ranges closer to 80%", 0.35, 0, 0, "stab-explore"),
    # stabilization's build: ideas
    ("I154 a game-noise factor above 1.2, then ties", 0.55, 0, 0, "stab-build"),
    ("I182 omega fits better", 0.40, 0, 0, "stab-build"),
    ("I155 the adjusted game split above 0.3 for 1+", 0.60, 1, 0, "stab-build"),
    ("I155 for pass rate over expected", 0.30, 1, 0, "stab-build"),
    ("I156 the second pull helps 1+ shipped expert", 0.50, 1, 0, "stab-build"),
    ("I152 (its form) the trend clears 1+ usage rate", 0.30, 1, 0, "stab-build"),
    ("I181 layered credibility, 2+ usage rates", 0.35, 0, 0, "stab-build"),
    ("I173 (its form) a movers' slope, 1+ of 20", 0.30, 1, 0, "stab-build"),
    ("I173 (its form) 5+ of 20", 0.10, 0, 0, "stab-build"),
    ("I174 per-position target slopes", 0.35, 0, 0, "stab-build"),
    ("I174 for tight ends alone", 0.50, 0, 0, "stab-build"),
    ("I104 (its form) this season's k, 1+ efficiency rate", 0.20, 0, 0, "stab-build"),
    ("I180 the correlation rises 0.02+", 0.60, 0, 1, "stab-build"),
    ("I5 (its form) rookies' usage misses positive", 0.55, 0, 0, "stab-build"),
    ("I14 widening improves half the shipped rates", 0.60, 0, 0, "stab-build"),
    # stabilization's build: the brief's odds (decision 0052)
    ("The second pull beats M1 for 12+ of 20", 0.55, 0, 0, "stab-build"),
    ("The ridge beats the rung below for 4+ of 20", 0.40, 0, 0, "stab-build"),
    ("The ridge for 1+", 0.75, 1, 0, "stab-build"),
    ("The filter, 4+ of 7 usage rates", 0.50, 1, 0, "stab-build"),
    ("The filter, 4+ of 7 offensive tendencies", 0.65, 1, 0, "stab-build"),
    ("The bar holds next season for 16+ of 20", 0.60, 1, 0, "stab-build"),
    ("Every shipped range in 75-85%, next 4 games", 0.50, 1, 0, "stab-build"),
    ("The same next season before conformal", 0.35, 0, 0, "stab-build"),
    ("Routes stand-in r 0.95+", 0.85, 1, 0, "stab-build"),
    ("Run-snap stand-in close", 0.45, 0, 0, "stab-build"),
    ("Defensive pass-snap stand-in close", 0.55, 1, 0, "stab-build"),
    ("At least one stand-in too poor", 0.40, 1, 0, "stab-build"),
    ("Career: drift beats M1 for 2+ of 8", 0.55, 1, 0, "stab-build"),
    ("The trend clears the shipped rung for 12+ of 20", 0.65, 0, 0, "stab-build"),
    ("The history's coverage in 74-90%", 0.75, 1, 0, "stab-build"),
    ("No lead back above 1 (I180 alone)", 0.55, 0, 0, "stab-build"),
    ("At most 2 above 1 (I180 alone)", 0.80, 0, 0, "stab-build"),
    ("Carries a run snap still beats the average in season", 0.85, 1, 0, "stab-build"),
    ("Its correlation stays 0.918 +- 0.01", 0.90, 1, 0, "stab-build"),
    # stabilization's spot-check
    ("Slopes within 0.1 of 2024's for 8+ of 11", 0.55, 1, 0, "stab-spot"),
    ("The pull beats M1 in 6+ of 7 seasons for 6+ of 11", 0.50, 0, 0, "stab-spot"),
    ("The walk-forward slope gets 70%+ of hindsight for 8+", 0.60, 1, 0, "stab-spot"),
    ("In-season slopes in 0.95-1.05 for most", 0.70, 0, 0, "stab-spot"),
    ("Dropping it ties 2+ shipped rates", 0.50, 1, 0, "stab-spot"),
    # vacated's build
    ("I55 the first game back, 1.5-2.5 points recovered (high)", 0.90, 0, 1, "vac-build"),
    ("I143 COVID rates agree", 0.65, 0, 0, "vac-build"),
    ("I143 the COVID rate is higher", 0.25, 1, 0, "vac-build"),
    ("I126 Z beats P where left empty", 0.25, 0, 0, "vac-build"),
    ("I136/I122 closeness beats the pooled rate offseason", 0.35, 0, 0, "vac-build"),
    ("I160 recalibrating gains on targets", 0.55, 0, 0, "vac-build"),
    ("I160 on snaps", 0.20, 0, 0, "vac-build"),
    ("I161 the trees' absence part on snaps", 0.40, 0, 0, "vac-build"),
    ("I161 on targets", 0.25, 0, 0, "vac-build"),
    ("I162 the choice model beats the plus-minus, targets", 0.25, 0, 0, "vac-build"),
    ("I162 on carries", 0.20, 0, 0, "vac-build"),
    ("I162 it beats no change", 0.80, 1, 0, "vac-build"),
    ("I164 a sudden absence transfers more", 0.60, 1, 0, "vac-build"),
    ("I164 by 0.03-0.06", 0.60, 0, 1, "vac-build"),
    ("I163 the nests below 1, WR and TE", 0.75, 0, 0, "vac-build"),
    ("I163 for RB", 0.60, 0, 0, "vac-build"),
    ("I165 the shrink beats the unshrunk on snaps", 0.60, 1, 0, "vac-build"),
    ("I165 then beats no change on targets", 0.55, 1, 0, "vac-build"),
    ("I165 on carries", 0.35, 0, 0, "vac-build"),
    ("vacated-live beats 19 copies, snaps", 0.95, 1, 0, "vac-build"),
    ("vacated-live beats 19 copies, targets", 0.95, 1, 0, "vac-build"),
    ("vacated-live beats 19 copies, carries", 0.95, 1, 0, "vac-build"),
    ("Beside participation (snaps)", 0.85, 1, 0, "vac-build"),
    ("Beside opportunity-quality (targets)", 0.80, 1, 0, "vac-build"),
    ("Beside opportunity-quality (carries)", 0.80, 1, 0, "vac-build"),
    ("The yardstick, receiving", 0.45, 1, 0, "vac-build"),
    ("The yardstick, rushing", 0.45, 1, 0, "vac-build"),
    ("Offseason left empty, snaps", 0.60, 1, 0, "vac-build"),
    ("Offseason left empty, targets", 0.55, 1, 0, "vac-build"),
    ("Offseason left empty, carries", 0.40, 0, 0, "vac-build"),
    ("Offseason, the lines' snaps", 0.75, 1, 0, "vac-build"),
    ("Offseason gated, all stayers", 0.55, 1, 0, "vac-build"),
    ("The offseason yardstick counts", 0.25, 1, 0, "vac-build"),
    # vacated's spot-check
    ("Shrink: beats 19 shuffles", 0.85, 1, 0, "vac-spot"),
    ("Shrink: 6+ of 8 seasons", 0.55, 1, 0, "vac-spot"),
    ("Shrink: TEs carry the largest gain", 0.55, 1, 0, "vac-spot"),
    ("Shrink: all 8 drops above 0", 0.40, 0, 0, "vac-spot"),
    ("Shrink: hindsight within 1 point", 0.70, 1, 0, "vac-spot"),
    ("Shrink: still ships", 0.75, 1, 0, "vac-spot"),
    # skill-over-expected's build
    ("I90 QB movers keep under half of sacks per pressure, both halves", 0.55, 0, 0, "skill-build"),
    ("I90 sacks per dropback follows the QB more", 0.70, 1, 0, "skill-build"),
    ("I170 pressures add for DL rushers", 0.55, 1, 0, "skill-build"),
    ("I170 by +3 to +6%", 0.55, 0, 1, "skill-build"),
    ("I171 the split pays for movers", 0.25, 1, 0, "skill-build"),
    ("I171 by 5-15%", 0.25, 0, 1, "skill-build"),
    ("I172 a tie for every trait", 0.70, 1, 0, "skill-build"),
    ("I172 per-group wins somewhere", 0.20, 0, 0, "skill-build"),
    ("I79 RBs: no efficiency measure makes 'use'", 0.75, 0, 0, "skill-build"),
    ("I76 linemen: the team's share larger", 0.60, 1, 0, "skill-build"),
    ("I112 beats the plain rate", 0.45, 0, 0, "skill-build"),
    ("I112 for movers", 0.65, 0, 0, "skill-build"),
    # skill-over-expected's spot-check
    ("85-120 movers", 0.70, 0, 1, "skill-spot"),
    ("Pressures' gain clear, +8 to +20%", 0.60, 1, 1, "skill-spot"),
    ("Rush share's gain clear, +10 to +25%", 0.65, 1, 1, "skill-spot"),
    ("Beats all 20 copies (pressures)", 0.50, 0, 0, "skill-spot"),
    ("Beats all 20 copies (rush share)", 0.60, 0, 0, "skill-spot"),
    ("No season carries more than half", 0.70, 0, 0, "skill-spot"),
    ("Clear without any one new team", 0.60, 0, 0, "skill-spot"),
    ("It's scheme", 0.75, 0, 0, "skill-spot"),
    ("Changes something that ships", 0.20, 1, 0, "skill-spot"),
]
claude_side_aging = [  # aging's exploration, unmerged branch; Claude's own side bets
    ("H115 side: one kind at one position", 0.40, 1, 0, "aging"),
    ("H116 side: usage alone", 0.45, 0, 0, "aging"),
    ("H117 told apart (the rule passes; proposed failed)", 0.30, 0, 0, "aging"),
    ("H118 side: D beats B for RB", 0.35, 0, 0, "aging"),
    ("H119 forecastable", 0.10, 0, 0, "aging"),
    ("H120 side: the difference is in usage", 0.45, 1, 0, "aging"),
    ("H121 side: roles within a position", 0.55, 0, 0, "aging"),
    ("Age against no age: usage at 4 of 4", 0.80, 0, 0, "aging"),
    ("Age against no age: efficiency at 2+", 0.50, 0, 0, "aging"),
    ("The ghosts steeper after 30", 0.85, 1, 0, "aging"),
    ("The risk score's AUC above 0.6", 0.60, 1, 0, "aging"),
    ("The hidden-state model beats its twin", 0.20, 1, 0, "aging"),
]


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def show(name, rows, kinds=None, detail=True):
    p = np.array([r[1] for r in rows])
    y = np.array([r[2] for r in rows])
    print(f"\n== {name}: {len(rows)} bets, {y.sum()} came true ({y.mean():.0%}), average stated {p.mean():.0%}; Brier {brier(p, y):.3f} (always saying 50%: 0.250)")
    for lo, hi in ((0, 0.35), (0.35, 0.55), (0.55, 0.75), (0.75, 1.01)):
        m = (p >= lo) & (p < hi)
        if m.any():
            print(f"   stated {lo:.0%}-{min(hi, 1):.0%}: {m.sum()} bets, average stated {p[m].mean():.0%}, came true {y[m].mean():.0%}")
    if kinds is not None:
        for k in ("claim", "method"):
            m = np.array([r[kinds] == k for r in rows])
            if m.any():
                print(f"   {k}s: {y[m].sum()} of {m.sum()} came true, average stated {p[m].mean():.0%}, Brier {brier(p[m], y[m]):.3f}")
    if detail:
        for r in rows:
            print(f"     {r[1]:.0%}  {'yes' if r[2] else 'no '}  {r[0]}")
    return p, y


show("THE CEO, FIRST NUMBER, CLOSED (H113, H114)", ceo_closed, kinds=3)
show("THE CEO, FIRST NUMBER, AGING (PROVISIONAL)", ceo_aging, kinds=3)
p, y = show("THE CEO, ALL NINE (PROVISIONAL)", ceo_closed + ceo_aging, kinds=3, detail=False)
pays = np.array([r[4] for r in ceo_closed + ceo_aging])
print(f"   pays (any held-out gain): {pays.sum()} of {len(pays)}")
show("CLAUDE, ON THE CEO'S CLAIM AS WORDED (ALL TEN, AGING PROVISIONAL)", claude_main + claude_main_aging, kinds=3)
# head to head on the nine with both numbers (H119 has no CEO odds)
both = [(c[1], m[1], c[2]) for c, m in zip(ceo_closed + ceo_aging, claude_main + [r for r in claude_main_aging if not r[0].startswith("H119")])]
pc, pm, yy = (np.array(v) for v in zip(*both))
print(f"\n== Head to head on the same {len(both)} hunches: Claude closer on {(np.abs(pm - yy) < np.abs(pc - yy)).sum()}, the CEO on {(np.abs(pc - yy) < np.abs(pm - yy)).sum()}, level {(np.abs(pc - yy) == np.abs(pm - yy)).sum()}; Brier CEO {brier(pc, yy):.3f}, Claude {brier(pm, yy):.3f}")
rows = claude_side + claude_side_aging
ps, ys = show("CLAUDE, SIDE BETS, IDEAS AND BUILD ODDS", rows, detail=False)
sz = np.array([r[3] for r in rows]) == 1
print(f"   size bets: {ys[sz].sum()} of {sz.sum()} came true, average stated {ps[sz].mean():.0%}, Brier {brier(ps[sz], ys[sz]):.3f}")
print(f"   other bets: {ys[~sz].sum()} of {(~sz).sum()} came true, average stated {ps[~sz].mean():.0%}, Brier {brier(ps[~sz], ys[~sz]):.3f}")
for src in ("stab-explore", "stab-build", "stab-spot", "vac-build", "vac-spot", "skill-build", "skill-spot", "aging"):
    m = np.array([r[4] == src for r in rows])
    print(f"   {src}: {ys[m].sum()} of {m.sum()} came true, average stated {ps[m].mean():.0%}, Brier {brier(ps[m], ys[m]):.3f}")
# W11 (size bets start at 35%): the size bets written after retro 4
print("\n   size bets in detail:")
for r in rows:
    if r[3]:
        print(f"     {r[1]:.0%}  {'yes' if r[2] else 'no '}  {r[0]}")
# confident bets that failed
print("\n   bets at 70%+ that failed:")
for r in rows:
    if r[1] >= 0.70 and not r[2]:
        print(f"     {r[1]:.0%}  {r[0]} ({r[4]})")

# sensitivity: score H117's told-apart half and H119's real half by their written rules (both pass)
alt_main = [(r[0], r[1], 1 if r[0].startswith("H119") else r[2], r[3]) for r in claude_main + claude_main_aging]
alt_side = [(r[0], r[1], 1 if r[0].startswith("H117 told") else r[2]) + r[3:] for r in rows]
pa = np.array([r[1] for r in alt_main]); ya = np.array([r[2] for r in alt_main])
pb = np.array([r[1] for r in alt_side]); yb = np.array([r[2] for r in alt_side])
print(f"\n== Sensitivity, the written rules scored instead: Claude on the CEO's claims Brier {brier(pa, ya):.3f}; side bets {brier(pb, yb):.3f}")
