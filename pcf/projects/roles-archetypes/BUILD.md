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
