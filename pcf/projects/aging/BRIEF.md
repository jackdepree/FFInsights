# Aging: how a player changes with age, and when his career ends

> **Status:** kickoff, 2026-11-25 (the CEO: "Ok let's start the aging expert!"). The CEO's hunches H115-H122 are in, word for word (2026-11-25), with Claude's odds. The CEO's odds for H117 (45%) and H122 (80%) added 2026-11-25; H119 has none. Three ways to test are below (one exploratory), waiting for the CEO's pick.

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
- **I153** (a dream): historical analogs, the 20 nearest past player-seasons. This is PECOTA's way.
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
