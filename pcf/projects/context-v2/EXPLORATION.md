# Context, the next version: exploration

> **Status:** first look pre-registered 2026-11-20, before any run. The CEO, 2026-11-20: "Ok let's start with A. I think routes and coverage should be in scope." So method A (the chain, with boosted trees) comes first, and the after-the-season tier is in scope. That is the CEO's sign-off to explore it; building it as its own expert (`context-retro`, rule m) is still a build decision. The 2025 vault is untouched.

## A data fact found before the design

**Participation's `route` is one route per play: the targeted receiver's.** For example, "IN", "FLAT", "SWING", or empty on a play with no target. It is not each receiver's route, so it can't describe the play's design (all routes together). It says where the ball went, so it is an **after-the-snap** fact, like the pass location. The brief's draft said "routes per receiver"; that was wrong and is corrected there. Coverage (`defense_coverage_type`: Cover 0, 1, 2, 2-man, 3, 4, 6, 9, combo; and man or zone) is charted per dropback. It is the defense's call, though charted from what it showed after the snap. Its coding changed with the provider in 2023 (Cover 9 and combo appear), like pressure.

## First look (written before the run, 2026-11-20)

**Plays and seasons.** Dropbacks in context-live's play tables (all season types), **trained on 2023 and scored on 2024**. 2023 is the first season with one provider for pressure, time to throw and coverage (`context-live#R12`), so every tier trains on the same season and is scored on the same plays.

**Outcomes:** pressure, time to throw, sack (dropbacks); depth of target and completion (attempts); dropback yards.

**Tiers** (each adds to the one before):

| Tier | Fields | Known |
|---|---|---|
| T0 | The training season's average | |
| T1 | context-live's situation and live calls (FTN: play action, screen, RPO, motion, box, blitzers, rushers, QB location, hash, backfield, trick, sneak; shotgun, no-huddle). FTN's "0 pass rushers" with a box of 2 or fewer is set to missing (backlog idea I72) | in season, before the snap |
| T2 | + coverage type and man or zone (participation) | after the season; chosen before the snap |
| Given (H86) | + the play's own earlier outcomes, in the chain's order: pressure → time to throw → sack → depth → completion → yards | after the snap |
| Hindsight (the room) | + the target's route and FTN's charting of the play (out of the pocket, throw-away, catchable, contested, drop, interception-worthy, QB-fault sack, which read was thrown) | after the play; never a forecast |

**Method A, the chain, before the snap:** each step uses T2 plus the *expected* values of the steps before it. In training they are cross-fitted in 5 folds of games, so a step never sees its own training rows' fitted values. This is set against T2's independent models.

**Models:** histogram boosted trees with context-live's settings (`models.TREES`), classifier for a chance, regressor for an amount's mean. No tuning.

**Scores, outcome by outcome (the CEO's test), on 2024:** the share of squared error removed against T0; for chances, the log-loss gain against T0 and the spread of chances (10th to 90th percentile); a 90% interval for every comparison from resampling weeks (`pcf.validation.compare`). **Fitting noise:** T2 refit on 3 resamples of 2023's games; the spread of its share removed.

**Pass rules:**
- **H86** (the CEO 75%, Claude 90%): **held** if T2 plus the real pressure removes clearly more error than T2 (the interval clear of zero) for at least 3 of time to throw, sack, completion and dropback yards, **and** sack's share removed at least triples. Claude's size bet: sack from about 1.4% to 10%+ (80%).
- **H87** (the CEO 75%, Claude 75%), quick and short passing as a planned strategy: a **quick pass** is an attempt thrown within 2.5 seconds and less than 5 yards downfield. Held if an offense's quick-pass rate over T2's expectation repeats 0.4+ between odd and even weeks of 2024, and 0.3+ from 2023 to 2024. That makes it the offense's plan rather than what the play gave it. Claude: 70% on the odd-even bar. Claude's earlier side bet, a design label from all receivers' routes, **can't be tested**: the route is only the target's.
- **Claude's new bets** (written now): coverage adds 1+ point of share removed for completion and for depth beyond T1, 55%; the chain before the snap is within 0.2 points of T2's independent models on every outcome, 75%; the hindsight tier removes 30%+ of completion's error, 70%.
- **H85 and H88** aren't tested in this look (method C comes after A; downstream gains need the yardstick).
