# Brief: Context, the play-outcome forecaster (`context-live`)

> The CEO's pick, 2026-11-16, in the strategy chat. This file gets the kickoff, the hunches, the exploration's changes and the agreed brief; the build happens in its own session, from this file.

**Status:** agreed (2026-11-16: the CEO's calls after the exploration are under "The CEO's calls"; the build runs in its own session, from this file and EXPLORATION.md) · **Layer:** expert · **Cadence:** in_season

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

## The CEO's design, as said
*2026-11-16, word for word (spoken; kept as transcribed). This sets what gets built.*

> Okay, so This expert is really trying to look at play calls and look at the situation to make an estimate that is better than nothing about what is going to happen on the play. So this is going to be really important for downstream models, because what this context is going to do is going to say, like, hey, this play right here, based on what we know before the play happened, before it started, with like a little bit of nuance to that, what do we think is going to happen on this play? Is this play really sucky for the offense? Or is this play going to like allow for an explosive outcome for the offense? So here's an example. Maybe we know that the defense is going to blitz because they did. So there's a little bit of leakage, but it's worth it because usually blitzes are called by the defensive coordinator. They didn't just happen randomly. So maybe we know there's going to be a blitz, and we know that there's only 6 people in the box on defense. And we also know that the play call is a run. It's not a QB scramble. It's an actual run given to the running back. But we know it's a blitz as well. So therefore, we can say, actually, this play, based on those 2 things alone, we can probably explain, I'm hoping for 10% of the variance. Because now we know, like, there's going to be, it looks like there's not a lot of people in the box, but there is actually going to be a blitz, so there's going to be more run defenders, and the offensive line maybe is separate from a tight end. Maybe there's no tight end blocking at this point because they're trying to make it look like they're not going to run, but we know they are going to run. So it's like things like that. The goal of this context live expert is to try and figure out if a play was doomed from the start, and then if we know a play was doomed from the start, then we don't assign the outcome, or at least we assign less of the outcome to the talent of the players. Does that kind of make sense? So let's say someone comes on the field, player A comes on the field every single time that we know is going to be bad for the offense. If we don't have this model, we're going to assign those outcomes to that player coming onto the field. But that's going to be wrong, because if we use this context expert, then we know that all of those plays were 10% less likely to be successful for the offense. So that's like added context about the play. It's like not omniscient, but it's like I don't know what the correct way to say it, but like obviously we know more information than either the offense or the defense, because we're combining both of their information together from a third point of view. So it's a very strong expert for downstream models. I think the outcomes that are most forecastable are probably rushing yards, because I would think there's a small amount of variance in rushing yards, but that doesn't really concern me. What really concerns me is what situations or what facts are we going to learn from the most. So I would think, like in my example before, I'm about 50% confident that if we can find, like for example, if we look at, we know it's a run, we know that it's a blitz at the same time, and we know they're not stacking the box. To me, this means, oh, the offense is showing pass, but they're actually going to run, and the defense is showing pass, but they're actually going to blitz. Now the running back is going to get stuffed at the line of scrimmage, and we can attribute that to the situation rather than to the running back or the offensive line. So we're not, in this context model, we're not actually assigning like fault, or we're not assigning an outcome to a specific player. I would say that's a different expert. This expert is simply taking in information from all perspectives and then, you know, seeing what would happen. So, or measuring the effects. So if you're just looking at the offense and you don't know what the defense is going to do, obviously everything kind of averages out. But if you know what the offense is going to do and you know what the defense is going to do, now you have this combination of information that should be able to give us a decent amount of explainability or variance. So like if there's a pressure, we don't if there's a pressure on a play, like the QB is getting pressured, I don't really care if it's the QB's fault or the offensive line's fault. What I care about is, oh, was it the play call? Was it the personnel? Was it the blitz? Was it, and so on. So this context model actually doesn't want to know anything about the players other than their positions. So if we start to learn about the players, that means we're bringing in talent or historical trends or team like effectiveness. We don't want to look at effectiveness at all. We just want to look at the context, the situation of the play. Oh, this play, it's in the 2-minute warning. The defense is blitzing. They're playing zone coverage. The offense has 3 wide receivers, you know. What's the chance of a quarterback pressure, or what's the estimated time that the offensive line can avoid a sack, or what's the time to throw, what's the average time to throw? I think we definitely also want to look at complete, like, what's the odds of a completion if the offense is calling a pass. What's the odds of a touchdown? What's the odds of a first down? What's the odds of a penalty happening? What are the odds of an explosive play? All that kind of stuff. And like I mentioned earlier, we can even look at the average time to throw. We can look at the average depth of target. We can, I think also what would be interesting is if we started to predict, this would be a little bit different in this expert. We might want to move this to another expert, but if we predicted like what kind of route the wide receiver is going to run based on past completions, because I'm pretty sure we only get the route data if there was a completion, but I'm not entirely sure about that. I think the context-live is a totally good name.

**The design rules Claude takes from it (the CEO can correct any of them):**
- **What it is:** for every play, an estimate of what should happen given the situation and both sides' calls, seen from a third point of view. Its job is to say whether a play was "doomed from the start" or set up to be explosive, so that later experts give the players less of the credit or blame for it.
- **No talent.** The model knows positions and counts, never who the players or teams are, and nothing about how good they have been.
- **The play's own calls are allowed** (a blitz, the box count, the personnel, the coverage), even though they are only known because they happened: "there's a little bit of leakage, but it's worth it".
- **It doesn't assign fault.** Splitting an outcome between players is a different expert.
- **Outcomes:** pressure, sack, time to throw, depth of target, completion, interception, fumble, touchdown, first down, penalty, explosive play, rushing yards.
- **Routes** may belong to another expert (logged as an idea).
- **The name stays** `context-live`.

## CEO hunches
*The CEO's words, recorded as said, before the exploration's results. Claude's expectations were written while the first run was still going.*

| # | Hunch | CEO's confidence and expected size | Claude expects | What the usual way says | How the exploration will test it |
|---|---|---|---|---|---|
| H63 | A run into a blitz with a light box gets stuffed, and the situation explains it. "we know it's a run, we know that it's a blitz at the same time, and we know they're not stacking the box... Now the running back is going to get stuffed at the line of scrimmage, and we can attribute that to the situation rather than to the running back or the offensive line." | "I'm about 50% confident" (before the test; after it the CEO said 25% for all); size: "based on those 2 things alone, we can probably explain, I'm hoping for 10% of the variance." | 5% that blitzers and box count alone remove 10% of rushing yards' squared error; 85% that they remove under 2%. Everything about the context together: 2% to 4%. 55% that these runs are stuffed at least 2 points more often than other runs; 60% that they also break 10+ yards more often (a blitz that misses leaves a gap) | Box count is a standard input to expected rushing yards; blitzes are studied on passes, rarely on runs | Runs by blitz and box count: yards, stuffed rate, 10+ rate; the share of squared error the two fields remove alone and beside the situation, held out |
| H64 | Rushing yards are the most forecastable outcome. "I think the outcomes that are most forecastable are probably rushing yards, because I would think there's a small amount of variance in rushing yards, but that doesn't really concern me." | 25% (given after the result, 2026-11-16: "I'm only probably like 25% confident for all my hunches that I gave"; not scored for calibration) | 15% that rushing yards rank first. Expect depth of target, time to throw, first down and completion ahead of it. A small spread isn't the same as a forecastable one: it is the share of the spread that the context explains that counts | Rushing yards are known to be noisy play to play; completion and first-down models explain more | Every outcome ranked by the share of squared error the context removes, held out |
| H65 | Both sides' calls together explain more than either side alone. "if you're just looking at the offense and you don't know what the defense is going to do, obviously everything kind of averages out. But if you know what the offense is going to do and you know what the defense is going to do, now you have this combination of information that should be able to give us a decent amount of explainability or variance." | 25% (given after the result, 2026-11-16: "I'm only probably like 25% confident for all my hunches that I gave"; not scored for calibration) | 97% that both beat either. 30% that the combination adds 0.3 points of share or more beyond the sum of what each side adds alone, for any main outcome (most of what each side knows should simply add up) | Most public models use the offense's side and the situation only | The share removed with the situation plus the offense's fields, plus the defense's, plus both; "together beyond each" = both minus the sum of the two alone |
| H66 | Without context, a player who comes on for bad situations gets blamed for them. "player A comes on the field every single time that we know is going to be bad for the offense. If we don't have this model, we're going to assign those outcomes to that player coming onto the field... all of those plays were 10% less likely to be successful for the offense." | 25% (given after the result, 2026-11-16: "I'm only probably like 25% confident for all my hunches that I gave"; not scored for calibration) | 85% that players differ in the context they play in and that it repeats (odd against even weeks at 0.5 or more). Size: a spread of 1 to 2 points of success rate across regulars; 10% that any player with 200+ plays sits 10 points from average. Most of it from down and distance (third-down backs, short-yardage players), less from the calls | On/off splits and most player grades adjust for down and distance at most | Each player's average held-out context (expected success of the plays he was on, minus the league's), its spread, its repeat, and its size against the spread of players' actual results |

**Claude's first read of the design (assumptions first; not a recommendation):**
- **For it:** this is the "expected" half that every later attribution needs, and keeping talent out of it makes the split clean: context first, then who did what with it. The combination of both sides' calls is information neither coach had.
- **It assumes the calls don't carry talent. They do, in part.** A defense plays a light box because it fears the offense's receivers, and blitzes more against a line it thinks is weak. So "the context was good" will sometimes be the offense's own doing. Flagged; the exploration measures how much team identity adds on top of the context.
- **Which fields arrive when.** Blitzers and the box count come from FTN charting, about two weeks after the game, from 2022. Personnel ("3 wide receivers"), coverage ("zone"), pressure and time to throw come from participation data, which is published only after the season. So part of the CEO's example is in-season and part is the retrospective expert's (`context-retro`). The exploration scores the two field sets apart.
- **It describes plays that happened; it doesn't forecast next week's.** The calls are known after the play, so this expert's outputs are known after the game (plus the charting lag). Forecasting the calls themselves is a different job.
- **A simpler alternative:** the situation only (down, distance, field position, score, clock), which is what public expected-points models use.

## Methods
*Claude, after the hunches: three ways to build it, one exploratory. The CEO takes part in the choice.*

| | Method | What it gives | Assumes | Costs |
|---|---|---|---|---|
| **A** | **One model per outcome** (the usual way): the same context fields into a separate set of trees for each outcome | A calibrated chance or expected value per outcome per play | Outcomes can be treated apart | Cheapest. The outcomes can disagree with each other (a 5% sack chance and a 40% pressure chance that don't fit together) |
| **B** | **A chain in the order a play unfolds:** pressure first, then sack or throw, then completion, then yards, each given the ones before | One coherent story per play, and the size of each link (how much of a sack is the pressure) | The order is right and the same for every play | More work; later links use things known only mid-play, so "before the play" outputs come from running the chain forward |
| **C** | **Plays like this one** (exploratory; from weather forecasting, where a forecast is built from the past days that most resemble today). For each play, find the few hundred most similar past plays and report what happened on them | Every outcome at once, consistent with each other by construction, with a spread; and it can be shown to a user ("on the 300 plays most like this, the back was stuffed 31% of the time") | A good measure of "similar" across fields of different kinds | Slower, and weaker than trees when many fields matter a little each |
| *(tempting, and wrong)* | **Add who the players and teams are** | A much better forecast | Nothing | It defeats the purpose: the output would hold talent, so later experts couldn't use it to separate talent from context |

**Claude's recommendation (the CEO decides):** A in the build, with B's question (how much of a sack is the pressure) answered by one extra column in the exploration, and C tried in the build as a check on A and as the version shown to users if it is close.

## The noise ceiling
*From [`EXPLORATION.md`](EXPLORATION.md), measured before the hunches.*

| Reference | Result |
|---|---|
| Fitting noise (refits on resampled training plays) | 0.02 to 0.28 points of share; differences under about 0.3 aren't read |
| Who the teams are, in hindsight, added to the context | Nothing for any outcome but time to throw (17.6% to 18.8%) |
| Knowing whether there was pressure (2024) | Sack 1.6% to 17.4%; yards 2.2% to 6.9%; success 2.1% to 5.9%; completion 4.5% to 7.8% |

Most of a single play is beyond any description of it. Leaving talent out costs almost nothing in accuracy at this level.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `grain-tables` | `play.pbp`, `play.ftn` (2022 on, known about two weeks after a game) | The situation and the live call fields |
| `participation-live`, `participation-late` | The in-season map of which positions were on the field on each play | The CEO's "3 wide receivers" in-season: positions and counts without waiting for the after-the-season data. Not tried in the exploration |
| `crude-forecaster` | One play's yards are about 2% explainable by anything we tried (crude-forecaster#F12) | The same size again here: rushing yards 2.5%, dropback yards 2.2% |
| `opportunity-quality` | The situation explains 6.9% of one target's points and 13.5% of one carry's (opportunity-quality#F1) | A first size for "what the situation knows" |
| `schemes-v2`, `tag-tables` | The registry's planned inputs (CEO, 2026-11-10) | Allowed (the CEO, 2026-11-16): how a team plays is context; how well it plays is not |

**Already tried:** the old context model's sub-models per play fed an expected-EPA model (`docs/OLD_INVENTORY.md`); here a dropback's EPA isn't explained by the context at all (0.0%), so the outcomes are kept apart and none is rolled into EPA.

## The question
Given the situation and what each side called, and nothing about who the players are, what should have happened on this play?

## Why it matters
Every later judgement of a player or a team needs to know what the play was worth before anyone did anything. This expert gives that number for each outcome, so the experts above it (value over expected, the attribution of a play to its players) start from "what was expected here" and credit only the difference. A user would see it as: "third and 9 against a blitz: pressure expected 41% of the time, league average 30%."

## Terms
- **Standard terms used:** dropback, pressure, sack, blitz, box, play action, screen, EPA, success (`docs/GLOSSARY.md`).
- **New terms this project introduces:**
  - **The situation:** down, distance, field position, quarter, clock, score, timeouts, home or away.
  - **Call fields:** what each side lined up in or did by design: shotgun, motion, play action, screen, the box count, blitzers, pass rushers.
  - **Context:** the situation plus both sides' call fields; never who the players or teams are.
  - **Expected outcome:** the context's estimate of an outcome for one play (a chance for yes-or-no outcomes, an average for yards and seconds).
  - **A player's context:** the average expected outcome of the plays he was on the field for, minus the league's.

## Assumptions
- The call fields describe a decision, not the result. **Flagged:** they are charted after the play; "screen" and "play action" partly describe what happened.
- The calls don't carry talent. **Flagged:** a light box is partly earned by the offense. The exploration's check found no team identity left at the play level.
- Three seasons of charting are enough to fit each outcome. **To test in the build** (fitting noise, and a refit as each season is added).
- A blitz on a run play can't be had from free data (EXPLORATION F1).

## Goals
- An expected value for each outcome on every play, from the situation and the live call fields, saved as a play-level table with its walk-forward history.
- A calibration check per outcome, and a plain statement of which outcomes the context can't explain.
- Each player's and team's context per game and season, with consistency entries.

## Tests
- **Success looks like:** each shipped outcome beats a shuffled copy of its call fields and beats the situation-only model on held-out seasons by more than the fitting noise; chances are calibrated by tenth.
- **Failure looks like:** an outcome doesn't beat the situation-only model (then the situation-only version ships for it, rule k) or doesn't beat its base rate (then the base rate ships).
- **No-noise target (approved by the CEO, 2026-11-16):** the outcome itself on held-out plays, against the situation-only model. This expert has no next-game forecast to be tested on; the yardstick (`crude-forecaster`) will say later what its player and team summaries add.
- **Seasons:** 2022 on for the live fields; scored 2023-2024; vault 2025.

## Inputs and outputs
- **Inputs:** `play.pbp` (known after the game), `play.ftn` (kickoff + 14 days), the in-season on-field map.
- **Outputs:** per play, an expected value for each outcome (known when the charting arrives); per player-game and team-game, the average context faced.

## How it will be used
Feeds `voe-live` (value over expected), the attribution of plays to players, `qb-talent`, `line-play` and the game simulator's play model.

## The CEO's calls
*After the exploration, 2026-11-16, word for word (spoken; kept as transcribed).*

1. **The aim.** The CEO asked what the question meant, and stated the aim: "to me, the aim of the expert should be to kind of explain what the play calling and the situation and the clock and the game script or anything that we kind of intuitively know when you're watching a game. You can tell, like, oh, they blitzed on that play and they called this screen pass, so it actually worked out really well for them. So it wasn't the players doing super good, it was actually just the situation they were in for that given play was favorable for the offense. So that's kind of the aim." Claude then laid out the two options (every play as designed, or pass plays only first), and the CEO chose: "Yes, I say every play." So the expert goes ahead as designed, for every play, runs included; it is an explainer of plays first, and the small size of the player adjustment (EXPLORATION F8) doesn't change that.
2. **Outcomes with nothing to explain: left out.** "Any outcomes with nothing to explain, like interceptions, fumbles, scrambles, we can definitely leave those out." *Claude's reading:* a dropback's EPA goes with them (0.0%); the build's test decides the final list.
3. **Screens and play action count as calls.** "Yes, I would say the screens and play actions definitely counts as calls."
4. **The no-noise test: approved.** "Yes, I approve. The situation only model must pass on how that plays for sure." Each outcome must beat the situation-only model on held-out plays.
5. **Schemes traits are allowed as inputs.** "No, I think schemes does help because showing how a player plays is fine, because the schemes was mostly designed so that the talent of a player isn't in consideration, it's just how they play. And the schemes are supposed to not be related to outcomes like points or yardage until you start combining schemes. So I think adding those is totally good in this." So the rule is: how a team or player plays is allowed; how well they play is not.
6. **Odds: 25% for all, given after the result.** "for all of them, I would say give them like 25% chance, because I know all this is pretty unlikely to work because each play is so noisy. So I'm only probably like 25% confident for all my hunches that I gave." Recorded for H64, H65 and H66 as given after the result (not scored for calibration). H63 keeps the 50% given before the test, with this remark beside it.

## Plan
One build session, from this file and EXPLORATION.md. Rungs: base rate, then the situation alone, then the situation with the live call fields; logistic and linear models before trees. Outcomes: pressure, sack, time to throw, depth of target, completion, rushing yards, dropback yards, stuffed run, explosive play, success, first down, touchdown, penalty (situation only); interceptions, fumbles, scrambles and a dropback's EPA are left out (the CEO's call 2). Order: (1) the play table with the situation and call fields through the gateway, with the 2023 change in participation data handled, and schemes-v2's traits as extra fields (the CEO's call 5); (2) one model per outcome through the harness, each against the situation-only model (the CEO's call 4), with calibration and the shuffled-fields test; (3) fitting noise; (4) player and team context tables with consistency entries; (5) the in-season on-field positions as extra call fields; (6) "plays like this one" (method C) as a check. The chain (method B) and the after-the-season fields (`context-retro`) are later projects.
