# Environment: exploration

> **Status:** pre-registered 2026-11-27, before any result. The CEO picked all three ways to test (2026-11-27: "Use all three methods to test please"). The weather fetch from Open-Meteo is running (the CEO's sign-off, 2026-11-27). Discovery only: 1999-2024, and the 2025 vault stays closed.

## What we expect (W16, written after the CEO's hunches)

**The frame: weather is a tax, not a talent.**
- The conditions take a cut from every team that plays in them, the same way a sales tax hits every buyer.
  - **Where the cut is largest:** wind takes it from long kicks, deep passes and totals; the roof gives it back.
  - **The bookmaker already reads the forecast,** so most of the tax is in the closing total before kickoff.
- **What's left for a model:**
  - the size of the tax where the market underrates it;
  - whether some teams pay less than others (agronomy's stable varieties).

  The second part is the CEO's bet (H124-H126). The record says it's usually small and noisy (F131: no team's home gap repeats; F136: travel adds nothing).
- **Where it sits:**
  - **Feeds:** kicker-dst (wind and distance), the game simulator, pace's forecast, the yardstick's totals and passing boards.
  - **Overlaps:** the closing total and spread (the market prices the forecast), Elo's home edge, and pace's own habits.
  - **Shouldn't redo:** travel and the body clock (F136), or a team's own home gap (F131).

**The results we expect** (Claude's; a middle and an 80% range, W15):
- **15+ mph wind,** against calm games (under 10 mph):
  - about −3 points on the total, 80% between −1.5 and −5;
  - about −1.5 percentage points of field goal makes from 40+ yards for every 5 mph, 80% between −0.5 and −3;
  - about −2 dropbacks a team, 80% between 0 and −4.
- **The roof:** dome and closed games score about +2 points more than outdoor games raw, 80% between +0.5 and +3.5.
- **Beside the closing total,** the conditions' leftover on total points is about 0.5 points or less, and a walk-forward gain on totals is about 0.1% of the squared error, 80% between −0.2% and +0.5%.
- **The largest share explained** is field goal accuracy or game totals, not margin or the per-play rates.
- **Teams' and players' sensitivities** (method 3) repeat weakly (split-half r about 0.1, 80% between −0.1 and 0.3) and don't forecast.
- **The forecast against the observed weather** (2022-2024): wind's correlation is about 0.85 (80% between 0.7 and 0.93), and the mean miss is about 2.5 mph.

The report explains in detail only what went against this frame.

## Data

- **Games:** `game.schedule` and `game.result` (1999-2024), with `team_game` parts `schedule` (rest, home), `pace`, `tendencies`, `stats`, `efficiency`, `pregame` (spread, total line) and `result`. Regular season only.
- **Weather** (`explore/env_fetch_weather.py`): Open-Meteo, hourly. **Observed:** the archive (ERA5 blends) for every outdoor or open-roof game, 1999-2024. **Forecast:** the historical forecast API, 2022-2024. A game's weather is the average over its first three hours from kickoff (UTC). Stadium coordinates are in `explore/stadiums.csv` (62 stadiums). Open-Meteo gives each location's elevation.
- **Stand-in (a technical call, rule c):** the observed weather stands in for the forecast before 2022. The gap is measured on 2022-2024, where both exist. A build would use the forecast issued before the game.
- **Roles:** roles-archetypes' history (2016-2024): players' coordinates `z0`-`z5`. Each is read from the player's *previous* season, so it is known before the game.
- **Schemes:** a team's tendencies (neutral pass rate over expected, shotgun rate) over its previous season.
- **Elo:** its walk-forward margin forecast, 2016-2024 (2,476 games).

**The conditions** (outdoor weather is set to 0, with the dome flag on, for dome and closed-roof games):

| Condition | Measure | The simple test's contrast |
|---|---|---|
| Wind | mph at 10 m | 15+ mph against under 10 (outdoor games) |
| Cold | °F | 32°F or colder against 50°F or warmer (outdoor) |
| Rain | precipitation, inches an hour (rain or snow) | 0.02+ against none (outdoor). Checked against play-by-play's weather text |
| Dome | roof dome or closed | dome against outdoor or open |
| Surface | artificial turf against grass | turf against grass |
| Rest | the team's days since its last game | 5 or fewer, and 13 or more, each against 6-8 |
| Altitude | the stadium's elevation | over 1,000 m (Denver, Mexico City) against the rest |
| Prime time | kickoff at 7 PM Eastern or later, or not on a Sunday | prime time against Sunday daytime |

**The outcomes** (per team-game, unless marked game):
- plays a game;
- seconds a play (`tempo_seconds`);
- dropbacks;
- pass rate over expected;
- runs;
- EPA a play;
- yards a play;
- sack rate (sacks a dropback);
- interception rate (an attempt);
- the spread of play outcomes (the standard deviation of EPA over the team-game's plays);
- points scored;
- game total points (game);
- home margin (game);
- field goal make rate (team-games with 2+ attempts; also per kick, by distance).

## The noise ceiling (first, before any hunch)

For each outcome:
1. **The hindsight room:** the share of the outcome's variation a flexible model (gradient-boosted trees) explains on the conditions alone. It's scored out of fold, a season held out at a time. This is the most the conditions could give.
2. **Split halves:** the conditions-only linear model fit on odd seasons and on even seasons; the correlation of their predictions across games, and of their coefficients.
3. **Fitting noise:** the trees over 5 seeds; the spread of the share explained.

## Method 1: simple tests, then the obvious inputs (H123, H126, H127)

1. **Simple tests (H123):** Welch's t-test for each condition's contrast on each outcome, with the false-discovery rate held at 5% over all of them (Benjamini-Hochberg). **H123 holds** if 3 or more conditions have at least one outcome that survives it.
2. **Beside the obvious inputs (side bet a):** a regression per outcome with every condition together. It holds fixed the team's and opponent's means of that outcome over their previous 8 games, and the closing spread and total. Robust errors, and the same 5% false-discovery rate. **It holds** if 3+ conditions keep an outcome.
3. **Beyond the closing total, out of sample (side bet b):** total points minus the closing total, regressed on the conditions. Walk-forward: trained on all earlier seasons, tested 2016-2024. **It holds** if the squared-error gain over the closing total alone is clear (a 90% interval from 1,000 resamples of weeks, above 0).
4. **The largest share explained (H127):** each outcome's share of variation explained by the conditions-only linear model, out of fold by season. **The CEO's H127 holds** if the outcome with the largest share is none of margin, interception rate, sack rate or yards per play. The side bets are read off the same ranking.
5. **Home field and the weather (H126):** home margin minus Elo's margin forecast (2016-2024). The terms:
   - a cold game (under 40°F) × a cold-climate home team against a dome or warm-climate visitor;
   - wind × home;
   - rain × home;
   - a dome team playing outdoors.

   They're fit leaving a season out at a time. **H126 holds** if the gain over Elo is clear (90% interval, games resampled). The same is reported against the closing spread, 1999-2024.

## Method 2: play-level interactions with roles, and the spread (H124, H125, the spread part of H127)

1. **H124 (2017-2024, roles from the season before).**
   - **Plays and outcomes:**
     - passing: air yards an attempt, completion, EPA a dropback;
     - rushing: EPA a run;
     - pressure: a sack or a QB hit on a dropback;
     - defensive: the same outcomes, read through the defense's role mix.
   - **The base model:** the situation (down, distance, yard line, score, quarter), the conditions, and the side's role mix (the snap-weighted mean of `z0`-`z5` over the team's players that season, from their previous season). On passes, it also has the targeted receiver's own coordinates.
   - **The test:** the base model with the roles × wind and roles × rain terms added, against the base model.
   - **Walk-forward:** trained on earlier seasons, tested 2019-2024, scored on plays in wind of 10+ mph or rain.
   - **H124 holds as worded** if each of the four kinds of outcome has at least one clear gain (90%, games resampled). The side bet holds if any one does.
2. **H125 (team-games, 2017-2024).**
   - **Outcomes:** pace (plays a game, seconds a play), and the schemes' tendencies (neutral pass rate over expected, shotgun rate).
   - **The base model:** the team's and opponent's means over their previous 8 games, plus the conditions.
   - **The test:** the base model with the role mix × conditions and the previous season's tendencies × conditions added, against the base model. Walk-forward, scored on bad-weather games.
   - **H125 holds** if pace's gain is clear.
3. **The spread of play outcomes (H127's first wording):** each play's squared distance from the situation model's EPA, modelled on the conditions (a gamma regression). Reported as the ratio of the spread in 15+ mph wind (and rain, and cold) to calm.

## Method 3 (exploratory): agronomy's stability analysis

1. **The environment index:** each team-game's out-of-fold forecast from method 1's conditions-only model, for pass rate over expected, dropbacks, EPA a play and points, centred on the league.
2. **Sensitivity:** for each team, in blocks of 3 seasons, its outcome (less its block mean) regressed on the index. The slope is its sensitivity: 1 is average, below 1 is weather-proof.
3. **Does it repeat?**
   - Split halves: alternate games within a block, the slopes correlated across teams.
   - The next block's slope against this block's.
   - The same for QBs with 40+ outdoor games, on EPA a dropback and air yards an attempt.
4. **Does it forecast?** Walk-forward: the previous block's shrunk slope × this game's index, added to the conditions-only forecast, scored on bad-weather games.

## The forecast against the observed weather (2022-2024)

- Wind, temperature and rain: the correlation between forecast and observed, the mean miss, and how often the 15+ mph and 32°F flags agree.

## Odds for the tests, written before the run (Claude, 2026-11-27)

| Test | Odds it holds | Size (middle, 80% range) |
|---|---|---|
| H123, simple tests: 3+ conditions | 95% | wind on the total about −3 points (−1.5 to −5) |
| Side a: 3+ beside the obvious inputs | 35% | |
| Side b: beyond the closing total, out of sample | 15% | about +0.1% of the squared error (−0.2% to +0.5%) |
| H127 (the CEO's wording): the largest is none of margin, interceptions, sacks, yards a play | 85% | |
| H127 side: the CEO's four exactly the top four | 20% | |
| H127 side: 3+ of the four in the top four | 55% | |
| H126: home × weather beyond Elo | 20% | about +0.1% of the margin's squared error (−0.2% to +0.4%) |
| H124 as worded: all four kinds | 10% | 0.2-1% of the error on bad-weather plays where it pays |
| H124 side: any one kind | 35% | |
| H125: pace's gain clear | 15% | |
| The spread: the SD of EPA a play in 15+ mph wind differs from calm by 3%+ | 50% | about −2% (−6% to +2%) |
| Method 3: team slopes repeat (split-half r above 0, clear) for pass rate over expected | 30% | r about 0.1 (−0.1 to 0.3) |
| Method 3: the slopes forecast bad-weather games (clear) | 10% | |
| Method 3: QB slopes repeat | 20% | |
| The forecast against observed: wind's correlation 0.8+ | 75% | 0.85 (0.7 to 0.93) |
| The forecast against observed: wind's mean miss 3 mph or less | 60% | 2.5 mph (1.5 to 4) |

## Results

*Not run yet.*
