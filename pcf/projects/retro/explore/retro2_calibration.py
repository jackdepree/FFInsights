# ruff: noqa: E501
"""Retro 2 (2026-11-20): calibration of the CEO's and Claude's odds, from the rows of HUNCHES.md and IDEAS.md.

Each entry: (row, the stated probability, 1 if it came true). "Held in part" counts as 1.
Run from pcf/:  python projects/retro/explore/retro2_calibration.py > projects/retro/explore/retro2_calibration.txt
"""

ceo = [
    ("H50", 0.60, 1),
    ("H51", 0.75, 1),
    ("H52", 0.60, 0),
    ("H54", 0.40, 1),
    ("H55", 0.70, 1),
    ("H56", 0.80, 1),
    ("H57", 0.25, 1),
    ("H59", 0.80, 1),
    ("H60", 0.30, 0),
    ("H67", 0.40, 1),
    ("H68", 0.50, 0),
    ("H69", 0.75, 1),
    ("H70", 0.60, 0),
    ("H72", 0.90, 0),
    ("H73", 0.60, 0),
    ("H75", 0.90, 1),
]
cl = [
    ("H50a", 0.60, 1),
    ("H50b", 0.25, 0),
    ("H51", 0.70, 1),
    ("H52", 0.20, 0),
    ("H54", 0.60, 1),
    ("H55a", 0.80, 1),
    ("H55b", 0.40, 1),
    ("H56a", 0.90, 1),
    ("H56b", 0.40, 0),
    ("H57", 0.60, 1),
    ("H59", 0.97, 1),
    ("H60", 0.20, 0),
    ("H61", 0.65, 1),
    ("H62a", 0.30, 0),
    ("H62b", 0.70, 1),
    ("H63a", 0.05, 0),
    ("H63b", 0.85, 1),
    ("H64", 0.15, 0),
    ("H65a", 0.97, 1),
    ("H65b", 0.30, 0),
    ("H66a", 0.85, 0),
    ("H66b", 0.10, 0),
    ("H67a", 0.65, 1),
    ("H67b", 0.20, 1),
    ("H68a", 0.80, 0),
    ("H68b", 0.25, 0),
    ("H68c", 0.15, 0),
    ("H69a", 0.60, 1),
    ("H69b", 0.40, 1),
    ("H70a", 0.45, 0),
    ("H70b", 0.30, 0),
    ("H72a", 0.85, 0),
    ("H72b", 0.35, 0),
    ("H72c", 0.30, 0),
    ("H73", 0.20, 0),
    ("H75a", 0.50, 0),
    ("H75b", 0.85, 1),
    ("I47", 0.90, 1),
    ("I63", 0.40, 0),
    ("I65a", 0.60, 0),
    ("I65b", 0.40, 0),
    ("I69a", 0.85, 1),
    ("I69b", 0.70, 0),
    ("I73a", 0.70, 1),
    ("I73b", 0.35, 0),
    ("I74a", 0.60, 0),
    ("I74b", 0.40, 0),
]


def rep(name, L):
    n = len(L)
    mc = sum(p for _, p, _ in L) / n
    hr = sum(y for *_, y in L) / n
    brier = sum((p - y) ** 2 for _, p, y in L) / n
    base = sum((hr - y) ** 2 for *_, y in L) / n
    print(
        f"{name}: n {n}, mean conf {mc:.0%}, came true {hr:.0%}, Brier {brier:.3f} (always-the-base-rate {base:.3f}, a coin 0.250)"
    )
    bands = [(0, 0.35), (0.35, 0.55), (0.55, 0.75), (0.75, 0.86), (0.86, 1.01)]
    for lo, hi in bands:
        B = [x for x in L if lo <= x[1] < hi]
        if B:
            print(
                f"   {lo:.0%}-{hi:.0%}: {len(B)} bets, mean conf {sum(p for _, p, _ in B) / len(B):.0%}, true {sum(y for *_, y in B)}/{len(B)} = {sum(y for *_, y in B) / len(B):.0%}  {[k for k, _, _ in B]}"
            )


rep("CEO", ceo)
rep("Claude", cl)
# Claude on the CEO's hunches only, main claim


# The same 16 CEO bets: (row, the CEO's odds, Claude's odds on the CEO's own claim, came true, c claim or m method)
E = [
    ("H50", 0.60, 0.40, 1, "c"),
    ("H51", 0.75, 0.70, 1, "c"),
    ("H52", 0.60, 0.20, 0, "c"),
    ("H54", 0.40, 0.60, 1, "c"),
    ("H55", 0.70, 0.80, 1, "c"),
    ("H56", 0.80, 0.90, 1, "c"),
    ("H57", 0.25, 0.60, 1, "c"),
    ("H59", 0.80, 0.97, 1, "c"),
    ("H60", 0.30, 0.20, 0, "m"),
    ("H67", 0.40, 0.65, 1, "c"),
    ("H68", 0.50, 0.15, 0, "c"),
    ("H69", 0.75, 0.60, 1, "m"),
    ("H70", 0.60, 0.45, 0, "m"),
    ("H72", 0.90, 0.85, 0, "m"),
    ("H73", 0.60, 0.20, 0, "m"),
    ("H75", 0.90, 0.65, 1, "m"),
]
print("\nHead to head on the CEO's 16 bets")
for k, name in (("c", "claims"), ("m", "methods"), (None, "all")):
    S = [e for e in E if k is None or e[4] == k]
    n = len(S)
    print(
        f"  {name}: {n} bets, held {sum(e[3] for e in S)}; average odds CEO {sum(e[1] for e in S) / n:.0%}, Claude {sum(e[2] for e in S) / n:.0%}; "
        f"Brier CEO {sum((e[1] - e[3]) ** 2 for e in S) / n:.3f}, Claude {sum((e[2] - e[3]) ** 2 for e in S) / n:.3f}"
    )
print(f"  Claude closer on {sum(abs(e[2] - e[3]) < abs(e[1] - e[3]) for e in E)} of {len(E)}")
