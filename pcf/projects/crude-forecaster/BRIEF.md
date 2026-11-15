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
| H50 | "I think the experts that are accounting for opponent strength are probably going to add the most predictive value." | "I am 60% confident there will be signal." | About 40% that an opponent-aware expert (Elo, team efficiency) ranks first: likelier for team yards (60%) than for player yards (25%), where who plays and how much should lead (participation) | A new signal is judged one at a time; no prior on which kind adds most | Each finished expert's held-out gain on each target; rank them, opponent-aware ones against the rest |
| H51 | "I think that past yards and first downs will account for most of the explained variance in future yards; I am fairly confident from past experience." | "fairly confident"; the share: "I think about 50%." | 70% that the share is above 70%: past yards carry most of what a crude model can explain, and first downs add under 2% beyond yards | Recent volume and efficiency are the standard inputs; first downs are rarely used beside yards | The share of the crude model's explained variation that past yards and first downs carry alone, against the full input list |
| H52 | Wide receivers' yards gained will be the easiest to predict. | "I am 60% confident that wide receivers yards gained will be the easiest to predict." | 20%. Expect quarterbacks' passing yards to have the smallest miss relative to their size and backs' rushing yards the largest share explained; receivers' the hardest of the three | Receiving yards are thought the most volatile; volume at running back and quarterback is steadier | Next-game yards by position among players who play: share of variation explained, and the typical miss as a share of the average |
| H53 | Our experts will improve efficiency (yards per attempt) more than volume (attempts). | "I am 60% confident that efficiency will be improved the most by our experts." | 25%. The finished experts are mostly about volume (who plays, how many plays, pass rate); yards per attempt is the noisier half | Volume is the more predictable half; projections are built volume first | Yards split into attempts and yards per attempt; each expert's held-out gain on each half |
| H54 | Recent games carry forward beyond the averages (the "difference in trends" input). | "Yes, I am 40% confident that recency biases will hold statistically significant variance for predictions." | 60% that a recent-minus-season term clears a 90% interval, and if so it is small: under 0.5% of the range score (recent form added 0.01 to 0.04 fantasy points, miss-lenses#F5) | The hot hand is mostly noise; weight recent games a little more | A recent-minus-season input beside the averages, held out; then by position |
| H55 | Boom-or-bust is a lasting property of a player. | "Yes, I am 70% confident that variance as a trait is consistent." | 80% that it repeats by the consistency test; 40% that it still repeats above 0.3 season to season once his average is taken out (spread grows with the average). Expect it to help the range, not the middle (participation#F29, F32) | Volatility is used for best-ball and DFS; rarely checked for whether it repeats | `pcf.validation.consistency` on each player's game-to-game spread of yards, raw and with his average taken out; then as an input to the middle and to the range |

**The CEO's design, as said (2026-11-15). These are calls, not hunches: they set what gets built.**
- **What it forecasts:** "I think it should predict overall yards gained and allowed. Obviously it can be split up for offensive players when they complete a reception or rush, but defenders will have to be clumped together as a unit."
- **Inputs:** "various simple inputs like rolling averages, difference in trends, cumulative sums, and variance of past yards, touchdowns, first downs, and maybe a few more easy to calculate and highly visible inputs."
- **The model:** "an ensemble model mixing lasso and xgboost." (A method the CEO brings; it is compared with the plain versions like any other, rule k.)
- **Team measures:** "Every time we have a team measure like Elo, we will just predict the team level of yards gained or allowed."
- **Worth it** (the CEO, later the same day: "Sorry I meant the literal shap test but I mistyped as sharp"; so read "a SHAP test"): "if we can prove that a sharp test shows predictive power then we can say it is worth it. If it adds nothing or hurts the model then it failed. A model being worth it can mostly be a vision and taste call from me, depending on the complexity."
- **Horizons:** "I think the crude forecaster should be both short horizon like maybe even within a game and then also long horizon outcomes." (Open: live in-game prediction is a non-goal in VISION.md, so what "within a game" means here is the CEO's to say.)
- "I do not have any strong/confident hunches." The CEO asked Claude for questions to draw more out; they were put in the chat the same day and the answers are recorded below as they come.

**Claude's first read of the design (assumptions first; not a recommendation):**
- **For it:** yards are one unit for players, offenses and defenses; a team's player yards add up to its total (grain-tables#F17); the props we collect are mostly in yards, so the yardstick sits next to the betting target.
- **It assumes** that what an expert is worth for yards is what it is worth for the products. Yards leave out touchdowns and turnovers, which move fantasy points and margins.
- **Limits:** an expert whose output isn't about yards (the chance a player is active, a win chance) is scored only through what it does to yards. Defensive players can't be scored one by one, only through the unit.
- **A simpler alternative that exists today:** the baselines' lasso on fantasy points, which already scored participation (participation#F15).

## Methods
*Claude, after the hunches: two or three ways to build it, one exploratory. The CEO takes part in the choice.*

The crude model itself is the CEO's: simple, visible inputs into a lasso and boosted trees, mixed. The methods below are about the other half, **how an expert's worth is read off it**.

| | Method | What it answers | Assumes | Costs |
|---|---|---|---|---|
| **A** | **Added alone** (the usual way). Fit the crude model; add one expert's saved walk-forward output; score the change on held-out seasons with the paired interval | "What is this expert worth on its own, on top of the crude inputs?" | Nothing beyond the harness | One refit per expert and target. Says nothing about overlap: two experts that carry the same thing both look good |
| **B** | **Withheld** (the weather services' denial experiment). Fit with every expert in; take one out; score the loss | "What would we lose without it, given everything else?" | The full set is fixed | One refit per expert. Every number changes when a new expert joins, and two overlapping experts both look worthless |
| **C** | **Shapley across experts, on held-out error** (exploratory). Fit the crude model with every combination of experts; an expert's worth is its average held-out gain over every order it could have been added in | "What is each expert's fair share of the total gain?" It has no order problem, and the shares add up to the total | Combinations can be fitted cheaply (7 experts is 128 fits per target; orders can be sampled when there are more) | The most fits. Shares still move when a new expert joins, so each table is dated, like the lens list |
| *(tempting, and wrong as the test)* | **SHAP values from one fitted model** | "What is this model leaning on?" | That leaning on an input means the input helps | Nothing extra. But SHAP describes the fitted model, not the truth: an input of pure noise that the trees over-fit gets a share, and two inputs that carry the same thing split theirs arbitrarily. It can't fail an expert that hurts held-out forecasts |

**Claude's recommendation (the CEO decides):** A and C from the same held-out runs, reported side by side (alone, and its fair share), with SHAP plots on the held-out rows as the explanation of *where* an expert helps (which positions, which situations). C is the CEO's SHAP idea moved from "what the model uses" to "what improves forecasts nobody has seen": the same Shapley arithmetic, applied to experts and to held-out error. Pass or fail stays VALIDATION.md's held-out rule (adds value, neutral, adds noise).

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
