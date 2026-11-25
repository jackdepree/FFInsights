# Aging: how a player changes with age, and when his career ends

> **Status:** kickoff, 2026-11-25 (the CEO: "Ok let's start the aging expert!"). Below: the usual way, two analogies, what we already know and the backlog that fits. Waiting for the CEO's hunches, before any recommendation or test.

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

*(Waiting for the CEO.)*
