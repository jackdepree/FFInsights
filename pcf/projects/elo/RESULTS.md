# Results: Team Elo (`elo`)

> **2026-11-07: done.** Every variant was revalidated with the 0.4 pull (decision 0021), and margin and win again with the seed-locked flag (decision 0022, F14); every check passes. The CEO reviewed the technical calls and the football sanity lists, did the spot-check (F12) and approved the merge (2026-11-07). No champion is registered: registering needs a logged model, and no project has one yet.

**Date:** 2026-11-07 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `elo` · **Champion:** not registered yet (proposed: `margin`, `total`, `win`)

## In short
A team rating in points, walked over every result since 1999, plus a missing-QB and same-team adjustment (the CEO's H1) and a seed-locked flag for the final week (the CEO's choice, F14), forecasts the margin within 0.27 points of the closing line and the total within 0.30. That's inside the brief's 0.5 bar, though not the 0.25 "strong" mark. Outside the last two regular-season weeks it is 0.22 behind. The final week is still the weakest, 0.89 behind (1.32 before the flag), because teams rest starters and a rating can't see it. Every check passes, and the full rating beats the plain chess-style Elo on all three forecasts. It adds nothing to the close: blended in, it changes nothing, as expected.

**Scorecards** (MLflow runs, in `data/outputs/elo/<variant>/<run>/scorecard.html`): `margin` 21082e26, `total` 417b504c, `win` b811be43; yardsticks `margin_simple` 16a0b1aa, `total_simple` a5ce1aa1, `win_simple` 75092826; long horizon `wins_next3` 90d57816, `wins_rest` 4cad4574, their yardsticks acb14f05 and f44e6c1f (they don't use the pull) · **Vault:** closed · **Versions tried:** through the harness, 3 for margin and win (pull 0.5, 0.4, then the lock flag), 2 for the others (the exploration tried 26 findings' worth of rungs and hunches)

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal | **Pass:** every variant beats 20 of 20 shuffled refits (margin 3.244 range score against shuffled 3.432–3.586) |
| No noise | **Pass, neutral:** the close with Elo blended in is unchanged: margin +0.000 (−0.003 to +0.004), total −0.000 (−0.005 to +0.004), win +0.001 (−0.000 to +0.001), 193 weeks (F4). Target approved by the CEO (2026-11-07) |
| Long horizon beats its yardstick | **Pass, both:** wins over the next 3 games, range score −0.011 (−0.013 to −0.009), mean miss 0.72 wins against 0.75; rest of season −0.027 (−0.033 to −0.021), 1.40 against 1.48 (F8) |
| Beats the simple Elo (the brief's main test) | **Pass, all three:** margin −0.031 range score (−0.045 to −0.017), total −0.013 (−0.024 to −0.002), win −0.007 log loss (−0.012 to −0.004) (F1) |
| Near the close (bar 0.5, strong 0.25) | **Pass, not strong:** margin 10.06 vs 9.79 (0.27), total 10.74 vs 10.44 (0.30) (F2) |
| Calibration | **Pass:** win chances: error 1.99 points (bar ≤ 3; 2.29 before the lock flag), slope 0.96 (bar 0.9–1.1) |
| Range coverage | **Pass:** margin 81.3%, total 80.7% inside q10–q90; every season 79–85% (margin) and 75–84% (total); favorites and close games 80–83% (F5) |
| Leakage | **Pass:** all 9 blocking checks on every variant; features identical at 25 cutoffs. The long horizon first failed two checks and the lock flag one; all are fixed (Pitfalls) |
| Football sanity | **Pass:** automatic rules pass, and the CEO reviewed the top and bottom forecasts and the biggest disagreements with the close (2026-11-07) |
| CEO spot-check | **Done:** the final-week misses (F12), plus the long horizon's assumptions (F13) |

## How it works, in plain terms
**Inputs:** every final score since 1999 (in the order they became known), the schedule (who's at home, neutral sites), each week's roster, the last 4 games' snap shares, and the injury report known by the run. Nothing else: no stats, no betting lines.

**The rating walk** (no fitting, the same every run):
1. Every team has a **rating in points**: how much better than an average team on a neutral field. All start at 0 in 1999.
2. Before a game, the **raw forecast** is the rating gap plus home field (the mean home margin of the last 3 seasons: 2.3 points in 2024).
3. After it, **both teams move by 6% of the miss**: the winner of the surprise goes up, the other goes down by the same amount.
4. Each new season, every rating is **pulled 40% of the way back to 0**: rosters change and luck doesn't repeat. 40% is how much Elo's end-of-season rating actually regresses into the next season (F9, decision 0021).
5. The same walk runs on **points scored and allowed** (offense and defense ratings, 5% step, one-third pull), which gives the total.

**The fitted layer** (refit every week on earlier games only) turns those numbers into the forecasts. It weighs the rating gap, home field, a missing usual QB and the share of usual snaps available, and adds ranges from past misses.

**Worked example, Lions at Texans, 2024 week 10** (Sunday night, forecast Saturday noon):

| Step | Number |
|---|---|
| Ratings at the end of the 2023 regular season | DET +2.8, HOU −1.6 (the playoffs then moved both up) |
| After the 40% pull, then 8 games of 2024 | DET +7.4 (1st in the league), HOU −0.1 (17th) |
| Raw forecast, Texans' margin | −7.5 gap + 2.3 home field = **−5.2** |
| Fitted forecast | the gap, home field and the same-team gap (Houston had 86% of its usual snaps, Detroit 90%), weighed by this week's refit = **−6.3**, range −22 to +11 |
| The close | −4.5 |
| Result | Lions won 26–23: Texans' margin **−3** |
| Update | miss = −3 − (−5.2) = +2.2; × 0.06 = 0.13. DET 7.39 → 7.26, HOU −0.10 → +0.03 |
| Total | 13.6 + 0.70 × 49.4 (offense/defense total) + 4.6 × 0.23 (share of usual snaps missing, both teams) = **49.1**; close 49.0; actual 49 |
| Win chance (Texans) | 31%; the close (no-vig moneyline) 33% |

## Hunch verdicts
From the exploration (EXPLORATION F5–F23), already in [`HUNCHES.md`](../HUNCHES.md). Validation changed none of them; the carryover study (F9) sized H2a's pull.

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H1 | Who is actually playing matters | held | A missing usual QB and the same-team share together cut the margin miss by about 0.06 points; through the harness, rung 3 beats rung 1 by 0.021 range score (F1) |
| H2a | Pull ratings back between seasons | held | Half pull: −0.21 points in the exploration; measured carryover puts it at 0.4 (F9) |
| H2b | Scale the pull by roster turnover | failed | Worse than a flat pull |
| H3 | Average win probability instead of the final margin | unclear | Best blend −0.02 points, interval reaching zero |
| H4 | Take luck plays out of the result | failed | +0.00 to +0.09 points (worse) |
| H5, H6 | Conditions and stabilization | open | Part 2, after `stabilization` |
| H7 | Parts: offense, defense, running, passing | unclear | Offense/defense kept (totals need them); running and passing ±0.01 |

## Findings

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | **The full Elo beats the plain one on all three forecasts.** The QB, same-team and lock adjustments cut the margin's range score by 0.031 (−0.045 to −0.017; mean miss 10.06 against 10.15), the total's by 0.013 (QB and same-team only; −0.024 to −0.002; 10.74 against 10.78) and the win chance's log loss by 0.007 (−0.012 to −0.004). Without the lock: 0.022, 0.013 and 0.005 | Scorecards `margin`, `total`, `win`; [`explore/lock_validated.py`](explore/lock_validated.py) | strong | 2016–2024, all games |
| F2 | **Elo is 0.27 points behind the close on margins and 0.30 on totals**, and 0.019 behind on win log loss (0.628 against 0.609; 0.013 to 0.025). The plain Elo is 0.36 and 0.34 behind | Same | strong | 2016–2024 |
| F3 | **Nearly all of the gap beyond 0.25 is the last regular-season week** (before the lock flag; F14 for after). There Elo misses margins by 11.34 against the close's 10.02 (1.32 behind, 144 games); in other weeks 10.02 against 9.78 (0.24); in the playoffs 9.82 against 9.65 (0.17, 109 games). 8 of the 10 biggest margin disagreements are final-week games, most with a team resting starters for the playoffs (KC 2020, LA 2017, BAL 2019, PIT against CLE). The other two are Houston at Cleveland in 2021 week 2 (Watson gone) and New Orleans at Denver in 2020 week 12 (Denver had no eligible QB). That context is football knowledge, not in our data. The close was nearer in 8 of 10. The biggest total disagreements add weather (snow and rain games) and the 2018 Chiefs, whose new offense Elo took weeks to believe. Over all games Elo was nearer in 44.9% | [`explore/sanity.py`](explore/sanity.py) | strong | final week; idea I19 |
| F4 | **Elo adds nothing to the close.** The close plus Elo, refit each week from 2010, ties the close on all three forecasts, and ties a recalibrated close too. The last window gives Elo's margin a weight of 0.16 next to 0.91 for the line | [`explore/no_noise.py`](explore/no_noise.py) | strong | betting products: Elo is a yardstick and a feature, not an edge on its own |
| F5 | **The ranges are honest everywhere we looked:** 79–85% per season (margin), 75–84% (total), 80–82% for close games, mid-size and big favorites, and for home or away favorites. Win chances are calibrated (1.99 points; 2.29 before the lock flag), slightly bold near the top (predicted 84%, happened 80%, 138 games) | Scorecards; `sanity.py` | strong | |
| F6 | **The three forecasts agree:** implied team points (total ± margin) / 2 never go below 9.9. In 47 of 2,476 games the win chance sits on the other side of 50% from the margin, all with margins under 1.8 points, because the two are fit separately | `sanity.py` | strong | products should take the side from one forecast |
| F8 | **The long horizon beats the yardstick at every point in the season.** Mean miss in wins over the rest of the season, Elo against the yardstick (win rate pulled toward .500 by 8 games): week 1, 2.32 against 2.58; weeks 2–5, 2.04 against 2.18; weeks 6–9, 1.59 against 1.66; weeks 10–13, 1.15 against 1.21; weeks 14+, 0.66 against 0.69. Next 3 games: 0.67–0.73 against 0.73–0.78 in every stretch. Ranges hold 79% (rest) and 80% (next 3), every season 72–84%; with 17 games left only 64% (126 rows, too few to judge) | Scorecards `wins_next3`, `wins_rest` | strong | 2016–2024, regular season |
| F7 | **Fixed walk settings match re-chosen ones:** margin 10.09 against the exploration's 10.10 with settings re-chosen every season; the total improved, 10.74 against the exploration's 10.83 | `explore/package_check.py`, decision 0018 | strong | |
| F9 | **A season keeps about 0.42 of itself; Elo's end-of-season rating keeps 0.60–0.68.** Year to year, a team's mean margin repeats with slope 0.42 (correlation 0.41) and its schedule-adjusted margin 0.45. Elo's rating at the end of the regular season predicts next season's adjusted margin with slope 0.65 (0.68 in 2002–2015, 0.60 in 2015–2024), because the walk has already discounted part of the season's luck. So the pull that fits the rating is 0.32–0.40. In the walk's own forecasts 0.4 and 0.5 tie (10.812 against 10.809 on 2002–2015, 10.173 against 10.178 on 2016–2024); 0.4 is the value both agree on, and it's now the setting. Rerun with it, no score moved by more than 0.007 | [`explore/carryover.py`](explore/carryover.py), decision 0021 | strong | the pull; any rating carried across seasons |
| F10 | **The rating credits strength of schedule.** End-of-season rating ≈ 0.70 × mean margin + 0.82 × the opponents' mean rating at game time (736 team-seasons). A win counts against what was expected, so beating good teams is worth more. Two limits: credit uses the opponent's rating when they played (it isn't revised later), and NFL schedules differ little (the opponents' mean rating has an sd of 0.7 points, range −2.3 to +1.8) | `carryover.py` | strong | |
| F11 | **Resting starters goes with the record, not the rating** (discovery only). In the final week the usual QB is on the roster, not listed Out or Doubtful, and plays under half the snaps for 12.5% of teams, against 5.6% in other weeks. By wins going in: 13+ wins 43%, 9–12 13–18%, 5 or fewer 4.5%. Teams at .800+ going into the final week score 5.5 points (± 3.4, 67 team-games) below Elo's rating-only forecast, against 1.4 above it in weeks 10 to the second-last; .700–.799 teams show nothing | `carryover.py` | moderate | I19: a ".800+ going in" flag, or "seed locked" from the standings |
| F12 | **The CEO's spot-check of F3: the final-week gap is rested starters.** The gap to the close, with 90% intervals: other weeks +0.22 (0.12 to 0.31), the second-to-last week +0.54 (0.20 to 0.87), the final week +1.32 (0.65 to 1.98), the playoffs +0.17 (−0.22 to 0.55). In the final week, the 31 games where a usual QB sat healthy hold 76% of the excess (+4.63, 2.26 to 6.84). In the 100 games with no usual QB missing the gap is +0.42 (−0.08 to 0.93), back to normal. Resting teams score 10.4 points below Elo and 5.3 below the close. That last number is inflated, though: rest is measured after the game, and a team can pull its QB because the game is decided. Cold games add a little (+2.33, 17 games). The 10 worst games hold 71% of the excess | [`explore/final_week.py`](explore/final_week.py) | strong | the lock flag (F14); the second-to-last week |
| F13 | **The long horizon's assumptions, checked cheaply:** (1) The 13.5-point curve is right: margins spread 13.6 around the rating-only forecast. (2) Frozen ratings aren't overconfident far ahead, as expected. They're *timid* near-term: the calibration slope is 1.14 for the next game, 1.12 for 1–3 weeks ahead, 1.06 for 4–8, and 0.95 for 9+. The walk under-reacts, and drift cancels that about 9 weeks out. The refit stretches the chances (b1 = 1.09), which is why it beats the raw sum. My expectation (slope below 1 everywhere) failed. (3) The games aren't independent: the actual spread of wins around Elo's expected wins is 1.05× what independent games give with 1–3 left, 1.13× with 4–8, 1.27× with 9–12, and 1.39× with 13–17, because a team's games share its unknown true strength. Ranges built from Σp(1−p) would be about 30% too narrow for a full season. Ours are fitted from misses for each number of games left, so they hold 79% | [`explore/horizon_checks.py`](explore/horizon_checks.py) | strong | futures and season wins: never use independent-game ranges |

| F14 | **The seed-locked flag closes a third of the final-week gap, through the harness.** Going into the final week, a team whose playoff seed no result can change (NFL tiebreakers, decision 0022) gets the flag, and the margin and win forecasts learn its size in the walk. Final-week margin miss 11.34 → 10.90 (−0.43, −0.80 to −0.08; range score −0.14, −0.24 to −0.05), so the gap to the close falls from 1.32 to 0.89 (0.35 to 1.44). Final-week coverage 78.5% → 80.6%. Every other part of the season moves by under 0.01. Overall: margin 10.09 → 10.06 (−0.024, −0.046 to −0.003); win log loss 0.630 → 0.628 (−0.002, −0.005 to −0.000), 0.678 → 0.636 in the final week (the close: 0.569); calibration error 2.29 → 1.99 points. It agrees with the exploration: locked teams score 6.8 points (−9.8 to −3.7) below the rating-only forecast, and a size fitted on 2002–2015 alone cut the gap to 0.98 | [`explore/lock_validated.py`](explore/lock_validated.py), [`explore/lock_flag.py`](explore/lock_flag.py) | strong | final-week margins and win chances; totals not tested |

## The ladder
| Rung | Method | Mean miss, margin (2016–2024) | Takeaway carried forward |
|---|---|---|---|
| 0 | Home field only | 10.98 | A rating must beat 1.2 points behind the close |
| 1 | Chess-style margin Elo, 0.4 pull (`margin_simple`) | 10.15 | The step from 2002–2015; the pull from the carryover study (F9) |
| 3 | Rung 1 + missing QB + same-team share | 10.09 | Rung 2 (H3/H4/H7 add-ons) failed or tied, so it was dropped |
| 4 | Rung 3 + seed-locked flag (`margin`) | 10.06 | Champion proposal. The flag is 0 outside the final week (F14) |

Totals: offense/defense ratings (`total_simple`) 10.78 → plus H1 (`total`) 10.74. Win: a logistic curve on the margin's features, 0.635 → 0.630 → 0.628 with the lock flag.

## Where it misses
The miss lenses are for player-game models; for games, these:

| Lens | Group | Rows | Elo's miss minus the close's |
|---|---|---|---|
| Week | Final regular-season week | 144 | +0.89 (+1.32 before the lock flag, F14) |
| Week | Second-to-last week | 143 | +0.54 |
| Week | Playoffs | 109 | +0.17 |
| Week | Every other week | 2,080 | +0.22 |

The final week became idea I19, now built as the seed-locked flag (F14). What's left of it, and the second-to-last week, are Could be improved 5.

## The case against
- **It's 0.29 behind a number anyone can read for free.** As a forecast on its own, Elo is worse than the close in every way we measure. Its value rests on being a *feature* and a yardstick for later models, and on forecasting earlier in the week than the close. Neither is proven yet. Downstream projects have to show it.
- **H1's gain is small and partly overlapping.** 0.021 range score is 0.06 points of miss. It's significant over 193 weeks, but a later model with real injury and depth-chart features may absorb it entirely.
- **The no-noise target was proposed by Claude after the brief** (the CEO approved it on 2026-11-07). "Neutral against the close" is the expected answer, so the test can't show much either way.
- **For the betting optimizer, being near the close is also a weakness.** A feature that tracks the close adds little a betting model doesn't already have (F4). Elo's value there is as a strength summary for other experts, and for moments with no line yet.
- **The 0.4 pull leans partly on the reported seasons.** The exploration chose 0.5 on 2002–2015 alone; on those seasons the carryover slope says 0.32 and the forecast test 0.5. 0.4 sits between, and the 2016–2024 forecasts were in view when it was picked. At most 0.005 points either way.
- **The exploration and the validation use the same seasons.** Rung 3 was picked by looking at 2016–2024, the same seasons it's validated on. The fixed settings came from 2002–2015, but which hunches made it in did not. The vault (2025) is the honest check, still closed.
- **"Strong" is close.** 0.24 outside the final week is under 0.25, but that split was found after looking at the misses.

- **The lock flag rests on 67 locked team-games (2002–2024), and its tiebreaker code is long.** The seeds match every real playoff field, but the locks themselves can't be checked against reality as directly: a wrong lock would be a quiet error. The final-week gain is 0.43 with an interval reaching −0.08, and it was found after looking at the final week (F3).

## Pitfalls
- **The lock flag first failed leakage check 3.** Three ways the future leaked into a past lock: locks were computed at mid-season moments (when every result is "to come"), from schedule rows not yet listed (scrambled playoff rows turned into fake final-week games), and an outcome no tiebreaker could settle counted as "locked". Now: final-week moments only, rows listed by the moment, and an unresolved outcome means "could differ". Each has a test.
- **The long horizon read schedule rows from the future in the bulk path.** Playoff games aren't on the schedule until their week; the bulk view holds them anyway, and when check 3 scrambled their labels they turned into fake regular-season games inside teams' windows. Live forecasts were never affected (a moment's view hides them), but the code now uses only games on the schedule by the moment.
- **Check 8 assumed nothing in a step is known before its later runs.** Thursday's result is known by the Saturday run and fairly moves future opponents' ratings. The check now leaves such results alone (decision 0020).
- **The 3-game yardstick fails the signal test (0 of 20)**: it has nothing to fit, so shuffled outcomes only move its ranges. It's a yardstick, not an expert.
- **Nondeterminism from joins:** polars joins can reorder rows. A rating walk must sort by a fixed order (when the result became known, then kickoff, then game id), and QB ties need a tiebreak. Without both, runs differed in the third decimal.
- **The synthetic test league** always paired the same teams with the stronger one at home, so home field absorbed the strengths. Test leagues for ratings need mixed home teams.
- **A null injury status** read as "not available" made 93% of QBs look missing in the exploration. `fill_null(False)` on the out flag.

## Not looked at
- Weather, travel and rest days, coaching changes mid-season. Rested starters had a first look only (F11).
- Earlier forecast moments: is Elo nearer the *opening* line than the close? That's where a rating could matter for betting.
- H5 and H6 (part 2).

## Could be improved
0. Publish the ratings in the live weekly run too: only the walk-forward history carries them so far (decision 0021).
1. Final-week rest beyond seed locks (F14 leaves 0.89 of the gap): teams that clinched a playoff spot but not their seed, coaches who rest anyway, and resting on totals (decision 0022, call 6).
2. Credit results for who played (a win without the QB counts for more), untested.
3. The long horizon with ratings that move along the way (simulating the season game by game) and known future absences.
4. A stretch that depends on how far ahead the game is (F13): stretch near games, not far ones.
5. A lock flag for the second-to-last week too (F12: +0.54 gap there), which means trying every outcome of two weeks.

## Don't redo
- Scaling the between-season pull by roster turnover (H2b), luck-play adjustments (H4), and running/passing ratings (H7): tried, no gain.
- Re-tuning the walk's settings each season: no better than fixed (F7).

## Interface card

| | |
|---|---|
| **Inputs** | `game`: schedule, result · `player_game`: roster, snaps, injury (gateway only) |
| **Outputs** | `outputs/elo/<variant>/<run>/history.parquet`: per game `home_margin`, `total_points` (mean, q10, q50, q90), `home_win` (mean); per team-game `wins_next3`, `wins_rest` (mean, q10, q50, q90); all with `train_end`. **The margin's history also carries the ratings** (decision 0021), per game at the forecast's moment: `hfa`, `home_rating`, `away_rating` (points against an average team), `home_offense`, `home_defense`, `away_offense`, `away_defense` (points against the league average), `h_qb`, `a_qb` (1 = usual QB out), `h_share`, `a_share` (share of usual snaps available), `h_lock`, `a_lock` (1 = seed locked going into the final week, decision 0022). Live runs don't carry them yet |
| **Level of detail** | game |
| **Interval** | every game, from week 1 (ratings carry over from last season, pulled 40% toward average) |
| **Cadence** | in_season |
| **Known at** | the Saturday run (Thursday noon for Thursday games, Tuesday for Wednesday games) |
| **How to use it** | As a feature and a yardstick. Not as a bet against the close on its own (F4). Final-week forecasts are still the weakest, 0.89 behind the close after the lock flag (F14) |
| **Feeds** | sides, totals and win products; the prediction ledger; team efficiency, game script, fantasy game environments |
