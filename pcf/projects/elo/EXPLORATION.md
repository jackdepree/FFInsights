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

- **The success bar is tightened (CEO, 2026-11-07):** within 0.5 points of the close on margins and totals, with 0.25 a strong result. The old 1.5 was met by home field alone (F1).
- **Rung 1 for the hunch tests is the margin Elo with a half pull, plus offense and defense ratings** (F3, F4). Each hunch is a variant of it, judged on the same 2,476 games.

## H4: luck plays

**Expected, written before running (Claude, 2026-11-07):** return touchdowns (defense and special teams) and which side recovers a fumble will barely repeat from one half of a season to the other, with a split-half correlation near 0. Kicking luck will repeat a little (kickers differ), and interceptions more (quarterbacks differ). Taking the luck out of the margin will help a little: about 0.03–0.08 points on the margin. That's real but small, because these plays add only a few points a game, and the Elo's small step already averages most of them away.

Run 2026-11-07 with [`explore/h4_luck.py`](explore/h4_luck.py). Repeatability is each team-season's average per game, net of the opponent, in odd weeks against even weeks (regular season, 1999–2024). Ratings are scored against rung 1 on the same 2,476 games, 2016–2024.

| # | Finding | Confidence |
|---|---|---|
| F7 | **Fumble recoveries are pure noise; the other candidates repeat a little.** Split-half correlation, net of the opponent: fumble recovery −0.05, kicking 0.09, long touchdowns 0.11, interceptions 0.13, return touchdowns 0.15. The margin itself is 0.51. Each candidate swings 1.6–4.2 points a game for a team. | strong |
| F8 | **Taking luck plays out of the margin doesn't help the rating; it hurts slightly.** The gap to rung 1, where positive means worse, with a 90% interval: no fumble luck +0.02 (−0.00 to +0.05), no return TDs +0.02 (−0.01 to +0.05), no kicking luck +0.00, no long TDs +0.01, no interceptions +0.09 (+0.05 to +0.13). All three noisiest together: +0.05 (+0.00 to +0.09). At half weight: +0.00. 2020–2024 alone, where expected points are out of sample: +0.03 (−0.03 to +0.09). Totals from offense and defense ratings: +0.02 (−0.03 to +0.07). | strong |
| F9 | **Why, probably:** the Elo's small step already averages luck away. A single play moves a rating by 6% of its points, so a 7-point return TD moves it by 0.4. Taking plays out also throws away the parts that do repeat (return TDs 0.15, interceptions 0.13). Fumble recovery (r = −0.05) is the cleanest test of pure noise, and it still didn't help. | moderate |

**H4 verdict: failed, as tested.** Expected a small gain (0.03–0.08 points). Got a small loss (0.00–0.09). The idea that a fumble returned for a touchdown is "a random fluke" holds for the fumble recovery (F7). But a rating that ignores luck plays forecasts no better, because over a dozen games the luck washes out anyway. What could still work: luck plays as a separate signal for the first few weeks, when ratings rest on few games, or for reading single games (game script, garbage time). Neither was tested here.

## H3: average win probability

**Expected, written before running (Claude, 2026-11-07):** a game's average home win probability across its plays measures control more steadily than the final margin. A late comeback barely moves it, and neither do garbage-time points. On its own, it will be about as good as the margin. Blended with the margin, it will help by 0.05–0.15 points. nflverse's win probability is fit on seasons through 2019 (tag-tables#F4), so the verdict rests on 2020–2024. It uses the model without the betting line (`home_wp`, not `vegas_home_wp`), so no market number leaks in.

Run 2026-11-07 with [`explore/h3_winprob.py`](explore/h3_winprob.py). Each game's average home win probability is turned into points by a straight line fit on 2002–2015: 52 points per unit above 0.5, so an average of 60% is worth about 5 points. The 3 games from 1999–2000 with no play-by-play fall back to their margin.

| # | Finding | Confidence |
|---|---|---|
| F10 | **Average win probability repeats less than the margin, not more.** Split-half correlation: 0.41 against the margin's 0.51. Game by game, the two agree closely (correlation 0.84). | strong |
| F11 | **On its own, it forecasts worse than the margin; blended in, it adds almost nothing.** Gaps to rung 1, where negative means better, with a 90% interval. 2016–2024: win probability alone +0.10 (+0.03 to +0.16), half and half +0.01, three-quarters margin −0.01 (−0.02 to +0.01). 2020–2024, out of sample for the win-probability model: alone +0.05 (−0.04 to +0.14), half and half −0.01 (−0.06 to +0.04), three-quarters margin −0.02 (−0.04 to +0.00). Tuning the blend picks three-quarters margin. | strong |

**H3 verdict: unclear, leaning failed.** Expected a gain of 0.05–0.15 points. The best blend gains 0.02 at most, and its interval reaches zero. The CEO's example is real: a late underdog win scores lower on average win probability than on the margin. But it's rarer or smaller than the margin's other strengths. The margin already captures most of what win probability knows, and win probability is noisier from week to week (F10). It's worth keeping as a small ingredient for rung 3, where small gains may add up, but not as a replacement for the margin.

## Still to do in this exploration

1. **H2, turnover:** the pull set by the share of last season's snaps that return.
2. **H1, same-team share:** the share of a team's usual snaps on the field this week, from participation and the injury report.
3. **H7, parts:** running and passing ratings, each kept only if it helps.
4. **Win chances, ranges and the long horizon:** calibration, q10–q90 coverage, and wins over the next 3 games and the rest of the season.
