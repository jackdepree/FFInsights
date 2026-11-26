# The CEO's spot-check: inside linebackers' movers (I171, R6)

**Asked** by the CEO on 2026-11-26: "Can you spot check the inside linebacker result?" The result under check is RESULTS R6 (F115). For inside linebackers who change teams, the first owner split (his shrunk rate plus his new team's rate at his position) beat his shrunk rate alone:
- pressures +20.7% (+10.1 to +29.8);
- rush share +27.9% (+17.4 to +37.9);
- 66 movers.

**Run after the CEO's reclassification** (same day): 4-3 outside linebackers who play off the ball count as inside linebackers, by rule. The rule moves an OLB player-season whose role-table fine role is off-ball: box linebacker or base defensive back (decision 0051 call 31).

## Odds, written before the rerun and before any spot-check number (Claude, 2026-11-26)

1. **Movers.** The movers in the scored inside-linebacker pairs go from 66 to between 85 and 120 (70%).
2. **Pressures.** The movers' gain still clears zero after the reclassification: 60%. Size: +8% to +20%.
3. **Rush share.** The same: 65%. Size: +10% to +25%.
4. **The shuffle test.** The movers' gain beats all 20 copies with the new team's part shuffled within season: 50% for pressures, 60% for rush share.
5. **Seasons.** No single target season carries more than half of either gain: 70%.
6. **Teams.** Dropping any one new team leaves the gain clear of zero: 60%.
7. **Role or scheme?** It's scheme: the new team's part predicts the change in his own rate, and the gain is concentrated in movers whose new team uses inside linebackers differently from the old (the team change above the median in size). 75%.
8. **What ships.** The spot-check, beyond the reclassification itself, changes something that ships: 20%. The history has no split rung, so a change would be to the interface card's advice for movers.

## Results (`build/spot_check.py`, `build/spot_check.txt`; the build's rerun, decision 0051 calls 31-33)

**In one line:** the inside linebackers' movers result is real but means something else. A mover's team-owned trait falls back toward the average more than a stayer's. His new team's rate adds nothing beyond that pull; a random inside linebacker's team rate does as well.

**Walking through it:**

1. **The rows.** The reclassification moves 472 of 1,280 OLB player-seasons to inside linebacker (the role table's box-linebacker or base-defensive-back call).
   - The inside linebackers' scored pairs go from 249 to 303.
   - Movers go from 66 to **80** (61 players). 14 of them were OLB-labelled off-ball players in the input season.
2. **The gain shrinks, but stays clear.** As pre-registered (his M1 plus his new team's rate, against M1, movers only):
   - pressures: **+9.4% (+1.1 to +16.7)**, was +20.7%;
   - rush share: **+11.0% (+4.0 to +19.5)**, was +27.9%.
   - On all rows (stayers too) it loses: −2.3% and −5.7%.
3. **The shuffle test fails.** Moving the new team's part to another inside linebacker that season, 20 times, scores as well as the real thing:
   - pressures: best copy +13.9%, median +9.7%;
   - rush share: best +16.0%, median +11.8%.
   - So the gain doesn't need the right team.
4. **What it is instead: a harder pull.** The second pull (one slope on his shrunk rate, fit on earlier pairs, no team at all) gives movers:
   - pressures +10.4% (+2.8 to +17.5);
   - rush share +12.4% (+5.7 to +20.7).
   - The split adds nothing beyond it: −1.2% (−6.1 to +3.3) and −1.7% (−5.6 to +3.0).
   - The split's fitted weight on his own rate is below 1 (0.87 and 0.97). That extra pull is what helps movers, whose team-owned rates fall further.
5. **Not scheme.**
   - The change in team part (new team less old) has no relation to how far his rate moves beyond his shrunk rate: weighted r −0.04 and 0.01.
   - Movers with a big change in team part gain a little more (+12.0% and +13.8%, against +5.5% and +5.3% for small changes), but the halves overlap.
6. **Seasons.** 2020's 10 movers carry 47% (pressures) and 51% (rush share) of the gain.
   - Without 2020, pressures fall to +5.8% (−3.7 to +12.9), which spans zero.
   - Rush share holds without 2020: +6.2% (+1.1 to +13.0).
7. **Teams.**
   - Pressures don't survive dropping the Giants' 5 incoming movers (+7.7%, −0.3 to +15.7) or the Lions' 2 (+7.9%, −0.6 to +15.5).
   - Rush share is clear without every one of the 28 new teams (lowest bound +1.8%).
8. **The players.** The movers it helps most had a high rate that fell after the move:
   - Jamie Collins, NE to DET, 2019: rush share +0.21 to −0.01;
   - Reggie Ragland, DET to NYG, 2020: +0.14 to −0.08;
   - Kaden Elliss, NO to ATL, 2022: +0.15 to +0.01.
   - The split helps them only by pulling harder.
9. **The other movers results the same way** (RESULTS R6 listed them):
   - WR catch rate: the split adds +1.1% (−1.5 to +3.8) beyond the second pull;
   - DB throw depth against: −1.3% (−2.2 to −0.5);
   - so those are also the harder pull.
   - **Only linemen follow the new team:** pressure +19.6% (+8.4 to +30.3) and sacks +23.2% (+8.1 to +36.1) beyond the second pull. This agrees with the ladder, where the linemen's split beats 20 of 20 shuffled copies.
10. **Checked afterwards: outside linebackers' pressures** (call 34). After the reclassification, the OLB group is edge players, and its shipped split is the champion.
    - Against the second pull it still clears: +2.9% (+0.7 to +5.6) on all 126 pairs, beating 20 copies (best +1.8%).
    - For the 34 movers it gives +10.8% (+3.0 to +18.4).
    - OLB rush share's split doesn't (−0.3%).
    - So edge pressure, like the line's, follows the new team a little. This test came after the result was seen, so it is a lead (I173).

**What would change the answer:** a larger mover sample for inside linebackers (more seasons), or a mover-only pull that beats the shared second pull. The mover-only pull is too noisy at 57 movers to say: +5.7% (−30.5 to +32.8).

## The odds, scored

| # | Bet | Odds | Verdict |
|---|---|---|---|
| 1 | 85-120 movers | 70% | **Failed**: 80 |
| 2 | Pressures' gain still clear, +8% to +20% | 60% | **Held**: +9.4% (+1.1 to +16.7), in the size range |
| 3 | Rush share's gain still clear, +10% to +25% | 65% | **Held**: +11.0% (+4.0 to +19.5), in the size range |
| 4 | Beats all 20 copies | 50% (pressures), 60% (rush share) | **Failed** both: the copies' median matches the real gain |
| 5 | No season carries more than half | 70% | **Failed**: 2020 carries 47% and 51% |
| 6 | Clear without any one new team | 60% | **Failed** for pressures, held for rush share |
| 7 | It's scheme | 75% | **Failed**: r −0.04 and 0.01; the second pull alone gives the gain |
| 8 | Changes something that ships | 20% | **Held**: the interface advice for movers changes (below) |

## What changes

- **F115 (RESULTS R6) is rewritten.** A mover's team-owned trait is pulled harder toward the average, not toward his new team. The new team's rate adds only for linemen.
- **The interface card and the registry** now say:
  - for a mover, use the second pull (`next_c` under the pull rung, or M1 times the trait's fitted slope);
  - add his new team's rate only for offensive linemen and edge pressure (OLB pressures).
- **I171** keeps its pre-registered verdict (held), with the reading corrected.
- **New idea, I173:** whether a movers-only pull beats the shared one across traits.
- **The history doesn't change** from the spot-check itself; it has no split rung. The reclassification changes the OLB and ILB rows (RESULTS).
