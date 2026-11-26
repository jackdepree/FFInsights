# Aging: exploration

> **Status:** pre-registered 2026-11-25, before any test (the CEO picked all three methods: "All three please!"). Results are added below the line in the same file. Discovery only: 2002-2024, with the 2025 vault closed.

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
