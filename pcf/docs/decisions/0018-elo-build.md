# 0018: How the Elo expert is built

**Date:** 2026-11-07 · **Decided by:** Claude (technical calls, listed for the CEO's veto at merge) · **Project:** `elo`

**Decision:** The package `pcf.experts.elo` is the exploration's rung 3 (EXPLORATION F26), built on the harness. The calls inside it:

1. **The walk's settings are fixed, not tuned per season.** Margin step 0.06 with a half pull between seasons; offense and defense step 0.05 with a one-third pull. They were chosen on 2002–2015, before any backtest season. The exploration re-chose them each season, and the fixed ones did as well (margin 10.09 against 10.10).
2. **The harness fits the sizes, the walk only rates.** The walk folds in raw results. How much the rating gap, home field, a missing QB and the same-team share are worth is a weighted regression refit in each training window, like every other expert. The walk itself doesn't adjust a result for who played (H1's adjustments enter the forecast, not the ratings).
3. **Results are walked in the order they became known** (then kickoff, then game id). So the ratings at any moment use exactly the results known by then, and per-moment features equal the bulk history (tested on 2016 week 1, 2019 week 9, 2023 week 2 and 2024 week 17).
4. **It forecasts at the Saturday run**, like the other in-season experts. A Thursday game takes the Thursday run (decision 0016).
5. **Three variants under one id:** `margin` (home margin), `total` (total points) and `win` (home win chance). They share the features and differ in the fit.
6. **The win chance is a logistic curve** fitted on the margin's features, not a fixed normal curve around the margin (exploration F24: the fitted curve was better calibrated).
7. **Same-team share and the usual QB:** a team's usual players are its last 4 games' snap shares, known after each game. A player counts as missing if they're off the roster for the week, or listed Out or Doubtful on a report known before the forecast. The usual QB is the one with the top offense share; ties go to the lower player id, so runs repeat exactly.
8. **Home field** is the mean home margin of the 3 seasons before, neutral games left out; league points per team are last season's mean. Both are known before the season starts.

**Why:** each one keeps the package equal to what the exploration measured (2016–2024: margin miss 10.09 against the close's 9.79; total 10.76 against 10.44; win log loss 0.631 against 0.609), and keeps it point-in-time.

**Alternatives:**
- Re-tune the walk each season (the exploration's way): no better, slower, and one more thing to leak.
- Adjust the ratings for missing players as the walk goes (a team that won without its QB gets extra credit): untested; a candidate for Elo part 2.
- Fit the walk's step inside the harness (tempting, rejected for now): it makes every training window rerun the walk many times, and the exploration found the settings flat near the chosen values.

**Revisit if:** the validation scorecard shows the fixed settings drifting (the misses growing in later seasons), or part 2 adds an adjustment that belongs inside the walk.

**Code:** [`src/pcf/experts/elo/`](../../src/pcf/experts/elo/), tests in [`tests/experts/test_elo.py`](../../tests/experts/test_elo.py), check script [`package_check.py`](../../projects/elo/explore/package_check.py).
