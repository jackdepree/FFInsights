# Exploration: Team Elo (`elo`)

> Is a simple rating near the closing line, and do the CEO's hunches beat it? Rungs 0–1 first, then each hunch as a variant of rung 1.
> Started 2026-11-07. Games 1999–2024; settings are tuned on 2002–2015 and results reported on 2016–2024. The vault (2025) isn't read.

**Verdict (2026-11-07): GO.** A margin Elo with a half pull between seasons is 0.37 points behind the closing line on margins and 0.39 on totals. That passes the tightened 0.5-point bar (F3, F4). The hunches, each against that rating, on 2016–2024, where negative means it helped:

| Hunch | Verdict | Gap to rung 1 (points) |
|---|---|---|
| H1 same team this week | **held**, modestly | −0.06 in rung 3 (QB −0.04, other absences −0.02) |
| H2 regress between seasons | **held** | −0.21 (the half pull, F3) |
| H2 pull scaled by turnover | **failed** | +0.00 to +0.05, worse the more it leans on turnover |
| H3 average win probability | **unclear**, leaning failed | −0.01 to −0.02 as a blend; +0.10 alone |
| H4 luck plays removed | **failed** | +0.00 to +0.09 |
| H7 passing and running parts | **unclear**, no gain | −0.01 to +0.00 |

**Rung 3** (rung 1 + H1, re-tuned each season) is 0.31 behind the close on margins and 0.39 on totals. Win chances are close to calibrated, ranges cover 81–82%, and the season-wins forecast beats its yardstick at every week (F22–F26). The 0.25 "strong" bar isn't reached. The CEO's second test, consistency, is in [`projects/CONSISTENCY.md`](../CONSISTENCY.md); finishing is a trait that doesn't help the margin (F19, F23).

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

## H2 and H1: is it the same team?

**Expected, written before running (Claude, 2026-11-07):**
- **H2, a pull set by turnover:** a small gain, 0.01–0.04 points, mostly in the first weeks. The half pull already catches most of the drift, and turnover is only part of why teams change.
- **H1, same-team share:** a starting quarterback out is the big one, about 0.05–0.10 points over all games, since it's a few games but large misses. Every other absence adds a little more, 0.02–0.05.
- **Data:** snap counts start in 2013, so H2 is measured from 2014 and H1 from 2013. H2 is tuned on 2014–2019 and reported on 2020–2024. H1 has no setting fit before 2016, so its size is tuned on 2013–2015 and reported on 2016–2024.

Run 2026-11-07 with [`explore/h2_h1_same_team.py`](explore/h2_h1_same_team.py).

| # | Finding | Confidence |
|---|---|---|
| F12 | **Teams bring back about two-thirds of last season's snaps:** a mean of 66%, ranging from 40% to 96% (2014–2024). | strong |
| F13 | **Setting each team's pull by its turnover makes the rating worse, the harder it leans on turnover.** With pull = 0.5 + b × (league average returning share − the team's), the gap to rung 1 on 2016–2024 is +0.00 (b = 0.5), +0.01 (1.5), +0.04 (3) and +0.05 (4). Tuned on 2014–2019, it picks b = 0, plain rung 1. | strong |
| F14 | **A missing usual quarterback is worth about 2–3 points, and it helps the rating.** The usual starter is out or off the roster in 5.7% of team-games. Tuned on 2013–2015, the adjustment is 2 points, with a gap of −0.039 (−0.059 to −0.019) on 2016–2024. (Rerun 2026-11-07 after ties between two quarterbacks with equal shares were broken by player id; it was −0.036 before.) | strong |
| F15 | **Other absences matter too (H1).** The same-team share averages 0.94 (bottom tenth: 0.88 or less). On its own, tuned at 5 points per unit of share, the gap is −0.021 (−0.031 to −0.011). With the QB adjustment it adds about 0.02 more: QB 2 + share 5 gives −0.054 (−0.078 to −0.030). | strong |
| F16 | **The best sizes are probably larger than tuning picked.** Tuning had only 2013–2015, and the 2016–2024 curve keeps improving up to QB 3 and share 10–20, reaching −0.07 with both. That's chosen with hindsight, so it isn't a result. In rung 3, sizes should be re-tuned each season on all seasons before it. | moderate |

**H2 verdict: half held.** The CEO's "every team should regress towards the mean when the season turns over" holds strongly. A half pull is the biggest gain on the ladder (F3), and larger than the usual one-third. "It's really a new team every season" scaled by each team's turnover fails (F13). Returning snaps don't say how much a team will change. Probably who leaves matters more than how many, which is H1's question asked between seasons. Expected 0.01–0.04 points from turnover; got nothing.

**H1 verdict: held, modestly.** Expected 0.05–0.10 from the quarterback and 0.02–0.05 from everyone else. Got 0.04 and 0.02, about 0.05–0.06 together, with intervals clear of zero. "Is this the same team that played last week?" is a real signal beyond the quarterback, the usual way's only adjustment. The tracking analogy's other half, trusting new results more after a big change, wasn't tested.

## H7: parts of a team

**Expected, written before running (Claude, 2026-11-07):** offense and defense ratings are already in (F4). They don't improve the margin but are needed for totals. Passing ratings, built from expected points per pass play for offense and defense, will add to the points rating: about 0.03–0.08 on the margin, because passing efficiency is steadier than points. Running ratings will add about nothing. Splitting into passing and running will beat a single efficiency rating only slightly. Expected points are fit through 2019 (tag-tables#F4), so 2020–2024 is the check.

Run 2026-11-07 with [`explore/h7_parts.py`](explore/h7_parts.py). Passing, running and all-play ratings of expected points per play are added to rung 1's forecasts, with weights fit on 2002–2015.

| # | Finding | Confidence |
|---|---|---|
| F17 | **Efficiency ratings mostly repeat what the points rating knows.** An all-play efficiency rating's edge correlates 0.93 with rung 1's forecast. On its own, it misses the margin by 10.24 on 2016–2024, against rung 1's 10.16. | strong |
| F18 | **Passing and running ratings add nothing measurable on top.** Gaps to rung 1 on 2016–2024, with a 90% interval. Passing: margin −0.003 (−0.023 to +0.016), total −0.004. Running: −0.003 and −0.001. Both: −0.007 (−0.032 to +0.017) and −0.003. All plays: −0.005 and −0.006. 2020–2024 is the same story, all within ±0.01. | strong |

**H7 verdict: unclear, failed as a forecasting gain.** The CEO's "overall predictor ... easy for downstream models to learn from" holds: one rating does the work. Offense and defense ratings earn their place because totals need them (F4). Passing and running parts don't improve next games' margins or totals (F18), against an expected 0.03–0.08 from passing. Two caveats: they may still be useful downstream, for game script, play mix or fantasy, and that's those projects' question; and the winning and losing parts of H7 are part 2 (H5).

## Consistency of every measure (the CEO's second test)

The CEO asked on 2026-11-07 that every measure also gets a consistency test, kept even when it doesn't help the target. All 20 Elo measures are in [`projects/CONSISTENCY.md`](../CONSISTENCY.md). Three things are new here:

| # | Finding | Confidence |
|---|---|---|
| F19 | **"Finishing" is a team trait.** It's the result minus average win probability, so it's high when a team wins games it didn't control: the CEO's late underdog win. Week to week r = 0.28 (90% interval from 0.22), and season to season r = 0.22. It carries into next season. Average win probability helped the rating only a little (F11), but the gap between control and result isn't random. | strong |
| F20 | **Kicking "luck" is kicker skill (r = 0.24, season 0.30). The opponents' kicking repeats too (0.16, season 0.28), probably the home stadium.** Only fumble recoveries and long TDs allowed are noise. | strong |
| F21 | **Same-team share is a trait across seasons (0.40), but a missing QB is only a state (0.06).** Some teams are reliably healthier, year after year. | moderate |

## Rung 3: what held, combined

**Expected, written before running (Claude, 2026-11-07):**
- **The combined rating:** rung 1 + H1, with sizes re-tuned each season on all seasons before it, plus the small H3 blend. About 0.05–0.07 points better than rung 1, so about 0.30–0.32 behind the close on margins: past the 0.5 floor, short of 0.25.
- **Finishing (F19):** may help win chances more than margins. About 0.00–0.02 points on margins.
- **Win chances:** close to calibrated, with log loss a little worse than the no-vig closing line.
- **Ranges:** q10–q90 near 80% once their width is fit on past seasons.
- **Long horizon:** summed game win chances beat the yardstick (the current win rate pulled toward .500) for the rest of the season, more so early in the season.

Run 2026-11-07 with [`explore/rung3.py`](explore/rung3.py). Settings are re-chosen before every season from 2016, on all seasons from 2013 up to it. The choice is rounded to 0.001 points, and ties go to the simpler setting, so float noise can't flip it. Three runs give the same forecasts.

| # | Finding | Confidence |
|---|---|---|
| F22 | **Rung 3 misses the margin by 10.10, 0.31 behind the close.** That's 0.06 better than rung 1, with a 90% interval of 0.03 to 0.09, on 2016–2024. On 2020–2024 it's 10.09, 0.10 better than rung 1 (0.06 to 0.15) and 0.31 behind the close. Each season picked the QB adjustment (2 points) and the same-team share (10 points per unit) almost every time. It never picked the win-probability blend. | strong |
| F23 | **Finishing (F19) is a trait but adds nothing to the margin:** 0.000 (−0.005 to +0.005), even though it was picked in 5 of 9 seasons. It may matter for win chances or game states (H5), which this didn't test. | strong |
| F24 | **Win chances: log loss 0.633 against the close's 0.609, Brier score 0.221 against 0.211.** Calibration is close but a little too timid in the middle. Forecasts of 0.40–0.50 win 38.5% (forecast 45.3%), and forecasts of 0.60–0.70 win 70.2% (forecast 64.8%). A wider margin-to-win-chance curve, or one fit by logistic regression, should help. | strong |
| F25 | **Ranges hold:** 82.4% of margins and 80.9% of totals land inside q10–q90, against an 80% target. Both are about 35 points wide, from earlier seasons' misses. | strong |
| F26 | **The long horizon beats the yardstick at every point in the season.** Mean miss in wins, Elo against the yardstick, with the yardstick pulling the win rate toward .500 by 8 games: rest of season before week 1, 2.34 against 2.58; after 4 games, 1.93 against 1.99; after 8, 1.38 against 1.44; after 12, 0.91 against 0.97. Next 3 games: 0.70 against 0.73 overall. It uses ratings as they stood, with no future injuries. | strong |

**Against the bars:** margins are 0.31 behind the close and totals 0.39 (F4). Both pass the 0.5 floor; neither reaches the 0.25 "strong" mark. Matching expectations: the margin gain (0.06) and the gap (0.31) came in as expected. Finishing's gain came in at the low end (0.00). Win chances are a little worse calibrated than expected (F24), and ranges and the long horizon came in as expected.

## Still to do

The exploration's questions are answered. Before building, for the CEO:
1. **Direction:** build rung 3 as the champion (the margin Elo with a half pull, QB and same-team adjustments, offense and defense ratings for totals, the long horizon), or chase the last 0.06 to the 0.25 bar first?
2. **Part 2** (H5, conditional strength) waits for `stabilization` (H6). Finishing (F19) and the same-team share (F21) are its first leads.
