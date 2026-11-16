# Brief: Opportunity quality (`opportunity-quality`)

> The CEO's pick, 2026-11-16, in the strategy chat: "let's do the opportunity quality expert brief and exploration". This file gets the kickoff, the hunches, the exploration's changes and the agreed brief; the build happens in its own session, from this file.

**Status:** draft (kickoff, 2026-11-16: the usual way and analogies written; waiting for the CEO's hunches) · **Layer:** expert · **Cadence:** in_season

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
| H56 | | | | | |

## Methods
*Claude, after the hunches: two or three ways to test or build it, one exploratory. The CEO takes part in the choice.*

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
