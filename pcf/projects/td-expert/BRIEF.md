# Brief: the touchdown expert (`td-expert`)

> The CEO's pick, 2026-11-16, in the strategy chat. This file gets the kickoff, the hunches, the exploration's changes and the agreed brief; the build happens in its own session, from this file.

**Status:** kickoff (2026-11-16: the usual way and analogies written; waiting for the CEO's hunches) · **Layer:** expert · **Cadence:** in_season

## What the CEO asked for
*Word for word, 2026-11-16.*

"Ok let us start the touchdown expert"

The registry's one-line summary, written when the project was listed: "Red-zone and goal-line usage, giving touchdown probability. Feeds TD-scorer props."

## The usual way
*Claude, before any research.*

Analysts treat touchdowns as the noisiest part of a player's line and forecast them in two steps. First, how many touchdowns will the team score (from the betting total or the team's offense rating), split into passing and rushing. Second, what share of them each player gets, from his share of the valuable chances: carries inside the 5, targets inside the 10 and into the end zone. A player's own scoring rate is pulled hard toward the league rate for that kind of chance ("touchdown regression": a receiver with 12 touchdowns on 90 targets is expected to fall back). Anytime-scorer props are then priced from the expected count, as the chance of at least one.

## Analogies
*Claude. Ways to look at it, not answers.*

1. **Goals in soccer and hockey (expected goals).** Goals are rare and decide everything, so analysts stopped counting them and started valuing each shot by where and how it was taken. Shot quality and shot volume repeat from season to season; finishing (goals beyond what the shots were worth) barely does, except for a handful of elite players. What it suggests looking at: whether scoring beyond the worth of the chances is a lasting trait for anyone, and for whom (a goal-line back, a tall red-zone target, a running quarterback); and whether the team creating the chances matters more than the player finishing them.
2. **An insurer pricing rare claims.** One driver's claims in a year say almost nothing about him, so the price comes mostly from his class (age, car, postcode) and moves toward his own record only as years accumulate. The method is a credibility weight: how much to trust the individual's record against the group's. What it suggests looking at: how many chances it takes before a player's own touchdown rate should be believed over his role's rate, and whether that number differs by kind of chance.

## What PCF already knows
*From finished work and explorations; the build must use these.*

- **Goal-line chances are worth the most** (opportunity-quality F3): a target into the end zone from the 10 or closer is a touchdown 45% of the time; a carry inside the 2, 52%.
- **But the kind of chance added nothing to next game's fantasy forecast beyond the count of chances** (opportunity-quality F4). The touchdown expert has to show it is different for touchdowns alone, or over a longer horizon.
- **A play's touchdown chance is among the most explainable outcomes** (context-live F3): the situation alone removes 27.7% of the error for a run and 16.7% for a dropback, almost all from field position and distance. The play call adds nearly nothing.
- **Depends on** opportunity quality and team efficiency (registry); neither's build output exists yet for opportunity quality.

## What the CEO said
*2026-11-16, word for word.*

> Can we predict red zone efficiency based on past play outcome variance in the red zone? Can we build features that predict touchdowns rather that field goals? I would love to forecast touchdown regression. I would love to have an estimate on the noisiness of an observed touchdown. That would also be a very cool measure, how many chances does each player need to estimate greater than 0.5 touchdowns? I think touchdown allocation will be closely tied to scheme and play calling tendencies; I am about 40% confident. I think the combination of explosive play rate and red zone opportunities will be the strongest predictors of rest of season touchdown totals; I am 50% confident. Do you have any more questions for me?

## CEO hunches
*The CEO's words, before any result. Claude's expectations were written before the first run.*

| # | Hunch | CEO's confidence and expected size | Claude expects | What the usual way says | How the exploration will test it |
|---|---|---|---|---|---|
| H67 | "touchdown allocation will be closely tied to scheme and play calling tendencies" | "about 40% confident"; no size given | 65% that a team's tendencies (how often it passes near the goal line, shotgun rate, pass rate overall) repeat and forecast how its touchdowns split between rushing and passing, removing 2 to 5% of that split's error. 20% that they add 0.3+ points to a player's touchdown forecast once his own share of the chances is known: expected under 0.3 | Allocation follows each player's share of goal-line carries and end-zone targets; the scheme is behind those shares, not beside them | (a) Does the team's past pass share inside the 10 and its other tendencies forecast the rushing share of its later touchdowns? (b) Do they add to a player's rest-of-season touchdowns beyond his own chances? |
| H68 | "the combination of explosive play rate and red zone opportunities will be the strongest predictors of rest of season touchdown totals" | "50% confident"; no size given | 80% that red-zone chances are in the top three single predictors. 25% that explosive-play rate is in the top five; expected to add under 0.3 points beside volume. 15% that this pair is the strongest pair: expected winner is plain volume (chances or yards a game) with red-zone chances | Volume first (touches, targets, yards), then red-zone share; explosive plays are treated as luck | Rank each single predictor and each pair of predictors of a player's rest-of-season rushing and receiving touchdowns, held out |

## The CEO's questions
*Asked as questions, so they aren't scored as hunches. Claude's expectation beside each, written before the first run.*

| # | The question | Claude's reading | Claude expects |
|---|---|---|---|
| Q1 | "Can we predict red zone efficiency based on past play outcome variance in the red zone?" | Does the spread of a team's past red-zone plays (boom or bust against steady) forecast its later touchdown rate per red-zone trip, beyond its past average? | Red-zone touchdown rate repeats weakly (half season to half season about 0.15). 85% that the spread of outcomes adds nothing beyond the average |
| Q2 | "Can we build features that predict touchdowns rather that field goals?" | For drives that reach the red zone: touchdown or field goal? Which team traits forecast it | 75% that the offense's plain efficiency everywhere on the field forecasts it better than its own red-zone history. All features together remove 1 to 3% of the error |
| Q3 | "I would love to forecast touchdown regression" | A player's touchdowns beyond what his chances were worth: how much of it carries forward | 90% that expected touchdowns forecast later touchdowns better than past touchdowns do. A player keeps 5 to 20% of his touchdowns over expected the next season |
| Q4 | "an estimate on the noisiness of an observed touchdown" | How likely was the average scored touchdown before the snap, and what is one observed touchdown worth as evidence about later ones, against one expected touchdown | The average touchdown came on a chance worth 20 to 30%. One observed touchdown is worth a quarter to a half of one expected touchdown as evidence |
| Q5 | "how many chances does each player need to estimate greater than 0.5 touchdowns?" | Two readings, both measured: (a) how many chances of each kind add up to half an expected touchdown; (b) how many chances before a player's own touchdown rate is worth as much as the league's | (a) About 1 carry inside the 2, 1 to 2 end-zone targets from close, 10 to 12 ordinary targets, 15 to 20 ordinary carries. (b) Several hundred targets or carries: more than a season |

## Open
- What the expert forecasts (a player's touchdowns next game, the rest of the season, a team's touchdowns, the chance of at least one), and for whom.
- The no-noise target.
