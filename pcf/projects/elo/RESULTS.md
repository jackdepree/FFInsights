# Results: Team Elo (`elo`)

> **Draft, 2026-11-07: validating.** The three game forecasts are validated. The long horizon is validated too (F8). Still to do before done: the CEO's review of the lists below, the CEO's spot-check, and the CEO's approval of the no-noise target. KNOWLEDGE and GLOSSARY entries wait for done.

**Date:** 2026-11-07 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `elo` · **Champion:** not registered yet (proposed: `margin`, `total`, `win`)

## In short
A team rating in points, walked over every result since 1999, plus a missing-QB and same-team adjustment (the CEO's H1), forecasts the margin within 0.29 points of the closing line and the total within 0.30. That's inside the brief's 0.5 bar, though not the 0.25 "strong" mark. Outside the last regular-season week it is 0.24 behind, and the gap is almost all teams resting starters, which Elo can't see. Every check passes, and the full rating beats the plain chess-style Elo on all three forecasts. It adds nothing to the close: blended in, it changes nothing, as expected.

**Scorecards** (MLflow runs, in `data/outputs/elo/<variant>/<run>/scorecard.html`): `margin` 79753c39, `total` 9faeb3f7, `win` 3af8cd13; yardsticks `margin_simple` c517e2ac, `total_simple` a4db9b97, `win_simple` 33d998fe; long horizon `wins_next3` 5cd5eeeb, `wins_rest` de2dc738, their yardsticks acb14f05 and f44e6c1f · **Vault:** closed · **Versions tried:** 1 each through the harness (the exploration tried 26 findings' worth of rungs and hunches)

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal | **Pass:** every variant beats 20 of 20 shuffled refits (margin 3.251 range score against shuffled 3.435–3.582) |
| No noise | **Pass, neutral:** the close with Elo blended in is unchanged: margin +0.001 (−0.003 to +0.004), total −0.000 (−0.005 to +0.004), win +0.000 (−0.001 to +0.001), 193 weeks (F4). *The target is proposed; the CEO approves it in the brief.* |
| Long horizon beats its yardstick | **Pass, both:** wins over the next 3 games, range score −0.011 (−0.013 to −0.009), mean miss 0.72 wins against 0.75; rest of season −0.028 (−0.033 to −0.022), 1.39 against 1.49 (F8) |
| Beats the simple Elo (the brief's main test) | **Pass, all three:** margin −0.021 range score (−0.033 to −0.010), total −0.013 (−0.024 to −0.002), win −0.005 log loss (−0.008 to −0.002) (F1) |
| Near the close (bar 0.5, strong 0.25) | **Pass, not strong:** margin 10.09 vs 9.80 (0.29), total 10.74 vs 10.44 (0.30) (F2) |
| Calibration | **Pass:** win chances: error 2.53 points (bar ≤ 3), slope 0.94 (bar 0.9–1.1) |
| Range coverage | **Pass:** margin 81.1%, total 80.7% inside q10–q90; every season 75–85%; favorites and close games 80–82% (F5) |
| Leakage | **Pass:** all 9 blocking checks on every variant; features identical at 25 cutoffs. The long horizon first failed two checks; both are fixed (Pitfalls) |
| Football sanity | Automatic rules pass. **CEO review pending:** the top and bottom 20 are in the scorecards, the 10 biggest disagreements with the close below (F3) |
| CEO spot-check | pending |

## How it works, in plain terms
**Inputs:** every final score since 1999 (in the order they became known), the schedule (who's at home, neutral sites), each week's roster, the last 4 games' snap shares, and the injury report known by the run. Nothing else: no stats, no betting lines.

**The rating walk** (no fitting, the same every run):
1. Every team has a **rating in points**: how much better than an average team on a neutral field. All start at 0 in 1999.
2. Before a game, the **raw forecast** is the rating gap plus home field (the mean home margin of the last 3 seasons: 2.3 points in 2024).
3. After it, **both teams move by 6% of the miss**: the winner of the surprise goes up, the other goes down by the same amount.
4. Each new season, every rating is **pulled halfway back to 0**: rosters change, so last year only half counts.
5. The same walk runs on **points scored and allowed** (offense and defense ratings, 5% step, one-third pull), which gives the total.

**The fitted layer** (refit every week on earlier games only) turns those numbers into the forecasts. It weighs the rating gap, home field, a missing usual QB and the share of usual snaps available, and adds ranges from past misses.

**Worked example, Lions at Texans, 2024 week 10** (Sunday night, forecast Saturday noon):

| Step | Number |
|---|---|
| Ratings at the end of 2023 | DET +3.3, HOU −0.2 |
| After the half pull, then 8 games of 2024 | DET +7.2 (1st in the league), HOU +0.05 |
| Raw forecast, Texans' margin | −7.1 gap + 2.3 home field = **−4.8** |
| Fitted forecast | 1.09 × −7.1 + 0.80 × 2.3 + 14.2 × (−0.04 same-team gap; Houston had 86% of its usual snaps, Detroit 90%) = **−6.4**, range −22 to +11 |
| The close | −4.5 |
| Result | Lions won 26–23: Texans' margin **−3** |
| Update | miss = −3 − (−4.8) = +1.8; × 0.06 = 0.11. DET 7.18 → 7.07, HOU 0.05 → 0.15 |
| Total | 13.6 + 0.70 × 49.4 (offense/defense total) + 4.6 × 0.23 (share of usual snaps missing, both teams) = **49.1**; close 49.0; actual 49 |
| Win chance (Texans) | 30%; the close (no-vig moneyline) 33% |

## Hunch verdicts
From the exploration (EXPLORATION F5–F23), already in [`HUNCHES.md`](../HUNCHES.md). Nothing in validation changed them.

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H1 | Who is actually playing matters | held | A missing usual QB and the same-team share together cut the margin miss by about 0.06 points; through the harness, rung 3 beats rung 1 by 0.021 range score (F1) |
| H2a | Pull ratings back between seasons | held | Half pull: −0.21 points |
| H2b | Scale the pull by roster turnover | failed | Worse than a flat pull |
| H3 | Average win probability instead of the final margin | unclear | Best blend −0.02 points, interval reaching zero |
| H4 | Take luck plays out of the result | failed | +0.00 to +0.09 points (worse) |
| H5, H6 | Conditions and stabilization | open | Part 2, after `stabilization` |
| H7 | Parts: offense, defense, running, passing | unclear | Offense/defense kept (totals need them); running and passing ±0.01 |

## Findings

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | **The full Elo beats the plain one on all three forecasts.** The QB and same-team adjustments cut the margin's range score by 0.021 (−0.033 to −0.010; mean miss 10.09 against 10.15), the total's by 0.013 (−0.024 to −0.002; 10.74 against 10.78) and the win chance's log loss by 0.005 (−0.008 to −0.002) | Scorecards `margin`, `total`, `win` | strong | 2016–2024, all games |
| F2 | **Elo is 0.29 points behind the close on margins and 0.30 on totals**, and 0.022 behind on win log loss (0.631 against 0.609; 0.016 to 0.029). The plain Elo is 0.35 and 0.34 behind | Same | strong | 2016–2024 |
| F3 | **Nearly all of the gap beyond 0.25 is the last regular-season week.** There Elo misses margins by 11.40 against the close's 10.02 (1.38 behind, 144 games); in other weeks 10.02 against 9.78 (0.24); in the playoffs 9.81 against 9.65 (0.16, 109 games). 9 of the 10 biggest margin disagreements are final-week games, most with a team resting starters for the playoffs (KC 2020, LA 2017, BAL 2019, PIT against CLE; that context is football knowledge, not in our data). The close was nearer in 8 of 10. The biggest total disagreements add weather (snow and rain games) and the 2018 Chiefs, whose new offense Elo took weeks to believe. Over all games Elo was nearer in 45.7% | [`explore/sanity.py`](explore/sanity.py) | strong | final week; idea I19 |
| F4 | **Elo adds nothing to the close.** The close plus Elo, refit each week from 2010, ties the close on all three forecasts, and ties a recalibrated close too. The last window gives Elo's margin a weight of 0.12 next to 0.94 for the line | [`explore/no_noise.py`](explore/no_noise.py) | strong | betting products: Elo is a yardstick and a feature, not an edge on its own |
| F5 | **The ranges are honest everywhere we looked:** 79–85% per season (margin), 75–84% (total), 80–82% for close games, mid-size and big favorites, and for home or away favorites. Win chances are calibrated (2.53 points), slightly timid at the extremes (predicted 92%, happened 87%, 30 games) | Scorecards; `sanity.py` | strong | |
| F6 | **The three forecasts agree:** implied team points (total ± margin) / 2 never go below 9.8. In 32 of 2,476 games the win chance sits on the other side of 50% from the margin, all with margins under 1.5 points, because the two are fit separately | `sanity.py` | strong | products should take the side from one forecast |
| F8 | **The long horizon beats the yardstick at every point in the season.** Mean miss in wins over the rest of the season, Elo against the yardstick (win rate pulled toward .500 by 8 games): week 1, 2.32 against 2.58; weeks 2–5, 2.04 against 2.18; weeks 6–9, 1.58 against 1.66; weeks 10–13, 1.15 against 1.21; weeks 14+, 0.66 against 0.69. Next 3 games: 0.68–0.73 against 0.73–0.78 in every stretch. Ranges hold 79% (rest) and 79% (next 3), every season 72–85%; with 17 games left only 64% (126 rows, too few to judge) | Scorecards `wins_next3`, `wins_rest` | strong | 2016–2024, regular season |
| F7 | **Fixed walk settings match re-chosen ones:** margin 10.09 against the exploration's 10.10 with settings re-chosen every season; the total improved, 10.74 against the exploration's 10.83 | `explore/package_check.py`, decision 0018 | strong | |

## The ladder
| Rung | Method | Mean miss, margin (2016–2024) | Takeaway carried forward |
|---|---|---|---|
| 0 | Home field only | 10.98 | A rating must beat 1.2 points behind the close |
| 1 | Chess-style margin Elo, half pull (`margin_simple`) | 10.15 | The step and pull, fixed from 2002–2015 |
| 3 | Rung 1 + missing QB + same-team share (`margin`) | 10.09 | Champion proposal. Rung 2 (H3/H4/H7 add-ons) failed or tied, so it was dropped |

Totals: offense/defense ratings (`total_simple`) 10.78 → plus H1 (`total`) 10.74. Win: a logistic curve on the margin's features, 0.636 → 0.631.

## Where it misses
The miss lenses are for player-game models; for games, these:

| Lens | Group | Rows | Elo's miss minus the close's |
|---|---|---|---|
| Week | Final regular-season week | 144 | +1.38 |
| Week | Playoffs | 109 | +0.16 |
| Week | Every other week | 2,223 | +0.24 |

The final week becomes idea I19.

## The case against
- **It's 0.29 behind a number anyone can read for free.** As a forecast on its own, Elo is worse than the close in every way we measure. Its value rests on being a *feature* and a yardstick for later models, and on forecasting earlier in the week than the close. Neither is proven yet. Downstream projects have to show it.
- **H1's gain is small and partly overlapping.** 0.021 range score is 0.06 points of miss. It's significant over 193 weeks, but a later model with real injury and depth-chart features may absorb it entirely.
- **The no-noise target was chosen by Claude after the brief.** VALIDATION says the brief names it with the CEO's approval. "Neutral against the close" is the expected answer, so the test can't show much either way.
- **The exploration and the validation use the same seasons.** Rung 3 was picked by looking at 2016–2024, the same seasons it's validated on. The fixed settings came from 2002–2015, but which hunches made it in did not. The vault (2025) is the honest check, still closed.
- **"Strong" is close.** 0.24 outside the final week is under 0.25, but that split was found after looking at the misses.

## Pitfalls
- **The long horizon read schedule rows from the future in the bulk path.** Playoff games aren't on the schedule until their week; the bulk view holds them anyway, and when check 3 scrambled their labels they turned into fake regular-season games inside teams' windows. Live forecasts were never affected (a moment's view hides them), but the code now uses only games on the schedule by the moment.
- **Check 8 assumed nothing in a step is known before its later runs.** Thursday's result is known by the Saturday run and fairly moves future opponents' ratings. The check now leaves such results alone (decision 0020).
- **The 3-game yardstick fails the signal test (0 of 20)**: it has nothing to fit, so shuffled outcomes only move its ranges. It's a yardstick, not an expert.
- **Nondeterminism from joins:** polars joins can reorder rows. A rating walk must sort by a fixed order (when the result became known, then kickoff, then game id), and QB ties need a tiebreak. Without both, runs differed in the third decimal.
- **The synthetic test league** always paired the same teams with the stronger one at home, so home field absorbed the strengths. Test leagues for ratings need mixed home teams.
- **A null injury status** read as "not available" made 93% of QBs look missing in the exploration. `fill_null(False)` on the out flag.

## Not looked at
- Rested starters in the final week (I19), weather, travel and rest days, coaching changes mid-season.
- Earlier forecast moments: is Elo nearer the *opening* line than the close? That's where a rating could matter for betting.
- H5 and H6 (part 2).

## Could be improved
0. Save the ratings themselves (overall, offense, defense, QB missing, same-team share per team-game) as an output, since downstream models will want them as features.
1. Final-week rest (I19): a playoff-locked flag would cut the 1.38 gap.
2. Credit results for who played (a win without the QB counts for more), untested.
3. The long horizon with ratings that move along the way (simulating the season game by game) and known future absences.

## Don't redo
- Scaling the between-season pull by roster turnover (H2b), luck-play adjustments (H4), and running/passing ratings (H7): tried, no gain.
- Re-tuning the walk's settings each season: no better than fixed (F7).

## Interface card

| | |
|---|---|
| **Inputs** | `game`: schedule, result · `player_game`: roster, snaps, injury (gateway only) |
| **Outputs** | `outputs/elo/<variant>/<run>/history.parquet`: per game `home_margin`, `total_points` (mean, q10, q50, q90), `home_win` (mean); per team-game `wins_next3`, `wins_rest` (mean, q10, q50, q90); all with `train_end`. The ratings themselves aren't saved yet |
| **Level of detail** | game |
| **Interval** | every game, from week 1 (ratings carry over from last season, half pulled) |
| **Cadence** | in_season |
| **Known at** | the Saturday run (Thursday noon for Thursday games, Tuesday for Wednesday games) |
| **How to use it** | As a feature and a yardstick. Not as a bet against the close on its own (F4). Discount final-week forecasts (F3) |
| **Feeds** | sides, totals and win products; the prediction ledger; team efficiency, game script, fantasy game environments |
