# Results: Pace and play-calling (`pace`)

**Date:** 2026-11-11 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `pace` · **Technical calls:** [decision 0028](../../docs/decisions/0028-pace.md)

## In short
PCF now measures each team's habits on every play. Two yardsticks: its own expected pass chance, and an expected pace that knows when the clock stopped. From those it forecasts each team's next-game habits and volume before kickoff.
- **H22, the brief's main test:**
  - every-play habits are steadier than neutral-situation ones, week to week: pace 0.84 against 0.77, pass rate over expected 0.77 against 0.63;
  - swapped into the same volume model, they beat the neutral ones for plays, dropbacks and runs, each with the whole 90% interval below zero.
- **The gains are small.** A team's volume in one game is still mostly decided on the day. For plays: r 0.17 per team, 0.27 per game.
- **The line is missing.** nflverse's lines are known only at kickoff, after the Saturday run, so the volume models have none (R5).

**Scorecards:** `data/outputs/pace/<variant>/<run_id>/scorecard.html` (MLflow experiment `pace`).
**Vault:** spent for schemes. The confirmation is the 2016–2024 walk-forward plus 2026 live (the brief).
**Versions tried:** 1 per final variant. plays_full was rerun once, to confirm R5.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal, or beats baselines | All 12 final models beat 100 of 100 shuffled refits. Each beats every one of its yardsticks, with the whole 90% interval below zero (R1, R2) |
| Calibration and range coverage | 80% ranges hold 79.4–81.8% for every final model, with every season inside the bar |
| Leakage | Every blocking check passes for every run: identical at 25 cutoffs when future data is changed or deleted |
| Football sanity | Game totals are forecast at 121–144 plays, inside 110–150. Coach changes move pace (R4). "Favorites run more" can't be tested without a line (R5). The CEO's review is pending |
| CEO spot-check | pending |

## What's built
- **`team_game.pace`** (decision 0028): each team's volume and habits per game, 2002 on (the first season with three earlier ones to fit on), known the day after the game.
  - **Volume:** plays, dropbacks, runs, drives, plays per drive.
  - **Habits:**
    - pass rate over expected, on every play and on 1st, 2nd and 3rd down apart, with their counts;
    - pace over expected, in seconds on every snap with a gap;
    - the no-huddle rate.
  - **Also:** EPA per play.
  - **The defense's versions:** what offenses did against it.
- **`play.pace`:** each snap's PCF expected pass chance, pass over expected, expected gap and pace over expected, for `player-pace`.
- **PCF's expected models:** expected pass chance and expected gap, gradient-boosted trees fit for each season on up to the 10 seasons before it. They're cached, and checked to have been fit only on earlier seasons.
- **The expert** (`pcf.experts.pace`), 39 variants:
  - **Per habit:** the league, last-4 and season averages, and schemes-v2's blend.
  - **Per volume measure** (plays, dropbacks, runs):
    - the league, season and last-season averages;
    - the usual way (`_neutral`: history, the line, efficiency, neutral habits);
    - the full-sample way (`_full`: the same with the full-sample habits).

## Build findings

**B1. The built measures repeat as the exploration found, once each is a gap from its season's league level** ([`build/consistency_built.py`](build/consistency_built.py); regular seasons 2006–2024, 608 team-seasons).

| Measure | Week to week r | Season to season r | Exploration |
|---|---|---|---|
| Pace over expected, clock-aware, every snap | **0.84** | 0.57 | 0.85 |
| Neutral tempo (seconds, after in-bounds runs) | 0.77 | 0.53 | 0.82 |
| PROE, every play (PCF's expected pass chance) | **0.77** | 0.49 | 0.77 |
| PROE, neutral (nflverse `xpass`) | 0.63 | 0.40 | 0.64 |
| PROE on 1st / 2nd / 3rd down | 0.67 / 0.68 / 0.59 | 0.44 / 0.47 / 0.52 | |
| No-huddle rate | 0.88 | 0.53 | 0.89 |
| Plays / dropbacks / runs | 0.29 / 0.49 / 0.48 | 0.34 / 0.34 / 0.40 | 0.35 / 0.56 / 0.51 |
| Drives / plays per drive | 0.30 / 0.37 | 0.34 / 0.40 | |
| Defense: plays / PROE / pace over expected allowed | 0.15 / 0.23 / 0.08 | 0.23 / 0.31 / 0.26 | |

The full-sample habits are steadier than the neutral ones: pace 0.84 against 0.77, PROE 0.77 against 0.63. That's the first half of the brief's test of H22. Third-down PROE repeats least within a season and most across seasons. What a defense allows barely repeats: pace is the offense's choice.

**B2. Pace over expected drifts in the early seasons, and that drift would have faked consistency.** The league's average pace over expected is +7.9 s in 2002, +3.3 s in 2006, and within ±0.9 s from 2010 on. Each season's model is fit on the seasons before it, and the early clock data looks different. Pooled raw, the shared drift makes the defense's pace over expected look like a strong trait (0.80 week to week, 0.80 season to season); centred, it is 0.08. Every feature is a gap from the league's level over the last two seasons, so the forecasts aren't touched, but any later use of the raw level must centre it by season.

**B3. PCF's expected pass chance has no drift:** the league's PROE stays within ±0.025 every season 2002–2026, where nflverse's `xpass` runs 1–2 points high from 2022 (pace#F13). A game's plays (both teams) run 111 to 158 (1st to 99th percentile, median 129), inside the brief's sanity band.

## Findings

**R1. The volume forecasts beat their averages, and the full-sample habits beat the neutral ones.**
- **The test:** walk-forward 2016–2024 at the Saturday run, 4,952 team-games each.
- **Runs:** `9d3af791` plays_full, `dc7b7181` plays_neutral, `d39f53b1` dropbacks_full, `151465b7` dropbacks_neutral, `252161d4` runs_full, `cdb7590f` runs_neutral.

| Next game | Season to date | Last season | Usual way (`_neutral`) | **Full sample (`_full`)** | Full against usual: range score (90%) | r with result, team / game | 80% range holds |
|---|---|---|---|---|---|---|---|
| Plays | 7.42 | 7.14 | 6.89 | **6.88** | −0.004 (−0.007 to −0.001) | 0.17 / 0.27 | 79.6% |
| Dropbacks | 7.47 | 7.39 | 6.97 | **6.94** | −0.009 (−0.013 to −0.005) | 0.28 / 0.38 | 80.6% |
| Runs | 6.03 | 5.90 | 5.62 | **5.60** | −0.007 (−0.010 to −0.004) | 0.30 / 0.39 | 80.8% |

- **Typical miss:** the mean absolute error, in plays.
- **Against the averages:** both rung-1 models beat both averages by a lot (range score −0.08 to −0.18).
- **The H22 test:** swapping the habit sets is like for like. Same model, same rows; only the habits differ.

**R2. Every habit forecast beats its averages.** Runs: `fdbdc0e5`, `331e6a9a`, `6562ef30`, `9d0879f9`, `abd4c79c`, `0ec004d4`. Typical miss:

| Habit (units) | League | Last 4 | Season to date | **Blend** | r with result | 80% range holds |
|---|---|---|---|---|---|---|
| Pace over expected (seconds) | 1.26 | 1.14 | 1.12 | **1.08** | 0.50 | 81.0% |
| PROE, every play | 0.061 | 0.058 | 0.057 | **0.055** | 0.45 | 80.1% |
| PROE, 1st down | 0.087 | 0.087 | 0.085 | **0.081** | 0.36 | 79.6% |
| PROE, 2nd down | 0.095 | 0.094 | 0.093 | **0.088** | 0.38 | 80.4% |
| PROE, 3rd down | 0.074 | 0.075 | 0.073 | **0.069** | 0.38 | 79.4% |
| No-huddle rate | 0.074 | 0.065 | 0.064 | **0.061** | 0.62 | 81.8% |

The every-play PROE forecast tracks its result at r 0.45; schemes-v2's neutral pass rate blend reaches 0.35 (schemes-v2#R1). The targets differ, so this compares how forecastable each one is, not which model is better.

**R3. What the volume models weigh.** From [`build/sanity.py`](build/sanity.py): fit once on 2010–2024 rows, for reading only. In plays, per sd of each input:
- **Plays:**
  - pace matters as much as the team's own play history: its own (−0.73; faster means more plays) and its opponent's (−0.59);
  - then what the opposing defense allows (+0.44), pass rate over expected (+0.35), and both offenses' and defenses' efficiency (+0.31, +0.29).
- **Dropbacks:** pass rate over expected dominates (+1.68), then what the defense allows (+0.60) and pace (−0.50).
- **Runs:** pass rate over expected (−1.56) and what the defense allows (+1.01), then efficiency (+0.72: good offenses lead, then run).
- **The neutral versions** weigh tempo and neutral PROE the same way (tempo −0.65; neutral PROE +1.09 for dropbacks).

**R4. Coach changes move pace** (the brief's sanity test). Over 576 team-season pairs, 2006–2024, centred by season, a team's season pace over expected repeats at:
- r 0.67 with the same head coach (typical change 0.69 s);
- r 0.22 with a new one (typical change 0.93 s).

Pass rate over expected: 0.54 against 0.23.

**R5. The schedule's line isn't known at the Saturday run, so the volume models have no line.**
- **Why:** nflverse's spreads and totals sit near the close, so PCF dates them at kickoff (docs/DATA_SOURCES.md).
- **What happened:** every Saturday forecast saw the fallback (a pick'em, a 44-point total), the same on every row. A column that never varies can't change a prediction, so it's now removed. A rerun of plays_full without it gives the same predictions on all 4,952 rows (run `dbdb566f`; largest difference 3×10⁻¹³ plays), and beats 100 of 100 shuffled refits.
- **What it costs:** the brief's "favorites run more" can't be tested here. Efficiency stands in for team strength (good offenses run more, R3).

## The ladder
| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | League, last 4, season, last season averages | — | Last season beats season to date for volume (single games are noisy) |
| 1 (habits) | schemes-v2's blend (shrunk season, last 4, last season, coach) | Beats every average, all six habits | The coach's history matters, as in schemes |
| 1 (volume) | Weighted least squares: history, what the defense allows, efficiency, habits | Beats both averages by 0.08–0.18 of range score; full beats neutral | Pace and PROE carry most of the habits' weight; the opponent's pace matters almost as much as the team's own |
| 2 | Drives × plays per drive, both teams together (brief item 2) | Not built | Waits: rung 1's gain over neutral is small, and plays per drive weighs little once efficiency is in (R3) |

## Where it misses
Not run: the miss lenses are built for player-game (`pcf.validation.misses`). Two things to look at next: playoffs (schemes' one clear miss) and blowouts, where volume follows the score.

## The case against (2026-11-11, written before the merge)
1. **The H22 win is small.**
   - Full against neutral is −0.004 to −0.009 of range score, or 0.01–0.03 plays of typical miss.
   - It's clear of zero on 4,952 rows, but downstream it may be worth nothing.
2. **The confirmation isn't independent of the discovery.**
   - The habits and the clock-aware pace were chosen on 2006–2024 in the exploration, and the backtests run on 2016–2024, inside that.
   - The vault is spent, so only 2026 live is a clean test.
3. **The neutral yardstick isn't the brief's exact "usual projection."**
   - It's the same model with neutral habits, which is richer than neutral pace plus the line's game script. That can't be built without a Saturday line (R5).
   - The test is fair to H22, but it isn't a test against what a public projection does.
4. **The volume models have no line (R5).** Any market-aware projection includes one, so these forecasts may lose to a simple line-based one at kickoff.
5. **The expected models drift in the early seasons (B2).** The forecasts work in gaps from the league's level, and the tests start in 2016. But anyone reading raw `pace_oe` before 2010 will be misled.
6. **The fitted models are cached by code version and seasons, not by the raw data.** If nflverse revises an old season, the cache keeps the old fit until `MODEL_VERSION` is bumped.
7. **Nothing reads these yet.** Whether they help player volume or fantasy projections is untested.

## Pitfalls
- **Pooled consistency needs centring by season** whenever a measure's league level moves (B2). The defense's pace looked like a strong trait until it was centred.
- **A line known only at kickoff vanishes at the Saturday run.** Check what a feature looks like at the moment, not in the table (R5).
- **Two column names clashed with existing parts:** `def_dropbacks`, and nflverse's `pass_oe`. `check_parts` caught both.

## Not looked at
- Pass success as an input to the PROE forecast (H21 held, small, in the exploration).
- The structural rung (drives × plays per drive).
- Playoffs and blowouts as miss lenses.
- The ledger: these forecasts aren't in live-experts yet.

## Could be improved
1. **A line at the Saturday run:** Elo's margin forecast, or the odds PCF collects from 2026. Elo's needs the gateway to read versioned outputs, which no expert does yet.
2. **The structural rung** for volume, built for both teams together.
3. **Pass success** in the PROE blend (H21).
4. **The live ledger:** add the 12 final models with their season-to-date yardsticks (the CEO's call, as for live-experts).

## Don't redo
- **Don't use nflverse's `xpass` for levels** (pace#F13). Use `play.pace`'s `pcf_xpass`.
- **Don't measure pace from win chance and expected points alone** (pace#F4). The clock stopping explains 78% of the gap.
- **Don't treat the schedule's line as known before kickoff.**

## Interface card
| | |
|---|---|
| **Inputs** | `team_game` (schedule, pregame, opening_coach, tendencies, pace); no model outputs |
| **Outputs** | Per team-game, with mean, q10, q50, q90: next-game `plays`, `dropbacks` and `runs` (`<v>_full`), and the habits `pace_oe`, `proe`, `proe_1st`/`_2nd`/`_3rd` and `no_huddle` (`<h>_shrunk`). Tables: `team_game.pace` (per game, 2002 on) and `play.pace` (per snap) |
| **Level of detail** | Team-game; the play part per snap |
| **Interval** | Weekly at the Saturday run (Thursday games on Thursday), from week 1, using last season's habits before a team's first game |
| **Cadence** | in_season |
| **Known at** | Forecasts at the Saturday run; the table parts the day after each game |
| **How to use it** | As features for player volume and fantasy projections; the habits as team traits (they follow the head coach). Use gaps from the league's level, never raw `pace_oe` before 2010 (B2). There's no line inside: add it downstream at kickoff |
| **Feeds** | player-pace (the play part), player opportunity, fantasy projections, environment |

## Open questions for the CEO
1. Should the 12 final models go into the live ledger now, or after the line is added?
2. Is the small H22 gain enough to call H22 held, or does it stay mixed until it helps something downstream?

## Technical calls (for veto at merge)
All in [decision 0028](../../docs/decisions/0028-pace.md):
- the expected models (trees, fit on the 10 earlier seasons, cached);
- keeping plays with missing inputs;
- what counts as a snap and a gap;
- the renamed columns;
- reusing schemes-v2's history averages, and dropping schemes-v2 from `depends_on`;
- the volume model's inputs;
- centring consistency by season;
- (R5) no line in the volume models.
