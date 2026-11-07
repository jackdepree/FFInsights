# 0016: The Wednesday run moves to Thursday noon

**Date:** 2026-11-06 · **Decided by:** CEO (`prediction-ledger`, EXPLORATION finding 10)

**Decision:** The weekly runs are now **Tuesday 10:00, Thursday 12:00 and Saturday 12:00 Eastern**. Thursday replaces Wednesday 16:00. The rule from decision 0010 is unchanged: each game is predicted at the latest allowed run before its kickoff.

**Why:** nflverse's injury file updates once a day, in the morning. At Wednesday 16:00 the live file has no final report for Thursday's game, while the backtest, using real times, saw 75.2% of them. At Thursday noon the backtest sees 99.7%, and the file should have them, so live and backtest match. The move also makes the scores better on 2016–2024:

| Champion | Score ×100, Thursday games | Change (90% interval) | All rows |
|---|---|---|---|
| `trees_week` (range score) | 3.392 → 3.297 | −0.095 (−0.143 to −0.051) | 3.553 → 3.547 |
| `active` (log loss) | 19.469 → 17.754 | −1.715 (−2.504 to −0.975) | 21.552 → 21.451 |
| `lasso_h3` (range score) | 3.936 → 3.904 | −0.032 (−0.056 to −0.012) | 4.125 → 4.123 |
| `lasso_rest` (range score) | 4.140 → 4.130 | tie | 4.374 → 4.374 |
| `last_game` (range score) | 4.239 → 4.240 | tie | 4.727 → 4.728 |

**What it costs:**
- **Less lead time.** A Thursday-night forecast comes about 8 hours before kickoff, not 28. Betting products will have less time to act on it.
- **The run must be quick on Thanksgiving.** A 12:30 game leaves 30 minutes. The ledger refuses a forecast written after kickoff, so its run has to finish in time.
- **Wednesday games go back to Tuesday 10:00.** They had been at Wednesday 16:00 when it came before kickoff. One game is left in 2026: `2026_12_GB_LA`, about 34 hours before kickoff with no final report.
- **Friday games move up but still miss their final report.** It comes Thursday afternoon. That's true in the backtest too, so it isn't a live gap. Four are left in 2026. Idea I18 is the cheap fix.
- **ECR gains rows.** ECR is known by Thursday noon for 100 Thursday and Friday rows that had none at Wednesday 16:00, so its scored rows grow from 17,221 to 17,321. Its scorecard is rerun; the numbers in baselines' RESULTS predate this.

**Alternatives:**
- Keep Wednesday 16:00: nothing to rerun, but Thursday forecasts would treat players on the report as healthy, unlike the backtest.
- Treat Thursday's report as known by Wednesday 16:00 (rejected as tempting and wrong): the tables would match the backtest while the live file still didn't have it.

**Reruns:** the four participation champions, `last_game` and ECR, all `--refit season`, on 2026-11-06. New runs: `trees_week` 2abc96bc, `active` 1a540654, `lasso_h3` f0da2987, `lasso_rest` 2de0578d, `last_game` f4bd4f92, `ecr` dcfb4dd9. All leakage checks pass, and each participation model still beats 20 of 20 shuffled refits. The move wasn't chosen from these scores, so it doesn't count as a new version tried. Other variants' saved histories keep the old moment. Comparisons among them in participation's RESULTS were made on one moment, so they stand as written.

**Revisit if:** the file's update time moves past noon on Thursdays, or products need a forecast earlier than Thursday noon. A product can declare the `tuesday` run, or a new one.

**Scripts:** [`thursday_run.py`](../../projects/prediction-ledger/explore/thursday_run.py), [`thursday_scores.py`](../../projects/prediction-ledger/explore/thursday_scores.py).
