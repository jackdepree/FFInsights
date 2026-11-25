# ruff: noqa: E501
"""Retro 4 (2026-11-25): calibration of the CEO's and Claude's odds since retro 3, from HUNCHES.md and IDEAS.md.

Each entry: (row, stated probability, 1 if it came true, kind). "Held in part" counts as 1 for the first number
(as at retro 3). Bets the tests never answered are left out (H100's 30% against a role table is in H107's; H101's
"closer than the depth chart's next man" wasn't tested; I113 became the role table without its test; I131 was
settled by the CEO; I123's 30% moved to participation). Where a row's verdict scores its own odds, that reading is used.
kind: "claim" (a football claim: what is true and whose it is) or "method" (a way to model or measure), sorted by
Claude after the results, as at retro 3 (W2 was rejected).
Also: "pays" for each hunch, read from HUNCHES.md's Pays? column (1 = it improved a held-out forecast, any size).
Run from pcf/:  python projects/retro/explore/retro4_calibration.py > projects/retro/explore/retro4_calibration.txt
"""

import numpy as np

# The CEO's first number, written before the test: (row, odds, held, kind, pays)
ceo = [
    ("H93 past injuries, recovery and age forecast time missed", 0.60, 1, "claim", 1),
    ("H94 proneness depends on the injury", 0.30, 1, "claim", 0),
    ("H95 roles differ in injury risk within a position (held in part)", 0.50, 1, "claim", 0),
    ("H96 risk-weighted snaps beat counts", 0.70, 0, "method", 0),
    ("H97 tacklers, a tackle behind the line, long plays raise injury risk (2 of 3)", 0.70, 1, "claim", 1),
    ("H98 a recency-weighted total of risky plays (held, small)", 0.50, 1, "claim", 1),
    ("H99 the plays he's not on say as much about his role", 0.60, 0, "method", 0),
    ("H100 a latent usage space of 4-6 features (held in part)", 0.50, 1, "method", 0),
    ("H101 like-for-like substitutes", 0.40, 1, "claim", 0),
    ("H102 the chance of keeping last season's role (held in part)", 0.60, 1, "claim", 1),
    ("H103 roles gravitate to schemes, combinations predict", 0.75, 0, "claim", 0),
    ("H104 a coach's scheme seeks roles when a starter leaves", 0.30, 0, "claim", 0),
    ("H105 teams target roles in free agency and trades", 0.30, 0, "claim", 0),
    ("H106 archetype against defensive scheme", 0.30, 0, "claim", 0),
    ("H107 a latent space of responsibilities beats labels (held in part)", 0.75, 1, "method", 0),
    ("H108 credit by identity and responsibility (held, by the role's part)", 0.50, 1, "method", 0),
    ("H109 a plus-minus for all players for stayers' shares", 0.75, 1, "method", 1),
    ("H110 efficiency losses bring intake at the group", 0.30, 0, "claim", 0),
    ("H111 roles' coordinates predict recipients better than labels", 0.60, 0, "method", 0),
    ("H112 bringing in a top player against leaving the group empty", 0.30, 0, "claim", 0),
]
# Claude's number for the CEO's claim as worded (W6), written before the test.
claude_main = [
    ("H93", 0.70, 1, "claim"),
    ("H94", 0.70, 1, "claim"),
    ("H95 (held in part)", 0.45, 1, "claim"),
    ("H96", 0.45, 0, "method"),
    ("H97 (2 of 3)", 0.75, 1, "claim"),
    ("H98", 0.30, 1, "claim"),
    ("H99", 0.65, 0, "method"),
    ("H100 (held in part)", 0.70, 1, "method"),
    ("H101 (like-for-like)", 0.85, 1, "claim"),
    ("H102 (held in part)", 0.70, 1, "claim"),
    ("H103", 0.30, 0, "claim"),
    ("H104", 0.55, 0, "claim"),
    ("H105", 0.35, 0, "claim"),
    ("H106", 0.15, 0, "claim"),
    ("H107 (held in part)", 0.80, 1, "method"),
    ("H108", 0.25, 1, "method"),
    ("H109 (against the proportional split)", 0.35, 1, "method"),
    ("H110", 0.25, 0, "claim"),
    ("H111", 0.55, 0, "method"),
    ("H112", 0.25, 0, "claim"),
]
# Claude's side bets and its own ideas, scored where the result answers them: (row, odds, came true, size bet?)
claude_side = [
    ("H93 adds beyond the after-the-fact ceiling", 0.35, 0, 0),
    ("H94 a hamstring repeats 2x+ in season", 0.40, 0, 1),
    ("H95 roles differ within a position", 0.60, 1, 0),
    ("H95 high variance in yards per play, more injuries", 0.30, 0, 0),
    ("H97 all three features", 0.45, 0, 0),
    ("H99 part-timers gain 0.05+", 0.55, 0, 1),
    ("H99 every-down players: nothing", 0.85, 0, 0),
    ("H100 top components repeat season to season 0.5+", 0.75, 0, 1),
    ("H100 stable loadings", 0.60, 1, 0),
    ("H101 like-for-like more for TE and RB than WR", 0.55, 1, 0),
    ("H102 already by week 4", 0.50, 1, 0),
    ("H103 roles cluster on schemes", 0.80, 1, 0),
    ("H104 newcomers nearer their own team's departed player", 0.60, 1, 0),
    ("H106 an interaction clear in-sample", 0.45, 0, 0),
    ("H107 beyond last season's volume", 0.45, 0, 1),
    ("H107 beats a role table of the same size", 0.30, 0, 0),
    ("H108 target group movers r 0.2+ (at the line, not cleared)", 0.50, 0, 1),
    ("H109 target and carry share too (against 1a)", 0.30, 1, 0),
    ("H109 weekly absences", 0.50, 1, 0),
    ("H110 he left: more intake (as specified)", 0.85, 0, 0),
    ("H111 beyond his current share", 0.35, 0, 0),
    ("H112 the spread differs", 0.20, 0, 0),
    ("H112 stayers grow less where a top player came in", 0.90, 1, 0),
    ("I29 the long-drive rise halves", 0.60, 0, 1),
    ("I30 it's the day's matchup (fails)", 0.75, 1, 0),
    ("I43 passing-down share in contracts", 0.75, 1, 0),
    ("I48 garbage time pooled ties, weight 0.8+", 0.75, 0, 1),
    ("I50 backups rise late in long drives (held, smaller)", 0.75, 1, 1),
    ("I50 the backup share explains I30", 0.60, 0, 0),
    ("I57 his own routes beat the position's mix", 0.90, 1, 0),
    ("I57 the role table adds beyond", 0.40, 1, 0),
    ("I58 QB red-zone carries 2%+ (nine seasons; the vault reversed it)", 0.70, 1, 1),
    ("I59 pass-heavy receivers 1%+", 0.30, 0, 1),
    ("I60 games played worth 2+ points", 0.60, 0, 1),
    ("I61 past thrown TDs fall under 2% given the passer", 0.50, 0, 1),
    ("I67 participation worth less on QB rushing", 0.70, 1, 0),
    ("I70 passing rises, the rest move under 1 point", 0.65, 0, 1),
    ("I75 continuity, defense 2%+", 0.50, 0, 1),
    ("I75 continuity, offense 2%+", 0.30, 0, 1),
    ("I84 receivers: own share wins", 0.80, 0, 0),
    ("I84 backs: the slot wins or ties", 0.75, 1, 0),
    ("I114 the line, team yards 2%+", 0.75, 1, 1),
    ("I114 the line, players' yards", 0.40, 0, 0),
    ("I116 players' 1+ error under 3, slope 0.9-1.1", 0.70, 1, 1),
    ("I116 thrown touchdowns too", 0.45, 0, 1),
    ("I118 the opener 3%+ for team touchdowns", 0.75, 1, 1),
    ("I121 proneness 0.5%+ receiving", 0.45, 0, 1),
    ("I121 proneness, rushing", 0.30, 0, 0),
    ("I122 the shrunk vacancy wins clearly", 0.55, 1, 0),
    ("I123 fewer flips than 14% (coarse yes, fine no)", 0.60, 1, 0),
    ("I124 3+ of 6 pooled defensive axes repeat", 0.60, 1, 0),
    ("I124 within position too", 0.35, 1, 0),
    ("I124 positions blur", 0.70, 1, 0),
    ("I124 beats labels on tackles and rushes", 0.60, 1, 0),
    ("I125 the plus-minus beats no change where left empty", 0.55, 1, 0),
    ("I125 the proportional split does too", 0.35, 0, 0),
    ("I128 the team's Questionable habit", 0.45, 0, 0),
    ("I129 the healthy rate counts releases, 2%+", 0.65, 1, 1),
    ("I130 a narrower chain", 0.55, 0, 0),
    ("I132 measurables beat the position mean (one axis, WRs)", 0.60, 1, 0),
    ("I133 the fullbacks fix turns rushing to a tie", 0.50, 1, 0),
    ("I134 the band: median under 14%", 0.45, 0, 1),
    ("I134 DL and OLB under 20%", 0.70, 0, 1),
    ("I134 the band forecasts as well", 0.80, 1, 0),
    ("I135 the 4-feature table, receiving", 0.40, 1, 0),
    ("I135 the 4-feature table, rushing", 0.30, 1, 0),
    ("I136 like-for-like on the role table", 0.55, 1, 0),
    ("I49 swap pairs: the partner gains more (vacated's pair part, +2.3%, clear)", 0.75, 1, 0),
]


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def show(name, rows, kinds=None):
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
            print(f"   {k}s: {y[m].sum()} of {m.sum()} came true, average stated {p[m].mean():.0%}, Brier {brier(p[m], y[m]):.3f}")
    for r in rows:
        print(f"     {r[1]:.0%}  {'yes' if r[2] else 'no '}  {r[0]}")
    return p, y


p, y = show("THE CEO, FIRST NUMBER", ceo, kinds=3)
pays = np.array([r[4] for r in ceo])
for k in ("claim", "method"):
    m = np.array([r[3] == k for r in ceo])
    print(f"   {k}s that pay (any held-out gain): {pays[m].sum()} of {m.sum()}")
show("CLAUDE, ON THE CEO'S CLAIM AS WORDED", claude_main, kinds=3)
ps, ys = show("CLAUDE, SIDE BETS AND IDEAS", claude_side)
sz = np.array([r[3] for r in claude_side]) == 1
print(f"   size bets: {ys[sz].sum()} of {sz.sum()} came true, average stated {ps[sz].mean():.0%}, Brier {brier(ps[sz], ys[sz]):.3f}")
print(f"   other bets: {ys[~sz].sum()} of {(~sz).sum()} came true, average stated {ps[~sz].mean():.0%}, Brier {brier(ps[~sz], ys[~sz]):.3f}")
# the same 20 hunches: who was closer, bet by bet
pc = np.array([r[1] for r in ceo])
pm = np.array([r[1] for r in claude_main])
yy = np.array([r[2] for r in ceo])
closer = (np.abs(pm - yy) < np.abs(pc - yy)).sum()
print(f"\n== Head to head on the same 20 hunches: Claude closer on {closer}, the CEO on {(np.abs(pc - yy) < np.abs(pm - yy)).sum()}, level {(np.abs(pc - yy) == np.abs(pm - yy)).sum()}")
