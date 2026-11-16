# Exploration: Context, the play-outcome forecaster (`context-live`)

> A first look at the CEO's design: for every play, what do the situation and both sides' calls say should happen, with nothing known about who the players are? And at hunches H63–H66: a run into a blitz with a light box, which outcomes are the most forecastable, whether both sides' calls together beat either alone, and whether players differ in the context they play in.
> Run on 2026-11-16 with [`explore/first_look.py`](explore/first_look.py) (output: [`explore/first_look.txt`](explore/first_look.txt)). Plays: regular seasons 2022–2024 (FTN charting starts in 2022): 39,804 designed runs, 61,019 dropbacks, 53,996 pass attempts. Scored on 2023 and 2024, each from boosted trees fit on the earlier seasons. The vault (2025) wasn't read.

**How to read it.** "Removes X%" is the share of squared error removed against the plain base rate of that outcome, on held-out plays. **The situation** is down, distance, field position, quarter, clock, score, timeouts, home or away. **The live call fields** arrive in-season, about two weeks after a game (play-by-play and FTN charting): shotgun, no huddle, where the QB lines up, backs in the backfield, motion, play action, screen, RPO, trick play, sneak, hash; the defense's box count, blitzers and pass rushers. **The after-the-season fields** come from participation data: formation, the offense's personnel (backs, tight ends, receivers, linemen), the defense's personnel, man or zone, the coverage. Intervals are 90%, resampling whole games. Discovery only: one rough version, not through the gateway or the harness.

**Verdict: GO.** Both sides' calls clearly add to the situation for what happens early in a pass play: pressure (0.8% to 4.2%), time to throw (1.7% to 17.6%), depth of target (4.3% to 18.1%), completion (1.5% to 3.9%), sack (0.5% to 1.4%). **Two results the CEO should weigh before the brief is agreed.** For runs, and for how a play ends (yards, success, explosive plays), the calls add about half a point to what down and distance already say (F3). And the adjustment this makes to a player's record is small: about 1 point of success rate for a typical regular, 4.5 at the most (F8), against the "10% less likely" the design imagined.

## The noise ceiling (measured first)

A single play has no hindsight average to compare with, so three other references:

| Reference | Result |
|---|---|
| **Fitting noise** (the same model refit three times on resampled training plays) | 0.02 to 0.28 points of share: rushing yards 0.28, sack 0.13, completion 0.10, pressure 0.06, success 0.02 to 0.06. Differences under about 0.3 points aren't read |
| **Who the teams are, in hindsight** (the offense's and the defense's average of the outcome over their other games that season, added to the context) | Nothing: rushing yards 2.48% to 1.69%, pressure 4.22% to 3.83%, completion 3.86% to 3.72%, sack 1.43% to 1.22%. Time to throw is the one gain (17.6% to 18.8%) |
| **Knowing mid-play facts** (whether there was pressure, on 2024) | Sack 1.6% to 17.4%; yards 2.2% to 6.9%; success 2.1% to 5.9%; completion 4.5% to 7.8% |

- **Most of a single play is beyond any description of it.** Even told whether the quarterback was pressured, 93% of a dropback's yards are unexplained.
- **Team identity adds nothing at the level of one play**, so the CEO's rule (no talent in the model) costs almost nothing in accuracy here.
- **The mid-play facts are worth far more than the pre-snap ones**, which is the case for the chain (method B) as a second step.

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **Data: a blitz isn't charted on runs.** FTN's blitzer count is filled on dropbacks only: 3 of 39,804 designed runs have one. So the CEO's example (a run into a blitz with a light box) can't be tested from free data; the box count can. | strong |
| F2 | **Data: the after-the-season fields changed in 2023 and can't be mixed with earlier seasons.** Participation data changed provider: boxes average 6.4 defenders in 2022 and 5.0 after, personnel strings changed format, formations were renamed. A model fit on 2022 and used on 2023 was worse than the base rate (run success −2.7%). Those fields are scored here on 2024 from 2023 alone. Also, charting differs on plays wiped out by a penalty, which made the call fields "remove" 28% of penalties' error by leakage; penalties use the situation only (2.7%). | strong |
| F3 | **H64: what the context explains, outcome by outcome** (situation, then with the live call fields). Touchdown on a run 27.7% → 27.8%; first down on a run 23.7% → 24.3%; depth of target 4.3% → 18.1%; time to throw 1.7% → 17.6%; touchdown on a dropback 16.7% → 17.0%; first down on a dropback 6.4% → 7.0%; run success 5.5% → 5.9%; pressure 0.8% → 4.2%; completion 1.5% → 3.9%; **rushing yards 2.1% → 2.5% (2.1 to 2.8)**; dropback success 2.2% → 2.4%; dropback yards 1.7% → 2.2%; explosive pass (20+) 1.0% → 1.9%; explosive run (10+) 1.0% → 1.5%; sack 0.5% → 1.4%; stuffed run 0.7% → 1.2%; run EPA 0.5% → 0.9%. **Nothing explains** interceptions (−0.3%), fumbles (−0.5%), scrambles (−1.2%) or a dropback's EPA (0.0%): for those the base rate is the best estimate. Rushing yards rank 10th of 22. | strong |
| F4 | **Where the calls teach the most beyond the situation:** time to throw (+15.9 points), depth of target (+13.8), pressure (+3.5), completion (+2.3), sack (+0.9), explosive pass (+0.8). For runs every outcome gains 0.2 to 0.6. Screens and play action do much of the work for time to throw and depth of target: they are the offense's call, and they nearly define the throw. | strong for the sizes; the screen flag is a judgement call |
| F5 | **H65: the two sides add up; there is no extra from combining them.** Pressure: the situation 0.8%, with the offense's fields 2.7%, with the defense's 2.3%, with both 4.2%. "Both together beyond the sum of each alone" is within noise of zero for every outcome that is explained at all: pressure −0.07 (−0.18 to 0.05), sack +0.08, completion −0.03, rushing yards +0.04, run success +0.12 (0.01 to 0.23), time to throw −0.79 (the two sides overlap). The defense's fields matter for pressure and little else in-season. | strong |
| F6 | **The after-the-season fields add for the pass, not the run** (2024, fit on 2023): completion 3.6% → 4.5% (4.0 to 5.2), depth of target 17.3% → 18.5%, sack 1.2% → 1.6%, pressure 4.1% → 4.3%; rushing yards 2.2% → 2.3% and run success 5.7% → 5.4% (no gain). Coverage and personnel are the defense's side of completion: 1.5% → 2.6% with them alone. | medium: one season to fit, one to score |
| F7 | **H63: box count and the run.** Runs into 6 or fewer in the box gain 4.65 yards and are stuffed (0 or fewer) 16.7% of the time; into 7, 4.17 and 18.9%; into 8 or more, 3.46 and 23.8%. On first and second down with 5 to 10 to go, from shotgun: 14.7% stuffed into a light box, 20.2% into 8 or more. The box count alone removes 0.80% of rushing yards' error; beside the situation it adds 0.2 points (2.07% → 2.26%). **The pass half of the example:** a blitz raises pressure from 26.5% to 39.0% and sacks from 5.9% to 8.4%, costs 0.3 yards a dropback and 1.3 points of success, and slightly raises 20+ yard plays (8.0% to 8.6%). Blitzers and box count alone remove 1.5% of pressure's error. | strong for the tables; the blitz-on-a-run cell doesn't exist (F1) |
| F8 | **H66: players do differ in the context they play in, by about a point.** Each player's average held-out context (the chance of success of the plays he was on, minus the league's 43.2%), players with 200+ plays in a season: spread 0.84 points on offense and 0.88 on defense; 5th to 95th percentile −1.3 to +1.5; the furthest −4.5 (a running back) and +3.0. No player is 5 points from average. It repeats at 0.37 odd against even weeks and 0.27 season to season (offense); 0.40 and 0.35 (defense). It is 4% of the spread in players' actual on-field success (7% on defense), and 91% of it comes from the situation alone, before any call is known. Running backs, tight ends and interior defensive linemen vary the most. | medium: success only; runs and passes pooled, so "he plays on run downs" is part of it |
| F9 | **How far apart good and bad contexts are.** Held-out chance of a successful run: 23% in the bottom tenth of contexts, 67% in the top tenth; for dropbacks 28% and 55%. Almost all of that is down and distance: with the situation alone the tenths are 25% and 66%, 29% and 54%. The forecasts are calibrated by tenth. | strong |

## The hunches

| # | Hunch | Verdict | Real? | Pays? | CEO said | Claude said |
|---|---|---|---|---|---|---|
| H63 | A run into a blitz with a light box gets stuffed; the two facts explain about 10% of the variance | **unclear** on the example (a blitz isn't charted on runs, F1); **the size failed**: the box count removes 0.8% of rushing yards' error, the whole context 2.5% (F3, F7) | unclear: the box half runs the expected way (a heavier box, more stuffs) | small: +0.2 points beside the situation | 50%; 10% of the variance | 5% it reaches 10%, 85% under 2%: 0.8%. "All context 2% to 4%": 2.5%. The stuffed and 10+ predictions couldn't be tested |
| H64 | Rushing yards are the most forecastable outcome | **failed** (F3): 10th of 22 at 2.5%; touchdowns and first downs (from field position and distance), depth of target and time to throw (from the call) are far ahead | no | not a forecast | none | 15% it ranks first; expected depth of target, time to throw, first down and completion ahead: all four are |
| H65 | Both sides' calls together explain more than either alone | **held in part** (F5): both beat either for pressure (4.2% against 2.7% and 2.3%) and completion; but they simply add up, with nothing extra from the combination | partly | partly: pressure, completion, sack | none | 97% both beat either: yes where anything is explained. 30% that the combination adds 0.3+ points: it doesn't |
| H66 | A player who comes on for bad situations gets blamed for them without this | **held, small** (F8): players differ by about 1 point of success rate (4.5 at most), repeating at 0.37; nine-tenths of it is down and distance | yes, small | not tested (it is an adjustment, not a forecast) | none; "10% less likely" as the example | 85% they differ and repeat at 0.5+: they differ, at 0.37. Spread 1 to 2 points: 0.84. 10% that anyone is 10 points off: nobody is 5. Mostly down and distance: yes |

Retro patterns: P2 (team-level traits add little) fits the team-identity reference. P4 (clever versions tie the plain one) fits F5 and F9: the calls barely move outcomes that down and distance already explain. P7 (real isn't the same as useful) fits H66.

## The case against this exploration

- **Three seasons, and two for the after-the-season fields.** FTN starts in 2022 and participation changed in 2023, so everything rests on 26,000 scored runs and 41,000 scored dropbacks, and F6 on a single season each way.
- **One setting of the trees, squared error for yes-or-no outcomes.** Rare outcomes (interceptions, fumbles) might show a little with a model built for rare events; the negative numbers say "not with this one".
- **The calls are charted after the fact.** "Screen" and "play action" partly describe what happened, not only what was called; a blitz is counted from who rushed. The CEO accepted this for blitzes; it applies to more fields than that one.
- **The calls carry talent.** A light box is partly earned by the offense's receivers. The team-identity reference found nothing at the play level, which is some comfort, but it was a blunt check (a season average).
- **H66 used success only**, pooled runs with passes, and counted every player on the field, not the ones the play went to. A back used only on third and long would show more than this average does; the furthest player (−4.5 points) is such a case.
- **The blitz-on-a-run example wasn't tested at all** (F1), and it was the CEO's central case.

## What this means for the brief

- **Build it as one model per outcome on the situation and the live call fields** (method A), calibrated; ship the base rate for interceptions, fumbles and scrambles until something beats it (F3).
- **The early-play outcomes are where it earns its place:** pressure, time to throw, depth of target, completion, sack (F4). That is also where the CEO's "was it the play call, the personnel, the blitz?" has answers.
- **Run plays get little from the calls** with free data; the box count is the one field that matters, and a blitz on a run isn't available (F1, F7).
- **The after-the-season fields belong to `context-retro`**, from 2023 only (F2, F6).
- **Player adjustment is real and small** (F8): worth passing to the attribution expert, not worth expecting large corrections from.
- **Open for the CEO:** what the no-noise test is, which outcomes ship, whether screens and play action count as calls, and the chain (method B) as a second step.
