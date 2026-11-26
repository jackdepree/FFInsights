# 0052: stabilization's build, its technical calls

**Date:** 2026-11-26 · **Decided by:** Claude (technical calls, for the CEO's veto) · **Project:** `stabilization` (the build of the agreed brief, `projects/stabilization/BRIEF.md`, "The agreed brief", the CEO, 2026-11-25: "Agree the brief") · **Vetoes:** none (the CEO, 2026-11-26: "No vetoes"; the list is near the end).

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

3. **Season rows and the pull target** (`rates`): an entity-season's class is the class with most of its attempts (in season: the class of its first game, call 23); the pull target is the class mean over entity-seasons with 10+ attempts, for classes with 20+ of them (a team's side always). **Next season** is centred by the input season's mean and the target on the same scale, so a league shift counts against every rung alike; **in season** by last season's mean (the brief), the data's first season by its own.
4. **k is pooled over a measure's classes** (each entity-season centred by its own class-season), refit for every input season on seasons up to it, from the shared `components` (noise from each player's games around his season rate; spread from the weighted variance less the noise). One k per measure, not per position: F37 (one pull per position as good as one per player) and the exploration's k's.
5. **In-season scoring:** forecasts after a player's game 4, 8 and 12, at his next kickoff, scored on his next 4 games' rate weighted by their attempts (the brief); the rest of his season as a side horizon. Static M1 pools last season's and this season's attempts (no drift). PFR measures (2018 on) are tested 2019-2024 (call 22).
6. **The filter** (`drift`): a local level per entity, q per game and q_s at each new season, both as shares of the true spread on grids (q 0-0.1, q_s 0-1), fit by the likelihood of games before the test season. I154's factor (1-2.5) and I182's fixed extra (0-10 of the spread) by a coordinate search (q and q_s at no extra noise; then the noise; then q and q_s again). Usage, mixed and the defense's faced rates try the plain filter; efficiency rates the filter with I154's factor (the brief). **A grid edge:** q_s reached 1.0 for offenses' pass rate over expected, shotgun and no-huddle (a new season nearly resets them), so the filter there may be held back slightly; not widened, to keep players and teams on one grid.
7. **PFR's lag:** each checkpoint reads the latest game whose `known_at` is no later than the next kickoff (an as-of join); the lag bites at 67-85% of PFR checkpoints (the leakage report).
8. **The second pull in season:** one slope on M1 per checkpoint (games 4, 8, 12), fit on earlier seasons' rows at the same checkpoint (the shared `second_pull`).
9. **Ranges:** M1's and the pull's variance = slope^2 x sigma2 / (N + k) + c + sigma2 / attempts, with c the drift left over, fit by moments on earlier seasons; the filter's = P + q (H + 1) / 2 + noise / attempts. Normal 80%. A conformal scale from earlier seasons is applied only where plain coverage falls outside 75-85%; I14's widening (swing shrunk toward 1 with 20 games) is kept only where the range score improves clearly.
10. **Next-season pairs:** input season s (10+ attempts) to target s + 1, weighted by next season's attempts; a mover is a player whose first game of s + 1 is for another team (known before that season).
11. **The second pull next season:** one slope per measure on its M1, fit on pairs with earlier targets.
12. **The ridge** (rung 3): RidgeCV with its own leave-one-out alpha (13 values, 0.001-1000) inside the training pairs, inputs standardized, no intercept; fit only with 100+ training pairs. His other rates are those whose true-rate season r is 0.5+ on earlier pairs only (feature selection inside the fold, rule k); H113's teammates' conditions, last season's and, for a mover, the change.
13. **Next-season ranges** as call 9, with the rung's weight on his own M1 (1, the slope, or the ridge's coefficient), c on earlier targets, and the conformal scale per target season.
14. **The ideas' forms** in this build: I152 his M1's change over his last two seasons added to the ridge; I173 two slopes (movers, stayers) against the shared one, movers only; I181 a pull toward his team's rate at his position (leave-one-out), itself pulled toward the position with its own k; I104 this season's k from games so far, blended with the pooled k by player-seasons; I5 static M1's mean miss for rookies after games 8 and 12.
15. **Clear** is a 90% interval from 2,000 resamples of entities (sorted first, so the interval doesn't move with row order) that leaves out 0. A tie goes to the simpler rung (rule k).
16. **The climb:** M1 against the average; the second pull must clear M1; the ridge (next season) or the filter (in season) must clear the winner below it.
17. **The expert's bar:** the champion clears the position's average and beats all 19 shuffled copies. A copy reruns the walk with every input (his pulled rate, attempts, other rates, conditions, the filter's states, swing) moved to another entity of the same season and class (and checkpoint). A measure that fails ships the position's average.
18. **Seasons won** (the share of test seasons the shipped rung beats the average) is reported, not used to decide.
19. **The rest of a career** (side report): players at the end of 2010-2018, the target their pooled rate in every later season through 2024 (careers still running are cut at 2024), k and the true rate's season r refit on seasons up to the end season; the drift folded in discounts older seasons by r^age and pulls by r^h over his later attempts.
20. **The stand-ins' test** (pre-registered): season rate r on 100+ exact attempts (close at 0.95+); too poor = the stand-in's next-season M1 forecast of the exact rate clearly worse than the exact version's by more than 5% of the error.
21. **A diagnostic added after the first stand-in result** (marked as such): both versions rescaled to the exact rate's level (an intercept and slope per position, fit on earlier targets), so a stand-in off by scale but right by order isn't charged for the scale. It doesn't change the verdict.
22. **A test season needs a season before it** (found by a crash): PFR's measures start in 2018, so they are tested 2019-2024 in season, as their next-season targets already were.
23. **In season, a player's class is his first game's** (found while writing the leakage checks): the season's majority class isn't known until it ends. It moved 7 of 6,350 receiver-seasons; the results changed by 0.1% at most.
24. **The leakage checks** (`checks`): future deletion and outcome scrambling at 8 cutoffs (2019 and 2023) for four measures in season (a usage, an efficiency, a PFR and a stand-in rate), outcome scrambling from the target season on for three measures next season, PFR's lag, known-at sanity, and the code scan. Three reads are expected and named: the data module reads its own cache of gateway rows (as other experts' do), I156's check reads opportunity-quality's backtest cache, and the checks read the package's own source to scan it.
25. **The history** (`history`): the shipped rung of each measure, every row from parameters fit on earlier seasons. In season, before every game 2-17; next season, from 2006-2024 inputs including the 2025 prior (made from 2024 and earlier; the vault's outcomes are never read). **The ranges use expected attempts** (attempts a game so far x 4; last season's attempts next season), since realised attempts aren't known at `as_of`; their coverage on the scored rows is reported. Where a season is too early for a slope or drift term, the row falls back to M1 (column `rung`), with no drift term and no conformal scale. `as_of` is the next kickoff in season, 1 September next season; `train_end` the last `known_at` of the seasons it was fit on.
26. **Teams:** each side (offense, defense allowed or faced) is a class of 32; teams are resampled. Next season climbs M1 and the second pull only: 32 teams a season leave the ridge under its 100 training pairs until the last test seasons.
27. **I155 is a description** (CONSISTENCY's test 2), fit on 2006-2024: each defensive game's rate less its opponent's usual offensive rate, the usual from the opponent's earlier games that season plus last season's pulled rate worth k plays; both centred by the season's league rate, and k fit once on every season.
28. **I156 on opportunity-quality's method B** (its per-player partial-pooling shrink, the one other shipped shrink by sample size alone scored on its own target): its backtest rows from its cache (the saved history lacks the realised gap), one second-pull slope per position on earlier seasons. VOE's values and opportunity-quality's feature shrinks feed linear or tree models, where a one-slope rescale is absorbed (decision 0051 call 28).
29. **I174 through vacated-offseason's own code** (routed by the build chat): its I165 shrink with one slope per skill group, fit on earlier pairs, against the shared slope; team bootstrap and 19 copies of shuffled departures (its own null).
30. **Linebackers keep the roster grouping** (the CEO, 2026-11-26: stabilization doesn't need the off-ball rule for now); an OLB counts as a rusher.
31. **Swing next season:** a player's games' squared surprises around his season rate against the noise alone, shrunk toward 1 with 20 games.
32. **The history's ranges get a walk-forward scale** (found in the final run, after the report was scored): on expected attempts the next-season ranges held only 68-80% on the scored rows (the report's, on realised attempts, 75-83%), because a player's attempts usually fall the next season and the noise term is understated. Each season's ranges in the history are scaled by the 80th percentile of earlier seasons' scored |actual - forecast| / sd (over the normal's; 1 before 30 such rows), in season and next season alike (`history.history_scale`, column `range_scale`). The report's verdicts are unchanged; only the saved ranges move.
33. **The history's in-season `reliability` uses each test season's own k** (a bug found while adding the brief's `k` and `swing` columns): it had used the k fit through 2023 for every season's rows, a look-ahead in that one column (the forecasts and ranges were never affected). The history now carries `k`, `reliability` and `swing` per row, as the brief's outputs list.
34. **`run --history-only`** rebuilds the history and its MLflow attempt from the saved verdicts and leakage result, the metrics re-read from the verdicts, so a history fix doesn't rerun the 19-copy report (a full run takes about two hours). The first full run's MLflow attempt crashed in the team history (a duplicate `team` column, fixed) and a second was stopped on purpose for call 32; both count in versions tried.

## For the CEO's veto (the calls that move results most)

Every call above is a technical call, and any of them can be vetoed. These are the ones a veto would change most:
- **Call 1:** the shared shrink lives in `pcf.validation.stabilize`, and skill-over-expected points at it.
- **Call 4:** one k per rate, pooled over positions (I185 tests a k per position).
- **Call 6:** the filter's grids. q_s reaches the edge (1.0) for three offensive tendencies.
- **Call 9:** a conformal scale only where plain coverage falls outside 75%-85%; I14's widening only where the range score clears.
- **Call 12:** the ridge's inputs are chosen inside each fold (season r 0.5+ on earlier pairs).
- **Call 17:** a rate that can't beat the position's average ships the average: yards after contact, broken tackles a touch and pressured rate next season, and 11 team sides.
- **Call 21:** the stand-ins' rescaled diagnostic, added after the first stand-in result (marked as such). It doesn't change a verdict.
- **Call 25 with call 32:** the history's ranges use expected attempts, scaled walk-forward on earlier seasons' misses.
- **Call 30:** linebackers keep the roster grouping (the CEO's answer).
- **Not a call, a question:** the trend (I152, F124) isn't shipped in v1. Shipping it would make it rung 4 next season.

## The CEO's answers (2026-11-26), and what follows

The CEO, word for word: "No vetoes. The next season forecast should add the trend now. For the run snap problem I think we can try out the cheaper fix first. Keep 2025 vault closed. Please spot check the second pull, then you may merge. Yes please always run and test all ideas from the backlog that are appropriate for a build and the ones specified in the brief."

- **No vetoes** on calls 1-34.
- **The 2025 vault stays closed.** Its odds and pass rules in RESULTS.md stay unscored.
- **The trend ships next season** (call 35, below).
- **The run-snap stand-in gets I180's correction** (call 36). `stabilization-retro` stays a proposal.
- **The spot-check is the second pull** (`SPOT_CHECK.md`).
- **The standing rule** (every backlog idea that fits a build is run and tested) is already how this build worked: every routed idea and every fitting open idea was run, and the rest are listed with a reason.

### Odds written before these results (2026-11-26, after the answers, before any code ran)

**The trend shipped (call 35):**
- It clears the rung that ships now for 12+ of the 20 player rates: 65%. It cleared the ridge for 16; against the shipped pull or M1 the base is weaker for some and stronger for others.
- The history's next-season coverage stays within 74%-90% for every rate: 75%.

**I180's correction for carries a run snap (call 36):**
- Already known, not a bet: in this build's stand-ins report the corrected stand-in removes 34% of the plain stand-in's error on next season's exact rate, about 40% of the gap to the exact version.
- No lead back (150+ corrected run snaps) has a 2025 prior above 1: 55%. At most 2 do: 80%.
- In season, the corrected rate's shipped forecast still beats the position's average and its 19 copies, and the filter still beats static: 85%.
- The season rate's correlation with the exact rate stays at 0.918 or within 0.01 of it (the report's): 90%.

**The spot-check of the second pull:**
- Its slope is fit only on earlier targets, and each test season's slope stays within 0.1 of its 2024 value for 8+ of the 11 rates it ships or helps for: 55%.
- The pull beats M1 in 6+ of 7 test seasons for 6+ of the 11: 50%.
- The walk-forward slope gets 70%+ of a hindsight constant slope's gain for 8+ of the 11: 60%.
- In season, the slopes sit within 0.95-1.05 for most rates (so the second pull has nothing to do): 70%.
- Dropping it turns 2+ shipped next-season rates into ties with the average (they'd ship the average): 50%.

## Calls after the CEO's answers (2026-11-26)

35. **The trend ships as rung 4 next season** (the CEO: "The next season forecast should add the trend now"). `ridge_trend` is the ridge plus his M1's change over his last two seasons (`trend` = m1 less last season's m1, 0 where he has no earlier season), fit walk-forward like the ridge. It ships where it clears the rung that would otherwise ship (rule k), then faces the same bar (the average and 19 copies). Its range uses its own weight on M1, like the other rungs (`b_ridge_trend`). It ships for 10 of 20 player rates; teams have no ridge, so no trend.
    - **Found on the seasons it was scored on.** I152's trend was first tested in this build, on 2018-2024, the same seasons that now choose it. The odds were written first, but the choice and the score share seasons, so it's a discovery result. **2026 is its first clean test** (2025 too, if the vault is ever opened).
    - **What pulls it back** (to the rung below it, per rate, with no new build needed): on 2026, scored when the season ends, (a) the trend loses to the rung below it for 6+ of the 10 rates it ships for, sign only; or (b) its 80% ranges cover outside 70%-90% for 3+ of them; or (c) for a single rate, it loses to the rung below by more than its 2018-2024 gain. Any of these goes to the CEO with the numbers.
36. **The run-snap stand-in is corrected by I180** (the CEO: "try out the cheaper fix first"; `correct.py`). Each back's run snaps (snap share × the team's runs) are multiplied by his last season's exact-over-stand-in ratio from participation, shrunk toward his position's ratio with 200 run snaps' weight. Before 2017, or with no exact count, the ratio is the position's, or 1. Last season's participation is a completed season, so this is a prior from a retrospective source (rule m), known before the season. Only carries a run snap is corrected (`CORRECTED`). The other stand-ins either tie the exact version (defense) or are off by level (routes, F128), which the pull already absorbs.
    - **A floor, added after the first look:** run snaps are at least his carries in each game (`FLOOR`). I180 alone still left 5 of 38 lead backs above 1 for 2024 (the odds below failed), and a back can't carry on a run he isn't on the field for. This is marked as found after the result.
    - The stand-ins report compares the plain stand-ins (`Inputs.plain`), so its verdicts are unchanged. `stabilization-retro` stays a proposal.
37. **The code scan now allows `run.py` to read its own reports, and only that** (`checks.code_scan`: `read_text` only, every other read still fails). `run.py` reads the build's own text and JSON reports, to log them in MLflow and for `--history-only`; it never reads data. **The first two full runs ended "all passed: False"** because the scan flagged those reads, and **the build reported the leakage checks as all passed**. That was wrong: every other check passed, and the flag was a false alarm, but the report should have said so. The checks were rerun with the fix: all passed (`build/leakage.txt`), and the history's MLflow attempt now logs the true result.

### The odds, scored

**The trend (call 35):**
- It clears the shipped rung for 12+ of 20: **failed**, 10 of 20. It cleared for targets and yards a route, aDOT, YAC over expected, carries a run snap, yards after contact, sack rate, pressures a pass snap, QB hits a pass snap and targets a coverage snap. For yards after contact it beats the average (+6.9%, +2.0 to +11.8), which it used to ship.
- The history's next-season coverage stays within 74%-90% for every rate: **held**, 74%-90% (catch over expected 74%, carries a run snap 90%; run `9b0f405ff265454885dfed8b9d580a46`). Against v1's history, the ranges moved by a point at most, except carries a run snap's next 4 games (81% to 79%).

**I180 (call 36):**
- No lead back has a 2025 prior above 1: **failed for I180 alone** (5 of 38 lead backs above 1 in 2024, M1's 2025 prior up to 1.14). With the floor, **0 of 41** (top 0.99), and the shipped prior (the trend) tops out at 0.96 in the saved history.
- At most 2 do: **failed for I180 alone** (5); held with the floor.
- In season, the corrected rate still beats the average and its 19 copies, and the filter still beats static: **held**. Vs the average +82.1% (+75.9 to +86.5), best copy −98.4%, filter vs the pull +24.9% (+19.2 to +30.6), up from +20.1%.
- The season rate's correlation with the exact rate stays at 0.918 or within 0.01: **held**, 0.918.

**The spot-check:** scored in [`SPOT_CHECK.md`](../../projects/stabilization/SPOT_CHECK.md): 3 held (slopes steady, 70%+ of hindsight, dropping it sends rates to the average), 2 failed (6+ of 7 seasons for 6+ rates: 5; in-season slopes near 1: no).

**For the CEO's veto (new):** call 35's pull-back rules, call 36's floor (added after the look) and call 37's allowance for `run.py`.
