# Results: Team Elo (`elo`)

> **Draft, 2026-11-07: validating.** The three game forecasts are validated. Still to do before done: the long-horizon forecasts (wins over the next 3 games and the rest of the season), the CEO's review of the lists below, the CEO's spot-check, and the CEO's approval of the no-noise target. KNOWLEDGE and GLOSSARY entries wait for done.

**Date:** 2026-11-07 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `elo` · **Champion:** not registered yet (proposed: `margin`, `total`, `win`)

## In short
A team rating in points, walked over every result since 1999, plus a missing-QB and same-team adjustment (the CEO's H1), forecasts the margin within 0.29 points of the closing line and the total within 0.30. That's inside the brief's 0.5 bar, though not the 0.25 "strong" mark. Outside the last regular-season week it is 0.24 behind, and the gap is almost all teams resting starters, which Elo can't see. Every check passes, and the full rating beats the plain chess-style Elo on all three forecasts. It adds nothing to the close: blended in, it changes nothing, as expected.

**Scorecards** (MLflow runs, in `data/outputs/elo/<variant>/<run>/scorecard.html`): `margin` 79753c39, `total` 9faeb3f7, `win` 3af8cd13; yardsticks `margin_simple` c517e2ac, `total_simple` a4db9b97, `win_simple` 33d998fe · **Vault:** closed · **Versions tried:** 1 each through the harness (the exploration tried 26 findings' worth of rungs and hunches)

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal | **Pass:** every variant beats 20 of 20 shuffled refits (margin 3.251 range score against shuffled 3.435–3.582) |
| No noise | **Pass, neutral:** the close with Elo blended in is unchanged: margin +0.001 (−0.003 to +0.004), total −0.000 (−0.005 to +0.004), win +0.000 (−0.001 to +0.001), 193 weeks (F4). *The target is proposed; the CEO approves it in the brief.* |
| Beats the simple Elo (the brief's main test) | **Pass, all three:** margin −0.021 range score (−0.033 to −0.010), total −0.013 (−0.024 to −0.002), win −0.005 log loss (−0.008 to −0.002) (F1) |
| Near the close (bar 0.5, strong 0.25) | **Pass, not strong:** margin 10.09 vs 9.80 (0.29), total 10.74 vs 10.44 (0.30) (F2) |
| Calibration | **Pass:** win chances: error 2.53 points (bar ≤ 3), slope 0.94 (bar 0.9–1.1) |
| Range coverage | **Pass:** margin 81.1%, total 80.7% inside q10–q90; every season 75–85%; favorites and close games 80–82% (F5) |
| Leakage | **Pass:** all 9 blocking checks on every variant; features identical at 25 cutoffs (104,523 rows) |
| Football sanity | Automatic rules pass. **CEO review pending:** the top and bottom 20 are in the scorecards, the 10 biggest disagreements with the close below (F3) |
| CEO spot-check | pending |

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
| F3 | **Nearly all of the gap beyond 0.25 is the last regular-season week.** There Elo misses margins by 11.40 against the close's 10.02 (1.38 behind, 144 games); in other weeks 10.02 against 9.78 (0.24); in the playoffs 9.81 against 9.65 (0.16, 109 games). 8 of the 10 biggest margin disagreements are final-week games where a team rested starters (KC 2020, LA 2017, BAL 2019, PIT against CLE). The close was nearer in 8 of 10. Over all games Elo was nearer in 45.7% | [`explore/sanity.py`](explore/sanity.py) | strong | final week; idea I19 |
| F4 | **Elo adds nothing to the close.** The close plus Elo, refit each week from 2010, ties the close on all three forecasts, and ties a recalibrated close too. The last window gives Elo's margin a weight of 0.12 next to 0.94 for the line | [`explore/no_noise.py`](explore/no_noise.py) | strong | betting products: Elo is a yardstick and a feature, not an edge on its own |
| F5 | **The ranges are honest everywhere we looked:** 79–85% per season (margin), 75–84% (total), 80–82% for close games, mid-size and big favorites, and for home or away favorites. Win chances are calibrated (2.53 points), slightly timid at the extremes (predicted 92%, happened 87%, 30 games) | Scorecards; `sanity.py` | strong | |
| F6 | **The three forecasts agree:** implied team points (total ± margin) / 2 never go below 9.8. In 32 of 2,476 games the win chance sits on the other side of 50% from the margin, all with margins under 1.5 points, because the two are fit separately | `sanity.py` | strong | products should take the side from one forecast |
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
- **Nondeterminism from joins:** polars joins can reorder rows. A rating walk must sort by a fixed order (when the result became known, then kickoff, then game id), and QB ties need a tiebreak. Without both, runs differed in the third decimal.
- **The synthetic test league** always paired the same teams with the stronger one at home, so home field absorbed the strengths. Test leagues for ratings need mixed home teams.
- **A null injury status** read as "not available" made 93% of QBs look missing in the exploration. `fill_null(False)` on the out flag.

## Not looked at
- Rested starters in the final week (I19), weather, travel and rest days, coaching changes mid-season.
- Earlier forecast moments: is Elo nearer the *opening* line than the close? That's where a rating could matter for betting.
- H5 and H6 (part 2).

## Could be improved
1. Final-week rest (I19): a playoff-locked flag would cut the 1.38 gap.
2. Credit results for who played (a win without the QB counts for more), untested.
3. The long horizon (goal 1, next).

## Don't redo
- Scaling the between-season pull by roster turnover (H2b), luck-play adjustments (H4), and running/passing ratings (H7): tried, no gain.
- Re-tuning the walk's settings each season: no better than fixed (F7).

## Interface card

| | |
|---|---|
| **Inputs** | `game`: schedule, result · `player_game`: roster, snaps, injury (gateway only) |
| **Outputs** | `outputs/elo/<variant>/<run>/history.parquet`: `home_margin`, `total_points` (mean, q10, q50, q90), `home_win` (mean), with `train_end` |
| **Level of detail** | game |
| **Interval** | every game, from week 1 (ratings carry over from last season, half pulled) |
| **Cadence** | in_season |
| **Known at** | the Saturday run (Thursday noon for Thursday games, Tuesday for Wednesday games) |
| **How to use it** | As a feature and a yardstick. Not as a bet against the close on its own (F4). Discount final-week forecasts (F3) |
| **Feeds** | sides, totals and win products; the prediction ledger; team efficiency, game script, fantasy game environments |
