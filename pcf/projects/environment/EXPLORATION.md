# Environment: exploration

> **Status:** pre-registered 2026-11-27, before any result; run the same day (Results, at the end): **GO**. The CEO picked all three ways to test (2026-11-27: "Use all three methods to test please"). The weather fetch from Open-Meteo is running (the CEO's sign-off, 2026-11-27). Discovery only: 1999-2024, and the 2025 vault stays closed.

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

## Results (2026-11-27)

> **Run:** `explore/env_m1.py` (the noise ceiling and method 1), `env_m2.py` (method 2), `env_m3.py` (method 3), each writing a `.txt` beside it. **Written after the run, and disclosed:** `env_m1_checks.py` (three checks on what went against the frame; they don't change any verdict); a bug fix in method 2's H125 (the previous season's tendencies were built after the 2017 filter, so 2017's rows had none; fixed and rerun, and the numbers barely moved); and a second run of method 2 with the ridge penalty tuned on the last training season (`--tuned`, `env_m2_tuned.txt`), to check the loss wasn't a badly set penalty. No verdict changes between the runs; the numbers below are the tuned run's where they differ.

**The data:** 6,695 regular-season games 1999-2024; 5,053 outdoor or open with weather; 12,894 team-games 2000-2024. Of outdoor games, 6.0% had 15+ mph wind, 5.8% were 32°F or colder, 6.7% had rain or snow. Open-Meteo's wind against the schedule's game-time reading: r 0.67; temperature r 0.97 (4,804 games).

### The noise ceiling

**The room is small but real.** The conditions explain at most 1.9% of any outcome's variation, and the trees find no more than the linear model (they do worse on totals and margin, from overfitting 6,447 games). But where they explain anything, it repeats: the odd-season and even-season models' predictions correlate at 0.83-0.95 for every outcome in the top seven. Plays a game (r 0.27) and sack rate (r −0.04) have no room at all.

| Outcome | Linear share, out of fold | Trees' share (5 seeds) | Split halves r |
|---|---|---|---|
| yards a play | +1.92% | +1.44% (+1.29% to +1.70%) | 0.95 |
| game total points | +1.79% | +0.37% | 0.87 |
| pass rate over expected | +1.25% | +1.18% | 0.95 |
| points scored | +0.85% | +0.71% | 0.87 |
| EPA a play | +0.45% | +0.29% | 0.83 |
| spread of play outcomes (SD of EPA) | +0.44% | +0.19% | 0.75 |
| runs | +0.44% | +0.24% | 0.94 |
| dropbacks | +0.27% | +0.31% | 0.88 |
| field goal make rate | +0.25% | −0.60% | 0.74 |
| home margin | +0.06% | −1.94% | 0.87 |
| interception rate | +0.02% | −0.21% | 0.53 |
| seconds a play | −0.09% | −0.22% | 0.47 |
| plays a game | −0.12% | −0.10% | 0.27 |
| sack rate | −0.13% | −0.05% | −0.04 |

### Against the frame (in detail)

**1. The closing total under-prices wind, by about half.**
- **What we expected:** the market reads the forecast, so the conditions' leftover beside the closing total is 0.5 points or less, and a walk-forward gain is about +0.1% (−0.2% to +0.5%).
- **What we found:**
  - Games in 15+ mph wind score 4.59 fewer points than calm games, but the closing total sits only 2.07 lower. The total lands about 2.5 points under the close.
  - Beside the close, the leftover is −0.25 points for every mph of wind (robust t −5.1). Rain leaves one too: −35 points an inch an hour (t −2.8), so about −1.8 points at a steady 0.05 in/h. Domes leave −1.5 (t −2.6).
  - **It isn't fading:**

    | Seasons | 15+ mph games | Their total less the close, against calm games' |
    |---|---|---|
    | 1999-2007 | 92 | −2.45 (±2.63) |
    | 2008-2015 | 68 | −0.52 (±3.10) |
    | 2016-2024 | 131 | −3.49 (±1.77) |

  - **With the forecast in place of the observed wind** (2022-2024): −0.231 points a mph, against −0.262 with the observed wind. The forecast flags only 16 games at 15+ mph, so this is thin, but it points the same way.
- **Out of sample (side bet b):** walk-forward 2016-2024, the conditions beside the closing total remove +0.70% of the total's squared error (90%: −0.05% to +1.36%; 2,367 games). That's above Claude's range, but the interval just reaches 0, so the pre-registered rule says **failed**.
- **What it means:** the tax is real, and the market charges only about half of it in wind. Against the frame's "most of the tax is in the closing total", this is the result to build on (I194). The case against is below: the forecast is short-lead, and the sample is about 130 windy games a decade.

**2. Pace doesn't move. The weather changes what teams call, not how fast they play.**
- Plays a game and seconds a play explain nothing (−0.12%, −0.09%), and their split halves barely repeat. In wind and rain, teams drop back 1-2 fewer times and run about 1 more (the t-tests), at the same tempo.
- This is against the CEO's first wording of H127 (pace among the largest), and it left H125's pace half little to win: there's no average effect for roles to sharpen.

**3. The largest effect is yards a play, by a coin flip over game totals.**
- **What we expected:** field goal accuracy or game totals on top.
- **What we found:** yards a play +1.92% against game totals +1.79%. With seasons resampled, yards a play is ahead by +0.10 points (90%: −0.48 to +0.69), in 61% of resamples. A tie, but the pre-registered rule reads the top row, so the CEO's H127 (as the CEO set its odds) **failed**, and so did Claude's 85%.
- **Field goals are smaller than the frame said.** Kick by kick (25,555 kicks), distance explains 11.4% of make or miss, and the conditions add +0.43% beside it. From 50+ yards outdoors, kickers made 57.7% in 15+ mph wind (104 kicks) against 60.2% under 10 mph (1,893). Coaches seem to choose their kicks in wind: there are few long tries left to miss.

**4. The conditions stay beside the obvious inputs (side bet a held, against Claude's 35%).** With every condition together, beside both teams' previous-8 means and the closing spread and total, 6 of 8 conditions keep at least one outcome at a 5% false-discovery rate: wind, cold, rain, dome, rest and prime time. Most of what survives is the play mix (dropbacks, pass rate over expected, runs), which the lines don't price directly. Long rest's survivor is −0.85 dropbacks after 13+ days, the same sign as I56 (teams run more after a bye; it stays in night batch N4).

**5. The cold mix: a home edge in sample, not out of it (H126).**
- A cold-weather home team against a dome or warm-climate visitor under 40°F beats the closing spread by +4.62 points (t +2.8; 116 games, 2000-2024) and Elo's margin by +2.21 (t +1.1; 48 games, 2016-2024).
- Out of sample it adds nothing: −0.05% of the margin's squared error beside Elo (−0.38% to +0.32%), and −0.01% beside the close.
- Eight terms were tested across H126's two fits, plus the checks; one t of 2.8 among them by chance is about a 1-in-25 event, uncorrected. Worth one cheap look in the build (I195), no more.

### What matched (one line each)

- **H123:** 7 of 8 conditions have an outcome that survives the simple tests (all but altitude; long rest has none, short rest has three). 15+ mph wind costs −4.59 points on the total raw (Claude's range −1.5 to −5).
- **Wind's dropbacks:** −1.96 a team (range 0 to −4).
- **The roof:** dome games total +3.63 points raw, +1.81 a team; just above Claude's +0.5 to +3.5 for the game.
- **H124 failed:** roles × wind and rain add only noise on every kind (0 of 4 clear; −0.03% to −0.22% on bad-weather plays, tuned or not).
- **H125 failed:** roles and tendencies × conditions lose on bad-weather games: plays −3.6%, seconds a play −8.2%, pass rate over expected −5.1%, shotgun rate −18.3%. Shotgun's league rate rose from 55% to 69% over 2017-2024, which may be why its loss is the largest (untested).
- **The spread of play outcomes:** 2.5% narrower in 15+ mph wind than calm (−4.4% to −0.5%), inside Claude's range; it misses the 3% bar. Rain −1.7%, cold −1.4%, neither clear. Wind narrows the outcomes: fewer deep shots, more runs.
- **Method 3, weather-proof teams:** sensitivities don't repeat (split halves r −0.06 to +0.05; next block −0.05 to +0.10) and they make forecasts worse (−0.2% to −2.0% on bad-weather games). QBs: r +0.04 on EPA a pass play, +0.16 on air yards (−0.09 to +0.39), neither clear. **The tax falls the same on everyone.**
- **The forecast against observed** (556 outdoor games, 2022-2024): wind r 0.85, mean miss 1.85 mph, the 15+ mph flags agree 95%; temperature r 0.99. Rain is poor: r 0.46. Open-Meteo's archive of forecasts stitches each run's first hours, so this is a short-lead forecast.

### The odds, scored

| Test | Odds (Claude) | Result | Size in Claude's range? |
|---|---|---|---|
| H123, 3+ conditions | 95% (CEO 80%) | **held**, 7 of 8 | yes (−4.59) |
| Side a, 3+ beside the obvious inputs | 35% | **held**, 6 of 8 | |
| Side b, beyond the close out of sample | 15% | failed: +0.70% (−0.05% to +1.36%) | no, above |
| H127, the CEO's wording | 85% (CEO 60%) | failed: yards a play on top, by a tie | |
| H127, exactly the CEO's four | 20% | failed | |
| H127, 3+ of the four | 55% | failed: 1 of 4 (game totals; pass rate over expected, 3rd, is the mix, not volume) | |
| H126, beyond Elo | 20% (CEO 30%) | failed: −0.05% | yes |
| H126 side, the cold mix by a point in sample | 30% | **held**: +2.21 beside Elo, +4.62 beside the close | |
| H126 side, out of sample | 10% | failed | |
| H124 as worded | 10% (CEO 70%) | failed: 0 of 4 | no (no gain) |
| H124, any one kind | 35% | failed | |
| H125, pace | 15% (CEO 70%) | failed | |
| The spread, 3%+ | 50% | failed: −2.5% | yes |
| Method 3, team slopes repeat | 30% | failed: r −0.04 | yes |
| Method 3, slopes forecast | 10% | failed | |
| Method 3, QB slopes repeat | 20% | failed | |
| Forecast wind r 0.8+ | 75% | **held**: 0.85 | yes |
| Forecast wind miss 3 mph or less | 60% | **held**: 1.85 | yes |

Claude's bets at 40% or lower: 2 of 12 came true (side a and the cold-mix side). Both surprises point the same way: the conditions carry more beside the obvious inputs than expected.

### The case against

- **The observed weather stands in for the forecast before 2022.** The market priced the forecast; we measure what happened. Part of wind's leftover may be wind the forecast didn't see. The 2022-2024 check with the forecast agrees (−0.23 a mph), but it's 16 windy games and a short-lead forecast.
- **Few windy games.** 291 games at 15+ mph in 26 seasons, 131 since 2016. A team or two going under in a blizzard moves the mean by a point.
- **The close here is nflverse's**, a consensus close, not FanDuel's. A sharp book may already price wind fully. "Bet the under in wind" is old betting folklore, so a market that ignores it for 25 years is suspicious.
- **Many tests.** Method 1's t-tests and regressions are corrected (Benjamini-Hochberg), but H126's terms and the checks after the run are not.
- **The weather window is the three hours from the UTC kickoff, at the stadium's coordinates.** A retractable roof's state comes from the schedule's `roof`, which can be wrong for a game.
- **The ranking depends on the model.** The linear model puts totals at +1.79% and the trees at +0.37%; the top two are a tie either way.

### Go / no-go: **GO**

There is signal, small and stable. What a build should carry:
- **A league-wide tax,** not team or player sensitivities. Method 3 and H124-H125 say the slopes are noise, and rule k gives every tie to the simpler side.
- **The outcomes it moves:** yards a play, totals and points, the play mix (dropbacks, runs, pass rate over expected), and the spread of play outcomes. Not pace, sacks, interceptions or margin.
- **Feeds:** the yardstick's totals and passing boards, pace's mix (not its clock), kicker-dst (small), the game simulator.
- **The betting test:** wind and rain beyond the closing total, scored with the forecast issued before the close (I194). Saving Open-Meteo's forecast before each 2026 game would make a clean test set, a job for odds-collection's workflow.

### Ideas from this exploration (homes in `NIGHT_BATCHES.md`, W17)

- **I194:** wind and rain beyond the closing total, as a betting input. Home: environment's build.
- **I195:** the cold mix beyond the close and Elo. Home: environment's build.

### Proposed hunch verdicts (the CEO closes them)

| Hunch | Proposed | Real? | Pays? |
|---|---|---|---|
| H123 | **held** | yes: 7 of 8 conditions, 6 beside the obvious inputs | not yet: beside the close, +0.70% on totals, just short of clear |
| H124 | **failed** | no evidence | no: −0.03% to −0.22% |
| H125 | **failed** | no: pace doesn't move with the weather | no: −3.6% to −18.3% |
| H126 | **failed** | in sample, only the cold mix (+4.6 beside the close, t 2.8) | no: −0.05% beside Elo |
| H127 | **failed**, by a tie | partly: totals 2nd and the pass mix 3rd; pace and the spread aren't | not tested for pay |
