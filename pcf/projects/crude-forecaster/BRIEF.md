# Brief: Crude forecaster (`crude-forecaster`)

> The yardstick for incremental gains (CLAUDE.md, "One yardstick for incremental gains"). Opened in the strategy chat, 2026-11-15: this file gets the kickoff, the exploration and the agreed brief; the build happens in its own session, from this file.

**Status:** draft (kickoff, 2026-11-15: the usual way and analogies written; waiting for the CEO's hunches) · **Layer:** foundation (phase 0: a measuring tool, never shipped as a product) · **Cadence:** in_season

## The usual way
*Claude, before any research.*

Forecasting shops judge a new signal by **ablation against a fixed reference model**: freeze a simple model, add the one new input, refit, and measure the change in error on held-out data with a paired test. The reference is kept deliberately plain and is changed rarely, so that numbers from different months can be compared. Public sports projections mostly skip this: they are judged on their final accuracy, and nobody reports what each ingredient is worth. PCF already does a one-off version: every expert's brief names its own downstream target and baseline for the no-noise test (VALIDATION.md §5), which is why participation was scored on the lasso's fantasy points and Elo against the closing line, in different units that can't be set side by side.

## Analogies
*Claude.*

1. **Weather services' denial experiments.** To learn what a satellite or a set of weather balloons is worth, forecasters rerun the same forecast system with that one data source withheld and measure how much skill is lost. What it suggests looking at: the value of a source depends on what else is already in the system (a second satellite over the same ocean is worth far less than the first), and on the horizon (some sources matter for tomorrow, others for next week).
2. **The factor zoo in investing.** Hundreds of published signals each predicted returns when tested alone; most add nothing once the handful of established factors are already in the model. What it suggests looking at: "does it predict?" and "does it add to what we already have?" are different questions with different answers, and the answer to the second depends on the order things were added.

## CEO hunches
*The CEO's words, recorded as said, before Claude's research. Each with a confidence (a percentage per outcome is best) and an expected size.*

| # | Hunch | CEO's confidence and expected size | Claude expects | What the usual way says | How the exploration will test it |
|---|---|---|---|---|---|
| H50 | "I think the experts that are accounting for opponent strength are probably going to add the most predictive value." | "probably"; no odds or size yet (asked 2026-11-15) | to be written before the test, after the CEO's odds | A new signal is judged one at a time; no prior on which kind adds most | Each finished expert added to the crude forecast alone; rank by gain, opponent-aware ones (Elo, team efficiency) against the rest |
| H51 | "I think that past yards and first downs will account for most of the explained variance in future yards; I am fairly confident from past experience." | "fairly confident"; "most of the explained variance" | to be written before the test | Recent volume and efficiency are the standard inputs; first downs are rarely used beside yards | The share of the crude model's explained variation that past yards and first downs carry alone, against the full input list |

**The CEO's design, as said (2026-11-15). These are calls, not hunches: they set what gets built.**
- **What it forecasts:** "I think it should predict overall yards gained and allowed. Obviously it can be split up for offensive players when they complete a reception or rush, but defenders will have to be clumped together as a unit."
- **Inputs:** "various simple inputs like rolling averages, difference in trends, cumulative sums, and variance of past yards, touchdowns, first downs, and maybe a few more easy to calculate and highly visible inputs."
- **The model:** "an ensemble model mixing lasso and xgboost." (A method the CEO brings; it is compared with the plain versions like any other, rule k.)
- **Team measures:** "Every time we have a team measure like Elo, we will just predict the team level of yards gained or allowed."
- **Worth it:** "if we can prove that a sharp test shows predictive power then we can say it is worth it. If it adds nothing or hurts the model then it failed. A model being worth it can mostly be a vision and taste call from me, depending on the complexity."
- "I do not have any strong/confident hunches." The CEO asked Claude for questions to draw more out; they were put in the chat the same day and the answers are recorded below as they come.

**Claude's first read of the design (assumptions first; not a recommendation):**
- **For it:** yards are one unit for players, offenses and defenses; a team's player yards add up to its total (grain-tables#F17); the props we collect are mostly in yards, so the yardstick sits next to the betting target.
- **It assumes** that what an expert is worth for yards is what it is worth for the products. Yards leave out touchdowns and turnovers, which move fantasy points and margins.
- **Limits:** an expert whose output isn't about yards (the chance a player is active, a win chance) is scored only through what it does to yards. Defensive players can't be scored one by one, only through the unit.
- **A simpler alternative that exists today:** the baselines' lasso on fantasy points, which already scored participation (participation#F15).

## Methods
*Claude, after the hunches: two or three ways to build it, one exploratory. The CEO takes part in the choice.*

## The noise ceiling
*Filled in by the exploration, before the hunches are tested.*

## Builds on
| Project | What we use | Why |
|---|---|---|
| `baselines` | The lasso and the averages (fantasy points, any scoring); ECR; the no-vig closing line | The plain reference models already exist and already run through the harness |
| `validation-harness` | The walk, the paired comparison, the signal and no-noise tests | The yardstick is a standing no-noise test, not a new kind of test |
| `elo`, `team-efficiency` | Margin, total and win forecasts; the offense and defense split | The game-level side of the yardstick |
| `participation` | Its saved walk-forward history | The first expert already scored this way: its share improved the lasso's fantasy points by 0.021 range score, a quarter of the gap to ECR (participation#F15) |

**Already tried:** Elo adds nothing to the closing line (elo#F4); team efficiency adds nothing to Elo's margin and helps points and team fantasy points through the offense and defense split (team-efficiency#R6, R18). Pre-game conditions explain under 0.6% of player misses; what happens in the game (snap share, team points, margin) explains the most (miss-lenses#F1, F2).

*The remaining sections (the question, terms, assumptions, goals, tests, inputs and outputs, how it will be used, plan) are written after the hunches and the exploration.*
