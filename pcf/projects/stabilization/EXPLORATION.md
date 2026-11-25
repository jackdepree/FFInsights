# Stabilization: exploration

> **Status:** pre-registered 2026-11-25, before any test (the CEO picked all three methods: "All three"). Results are added below the line in the same file. Discovery only: 2016-2024 (2006-2024 for measures from play-by-play alone), with the 2025 vault closed.

## What is measured (pre-registered)

Every measure is a rate with a count behind it (its attempts), per player-game, regular season. Positions come from the weekly roster.

| Group | Measure | Attempts | Years |
|---|---|---|---|
| Receivers (WR, TE, RB) | targets per route (`tprr`) | routes: on the field on a dropback | 2016+ |
| | yards per route run (`yprr`) | routes | 2016+ |
| | aDOT (air yards a target) | targets | 2006+ |
| | catch over expected (caught less `cp`) | targets | 2006+ |
| | yards after the catch over expected (less `xyac_mean_yardage`) | catches | 2006+ |
| Backs (RB) | carries per run snap | run snaps on the field | 2016+ |
| | yards after contact a carry (PFR) | carries | 2018+ |
| | broken tackles a touch (PFR) | carries and catches | 2018+ |
| QBs | hit-or-sack rate faced | dropbacks | 2006+ |
| | sack rate | dropbacks | 2006+ |
| | scramble rate | dropbacks | 2006+ |
| | aDOT | attempts | 2006+ |
| | completion over expected (`cpoe`) | attempts | 2006+ |
| | pressured rate (PFR) | dropbacks | 2018+ |
| Pass rushers (DL, edge, OLB) | pressures a pass snap (PFR) | pass snaps on the field | 2018+ |
| | QB hits a pass snap | pass snaps on the field | 2016+ |
| Coverage (CB, S, LB) | targets a coverage snap (PFR) | pass snaps on the field | 2018+ |
| | catch rate allowed (PFR) | targets | 2018+ |
| | aDOT allowed (PFR) | targets | 2018+ |
| | missed tackle rate (PFR) | tackles and misses | 2018+ |
| Teams, offense and defense | hit-or-sack rate (allowed, made), pass rate over expected, shotgun rate, no-huddle rate, explosive-play rate (20+ pass, 10+ run), success rate, aDOT | plays (dropbacks for pass measures) | 2006+ |

**Why these:** each describes how a player or team plays, not a fantasy outcome (the CEO: "things that aren't exactly outcomes, but they're football real"). Each is free and known after each game. The route and on-field counts come from participation, a post-season source. The in-season version would need a live stand-in (snap share times the team's dropbacks); that is a limit for the build, not for this exploration.

## The noise ceiling (first)

For each measure:
- **The noise per attempt (σ²)** is read from how much a player's games scatter around his season rate.
- **The true spread between players (τ²)** is the spread of season rates less that noise.
- **The ceiling** is the share of next season's rate a perfect knowledge of each player's true rate would explain, at next season's attempts: τ² / (τ² + σ²/n).
- **The true rate's season-to-season correlation** is the observed correlation over the product of the two reliabilities' square roots. Under 1, the true rate drifts.

## Method 1: the usual way, drawn whole (the base)

- **The curve.** Reliability at n attempts is τ² / (τ² + σ²/n) = n / (n + k), with k = σ²/τ². The 50% point is k, the CEO's LD50. It is checked against split halves by games (odd against even) at 10, 25, 50, 100, 200 and 400 attempts. A curve fit as c × n/(n + k) shows whether reliability tops out below 1 (c < 1, drift within a season), which is the curve's steepness question.
- **The pull-back (M1):** the season rate pulled toward the position's average by k, so it is n / (n + k) of the way to his own rate. k and the average are fit on earlier seasons only.
- **Scored on:** next season's rate (weighted by next season's attempts), against the raw rate and the position's average; intervals from resampling players.

## Method 2: the hunches, and drift

**H113** (teammates prop rates up or hold them down):
- **Teammates' conditions:**
  - for receivers: the team's hit-or-sack rate allowed, the passer's completion over expected on throws to other players, and the team's pass rate over expected;
  - for pass rushers: the rest of the defense's pressure rate;
  - for coverage: the rest of the secondary's catch rate allowed.
- **Real:** a player's change in rate from one season to the next, regressed on the change in his teammates' condition (weighted, clustered by player, 90% bootstrap). Real if at least one rate's coefficient is clear of 0. Claude: 70%.
- **Pays:**
  - The forecast is M1 with the teammates' part taken out, then put back at next season's expected condition: his team's condition last season, pulled back by its own repeat, or the new team's for a mover.
  - It is scored against M1. Earlier wording in HUNCHES.md said "the raw rate"; it means the rate without teammates taken out and pulled back the usual way. That is the fair comparison, since the pull-back is the obvious input (the obvious-input check).
  - Pays if the gain over M1 is clear of 0 for at least one rate. Claude: 25%.

**H114** (a consistent measure sets where the others regress to):
- **The pull-back target:** each rate is pulled toward a target predicted from the player's other measures. Those are his last season's pulled-back rates, the ones with season r of 0.5 or more in method 1. Position is added too.
- **How it's fit:** a ridge regression fit on earlier seasons. The weight on his own rate comes from the true spread left around that target.
- **Pays:** beats M1 on next season, clear of 0, for at least one rate (Claude: 45%), or for most rates tested (Claude: 30%). Size: 1-3% of the error.

**Drift and ranges (the CEO's range and new-level questions):**
- **The model:** a local-level time series (a Kalman filter). The true rate takes a random step each game (variance q) and a larger one each offseason (q_s), and is seen with noise σ²/n. q and q_s are fit on earlier seasons.
- **Next 4 games:** forecast after games 4, 8 and 12 of a season, against the static M1 (last season's M1 updated with this season's attempts, no drift). Claude: 40% the filter beats the static version clearly for half the measures or more.
- **Ranges:** the filter's 80% ranges for the next 4 games' rate (true-rate uncertainty plus the next games' noise), scored by coverage. Claude: 60% they hold 75-85%.
- **Peak, new level or noise:** a recent-against-career gap, the CEO's example. It is his last 4 games against his rate before them; how much of the gap lasts into the next 4 games is read by the recent attempts behind it, observed against what the filter says. Claude: 50% the filter's kept share matches the observed one within 0.1 in every bin.
- **Teams:** the same at the game level. Reliability is also read quarter by quarter (odd against even quarters of the same games), the CEO's finer levels of detail.

## Method 3 (exploratory): denoising all of a player's rates at once

- **The twin (simple side under rule k):** a multivariate empirical-Bayes pull. All of a player's rates are pulled together, using how the true rates move together (their covariance, from the observed covariance less the noise). Its ranges are normal: the posterior spread plus next season's noise.
- **The diffusion model** (the CEO's push; the conditional denoiser of context-v2's second look, adapted):
  - It learns the distribution of a player's next-season rate vector given his observed vector this season, his attempts, his position and his teammates' conditions.
  - The mean of its draws is the forecast; its quantiles are the ranges.
  - It is fit on earlier seasons, the same as the twin.
- **Claude's odds:**
  - 55% the twin beats univariate M1 on at least one rate, clearly.
  - 15% the diffusion model beats the twin on next season's rates, clearly.
  - 35% its 80% ranges cover closer to 80% than the twin's.

## The side horizon: rest of career

- **The rows:** measures from play-by-play alone (2006 on), and players at the end of seasons 2010-2018 who play later.
- **The target:** his pooled rate over every later season through 2024. Careers still running are cut off at 2024: a stated limit.
- **Scored on:** M1, raw, the position's average, and M1 with the season-to-season drift folded in (the pull grows with the horizon).
- **Limits:** aging isn't built; this is a first look.

## The backlog first

- **I104** (the kept share changes by season): method 1's k fit per season is reported against the pooled k.
- **I14** (ranges widen with a player's swings): the filter's ranges already widen with fewer attempts and with q. Coverage by how much a player's games scatter is reported.
- **I52** (real but redundant traits belong in the ranges): not checked here.

## Pass rules, summed up

| Bet | Passes if | Odds before |
|---|---|---|
| H113 real | a teammate-condition coefficient clear of 0 for 1+ rate | Claude 70% |
| H113 pays (the CEO's 25%) | its forecast beats M1, clear of 0, for 1+ rate | Claude 25% |
| H114 pays (the CEO's 25%) | the conditional target beats M1, clear of 0, for 1+ rate (most rates: the side bet) | Claude 45% (30%) |
| Drift | the filter beats static M1 on the next 4 games for half the measures or more | Claude 40% |
| Ranges | the filter's 80% ranges hold 75-85% | Claude 60% |
| New level | the filter's kept share within 0.1 of the observed in every bin | Claude 50% |
| Twin | beats M1 for 1+ rate | Claude 55% |
| Diffusion | beats the twin, clearly; ranges closer to 80% | Claude 15%; 35% |

"Clear of 0" means a 90% interval from resampling players, or teams for team measures. A tie goes to the simpler side (rule k).

---

## Results
