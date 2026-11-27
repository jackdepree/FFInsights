# Environment: the conditions a game is played in

> **Status:** kickoff, 2026-11-27 (the CEO: "Ok let's kick off the environment expert"). The usual way and two analogies are below, with what we already know. The CEO's hunches H123-H127 are in, word for word (2026-11-27), with Claude's odds; the CEO's odds for H123-H126 came with them, and H127 has none yet. The CEO signed off on Open-Meteo (or another free source of forecasts) as a new source. The CEO's odds for H127 came 2026-11-27 (60%, on their own wording), and the CEO picked all three ways to test ("Use all three methods to test please"). The exploration is pre-registered in `EXPLORATION.md`, and it ran 2026-11-27: **GO** (its Results). The CEO closed H123-H127 as proposed (2026-11-27: "Close h123-h127"; H123 held, H124-H127 failed), added H128, and set the brief's scope: "Brief should be around totals and the play mix and the wind bet." **The brief is drafted below** ("The brief"), with four open questions for the CEO before it's agreed.

## Why now

- **Two projects wait on it.** `kicker-dst` and the `game-simulator` list it in `depends_on`, and it depends only on things already built (grain tables, the harness).
- **The schedule's facts are already clean** (`pcf.data.tables.games`): roof, surface, stadium, each team's rest days, and game-time temperature and wind. The tag tables already have "primetime", "4 or fewer days of rest", "13 or more days of rest" and "a cold or windy game".
- **Nothing in PCF reads the conditions yet,** apart from Elo's league-wide home edge. Elo's results list "weather, travel and rest days" under what it didn't look at.

## The usual way

- **Betting markets and analytics sites treat the environment as a few additive adjustments** to a game's spread and total, and to players' projections:
  - **home field:** about 2.5 points historically, nearer 1.5 since 2020;
  - **wind** (15+ mph) lowers totals, passing and kicking;
  - **cold and rain:** smaller effects, mostly through the wind and the ball;
  - **a dome team playing outdoors late in the season;**
  - **rest:** an edge after a bye; a cost on a short week (Thursday games);
  - **travel:** the body clock, such as a western team's 1 PM kickoff in the east;
  - **altitude** in Denver.
- **Each adjustment is usually fit on its own** as an average over past games, then added to a team or player baseline.
- **The market prices most of it before kickoff.** Wind is the one input bettors still argue moves totals after the line opens. So the edge, if there is one, is in the size and the interactions, not the direction.
- **Surface comes up mostly in injury research** (more lower-body injuries on artificial turf, from the NFL Players Association's case for grass) and a little in speed. It rarely shows up in game forecasts.

## Two analogies

- **Agronomy: genotype by environment (G×E).** A crop variety's yield depends on the field and the season, so seed companies trial every variety across many sites.
  - **The trials separate a variety's own merit from the site's.** Here, that's a team's or player's level, separate from the conditions.
  - **Some varieties are stable across environments; others respond to them.** Some teams or players may be "weather-proof", while others fall apart in the wind. That's a trait to test, the same way stabilization tests whether a rate repeats.
  - **An average effect across varieties can hide opposite responses.** One wind effect for the league may hide passing teams that lose a lot and running teams that lose nothing.
- **Athletics: wind-assisted and altitude marks.** A 100 m time with more than 2.0 m/s of tailwind doesn't count for records, and marks set at altitude carry a note. The sport corrects performances for the conditions before comparing them.
  - **Correct the past, not just the future.** A receiver's yards in a windy game, or a kicker's misses in Denver, say less about him. Environment's outputs could correct other experts' history before they read it, as well as forecast the next game.
  - **Conditions matter most at the margins.** Wind changes a 50-yard kick far more than an extra point, and a deep pass more than a screen. So effects may live in particular plays, not in game totals.

## What we already have

**Findings:**
- **F136 (I192, retro 5):** travel and the body clock add nothing beside Elo. That covers hours crossed, a western team's early kickoff in the east, and short rest after travel. The gain was −0.34% of the margin's squared error (−0.73% to +0.05%), on 2016-2024.
- **F131 (H5, the CEO's, failed):** beyond Elo's league-wide home edge, no team's home gap repeats, and no team-by-condition term adds.
- **tag-tables#F9:** weather is known only after the game. The schedule has game-time readings, not forecasts, so an in-season forecast can't use them as they are (rule c).
- **tag-tables#F15:** the readings exist for only 54% of 2022's outdoor games and 79% of 2023's (95-99% in other seasons).
- **data-layer#F9:** a few `roof` values are blank and get nulled.
- **elo#F12:** the final week's gap to the close is rested starters (a "rest" of a different kind).

**Data:**
- **The schedule** (1999 on): roof, surface, stadium, rest days, kickoff time, and game-time temperature and wind.
- **Play-by-play:** the play-level outcomes the conditions might touch (pass depth, kicks by distance, fumbles).
- **Open-Meteo** is already listed in `docs/DATA_SOURCES.md` (tier 3, free, no key, "to explore") for weather forecasts and history. It isn't connected yet.

**The ideas that fit** (`NIGHT_BATCHES.md` has their homes):
- **I56** (N4): teams run more after a bye: 1.4 more runs and 1.0 fewer dropbacks than pace forecast.
- **I11** (N1): players coming off a bye are over-forecast for snaps by 0.7 points of share.
- **I8** (N11): ECR under-projects players at home by about 0.3 points.
- **I192** was killed in retro 5 (F136).

## What it would deliver (a sketch, for the CEO to change)

For every game, known before kickoff:
- the conditions: the expected wind, temperature and rain, the roof and surface, each team's rest, travel and body clock, and altitude;
- how much they move the game's total, margin and pace;
- how much they move each side's passing, rushing and kicking, as inputs for the experts and products above it.

It updates between games (in season) and serves `kicker-dst`, the `game-simulator` and the yardstick.

## The CEO's direction and hunches (word for word, before any test)

**The CEO, 2026-11-27:** "I think all of those conditions matter, wind, cold, rain, dome, surface, rest between games, and altitude and prime time. I would be 80% confident that a t-test or another simple test would find significant results from at least three of those conditions. I would also be 70% confident that roles and archetypes reduce error to a significant degree for rain and wind on passing and rushing and pressure and defensive outcomes. I would also be 70% confident that roles and archetypes reduce error for pace and possibly even schemes under specific conditions like rain and wind and temperature. We should definitely use open meteo as our source or another source that can give us forecasts of weather before hand. I am 30% confident that home field advantage has mixed effects when paired with weather conditions. I think the largest effects will be found in pace, passing volume, variance in play outcomes, and game totals."

**The CEO's data decision (sign-off for a new source, 2026-11-27):** Open-Meteo, or another free source of forecasts issued before the game. It's already listed in `docs/DATA_SOURCES.md` (tier 3, no key). The exploration checks how far back its archive of issued forecasts goes. For earlier seasons, the observed weather (its history) stands in for a forecast, and the gap between the two is measured on the seasons that have both. A technical call for rule c, for the CEO's veto.

### The hunches (the CEO's odds; the wording "as read" is Claude's, for the CEO to confirm or edit)

**The conditions, as read for every hunch:**
- wind (mph) and cold (temperature): Open-Meteo, at kickoff;
- rain: Open-Meteo's precipitation, checked against the play-by-play's weather text;
- dome: the roof (dome or closed);
- surface: artificial turf or grass;
- rest between games: days since each team's last game, with byes and short weeks flagged;
- altitude: Denver's home games;
- prime time: night and stand-alone kickoffs.

"Significant" or "clearly" means a 90% interval clear of 0, games (or players) resampled. Where many conditions and outcomes are tested at once, the false-discovery rate is held at 5%.

| # | The claim, as read | The CEO's odds | Claude's odds (the exact claim first) |
|---|---|---|---|
| **H123** | **The conditions matter:** a simple test (a t-test, or a regression with nothing else in it) finds clear effects for at least 3 of the 8 conditions. The outcomes tested are pace, passing volume, rushing volume, the spread of play outcomes, EPA per play, game totals and kicking | 80% | **95%.** Twenty-five seasons is about 6,700 games, and wind, the roof and cold move passing and totals in every study of them. **Side bets:** (a) at least 3 conditions stay clear beside the obvious inputs, both teams' strength and the closing total (which already prices the weather): **35%**. (b) At least one condition improves a forecast of total points beyond the closing total, out of sample: **15%**. **Size:** 15+ mph wind lowers the total by about 3 points raw (80% between 1.5 and 5), and by about 0.5 beyond the closing total (80% between 0 and 1.5) |
| **H124** | **Roles under rain and wind:** adding the role table's coordinates (roles-archetypes, summed to each side), and their interactions with rain and wind, to a model of passing, rushing, pressure and defensive outcomes clearly reduces the held-out error, beyond the conditions' average effects | 70% | **10%** for all four kinds of outcome, as worded. **Side:** **35%** for at least one, most likely pass depth (deep threats should lose more in the wind). Bad-weather games are few (15+ mph wind in about a tenth of outdoor games), and F131 found team-by-condition terms don't repeat. **Size** where it pays: 0.2-1% of the outcome's error, on bad-weather games only |
| **H125** | **Roles and schemes for pace in the conditions:** the role table's coordinates, and possibly schemes (schemes-v2's team tendencies), clearly reduce the error of a pace forecast (seconds a play, plays a game) in rain, wind and temperature, beyond the conditions' average effect | 70% | **15%.** Pace is a team outcome that pace's expert already forecasts well, and roles are a player-level table. **Side:** **30%** that a team's scheme tendencies (pass rate over expected, shotgun) change in the wind and rain by more than the league's average change, as a trait that repeats (split halves) |
| **H126** | **Home field mixes with the weather:** the home edge grows in some conditions and shrinks in others (for example, a cold-weather home team in a cold game; a dome team's edge outdoors), clearly, beyond Elo's league-wide home edge | 30% | **20%.** F131 found no team's home gap repeats, and F136 found travel adds nothing. **Side:** **30%** that cold-weather home teams against dome or warm-weather visitors, in games under 40°F, beat Elo's margin forecast by a point or more in sample; **10%** that it holds out of sample |
| **H127** | **Where the largest effects are.** The CEO's bet, as they set its odds (2026-11-27: "H127; 60% that the largest effect is not margin or interception rate or sack rate or yards per play"): ranked by the share of each outcome's variation the conditions explain, the outcome with the largest is none of margin, interception rate, sack rate or yards per play. Their first wording named pace, passing volume, the spread of play outcomes and game totals as the largest | 60% (the CEO, 2026-11-27, before any test) | **85%** for the CEO's bet as they set its odds: totals, passing volume and kicking should all beat those four. **Side bets on the first wording:** **20%** that pace, passing volume, the spread of play outcomes and game totals are exactly the top four; **55%** that at least three of them are. Kicking accuracy is the likeliest to beat them, through the wind on long kicks |

### Three ways to test (one exploratory; the CEO picks, or brings another)

1. **Simple tests, then the obvious inputs (the usual way).** Game by game, each condition against each outcome: t-tests and plain regressions, with the false-discovery rate held across them.
   - Then the same beside both teams' strength (Elo) and the closing spread and total. nflverse's schedule has both lines from 1999.
   - Then a walk-forward forecast beside them.
   - **Tests:** H123, H126, H127.
   - **Assumes** each condition's effect is the same size everywhere and adds to the others.
   - **Cost:** under an hour, once the weather is joined.
2. **Play-level interactions with roles (structured).** A play model in context's style (pass depth, completion, pressure, run success) with the conditions, and their interactions with the role table's coordinates and schemes' tendencies, walk-forward, against the conditions alone.
   - A distributional model (one that forecasts both the middle and the spread) for the spread of play outcomes.
   - **Tests:** H124, H125, and the spread part of H127.
   - **Assumes** there are enough bad-weather plays for the interactions.
   - **Cost:** a session.
3. **Exploratory: agronomy's stability analysis (Finlay-Wilkinson regression).** Give every game an environment index: the league's average outcome in those conditions. Regress each team's (and each player's) outcome on the index, and read the slope as his sensitivity: 1 is average, below 1 is weather-proof, above 1 is fragile.
   - It tests whether the slopes repeat (split halves, across seasons), and whether they forecast bad-weather games beyond the average effect.
   - **Tests:** who the effect belongs to, in H124-H126.
   - **Assumes** one index sums up the conditions, and the response to it is a straight line.
   - **Cost:** under an hour.

## After the exploration (2026-11-27: go; `EXPLORATION.md`, Results)

**What it found, in one line each:**
- **Weather is a small tax that repeats.** The conditions explain at most 1.9% of any outcome, but the odd-season and even-season models agree at 0.83-0.95.
- **The tax falls on yards a play, totals and points, and the play mix.** Wind and rain cost 1-2 dropbacks and add about 1 run a team. Pace, sacks, interceptions and margin don't move.
- **The closing total charges only about half of wind's cost.** Beside it, the leftover is −0.25 points a mph (t −5.1), largest in 2016-2024, and the forecast wind agrees on 2022-2024. Walk-forward, +0.70% of the total's squared error (−0.05% to +1.36%): just short of clear.
- **Nobody is weather-proof.** Team and QB sensitivities don't repeat, and roles × weather add only noise (H124, H125).
- **Field goals barely move** beside distance (+0.43% of make or miss). They stay with `kicker-dst`.
- **The cold mix** (a cold-weather home team against a dome or warm visitor under 40°F) beats the close by +4.6 points in sample, and adds nothing out of sample.
- **The CEO closed H123-H127 on 2026-11-27, as proposed** ("Close h123-h127"): H123 held; H124-H127 failed.
- **The forecast tracks the observed weather** for wind (r 0.85, a 1.85 mph mean miss) and temperature (r 0.99), not rain (r 0.46).

## The CEO's direction for the brief (2026-11-27, word for word)

"Close h123-h127. I still expect some teams to fair better than other based on roles or schemes, but I do not believe some teams to be weather-proof. Brief should be around totals and the play mix and the wind bet."

- **Scope:** totals, the play mix and the wind bet.
- **A new hunch, H128** (`HUNCHES.md`): roles and schemes decide who fares better in the weather, as a matchup, not a weather-proof team. The CEO's odds are asked; Claude's are 15% for the claim as read. The build tests it.

## What we expect (W16, written 2026-11-27 for the build; the hunches came first)

**The frame: weather is a sales tax, and the market undercharges it on windy days.**
- **The tax:** the same cut from every team in the same conditions, set league-wide, with no team rates (method 3 and H124-H125 say a team's own rate is noise).
- **Where it's charged:** yards a play, points and the total, and the play mix (fewer dropbacks, more runs).
- **The undercharge:** the closing total already prices about half of wind's cost. The other half is the wind bet.
- **The CEO's H128 is the one place a matchup could show:** a run-heavy side may lose less than a pass-heavy one in the same wind. It's a difference between two teams, not a team's own sensitivity, so it isn't the same test as method 3.
- **Where it sits:**
  - **It feeds:** the yardstick's team passing and rushing yards boards, pace's play mix (not its clock), the game simulator's totals, and the betting products' totals.
  - **It overlaps:** the closing total (which prices most of it), pace's previous-8 habits, and Elo's home edge.
  - **It shouldn't redo:** travel and the body clock (F136), a team's own home gap (F131), team or QB weather sensitivities (method 3), or field goals by distance (`kicker-dst`).

**The results we expect from the build** (Claude's, a middle and an 80% range, W15):
- **Totals beside the closing total**, walk-forward 2016-2024: about +0.7% of the squared error, 80% between 0 and +1.4%. Clear (the interval above 0): 45%.
- **With the forecast in place of the observed weather** (2022-2024): about 80% of the observed weather's gain (80% between 40% and 110%).
- **The play mix beside the previous-8 means**, on bad-weather games: dropbacks about +1.0% of the squared error (80% +0.3% to +2%), runs about +0.8% (80% +0.2% to +1.5%), pass rate over expected about +1.5% (80% +0.5% to +2.5%). On all games about a fifth of that.
- **The ladder:** the nonlinear wind rung (bands) ties the straight line (70%), so the straight line ships (rule k). The trees tie or lose (85%).
- **The wind bet** (I194), 2016-2024: the under, when the model's total sits 1.5+ points below the close, wins about 55% of about 120 bets (80% between 48% and 61%). Too few bets to be clear (the break-even at −110 is 52.4%).
- **H128:** 15% clear on the margin beside the close; I195 (the cold mix): 20%.
- **Downstream, on the yardstick's team yards boards:** about +0.2% (80% 0 to +0.5%), almost all on bad-weather games.
- **Ranges:** the total's 80% range covers 75-85% of games, outdoors and in domes alike.

Anything else the build finds goes in its report in detail. What matches this gets one line.

## The brief (draft 2026-11-27, for the CEO to agree)

The build starts from this section, `EXPLORATION.md` (its Results and the technical calls) and the registry, and nothing else. It runs at night in the build session.

### The question

For every game, before kickoff, from the forecast:
- how much do the conditions move the game's total and each team's points?
- how much do they move each side's play mix: dropbacks, runs and pass rate over expected?
- how much of that does the closing total leave unpriced (the wind bet)?

### Why it matters

- **Totals are a betting product,** and wind is the one input the exploration found the market undercharges. If the build confirms it, it's PCF's first edge against a closing line from a condition, not a team rating.
- **The play mix feeds the yardstick's team yards boards** and every passing and rushing projection above them: a windy game moves passing yards into rushing yards before any player is read.
- **`kicker-dst` and the game simulator** list environment in `depends_on`. This build gives them the conditions and the totals shift, saved and versioned.

### Terms

- **The conditions:** wind (mph at 10 m), cold (50°F less the temperature, 0 when warmer), precipitation (inches an hour, rain or snow), dome (dome or closed roof; its weather is set calm, dry and 70°F), turf, short rest (5 days or fewer), long rest (13 or more), altitude (over 1,000 m) and prime time (7 PM Eastern or later, or not on a Sunday).
- **The forecast weather:** Open-Meteo's forecast for the stadium, averaged over the three hours from kickoff. **The observed weather:** its archive (ERA5) for the same hours, the stand-in before 2022.
- **The tax:** the conditions' league-wide shift on an outcome against a calm, dry, mild outdoor game, in the outcome's units (points, dropbacks).
- **Beyond the close:** the total less the closing total. The wind bet forecasts it.
- **A bad-weather game:** outdoors with 10+ mph wind, 0.02+ inches an hour, or 40°F or colder.
- **The play mix:** a team-game's dropbacks, runs and pass rate over expected.

### Builds on

- **The exploration:** the conditions table, the weather window, the stand-in, and the results (the tax repeats, pace doesn't move, wind beyond the close, no sensitivities).
- **Findings:** F131 (no team home gaps), F136 (travel adds nothing), tag-tables#F9 and F15 (the schedule's readings are post-game and patchy, so the build reads Open-Meteo).
- **Code:** `explore/env_common.py` (the weather join, the game and team-game tables), `env_fetch_weather.py` (the batched Open-Meteo client) and `env_m1.py` (the walk-forward beside the close). The logic moves into the package; the scripts stay as exploration.
- **Pace's previous-8 habits** for the play mix, and the schedule's closing spread and total.
- **Already tried, not to redo:** roles × weather on plays (H124), roles and tendencies × weather on pace (H125), Finlay-Wilkinson slopes for teams and QBs (method 3), home × weather beyond Elo (H126), travel (F136).

### Assumptions

- **The observed weather stands in for the forecast before 2022** (a technical call, rule c). The build scores 2022-2024 with the forecast too, and reports both. Every live forecast uses the forecast issued before kickoff.
- **Open-Meteo's archived forecasts are short-lead** (each run's first hours, stitched). A forecast read the morning of the game may miss more. The build reports the gain's sensitivity to the miss by adding the 2022-2024 forecast's own error to the observed weather.
- **The tax is league-wide and adds up.** Interactions are tested only where named (wind × rain, wind bands, H128's matchup).
- **The close is nflverse's consensus close.** Odds-collection holds other books' lines from 2022 on (ESPN's backfill); where both exist, the build reports the wind leftover against each.
- **Retractable roofs follow the schedule's `roof`.** Wrong rows are a stated limit.

### Goals and the ladder (rule k: a tie goes to the simpler rung)

**Totals** (the game total less the closing total, and each team's points):
1. **The baseline:** the closing total (and each team's implied points from the spread and total).
2. **The linear tax:** every condition, league-wide, fit on earlier seasons.
3. **Wind's shape:** wind in bands (under 10, 10-15, 15-20, 20+) and wind × rain, against the straight line.
4. **Trees, once, as the check**, on the same inputs. They ship only if they beat the rung below clearly.
5. **Ranges:** the total's distribution given the shipped rung (a normal around it with a variance that can depend on the conditions, against a constant one), with q10, q50 and q90.

**The play mix** (dropbacks, runs, pass rate over expected, per team-game):
1. **The baseline:** the team's and opponent's previous-8 means and the closing spread and total.
2. **The linear tax** on top, then wind's shape and the trees as above.
3. **Ranges** the same way.

**H128, the matchup** (on the shipped rungs): both sides' last-season pass rate over expected and role mix, as the difference between the teams, × wind and rain, on the margin beside the closing spread and on each side's play mix. Walk-forward, scored on bad-weather games.

**Not built:** team or player sensitivities, pace (plays and seconds a play), sacks, interceptions, field goals, travel and the body clock.

### Tests (walk-forward; test seasons 2016-2024; the earlier-seasons check on 2008-2015, W14; the 2025 vault once, at the end)

- **The expert's bar:**
  - the shipped tax beats the baseline and a shuffled-weather null (each game's conditions shuffled among games in the same month and roof, 19 copies), weeks resampled;
  - each rung is kept only where it beats the rung below clearly (a 90% interval clear of 0);
  - no rung adds noise.
- **The no-noise target (for the CEO to approve):** the game total's squared error beside the closing total, 2016-2024. The play mix's squared error beside the previous-8 means is the second target.
- **The wind bet (I194):**
  - the gain beside the close, on all games and on 15+ mph forecast games;
  - the under's record when the forecast total sits 1.5+ points below the close, against 52.4% (−110), with its interval. Discovery only: there are too few bets to prove an edge, and no closing line value without an earlier line;
  - 2022-2024 with the forecast, and against odds-collection's collected closes where they exist.
- **Gains per season** (W13): every rung's gain for each test season, in a small table.
- **Ranges:** the total's 80% coverage within 75-85%, outdoors and in domes, and on 15+ mph games.
- **Downstream:** the play mix as an input to the yardstick's team passing and rushing yards boards, against 19 copies.
- **Football sanity:** the tax in plain units (points in 20 mph wind, dropbacks in rain) read against the folk numbers.
- **Ideas tested in the build** (W17; odds in `IDEAS.md`): **I194** (the wind bet), **I195** (the cold mix beside the close and Elo), and the CEO's **H128**.
- **Leakage:** every model's checks run (rule c). The vault uses only forecast weather.

### Inputs and outputs

- **Cadence: in season** (rule m). It updates before each game from the forecast.
- **Inputs:**
  - the schedule (roof, surface, stadium, rest, kickoff, the closing spread and total);
  - Open-Meteo: the archive (observed) and the historical forecast API, by stadium and kickoff (known at the forecast's issue time);
  - pace's team-game table and previous-8 habits;
  - the role table's history and schemes' tendencies from the season before (for H128 only).
- **Outputs, saved as walk-forward history in the standard schema, known before kickoff:**
  - **game:** the conditions; the tax on the total (points, with q10, q50 and q90); the total beyond the close (the wind bet's number);
  - **team-game:** the tax on points, dropbacks, runs and pass rate over expected, each with q10, q50 and q90.
- **Live forecasts:** a small Open-Meteo step in the collector (`collect-odds.yml`, or the PC fallback) saves each game's forecast the morning of the game into `pcf-data`, from 2026's remaining weeks on. Open-Meteo has no key and the step costs no credits.

### How it will be used

- As the totals shift and the wind bet for the betting products and the prediction ledger.
- As the play mix shift for the yardstick's team yards boards, pace's forecast and player projections.
- As the conditions and the totals shift for `kicker-dst` and the game simulator.

### Plan

- One night's build: the package module (the Open-Meteo client, the conditions table, the two ladders, the ranges), the ideas (I194, I195, H128), the earlier-seasons check, then the vault. Then RESULTS.md with "Against the frame", the findings, the case against, the interface card and the CEO's open questions.
- The live forecast step goes in a separate small commit, after the CEO sees it (it touches the collector that runs on GitHub).
- The morning: the CEO's spot-check and the merge.

## Open questions for the CEO (before the brief is agreed)

1. **The no-noise target:** the game total's squared error beside the closing total (2016-2024), with the play mix beside the previous-8 means second. Approve, or change?
2. **Yards a play:** the exploration's largest effect, and it feeds the yardstick's yards boards. Add it to the team-game outputs? (It costs nothing extra.)
3. **H128's odds:** your confidence that roles or schemes make some teams fare better than their opponents in bad weather (beside the closing spread, out of sample).
4. **The live forecast step** in the collector: yes now, or after the build?
