# context-retro: build notes

> **The brief** is the last section of [`../context-v2/BRIEF.md`](../context-v2/BRIEF.md), "The brief, after the exploration" (agreed 2026-11-21: the CEO, "I do not veto anything in the brief. Merge approved"). The exploration is [`../context-v2/EXPLORATION.md`](../context-v2/EXPLORATION.md) (four looks). This file holds what the build decided and pre-registered as it went, in order, before each result. The technical calls are [decision 0041](../../docs/decisions/0041-context-retro.md). Results: [RESULTS.md](RESULTS.md).

## 2026-11-21: a data trap found in the smoke run (before the backtest)

The first smoke run (2023-2024, two outcomes) had sack's chance before the snap **worse than the plain average** (by 0.27 points of log loss per thousand plays, clear), with a calibration slope of **-0.68**: higher chances went with fewer sacks. The cause: **before 2023, participation leaves coverage empty on every sack**, as it does the pressure flag (context-v2's fourth look). From 2018 to 2022 coverage is missing on 100% of sacks and about 5% of other dropbacks; from 2023 on 1% and 0.3%. Trees trained on 2018-2022 learn "no coverage, so a sack", and the rule turns over in 2023.

- **Pass attempts are clean:** coverage is missing on 285 of 94,308 attempts in 2018-2022, completed at the usual rate (65.3% against 64.7%). Depth and completion keep coverage from 2018 (the exploration's +1 point, F2).
- **The fix** (decision 0041, call 7): outcomes whose plays include sacks (pressure, time to throw, sack, dropback yards) read coverage only from 2023 (`dcov_*`, `dman`); before that it is missing for every dropback alike.
- **A smaller one of the same kind** (call 8): in 2016-2017 participation has no rusher count on 1,447 dropbacks, sacked 0.1% of the time against 6.1%. Filled with the usual count (4 rushers; a missing box with 6), so the gap marks nothing.

After the fix the smoke numbers line up with the exploration's (2024 trained on 2023, there; here 2023-2024 walk-forward): sack before the snap 1.7% of squared error (first look 1.2%), given the pressure 17.9% (16.8%); completion 5.1% and 8.0% (4.6%, 7.7%); depth 19.6%; time to throw 17.0% and 29.0% (17.5%, 29.2%). The smoke runs count as versions tried.

## 2026-11-21: H88's test, pre-registered (before any H88 code or run)

**The claim** (the CEO, 2026-11-20): "The more we improve this expert the better our downfield models become, almost on an exponential path." The brief's test: *does the crude forecaster's yards forecast improve when context-retro's season priors replace context-live's?* The odds were given with the brief: the CEO 50%, Claude 10% as worded.

**Season priors.** From a completed season (rule m: a retrospective output feeds a later forecast only from completed seasons, as a prior), each passer's and each offense's rates **over expected** on five outcomes the two experts share: pressure, sack and time to throw per dropback; depth and completion per attempt. Over expected is the actual minus the expert's walk-forward expectation before the snap (E0), summed over the season and divided by the plays plus 100 (pulled toward 0 by 100 of its own plays, as context-v2's third look did, so a backup's 40 dropbacks aren't read at face value). A player or team with no rows last season gets 0 (average). Every row of season s gets season s-1's priors, and only when they were known before the row's moment (the prior's `as_of` ≤ the row's).

**Four arms**, each the same five columns (the passer's on the passing boards, the offense's on the team boards):
1. **plain:** the actual minus the league's season average: the obvious input (the charter's check).
2. **live:** over context-live's walk-forward expectation, the back-history's calls16 edition (run `b68c042b`, decision 0038), the only context-live history that covers 2017-2024.
3. **retro:** over context-retro's walk-forward E0 (this build's backtest).
4. **retro+** (a side arm): retro's five plus the after-pressure part and the pressure part per dropback (the split).

The same actual for every arm: the pressure counts a sack (call 3), so the live arm's pressure over expected carries context-live's old trap (its pressure was trained on the raw flag). That is part of what the build improved.

**Boards** (the yardstick, `pcf.baselines.crude.yardstick`): passing yards (QBs) and team yards gained, each next game and rest of season: four boards. Scored 2019-2024, walk-forward, lasso, as every yardstick reading (decision 0037). The vault stays closed for the crude forecaster (the CEO, 2026-11-19).

**The test.** Retro's forecast against live's, paired on the same rows: the share of live's squared error removed, 90% interval from resampled weeks. Each arm against the crude forecast alone is reported beside it, with its range score (the no-noise verdict).

**Pass rule for H88 as worded:**
- **Held** if retro beats live (the interval above zero) on 2 or more of the 4 boards and is clearly worse on none.
- **Failed** if retro beats live on none of the 4.
- **Unclear** otherwise.
- "Almost exponential" isn't testable with two versions of one expert; the rule reads the direction (a better expert gives a better downstream forecast), which is the claim's necessary part.

**Claude's side bets** (written now):
- Retro beats live on at least 1 of the 4 boards: 25%.
- Any of the three expectation arms adds a gain over the crude forecast alone with its interval above zero on passing yards next game: 30%.
- The plain arm is within the interval of the live and retro arms on all four boards (the expectation doesn't matter at season level, as H84 found): 70%.
- retro+ beats retro on any board: 20%.

**Why Claude expects it to fail:** at season level the calls average out (F24, F16: over-expected rates barely differ from plain ones), and the two expectations agree closely before the snap; the crude forecaster already has each QB's and offense's yards to date. A better expectation can change a season prior by a few hundredths at most.
