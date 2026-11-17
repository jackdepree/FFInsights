# Results: Context, the play-outcome forecaster (`context-live`)

**Date:** 2026-11-17 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **Decision:** [0036](../../docs/decisions/0036-context-live.md) · **MLflow experiment:** `context-live` · **Champion:** CHAMPION_TBD

## In short
For every scrimmage play from 2023, the expert gives 17 expected outcomes from the situation and both sides' calls, with nothing about who played. The calls beat the situation-only model, by more than the fitting noise, for 12 of the 17. They matter most for how a pass is thrown: time to throw (1.3% to 17.4% of squared error removed), depth of target (4.3% to 18.2%), pressure (1.0% to 4.2%) and completion (1.6% to 3.9%). For a run's yards and for how a play ends they add a few tenths of a point. Five outcomes ship the situation-only model: a stuffed run, a run's first down and touchdown, a dropback's touchdown, and penalties. Every shipped outcome beats all 20 of both nulls and is calibrated (after recalibrating two). Its ranges hold 79% to 82%. VAULT_SHORT

**Scorecard:** MLflow `context-live`, backtest run `70eeeeac16d24ae1aa4445aa10f4e695`; reports in [`build/`](build/) (`backtest.txt`, `sanity_backtest.txt`, `misses_backtest.txt`, `context_backtest.txt`, `vault.txt`) · **Vault:** VAULT_LINE · **Versions tried:** 3 before the vault, all 2023-2024: `smoke` (an end-to-end try, run 3a43d155), the first backtest (eb5cfc97) and the backtest with two fixes from the sanity check (70eeeeac). The ladder's 8 rungs per outcome and the 5 noise refits are inside each.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | 12 outcomes ship the live model: each beats the situation-only model (the whole 90% interval of the paired difference by week, 44 weeks) by more than the fitting noise, and beats all 20 shuffled-outcome nulls and all 20 shuffled-calls nulls. 5 ship the situation-only model, which beats the base rate and all 20 shuffled-outcome nulls |
| Calibration and range coverage | Chances: calibration error 0.18 to 1.34 points, slope 0.90 to 1.00, all pass (sack and explosive pass after recalibration: 0.81 to 1.00 and 0.94). Ranges: q10-q90 hold 79.7% (rushing yards), 79.6% (time to throw), 81.9% (dropback yards), 78.8% (depth of target), every season inside 70-90% |
| Leakage | `check_point_in_time`: 12 sample games (2023, 2024) rebuilt from a view at their own `as_of`, largest gap 0.0 in every field; 0 FTN rows visible the morning after a game. Training rows must be known before the test season's first `as_of` (the runner refuses otherwise). The on-field map's personnel was found to leak and left out (R11) |
| Football sanity (CEO review date) | Automatic rules: 0 violations after the fixes (chances in 0-1, ordered ranges, no yards past the end zone or behind the own goal line, no negative time to throw). The first backtest had 1,246 rushing and 1,970 dropback forecasts past the end zone: fixed by a clip (decision 0036, call 18). Review lists in `build/sanity_backtest.txt`: CEO review pending |
| CEO spot-check (date): what was checked | pending |

## Hunch verdicts
Copied into [`projects/HUNCHES.md`](../HUNCHES.md). The exploration's verdicts stand; the build's numbers are held-out over 2023-2024 with the shipped models.

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H63 | A run into a blitz with a light box gets stuffed, and the situation explains it | unclear (the size failed) | A blitz isn't charted on runs (EXPLORATION F1). The defense's call fields on a run are the box count: beside the situation they add 0.23 points of share to rushing yards (0.73% to 0.96%, the paired gain's interval clear of zero) and 0.11 to the stuffed chance (interval reaching zero). The CEO hoped for 10% |
| H64 | Rushing yards are the most forecastable outcome | failed | 16th of 17: 1.2% of squared error removed (against a base rate clipped to the field; 2.4% against the plain average). Ahead: a run's touchdown 28.2% and first down 24.3% (field position and distance), depth of target 18.2%, a dropback's touchdown 17.7%, time to throw 17.4% |
| H65 | Both sides' calls together explain more than either alone | held in part | Both beat either alone wherever the defense's calls matter (pressure: the situation 1.0%, with the offense's calls 2.8%, the defense's 2.4%, both 4.2%). Beyond the sum of each alone: nothing, for every outcome (−0.52 to +0.08 points; time to throw −0.52 and pressure −0.23, where the two sides' fields overlap) |
| H66 | Without context, a player who comes on for bad situations gets blamed for them | held, small | Players' average context spreads 0.71 points of success rate on offense and 0.67 on defense (player-seasons with 200+ plays); the furthest −3.3 and +2.2. It repeats (odd against even weeks 0.32 / 0.28; season to season 0.17 / 0.21). It is 3% / 5% of the spread in players' actual on-field success, and 80% / 77% of it is the situation alone |

## Terms
In `docs/GLOSSARY.md`: **context** (final), **the situation**, **call fields**, **expected outcome**, **a player's context** (`ctx_success`, `ctx_success_sit`, `ctx_calls`).

## Findings
Cited as `context-live#R<n>` (the exploration's are `#F<n>`). Held out over 2023-2024 (pressure and time to throw 2024 only), walk-forward, refit each season.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | **The calls beat the situation for 12 of 17 outcomes, by more than the fitting noise.** Gain in the main loss (log loss or range score) over the situation-only model: time to throw 12.0%, depth of target 10.5%, pressure 2.8%, sack 2.5%, completion 2.1%, explosive pass 1.4%, explosive run 0.9%, rushing yards 0.7%, dropback yards 0.5%, dropback first down 0.4%, run success 0.2%, dropback success 0.2%. The fitting noise: 0.04 to 0.42 | `build/backtest.txt` | strong | every scrimmage play, 2023-2024 |
| R2 | **What ships the situation alone:** a stuffed run (the calls' gain 0.20% with an interval reaching zero), a run's first down (0.17%, noise 0.41), a run's touchdown (−0.39%), a dropback's touchdown (0.30%, equal to its noise), and penalties (situation only by design). These are mostly the field: a touchdown and a first down are about distance | `build/backtest.txt` | strong | |
| R3 | **Linear rungs are as good as trees for three chances.** The live model is logistic for explosive run, pressure and sack (the trees didn't beat it); trees for the rest. Trees win the situation-only rung for amounts (rushing yards, time to throw, depth of target) and for run success | `build/backtest.txt` | moderate | |
| R4 | **Last season's scheme traits never beat the play's own calls.** schemes-v2's traits (over expected) added to the live fields: worse or level for every outcome, clearly worse for dropback yards (+0.007 range score), depth of target (+0.005) and run success (+0.003 log loss). A play's calls already say what the team did on it | `build/backtest.txt`, "traits vs live" | strong | post-game play models (not tested before the play) |
| R5 | **The two sides' calls add up, with no extra from the combination** (H65). The defense's calls (box, blitzers, pass rushers) matter for pressure (+1.7 points of share over the situation, both as trees), time to throw (+1.8) and sack (+0.2); for depth of target and dropback yards it adds nothing. The offense's side carries the rest | `build/backtest.txt`, "H65" | strong | |
| R6 | **Two chances were over-confident and are recalibrated.** Sack and explosive pass had calibration slopes of 0.81. Platt scaling fit on the last fifth of each training window takes them to 1.00 and 0.94, with log loss level (+0.0002, −0.0001). It made pressure worse (error 1.3 to 4.8 points: 2023 alone trains 2024) and completion too (slope 1.15), so it isn't applied to every chance | decision 0036, call 17 | strong | |
| R7 | **Half of what the situation "explains" about a run's yards is the end of the field.** Clipping every forecast, the base rate's included, to the distance to the end zone cuts the shares against the base: rushing yards 2.5% to 1.2% (situation alone 2.3% to 1.0%), dropback yards 2.2% to 1.6%. What the calls add over the situation hardly moves (0.68% to 0.69% of the loss) | decision 0036, call 18 | strong | yards outcomes; any "share explained" for yards |
| R8 | **"Plays like this one" (method C) is weaker than one model per outcome (method A), everywhere.** The 300 nearest earlier plays on the same fields: 0.3 to 3.5 points of share behind (rushing yards 2.0% against 2.4%, sack 1.1% against 1.4%, pressure 3.5% against 4.2%, completion 3.0% against 3.9%, depth of target 14.6% against 18.2%, time to throw 14.2% against 17.4%; both against the plain average). The two agree play by play at r 0.65 to 0.90. It isn't the version shown to users unless the gap is worth the story | `explore/plays_like_this.txt` | strong | |
| R9 | **Players play in different contexts, by about 0.7 points of success rate, and it repeats** (H66). Offense: spread 0.71 points across 1,117 player-seasons, 5th to 95th percentile −1.3 to +1.1; defense 0.67 across 1,185. Week r 0.32 / 0.28, season r 0.17 / 0.21. 80% / 77% of it is the situation alone; the calls' part spreads 0.32 points. 3% / 5% of the spread in players' actual on-field success. Wide receivers sit lowest on offense (−0.27), tight ends highest (+0.11) | `build/context_backtest.txt` | strong | player-games, 2023-2024 |
| R10 | **A defense's calls are steadier than an offense's** (I65). A team's call-added context (`ctx_calls`): the defense's repeats odd against even weeks at 0.40 (0.22 to 0.56), the offense's at 0.18 (−0.03 to 0.37). Season to season neither clears 0.3 (0.27 and 0.09, only 32 pairs). The offense's situation-only context repeats (0.41, season 0.31): it sets its own down and distance | `build/context_backtest.txt` | moderate | team-games |
| R11 | **participation-late's on-field chances leak a play's result into its personnel.** The map pins every player the play-by-play names and balances each play to 11, so its expected position counts know who was named. As call fields they "added" 0.3% to 1.7% of the loss; undoing the pins roughly made it larger (sack 1.1% to 15.3%). Left out (decision 0036, call 14; idea I63) | `explore/personnel_pins.txt` | strong | any model that uses the map's chances on the same play as its outcome |
| R12 | **Pressure and time to throw can't mix 2022 with later seasons.** The provider change of 2023 halved the pressure rate (29% to 15% of dropbacks) and moved time to throw (2.79 s to 2.65 s). Both are fit from 2023 here | decision 0036, call 5 | strong | any model with pressure or time to throw as target or input |
| R13 | **The biggest misses are whole seasons.** 2023 (trained on 2022 alone): rushing yards forecast 0.25 yards high, depth of target 0.22 yards low, run success 1.9 points high. 2024: dropback yards 0.17 low, completion 1.3 points low, pressure 0.9 points low. Within a season the misses by down, quarter, score, field zone, screen and play action are mostly under a tenth of the outcome's spread | `build/misses_backtest.txt` | moderate | |
| R14 | **The trees' mean over-shoots its own top tenth of expected rushing yards** (6.09 forecast, 5.20 actual, 2,761 plays); the linear rung's doesn't. Trick plays are 30% to 43% of the plays forecast above 7 yards: they do gain more (5.6 yards against 4.2) but not as much as the trees say at the top. The range score, which is what's scored, doesn't see it (idea I66) | `build/backtest.txt`, "mean by tenth" | moderate | rushing yards' mean |
| R15 | VAULT_FINDING | `build/vault.txt` | | 2025 |

## The ladder
Per outcome; the full table is in `build/backtest.txt`. Takeaways carried up: the exploration's tree settings; the call fields as one set (the exploration found no field worth dropping); FTN's "0" as missing; penalties on the situation only (EXPLORATION F2).

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | base rate (training mean and quantiles; clipped to the field for yards) | — | the floor every outcome must beat |
| 1 | the situation, linear (logistic or ridge, splines on distance, field position, clocks and score) | beats the base for every outcome (all 17 intervals below zero) | the splines' fields matter most: field position, distance, the clock |
| 2 | the situation, trees | beats linear for run success and the amounts; ties or loses for most chances | the situation's shape is simple: linear is enough for most chances |
| 3 | the live call fields, linear | beats the situation for 12 outcomes | the calls are mostly additive (H65) |
| 4 | the live call fields, trees | beats linear for 9 of those 12 (amounts, completion, the dropback's success and first down, explosive pass, run success) | the calls interact with the situation for amounts |
| 5 | plus schemes-v2's traits, trees | never beats rung 4 | the play's own calls carry what the traits know (R4) |
| side rungs | the situation plus one side's calls, trees | for H65: the sides add up (R5) | |

## Where it misses
The miss-lenses list (2026-11-15) is per player-game; this expert is per play, so its own play lenses are used (`report.misses`: season, down, quarter, score, field zone, screen, play action, trick play, the top tenth). The full report is `build/misses_backtest.txt`. The patterns that clear zero and matter:

| Lens | Group | Rows | Average miss (actual − predicted) | Idea |
|---|---|---|---|---|
| top tenth | rushing yards, the trees' top tenth | 2,761 | −0.89 yards | I66 (blend with the linear rung) |
| season | rushing yards, 2023 | 13,734 | −0.25 yards | I64 (weekly refits) |
| season | depth of target, 2023 | 19,184 | +0.22 yards | I64 |
| season | dropback yards, 2024 | 21,030 | +0.17 yards | I64 |
| down | depth of target, third down | 9,880 | +0.30 yards | third-down throws go deeper than the context says |
| screen | depth of target, screens | 4,026 | −0.26 yards | |
| screen | time to throw, screens | 1,879 | −0.08 s | |

## The case against
- **Every gain is the calls, and the calls are charted after the play.** A screen, play action and a trick play are partly what happened, and the box count and blitzers are what FTN saw. The biggest gains (time to throw, depth of target) are where the offense's calls describe the throw itself: a screen is a short, quick throw by definition. So "the context explains 18% of a target's depth" is partly "a screen is short". The brief accepts this (the CEO's call 3), but a later expert crediting a quarterback for depth over expected should know that the expected part already holds his screen calls.
- **Two test seasons, one for pressure and time to throw.** 44 weeks of blocks for most outcomes and 22 for those two. The no-noise rule asks for an interval clear of zero and a gain larger than the fitting noise; with one season, pressure's 2.8% gain rests on 2024 alone, trained on 2023 alone. The vault adds one more season.
- **The choice of what ships, and of which chances to recalibrate, was made on the same two seasons it is reported on.** The calibration fix (sack and explosive pass) was picked by their 2023-2024 slopes. The vault is the clean check (VAULT_CASE).
- **The fitting noise is small because the rows are many, not because the gain is large.** Run success ships the trees with a gain of 0.22% of the loss against a noise of 0.12. For a downstream user that is about 0.3 points of success rate on a play.
- **The calls carry talent in part** (the brief's flagged assumption). A light box is earned by the offense's receivers; a blitz is chosen against a weak line. Nothing measures how much here; the exploration found no team identity left at the play level, which bounds it but doesn't rule it out.
- **The player context uses the on-field map that leaks on single plays** (R11). Averaged over a player's 200+ plays the pins are a small part, but a player who is named often (a busy receiver) is placed on his own plays with more certainty than a blocker: his context is measured more sharply, not more favourably. Not measured.

## Pitfalls
- **Pressure and time to throw changed with the data provider in 2023** (decision 0036, call 5). `was_pressure` is charted on 29% of 2022's dropbacks and 15% after; time to throw averages 2.79 s then 2.65 s. The exploration trained 2023's pressure on 2022, which teaches the model the wrong base rate. Here they start in 2023: one season trains 2024, two train the vault.
- **participation-late's on-field chances carry the play's result** (call 14). The map pins every player the play-by-play names (the target, the tackler, the sacker, a pass defender) and balances each play to 11, so a play's expected position counts know who made the play. Added as call fields, they looked like 0.3% to 1.7% of the loss; undoing the pins made the "gain" larger (sack 1.1% to 15.3%), which is the signature of a leak. Any model that uses the map's chances on the same play as its outcome has this problem; a player's average over many plays (this project's player context) is much less exposed, since each play's pins are a small part of it, but not free of it.
- **FTN writes "0" for an uncharted QB location or hash.** Read as a value, it is a category of its own that marks plays FTN didn't fully chart. It is turned into missing here.
- **FTN's own known-at isn't the play-by-play's.** The gateway names it `ftn_known_at`; a play's row is known at the later of the two. The first point-in-time check used the combined known-at and counted 859 "early" FTN rows that weren't; it now compares FTN's rows against the play-by-play spine's known-at (the morning after) and finds 0.
- **The calendar for `as_of` must cover every season read.** A calendar limited to the scored seasons left 2022's playoff games without an `as_of`; the runner now takes the full calendar and refuses a play without one.
- **The trees' mean for an amount over-shoots its top tenth** (rushing yards 6.1 forecast against 5.2 actual). The range score, which is what's scored, doesn't see it; a squared-error check by tenth does (report `mean by tenth`). Read the trees' mean at the top with care (idea I66).
- **The smoke run is an attempt.** The first end-to-end try (tag `smoke`, MLflow run 3a43d155) counts in versions tried.

## Could be improved
1. **Weekly refits** (I64): the largest misses are whole seasons (R13), and 2023 trains on 2022 alone.
2. **The map without the play's own names** (I63), then personnel as a call field: the CEO's "3 wide receivers".
3. **A blend of the trees and the linear rung for the amounts' means** (I66), for the top tenth's over-shoot (R14).
4. **The chain (method B)**: pressure, then sack or throw, then completion, so the outcomes agree with each other.
5. **A shared post-game mode for the harness** (I62), before a fourth post-game expert writes its own runner.

## Not looked at
- **Method B, the chain** (pressure, then sack or throw, then completion, then yards): a later project, per the brief. How much of a sack is the pressure was answered in the exploration only.
- **Weekly refits** (idea I64): every test season is fit once, on the seasons before it.
- **The after-the-season fields** (coverage, routes, personnel from participation): `context-retro`.
- **Interceptions, fumbles, scrambles and a dropback's EPA**: left out by the CEO's call 2 (the exploration found nothing to explain).
- **A player-level or team-level forecast from the context** (does a player's context predict his next game?): the yardstick (`crude-forecaster`) will measure what the summaries add downstream.
- **Isotonic recalibration, or recalibrating every chance**: tried for five chances before the rerun, kept for the two that failed (call 17).

## Don't redo
- **Personnel from participation-late's map as a call field.** It leaks (call 14). Retry only with an edition that doesn't pin the play's own names (idea I63).
- **2022 in pressure or time to throw** without a fix for the provider change.
- **Schemes-v2's traits as play inputs.** Last season's team traits never beat the live call fields (they lose clearly for several outcomes): the play's own calls already say what the team did on it. They might still help a forecast before the play, which this expert doesn't make.
- **The map's named-player check** (`explore/personnel_pins.py`): done; the answer is above.

## Interface card
| | |
|---|---|
| **Inputs** | `play.pbp`, `play.ftn` (in-season view), `team_season.charted` (schemes-v2's traits, last season's; tried, not shipped), `play.participation` (retrospective view; pressure and time to throw as outcomes only); participation-late's history run `2a30b3e5` (player context only) |
| **Outputs** | `outputs/context-live/<run_id>/history.parquet`: the standard schema, one row per play and outcome, keyed `game_id, play_id`; `quantity` the outcome (`rush_yards_exp`, `run_stuffed_prob`, `run_explosive_prob`, `run_success_prob`, `run_first_down_prob`, `run_td_prob`, `pressure_prob`, `sack_prob`, `time_to_throw_exp`, `dropback_yards_exp`, `pass_explosive_prob`, `dropback_success_prob`, `dropback_first_down_prob`, `dropback_td_prob`, `air_yards_exp`, `completion_prob`, `penalty_prob`); `mean` the chance or expected value, q10-q90 its range (equal to the chance for a chance); `model_version` the shipped rung. Beside it: `player_game.parquet` and `team_game.parquet` (`ctx_success`, `ctx_success_sit`, `ctx_calls`, plays) |
| **Level of detail** | play (each outcome on its own population: designed runs, dropbacks, pass attempts, every snap); player-game and team-game for the context summaries |
| **Interval** | every scrimmage play from 2023 (walk-forward history; pressure and time to throw from 2024), 2025 from the vault run, 2026 from the champion |
| **Cadence** | in_season (post-game: describes plays that happened) |
| **Known at** | a play's rows: the first weekly run at least 14 days after kickoff (FTN's known-at), the same `as_of` as participation-late |
| **How to use it** | As "what the context expected" on a play: credit players and teams with the difference (actual minus expected). Read only the walk-forward history for training (rule e). A chance's range is the chance itself. Don't use a play's expected value as an input to a forecast made before that play's game: it is known two weeks after it |
| **Feeds** | voe-live, the attribution of plays to players, qb-talent, line-play, the game simulator's play model, the yardstick (`crude-forecaster`) |

## Open questions for the CEO
1. **The football sanity review lists** (`build/sanity_backtest.txt`): the plays with the highest and lowest expected pressure, completion, rushing yards, run and dropback success and depth of target, and where the calls move them most. Anything that looks wrong to you as a football watcher? The trick plays at the top of rushing yards (R14) are the one thing that looked odd to me.
2. **Method C as the version users see?** It is weaker everywhere (R8), but it is the one you can say out loud ("on the 300 plays most like this one, the back was stuffed 31% of the time"). Use it for display only, beside A's numbers, or not at all?
3. **Is a defense's steadier call pattern (R10) worth chasing as its own measure** (a defense's call-added context as a coaching trait, for game script or matchup models)?
