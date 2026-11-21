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

### First look: the results ([`explore/first_look.py`](explore/first_look.py), output [`first_look.txt`](explore/first_look.txt))

21,740 dropbacks in 2023 (training), 21,030 in 2024 (scored). Coverage is charted on 100% of 2024's dropbacks, the target's route on 97% of attempts. **Sanity:** T1 here, trained on 2023 alone, matches the shipped context-live on the same 2024 plays: pressure 4.3% against 4.2%, time to throw 17.3% against 17.4%, depth 17.3% against 17.8%, completion 3.6% against 4.2%.

**Each outcome by tier, 2024** (the share of squared error removed against 2023's average; for chances, the log-loss gain and the spread of chances, 10th to 90th percentile):

| Outcome | T1 calls | T2 + coverage | Chain, before the snap | T2 + real pressure | Given, all earlier | Hindsight (the room) | Fitting noise (sd) |
|---|---|---|---|---|---|---|---|
| Pressure | 4.3% (18-44%) | 4.2% | 4.2% | | | 29.9% | 0.11 |
| Time to throw | 17.3% | **17.5%** | 17.5% | **29.2%** | 29.2% | 65.0% | 0.27 |
| Sack | 1.1% (2-12%) | 1.2% | 1.2% | **16.8%** (0-25%) | 69.2%* | 83.0% | 0.13 |
| Depth of target | 17.3% | **18.5%** | 18.1% | 18.7% | 27.0% | 78.1% | 0.28 |
| Completion | 3.6% (53-77%) | **4.6%** | 4.7% | **7.7%** | 16.7% | 87.4% | 0.16 |
| Dropback yards | 2.1% | 2.2% | 2.1% | **6.6%** | 72.2%* | 73.4% | 0.15 |

\* **Leak by a missing value, not a finding:** time to throw is charted on 94% of non-sack dropbacks and on 2% of sacks, so "given time to throw" tells the model it wasn't a sack. Dropback yards given the completion and the depth is close to arithmetic. The clean numbers for H86 are the "T2 + real pressure" column.

**The paired comparisons** (the gain in % of the simpler model's loss, 90% interval from resampling weeks):

| Outcome | Coverage beyond the calls | The chain beyond T2 | Real pressure beyond T2 |
|---|---|---|---|
| Pressure | -0.02% (-0.10 to +0.07) | 0.00% | |
| Time to throw | **+0.17%** (+0.05 to +0.28) | +0.05% (-0.05 to +0.16) | **+14.1%** (+12.8 to +15.6) |
| Sack | +0.10% (-0.20 to +0.40) | -0.11% (-0.41 to +0.18) | **+33.0%** (+31.2 to +34.8) |
| Depth of target | **+1.50%** (+1.24 to +1.79) | **-0.55%** (-0.79 to -0.33): worse | +0.21% (+0.04 to +0.37) |
| Completion | **+0.79%** (+0.51 to +1.11) | +0.10% (-0.04 to +0.24) | **+2.58%** (+2.27 to +2.91) |
| Dropback yards | +0.06% (-0.05 to +0.19) | -0.04% (-0.23 to +0.15) | **+4.56%** (+3.72 to +5.35) |

**H87, quick passes:** 25.5% of 2024's attempts are thrown within 2.5 seconds and under 5 yards downfield. T2 explains 26.5% of their squared error (log loss 21.6%), with chances from 9% to 60%. An offense's quick-pass rate over that expectation repeats **0.70** between odd and even weeks of 2024 (90%: 0.54 to 0.82; 2023: 0.57), and **0.68** from 2023 to 2024 (0.49 to 0.82). Offenses spread by 3.7 points of quick-pass rate (one standard deviation) beyond what their calls and situations explain.

### What the first look found

**F1. Before the snap, the room on a yes-or-no outcome stays small, even with coverage.** Pressure 4.2%, sack 1.2%, completion 4.6%. The amounts the calls describe are where it's large: time to throw 17.5%, depth 18.5%. The CEO's "1 to 4%" is the nature of a single play, not a weak model. Even the hindsight tier (the play's own charting) leaves pressure at 30%.

**F2. Coverage helps the throw, not the rush.** Knowing the coverage adds about 1 point of share for completion (3.6% to 4.6%) and depth (17.3% to 18.5%), both clear of the noise. It adds a little to time to throw, and nothing to pressure, sack or yards. That is about the size of one extra FTN call. It is after-the-season data, so it belongs to `context-retro`.

**F3. Within a play, pressure changes everything after it** (H86). Given a real pressure, the sack chance runs from about 0% to 25%, not 2% to 12%. Sack's share removed goes from 1.2% to 16.8%, 14 times more. Time to throw's goes from 17.5% to 29.2%, completion's from 4.6% to 7.7%, and dropback yards' from 2.2% to 6.6%. Every gain is far clear of zero. This is the blame-splitting tool: a sack or an incompletion measured "given the pressure" credits the QB with what he did after it and leaves the pressure itself to the line.

**F4. The chain adds nothing before the snap.** Feeding each step the expected values of the steps before it changes nothing for five outcomes, and makes depth slightly worse (-0.55%). The trees already see every call the earlier steps see, so an expected pressure tells them nothing new. The chain's value is only in its "given" mode (F3).

**F5. Quick passing is an offense's plan** (H87). Beyond what its calls and situations explain, an offense's quick-pass rate repeats 0.70 within a season and 0.68 from one season to the next. That is as steady as any team trait PCF has measured. It fits the CEO's reading: time to throw and depth are partly strategy.

**F6. Data facts.** Participation's `route` is only the target's route (one per play), so the play's design from all routes isn't in free data. Time to throw is missing on 98% of sacks, so any model given time to throw learns the sack from the gap.

### The hunches

| # | Verdict | Why | Real? | Pays? |
|---|---|---|---|---|
| H86 | **Held** | Given the real pressure, all four later outcomes improve clearly: time to throw +14.1%, sack +33.0%, completion +2.6%, yards +4.6% of the loss. Sack's share goes from 1.2% to 16.8% (14 times) | Yes | Not a forecast (within the play); its use is splitting the blame |
| H87 | **Held** | An offense's quick-pass rate over expected repeats 0.70 (odd against even weeks, 2024) and 0.68 (2023 to 2024); play action was already a call | Yes | Not tested |

### The odds, scored

| Bet | CEO | Claude | Result |
|---|---|---|---|
| H86 as worded | 75% | 90% | Held |
| H86: sack's share from about 1.4% to 10%+ given pressure | | 80% | Held (1.2% to 16.8%) |
| H87 as worded | 75% | 75% | Held |
| H87: the odd-even repeat 0.4+ | | 70% | Held (0.70) |
| H87: a design label from all routes | | 60% | Can't be tested (the route is only the target's) |
| Coverage adds 1+ point for completion and for depth | | 55% | Held (1.0 and 1.2 points) |
| The chain before the snap within 0.2 points of T2 on every outcome | | 75% | Failed: depth 0.4 points worse |
| The hindsight tier removes 30%+ of completion's error | | 70% | Held (87%) |

### The case against

- **One test season.** Everything is trained on 2023 and scored on 2024. A provider that changes again would move these numbers.
- **Coverage is charted from what the defense showed after the snap.** Some of its 1-point gain may be disguise resolved by the play, not the call itself.
- **"Given pressure" is only as good as the pressure flag.** It changed provider in 2023 and halved, so this provider's pressure is a stricter event.
- **Quick passes' repeat is 32 offenses.** The interval is wide (0.54 to 0.82). And the quick-pass definition uses time to throw and depth, which are partly the QB's (I89: a QB keeps 36% of his time to throw when he moves).
- **No tuning.** Trees with fixed settings. Method C or a tuned model might do better, and that is H85's test.

### Next steps (for the CEO's direction)

1. **Method C, the CEO's diffusion model, against this chain** (H85), on the same plays and tiers.
2. **The blame split as a product of this expert:** the chain's "given pressure" expectations (sack, time to throw, completion) as context-live outputs, so `qb-talent` and `line-play` can credit a QB for what he does after a pressure (I94).
3. **Quick-pass rate over expected as an offense trait** (I95): does it forecast next week's pressure allowed and sacks?
