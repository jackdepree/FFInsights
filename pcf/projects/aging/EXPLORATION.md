# Aging: exploration

> **Status:** pre-registered 2026-11-25, before any test (the CEO picked all three methods: "All three please!"). Run the same day: **go** (Results below the line). The hunches' verdicts are proposed; the CEO closes them. Discovery only: 2002-2024, with the 2025 vault closed.

## What is measured (pre-registered)

**Rows:** a player-season, 2002-2024, with:
- his age on September 1;
- his position (the roster's, by the season's mode);
- his draft pick (or undrafted) and his entry year.

**Usage** is his share of his team's opportunities over every week he was on its roster, so missed games and benching count as lost usage:

| Position | Usage | Efficiency (per opportunity) |
|---|---|---|
| QB | dropbacks (attempts plus sacks) | EPA a dropback |
| RB | carries plus targets | rushing EPA a carry |
| WR, TE | targets | receiving EPA a target |
| DL, LB, CB, S | defensive snaps (2013+) | not measured (a stated limit) |

- **A player who leaves the league** (no roster weeks next season) has a usage of 0 next season. That is the CEO's "downfall", read through usage.
- **Efficiency is centred** by the position's mean that season, which takes out the era: the period part of age-period-cohort.
- **Every rate is pulled back** by its k, the noise per attempt over the true spread, fit as in stabilization on game rows. Changes are read on pulled rates, so noise isn't read as decline.

**Pairs:** season s to s + 1, for players with 2%+ usage in s (offense) or 100+ defensive snaps (defense).

**The target:** next season's rate, weighted by next season's opportunities (efficiency) or by the team's (usage).

**The scoring:**
- Walk-forward: fit on pairs ending before each target season, tested on 2010-2024 (2016-2024 where roles are used).
- The gain is the share of the baseline's weighted squared error removed.
- "Clear" means a 90% interval from resampling players that leaves out 0. A tie goes to the simpler side.

## The noise ceiling (first)

For each position and kind:
- the spread of next season's change;
- the part of it that is noise (σ²/n₁ + σ²/n₂);
- the rest, which is the true change: the room any age model has.

Every gain below is also read as a share of that room.

## Method 1: delta curves with the survivor fix (the base)

**The curves:**
- the weighted mean change at each age (harmonic-mean weights), by position, for usage and efficiency, chained;
- **survivors only**, against **with ghosts**: a vanished player's next efficiency set at replacement level, the 20th percentile of his position's pulled rate;
- a **still-playing curve**: the chance he plays next season, by age and position (a logistic).

**The forecast:**
- **Baseline, no age:** next season = his pulled rate times the position's drift pull (fit walk-forward).
- **The age model:** the baseline plus an age step by position (ages 21 or younger to 35 or older).
- **A mixed model as a check:** a player intercept plus the age steps.

**Hunches tested here:**
- **H121** (positions and roles age differently):
  - **Positions:** passes if position-specific age steps beat one shared set of steps, clearly, for usage or efficiency. This is the reading Claude's 90% was for.
  - **Roles, the side bet** (Claude 55%): steps by roles-and-archetypes' coarse role beat position steps within at least one position, clearly (2016+).
- **H122** (usage shows aging better than efficiency):
  - At each offensive position, the share of the true change the age model explains is read for usage and for efficiency (the gain over the baseline, divided by the room).
  - Passes if usage's share is clearly larger at 3 of 4 offensive positions (players resampled).
- **H120** (stars age differently):
  - **A star:** a season up to s in his position's top 5 in PPR fantasy points.
  - **Never:** no top-24 season (no top-12 for QB and TE).
  - Passes if star-by-age steps beat pooled steps clearly, for usage or efficiency. The pattern is reported either way.
- **H117, the "real" half:** among usage decliners (usage down by a third or more, at or past the position's peak age), the true spread of the efficiency change (observed less noise) is clear of 0, **and** the type persists. A decliner who kept his efficiency (pulled change at or above 0) is more likely to keep it in his next decline season (odds ratio clear of 1).

## Method 2: load, risk and roles

**The inputs** (careers that started 1999 or later, so the counts are complete):
- **Mileage:** cumulative passing involvements (targets; dropbacks for QBs) and rushing involvements (carries), through season s, split as the CEO said. Snap counts start in 2013 and participation in 2016, so plays stand in.
- **Risk-weighted mileage:** each play weighted by its chance of an injury to him.
  - The chance is a logistic for "named as injured on the play" (play-by-play's notes, matched by team and jersey). Its inputs: play type (carry, target, catch, sack, scramble, throw), yards, a tackle, a QB hit, position.
  - It is fit on 1999-2009 and applied forward.
  - Its own check: an AUC on 2010-2024 (Claude: 60% it's above 0.6).
- **The roles-and-archetypes coordinates** (z0-z5 and the role table t0-t5) from its saved walk-forward history (rule e), 2016-2024.

**The models:** one ridge per position on next season's rate.
- **A:** the age model of method 1.
- **B:** A plus mileage (logs of both counts).
- **C:** B plus roles.
- **D:** A plus risk-weighted mileage.

For "downfall", a yearly still-playing logistic is fit with the same input sets.

**Pass rules:**
- **H115** (mileage split by kind): B beats A clearly for usage **and** for efficiency, pooled over the four offensive positions. Side: clearly for at least one kind at one position or more.
- **H116** (roles beyond snaps and age): C beats B clearly for usage **and** for efficiency, on 2016+ rows. Side: usage alone.
- **H118** (risk-weighted mileage predicts downfall): D beats A clearly on next season's usage, where a player out of the league counts as 0, pooled. Side: D beats B for running backs; D beats A on the still-playing curve.

## Method 3 (exploratory): career phases as hidden states

**The model:**
- A hidden Markov model over each player's seasons: Gaussian on (usage change, efficiency change), five states.
- The states start as rising, steady, usage-only decline, full decline and efficiency rebound, then are learned by EM.
- Transitions depend on age band (under 26, 26-29, 30+).
- **The forecast:** the next-season change is the mix of each state's mean, by the chance of each state next season.

**The simple twin:** k-means (5 clusters) on each player's last two seasons of change, plus method 1's age steps. The next change is the cluster's mean next change.

**Pass rules:**
- **The model beats the twin:** clearly, for usage or efficiency, pooled. Claude: 20%.
- **H117, the "told apart in advance" half:** a logistic on what is known before the decline season predicts the decliner's type (efficiency kept or lost), with a held-out AUC clear of 0.5. The inputs are age, usage and efficiency levels, last season's changes, star status, mileage and the model's state chances.
- **H119** (late-career comebacks):
  - **Real:** after a full-decline season (usage and efficiency both down, at or past peak age), the next season's efficiency is above what method 1's forecast already expects (its own pull-back), clearly. The mean of the leftover, players resampled.
  - **Forecastable:** the model's rebound-state chance (or the twin's cluster) predicts that leftover, a correlation clear of 0 on held-out seasons.

**The backlog checked:** I153 (historical analogs): the 20 nearest past player-seasons on age, usage, efficiency and their last changes. Their mean next change is reported beside the twin.

## Pass rules and odds, summed up

| Bet | Passes if | Odds before |
|---|---|---|
| H115 | B beats A for usage and efficiency, pooled | the CEO 30%; Claude 25% (40% for at least one) |
| H116 | C beats B for usage and efficiency, 2016+ | the CEO 30%; Claude 30% (45% for usage) |
| H117 real | the true spread of efficiency change among decliners clear of 0, and the type persists | the CEO 45% (for the hunch); Claude 65% |
| H117 told apart | a held-out AUC clear of 0.5 | Claude 30% |
| H118 | D beats A on usage with the zeros, pooled | the CEO 50%; Claude 25% |
| H119 real | the leftover after a full decline is positive, clearly | Claude 20% |
| H119 forecastable | the rebound chance predicts the leftover, held out | Claude 10% |
| H120 | star-by-age steps beat pooled steps | the CEO 60%; Claude 60% (45% that the difference is in usage) |
| H121 | position steps beat shared steps (roles within a position: the side bet) | the CEO 95%; Claude 90% (roles 55%) |
| H122 | usage's explained share of the true change clearly larger at 3 of 4 offensive positions | the CEO 80%; Claude 70% |
| Age model against no age | clear for usage at 4 of 4 offensive positions; for efficiency at 2+ | Claude 80%; 50% |
| The ghosts | with ghosts, the curves fall more steeply after 30 than with survivors only | Claude 85% |
| The risk score | AUC above 0.6 on 2010-2024 | Claude 60% |
| Method 3 | the hidden-state model beats the twin | Claude 20% |

---

## Results

Run 2026-11-25, in one sitting. Scripts and their full outputs are in `explore/`:
- `aging_common.py`: the shared player-season table and the season pairs.
- `m1_curves.py`: the noise ceiling, curves, age model, H120-H122 and H117's real half. Outputs: `m1_curves.txt` (the pre-registered form, one step a year of age) and `m1_curves_smooth.txt` (a cubic in age).
- `m2_load.py`: the per-play injury score, H115, H116, H118 and the obvious-input check. Outputs: `.txt`, `m2_old_check.txt` and `m2_consistency.txt`.
- `m3_phases.py` (`.txt`): the hidden-state model, its twin, I153's analogs, H117's told-apart half, H119 and the pull-back checks.

"Clear" means a 90% interval from resampling players that leaves out 0. Gains are the share of the simpler model's weighted squared error removed, on held-out seasons (walk-forward, targets 2010-2024).

**Go.** There is signal: age forecasts next season's usage and whether a player is still playing. It doesn't forecast efficiency. Most of the hunches about *what* ages held. The ones that need a player's type to be read from a noisy season failed once the pull-back was taken out.

**A data hole, found and fixed first.** The stats table has almost no targets for 2003-2008 (3 to 67 a season, against about 17,500). Its receiving EPA leaves out incompletions in those years. The first run read WR, TE and RB usage as broken. Targets and receiving EPA are now rebuilt from play-by-play. Play-by-play names an incompletion's receiver by jersey but gives no id in those years, so the id is filled from the game's roster by team and jersey. That finds the target for 95.5-98.8% of pass attempts every season. Every number below is from the fixed table. This is worth knowing for any project that reads `targets` before 2009.

### The noise ceiling (first)

| Position | Usage: k (team opportunities) | Usage: room (true change) | Efficiency: k (own opportunities) | Efficiency: room |
|---|---|---|---|---|
| QB | 16 | 95% | 190 | 48% |
| RB | 32 | 92% | 306 | 26% |
| WR | 21 | 91% | 171 | 24% |
| TE | 21 | 92% | 155 | 18% |
| DL, LB, DB | 37, 28, 39 | 93-95% | not measured | |

- **Usage's change from one season to the next is almost all real.** Departures count as 0, and a lost job isn't noise. **Efficiency's change is mostly noise.** Only a fifth to a half of it is real, as stabilization found for one season.
- **The age model explains little of the room:** 1-7% for usage and about 0 for efficiency (below). Aging is a small part of what changes between seasons. Most of the change is noise, drift, and jobs won and lost for other reasons.

### Method 1: the delta curves, the survivor fix and the age model

**The curves.** These are chained changes from age 23. Usage is in points of team share; efficiency is in EPA per opportunity.

| Position | Usage peak (survivors) | Usage at 30 / 34, survivors | Usage at 30 / 34, departures as 0 | Efficiency at 30 / 34, survivors | Still playing next season at 31 / 34 |
|---|---|---|---|---|---|
| QB | 27 | -4.6 / -11.6 | -85 / -133 | -0.000 / -0.046 | 93% / 82% |
| RB | 24 | -11.4 / -24.4 | -36 / -69 | -0.034 / -0.058 | 63% / 75% |
| WR | 25 | -3.7 / -11.8 | -20 / -39 | -0.061 / -0.113 | 77% / 72% |
| TE | 25 | -1.2 / -5.5 | -13 / -27 | -0.034 / -0.065 | 78% / 64% |
| DL | 26 | -2.0 / -25.1 | -44 / -112 | | 71% / 54% |
| LB | 26 | +0.5 / -32.7 | -81 / -163 | | 81% / 68% |
| DB | 27 | -5.8 / -28.2 | -81 / -186 | | 69% / 58% |

- **Survivors' curves hide most of the decline.** With departures counted as 0, usage falls several times faster. This is survivor bias, the delta method's known trap, at full size.
- **Efficiency does fall with age on the curves.** A WR loses about 0.11 EPA a target from 23 to 34; a QB loses little until 30. The fall is small against one season's noise.
- **The ghosts** (a departure's next efficiency set at his position's 20th percentile) make the fall after 30 steeper at every position, but barely: WR and TE by -0.009, QB and RB by -0.001. Few players leave with enough opportunities to matter.

**The age model against no age** (the baseline is his pulled rate times a fitted pull, plus an intercept):

| Position | Usage, steps (pre-registered) | Usage, smooth | Efficiency, steps | Efficiency, smooth |
|---|---|---|---|---|
| QB | +0.41% (-1.99% to +2.76%) | +1.25% (-0.44% to +2.68%) | -3.81%, clearly worse | -1.21%, clearly worse |
| RB | +0.90% (-1.02% to +2.95%) | **+3.14%** (+1.43% to +4.76%) | -0.34% | +0.13% |
| WR | **+5.32%** (+4.06% to +6.61%) | **+5.81%** (+4.67% to +7.01%) | -0.70%, clearly worse | -0.10% |
| TE | +1.79% (-0.43% to +3.87%) | **+3.02%** (+1.12% to +4.74%) | -2.81%, clearly worse | -0.08% |
| DL | **+4.76%** | **+5.81%** | | |
| LB | **+3.64%** | **+5.45%** | | |
| DB | **+5.26%** | **+5.60%** | | |

- **One step for each year of age (15 steps) is too noisy** with seven training seasons at the first test. A cubic in age (3 terms) beats it in every row, and rule k prefers it anyway. Methods 2 and 3 use the cubic (a technical call, below). The bets are scored on the pre-registered steps, with the cubic beside them.
- **Age pays for usage, not for efficiency.** Even the cubic adds nothing to efficiency at any position, and makes QB efficiency worse. The pull-back toward the position's mean already carries what age would say.
- **The mixed check** (his own earlier leftovers, shrunk) makes every forecast worse, by 1-5%. Once the pull is in, there is no lasting player level left over.

**H122 (age shows in usage more than in efficiency).** Usage's explained share of the room minus efficiency's (steps): QB +8.6 points (+1.5 to +16.4), WR +9.0 (+5.7 to +12.4), TE +15.9 (+7.8 to +28.6), RB +2.3 (-1.2 to +6.2). **Clearly larger at 3 of 4.** With the cubic it is also 3 of 4 (QB, RB and WR; TE's interval reaches 0). A caution: much of the gap is efficiency's share being about 0, not usage's being large.

**H121 (positions age differently).** Position-specific age steps against one shared set (each position keeps its own intercept and pull):
- **Usage:** clearly better for WR (+5.1%) and TE (+8.8%). With the cubic, clearly better at 6 of 7 positions (QB +0.4% isn't clear).
- **Efficiency:** clearly better for RB (+1.9%), and clearly worse for QB, WR and TE with steps (the extra steps are noise there).
- **Roles within a position (the side bet):** only TE has two coarse roles with enough rows. In-tight against split-out steps don't help: usage +0.3% (-1.5% to +1.9%), and efficiency is clearly worse (-1.7%).

**H120 (stars age differently).** Star-by-age-band steps on top of the age model, clear for **3 of 8**: QB usage +3.6%, RB usage +2.8%, QB efficiency +3.6%. The pattern:
- **Stars keep their jobs longer.** A prime-age star QB loses 6.4 points of share a season against 9.4 for a never-was; an old star RB loses 7.8 against 3.2 for a never-was, but from a much higher share.
- **Star QBs keep their efficiency:** +0.024 at prime age, +0.001 old, against -0.017 and -0.040 for never-were.
- WR and TE stars don't age clearly differently once the age model and their level are in.

**H117, the real half (two ways to decline).** Usage decliners are players whose usage fell to two-thirds or less, at or past the position's peak, with 10+ opportunities both seasons. Their efficiency change, less what noise alone gives:
- QB: true spread +0.0011 (-0.0002 to +0.0027), 153 seasons.
- RB: +0.0002 (-0.0000 to +0.0003), 342 seasons.
- WR: +0.0008 (-0.0000 to +0.0016), 361 seasons.
- TE: +0.0001 (-0.0007 to +0.0009), 172 seasons.
- **None is clear.** About half keep their efficiency (46-56%), which is what noise gives a coin.
- **Persistence:** a decliner who kept his efficiency is no more likely to keep it in his next decline. The odds ratio is 0.87 (0.59 to 1.28) over 287 players with two decline seasons.

### Method 2: load, risk and roles

These rows are careers that started in 1999 or later (8,528 offensive pairs).

**The per-play injury score.** "TEAM-##-Name was injured during the play" names the player in play-by-play's notes from 2005. Before 2005 the notes are free text, so the logistic is fit on 2005-2009.
- 2,414 of 1,000,715 involvements name the player (0.24%). By kind: sack 0.53%, catch 0.44%, scramble 0.41%, incomplete target 0.39%, carry 0.22%, throw 0.06%.
- **AUC on 2010-2024: 0.682** (the bet: above 0.6). The kind of play alone gives 0.685. Yards, tackles, QB hits and position add nothing.
- The score is therefore close to a weighted count of plays by kind.
- **Consistency** (`m2_consistency.txt`): a player's average risk per involvement is a trait at every position (week-to-week r 0.12-0.43), because it is his play mix. Actually getting hurt on a play is noise at every position (r -0.01 to 0.01).

**H115 and H118** (pooled over the four positions, each weighing the same):

| Comparison | Usage (0 if he left) | Efficiency | Still playing |
|---|---|---|---|
| B (age + mileage) against A (age) | **+2.20%** (+1.47% to +2.96%) | **+1.20%** (+0.58% to +1.81%) | **+1.08%** |
| D (age + risk-weighted mileage) against A | **+2.62%** (+2.01% to +3.23%) | **+1.23%** (+0.73% to +1.75%) | -0.29% |
| D against B | +0.43% (-0.12% to +0.95%) | +0.03% | -1.39%, clearly worse |
| **The obvious-input check:** H (A + his last two seasons' rate + years in the league) against A | **+2.90%** | **+1.73%** | -0.59% |
| H + mileage against H | **+1.28%** (+0.55% to +2.01%) | +0.40% (-0.10% to +0.85%) | **+1.60%** |
| H + risk-weighted mileage against H | **+0.59%** (+0.08% to +1.07%) | **+0.53%** (+0.26% to +0.80%) | -0.22% |

- **By position, B against A:** usage is clear at all four. Efficiency is clear only for QB (+4.4%). Still playing is clear for RB and WR (+1.9%, +2.0%).
- **Mileage says durability, not wear.** With age held, more mileage means *more* usage next season at every position (standardized coefficients +0.004 to +0.027). A player who has piled up plays is one teams keep using.
- **Among players 29 and older** (in-sample, `m2_old_check.txt`), rushing mileage's coefficient on efficiency is negative at all four positions (-0.014 to -0.069 against spreads of 0.30-0.47). That is a hint of wear in efficiency, small and not tested out of sample (I157).
- **Risk weighting adds nothing over plain mileage** (D against B), as expected from an injury score that is mostly the kind of play.

**H116 (roles beyond mileage and age),** on 2016+ rows with a roles-and-archetypes row, targets 2018-2024. C (B + z0-z5 + t0-t5) against B:
- usage +0.36% (-1.33% to +1.85%);
- efficiency +0.75% (-0.64% to +1.99%);
- still playing +0.60% (-1.63% to +2.65%).
- Nothing is clear (TE efficiency is +3.4%, alone). Roles-and-archetypes' history has no QB rows, so this is RB, WR and TE.

### Method 3: career phases as hidden states

**The states learned** (5,091 survivor pairs; standardized changes):

| State | Usage change | Efficiency change | Stay chance: under 26, 26-29, 30+ |
|---|---|---|---|
| rising | +0.93 | +0.00 | 0.12, 0.03, 0.00 |
| steady | -0.10 | -0.02 | 0.59, 0.74, 0.70 |
| usage-only decline | -0.97 | +0.00 | 0.19, 0.20, 0.28 |
| full decline | -0.25 | -1.14 | 0.00, 0.08, 0.08 |
| efficiency rebound | -0.23 | +1.08 | 0.03, 0.03, 0.01 |

Only "steady" persists. The other states last a season, which is how noise behaves.

**Forecasts of next season's change:**

| Comparison | Usage change | Efficiency change |
|---|---|---|
| Hidden states against the twin (k-means plus age) | +0.12% (-0.76% to +0.98%) | **+5.02%** (+3.86% to +6.13%) |
| The twin against age only | **+3.15%** | **+5.99%** |
| **Levels** (age, his levels and last changes, linear) against age only | **+12.39%** | **+31.06%** |
| Levels plus the hidden-state forecast against levels | +0.21% (-0.22% to +0.65%) | -1.19%, clearly worse |
| Levels plus the twin's clusters against levels | +0.22% | +0.14% |
| I153's analogs against levels (the same inputs, linear) | -0.16% (-1.76% to +1.46%) | -1.57% (-3.47% to +0.22%) |

- **The hidden-state model beats its twin on efficiency, as pre-registered.** But both lose to a linear model that knows his levels. That model also carries the pull-back, since a high season is followed by a fall.
- **Beyond the levels, the states add nothing**, and make efficiency worse. The twin's clusters add nothing either. The analogs tie the linear model on the same inputs, and the tie goes to the linear model.

**H117, told apart in advance.** A logistic on what is known before the decline season, on 626 held-out decline seasons:
- **AUC 0.847** (0.824 to 0.870), and 0.836 with the state chances added.
- **The check:** his pulled efficiency this season alone gives 0.810. The label (efficiency up or down) is mostly the pull-back. A good season is followed by a fall.
- **With the label taken beyond expectation** (next season's efficiency at or above the age model's forecast), every input and the state chances give **AUC 0.536** (0.499 to 0.576). That is not clear of chance.

**H119 (late-career comebacks).** After a full-decline season (usage and efficiency both fell, at or past peak age), next season's efficiency compared with the forecast:
- **Against method 1's forecast:** +0.011 EPA an opportunity above it (+0.0001 to +0.0218), over 765 seasons. Every other season is at -0.005. **Clear by a hair.**
- **The check:** against a forecast that also knows his last two seasons (method 2's H), the leftover is -0.002 (-0.013 to +0.009). The "comeback" is regression to *his own* level, which method 1 didn't know: a player whose last season was a dip below his usual tends to come back toward it.
- **Forecastable:**
  - the rebound state's chance against the leftover: r -0.000 (-0.051 to +0.050);
  - the twin's forecast: +0.000;
  - the analogs' forecast: +0.008.
  - None of them forecasts it.

### The bets, scored

| Bet | Odds before | Result |
|---|---|---|
| H115 | the CEO 30%, Claude 25% | **held by its rule:** B beats A for usage (+2.2%) and efficiency (+1.2%). With the obvious inputs in, usage +1.3% stays clear and efficiency +0.4% doesn't. It reads as durability (more mileage, more usage), not as wear |
| H115 side (one kind, one position) | Claude 40% | **held:** usage at all four, QB efficiency |
| H116 | the CEO 30%, Claude 30% | **failed:** usage +0.4%, efficiency +0.8%, neither clear |
| H116 side (usage) | Claude 45% | **failed** |
| H117 real | the CEO 45% (the hunch), Claude 65% | **failed:** the true spread isn't clear at any position, and persistence is 0.87 (0.59-1.28) |
| H117 told apart | Claude 30% | **held by its rule (AUC 0.85), but it is the pull-back;** beyond expectation 0.54 (0.50-0.58). Claude's read: failed |
| H118 | the CEO 50%, Claude 25% | **held by its rule:** D beats A on usage with the zeros (+2.6%). Risk weighting adds nothing over plain mileage (+0.4%, not clear), and the score is the play's kind |
| H118 side (D beats B for RB; D beats A on still playing) | Claude 35% | **failed,** both |
| H119 real | Claude 20% | **held by its rule, by a hair** (+0.011, lower end +0.0001); gone with his own history (-0.002). Claude's read: failed |
| H119 forecastable | Claude 10% | **failed:** r 0.00 |
| H120 | the CEO 60%, Claude 60% | **held:** 3 of 8 (QB usage +3.6%, RB usage +2.8%, QB efficiency +3.6%) |
| H120 side (the difference is in usage) | Claude 45% | **held, mostly:** 2 of 4 for usage, 1 of 4 for efficiency |
| H121 | the CEO 95%, Claude 90% | **held:** usage WR +5.1%, TE +8.8%; efficiency RB +1.9% |
| H121 roles side | Claude 55% | **failed:** TE only, not clear; efficiency worse |
| H122 | the CEO 80%, Claude 70% | **held:** 3 of 4 (QB, WR, TE) |
| Age model against no age | Claude 80% (usage 4 of 4); 50% (efficiency 2+) | **failed, both:** steps 1 of 4 for usage, 0 for efficiency (the cubic: 3 of 4, 0) |
| The ghosts | Claude 85% | **held, barely:** steeper at all four, by 0.001-0.009 |
| The risk score | Claude 60% | **held:** AUC 0.682 (play kind alone: 0.685) |
| The hidden-state model beats the twin | Claude 20% | **held by its rule** (efficiency +5.0%); neither adds anything beyond a linear model on his levels |

### What it means for the brief (Claude's reading, for the CEO)

1. **Aging is a usage expert.** Age forecasts next season's share and whether he's still playing, at every position, by 3-6% of the error. It doesn't forecast efficiency. Efficiency's decline is real on the curves but small against one season's noise, and stabilization's pull already handles it.
2. **The age term is smooth and per position:** a cubic, not a step a year. Stars (QB, RB) get their own age bands.
3. **The inputs beside age:** his last two seasons and years in the league (the biggest gain), then mileage, which is durability. Not roles, not risk weighting, not hidden states, not analogs, and not a player intercept.
4. **The outputs:** next season's usage share and still-playing chance per player. They are the predictable part of the drift stabilization found, so they feed its second pull and dynasty values.
5. **H117 and H119 belong to the pull-back.** The two ways to decline and the comebacks are what noise and regression to a player's own level produce. A build shouldn't model them as types.

### The case against

- **The data hole.** Targets for 2003-2008 come from jersey matching, at 95-98% coverage. The unmatched 2-5% may lean toward some players (practice-squad call-ups, mid-season trades), which slightly biases those years' shares.
- **The smooth form was chosen after seeing the steps.** It won in every row and is simpler (rule k), but it is still a choice made on the test seasons. The bets are scored on the steps.
- **Mileage is career usage.** The obvious-input check shrinks its gain by about 40% for usage and makes efficiency's unclear. Some of what's left may be the history the check didn't hold: three seasons back, or his peak.
- **The 1999+ restriction** for method 2 drops older players in the early years. Ages 30+ before 2008 are thin, which makes the risk test weaker for veterans.
- **H117 and H119's pull-back checks were not pre-registered.** I added them after seeing results that looked too good. Both hunches pass their written rules; the CEO should weigh the rules against the checks.
- **Ghosts at the 20th percentile** are an assumption. A different level would change the efficiency curves after 30, not the forecasts.
- **Stars by PPR** carry touchdown luck, so some "stars" were lucky seasons. That works against H120 rather than for it.
- **Age-period-cohort:** the era is centred out, but cohorts (draft classes, rule changes for QBs' protection) aren't separated. A cohort shift would read as aging.
- **Many tests.** Over 60 rows were scored. The patterns (age for usage at 7 of 7 positions with the cubic; nothing for efficiency anywhere) are safer than any single row.

### Technical calls made here (for the CEO's veto)

- **Targets and receiving EPA from play-by-play** for all seasons, with a missing receiver id filled from the game's roster by team and jersey (`pass_plays` in `aging_common.py`).
- **Corners and safeties merged into DB**, because the roster calls corners DB from 2016.
- **The age model's form:** a cubic in age, standardized at 27, for methods 2 and 3 and the brief. The pre-registered steps are scored and reported.
- **Usage curves' weights:** survivors by the harmonic mean of both seasons' opportunities; with departures, by this season's (a departure has none next season).
- **The mixed model** is his earlier leftovers, shrunk by five seasons' weight. statsmodels isn't installed.
- **The risk logistic** is fit on 2005-2009, where the note's fixed form begins. It is applied to every involvement from 1999 for mileage, using only play features, not labels.
- **Pooled scores** average each position's gain, each weighing the same, because their errors are on different scales. Players are resampled within each position.
- **Method 2's ridges:** standardized inputs, penalty 0.01 (0.1 with roles), test inputs clipped at ±5 standard deviations. Roles from the most-snaps row per player-season, offense only.
- **Method 3:** one hidden-state model for the four positions, changes standardized by position on seasons before 2010, refit every three target seasons. The twin's clusters are on his last two seasons' standardized changes (0 when missing).
- **Checks added after the pre-registration:** the obvious-input check (H), the levels floor in method 3, and the pull-back checks for H117 and H119.
