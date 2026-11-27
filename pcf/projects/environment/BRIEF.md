# Environment: the conditions a game is played in

> **Status:** kickoff, 2026-11-27 (the CEO: "Ok let's kick off the environment expert"). The usual way and two analogies are below, with what we already know. The CEO's hunches H123-H127 are in, word for word (2026-11-27), with Claude's odds; the CEO's odds for H123-H126 came with them, and H127 has none yet. The CEO signed off on Open-Meteo (or another free source of forecasts) as a new source. Three ways to test are below, for the CEO to pick.

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
| **H127** | **Where the largest effects are:** ranked by the share of each outcome's variation the conditions explain, pace, passing volume, the spread of play outcomes and game totals come out above the other outcomes (rushing volume, EPA per play, margin, turnovers, kicking accuracy) | not given yet | **20%** that those four are exactly the top four. **Side:** **55%** that at least three of them are. Kicking accuracy is the likeliest to beat them, through the wind on long kicks |

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
