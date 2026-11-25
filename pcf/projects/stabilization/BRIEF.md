# Stabilization: how many attempts until a rate is real, and how far to pull it back

> **Status:** kickoff, 2026-11-25 (the CEO: "Kick off stabilization"). The usual way and two analogies are below, with what we already know. Waiting for the CEO's football claims (hunches), each with its odds; then Claude lays out two or three ways to test them, one exploratory, and the exploration runs.

## Why now

- **Everything it needs is done:** the grain tables (player-game and player-season rows from play-by-play) and the validation harness.
- **Every expert already shrinks its own way.** pace and schemes-v2 have `_shrunk` variants, opportunity-quality pulls efficiency back by one rate per position (F37), and td-expert keeps a tenth of touchdowns over expected (F64). Each answer was found once, for one measure. One shared answer (how far to trust a rate after n attempts, and how sure to be of it) would let every expert, and every new measure, start from it.
- **It's the base of player-level uncertainty.** qb-talent, the game simulator and the outcome ranges (floor, median, ceiling) need to know how wide a player's true rate could be, not just its middle.
- **A hunch waits on it:** H6 (consistent measures predict other outcomes) was first filed here. Its sharpened test now runs in I141's night build. This project answers the question underneath: how consistent each player measure is, at each sample size.

## The usual way

Baseball's sabermetrics answered this first. A rate's **stabilization point** is the sample at which its split-half reliability reaches 0.5: odd attempts against even ones, correlated across players. At that point the observed rate is half signal and half noise. The point also gives the shrink: add that many attempts at the league average to the player's own (Tango's "regress by k"), so a rate with k = 300 and 300 attempts is pulled halfway back. The same idea, written as a model, is **empirical Bayes**: a beta-binomial for yes-or-no rates (catch rate, sack rate) and a normal-normal for averages (EPA a play). Each player's estimate is a weighted mix of his own rate and the population's, weighted by how much the population really varies against how noisy his sample is.

Football writers quote the same kind of numbers: "sack rate stabilizes in about a season's dropbacks; interception rate never does; yards per carry barely stabilizes at all." They are usually computed once, for all players of a position, and against the league average.

## Two analogies

- **Insurance: credibility theory (Bühlmann).** An actuary pricing a fleet's premium mixes its own claims record with the rate for its class: premium = Z × own + (1 − Z) × class, with Z = n / (n + k) and k = the expected noise over the true spread between fleets. Two things carry over that the usual way skips:
  - **The class matters as much as the shrink.** Actuaries pull toward the right class, not toward everyone: a delivery fleet toward delivery fleets. For a player that's his role (P11: much of what repeats is role), his team or his scheme, not his position's average.
  - **Credibility can be layered:** a player toward his role, his role toward the position. A thin role borrows from the next level up.
- **Psychometrics: test reliability and item information.** A test's reliability depends on how many questions it has, and on how much each question says. A hard question separates strong from weak students; an easy one tells you little. Three things carry over:
  - **Not every attempt is equal.** A contested deep target may say more about a receiver than a screen. Counting attempts by their information, perhaps by context-live's expectation, would make a rate stabilize sooner in real attempts.
  - **Reliability changes with conditions** (measurement invariance). A rate measured before a move may not mean the same after it. H26 already found that a new team, a new coach and part-time roles break consistency.
  - **Talent drifts.** A test score from three years ago is weaker evidence than last month's. The pull-back should also forget: aging, role changes and injuries move the true rate, so old attempts should count for less.

## What we already have

**Findings: how fast things become real:**
- **Fast:**
  - pass rushers' pressures per dropback (season to season DL 0.63, OLB 0.72; movers keep 81% and 97%; F9);
  - a receiver's route mix (vertical share r 0.51, F86);
  - a new head coach's tendencies (80-90% of their level in 1-2 games, F89);
  - target share and depth, which travel with the receiver (F1).
- **Slow, or never:**
  - efficiency per chance (week to week 0.02; a player keeps 0.12 of his points over expected per chance at 20-50 chances, 0.36 at 100-200, 0.6 at 400+; F37);
  - touchdowns over expected (keep about a tenth, F64; a season of them is dice, F68);
  - yards per carry (his own past removes 4.7% of the error next season, F15);
  - running backs' catching over expected (noise, F14);
  - defensive backs' coverage (0.15 to 0.37, F19).
- **Who to pull toward:**
  - one pull-back rate per position was as good as one per player (F37);
  - players whose pattern held across teams didn't keep more (H62 failed);
  - the kept share swings by season (0.15 in 2016, 0.38-0.47 in 2018-2024, 0.24 in 2025; I104).

**Code and tables:**
- `pcf.validation.consistency`: split-half and season-to-season r with intervals.
- [`CONSISTENCY.md`](../CONSISTENCY.md): about 220 measures, mostly team level.
- The grain tables' player-game rows, and play-by-play per play from 1999, free and in season.

## The backlog that fits

- **I104:** a kept share that changes by season, set from what this season's gaps have already done.
- **I14:** ranges should widen with how much a player's share swings.
- **I52:** real but redundant traits belong in the ranges, not the middle.
- **H26** (held): the conditions that break a rate's consistency; here, they'd set where the pull-back restarts.
- **I152** (a dream): where a player's role is heading, which is the drift side of the same question.

## What it would deliver (a sketch, for the CEO to change)

For every player rate we use, by position:
- its stabilization point;
- the shrunk rate after n attempts, with an interval;
- what it's pulled toward;
- how fast old attempts fade.

All of it is known before each game and served to the other experts. The test: the shrunk rate forecasts the player's next games and the rest of his season better than the raw rate, better than one rate per position, and better than each expert's own shrink. The intervals should hold their coverage.

## The CEO's direction and hunches (word for word, before any test)

*Waiting.*
