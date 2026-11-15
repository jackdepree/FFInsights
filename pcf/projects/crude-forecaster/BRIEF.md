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
| H50 | | | | | |

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
