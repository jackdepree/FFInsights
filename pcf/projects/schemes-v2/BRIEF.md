# Brief: Schemes v2 (`schemes-v2`)

**Status:** draft, 2026-11-08 (kickoff; the CEO's hunches recorded, back and forth under way) · **Layer:** expert · **Cadence:** to be decided: likely two experts, in_season and retrospective (rule m; see Inputs)

## The usual way
*Claude, 2026-11-07, before any research.*
- **Charting:** analysts tag every play from film.
  - Offense: personnel (11, 12, 21), formation, shotgun or under center, motion, play-action and run-pass options, run concepts (zone or gap) and pass concepts.
  - Defense: coverage shell (one deep safety or two), man or zone, blitz rate and men in the box.
- **Tendencies:** the tags become rates in neutral situations, adjusted for what the situation expects ("pass rate over expected" is the standard).
- **Grouping:** clustering or a few axes, often labelled by coaching tree.
- **Uses:** scheme fit for players, matchups (a man-heavy defense against an offense that beats man), and what changes when a coordinator changes.

## Analogies
1. **Investment style analysis.** A fund's style can be read from what it holds, or only from how its returns move with known factors. Schemes can likewise be read from charted labels, or from the patterns they leave in results: who gets the ball, where, and when.
2. **Dialects.** Most words are shared; what differs is how often each is used. Dialects spread with people as schemes spread with coaches, so coaching trees work like language families, and a team is often a blend, not one category.
3. *(Added 2026-11-08, for H10.)* **Movers in labor economics.** To tell whether a worker's pay comes from the worker or from the firm, economists follow people who switch firms: what moves with them is theirs, and what stays is the firm's (the "movers" design). Health economists do the same with patients who move between regions, to separate a doctor's habits from a place's. H10 is this design applied to football: coaches and players who change teams.

## CEO hunches
*The CEO's words as said on 2026-11-08, before Claude's research. Each gets a verdict in [`projects/HUNCHES.md`](../HUNCHES.md).*

| # | Hunch, in short | What the usual way says | How the exploration will test it |
|---|---|---|---|
| H9 | Rock-paper-scissors: circles (A beats B, B beats C, C beats A) come either from flukes in close games or from schemes that give one team an edge over another | Matchups are a scouting talking point; models rate teams on one line (strength plus home field) | (1) Are circles more common than strength plus luck produce? (first look below). (2) The sharper test: do offense-style × defense-style pairings predict margins beyond Elo? |
| H10 | What follows a coach or coordinator to a new team is the scheme; what follows a player is their role. Schemes and roles are the consistent parts of play style | Schemes are labels from charting, often by coaching tree; roles come from usage at one team | The movers design (analogy 3): for each tendency, does it move with the play caller, the player, or stay with the roster? |
| H11 | Knowing a scheme should predict performance under conditions (for example, a team losing at halftime most likely won't come back), or predict the matchups in H9 | Scheme labels are judged by whether they look right to film people | Do scheme tendencies predict how a team does in a game state, beyond the win-probability model's expectation for that state? |

**H9.**
> "what are the core differences and patterns between teams that beat each other and simultaneously lose to each other, like rock-paper-scissors? Let me explain with an example, if team an overcomes team b, then next week team b plays team c and wins, then next week team c plays team an and beats them too. Now we have a circle of teams outperforming each other. To me, there are two explanations, either the games were really close and one or two of the games are flukes, or the schemes that each team utilizes determines which team would have an advantage over another team."

**H10.**
> "My second hunch is that schemes and roles must be consistent, but it depends on which part of play styles is consistent. Let me explain, if a player leaves one team and joins another, what tendencies and charters follow that player between teams? Those consistencies are what should be known as roles. The same goes for head coaches and coordinators, if they leave a team, what tendencies and charters follow them is what should be considered a scheme."

**H11.**
> "A successful criteria of knowing a scheme could be two things, either the same as my first hunch like rock-paper-scissors or that we can predict performance based on conditions, like if a team is losing at halftime then they will most likely not be able to come back."

**Scope and the old model (the CEO's words).**
> "This expert would definitely cover both offense and defense respectively."

> "I'm not quite sure what the old model got wrong, I think my exploration was too narrow and I ended up finding nothing reliable."

> "I do not think it necessarily should follow the same exact structure as my old model."

### First look at H9 (2026-11-08, discovery only)
[`explore/cycles.py`](explore/cycles.py), 2016–2024, 2,467 games, 4,495 triangles of teams that all played each other in a season.

| | Share of triangles that are circles |
|---|---|
| Actual | **18.1%** |
| Coin flips | 25.0% |
| Elo's win chances, games independent | 21.6% (20.7–22.6%) |
| The close's win chances, games independent | 21.4% (20.3–22.5%) |
| Elo's chances plus a hidden season strength per team, sized to match the real spread of wins | 21.2% (20.1–22.3%) |

- **Circles are *rarer* than strength plus luck predicts, not more common.** Real seasons are more ordered than any of the chance models. My expectation (about as common as chance) failed in the other direction. The likely reason: strength differences are larger, or move more within a season, than the forecasts know. That's a team-strength finding (it echoes elo#F13), not a scheme one.
- **Flukes, partly:** games inside circles are closer than games inside ordinary triangles (54% decided by 7 or fewer, against 47%; at least one game decided by 3 or fewer in 62% of circles, against 55%).
- **What it doesn't rule out:** a circle uses one bit per game (who won). A scheme edge worth a point or two would barely change who wins, so it can't show here. H9's real test is on margins (the table above, column 3, test 2).

## The question
How does each team play, on offense and on defense, in ways that belong to its play caller rather than to its players or to luck? And do those styles explain who beats whom and how teams do in particular game states?

## Why it matters
- **Matchups:** if styles interact (H9), side and total forecasts gain a term no rating has.
- **Coaching changes:** when a coordinator moves, we'd know what moves with them, the moment the hire is announced (offseason).
- **Roles:** the same design tells which player tendencies are theirs (H10), feeding `roles-archetypes`, player projections after a trade or signing, and the consistency meta process (IDEAS I20).
- **Game environments:** pace, pass rate and how a team plays when behind feed totals, fantasy and props.

## Terms
- **Standard terms used:** EPA, pass rate over expected, neutral situation, personnel, play-action, man and zone coverage (`docs/GLOSSARY.md`).
- **New terms (draft):**
  - **Tendency:** a rate in comparable situations (e.g. shotgun rate on 1st and 10 in a one-score game), adjusted for what the situation expects.
  - **Scheme:** the tendencies that move with a play caller when they change teams (H10).
  - **Role:** the tendencies that move with a player when they change teams (H10).
  - **Roster trait:** the tendencies that stay with the team when the play caller leaves.
  - **Circle:** three teams that each beat one of the others in the same season (H9).
  - **Mover:** a play caller or player who changes teams between seasons (or mid-season).

## Builds on
| Project | What we use | Why |
|---|---|---|
| `elo` | ratings in the `margin` history (decision 0021); its margin misses | Matchup effects are measured on what Elo misses; the ratings set "expected" |
| `tag-tables` | situation tags (score, clock, down and distance) | Neutral situations and game states (H11) |
| `participation` | snap shares | Which players moved, and how much they played (H10's player side) |
| `elo` H5, H6 | "strength is conditional: … against heavy zone coverage, when trailing at halftime" | H11 is H5 measured through schemes |

**Already tried:** `schemes-v1` (`old/code/Schemes_Model.ipynb`): over-expectation features, then PCA, then clustering into team schemes. Little usable signal. The exploration reads it first (read-only) to see why. CONSISTENCY.md: "finishing" repeats (r 0.28 week to week, 0.22 season to season), a candidate for H11.

## Assumptions
- **Tendencies can be measured from free data.** Play-by-play has shotgun, no-huddle, pass rate over expected, pass depth and direction (1999 on). FTN charting has play-action, motion, blitzers and men in the box (2022 on, about two weeks behind). Participation has formation, personnel, coverage and routes (2016–2025, after the season only).
- **Play callers can be identified.** nflverse has head coaches only. Coordinators and who calls plays aren't in our data (an open decision below).
- **Enough movers.** Each season perhaps 10–20 coordinators and many players change teams. Coordinators are few, so intervals will be wide.
- **A tendency is a choice, not a forced response.** Shotgun when trailing is the game state talking; neutral situations and an expected-rate adjustment are meant to remove that.

## Goals
1. A map of tendencies: which ones are consistent (CONSISTENCY.md), and whose they are (play caller, player, roster).
2. A test of matchups on margins (H9) and of game-state performance (H11).
3. Scheme features for downstream experts, saved like Elo's ratings.

## Tests
*Draft, to agree with the CEO.*
- **H9, matchups:** an offense-style × defense-style term improves held-out margin (or total) forecasts over Elo, with an interval clear of zero; the shuffled-pairings version doesn't.
- **H10, whose is it:** for each tendency, the share that moves with a play caller (and with players) across movers, with an interval. A tendency counts as **scheme** if it moves with the play caller clearly more than it stays with the roster.
- **H11, conditions:** scheme tendencies predict a team's result from a given game state (e.g. trailing at halftime) beyond the win-probability model's expectation for that state, on held-out seasons.
- **Signal and no noise** (VALIDATION.md): beats its shuffled self; the no-noise target to be proposed after the exploration (CEO approves).
- **Failure looks like:** no tendency moves with play callers more than chance, and neither matchup nor game-state test finds anything. Then schemes are roster traits, and that is itself a finding for `roles-archetypes`.
- **Seasons:** 2006–2024 for play-by-play tendencies, 2016–2024 with participation, 2022–2024 with FTN. The vault (2025) stays closed.

## Inputs and outputs
- **Inputs:** play-by-play (known after each game), FTN charting (kickoff + 14 days), participation (after the season: retrospective only), snap counts, head coaches from the schedule, and possibly a play-caller table (decision below).
- **Outputs (draft):** per team-week, offense and defense tendencies (live), and per team-season the scheme, role and roster parts (retrospective); matchup terms if H9 holds.
- **Cadence:** the live fields and the post-season fields probably make two experts, as with Context and VOE (rule m).

## How it will be used
Matchup terms for sides and totals; coaching-change priors in the offseason; scheme context for `roles-archetypes` and player projections; game-environment features for fantasy and props.

## Plan
Exploration first, time-boxed: (1) why v1 found little; (2) the tendency list and its consistency; (3) the movers design (H10); (4) matchups on margins (H9); (5) game states (H11). The ladder after: tendencies as plain rates → shrunk rates → a few axes → (only if it beats them) clusters.
