# Context, the next version (`context-v2`)

> **Status:** draft brief, kickoff 2026-11-20; four looks done (EXPLORATION.md) and the build section drafted 2026-11-21 ("The brief, after the exploration", at the end), for the CEO to agree; the CEO chose method A first and put routes and coverage in scope ("Ok let's start with A. I think routes and coverage should be in scope."); first look pre-registered in [EXPLORATION.md](EXPLORATION.md) (the CEO: "Next thing I want to explore is possibly another exploration or a brainstorm on how we can improve the context expert model"). It is agreed after the exploration (CLAUDE.md, lifecycle step 3). Builds on `context-live` (RESULTS.md) and its back-history (decision 0038).

## The usual way

Professionals improve expected-outcome models in four ways:

- They add information from before and around the snap: alignment, motion, coverage, routes and, with tracking, separation. Next Gen Stats' completion chance is built from tracking.
- They refit often, weighting recent seasons as the league changes.
- They model a play's outcomes as a chain (pressure, then sack or throw, then completion, then yards), so the forecasts agree with each other.
- They check calibration within slices and on a held-out season.

## Two analogies

- **Weather forecasting.** The big gains came from better observations (satellites, radar), not better equations, and from updating every few hours as new readings arrive. For us, that points at better inputs and weekly refits more than a fancier model.
- **Hospital case-mix adjustment.** Hospitals are compared after adjusting for how sick their patients were. The long argument is whether to also adjust for things the hospital chooses, like which surgery to do. Adjusting for a choice hides the skill in making it. That is the CEO's strategy point: should the context explain time to throw and depth, or should they be credited to the QB and the play-caller?

## The CEO's hunches (word for word, before any test)

The CEO, 2026-11-20, on why: "I know these are mostly method hunches but I am just disappointed that this expert can only explain 1 to 4% of the variance for these outcomes."

| # | Hunch | The CEO's odds | Claude's odds |
|---|---|---|---|
| H85 | "can we use a conditional diffusion model? The conditional diffusion model would be conditioned in all of the charters like personnel, play calls, schemes, score, blitz, down, and so on. Then the diffusion model will simultaneously learn and predict the multiple outcomes. ... there would be two diffusion models, one for passes and another for rushes" | 25% | 15% as worded (more signal than per-outcome models on the same inputs); 50% it matches them; 60% its joint forecasts are better calibrated |
| H86 | "What if we leak some information from past outcomes like pressures or time to throw to then condition the given play? ... 'given there is a pressure on this play, plus all of the charters, what would we expect the rest of the outcomes to be?'" | 75% | 90% that it sharpens the rest a lot (it is after-the-snap information); 80% sack's share removed goes from about 1.4% to 10%+ given pressure |
| H87 | "play action definitely counts as a conditional charter as it is called before the play and planned to happen ... we can log short and quick passes as possibly strategy"; and "time to throw and adot can be interpreted as strategy rather than pure play outcomes" | 75% | 75% as worded; 60% a design label from routes lifts depth's share removed from about 18% to 30%+ |
| H88 | "The more we improve this expert the better our downfield models become, almost on an exponential path." | 50% | 10% as worded; 60% that gains are real but shrink with each extra point |
| (I93) | "Is there any room for a propensity model in this expert?" (a question; in IDEAS.md) | | 55% play action's effect on depth shrinks by a third once weighted by its propensity |

**The CEO's test for the expert:** "The context model should be judged on each outcome and how well it can fit to that outcome."

## Known before the exploration

- **The room on a yes-or-no outcome is small by nature.** Context-live's chances already spread widely: pressure from 18% to 44% (10th to 90th percentile of plays, 2023-2024), sack 3% to 10%, completion 53% to 78%. Yet those spreads remove only 1 to 4% of squared error, because a single play is a coin flip around its chance. If every play's true chance were known, the share removed would be the spread of true chances over the coin flip's own variance. Even a perfect pre-snap model of pressure would remove only about 20% if true chances ran from 5% to 60% (10th to 90th percentile). The share of squared error is the wrong scale for "how good". The exploration measures the ceiling first and reports the spread of chances and the log-loss gain beside it.
- **Information sets the ceiling, not the method.** Three tiers exist, each later than the last:
  - **In-season, before the snap:** the situation; FTN's calls from 2022 (play action, screen, RPO, motion, box, blitzers, rushers, QB location, hash). Already in context-live.
  - **After the season, chosen before the snap:** participation's coverage type and man or zone (from 2018; coding changed in 2023), formation and personnel (coding changed in 2023). This is `context-retro`'s tier (rule m), not yet used. **Corrected 2026-11-20:** participation's `route` is only the targeted receiver's route, one per play, so it belongs with the after-the-snap facts below, not here (EXPLORATION.md).
  - **After the snap, on this play:** FTN's QB out of the pocket, throw-away, catchable ball, contested ball, drop, interception-worthy, which read was thrown, and QB-fault sack (2022 on); participation's pressure and time to throw; the play-by-play's pass location (left, middle, right) and length (short, deep), and run gap and direction, from 1999. These are the conditions H86 would use.
- **Screens and sides:** FTN's screen flag starts in 2022. Left and right exist only as where the ball went (play-by-play `pass_location`) and where it started (FTN `starting_hash`), not as a planned side.
- **Ideas that fit** (the backlog read): I64 (weekly refits), I66 (blend trees and linear for the top tenth), I72 ("0 pass rushers" as missing), I71 (a defense's call pattern), I92 (expected yards after contact), I93 (propensities), the chain (context-live's method B), and `context-retro`.

## The CEO's odds

The CEO, 2026-11-20, before any test: "H85; 25%, h86; 75% h87; 75%, h88; 50%". No sizes were given.

## Methods (Claude's options, for the CEO to choose from with Claude)

The same exploration steps come first for every method: (1) the room (the ceiling on each outcome, with the spread of chances and the log-loss gain beside the share of squared error); (2) what each tier of information adds (pre-snap calls; then routes and coverage, after the season; then the play's own outcomes, after the snap). The seasons are 2022-2024 for FTN's tier: fit on the earlier seasons, scored on 2024 and on 2023 where possible. The 2025 vault stays closed. Every method is scored outcome by outcome (the CEO's test), with log loss or the range score and calibration.

| | Method | What it assumes | What it costs | What it gives |
|---|---|---|---|---|
| A | **The chain, with boosted trees** (the conventional one; context-live's method B). One model per outcome in the play's order: pressure → time to throw → sack or throw → depth → completion → yards. Each uses the calls plus the outcomes before it. Before the snap, it feeds each step the expectations of the earlier ones; "given a pressure", it feeds the real one | The order of a play is right (pressure comes before the throw); each step needs only what came before it | About one session; the existing code and libraries | Every "given X" that follows the play's order; outcomes that agree; easy to read |
| B | **One network that fills in the blanks** (masked conditioning). One model for all of a play's outcomes, trained with a random subset of them shown as inputs each time, so it can answer "given any of them, the rest" | A shared model learns the links between outcomes better than separate ones; enough plays (about 60,000 dropbacks a season) | One or two sessions; a new library (PyTorch, a technical call) | Any "given X", in any order; one model to keep |
| C | **The CEO's conditional diffusion model** (the exploratory one). It learns the joint distribution of a play's outcomes given its calls (tabular diffusion, built for mixed yes-or-no and amount columns) and answers "given X" by filling in the rest. One model for passes, one for runs | The joint shape (which outcomes come together) carries signal the separate models miss; it can be calibrated | Two sessions or more; PyTorch; scored by drawing many samples per play, so slower and noisier to score | Whole plays drawn at once (for simulation: a game simulator later), any "given X", and a full distribution for every outcome |

**The tempting bad option:** train one model on every tier, the play's own outcomes included, and score it as a before-the-snap forecast. It would explain far more than 4%, and all of it would be leak: the catchable ball says the pass was completed. What separates good from bad is which conditions are allowed for which use. Before the snap: calls only. To split blame on a play: the earlier outcomes, never the one being credited.

**Claude's recommendation:** A first, as the bar every other method must beat (rule k), then C against A on the same plays, so the CEO's method gets a fair test against the cheap one. B only if C is too slow to score.

## The brief, after the exploration (a draft for the build, 2026-11-21; for the CEO to agree)

The CEO, 2026-11-20: "Can you please draft the build for the chain and explore the blame split?" This section is the handoff to the build chat (the CEO, 2026-11-20: "This chat is reserved for vision and strategy and meta analysis for pcf. Our other chat is reserved for full builds."). It's a draft until the CEO agrees it.

**The question.** Build the chain of per-play expectations as `context-retro` (the registry's planned retrospective context expert): for every dropback 2016 on, each outcome's expectation in the play's order, in two modes, before the snap and given the real pressure, plus the blame split (which part of each sack is the pressure's and which is the QB's after it).

**Why it matters.** Before the snap, no method gets much more out of a single play (F1, F7): the room is in information, and the information after the season is retrospective. The given-pressure mode is where context-v2 found real size (sack's share 13% to 17% in every season, against 1% to 2% before the snap), and the split gives `qb-talent` and `line-play` an owner on each part of a sack (F13, F14). The in-season `context-live` stays as it is: T1 matched it (first look), and the chain adds nothing before the snap (F4).

**What the exploration settled:**

| Use | Ignore |
|---|---|
| Boosted trees, one per outcome, in the play's order (method A) | The diffusion model as a forecaster (H85 failed; parked as a simulator, I96) |
| Coverage and man or zone as inputs (2018 on): +1 point for completion and depth (F2) | The earlier steps' expected values as inputs before the snap (F4: nothing, depth worse) |
| The given-pressure mode for time to throw, sack, depth, completion, yards (F3; nine seasons in the fourth look) | Time to throw as a condition for the sack: it is missing on 98% of sacks (F6) |
| A sack counted as a pressure, in every season (the fourth look's data fact) | Participation's `route` as a play design: it's only the target's (F6) |
| The split: pressure part (E1 - E0) and after-pressure part (sack - E1), summed by player | An offense's quick-pass rate as a forecast input (I95 failed) |
| | Adjusting a QB's season rates for the calls: it changes nothing (F16, H84) |

**The terms.**
- **E0:** an outcome's chance (or expected value) before the snap, from the calls.
- **E1:** the same, given whether the play had a pressure.
- **The pressure part:** E1 - E0 for the sack: how much the pressure, or its absence, moved the sack chance.
- **The after-pressure part:** the sack (0 or 1) minus E1: what happened once the pressure was known.
- The two add up to the sack over expected (sack - E0).

**Assumptions.** The play's order is pressure, then time to throw, then the sack or the throw, then depth, completion and yards. Participation's pressure is a consistent judgment within each provider (2016-2022, 2023 on). Retrospective data feeds in-season models only from completed seasons (rule m).

**Goals for the build.**
1. `context-retro`, retrospective cadence: walk-forward E0 and E1 for the six dropback outcomes, 2017-2024 (participation's outcomes trained within their provider, as in decision 0038), and the 2025 vault once.
2. The split per dropback, and summed per player-game for the passer and the five linemen (player_game output).
3. Hand the QB's after-pressure part and sacks per pressure (fixed denominator) to skill-over-expected's trait table, replacing its "sacks per pressure, until I90" row (FINDINGS F20).

**Tests (proposed by Claude; what counts as success is the CEO's call):**
- **The no-noise target** (rule k), outcome by outcome (the CEO's test): each walk-forward E0 beats a shuffled copy of itself and the training mean on held-out seasons, in log loss or squared error, with calibration by tenths.
- **The given-pressure mode:** E1's sack log-loss gain over E0 is 25% or more in every held-out season (the first look: 33%).
- **The split, out of sample:** with walk-forward chances, the QB's after-pressure part still repeats 0.2+ and QB movers keep half (F13 replicated).
- **H88's test, the downstream gain:** does the crude forecaster's yards forecast improve when context-retro's season priors replace context-live's? (H88 is open: the CEO's 50%, Claude's 10% as worded.)
- **Failure:** E0 doesn't beat the shuffled copy, or the split's owners don't hold out of sample. Then context-live alone ships, and the split stays a discovery.

**Inputs and outputs.**
- **Inputs:** play-by-play; participation (pressure, time to throw, rushers, box, coverage, man or zone; retrospective); FTN's calls where charted (2022 on); the on-field map; the main-team table.
- **Outputs:**
  - `outputs/context-retro/<run_id>/history.parquet`: the standard schema, keyed by game and play, with quantities `<outcome>_e0` and `<outcome>_e1`, plus `sack_pressure_part` and `sack_after_part`;
  - `player_game.parquet`: each passer's and lineman's sums of the parts, dropbacks and pressures.
- **Cadence:** retrospective; a season's rows are known after its participation release.

**How it will be used.**
- By `qb-talent` (sack avoidance after pressure, as the QB's) and `line-play` (the pressure part, as the line's and the scheme's, not one lineman's).
- By skill-over-expected's trait table.
- By later in-season models, as priors from completed seasons.

**Technical calls (Claude's, for the CEO to veto before the build starts):**
1. One model per outcome and mode, trees with context-live's settings. Seasons without a field (coverage before 2018, FTN before 2022) get it as missing, not a separate edition per era.
2. Participation outcomes and the pressure condition trained within their provider; the sack and completion from play-by-play trained on every earlier season.
3. A sack counts as a pressure in every season; dropbacks with the flag missing otherwise are left out of E1's training and scored with E0 only.
4. Fix the main-team table's tie-break, so movers don't change between runs.
5. The ladder for each outcome: the training mean, then linear, then trees, keeping a rung only if it beats the one below on held-out seasons (rule k).

**Plan.** One build session in the build chat, after the CEO agrees this section. It starts from this brief, EXPLORATION.md (four looks), decisions 0038 and 0039, and the registry.
