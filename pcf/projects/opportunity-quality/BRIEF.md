# Brief: Opportunity quality (`opportunity-quality`)

> The CEO's pick, 2026-11-16, in the strategy chat: "let's do the opportunity quality expert brief and exploration". This file gets the kickoff, the hunches, the exploration's changes and the agreed brief; the build happens in its own session, from this file.

**Status:** draft (2026-11-16: kickoff, hunches, methods and exploration done (GO); waiting for the CEO's odds on H58, H61, H62, the method choice and the calls under "Open for the CEO") · **Layer:** expert · **Cadence:** in_season

## The usual way
*Claude, before any research.*

Fantasy analysts separate **how much work a player gets** from **what he does with it**. The standard tool is an "expected points" model: every target and carry is given the yards and touchdowns an average player would produce from that spot (the yard line, the down and distance, how far downfield the throw travels), and those are summed into a player's expected fantasy points. The gap between actual and expected is called efficiency and is assumed to drift back toward zero, so next week's projection leans on the expected part. Simpler versions skip the model and weight raw counts: target share, share of air yards, carries inside the 10. nflverse ships one such model's output (`ff_opportunity`); it covers about a fifth of our player-games (grain-tables#F5).

## Analogies
*Claude.*

1. **Expected goals in soccer.** Each shot is scored by how often shots from that spot go in, and a striker's expected goals predict his future goals better than his past goals do. What it suggests looking at: the chances a player gets are steadier than what he makes of them; and a few players do beat their expected numbers year after year, so "efficiency always drifts back" is a rule with exceptions worth finding.
2. **A sales territory.** A salesperson's results depend on the leads the firm hands them as well as their own skill; when they change firms, part of the record stays behind with the territory. What it suggests looking at: how much of a player's opportunity is his (it follows him to a new team) and how much is the offense's (the next man in the same spot gets it).

## CEO hunches
*The CEO's words, recorded as said, before Claude's research. Each with a confidence (a percentage per outcome is best) and an expected size.*

| # | Hunch | CEO's confidence and expected size | Claude expects | What the usual way says | How the exploration will test it |
|---|---|---|---|---|---|
| H56 | Goal-line carries and targets are worth the most expected fantasy points. | "I am 80% confident that goal line carries and targets will be worth the most expected fantasy points." | 90% that a carry inside the 5 and a target into the end zone are the two most valuable kinds of chance, each worth three or more times an average one. 40% that knowing them improves next game's forecast by more than 0.5% beyond past points (they are rare, and past touchdowns already hint at them) | Expected-points models weight red-zone work heavily; "carries inside the 5" is a standard stat | The average points per chance by kind (where on the field, how deep the throw); then whether those counts improve next game's points forecast, held out |
| H57 | A player's expected fantasy points follow him from team to team. | "I am 25% confident that a player's expected fantasy points will follow them from team to team." | 60% that they follow in part: a mover's expected points per game repeat season to season at 0.5 or more, against about 0.75 for a player who stays. Quality per chance follows less than quantity | Roles are assumed to reset on a new team; projections for movers start from the depth chart | Season to next season, movers against stayers: expected points per game, per snap and per chance |
| H58 | "I think that some players like wide receivers that have strong yards after the catch patterns will consistently outperform their expected fantasy points." | none given | 65% that a receiver's yards after the catch over expected repeat season to season (0.25 or more) and predict next season's points over expected; the effect is small, under 0.5 points a game for most | Efficiency is treated as luck that drifts back to zero for everyone | Season-to-season repeat of yards after the catch over expected; whether it predicts the next season's points over expected, beside last season's points over expected |
| H59 | Expected fantasy points are more consistent week to week than efficiency. | "I am 80% confident that expected fantasy points is more consistent week to weeks than efficiency." | 97%. Expect expected points per game to repeat at 0.7 or more and points over expected at under 0.15 | The same: opportunity is sticky, efficiency is noisy | The consistency of each, odd against even weeks and season to season (CONSISTENCY.md) |
| H60 | Opportunity quality broken up by schemes follows a player better than the overall number. | "I would be curious if opportunity quality broken up by schemes will follow players better than overall opportunity quality as an aggregate, I am 30% confident." | 20%: thinner slices are noisier, and the retro's record on team-level fit is 0 of 8 (pattern P2). If it helps anywhere, it's for movers to a team with a very different scheme | Not usually done; scheme fit is argued, rarely measured | For movers: next season's expected points forecast from last season's overall rate, against last season's rates by scheme (shotgun or under center) re-weighted by the new team's mix |
| H61 | A player creates his own opportunity through his efficiency. | "Maybe a player is highly efficient and necessarily they are creating more expected points for themselves than what we would have thought. And maybe another player is underperforming in efficiency metrics and they are causing their opportunities to go down as well." No confidence given | 65% that recent points over expected predict a change in expected points, clear of zero and small (under 1% of the error); stronger for players in their first two seasons | Opportunity is treated as the coach's decision, modelled apart from efficiency | Next game's expected points forecast from past expected points, with and without past points over expected, held out; then by experience |
| H62 | Players whose pattern holds across teams won't regress to the mean. | "if they carry some variance then we should also expect that those types of players will not regress towards the mean, because the team is actively saying that they deserve those opportunities." No confidence given | 30% that players with a record of beating expected points keep more of it than others do; 70% that everyone keeps under a third of last season's gap | Regress everyone toward the average at the same rate for the position | How much of one season's points over expected per chance is kept the next season: everyone, players who beat it two seasons running, and movers |

**The CEO's design, as said (2026-11-16). These set what gets built.**
- **A regression-to-the-mean measure:** "Something that I would want to incorporate into this expert is a 'regression to the mean' measure. I would love to be able to measure the chance that a player will actually bridge the gap between their expected fantasy points and their efficiency."
- **Where the idea comes from:** "Part of this idea comes from watching players move from one team to another and to see if they carry their expected fantasy points patterns".
- **Opportunity that a player creates:** "It would also be interesting to attempt to measure the opportunity that a player actively creates because of their efficiency."
- **Units:** the CEO spoke of expected fantasy points throughout, so this expert's output is in fantasy points (PPR in the exploration; any scoring in the build), with expected yards beside it for the yards-only yardstick. *Claude's reading; the CEO can change it.*

**Claude's first read of the design (assumptions first; not a recommendation):**
- **For it:** the three parts fit one frame: points = expected points (opportunity) + points over expected (efficiency), and the CEO's questions are how much of each part lasts, who it belongs to, and whether one feeds the other. Movers are the natural test of ownership, the kind of question that has held most often here (retro pattern P1).
- **It assumes** that "expected" can be fixed from the situation alone. A throw's depth and place on the field are partly the receiver's doing (he got open deep), so some skill sits inside expected points and some luck sits inside efficiency.
- **Limits:** movers are few (a few hundred player-seasons with enough work) and not random: teams pay for players they think will keep their role. Efficiency per player is measured on 50 to 150 chances a season, so "the chance he bridges the gap" will be wide for most players.
- **A simpler alternative:** skip the expected-points model and use counts (targets, carries, carries inside the 5, air yards). The exploration compares the two.

## Methods
*Claude, after the hunches: two or three ways to test or build it, one exploratory. The CEO takes part in the choice.*

| | Method | What it gives | Assumes | Costs |
|---|---|---|---|---|
| **A** | **Expected points, then one pull-back rate** (the usual way). A model scores every target and carry from its situation; a player's points over expected are pulled toward zero by one rate per position | Expected points per player-game, and a forecast that leans on them | Everyone regresses alike | Cheapest. Can't answer "which players won't regress" |
| **B** | **A pull-back rate per player** (partial pooling). Each player's points over expected are pulled toward his position's average by an amount set by how many chances he's had and how much players truly differ; the output is a range for his true level | The CEO's measure directly: the chance his true efficiency is above zero, and the chance next season's gap closes by half or more | Chances are roughly independent draws; true skill moves slowly | Moderate. Standard statistics, a new kind of output for PCF (a probability about a trait) |
| **C** | **Player and seat, split by movers** (exploratory; from labor economics, where wages are split into a worker's part and a firm's part using people who change jobs). Opportunity = the player's part + the seat's part (team and role), identified from players who move | How much of opportunity a player owns, and each player's portable part; answers H57 and H60 with one model | Moving isn't caused by the thing being measured (it partly is) | The most work and the most fragile: few movers, and seats change with coaches |
| *(tempting, and wrong)* | **Call all of points over expected "luck"** and forecast expected points alone | Simple, and right on average | That no player beats his expected points for real | It throws away exactly what the CEO wants measured |

**Claude's recommendation (the CEO decides):** A and B in the build (B is the regression-to-the-mean measure, A is its plain rung), with C's question answered in the exploration by the plain movers comparison first, and built only if that shows something worth splitting.

## The noise ceiling
*Filled in by the exploration, before the hunches are tested.*

From [`EXPLORATION.md`](EXPLORATION.md): next game's points for players with a snap, 2019-2024, share of squared error removed.

| What is known | Removed |
|---|---|
| His past points | 40.3% |
| Hindsight: his average over the season's other games | 42.5% |
| The chances he actually got in that game (their expected points) | 73.6% |

The room is in forecasting opportunity (33 points of error); efficiency on the day is the other 26% and nothing forecasts it (past points over expected remove 0.1%). Next game's expected points are 52.5% predictable from their own past. **Fitting noise wasn't measured**; the build measures it before reading any gain under 0.5%.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `participation` | Snap share and the chance of playing (saved walk-forward history) | Opportunity starts with being on the field; this expert is about what happens once he is |
| `crude-forecaster` | The exploration's findings; the yardstick once built | Attempts are the predictable half of yards (crude inputs remove 50-61% of attempts' error, 3-5% of yards per attempt's: crude-forecaster#F9); past yards already carry 98-100% of what crude inputs explain (F4) |
| `pace`, `player-pace` | Team plays, dropbacks, runs; pass rate over expected | The team's volume that a player's share is a share of |
| `schemes-v2` | Throw depth is a QB and roster trait (R3) | Part of "where the targets happen" belongs to the passer |

**Already tried:** who is on the field matters far more than any team-level trait (crude-forecaster#F6). A teammate ruled out is information box-score models lack (miss-lenses#F4). Past box-score stats add almost nothing to snap share once past snap shares are known (participation#F7). Leverage-weighted snap share is 0.99 alike with plain snap share and adds noise (snap-leverage#R1-R4).

## The question
How much of a player's fantasy production is the work he's given and how much is what he does with it; how much of each lasts, for whom; and does doing well with it earn him more?

## Why it matters
Every projection and every "buy low, sell high" call rests on a guess about regression: will this player's hot or cold run last? This expert turns the guess into a number per player (the chance the gap closes), and gives the forecasts of playing time and the ball a new input (efficiency earns work). Users would see it as a line on a player card: "12.1 expected, 15.3 actual; about a quarter of that gap usually lasts."

## Terms
- **Standard terms used:** target, carry, air yards, PPR, target share (`docs/GLOSSARY.md`).
- **New terms this project introduces:**
  - **Chance:** one target or one carry.
  - **Expected points (xfp):** the fantasy points an average player scores on a chance from that situation (yard line, down, distance, throw depth, side, formation), summed over a player's chances. Computed by a model fit only on earlier seasons.
  - **Points over expected:** actual points on those chances minus expected points. The fantasy analysts' "efficiency".
  - **Kept share:** how much of a player's points over expected per chance is expected to last, set by how many chances he's had (the regression-to-the-mean measure).
  - **Chance the gap closes:** the probability that next season's (or the rest of this season's) points over expected per chance are less than half of the current gap.
  - **The seat:** the work a team gave whoever held a depth rank at a position the season before.

## Assumptions
- "Expected" can be fixed from the situation alone. **Flagged:** throw depth and place are partly the receiver's doing.
- Points over expected on separate chances are roughly independent draws around a player's true level, which moves slowly. **To test in the build** (the kept share should rise with chances the way the model says; the exploration's 26% overall and 35% at 150+ chances agree in direction).
- Season-to-season numbers come from players with roles in both seasons. **Flagged:** the build's version must include players who lost their role.
- Scoring: any; PPR is the default for reports.

## Goals
- Expected points and points over expected per player-game, saved as a table, any scoring.
- The regression measure per player and week: kept share, the range for his true level, the chance the gap closes.
- A forecast of next game's expected points (and the next 3 games, and the rest of the season) that uses efficiency as an input.
- Consistency entries for every new measure (CONSISTENCY.md).

## Tests
- **Success looks like:** the expected-points forecast beats a shuffled copy of itself and beats the last-4-games average of expected points on held-out seasons; past points over expected improve it (the exploration: +0.94%); the regression measure is calibrated (players given a 60% chance of closing the gap close it about 60% of the time, checked in bands).
- **Failure looks like:** the forecast doesn't beat plain counts of targets, carries and snaps on its own target; or the per-player kept share predicts next season's points over expected no better than one rate per position (then method A ships, rule k).
- **No-noise target (the CEO approves):** next game's PPR points on targets and carries, against a baseline of past points plus past targets, carries and snaps. The exploration says expected points alone don't clear this (-0.19%); the expert's forecast of expected points, with efficiency in it, has to. *Proposed by Claude; the CEO's to approve.*
- **Yardstick:** scored on `crude-forecaster` (yards) once it is built.
- **Seasons:** expected-points model from 2006; player-games from 2012; scored 2019-2024; vault 2025.

## Inputs and outputs
- **Inputs:** `play.pbp` (known after each game), rosters, `player_game.snaps`, participation's saved walk-forward history (Saturday), pace's team volume forecasts.
- **Outputs:** player-game expected points and points over expected (retrospective facts, known after the game); a pre-game forecast of expected points with a range; the regression measure (kept share, chance the gap closes) per player.

## How it will be used
Feeds `vacated-opportunity`, `td-expert`, `player-opportunity` and `fantasy-projections`; the regression measure goes on player cards and into buy-low and sell-high lists in the weekly report.

## Open for the CEO
*Taste calls the exploration raised. The CEO's instinct first; Claude's view is in the chat until asked.*
1. **What is the main output?** The quality of chances adds nothing to next game's forecast beyond counts (EXPLORATION F4). Is this expert mainly (a) the regression measure and the story of a player's production, (b) a forecast of opportunity, or (c) both?
2. **Rest-of-season horizon before agreeing?** Rare, valuable chances (goal-line work) might pay over a season where they don't over one game. Test it now in the strategy chat, or leave it to the build?
3. **Tight ends after the catch** (F11): an input now, or an idea for later?
4. **Odds** for H58, H61 and H62 were not given before the test; they stay blank unless the CEO wants them marked as given after the result.

## Plan
One build session, from this file and EXPLORATION.md. Rungs: counts (targets, carries, snaps), then expected points, then expected points with efficiency, lasso before trees. Order: (1) the chance table and the expected-points model in the package, any scoring, checked against `ff_opportunity`; (2) player-game expected points and points over expected through the gateway, with consistency entries; (3) the regression measure (method A, then B) with its calibration check; (4) the forecast of expected points through the harness with the no-noise test; (5) fitting noise; (6) the longer horizons. Time box: one session for 1-3, a second for 4-6.
