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

## CEO hunches
*To be recorded word for word.*

## Open
- What the expert forecasts (a player's touchdowns next game, the rest of the season, a team's touchdowns, the chance of at least one), and for whom.
- The no-noise target.
