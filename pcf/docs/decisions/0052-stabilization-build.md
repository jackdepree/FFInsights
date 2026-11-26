# 0052: stabilization's build, its technical calls

**Date:** 2026-11-26 · **Decided by:** Claude (technical calls, for the CEO's veto) · **Project:** `stabilization` (the build of the agreed brief, `projects/stabilization/BRIEF.md`, "The agreed brief", the CEO, 2026-11-25: "Agree the brief") · **Vetoes:** pending.

## Odds written before any result (2026-11-26)

Written after the shared module was moved and the inputs were built (row counts only), before any rung was fit or scored. "Clear" means a 90% interval from resampling players (teams for team measures) that leaves out 0; "beats the copies" means beating all 19 shuffled-player copies.

**The ladder (rule k: a tie goes to the simpler rung):**
- **Rung 2 over M1, next season:** the second pull beats M1 clearly for 12+ of the 20 player rates: 55%. (The exploration recalibrated M1 for 12 of 18; the walk-forward slope has fewer earlier pairs to fit on in the first test seasons.)
- **Rung 3 (the ridge) over rung 2, next season:** clear for 4+ of 20: 40%; for 1+: 75%. Size where it clears: 1-4% of the error.
- **Rung 4 (the filter) over the static two pulls, next 4 games:** clear for 4+ of the 7 usage rates (targets a route, aDOT, carries a run snap, scramble rate, QB aDOT, targets a coverage snap, aDOT allowed): 50%. For team offensive tendencies, 4+ of 7: 65%.
- **The expert's bar:** the shipped forecast beats the position's average and all 19 copies on next season for 16+ of 20 rates: 60% (the exploration's M1 tied the average for 4).
- **Ranges (80%) within 75-85%:** for every shipped player rate on the next 4 games: 50%; on next season, before any conformal step: 35%.
- **I14 (rung 5):** widening by swing improves the range score clearly for half or more of the shipped rates on the next 4 games: 60%.

**The live stand-ins** (season rate, stand-in against participation's exact attempts, 2016-2024; "close" = correlation 0.95+ across player-seasons with 100+ exact attempts):
- routes (targets a route, yards a route): 85%;
- run snaps (carries a run snap): 45% (a third-down back and an early-down back share the snaps unevenly between runs and passes);
- pass snaps on defense (pressures and QB hits a pass snap, targets a coverage snap): 55% (pass-rush specialists come in on passing downs).
- A stand-in is **too poor** if its next-season M1 forecast of the exact rate is clearly worse than the exact version's by more than 5% of the error. Odds that at least one is too poor: 40%.

**The rest of a career (side report):** drift folded in beats plain M1 clearly for 2+ of the 8 play-by-play measures: 55%.

**Ideas** (odds also in `IDEAS.md`, in each row): I154 (its 2026-11-25 odds), I155 (2026-11-25), I156 (2026-11-25, and the in-build odds above for rung 2), I173, I152, I104 and I5 in this build's form, and the new I180-I182.

## Calls made during the build

1. **The shared shrink is `pcf.validation.stabilize`**, owned by stabilization (the CEO, 2026-11-26: "Yes stabilization should own the code for pulling rates toward the average, but that does not necessarily mean other experts can not use that code. The code should be consistent between projects unless there is a good football reason"; decision 0051 call 32).
   - **Where:** in the shared package beside `owners` and `consistency`, because every expert's shrink can import it there without importing another expert's package (rule j). Its docstring names stabilization as the owner.
   - **What moved:** `centre` (the pull target, `"same"` or `"last"` season, and the floor as arguments), `noise`, `spread`, `components`, `k_of`, `reliability`, `shrink` and `shrink_expr`, `posterior_sd`, `wls`, `walk_slopes` and `second_pull`. The math is skill-over-expected's, unchanged.
   - **Skill-over-expected points at it:** `traits.season_rows`, `components`, `team_components`, `rungs` and `fit_slopes` call the shared functions; its off-ball linebacker rule (`regroup`) stays in its own package, the one football difference (the CEO, 2026-11-26).
   - **The proof it's unchanged:** its full report (`run --no-log --no-yardstick`) reruns word for word identical; its table matches the old code's to 1e-12 relative, and two runs of the old code differ from each other by 3e-13 (polars' group order in floating sums). Its 12 tests pass.

2. **The inputs, through an in-season view** (`stabilization.data`): only live parts are declared (`play.pbp`, `player_game` roster, snaps and pfr, `team_game` schedule). Participation is read only for the stand-ins' report, through a retrospective view. Each player-game row carries the latest `known_at` of the sources it used; PFR's rows carry PFR's (the Tuesday after the following week).
