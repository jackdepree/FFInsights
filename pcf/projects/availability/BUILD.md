# Build plan: availability (`availability`)

> Written 2026-11-24, before any build result, in the build session (the build chat: "Build the availability expert ... from its agreed brief"). It holds the build's design and every odds the build will be scored on. Technical calls are logged in [decision 0047](../../docs/decisions/0047-availability-build.md); results go in [RESULTS.md](RESULTS.md). Nothing here is edited after a result, except to mark it scored in RESULTS.md.

## What gets built (from the agreed brief)

1. **The tables (layer 0, additive):**
   - **`roster_week`, a new table:** every player on a team's 53-man roster *or a reserve list* for each of the team's games, 2016 on (weekly statuses start in 2016, grain-tables#F11). `player_game`'s spine leaves reserve lists out, so without this an injured-reserve stint is invisible. Spine part `status`: the team, the roster status (`ACT`, `INA`, `RES`, `PUP`, `RSN`), its code, and `reserve` (on a reserve list for injury, illness or non-football injury), known at the start of the week, like `player_game`'s spine.
   - **`player_game.injured`:** each in-game injury named in the play-by-play ("was injured during the play"), matched by team, jersey and last name (the exploration's rule, decision 0044 call 1), 2013 on, known the day after the game.
2. **The forecasts, players** (every position group: QB, RB, WR, TE, OL, DL, LB, DB):
   - **Next game:** the chance of a health absence (rows: the 53-man roster), and, for QB/RB/WR/TE, the chance he's active, beside participation's `active` (the brief's test 1).
   - **Next 3 games and the rest of the season:** expected games of health absence with q10, q50, q90 (rows: the roster and the reserve lists), and games played for any reason, composed with his rate of playing when healthy.
   - **Kept share:** his snap share when he plays while listed, over participation's healthy share.
3. **The measures:** proneness (in-game injuries per snap over his position's rate, credibility-shrunk, with the body-part repeat flag), and the snap-weighted adjusted games lost per team.
4. **The team output:** snap-weighted adjusted games lost to date and its forecast for the next game and the rest of the season.

## Terms used in the build

- **Health absence** (the brief's): a game with no snap while he's on that game's injury report (any status) or on a reserve list for injury, illness or non-football injury. No snap while unlisted and on the 53 is participation's (a scratch or a benching). Off every roster (released, unsigned) is participation's too.
- **The state** each game (the chain's): `healthy` (on the 53, not listed), `listed` (on the report, Questionable or no game status), `out` (Out or Doubtful), `reserve`, and `off` (on no roster that week; absorbing in the roll-forward).

## How it is scored

- **Seasons:** walk-forward, scored 2017-2024; training rows from 2016 (the first season with weekly reserve statuses); a player's history (snaps, reports, in-game injuries) from 2013. The 2025 vault stays closed in this build (the build chat: "Don't open the vault (2025) unless the brief says to"); opening it once is a yes/no for the CEO.
- **Next game:** log loss (decides), Brier (readable); calibration error ≤ 3 points, slope 0.9-1.1; the brief's own Questionable slope 0.85-1.15.
- **Horizons:** the range score (the average pinball loss over q10, q50 and q90, in games) decides; the mean's squared error is readable; q10-q90 coverage 75-85%.
- **"A beats B":** the paired difference resampled by whole weeks, 2,000 draws, 90% interval above 0 (VALIDATION §4). A tie goes to the simpler side (rule k), named by the brief: participation's `active` and I60's crude forecast over any availability model; method 1 over the chain; the chain over the hidden health state; the lasso over trees.
- **Signal:** every shipped forecast beats its shuffled-outcome refits (95 of 100, or 20 of 20 for the expensive ones).
- **Downstream:** the yardstick's rest-of-season boards (`score_input`, 19 shuffled copies), beside I60's crude forecast and participation; teams beside Elo.

## The ladder

| Rung | Method | Next game | Next 3 / rest of season |
|---|---|---|---|
| 0 | baseline | his position's rate × the status-by-body-part table | the position's rate per game ahead, plus the status-by-body-part table's expected games for the current absence |
| 1 | method 1: two models | logistic / lasso on the report, history, proneness, log exposure and recency | per horizon: the chance of any health absence × the games if any (two parts), each fit on its own |
| 2 | method 2: the chain | rung 1's next game (the chain starts from this week's known state) | a weekly health-state chain (multinomial logistic for each state's moves, with weeks in the state), rolled forward exactly |
| 3 | trees | gradient-boosted trees on rung 1's inputs | trees on the chain's moves |
| 4 | method 3: hidden health state | the HMM's filtered state, next game | the HMM rolled forward |

## Claude's odds, written before any run

| # | Bet | Chance | Expected size |
|---|---|---|---|
| A1 | **Next game, health absence: method 1 beats rung 0** (the status × body part table), interval clear | 85% | 3-8% of the log loss |
| A2 | Trees beat the lasso on next game's health absence, interval clear | 35% | +0.5% |
| A3 | **Test 1: the chance he's active, beside participation's `active`, beats `active` alone** on QB/RB/WR/TE, interval clear | 55% | 0.5-2% of the log loss |
| A4 | It also beats `active` recalibrated inside the folds (a fairer bar) | 40% | 0.3-1% |
| A5 | Questionable players' calibration slope comes out 0.85-1.15 | 60% | about 0.95 |
| A6 | Out and Doubtful are no longer overstated twofold (predicted over actual active rate under 1.3) | 75% | about 1.1 |
| A7 | **Test 2: rest-of-season games played beats I60's crude forecast** (squared error of the share played), interval clear | 75% | 3-8% of the squared error |
| A8 | Its q10-q90 coverage lands in 75-85% (the shipped method) | 55% | |
| A9 | The q10 problem is fixed: the share of results below q10 is 7-13% | 55% | |
| A10 | **The chain beats method 1** on the rest-of-season range score of health absences, interval clear | 40% (tie 45%, method 1 better 15%) | 1-3% of the range score |
| A11 | **The hidden health state beats the chain**, interval clear | 20% (tie 50%, worse 30%) | |
| A12 | **Test 3: kept share beats participation's share alone** on the squared error of listed players who play | 55% | 1-3% |
| A13 | **Test 4: the yardstick:** beside I60 and participation, it adds clearly on at least one rest-of-season board and beats its 19 copies | 45% (receiving the likeliest) | +0.3-1% |
| A14 | **Test 5a: snap-weighted AGL repeats** season to season, r 0.10-0.35 with the interval above 0 | 70% | r about 0.2 |
| A15 | Test 5b: it tracks the same season's change in net EPA per play, r −0.15 to −0.35 | 70% | about −0.22 |
| A16 | Test 5c: its rest-of-season forecast adds beside Elo on the team rest-of-season board, interval clear | 40% | +0.5-2% |
| A17 | Every shipped forecast beats its shuffled copies | 95% | |
| A18 | Proneness repeats season to season (r above 0.1, interval above 0) | 80% | r about 0.25 |
| I121 | (already in IDEAS.md, odds as written there) proneness beside I60 on the rest-of-season boards | 45% receiving 0.5%+, 30% rushing | |
