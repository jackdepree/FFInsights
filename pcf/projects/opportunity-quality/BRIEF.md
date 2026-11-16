# Brief: Opportunity quality (`opportunity-quality`)

> The CEO's pick, 2026-11-16, in the strategy chat: "let's do the opportunity quality expert brief and exploration". This file gets the kickoff, the hunches, the exploration's changes and the agreed brief; the build happens in its own session, from this file.

**Status:** draft (2026-11-16: kickoff, the CEO's hunches and Claude's expectations written; methods proposed; exploration next) · **Layer:** expert · **Cadence:** in_season

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

## Builds on
| Project | What we use | Why |
|---|---|---|
| `participation` | Snap share and the chance of playing (saved walk-forward history) | Opportunity starts with being on the field; this expert is about what happens once he is |
| `crude-forecaster` | The exploration's findings; the yardstick once built | Attempts are the predictable half of yards (crude inputs remove 50-61% of attempts' error, 3-5% of yards per attempt's: crude-forecaster#F9); past yards already carry 98-100% of what crude inputs explain (F4) |
| `pace`, `player-pace` | Team plays, dropbacks, runs; pass rate over expected | The team's volume that a player's share is a share of |
| `schemes-v2` | Throw depth is a QB and roster trait (R3) | Part of "where the targets happen" belongs to the passer |

**Already tried:** who is on the field matters far more than any team-level trait (crude-forecaster#F6). A teammate ruled out is information box-score models lack (miss-lenses#F4). Past box-score stats add almost nothing to snap share once past snap shares are known (participation#F7). Leverage-weighted snap share is 0.99 alike with plain snap share and adds noise (snap-leverage#R1-R4).

*The remaining sections are written after the hunches and the exploration.*
