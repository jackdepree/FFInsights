# Results: Opportunity quality (`opportunity-quality`)

**Date:** 2026-11-21 (the build) · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `opportunity-quality` · **Champion:** none registered yet (as participation: the champion's history is pinned in the registry) · **Decisions:** [0041](../../docs/decisions/0041-opportunity-quality.md)

## In short
Expected fantasy points per chance are now a table (`play.xfp`, `player_game.opportunity`, 2009-start models, r 0.99 with nflverse's), and both of the CEO's main outputs pass the brief's tests. **The forecast of opportunity** (next game's expected points) beats its shuffled copy 100 of 100 times, beats the last-4 average by 17.6% of the range score and plain counts by 0.7%, and past efficiency is what lifts it (H61 held again: +1.1% of squared error). It also passes the no-noise target and adds 4% to the yardstick's crude forecast of yards. **The regression measure** (method B, a kept share per player) beats one rate per position by 1.2% and is calibrated once recalibrated on earlier seasons, but it barely separates players: most chances that a gap closes sit between 50% and 60%. ⟨trees, horizons, vault⟩

**Scorecard:** `outputs/opportunity-quality/eff/c95835de1df14da399a4024853e9ddd2/scorecard.html` (MLflow run `c95835de…`) · **Vault (2025):** ⟨pending⟩ · **Versions tried:** ⟨n⟩

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal | The forecast (`eff`) beats 100 of 100 shuffled refits; the regression measure beats 100 of 100 copies with its forecasts moved between players; the yards variants 20 of 20 |
| No noise | Next game's PPR points on targets and carries: the forecast adds +11.9% of squared error (+11.2 to +12.5), +7.6% range score: adds value. ⟨beside playing time⟩ |
| Beats baselines | Last-4 expected points −17.6% range score; counts −0.69% (−0.82 to −0.55); expected points without efficiency −0.60% (−0.73 to −0.47), all 90% intervals clear |
| Calibration and range coverage | Chance of a chance: error 1.1 points, slope 0.97. If he gets one: ranges hold 79.5% (80% target), 50.2% above the median; every position 78-80%. The regression measure: the chance the gap closes, 0.9 points error and slope 0.92 after recalibration (2.7 and 0.63 before); its future-gap range holds 79.5% |
| Leakage | All 10 checks pass at 25 cutoffs (10,553 rows compared); the regression measure's windows don't move when the future is deleted (test) |
| Football sanity | ⟨CEO review⟩ |
| CEO spot-check | ⟨date: what was checked⟩ |

## Hunch verdicts
Copied into [`projects/HUNCHES.md`](../HUNCHES.md). The exploration's verdicts stand where the build didn't retest.

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H56 | Goal-line chances are worth the most | held; real, doesn't pay (as the exploration) | The 2009-start model gives the exploration's numbers exactly (R2). Beyond plain counts the kinds add nothing to next game's points (+0.08% of squared error, range score +0.00%) or expected points (+0.04%, not clear) (R4). ⟨horizons⟩ |
| H57 | Expected points follow a player to a new team | partly (exploration; not retested) | Movers 0.52, stayers 0.67 (F7, F8) |
| H58 | Strong yards-after-catch receivers beat their expected points | unclear (as the exploration) | A weak trait (WR 0.09 week to week); as an input to the regression measure it pays for tight ends (+0.60%), not receivers (+0.09%, not clear) (R6) |
| H59 | Expected points are more consistent than efficiency | held | 0.84 against 0.13 per game week to week; per chance 0.75 against 0.02 (R3) |
| H60 | Opportunity by scheme follows movers better | failed (exploration; method C not built) | F10 |
| H61 | A player creates his own opportunity through efficiency | held, small | +1.11% of squared error (+0.87 to +1.33) on next game's expected points; first two seasons +1.47%; fitting noise 0.02 (R10, R16) |
| H62 | Players whose pattern holds across teams don't regress | failed, leaning (exploration; not retested) | F12; method B's per-player rates come from sample size alone and beat one rate per position (R5), which is not H62's claim |

## Terms
In `docs/GLOSSARY.md`: **chance**, **expected points of a chance** (PCF's xfp), **points over expected**, **the gap**, **kept share**, **chance the gap closes**, **chance of a chance**. The brief's "seat" wasn't needed (method C not built).

## Findings
Build findings are R1-R⟨n⟩; the exploration's are F1-F13.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | **The expected-points table matches nflverse's** at r 0.992 per player-game (64,795; 0.990-0.994 every season 2012-2025), means 7.94 against 8.12. The situation alone removes 6.8% of a target's squared error and 13.6% of a carry's | `build/facts.txt` | strong | RB, WR, TE, 2012 on |
| R2 | **Points per kind of chance, on the 2009-start model, are the exploration's:** an end-zone target from the 10 or closer 3.36 points (45% a touchdown), a carry inside the 2 3.18 (52%), against 1.69 for an average target and 0.63 for a carry. The td-expert pitfall (biased 2006-2008 targets) didn't move them | `build/facts.txt` | strong | 2019-2024 |
| R3 | **Expected points are a trait; efficiency per chance is noise.** Per player-game, 2012-2024: expected points 0.84 week to week, 0.75 season to season; points over expected per game 0.13 and 0.17 (a weak trait, carried by volume); per chance 0.02 (−0.00 to 0.04) and 0.03: noise. Expected points per chance 0.75 and 0.78, deep-target share 0.42 and 0.45, goal-line share 0.17 and 0.20 (traits) | `build/facts.txt`, CONSISTENCY.md | strong | RB, WR, TE |
| R4 | **The kind of chance adds nothing beyond the count** (exploration F4, rechecked): goal-line carries, red-zone, end-zone and deep targets, air yards and expected touchdowns add +0.08% of squared error (+0.03 to +0.13) and +0.00% range score to next game's points, −0.03% beside the forecast, +0.04% (not clear) to next game's expected points. ⟨horizons⟩ | `build/downstream_eff.txt` | strong | next game |
| R5 | **Method B (a kept share per player) beats one rate per position** on the rest of the season's points over expected per chance: +1.19% of the weighted squared error (+0.95 to +1.44); RB +1.90%, WR +0.69%, TE +2.12%. Method A beats "all luck" by +2.71%; "it all lasts" is 38% worse than all luck. Shuffled null 100 of 100. **At week 1 (next season, 2,005 rows) B and A tie:** +0.74% (−0.39 to +1.79) | `build/regression_backtest.txt` | strong in season; a tie for next season | 2016-2024, 20+ chances behind, 10+ ahead |
| R6 | **Yards after the catch pay for tight ends only.** Added to B: TE +0.60% (+0.40 to +0.80), WR +0.09% (−0.07 to +0.25), RB +0.00%. The receivers' weight flips sign from season to season (−0.51 to +0.87); the tight ends' is positive every season (+0.23 to +0.65) | as R5 | suggestive | TE |
| R7 | **The kept share rises with chances, as the model says, but B keeps too much at 200-400 chances:** kept 0.12, 0.23, 0.36, 0.48, 0.60 at 20-50, 50-100, 100-200, 200-400, 400+ chances; seen 0.10, 0.16, 0.36, 0.36, 0.54 | as R5 | strong | |
| R8 | **The chance the gap closes is honest but not sharp.** Gaps close by half or more 55.4% of the time. Raw, B is overconfident (calibration error 2.7 points, slope 0.63); recalibrated on earlier seasons (Platt), 0.9 points and 0.92. 72% of the forecasts sit between 50% and 60%; under 1% are above 80% | as R5 | strong | |
| R9 | **The forecast of opportunity works:** next game's expected PPR points, range score 0.82 (MAE 2.56 points; average 5.03, 36% of rostered player-games get no chance). It beats the last-4 average by 17.6% of the range score, counts by 0.69%, expected points without efficiency by 0.60%; 100 of 100 shuffled refits; all 10 leakage checks | the scorecard | strong | RB, WR, TE, 2016-2024 |
| R10 | **H61: efficiency earns work.** Past points over expected improve next game's expected-points forecast by +1.11% of squared error (+0.87 to +1.33), +0.60% range score; first two seasons +1.47%, veterans +0.96%; WR +1.44%, RB +0.94%, TE +0.43%. The fifth of players most over expected this season are forecast 0.55 expected points a game above the forecast without efficiency, and get 0.53 more; the fifth most under, −0.45 and −0.56 | walks on the saved features | strong | |
| R11 | **Past expected points add little beside counts and playing time:** +0.12% of squared error (+0.01 to +0.24), +0.09% range score, about 3 times the fitting noise. The exploration's F5 (+0.73%) was beside past points with no counts | as R10 | strong | |
| R12 | **Trees beat the lasso on the same inputs:** +2.75% of squared error (+2.24 to +3.27), +1.83% range score; seeds 0, 1, 2 give +2.85, +2.86, +2.78. ⟨harness⟩ | `build/downstream_eff.txt` | strong | |
| R13 | **The forecast passes the no-noise target:** next game's PPR points on targets and carries, against past points, targets, carries, snaps and position: +11.9% of squared error (+11.2 to +12.5), +7.6% range score; RB +13.7%, WR +11.9%, TE +8.0%. Past expected points alone add nothing there (−0.05%; the exploration's −0.19%). ⟨beside playing time⟩ | as R12 | strong | 2019-2024 |
| R14 | **On the yardstick, expected yards add 4%.** Alone on the crude forecast of next game's yards (2019-2024): the expected receiving yards forecast +4.15% (+3.72 to +4.58), range +2.87%; expected rushing yards +4.55% (+3.68 to +5.39), range +2.58%; the expected points forecast +2.0% and +2.2%. The crude forecast already has participation's forecasts | as R12 | strong | receiving, rushing |
| R15 | **Fitting noise is small:** leaving out one training season moves each gain by 0.02-0.04 points of share (eff over xfp, eff over counts, xfp over counts) and the no-noise gain by 0.10 | as R12 | strong | |
| R16 | **The situation model under-expects tight ends, and receivers more each year.** The average points over expected per chance, fit on the six earlier seasons: TE +0.09 every season; WR +0.025 (2016) rising to +0.073 (2024); RB about 0 to +0.03. The method subtracts this average, so it doesn't bias the measure, but "expected" has no position in it | `build/regression_backtest.txt` | strong | |

## The ladder
Next game's expected PPR points, 2016-2024, range score.

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | Last 4 rostered games' expected points (absences 0) | — | |
| 1a | `counts`: playing time (participation's inputs) + past targets, carries, snaps; two-part lasso | −17.0% range score vs rung 0 | Playing time first (participation) |
| 1b | `xfp`: + past expected points | −0.09% vs counts (R11) | Small: counts already carry it |
| 1c | `eff`: + past points over expected, per chance, yards after the catch | −0.60% vs xfp (R10) | The efficiency inputs are the gain (H61) |
| 3 | `eff_trees`: boosted trees on `eff`'s inputs | −1.83% vs eff (R12) ⟨harness⟩ | |

## Where it misses
⟨from the scorecard's misses⟩

## The case against
1. **The no-noise pass is mostly playing time.** The brief's baseline has no snap shares, injury report or depth chart; the forecast carries participation's inputs. ⟨the fair pair⟩
2. **The regression measure barely separates players.** It beats one rate per position by 1.2% of a small number: the whole measure removes 3.9% of "all luck"'s error. 72% of its chances sit between 50% and 60%; a "buy low" list from it would be mostly coin flips. And for next season (week 1) it ties method A, the brief's literal failure test (R5): by rule k, A could ship for the season-ahead case.
3. **B keeps too much for players with 200-400 chances** (0.48 against 0.36 seen, R7), the players fantasy cares about most. The normal model for one chance's points over expected is too simple (they are skewed: a touchdown is +5 on one chance).
4. **"Expected" isn't expected for tight ends** (R16): a model without position calls every tight end efficient by 0.09 a chance. The measure subtracts the average, but any reader of the raw table will be misled.
5. **The yardstick's 4% looks large** for an input the crude forecast nearly has (past yards). The likeliest reason is real (expected yards are past yards with the luck taken out), but no check here tells that from an alignment error, beyond the as-of check and the leakage checks on the forecast itself.
6. **The 2016-2018 seasons are in every downstream model's training,** so the no-noise and yardstick gains are 2019-2024 only, as the brief says, on one set of training seasons (fitting noise 0.10).

## Pitfalls
- **A null `sack` dropped targets:** `sack != 1` drops nulls in Polars; `fill_null(0)` first.
- **Reading saved files from an expert's package fails leakage check 1,** even for analysis code. The saved-feature readers now live in `pcf.validation.backtest` (`save_features`, `load_features`, `latest_history`).
- **A saved feature history's step numbers count from its first season;** walking it again needs the same first season (`downstream.walk_saved`).
- **Participation's saved histories stop at 2024,** so an expert that reads them can't be scored on the vault; this one recomputes participation's inputs instead (decision 0041).

## Not looked at
- Method C (player and seat) and H60, as the CEO decided; H57 and H62 not retested.
- Pace's team volume forecasts as inputs (decision 0041, call 8).
- Half-PPR and standard: the table supports them; only PPR was validated.
- Playoff games: the expected models learn from regular seasons; playoff chances are scored but not validated.

## Could be improved
1. A position term (or position-specific models) in the expected-points model, so tight ends aren't "efficient" by construction (R16).
2. A skewed noise model for one chance's points over expected (touchdowns), to fix B's over-keeping at 200-400 chances (R7).
3. Trees for the yards variants, if the trees rung holds for expected points.
4. The yardstick's shuffled-copy check for this expert's columns, to read the 4% against the noise floor directly.

## Don't redo
- The kinds of chance beyond counts: two looks (F4, R4), nothing. Retry only with a new outcome (touchdowns: td-expert).
- Past expected points beside counts: +0.12% (R11).

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `play.pbp`, `player_game` parts roster, snaps, game_status, depth, injury, stats, opportunity through the gateway; game schedule for the horizons |
| **Outputs** | Facts: `play.xfp` and `player_game.opportunity` (`oq_` columns: chances, targets, carries, catches, yards, touchdowns and their expected values, goal-line, red-zone, end-zone and deep chances, air yards, yards after the catch over expected). Forecast: `outputs/opportunity-quality/<variant>/<run_id>/history.parquet`, next game's expected PPR points with `p_nonzero` and `if_nonzero_*` ⟨champion⟩. Regression measure: `outputs/opportunity-quality/regression/<tag>/history.parquet` (points over expected per chance over the rest of the season, mean and q10-q90; `kept_share`, `true_q10`/`true_q90`, `p_gap_closes`, `gap`, `chances`) |
| **Level of detail** | play; player-game |
| **Interval** | facts 2002 on (expected values 2012 on); forecast and measure weekly, 2016-2024 reported, every rostered RB, WR and TE; the measure for players with 20+ chances behind them |
| **Cadence** | in_season |
| **Known at** | facts with the play-by-play (kickoff + 1 day); forecast and measure at the Saturday run |
| **How to use it** | Expected points per player-game as an opportunity feature (a trait, R3). The forecast as a feature for points and yards, from saved histories only (rule e). The regression measure as a player-card number and a prior; don't sort players by it (R8) |
| **Feeds** | td-expert, vacated-opportunity, player-opportunity, fantasy-projections; the yardstick |

## Open questions for the CEO
⟨in the report⟩
