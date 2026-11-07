# Hunches: the scoreboard of unconventional bets

> Where PCF went against the usual way, and whether it paid off (CLAUDE.md, "The hunch scoreboard"). The market and the consensus are the average, so our edge comes from bets that are different *and* right. This page counts both.

- **Who adds rows:** mostly the CEO, from each brief's "CEO hunches". Claude adds one when it notices we're doing something unconventional.
- **When:** a row is added when the bet is made, and its verdict filled in when it's tested. Failed bets stay: they show where to lean on the data.
- **Verdicts:** **held** (beat the usual way on held-out data, or the exploration found the signal it predicted), **failed** (it didn't, or the usual way won), **unclear** (too little data, or mixed), **open** (not tested yet).
- **The size matters as much as the verdict.** Each verdict gives its numbers, so a small win isn't counted like a large one.
- **A held hunch in an exploration is discovery, not proof.** Only the harness proves a model beats something.

| # | Date | Who | Project | The usual way | Our bet | How it was tested | Verdict | Size |
|---|---|---|---|---|---|---|---|---|
| H1 | 2026-11-07 | CEO | elo | Only a QB adjustment | Injury reports and snap shares say whether it's the same team this week | Rating adjusted by the usual QB missing and the same-team share (2016–2024) | held | 0.06 points on the margin in rung 3 (QB 0.04, other absences 0.02), intervals clear of zero |
| H2a | 2026-11-07 | CEO | elo | Pull a third of the way to average between seasons | Every team should regress toward the mean when the season turns over | Pull sizes tried on 2002–2015, scored on 2016–2024 | held | A half pull is the biggest gain on the ladder: 0.21 points over no pull, and better than a third. Measured directly (2026-11-07, decision 0021): a season's margin keeps 0.42 of itself into next season, Elo's smoothed end-of-season rating 0.60-0.68, so the pull is now 0.4 (ties 0.5 in forecasts) |
| H2b | 2026-11-07 | CEO | elo | The same pull for every team | It's a new team every season: turnover sets how far a team moves | Pull scaled by the share of last season's snaps that return (2014–2024) | failed | Worse the more it leans on turnover (+0.00 to +0.05) |
| H3 | 2026-11-07 | CEO | elo | Final margin, damped | Average win probability across plays says more than the margin | Ratings learning from a blend of the two (2016–2024; 2020–2024 out of sample) | unclear | At most 0.02 points as a blend, interval reaching zero; worse alone (+0.10) |
| H4 | 2026-11-07 | CEO | elo | Final score as it happened | Noise-cancelled scores: high-impact luck plays count as if they didn't happen | Repeatability of five play types, then ratings on the margin without them | failed | Fumble recovery is pure noise (r −0.05), but removing it or any other gives +0.00 to +0.09 |
| H5 | 2026-11-07 | CEO | elo | One rating plus a home bonus | Strength is conditional (home, opponent's QB, coverage, game state) | Part 2, after `stabilization` | open | |
| H6 | 2026-11-07 | CEO | stabilization | Not part of Elo | First find which conditions are consistent and predict the future | Its own project | open | |
| H7 | 2026-11-07 | CEO | elo | One rating, sometimes offense and defense | An overall rating plus parts: offense, defense, running, passing | Passing, running and all-play efficiency ratings added to the points rating | unclear | Offense and defense needed for totals; passing and running add nothing (±0.01) |

## Tally

Updated with each verdict.

| Who | Held | Failed | Unclear | Open |
|---|---|---|---|---|
| CEO | 2 | 2 | 2 | 2 |
| Claude | 0 | 0 | 0 | 0 |
