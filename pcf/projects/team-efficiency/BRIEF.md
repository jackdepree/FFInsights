# Brief: Opponent-adjusted efficiency (`team-efficiency`)

**Status:** agreed 2026-11-13 (the CEO: "I think we can agree on the brief and start the build"), with what the exploration (GO) and round two changed; building (decision 0032). Early-season gains wait for the build's first results (IDEAS I38). Kickoff 2026-11-12 ([EXPLORATION.md](EXPLORATION.md), "What this changes in the brief" and "What round two changes in the brief") · **Layer:** expert · **Cadence:** in_season

## The usual way
*Claude, 2026-11-12, before any research.*
- Every play is scored against what's normal for its down, distance and field position: EPA, or "success value" in DVOA.
- Each team's average is split into how good it is and who it happened to play. This is usually a ridge regression where every play is offense + defense + home field (DVOA, nfelo, the public EPA sites).
- Garbage time is dropped or down-weighted with a fixed rule, typically win chance outside 10–90% or the last minutes of a half. Passing and rushing are rated separately.
- Early-season numbers are pulled toward last season's, because a few games of data is noisy.

## Analogies
1. **Adjusted plus-minus in basketball.** A player's raw plus-minus mostly reflects his teammates and opponents; a regression separates his own effect. Here the offense plays the player's role and the defenses it faced play the teammates'.
2. **Strokes gained in golf.** Each shot is judged against what's expected from that exact spot (EPA's idea), then adjusted for the field and the course: a 70 at Augusta in wind beats a 68 at an easy course.

## CEO hunches
*The CEO, 2026-11-12, word for word:*

"Efficiency in my mind is a measure of EPA and Winning Percent Added per series. I think the interval that we measure the efficiency should be dependent upon a propensity model. I think that what most models miss is arbitrary sampling whereas we can build a model to tell us statistically which plays are representative of the future and therefore repeatable. I think we have the opportunity to utilize some advanced statistical methods like causal inference (dml) to extract efficiency measures. I think it would be interesting if we applied a propensity model to multiple intervals like one for a play by play and another for drives and another for quarters or even game situations. I think it is important to mesh epa and wpa because a team may be in a position where they will sacrifice points to increase their chances of winning; or at least we could force discrepancies between epa and wpa as a feature for the propensity model. I think the general idea of adjusted efficiency is well understood. We want to measure the difference between situationally explained success against what can be attributed to a team's innate ability. This expert should create a measure of efficiency that is consistent and predictive of other success factors."

| # | Hunch | What the usual way says | How the exploration will test it | Claude's expectation, before testing |
|---|---|---|---|---|
| H40 | Efficiency is "EPA and Winning Percent Added per series" | Per play (EPA per play, success rate) | Series-level EPA and WPA against play-level, same adjustment: consistency, and how well each predicts the targets | EPA per series ties per play (a series' EPA is its plays' EPA summed, so it mostly reweights them); WPA alone repeats less than EPA, because late close plays dominate it |
| H41 | Which plays count, and how much, should come from "a propensity model ... which plays are representative of the future and therefore repeatable", not "arbitrary sampling" | A fixed garbage-time rule (win chance 10–90%) and a fixed recency weight | Learned play weights from the play's situation, against all plays counting equally and against the usual garbage-time rule, on held-out seasons | A modest win over the fixed rule. It should learn to discount kneel-downs and blowouts but keep most plays. That's in line with H22 in pace, where the full sample beat the neutral-only sample |
| H42 | Use "causal inference (dml)" to separate "situationally explained success" from "a team's innate ability" | Ridge on raw EPA: offense + defense + home | Double machine learning: a model of each play's EPA from its situation, fitted only on earlier seasons; team effects estimated on what it leaves over. Compared with plain ridge | A small gain at most. EPA already accounts for down, distance, field and clock, so the gain has to come from the score and the matchup |
| H43 | Apply the propensity model "to multiple intervals": plays, drives, quarters, game situations | One grain, plays (sometimes points per drive) | The same measure built at each grain; does any add beyond the play grain? | The play grain carries most of it; drives may add a little (finishing drives); quarters mostly noise |
| H44 | "Mesh epa and wpa", because a team "will sacrifice points to increase their chances of winning"; the gap between them as "a feature for the propensity model" | EPA only; WPA is treated as too noisy to measure ability | The EPA–WPA gap as a feature in H41's weights, and a blend of EPA and WPA against EPA alone | The gap will be a useful flag for plays that aren't trying to gain points (clock-killing runs, kneels). A blend won't beat EPA on its own future, but may on win-related targets |

The CEO's other points: the general idea of adjusted efficiency "is well understood"; the expert "should create a measure of efficiency that is consistent and predictive of other success factors".

## The question
How efficient is each offense and defense per snap, once the situation and the opponents are taken out, measured so that it repeats and predicts what comes next?

## Why it matters
Efficiency is the main input that game script (who leads, and so who passes) and the team-strength composite are waiting on. It feeds pace (good offenses run more plays, pace#R3) and every player's fantasy ceiling through team scoring. The miss lenses found team scoring and QB efficiency among the three biggest sources of every baseline's misses (miss-lenses#F10).

## Terms
- **Standard terms used:** EPA, WPA (win probability added), success rate, series, drive, garbage time, ridge regression ([GLOSSARY](../../docs/GLOSSARY.md)).
- **New terms this project introduces:**
  - **Series:** nflverse's set of downs: from a first down until the next first down, a score, a turnover or a punt. About 21 per team per game (2024).
  - **Representativeness weight** (the CEO's "propensity model", H41; name to be settled): how much a play counts toward a team's efficiency, learned from how well plays like it predict the team's future.
  - **Double machine learning (DML):** first predict each play's EPA from its situation with a flexible model; then rate the teams on what's left over. The first step is fitted on other data (cross-fitting), so it can't memorise the plays it explains.
  - **EPA–WPA gap:** a play's WPA against what its EPA would usually be worth in win chance at that moment. A large gap marks plays where a team trades points for win chance.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `grain-tables` | `play` (`pbp`: EPA, WPA, win chance, series, drive), `game`, `team_game` | The plays and their timing |
| `tag-tables` | Situation tags (garbage time, two-minute, red zone) | The usual filters to beat (H41) |
| `pace` | `play.pace` (PCF's own expected pass chance and expected pace); its opponent-adjusted pass success (pace H21) | Situation features, and a simple adjusted measure already built |
| `elo` | Ratings and its H7 finding | The margin bar, and what's already been tried |
| `schemes-v2` | `team_season.charted` (from the next season only) | Possible priors for early weeks |
| `validation-harness`, `stabilization` *(idea)* | Walk-forward moments, consistency (`pcf.validation.consistency`) | The tests |

**Already tried:**
- **Elo's H7 (unclear):** passing, rushing and all-play EPA ratings added nothing to Elo's margin forecasts beyond the points rating (±0.01). Efficiency has to earn its place on other targets, or as a better measure, not as another margin model.
- **Pass EPA is our most consistent team measure** (0.53 week to week; run defense 0.31, pass defense 0.25: CONSISTENCY.md).
- **Schedules differ little** (sd 0.7 points, elo#F10), so the opponent adjustment will move season-long numbers only a little; it matters most early in the season.
- **nflverse's EPA and win chance are in-sample before 2020** (tag-tables#F4): they were fit on those seasons, so measures built on them look better there than they were.
- **The full sample beat neutral situations for pace** (pace H22, held).

## Assumptions, limits and advantages (to test, not settled)
- **What "propensity" means.** In causal inference, a propensity is the chance a team ends up in a situation (say, leading by 14), used to compare teams on equal footing. The CEO's words read more like the chance a play is representative of the future. The two are different models; both fit the hunch, and the exploration can try both (question 2 below).
- **The score is partly the team's own doing.** Good teams lead, and leading changes how they play. Taking the score out as "situation" also takes out some real ability: in causal terms, the score is a mediator, so controlling for it is a "bad control". The exploration measures efficiency with and without the score in the situation and reports both.
- **No look-ahead in the situation model.** DML's first step and the learned weights are fitted on earlier seasons only. Fitting them on the whole history would let in-season numbers borrow from the future (rule c).
- **WPA is lumpy.** A few late plays in close games carry most of a game's WPA. EPA and WPA agree closely on most plays (r 0.75 per play, 0.77 per series, 2024), so WPA's extra information sits where the two disagree.
- **Many variants.** Grains × weights × measures add up quickly. The comparisons are fixed in this brief and every version tried is counted, so the vault isn't spent on a lucky one.
- **Advantages:** EPA, WPA, series and drives are all in nflverse, free, from 1999; no new data source. Our timing rules and harness already exist.
- **The simpler alternative:** ridge offense + defense + home on EPA per play, with the usual garbage-time rule and a recency weight. It's the bar every hunch must beat (rung 1).

## Goals
- An offense and a defense efficiency per team, after every game, for passing, rushing and all plays, with their uncertainty.
- Consistent (repeats week to week and season to season) and predictive of the targets below.

## Tests
- **Success looks like:**
  - beats the shuffled, signal-free version of itself on held-out seasons;
  - is more consistent than raw EPA per play;
  - predicts the targets below better than the simple alternative.
- **Failure looks like:** no hunch variant beats the simple alternative (that alternative then ships as the measure), or the measures don't repeat.
- **No-noise target (the CEO, 2026-11-12: "its own future is the main test"):**
  - **Target:** each team's EPA per play on offense and defense in its next 3 games and the rest of the season, all plays, with those games' opponents taken into account.
  - **Baseline:** the simple alternative, and its shuffled version.
  - **Beside it:** next game's points scored and allowed, the play mix (dropbacks, runs), and the team's fantasy points.
- **Seasons:**
  - the situation model and weights are fitted on earlier seasons;
  - choices are tuned on 2006–2015 and scored on 2016–2024;
  - 2025 is the vault.

## Inputs and outputs
- **Inputs:** `play.pbp` (known after each game), `game`, `play.pace`, tags; earlier seasons' fitted models.
- **Outputs:** `team_game` efficiency per team and side (pass, rush, all; EPA and WPA), as of each weekly moment, with an interval; a play-level weight table if H41 holds.

## How it will be used
- **Game script:** who leads, and so the play mix.
- **The team-strength composite.**
- **Pace:** play volume.
- **Player opportunity and fantasy:** team scoring environment.
- **Elo:** a test of whether better-measured efficiency finally adds to the margin.

## Plan
- **Exploration (about one session):**
  - the simple alternative first;
  - then each hunch against it;
  - each hunch gets a verdict with numbers.
- **The ladder:** ridge (rung 1) → DML partially linear (rung 2) → learned weights (rung 3) → grains (rung 4).

## Open questions for the CEO
Answered 2026-11-12, word for word: "1d, its own future is the main test. 2c, as long as we appropriately separate their semantics we can build powerful insights from both!"
1. **What should it predict?** All of them, with its own future as the main test: each team's efficiency over its next 3 games and the rest of the season, with those games' opponents taken into account. The other targets (next game's points scored and allowed, the play mix, the team's fantasy points) are reported beside it.
2. **Which "propensity"?** Both, kept apart by name:
   - **Representativeness weight** (H41's learned weight): how much a play counts, from how well plays like it predict the team's future.
   - **Situation propensity** (the classic causal sense): the chance a team is in a situation (for example, leading by 14), used to compare teams on equal footing, as DML does (H42).
