# Build plan: the touchdown expert (`td-expert`)

> Written 2026-11-24, before any build result, in the build session (the CEO: "Yes, start td-expert", 2026-11-24). It holds the build's design and every odds the build will be scored on. The technical calls are logged in [decision 0043](../../docs/decisions/0043-td-expert.md); results go in [RESULTS.md](RESULTS.md). Nothing here is edited after a result, except to mark it scored in RESULTS.md.

## What gets built (from the agreed brief)

1. **The facts, as table parts** (layer 0, additive; built with `build_touchdowns`):
   - `play.xtd`: every target and carry by a QB, RB, WR or TE (two-point tries out), with its expected touchdowns, who threw it, the team and the drive. RB, WR and TE chances take opportunity-quality's value (`play.xfp`'s `oq_td_exp`), so the two experts agree; QB carries get their own situation model (scrambles and sneaks are a different mix), fit the same way (up to 10 earlier regular seasons, never fewer than 3, from 2009); targets to anyone else use opportunity-quality's target model.
   - `drive.td_chance`: each drive's chance of a touchdown from the drive model (the chance that a drive ends in a touchdown, from the situation before each snap, fit on earlier seasons): at its first snap, at its first snap inside the 20, and at its closest (the near miss).
   - `player_game.touchdowns`: each rostered QB, RB, WR and TE's rushing, receiving and thrown touchdowns and expected touchdowns, the dice's spread on them, his chances inside the 20 and the 10, and the luck measure (touchdowns over expected in dice spreads, and the chance of scoring at least that many).
   - `team_game.touchdowns`: each team-game's touchdowns, expected touchdowns, red-zone trips, the drive-aware hindsight (below), near misses, and the calling near the goal line.
2. **The forecasts**, players and teams, next game and rest of season, rushing and receiving touchdowns (every QB, RB, WR, TE) and a quarterback's thrown touchdowns, each by method B (a count model on volume) and method A (chances times their worth), with the chance of 0, 1, 2+ from a Poisson count around the forecast.
3. **The regression measure:** touchdowns over expected so far and the share to keep, by position, against keeping all and keeping none.
4. **The luck measure** (looking back) and **near misses** (a description only, never an input).

## How it is scored

- **A new harness kind, `count`** (decision 0043): forecasts of a count are scored by the Poisson log loss (the proper score for a count's mean), with squared error as the readable score. Its calibration is the chance of 1+ and of 2+ by tenth (≤ 3 points, slope 0.9-1.1, VALIDATION.md §7). Ranges q10-q90 are Poisson's, reported.
- **"Removes X%"** is the share of squared error removed against the plain average (the exploration's unit), on held-out seasons. **"A beats B"** is the paired Poisson log loss resampled by whole weeks, 90% interval (VALIDATION.md §4).
- **Seasons:** reported backtest 2016-2024 (training from 2013, the first season with a full year of expected touchdowns behind it); the 2025 vault opened once, at the end, for the shipped forecasts and the regression measure.
- **The yardstick doesn't apply:** the crude forecaster scores yards, market-free. Touchdowns get their own baseline, the one VALIDATION.md names for anytime touchdowns: a player's (or team's) season touchdown rate, shrunk toward his position's (rung 0). The market's anytime price is the other named baseline; we have no free history of it before 2026, so it isn't used.

## The ladder (each family: players, thrown, teams; each horizon)

| Rung | Method | What it is |
|---|---|---|
| 0 | `rate` | Touchdowns a game so far (this season and last), shrunk toward the position's rate |
| 1 | `volume` (method B) | Poisson regression on volume: yards, chances, snaps, past touchdowns, the team's touchdowns and offense, position; the opponent's touchdowns allowed |
| 1 | `chances` (method A) | Two stages: (1) next game's expected touchdowns from the chances he gets (kinds, near the goal line, playing time), fit on later expected touchdowns, which are less noisy than touchdowns; (2) touchdowns = that forecast × the small corrections (his touchdowns over expected so far, shrunk; the offense's quality; the team's calling near the goal line; the opponent) |
| 3 | trees | Only if rung 1 shows interactions worth looking for |

The no-noise test (the CEO's, 2026-11-17): **A must do at least as well as B** (the 90% interval of A minus B not entirely worse), for each horizon, for players and teams; where it doesn't, B ships as the forecast and the expert ships its measures.

## Claude's odds, written before any run

| # | Bet | Chance | Expected size |
|---|---|---|---|
| O1 | **The team's ceiling** (drive-aware hindsight: knowing every red-zone trip's chance at the 20 and every long touchdown) removes 40%+ of the next game's error | 65% | about 50% next game, 75% rest of season |
| O2 | The plain chance-sum hindsight (F21's) removes less than the drive-aware one next game | 80% | 14% against about 50% |
| O3 | **Players, next game: A at least as good as B** (passes the no-noise test) | 60% | A − B within ±0.2% of the Poisson log loss |
| O4 | Players, next game: A clearly beats B | 25% | |
| O5 | Players, rest of season: A at least as good as B | 55% | |
| O6 | Thrown, next game: A at least as good as B | 50% | |
| O7 | Teams, next game: A at least as good as B | 50% | |
| O8 | Teams, rest of season: A at least as good as B | 45% | |
| O9 | Every shipped forecast beats its shuffled copies (20 of 20 or 95 of 100) | 95% | |
| O10 | Every shipped forecast beats rung 0 (the season rate) | 90% | 3 to 8% of the squared error, next game |
| O11 | Players' chance of 1+ touchdowns is calibrated (≤ 3 points, slope 0.9-1.1) | 85% | error about 1 point |
| O12 | Thrown touchdowns' chance of 2+ is calibrated under Poisson (≤ 3 points) | 65% | Poisson slightly too wide (QBs' thrown touchdowns are less spread than Poisson) |
| O13 | **The regression measure** (a kept share per position) beats both "keeps all" and "keeps none" for rushing and receiving | 75% | beats keep-none by about 0.5% of the squared error; kept share about 0.1 (RB, TE), 0 (WR) |
| O14 | The same for thrown touchdowns | 50% | kept share about 0.1 |
| O15 | **H67 (build):** the team's calling near the goal line adds to a player's forecast beyond the offense's quality, interval clear of 0 | 30% | +0.2% of the squared error |
| O16 | **H68 (build):** red-zone chances add to a non-QB's rest-of-season forecast beyond volume, interval clear | 15% | about 0 |
| O17 | I58 (already in IDEAS.md): a QB's red-zone carries add 2%+ of the remaining error to his rushing touchdowns beyond volume | 70% | |
| O18 | I61 (already in IDEAS.md): once the throw's expected touchdowns know the passer and his offense, past thrown touchdowns add under 2% beyond them | 50% | |
| O19 | Near misses repeat under 0.1 half to half (noise) | 85% | 0.05 |
| O20 | Expected touchdowns a game repeat 0.5+ week-to-week halves; touchdowns over expected under 0.1 | 85% | 0.6 and 0.05 |
| O21 | The vault (2025) agrees: the shipped forecasts beat their shuffled copies and rung 0, and the A-against-B verdict doesn't flip | 70% | |
| O22 | Trees beat the Poisson regression on B's inputs (players, next game), interval clear | 35% | +0.3% |

Why these odds: the exploration says volume carries almost all of it (F2-F4, F6), so A's two-stage idea (fit on expected touchdowns, which are steadier than touchdowns: 0.60 against 0.43) has a real but small edge to find, and B's inputs already see most of what A's corrections add (F16). Thrown touchdowns are a larger count (1.4 a game), so Poisson's fit there is the least sure.
