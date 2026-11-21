# Context, the next version (`context-v2`)

> **Status:** draft brief, kickoff 2026-11-20; the CEO chose method A first and put routes and coverage in scope ("Ok let's start with A. I think routes and coverage should be in scope."); first look pre-registered in [EXPLORATION.md](EXPLORATION.md) (the CEO: "Next thing I want to explore is possibly another exploration or a brainstorm on how we can improve the context expert model"). It is agreed after the exploration (CLAUDE.md, lifecycle step 3). Builds on `context-live` (RESULTS.md) and its back-history (decision 0038).

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
