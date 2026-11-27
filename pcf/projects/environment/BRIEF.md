# Environment: the conditions a game is played in

> **Status:** kickoff, 2026-11-27 (the CEO: "Ok let's kick off the environment expert"). The usual way and two analogies are below, with what we already know. Next: the CEO's hunches, word for word, with their odds; then Claude's odds beside each, and two or three ways to test them (one exploratory).

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

*Waiting for the CEO.*
