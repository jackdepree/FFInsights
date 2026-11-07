# Exploration: Team Elo (`elo`)

> Is a simple rating near the closing line, and do the CEO's hunches beat it? Rungs 0–1 first, then each hunch as a variant of rung 1.
> Started 2026-11-07. Games 1999–2024; settings are tuned on 2002–2015 and results reported on 2016–2024. The vault (2025) isn't read.

## Expectations, written before running (Claude, 2026-11-07)

- **Rung 0 (home field only):** misses the margin by about 11.3 points and the total by about 11.0. That is roughly the "near the close" bar for margins (11.3), so the bar may be met by a rating that knows nothing. If so, the real test is beating rung 1, and the CEO should hear that the 1.5-point bar is loose.
- **Rung 1 (margin Elo):** about 10.3–10.6 on the margin, 0.5–0.8 points behind the close. Totals need offense and defense ratings and will be weaker: about 10.8–11.2, against the close's 10.4.
- **Chess-style win/loss Elo:** a little worse than the margin Elo on margins (it throws away the size of the win).
- **The one-third pull between seasons:** helps, by about 0.1 point early in the season.

## Findings

Rungs 0–1, run 2026-11-07 with [`explore/ladder.py`](explore/ladder.py). There are 2,476 games from 2016–2024, including the playoffs, and every rung is scored on the same games. Ratings are frozen for each week, so no game sees a result from its own week. Home field is the mean home margin of the previous three seasons.

| # | Finding | Confidence |
|---|---|---|
| F1 | **The "near the close" bar is met by a rating that knows nothing.** Home field alone misses the margin by 10.98 points, 1.19 more than the close's 9.79, which is inside the 1.5-point bar. On totals, last season's average total misses by 11.08, 0.64 more than the close's 10.44. So the 1.5-point bar can't tell a good rating from no rating. The test with teeth is beating rung 1. | strong |
| F2 | **The CEO's base (margin-only Elo, ratings in points) misses the margin by 10.37, 0.58 more than the close.** After each game, both teams move by 0.05 times the miss on the margin. It beats the chess-style win/loss Elo (10.51) by 0.14 points, with a 90% interval of 0.06 to 0.22. It also beats last season's point differential (10.61) by 0.24. The size of the win carries information that win/loss throws away. | strong |
| F3 | **Pulling ratings halfway back toward average between seasons is the biggest single gain: 10.16, 0.37 more than the close.** That beats the base by 0.21 points, with a 90% interval of 0.13 to 0.30. Pulls of 0.4–0.5 are best both on the tuning seasons and on 2016–2024. The usual one-third is close behind, and 0.7 or more is worse. This is H2's fixed-pull version, and it's larger than FiveThirtyEight's one-third. FiveThirtyEight's own recipe scores 10.20. | strong |
| F4 | **Offense and defense ratings predict the total at 10.83, 0.39 more than the close, with the margin unchanged (10.18).** They beat last season's average total by 0.25, with a 90% interval of 0.14 to 0.37. Their best setting has the same step size and pull as F3. | strong |
| F5 | **The gap to the close is steady across seasons:** 0.10 (2018) to 0.52 (2023) points on the margin, never negative. Early-season games (weeks 1–4) are no worse than later ones once ratings are pulled toward average (10.19 against 10.15). Last season's point differential alone is as good as Elo in weeks 1–4 (10.19), and much worse after (10.74). | moderate |
| F6 | **Home field has moved:** the previous three seasons' mean home margin fell from 2.5 points (2016) to 0.7 (2022) and recovered to 2.3 (2024). A fixed home bonus tuned on older seasons would have overrated home teams in 2020–2023. | strong |

**Against the expectations:** rung 0 matched (10.98 against about 11.3 expected; the bar is loose, F1). Rung 1 did better than expected: 0.37 points behind the close, not 0.5–0.8. Totals too: 0.39 behind, not about 0.6. The pull between seasons helped twice as much as expected (0.21 points, not 0.1), and its best size is about a half, not a third.

**Early read on H2:** the first half of H2, "every team should regress towards the mean when the season turns over", holds strongly (F3). The pull is the largest gain on the ladder, and stronger than the usual one-third. The second half, a pull set by each team's turnover, is still to test.

## What this means for the brief

- **The success bar needs a decision (CEO, taste call).** Within 1.5 points of the close is met by home field alone (F1). Rung 1 is already 0.37 behind on margins and 0.39 on totals.
- **Rung 1 for the hunch tests is the margin Elo with a half pull, plus offense and defense ratings** (F3, F4). Each hunch is a variant of it, judged on the same 2,476 games.

## Still to do in this exploration

1. **H4, luck plays:** find high-impact plays that teams don't repeat, and rate teams on the margin without them.
2. **H2, turnover:** the pull set by the share of last season's snaps that return.
3. **H3, average win probability:** judged on 2020–2024 only (tag-tables#F4).
4. **H1, same-team share:** the share of a team's usual snaps on the field this week, from participation and the injury report.
5. **H7, parts:** running and passing ratings, each kept only if it helps.
6. **Win chances, ranges and the long horizon:** calibration, q10–q90 coverage, and wins over the next 3 games and the rest of the season.
