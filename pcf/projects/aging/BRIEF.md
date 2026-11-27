# Aging: how a player changes with age, and when his career ends

> **Status:** kickoff, 2026-11-25 (the CEO: "Ok let's start the aging expert!"). The CEO's hunches H115-H122 are in, word for word (2026-11-25), with Claude's odds. The CEO's odds for H117 (45%) and H122 (80%) added 2026-11-25; H119 has none. Three ways to test are below; the CEO picked all three (2026-11-25: "All three please!"). The exploration is pre-registered in `EXPLORATION.md`; it ran 2026-11-25 (go), and the CEO closed its verdicts 2026-11-27. The brief below was drafted 2026-11-27, with W16's "What we expect" frame; three questions are open for the CEO before it is agreed.

## Why now

- **Stabilization just found the gap.** A player's true rate moves between seasons. Its season-to-season r runs from 0.53 (catch over expected) to 0.97 (carries a run snap). Stabilization's build treats that move as random. Aging is the part of it we can predict.
- **Stabilization's rest-of-career forecasts left age out** (`stabilization/EXPLORATION.md`, the side horizon: "aging isn't built").
- **It feeds the products closest to fantasy:** fantasy projections, dynasty values and career-snaps all list it as an input.
- **Everything it needs is free and ready:**
  - play-by-play from 1999, and weekly snap counts from 2013;
  - participation, 2016-2025, post-season;
  - birth dates from the players file;
  - draft year and pick;
  - stabilization's k per rate, which says how much of each season's change is noise.

## The usual way

- **The delta method (baseball first: Tango, Lichtman).**
  - Pair each player's consecutive seasons and take the change in a rate from age a to a + 1. Weight each pair by the smaller of the two seasons' playing time.
  - Average the changes at each age and chain them into a curve.
  - Players who decline get cut and drop out of the pairs (survivor bias), so the raw curve declines too slowly. The usual fix adds a "ghost" season at replacement level for players who vanish.
- **The other common way: a mixed model.** Each player gets his own level and the position shares a smooth curve in age. Bayesian versions also separate the era from the age.
- **Projection systems (Marcel, PECOTA, ZiPS) apply the curve** as a last step on a weighted, pulled-back baseline. PECOTA instead forecasts from the paths of similar past players.
- **In football, the folk numbers:**
  - running backs peak at 24-26 and fall off "the cliff" near 28;
  - receivers peak at 26-28;
  - tight ends and QBs peak later (QBs into their 30s).

  These are usually fit to fantasy points, not to the rates underneath. The rates likely age at different speeds: playing time and role against efficiency.

## Two analogies

- **Demography: life tables and the age-period-cohort problem.** Actuaries read mortality by age, and three things carry over.
  - **Survivor bias** is their healthy-survivor effect: the old who remain are the fit ones. A career's end is its own curve, the chance he is still playing next season, and it can be fit as a hazard (survival analysis).
  - **Age, period and cohort can't all be read apart.** A player's age, the season (era: league rates drift, as stabilization had to centre for) and his draft class are tied: season = draft year + years in. A curve fit naively mixes all three.
  - **Cohorts differ.** A class drafted into a passing league may age differently from one drafted into a running league.
- **Engineering: the bathtub curve and fatigue by load.** A machine's failure rate is high when new (break-in), low in its useful life and rising at wear-out. Wear-out often follows load, not the calendar: a bearing fails by its cycles, not its years. Two things carry over.
  - **Mileage against age.** A running back's decline may follow his carries and hits, not his birthday: the "mileage" lore, testable.
  - **Early volatility.** A young player's level moves fast (break-in), then settles. That would show as more drift in years 1-3 than later, which stabilization's filter could read as a changing q by career year.

## What we already have

**Findings that touch age:**
- **H30 (held, small):** within a coach's stint, a rookie QB's season runs 2.5 points less pass rate over expected. Receivers, linemen and tight ends add 0.3 to 0.5 points a year of age. Pace: nothing clear (player-pace#F7).
- **participation#F29:** age adds nothing to a next-game snap share forecast once recent games are in. Within a season, age is already in the recent games.
- **availability#R14:** age is one input to the healthy-rate model. **H93 (held):** age is one of the inputs that say how long an injured player is out.
- **F87:** a rookie receiver's measurables place him on the slot-or-outside axis, not much else.
- **Stabilization (merged 2026-11-25):**
  - each rate's k, so a season's change can be read as true change against noise;
  - true rates drift between seasons;
  - its rest-of-career horizon, for a target.

**Code and data:**
- the grain tables (player-game and player-season);
- stabilization's `explore/stab_common.py` (20 player rates, centred by position and season);
- `old/`'s career averaging (`docs/OLD_INVENTORY.md`), as a reference only.

## The backlog that fits

- **I152** (a dream): role drift, where a player's role is heading. It is the role side of aging.
- **I153** (a dream): historical analogs, the 20 nearest past player-seasons. This is PECOTA's way. *Killed 2026-11-27: they tie a linear model in the exploration.*
- **I156:** the second pull elsewhere. An age-shaped drift is a sharper second pull.
- **H26** (held): moves and new coaches break consistency. A move at 30 may not mean what a move at 24 does.

## What it would deliver (a sketch, for the CEO to change)

For every position and every rate we use (usage, efficiency, availability):
- the expected change from one age to the next, with a range;
- the chance he is still playing next season, and the season after;
- how the change differs by mileage, draft pedigree or era, if it does.

It updates between seasons, from completed seasons only. It serves next-season priors and the career horizon to stabilization, the fantasy projections and dynasty.

## The CEO's direction and hunches (word for word, before any test)

**The CEO, 2026-11-25:** "I would be 30% confident that cumulative snaps split between passing and rushing predict efficiency and usage declines better than just age. I would be 30% confident that our roles and archetypes coordinates reduce the error on future decline of efficiency and usage better than just snaps and age. I would be curious to see if we can distinguish between players that observe just lower usage and maintain their efficiency as they age and between players that players that observe both efficiency and usage decreases. I would be 50% confident that weighted snaps - the risk score of an injury occurring on a play - predict downfall better than just age. I wonder if we can also predict which players have a late career comeback, some players decrease their efficiency and usage but then spontaneously increase their efficiency before retiring. I would be 60% confident that top players - those who score extremely high outcomes for at least one season - decline on a different pattern - usage and efficiency trends - when compared to career backups or players that never accomplished high outcomes. I am 95% confident that some positions and roles (coordinates) age differently. I would say the best measure of decline because of age would be usage rather than efficiency, because efficiency is so closely tied with teammate performance."

### The hunches (the CEO's odds; the wording "as read" is Claude's, for the CEO to confirm or edit)

"Better than just age" is read the same way each time: the forecast of next season's change with the new input added to age clearly beats age alone. It is scored on held-out seasons, players resampled, a tie going to age alone. "Decline" is read as next season's change in a rate, and, for "downfall", also whether he plays next season.

| # | The claim, as read | The CEO's odds | Claude's odds (the exact claim first) |
|---|---|---|---|
| **H115** | **Mileage, split by kind:** a player's cumulative snaps, passing plays and running plays counted apart, forecast his decline in efficiency and in usage better than his age alone | 30% | **25%** for both efficiency and usage. Side: 40% for at least one, at one position or more (likeliest: running backs' usage). Mileage and age move together, and good players play more, so most of mileage is age and talent. Size: 0.5-2% of next season's error where it pays |
| **H116** | **Roles add to mileage and age:** the roles-and-archetypes coordinates reduce the error on a player's future decline in efficiency and usage beyond snaps and age | 30% | **30%** for both. Side: 45% for usage alone (the role table pays for usage elsewhere: F76, F79). Size: 0.5-2% |
| **H117** | **Two ways to decline:** players who lose usage and keep their efficiency, and players who lose both, are distinct groups, and which one a player is can be told before it happens | 45% (the CEO, after recording: "H117; 45%"; still before any test) | **Real (the two groups exist, beyond noise): 65%. Told apart in advance, better than chance: 30%** |
| **H118** | **Mileage weighted by risk:** snaps weighted by each play's chance of an injury forecast a player's downfall (his decline and his career's end) better than his age alone | 50% | **25%.** No per-play injury risk exists yet. It would be built here from play type, contact and the injury reports (availability's events), which is the cost. Side: 35% it beats plain mileage (H115) for running backs |
| **H119** | **Late-career comebacks:** some players' efficiency and usage fall, then their efficiency rises again before they retire, and which players will do it can be forecast | no odds yet (the CEO: "I wonder if") | **Real, beyond what pulling a bad season back toward his level already gives: 20%. Forecastable: 10%.** A dip followed by a rise is what noise and the pull-back produce on their own (stabilization: efficiency is mostly noise in one season), so the test must beat that |
| **H120** | **Stars age differently:** players with at least one season of extremely high outcomes decline on a different pattern (their usage and efficiency trends) from career backups and players who never had one | 60% | **60%.** Side: 45% the difference is in usage (stars keep their jobs longer as they decline), against 25% in efficiency. Selection is the case against: a star's peak is partly luck, so he regresses from it |
| **H121** | **Positions and roles age differently:** some positions, and some roles within a position (the roles-and-archetypes coordinates), age on different curves | 95% | **90%** for the claim as worded (positions alone: 97%). Roles within a position: 55% |
| **H122** | **Usage shows aging better than efficiency:** the best measure of decline from age is usage, not efficiency, because efficiency is so tied to teammates' performance | 80% (the CEO, after recording: "H122; 80%"; still before any test) | **70%** that age explains a clearly larger share of the real change in usage than in efficiency. Two cases against: usage also depends on teammates (who else is on the depth chart), and efficiency is mostly noise in a season anyway. This is also a taste call on the target: which measure aging is judged on |

**Assumptions to flag (Claude):**
- **Mileage needs counts back to each career's start.** Snap counts begin in 2013 and participation in 2016. Before that, plays from play-by-play stand in: carries, targets and dropbacks from 1999. Careers that started earlier are cut off, a stated limit.
- **Survivor bias touches every hunch.** Players who decline get cut and leave no next season. Each test also reads "still playing next season" as an outcome, or adds replacement-level seasons for those who vanish (the delta method's fix).
- **The roles-and-archetypes coordinates** are read from that project's saved walk-forward history (rule e), for the seasons it covers.

## Ways to test it (for the CEO to choose; one is exploratory)

**Every method shares one design:**
- **The rates:** usage (snap share, targets a route, carries a run snap, dropbacks) and efficiency (yards a route, catch over expected, yards after contact, cpoe and the like), each pulled back by stabilization's k before any change is read. Otherwise noise looks like decline.
- **The target:** next season's change, plus whether he plays next season at all.
- **The baseline:** the forecast with no age in it.
- **The scoring:** held-out seasons, players resampled. A tie goes to the simpler side.

1. **The usual way, drawn whole: delta curves with the survivor fix** (the base; the simple side under rule k).
   - **The curves:** the weighted change from one age to the next by position, for usage and efficiency apart, chained into curves.
   - **The survivor fix:** two versions, compared. One adds a replacement-level season for players who vanish. The other fits a separate "still playing" curve.
   - **A mixed model as a check:** each player's own level, plus a shared age curve.
   - **Tests:** H121 (curves by position, then by role), H122 (how much of each kind's real change age explains), H120 (stars against the rest) and the "real" half of H117.
   - **Cost:** a session.
2. **Load, risk and roles: what besides the calendar** (tests H115, H116, H118, H120).
   - **The inputs:** cumulative plays split by kind (passing and rushing; touches and hits for backs), a risk-weighted version, and the roles-and-archetypes coordinates. Each is added to age in a ridge for next season's change, and in a yearly survival model (the chance he plays next season).
   - **The risk score:** each play's chance of an injury, fit on play type, contact and the injury events (play-by-play's injury notes, the weekly reports).
   - **The obvious-input check:** each one beside age and last season's usage.
   - **Cost:** a session, mostly the risk score.
3. **Exploratory: career phases as hidden states** (tests H117 and H119, and the CEO's comeback question directly).
   - **The model:** a hidden Markov model over a player's seasons. Its states are rising, peak, usage-only decline, full decline and a comeback state. Each state has its own usage and efficiency trend, and the chance of moving between states can depend on age, load and role.
   - **What it gives:** a player's chance of each state next season, so it says "losing his job but still good" apart from "losing it all".
   - **Assumptions:** careers move through a few phases, and 10-20 thousand player-seasons are enough to learn them. That is the expensive part.
   - **Its simple twin:** clustering each player's last two seasons of change (usage against efficiency), with the delta curves for the rest. The model must beat the twin.
   - **The record** (P4: methods rarely win; F30, F80) says it will likely tie on forecasts. It may still be the clearest way to read H117 and H119.
   - **Cost:** a session or two.

**The backlog checked along the way:** I153 (historical analogs, PECOTA's way) as a side model in method 3, and I152 (role drift) in method 2.

## After the exploration (2026-11-25: go; `EXPLORATION.md`, Results and the 2026-11-27 follow-up)

**What it found, in one line each:**
- **Aging is a usage expert.** Age (a cubic, per position) forecasts next season's share and whether he's still playing, by 3-6% of the error at every position. It adds nothing to efficiency: stabilization's pull already carries it.
- **Survivor bias is most of the curve.** With departures counted as 0, usage falls several times faster after 30 than survivors show.
- **Beside age, the inputs that pay:** his last two seasons and years in the league (the most), then mileage. Mileage reads as durability (more mileage, more usage next season), and it holds beside a longer history (+1.6% usage, +2.8% still playing).
- **Stars keep their jobs longer** at QB and RB (+3.6% and +2.8% for usage), and star QBs keep their efficiency.
- **Positions age differently** (H121), and usage shows it more than efficiency (H122).
- **Nothing else pays:** roles (H116), risk weighting (H118's twist), hidden career phases, analogs (I153), a player's own lasting level.
- **The two ways to decline (H117) and the comebacks (H119) are the pull-back.**
- **The CEO closed H115-H122 on 2026-11-27, as proposed.**

## What we expect (W16, written 2026-11-27 for the build; the hunches came first)

**The frame: a depreciation schedule beside an inspection.** A used car's price falls on a schedule by age and mileage, and an inspection says what this car is like today.
- **Stabilization is the inspection.** It says where a player's rates are now, pulled back for noise.
- **Aging is the schedule.** It says how much a player's job typically shrinks from this age to the next, and the chance he's off the road next year.
- **Mileage works like a high-mileage car still on the road:** it was kept because it runs. More mileage at the same age means a job teams keep giving, not a body wearing out.
- **The schedule doesn't re-inspect.** Efficiency belongs to stabilization, so aging forecasts no efficiency.
- **Where it sits:**
  - **It feeds:** next season's usage prior for player-opportunity, dynasty values and fantasy projections, and a career-end chance for dynasty and career-snaps.
  - **It overlaps:** participation within a season (age adds nothing once recent games are in, participation#F29), and availability (games missed to injury). Aging's "still playing" is a career ending, not a missed game.
  - **It shouldn't redo:** stabilization's pull and k, or availability's injuries.

**The results we expect from the build** (Claude's, a middle and an 80% range, W15):
- **Next season's usage share, against the no-age baseline** (his pulled share, his last two seasons, years in the league): about +4% of the squared error at offensive positions, 80% between +2% and +6%; about +5% on defense, 80% between +3% and +7%.
- **Mileage on top:** about +1.5% for usage, 80% between +0.5% and +2.5%; clear for RB and WR, not for QB and TE.
- **The still-playing chance:** log loss better than the baseline's by about 3%, 80% between +1% and +5%. Calibrated within 5 points in every tenth.
- **Star bands (QB, RB):** about +3% for usage at those two, 80% between +1% and +5%.
- **Downstream, on the yardstick:** a small gain on the rest-of-season boards early in the season, when in-season data is thin. About +0.3% for weeks 1-4, 80% between 0 and +1%, fading to 0 by midseason.
- **Ranges:** 80% ranges covering 75-85% at every position.

Anything else the build finds goes in its report in detail. What matches this gets one line.

## The brief (draft, 2026-11-27; the CEO agrees it, and answers the three open questions first)

The build starts from this section, `EXPLORATION.md` (its Results, follow-up and technical calls) and the registry, and nothing else. It runs at night in the build session.

### The question

For each player at the end of a season: how much of his team's work will he have next season, given his age, his history and his mileage? And what's the chance he's still in the league?

### Why it matters

Every forecast of next season starts from this season and drifts. Stabilization found the drift and treated it as random. Aging is the predictable part, so next season's priors stop assuming a 31-year-old back keeps his job like a 25-year-old does. It matters most where a season-long or multi-season view is the product: dynasty values, best ball, season-long projections.

### Terms

- **Usage share:** his share of his team's opportunities over every week he was on its roster (dropbacks for QB, carries plus targets for RB, targets for WR and TE, defensive snaps on defense). Missed games and benchings count as lost usage. **A player out of the league next season has a share of 0.**
- **Still playing:** he has a roster week next season.
- **Mileage:** his career passing involvements (dropbacks or targets) and rushing involvements (carries) through this season, from play-by-play from 1999, logged.
- **Star:** a season up to now in his position's top 5 in PPR points.
- **The no-age baseline:** next season's share from his pulled share, his last two seasons and his years in the league, with no age term.

### Builds on

- **The exploration:** the cubic in age per position, survivor handling (departures as 0), mileage as durability, the star bands, and the play-by-play rebuild of targets for 2003-2008 (a fix any project reading pre-2009 targets needs).
- **Stabilization:** each rate's k, used to pull this season's rates before they're read.
- **Findings:** participation#F29 (age adds nothing within a season), F2 and F23 (a mover's share comes from his new room), H26 (moves and new coaches break consistency).
- **Code:** `explore/aging_common.py` (the player-season table, the pairs, `pass_plays`), `m1_curves.py` and `m2_load.py`. The logic moves into the package; the scripts stay as exploration.
- **Already tried, not to redo:** step-a-year curves (the cubic beats them), the mixed model's player intercept, roles, risk weighting, hidden states, analogs, and the comeback and two-kinds labels (the pull-back).

### Assumptions

- **The season is the unit.** Changes are read between completed seasons, and nothing within one.
- **Era is taken out by centring** on the position's season mean. Cohorts (draft classes, rule changes) aren't separated, a stated limit.
- **A departure is a 0,** not a missing row. Survivors-only curves are reported beside it as a check.
- **Mileage before 1999 is unknown,** so careers that started earlier get mileage from 1999 and a flag. The build reports whether the flag matters.
- **A team change isn't known at the season's end.** Aging forecasts as if he stays. Movers are scored apart in the build's report (H26), and a mover's new room belongs to player-opportunity (F23).

### Goals and the ladder (rule k: a tie goes to the simpler rung)

1. **Baselines:** the no-age baseline. The position's average share is reported for reference.
2. **Age:** a cubic in age per position, added to the baseline. This is the base that ships unless a higher rung beats it.
3. **Mileage:** logged passing and rushing mileage on top.
4. **Stars:** star-by-age-band terms at QB and RB.
5. **Trees, once, as the check:** gradient-boosted trees on the same inputs, to catch an interaction the linear rungs miss (age by mileage by position). They ship only if they beat rung 4 clearly. The exploration found the gains linear, so the expectation is a tie.
6. **The still-playing chance:** a logistic on the shipped rung's inputs, with its own ladder (baseline, age, mileage).
7. **Ranges:** next season's share as a spike at 0 (one minus the still-playing chance) plus a distribution if he plays. This is the spike form participation and availability use (decision 0014), with q10, q50 and q90.
8. **Not built:** an efficiency forecast; roles, risk weighting, hidden states, analogs and a player intercept.

### Tests (walk-forward; test seasons 2016-2024; the earlier-seasons check on 2010-2015, W14; the 2025 vault once, at the end)

- **The expert's bar:**
  - the shipped forecast beats the no-age baseline and a shuffled-age null (age shuffled within position and season, 19 copies), players resampled;
  - each rung is kept only where it beats the rung below clearly (a 90% interval clear of 0);
  - no rung adds noise.
- **The scores:**
  - next season's usage share, with departures as 0, weighted by the team's opportunities: the squared error, and the range score for the ranges;
  - the still-playing chance: log loss, and calibration by tenths.
- **Gains per season** (W13): every rung's gain for each test season, in a small table.
- **Ranges:** 80% coverage within 75-85% at every position, also by age band (under 26, 26-29, 30+) and for movers.
- **Downstream:** next season's usage share as an input to the crude forecaster's rest-of-season boards for weeks 1-4, against 19 copies.
- **Ideas tested in the build** (W17; odds in `IDEAS.md`):
  - **I157:** wear shows in efficiency through rushing mileage after 29;
  - **I158:** stars keep their jobs beyond their play;
  - **I188:** the pull-back null as a shared function in `pcf.validation`, used on the star bands and on I157 and I158, then on the past "kinds" results it names.
- **Leakage:** every model's checks run (rule c). The yardstick input is read only from aging's walk-forward history (rule e).

### Inputs and outputs

- **Cadence: retrospective** (rule m). Built between seasons from completed seasons only. In season it serves only as a prior from the last completed season.
- **Inputs:**
  - play-by-play (1999 on);
  - weekly rosters and the players file (birth dates, draft year and pick);
  - weekly snap counts (defense, 2013 on);
  - PPR points from the stats table, with targets rebuilt from play-by-play before 2009;
  - stabilization's k per rate.
- **Outputs, saved as walk-forward history in the standard schema:**
  - **player-season:** next season's usage share (mean, q10, q50, q90, the spike at 0) and the still-playing chance, known at the end of the season;
  - **position-age:** the curve table (the expected change in share from each age to the next, and the still-playing chance), as a description for the other experts.

### How it will be used

- As next season's usage prior for player-opportunity, fantasy projections, dynasty values and the crude forecaster.
- As the career-end chance for dynasty and career-snaps.
- As a candidate input to stabilization's next-season ridge for usage rates (its next version tests it).

### Open for the CEO (taste calls: your instinct first)

1. **How far ahead?** Next season only, or also two and three seasons ahead (dynasty's horizon)?
2. **Which positions?** Offense only (QB, RB, WR, TE), or defense too (DL, LB, DB: IDP, and team strength later)?
3. **The no-noise target** (yours to approve): aging is judged on next season's usage share with departures as 0, and the still-playing chance, not on efficiency or fantasy points. Approve, or change it?

### Plan

- One night's build: rungs 1-7, the ideas, the earlier-seasons check, then the vault. Then RESULTS.md with "Against the frame", the findings, the case against, the interface card and the CEO's open questions.
- The morning: the CEO's spot-check and the merge.
