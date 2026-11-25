# Roles and archetypes: the build's odds (written before the forecasting tests ran)

> Written 2026-11-24, in the build session, before `python -m pcf.experts.roles_archetypes.run` scored tests 2, 3 and 4 or the autoencoder and trees rungs. Claude's odds, by the charter's rule ("every bet states its odds first"). The code is in `src/pcf/experts/roles_archetypes/`; the technical calls are in [decision 0048](../../docs/decisions/0048-roles-archetypes-build.md).

## Seen while building, so no odds

Two tests' numbers were seen while the package was being written and checked against the exploration, so no odds are claimed for them:

- **Test 1 (consistency held out):** the frozen 2016–2020 fit, read on 2021–2024, has 5 of 6 offensive axes and 4 of 6 defensive axes at a centred split-half of 0.5+ (seen in the check that the build reproduces the exploration's space).
- **Test 5 (named roles' flips):** the cuts were chosen while looking at flips on 2016–2020. The coarse roles flip about 3% and the fine roles about 16% at the median group on those seasons. The held-out seasons (2021–2024) weren't looked at for flips before the run.

## Odds before the run

| Test | Claude's chance it comes out as stated | Expected size |
|---|---|---|
| **Test 2, offense:** the coordinates beat the position labels on next season's targets per snap | 90% | +35% to +45% of the labels' squared error |
| **Test 2, offense:** the same on carries per snap | 35% | −10% to +10% (the exploration's step problem) |
| **Test 2, defense:** tackles per snap, and rushes per pass snap | 85% each | +20% to +30% |
| **Rung 1:** the role table and named roles beat the labels (targets per snap) | 90% | +30% to +45% |
| **Rung 2:** the coordinates beat the role table (a tie goes to the table) | 25% | within ±3% |
| **Rung 3:** trees on the coordinates beat their lasso, on carries per snap | 60% | +5% to +20% |
| **Rung 3:** the same on targets per snap | 30% | ±3% |
| **Rung 4:** the autoencoder beats PCA (a tie goes to PCA) | 20% | ±3% |
| **Test 3:** the coordinates add to labels plus his own last-season rates (any target) | 15% per target | +0 to +1% |
| **Test 3:** the coordinates make that forecast clearly worse (adds noise) | 15% per target | |
| **Signal:** the coordinates' model beats all 20 shuffled refits (each target) | 95% | |
| **Test 4:** the coordinates count on the receiving rest-of-season board (interval clears 0 and beats all 19 copies) | 20% | under +0.3% of squared error |
| **Test 4:** the same on the rushing board | 15% | under +0.3% |
| **Test 5:** like-for-like substitutes rank under 0.5 with the interval under 0.5, offense and defense | 75% offense, 55% defense | about 0.44 (H101) |
| **Test 5:** fine roles flip under 14% at the median group on 2021–2024 | 25% | about 15–16% |

## The odds, scored (after run `696a3f0b`, 2026-11-24)

| Test | Claude's odds | Came out | Size against expected |
|---|---|---|---|
| Test 2, targets | 90% | **Held** | +42.9% (expected +35 to +45) |
| Test 2, carries | 35% | Didn't beat (a tie) | −14.1% (interval −54 to +11; expected −10 to +10) |
| Test 2, tackles; rushes | 85% each | **Held** both | +26.5%, +27.6% (expected +20 to +30) |
| Rung 1 | 90% | **Held** | +48.1% (expected +30 to +45: a bit larger) |
| Rung 2 | 25% | Didn't hold: the coordinates lose to the table | −10% to −207% (expected ±3: much larger) |
| Rung 3, carries | 60% | **Held** | +43.8% (expected +5 to +20: larger, because the PCA lasso was so poor on carries) |
| Rung 3, targets | 30% | Didn't hold (trees worse) | −11.7% (expected ±3: larger) |
| Rung 4 | 20% | Didn't hold | −17% to +2% alone; ties beyond his own rates but +1.1% on rushes |
| Test 3 adds | 15% per target | Held on 2 of 4 (carries +1.0%, rushes +3.1%) | Rushes larger than +0 to +1 |
| Test 3 adds noise | 15% per target | Didn't happen (0 of 4) | |
| Signal | 95% | **Held**, 4 of 4 | |
| Test 4, receiving | 20% | **Held** (counts) | +0.30% (expected under +0.3: at the top) |
| Test 4, rushing | 15% | Didn't hold: adds noise | −0.90% (no odds were written for noise) |
| Substitutes | 75% offense, 55% defense | Offense failed by a hair, defense held | 0.477 both (expected about 0.44) |
| Fine flips under 14% | 25% | Didn't hold | 16.3% (expected 15 to 16) |

Claude's read: the direction calls were well calibrated. The sizes were too small wherever the PCA lasso met a step (carries) or the table. I underrated how much a handful of plain rates beats a fitted space.

## Round 2: the CEO's answers and the odds written before the second round's tests (2026-11-25)

The CEO's answers (2026-11-25, word for word): "I think the 12 role names work great! I think movers keep only the parts that repeat. Yes ship roles as leans with a certainty score. Can you spot check the rushing noise? No vetoes from me. Make sure to check the backlog of ideas and test the ones that fit into both of these builds, please."

Written by Claude before any of these tests ran. The ideas' own rows in `IDEAS.md` already hold odds for I122, I133–I136 and I43 (written earlier, before any test); they're repeated here so the round is scored in one place, and the new ones are marked new.

| Test | Claude's odds | Expected size |
|---|---|---|
| **Spot-check S1** (new): the coordinates' rushing loss sits mostly (over 60% of it) in one position group's rows | 55% (RB 30%, WR 15%, QB or others 10%) | |
| **Spot-check S2** (new): it sits mostly (over 50%) in one target season | 25% | |
| **Spot-check S3 = I133** (earlier): dropping fullbacks' rows from the prior, or adding carries per run snap beside the axes, turns the coordinates' rushing gain to a tie or better | 50% | |
| **Spot-check S4** (new): a fix of the coordinates (any variant here) beats the role table on the rushing board | 15% | |
| **Spot-check S5** (new): the loss comes from the board's linear fit reading a coordinate as a straight line where carries are a step (back or not): the coordinates turned into the coarse role (back, in tight, split out as three dummies) count on rushing | 45% | +0.3 to +0.6% |
| **I134** (earlier): a hysteresis band brings the fine roles' median flip under 14% | 45%; DL and OLB under 20%: 70% | |
| **I134** (new): the band's labels predict next season's rates as well as the plain labels (a tie or better) | 80% | |
| **I135** (earlier): the 4-feature table (no targets per pass snap, no carries per run snap) still counts on the receiving board | 40%; on rushing 30% | |
| **I135** (new): the 4-feature table still beats the position labels on next season's targets and carries per snap | 75% targets, 50% carries | +10 to +25% |
| **I136** (earlier): offense's substitutes rank under 0.5 with its interval on the role table | 55% | about 0.45 |
| **I122** (earlier): the shrunk vacancy blend beats the group average on newcomers (team-bootstrap interval above 0) | 55% | about 5% of the squared distance |
| **I43** (earlier, medium): a passing-down role measure adds to a next-contract model within position, on contracts it wasn't fit on | 75% (written as medium) | about +1% |
| **I57** (new): a receiver's own past vertical route share forecasts next season's better than his position's mix | 90% | 20 to 40% of the squared error |
| **I57** (new): the role table adds to his own past share | 40% | 2 to 5% |
| **I132** (earlier): measurables (40, height, weight, draft slot) beat the position mean on a rookie's first-season in-tight and ball-carrier axes | 60% | 10 to 20% of the squared distance |
| **Test 1 re-scored** (new): offense passes under the CEO's reading (movers keep half of each repeating component's season r) | 95% (the report already shows it) | |

## Round 2's odds, scored (2026-11-25; scripts and outputs in `explore/build2_*`)

| Test | Claude's odds | Came out | Size against expected |
|---|---|---|---|
| S1: the rushing loss mostly in one position group | 55% | **Void as worded** (the rushing board holds only RBs); by the backs' prior role, no: early-down backs 55%, passing-down backs 43% | |
| S2: mostly in one season | 25% | Didn't hold: 2019 38%, 2021 35% | |
| S3 = I133: fullbacks set aside, or carries per run snap beside the axes, turns it to a tie or better | 50% | **Held** both ways: −0.13% (−0.44 to +0.16) and −0.25% (−0.52 to +0.04) | The fullbacks are only part of the cause: signal-free copies of the coordinates cost −0.48% on average on this board |
| S4: a fix of the coordinates beats the role table on rushing | 15% | Didn't hold (best −0.13% against the table's +0.74%) | |
| S5: the coarse roles as dummies count on rushing | 45% | Didn't hold (−0.03%). Side result: the two fine back roles as dummies count, +0.45% (+0.30 to +0.60), beating 19 of 19 copies | +0.45% inside the +0.3 to +0.6 expected for the coarse version |
| I134: the band brings the median flip under 14% | 45% | Didn't hold, by a hair: 14.05% | DL 26%, OLB 31% |
| I134: DL and OLB under 20% | 70% | Didn't hold | |
| I134: the banded labels forecast as well (a tie or better) | 80% | **Held**: ties on all four rates | |
| I135: the 4-feature table counts on receiving | 40% | **Held**: +0.23% (+0.14 to +0.32), beats 19 of 19 | |
| I135: and on rushing | 30% | **Held**: +0.88% (+0.67 to +1.11), beats 19 of 19 | Larger than the 6-feature table's +0.74% |
| I135: the 4-feature table beats labels on targets; on carries | 75%; 50% | **Held** on targets (+28.1%); a tie on carries (+4.3%, −1.9 to +10.8) | Targets inside +10 to +25%, a little above |
| I136: offense's substitutes under 0.5 on the role table | 55% | **Held**: 0.436 (0.404 to 0.466); defense 0.440 too | About 0.45 expected |
| I122: the vacancy blend beats the group average | 55% | **Held** on the coordinates (+1.7%, +0.3 to +3.1; beats 20 of 20 placebo vacancies); a tie on the role table (+0.8%) | Smaller than the 5% expected |
| I43: the passing-down share adds to a contract model within position | 75% | **Held where the idea said** (DL and OLB: +5.4% lasso, +5.8% trees, both beating 20 of 20); overall +3.6% on the lasso, a tie on the stronger trees (+1.3%) | Larger than the +1% expected, where it holds |
| I57: his own past vertical share beats the position's mix | 90% | **Held**: +18.6% (+11.5 to +25.0) | Just under the 20 to 40% expected |
| I57: the role table adds beyond his own share | 40% | **Held**: +9.1% (+6.2 to +12.0), beats 20 of 20 | Larger than the 2 to 5% expected |
| I132: measurables beat the position mean on rookies' in-tight and ball-carrier axes | 60% | **Held in part**: WR in tight +15.8% (+5.2 to +25.2), beats 20 of 20; WR ball carrier, TE and RB ties | In-tight inside the 10 to 20% expected |
| Test 1 under the CEO's reading | 95% | **Held**: the five repeating offensive axes keep 79-93% | |

Claude's read: 11 of the 16 scorable direction calls came out on the side of 50% I had put them (S1 is void; S3 and I135's carries were at 50%; I132 held in part). The five misses: four times I doubted the role table (I135 on both boards, I57's table), and once I was too hopeful about the front (DL and OLB under 20%). The sizes I most underrated were the role table's extra worth: on the route mix (+9.1% against 2 to 5%) and without his own rates on rushing (+0.88%). I overrated the vacancy blend (+1.7% against 5%).
