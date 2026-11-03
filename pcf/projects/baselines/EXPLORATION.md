# Exploration: Baselines (`baselines`)

> A first look at the candidate yardsticks in VALIDATION.md §6: FantasyPros ECR, rolling averages, last season's average and the betting market's closing lines. Is each one there, when is it known, and how good is it?
> Run on 2026-11-02 with [`explore/profile_baselines.py`](explore/profile_baselines.py) on the built tables and the raw ECR archive. Results are measured on 2021–2024. The vault (2025) wasn't read.

**Verdict: GO.** Every candidate exists and has signal. **ECR is the real bar:** it ranks players clearly better than any average (F3) and predicts points slightly better (F4). The catch is timing. ECR is a Friday snapshot, so it can honestly rank only games after Friday: the Saturday run's Sunday and Monday games (F2). Closing lines are known only at kickoff (F6). Both are fine as yardsticks to compare against, but neither can be a feature at an earlier run.

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **The weekly ECR archive is one Friday snapshot a week from 2021, and covers weeks 2–17.** 2020 snapshots fall on mixed weekdays. Week 1 is missing in 2022 and 2023, weeks 1–3 in 2024, and week 18 and the playoffs every year. A snapshot is known at the start of the next day, Eastern (DATA_SOURCES.md). 99.6% of rows match a `gsis_id` (100% of each position's top 24). | strong |
| F2 | **The week's ECR can't rank Thursday games.** The Friday snapshot comes after Thursday's kickoff, yet still lists those players: Lamar Jackson and Joe Burrow are ranked on 2024-11-08, the day after their game. Used for that game, it's a leak. Only 0–16% of Thursday games and 33–70% of Saturday games have a snapshot from before kickoff; 73–91% of Sunday games do. | strong |
| F3 | **ECR ranks players better than every average.** Mean rank correlation with PPR points inside each position-week, 2021–2024: QB 0.46 (4-game average 0.37, season so far 0.37), RB 0.71 (0.65, 0.66), WR 0.66 (0.60, 0.61), TE 0.61 (0.53, 0.53). Same rows for every method. | strong |
| F4 | **As points, ECR wins narrowly.** Turned into points by a rank-to-points curve fit on 2021–2022, its mean absolute error on 2023–2024 is QB 6.04 (4-game average 6.36), RB 4.49 (4.55; season so far 4.47), WR 4.49 (4.70), TE 3.56 (3.81). | strong |
| F5 | **Last season's per-game average is the weakest yardstick:** rank correlation 0.32–0.56, below the in-season averages at every position. | strong |
| F6 | **Closing lines are sharp:** 2016–2024 spreads miss the margin by 9.8 points on average, totals by 10.4. Favorites win 66.5% of games. Moneylines exist for 99.96% of games. They're known only at kickoff (validation-harness#F3). | strong |
| F7 | **ECR is a rank, not a number of points or a range.** To be scored like a projection (pinball, VALIDATION.md §3), it needs a rank-to-points curve and a spread, fit on training weeks. FantasyPros also gives the experts' disagreement (`sd`, on every row), which could widen ranges when experts disagree. | strong |
| F8 | **The contract has two gaps for baselines.** A product needs several baselines on the same quantity, and some are known only at kickoff (closing lines). The harness already reruns a product's baselines on its own moments (`baselines()`, the toy's `LastFour`), but no run happens at kickoff, and each baseline is written for one quantity. | strong |

## What this means for the brief

- **ECR is the headline yardstick for weekly fantasy points** (F3, F4), matching the charter's success test ("at least as accurate as ECR"). Comparisons with it run at the Saturday run, on Sunday and Monday games, 2021–2024 (F1, F2).
- **Rolling averages are the floor**, and every season since 2016 has them. Last season's average is a weak floor (F5).
- **The market's closing line is a benchmark at kickoff, not a feature** (F6). It needs a "kickoff" moment that only benchmarks may use (F8).
- **ECR needs a points curve** before it can be scored like a projection (F7).
