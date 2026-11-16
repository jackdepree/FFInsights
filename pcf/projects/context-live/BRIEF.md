# Brief: Context, the play-outcome forecaster (`context-live`)

> The CEO's pick, 2026-11-16, in the strategy chat. This file gets the kickoff, the hunches, the exploration's changes and the agreed brief; the build happens in its own session, from this file.

**Status:** draft (2026-11-16: kickoff written; waiting for the CEO's hunches) · **Layer:** expert · **Cadence:** in_season

## What the CEO asked for
*Word for word, 2026-11-16.*

"i would like to work on the context expert. the name might be misleading, but this expert is supposed to be a multi-outcome forecaster. this expert makes simple predictions for common play-level outcomes like pressures, sacks, interceptions, fumbles, receptions and everything in between."

## The usual way
*Claude, before any research.*

Analysts build one model per outcome: a completion-probability model, a sack model, an interception model, each a set of boosted trees on the situation before the snap (down, distance, field position, score, clock) and, where charting exists, the throw's depth and the pressure. Each model is judged by calibration (when it says 30%, does it happen 30% of the time?) and its output is mostly used after the game, as "expected" to measure players against: completion percentage over expected is the best-known case. The models rarely know who is on the field, and the outcomes are treated one at a time even though they are linked (a pressure makes a sack, a sack makes a fumble). The old context model in `old/` followed this shape: sub-models per play (pressure, time to throw, rush yards, yards after the catch, completion, pass breakup) feeding an expected-EPA model (`docs/OLD_INVENTORY.md`).

## Analogies
*Claude.*

1. **Baseball's plate appearance.** Every plate appearance ends in one of a few outcomes (strikeout, walk, home run, ball in play), and the chance of each is built from three rates: the batter's, the pitcher's and the league's. Some outcomes belong mostly to the pitcher (strikeouts), some to the batter (home runs), some to neither (whether a ball in play falls for a hit). What it suggests looking at: for each football outcome, whose rate is it (the offense's, the defense's, a player's, nobody's), and which outcomes are mostly luck.
2. **A weather forecast.** One forecast gives rain, wind and temperature together from the same picture of the atmosphere, and the outcomes are tied (no rain without cloud). The bar every forecast has to clear is the plain seasonal average for that place and date. What it suggests looking at: how far each outcome can be forecast beyond its base rate for the situation, and whether forecasting the linked outcomes together (pressure, then sack, then fumble) beats forecasting each alone.

## CEO hunches
*The CEO's words, recorded as said, before Claude's research. Each with a confidence (a percentage per outcome is best) and an expected size.*

| # | Hunch | CEO's confidence and expected size | Claude expects | What the usual way says | How the exploration will test it |
|---|---|---|---|---|---|
| | *(waiting for the CEO)* | | | | |

## Methods
*Claude, after the hunches.*

## The noise ceiling
*Filled in by the exploration, before the hunches are tested.*

## Builds on
| Project | What we use | Why |
|---|---|---|
| `crude-forecaster` | One play's yards are about 2% explainable by anything we tried (crude-forecaster#F12) | Single plays are mostly noise; the value may be in rates summed over a game |
| `opportunity-quality` | The situation explains 6.9% of one target's fantasy points and 13.5% of one carry's (opportunity-quality#F1) | A first size for "what the situation knows" |
| `schemes-v2`, `tag-tables` | Team traits and play tags, planned inputs (CEO, 2026-11-10) | The registry's planned dependencies |

**Open before the hunches (the CEO's to say):** which moment the forecast is made at (before the game, before the snap, or after the game as "expected"), which outcomes are in the first version, and whether the name changes.

## The question, why it matters, terms, assumptions, goals, tests, inputs and outputs, how it will be used, plan
*Written after the hunches and the exploration.*
