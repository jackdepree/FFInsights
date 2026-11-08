# Hunches: the scoreboard of unconventional bets

> Where PCF went against the usual way, and whether it paid off (CLAUDE.md, "The hunch scoreboard"). The market and the consensus are the average, so our edge comes from bets that are different *and* right. This page counts both.

- **Who adds rows:** the CEO, from each brief's "CEO hunches". **Whose hunch it is (the CEO, 2026-11-08):** this log tests the CEO's domain knowledge. A hunch Claude proposes counts as a hunch only if the CEO edits it significantly; otherwise it is recorded in IDEAS.md as Claude's idea or discovery. The point is not to diminish Claude's ideas but to keep this page a clean measure of the CEO's instinct, so we can learn which kinds of hunches give an edge.
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
| H8 | 2026-11-07 | CEO | elo | A rating ignores what a game means for the standings | Teams with their playoff seed locked rest starters in the final week: flag them from the tiebreakers ("cheap and easy and reliable") | Seed-locked flag in the margin and win forecasts, through the harness (2016–2024) | held | Final-week margin miss −0.43 points (−0.80 to −0.08), gap to the close 1.32 → 0.89 (elo#F14). Not cheap: it needed the NFL's tiebreakers (`pcf.data.standings`) |
| H9 | 2026-11-08 | CEO | schemes-v2 | Teams rated on one line: strength plus home field | Rock-paper-scissors: circles come from flukes in close games, or from schemes that give one team an edge over another | First look: circles against chance models (`schemes-v2/explore/cycles.py`); the real test is style pairings on margins | open | First look: circles are rarer than chance (18.1% against 21.2%), and circle games are closer. Win/loss can't show a point-sized edge; margins can |
| H10 | 2026-11-08 | CEO | schemes-v2 | Schemes are charted labels, often by coaching tree; roles are usage at one team | What follows a coach or coordinator to a new team is the scheme; what follows a player is their role | The movers design: does each tendency move with the play caller, the player, or stay with the roster? | open | |
| H11 | 2026-11-08 | CEO | schemes-v2 | Scheme labels are judged by whether they look right on film | A real scheme predicts performance under conditions (e.g. trailing at halftime) or the matchups in H9 | Scheme tendencies against the win-probability model's expectation for a game state, held-out seasons | open | |
| H12 | 2026-11-08 | CEO | schemes-v2 | A player's efficiency is theirs, adjusted for teammates and opponents | Performance depends on the fit between player and scheme, beyond the talent around them; found by a causal process close to double machine learning | Movers: change in efficiency against old-to-new scheme distance, with prior efficiency, age and supporting cast partialled out | open | |

## Tally

Updated with each verdict.

| Who | Held | Failed | Unclear | Open |
|---|---|---|---|---|
| CEO | 3 | 2 | 2 | 6 |
| Claude | 0 | 0 | 0 | 0 |
