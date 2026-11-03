# Results: Baselines (`baselines`)

**Date:** 2026-11-02 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `baselines` (one attempt per variant) · **Champion:** none registered (yardsticks, not models we ship)

## In short
Every product now has its yardsticks, each validated through the harness with every leakage check passing. **FantasyPros' ECR is the bar for weekly projections:** on Sunday and Monday games (2022–2024, Saturday run), it beats every baseline PCF can build from box scores, the lasso included (F9). The lasso beats the plain averages (F10). The closing line is sharp and calibrated (F13). Ranges per position fix the toy's QB problem (F12).

**Scorecards:** `outputs/baselines/<variant>/<run_id>/scorecard.html` (also in MLflow) · **Vault:** not opened · **Versions tried:** 1 per variant (ECR 2: rerun for a corrected scorecard)

| Variant | Run | Seasons | Main score | Readable | Coverage q10–q90 / calibration | Signal |
|---|---|---|---|---|---|---|
| `rolling4` (last 4 games) | Tue | 2016–2024 | pinball 1.608 | MAE 4.79 | 80.7% (every position 79–81%) | 100/100 |
| `season` (so far; week 1: last season) | Tue | 2016–2024 | 1.586 | 4.72 | 80.8% | 100/100 |
| `last_season` | Tue | 2016–2024 | 1.674 | 5.09 | 80.8% (no rookies: 43,254 rows) | 100/100 |
| `lasso` | Tue | 2016–2024 | 1.492 | 4.50 | 80.7% | 20/20 |
| `ecr` (benchmark) | Sat | 2022–2024 | 1.382 | 4.24 | 80.0% (every position and rank band 79–81%) | n/a |
| `market_margin` (benchmark) | Kickoff | 2016–2024 | 3.176 | 9.80 | 82.1% | n/a |
| `market_total` (benchmark) | Kickoff | 2016–2024 | 3.297 | 10.44 | 81.8% | n/a |
| `market_win` (benchmark) | Kickoff | 2016–2024 | log loss 0.609 | Brier 0.211 | error 1.66 points, slope 1.08 | n/a |

The brief's tests:

| Test | Result |
|---|---|
| Every baseline passes all blocking leakage checks | Pass: 8 of 8, at 25 cutoffs each |
| ECR never ranks a game that kicked off before its snapshot | Pass: offline (a planted Thursday game) and on 2021–2024 (every row known before kickoff, within 4 days) |
| Walk-forward, ECR-as-points beats the 4-game average | Pass, and by more than the exploration suggested: −0.186 pinball (F9) |
| Averages' coverage 75–85% overall, 70–90% per position | Pass: 79–81% at every position (F12) |
| The market's win probabilities calibrated within 3 points | Pass over 2016–2024: 1.66 points. Not on one season alone (F13) |

## Terms
As in the brief, now in `docs/GLOSSARY.md`: **benchmark**, **rank-to-points curve**, **kickoff moment**, and one addition, **variant** (one of several models under one project id, e.g. `baselines/ecr`).

## Findings
Exploration findings F1–F8 are in [EXPLORATION.md](EXPLORATION.md). These continue from them.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F9 | **ECR beats every baseline PCF can build from box scores.** Sunday and Monday games, 2022–2024, all at the Saturday run, paired on the same player-games: ECR pinball 1.382 against the lasso's 1.446 (−0.072, 90% interval −0.082 to −0.061), the season average's 1.532 (−0.162) and the 4-game average's 1.561 (−0.186). **The weekly fantasy product's bar is ECR.** | ECR scorecard | strong | QB, RB, WR, TE; weeks 2–17 |
| F10 | **The lasso beats the averages**, 2016–2024: pinball 1.492 against 1.608 for the 4-game average (−0.116, −0.121 to −0.111) and 1.586 for the season average (−0.094, −0.106 to −0.081). Box-score history carries more than one average. | lasso scorecard | strong | every position |
| F11 | **Season so far beats the last 4 games** (1.586 vs 1.608 pinball), and last season's average is the weakest (1.674, and it has nothing for rookies). Stable skill beats recent form as a single number. | the averages' scorecards | strong | weekly fantasy points |
| F12 | **Ranges per position cover honestly.** Every average, the lasso and ECR hold 79–81% of results inside q10–q90 at every position and season (bar 70–90%). The toy's single spread had QBs at 69% (validation-harness#F15). | scorecards | strong | every amount model |
| F13 | **The closing line is sharp and calibrated.** Margins miss by 9.8 points on average, totals by 10.4, with ranges covering 82%. No-vig win probabilities have log loss 0.609 over 2,466 games, calibration error 1.66 points and slope 1.08. **One season of games is too few to judge calibration:** 2024 alone (285 games) shows 6.1 points, from noise. | market scorecards; the 2024 trial run | strong | sides, totals, win probability |
| F14 | **Four harness gaps showed up and are fixed.** The test-label check broke on probability models (no q10–q90) and on weeks with no predictions (ECR has no week 18). A scorecard compared a model with baselines run at a different moment. "Versions tried" counted every variant of a project together. | tests in `tests/baselines/`, `tests/core/test_tracking.py` | strong | every later model |
| F15 | **Each validation fits the time goal.** With 100 shuffles an average takes about 10 minutes; the lasso with 20 takes 11.5; ECR, with its three baselines rerun at Saturday, 7; each market benchmark 20 seconds. | run log | strong | every model |

## The ladder
These are rung 0 for every product, so there's no ladder of their own. The lasso is the first rung-1 model in PCF: it beat the rung-0 averages (F10). Its takeaway for the next rung: averages of several box-score stats beat one average of points.

## Pitfalls
- **A part comes with its table's spine.** `load("player_game", parts=["ecr"])` returns every rostered player, with nulls where there's no rank. Filter on `ecr_known_at`.
- **A Friday snapshot still lists Thursday's players** (F2). The part drops them, so no model has to remember.
- **The synthetic league can't test ECR's skill:** with 6 teams a rank is one of 4, too coarse. ECR's value is shown on real data only.
- **Comparing at different moments flatters someone.** Tuesday averages can't see Monday night; Saturday ECR can. The harness now reruns baselines at the model's run (decision 0012).

## Not looked at
- **Props, anytime TD, rest-of-season, dynasty and futures baselines** (D1): they come with their products. Props and TD need our collected odds as a table.
- **The market at our run times** (the line we could actually bet on Saturday): it needs our own odds snapshots as a table.
- **ECR in half-PPR and standard:** the archive's weekly pages are PPR (and QB).
- **The vault (2025).**

## Could be improved
1. **An odds table** from the collected ESPN and Odds API data, for props baselines and a Saturday-run market benchmark.
2. **ECR's expert spread (`ecr_sd`)** to widen ranges where experts disagree. It's in the part, unused.
3. **A lasso with ECR as a feature,** as a product's first rung (not as a baseline: D6).
4. **Parallel shuffles** to cut the averages' 10 minutes.

## Don't redo
- Don't judge a weekly projection against the rolling average alone: ECR is the real bar (F9).
- Don't use the week's ECR for Thursday games (F2), or the closing line before kickoff (F6).
- Don't judge calibration on one season of games (F13).

## Interface card
Also in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `player_game` stats and the new `ecr` part; `game` pregame lines and results |
| **Outputs** | `pcf.baselines`: `RollingAverage`, `SeasonAverage`, `LastSeason`, `Lasso`, `Ecr`, `MarketMargin`, `MarketTotal`, `MarketWin`, `VARIANTS`, `scored(cls, scoring)`. Walk-forward histories and scorecards in `outputs/baselines/<variant>/<run_id>/` |
| **Level of detail** | player-game (fantasy points); game (the market) |
| **Interval** | weekly; fantasy 2016–2024 (ECR 2022–2024, weeks 2–17, Sunday and Monday games) |
| **Cadence** | in_season |
| **Known at** | the averages and lasso at the Tuesday run (or the product's run); ECR at the Saturday run; the market at kickoff |
| **How to use it** | A product lists the baselines it must beat in `baselines()`, e.g. `[Ecr, Lasso, RollingAverage]`; the harness reruns them at the product's run (benchmarks at their own) and the scorecard shows "beats" for each. Another scoring: `scored(Lasso, "half")`. Never use a benchmark as a feature before it's known. |
| **Feeds** | every product's scorecard; the weekly fantasy product must beat `ecr` |

## Open questions for the CEO
1. **To ship, must the weekly fantasy product clearly beat ECR, or is matching it enough?** The charter says "at least as accurate as ECR". VALIDATION.md's "beats" means the whole 90% interval is better. Matching ECR (the interval includes zero) would pass the charter's wording but not "beats". Recommended: matching ECR is enough to ship, since it's the best free yardstick there is; beating it is the goal.
