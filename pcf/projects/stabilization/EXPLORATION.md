# Stabilization: exploration

> **Status:** run 2026-11-25: **go** (Results below). Pre-registered 2026-11-25, before any test (the CEO picked all three methods: "All three"). Results are added below the line in the same file. Discovery only: 2016-2024 (2006-2024 for measures from play-by-play alone), with the 2025 vault closed.

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

Run 2026-11-25, in one sitting. Scripts and their full outputs are in `explore/`:
- `m1_curves.py` (`.txt`): the noise ceiling, the curves, M1, I104, teams.
- `m2_hunches.py`: H113 and H114.
- `m2_drift.py`: drift, ranges, new levels, I14, teams game by game.
- `m3_twin_diffusion.py`: the twin and the diffusion model.
- `m4_career.py`: the rest of a career.

"Clear" means a 90% interval from resampling players (teams for team measures) that leaves out 0.

**Go.** There is signal everywhere it was looked for. The usual way is strong. A few things beat it, and each has a simpler version that does as well.

### The noise ceiling (first)

How much room there is. Per measure, from `m1_curves.txt`. All rates are centred by their position's mean that season, because league rates shift with charting and model changes; without this, catch over expected's k read 16 instead of 136.

| Kind | Measures | k: the 50% point, in attempts (the CEO's LD50) | Reliability at a typical season | Ceiling next season | True rate's season r |
|---|---|---|---|---|---|
| Usage and role | carries a run snap, targets a route, targets a coverage snap, scramble rate, aDOT | 2, 70, 67, 69, 18 | 0.69-0.98 | 0.77-0.99 | 0.78-0.97 |
| Mixed | yards a route, hit-or-sack faced, QB hits a pass snap, sack rate, cpoe | 121, 176, 179, 269, 242 | 0.50-0.60 | 0.61-0.71 | 0.68-0.86 |
| Efficiency over expected | catch over expected, YAC over expected, yards after contact, broken tackles, catch allowed, missed tackles, pressures a pass snap | 136, 95, 149, 255, 129, 220, 346 | 0.19-0.33 | 0.27-0.52 | 0.53-0.82 |

- **Efficiency is mostly noise in one season.** At a typical season (39 targets for catch over expected), a fifth to a third of the spread between players is real. Usage rates are mostly real.
- **The true rates drift between seasons.** No measure's true rate repeats perfectly (r 0.53 to 0.97). A season's reliability is therefore not next season's: there is a second pull, for drift, on top of the noise pull (below: M1 recalibrated).
- **The curve's shape.** Split halves follow n/(n + k) at small n. Several top bins fall short (targets a route at 243 routes in a half: 0.71 against 0.78 predicted), which is the within-season drift the filter finds below.

**I104 (the kept share changes by season):** k moves a lot by season. Catch over expected runs 98 to 456, cpoe 143 to 609, pressures a pass snap 241 to 815. aDOT stays at 16-19. So I104's premise holds for efficiency rates, not for usage. I104 itself (a season factor for opportunity-quality's B) wasn't tested and stays open.

### Method 1: the usual way (M1)

M1 against the position's average, on next season's rate: clear for 16 of 20 measures.
- Carries a run snap +89%, scramble rate +57%, targets a coverage snap +53%, targets a route +36%, aDOT +32%, yards a route +30%, hit-or-sack +27%, QB hits a pass snap +26%.
- Ties for 4: catch over expected (+0.8%), yards after contact, broken tackles and catch allowed. The pull-back is nearly all the way to the average, which is what k says it should be.

**Teams** (each team-season centred by its season's league rate):
- **Offense's tendencies are among the most reliable things measured.** Shotgun (k 68 plays), no-huddle (72) and pass rate over expected (194) reach 0.84-0.94 reliability in a season. Explosive-play rate has k 750, reliability 0.57.
- **The defense's "faced" rates are mostly the opponents'.** Pass rate over expected, shotgun and no-huddle faced have k of 1,477 to 3,391. Their quarter-by-quarter split (0.54-0.68) is far above their game-by-game split (0.11-0.21), because a game's quarters share one opponent. Read at the quarter level, they measure who the defense played, not the defense. The defense's own rates (hit-or-sack made k 712, success allowed 855) sit in between.

### Method 2: the hunches

**H113 (teammates prop rates up or hold them down): real, held. Pays: the rule is met narrowly, and the result is mixed.**
- **Real:** 11 of 21 coefficients are clear of 0, against about 2 expected by chance. Per a typical change in the teammates' condition:
  - a receiver's aDOT falls 0.32 yards when the team's pass rate over expected rises;
  - his catch over expected rises 1.2 points when the passer completes more over expected to others;
  - his yards a route fall 0.03 when the line allows more hits and sacks;
  - his YAC over expected moves with the line (-0.09) and the passer (+0.13);
  - a pass rusher's pressures a snap rise 0.005 when the rest of the defense pressures more (the CEO's "propped up", on defense);
  - a defender's catch allowed rises 1.1 points when the rest of the coverage allows more.

  Movers alone give the same signs and sizes. So these aren't just a team changing around a player who stayed.
- **Pays (against M1, walk-forward):**
  - Clear for 2 of 11 rates: aDOT +0.7% (90% +0.2% to +1.1%; movers +1.3%) and pressures a pass snap +0.8% (+0.4% to +1.2%).
  - Clearly worse for 2: catch over expected -0.4%, QB hits a pass snap -1.4%.
  - Ties for the rest.

  The pass rule (clear for 1+ rate) is met, but the gains are under 1% and as many rates lose as win. **Claude's read: real, pays a little and unevenly.** The teammates' part is a real input for a downstream model, not a better pull-back.

**H114 (a consistent measure sets where the others regress to): the pre-registered form fails. The idea pays in a different form.**
- **Pre-registered form** (pull toward a target predicted from the other consistent measures):
  - Clear for 1 of 18 rates: sack rate +2.5% (90% +0.8% to +4.2%), its target set by hit-or-sack and scramble rates. That is about what chance gives across 18 tests. QB aDOT (+0.9%) was clear in one bootstrap draw and not in the next.
  - Clearly worse for receivers: yards a route -1.8%, aDOT -0.7%, catch over expected -1.4%. A target that removes spread makes k grow, so the pull goes further toward a target that isn't good enough.
  - "Most rates": failed.
- **Fitting the target and the weight together works:** a ridge on his own pulled rate plus the other consistent measures.
  - Two things are inside it. **Recalibrating his own pull alone** beats M1 clearly for 12 of 18 rates: M1's within-season pull isn't next season's (the drift above).
  - **The other measures add beyond that** for 4 of 18:
    - targets a route +2.1% (from yards a route and aDOT);
    - yards a route +1.3%;
    - sack rate +3.6%;
    - pressures a pass snap +1.0% (from QB hits).

  The CEO's example, an aDOT of 14 saying where yards a route should settle, is one of the four that pay.

**Drift, ranges and new levels** (the filter fit before 2020, tested on 2020-2024's next 4 games after games 4, 8 and 12):
- **Drift: failed** (Claude 40%). The filter beats static M1 clearly for 6 of 20, under the half needed:
  - targets a route +2.7%, yards a route +1.7%, aDOT +3.9%, carries a run snap +19.6%, hit-or-sack +5.6%, QB hits a pass snap +2.9%.

  These are usage rates: roles move within a season, efficiency doesn't. For catch over expected the filter chose the grid's largest drift and lost 5.8%. A game's catch rate swings more than its targets explain, so the filter takes extra noise for drift.
- **Teams:** the filter beats static clearly for 5 of 7 offensive tendencies (shotgun +24%, no-huddle +37%, pass rate over expected +10%, success +12%, hit-or-sack +5%) and for none of the 7 defensive rates. Offenses change how they play during a season; what a defense faces is its schedule.
- **Ranges: held** (Claude 60%). The filter's 80% ranges hold 75-85% for 19 of 20 measures. Static M1's are a little narrower (69-85%).
- **I14 (ranges widen with a player's swings): graduates.**
  - Coverage falls with how much a player's games have swung so far: aDOT 92% in the steadiest third against 66% in the swingiest, scramble 87% against 63%.
  - Widening each range by his own swing (shrunk toward 1 with 20 games' weight) narrows that gap by 5+ points for 10 of 20 measures. It improves the range score for 16 of 20, by up to 4.8%.
- **New level: failed** (Claude 50%, on "every bin"). The filter's kept share of a recent gap matches the observed one within 0.1 in all three bins for 10 of 20 measures (44 of 60 bins).
  - The kept share is small: 0.12 to 0.46 of a 4-game gap lasts into the next 4 games, more with more attempts behind it. Carries a run snap keeps up to 0.73.
  - **Where the filter misses, it keeps too much:** catch over expected 0.26-0.38 against 0.16-0.23 observed, targets a coverage snap 0.37-0.45 against 0.28-0.33, pressured 0.37-0.45 against 0.15-0.37.

  The CEO's pass-rusher example, as a number: of a recent jump in pressures a pass snap, about 0.12 lasts at 72 recent pass snaps and 0.32 at 126.

### Method 3: denoising all of a player's rates at once

Receivers 2016+ and coverage players 2018+. Fit on target seasons before 2022, tested on 2022-2024.
- **The twin beats M1: held** (Claude 55%), small: clear for 2 of 9 rates (targets a route +1.1%, catch over expected +0.8%).
  - Its noise correlations are real and large: targets a route and yards a route share +0.57, yards a route and YAC over expected +0.50.
  - The true rates' correlations are larger still: targets and yards a route +0.88; catch allowed and aDOT allowed -0.69.
- **The diffusion model beats the twin: failed** (Claude 15%).
  - **First run:** a leak, caught and fixed. It was given next season's attempts, and targets over routes next season is the rate itself (+98%).
  - **After the fix:** it beats the twin clearly for targets a route (+5.5%) and yards a route (+5.9%), and loses clearly for 6 of 9.
  - **The ridge test (rule k):** a ridge given exactly the same inputs beats the twin for 4 of 9 (targets a route +9.9%, yards a route +5.1%, targets a coverage snap +7.5%, catch allowed +3.2%). The diffusion model beats that ridge for none: 7 are clearly worse, 2 tie.
  - So the diffusion model's wins were a linear pull it learned. The simple version wins. Seed to seed, its forecasts differ by up to 4% of the error.
- **Its ranges closer to 80%: failed** (Claude 35%). It was closer for 3 of 9 rates, and its average distance from 80% was 3.6 points against the twin's 3.4.

### The side horizon: rest of a career

Measures from play-by-play, players at the end of 2010-2018, the target pooled through 2024 (a median of 3 later seasons for receivers, 5 for QBs).
- **M1 on the career so far beats the raw career rate for all 8 measures (by 19-53%).**
- **Against the position's average, it's mixed:** aDOT +36%, scramble rate +46%, and catch over expected -9%.
- **Folding drift in** (the pull grows with the horizon) beats plain M1 clearly for catch over expected (+15%) and cpoe (+38%), and ties for the rest. The QB rows are few (132 players), so their intervals are wide.

### The bets, scored

| Bet | Odds before | Result |
|---|---|---|
| H113 real | Claude 70% | **held:** 11 of 21 clear (2 expected by chance) |
| H113 pays | the CEO 25%, Claude 25% | **held by the rule, narrowly:** 2 of 11 clear (+0.7%, +0.8%), 2 clearly worse; Claude's read: unclear |
| H114 pays, 1+ rate | the CEO 25%, Claude 45% | **held by the rule, by chance's margin:** 1 of 18 (sack rate +2.5%); one other rate flipped between draws. The other form pays for 4 of 18 (+1.0% to +3.6%) |
| H114, most rates | Claude 30% | **failed** |
| Drift | Claude 40% | **failed:** 6 of 20 (usage rates); teams' offense 5 of 7 |
| Ranges | Claude 60% | **held:** 19 of 20 within 75-85% |
| New level | Claude 50% | **failed:** 10 of 20 match in every bin; where it misses, the filter keeps too much |
| Twin | Claude 55% | **held:** 2 of 9, about 1% |
| Diffusion beats the twin | Claude 15% | **failed:** 2 of 9 better, 6 worse; the same-inputs ridge beats or ties it everywhere |
| Diffusion's ranges closer to 80% | Claude 35% | **failed:** closer for 3 of 9 |

### What it means for the brief (Claude's reading, for the CEO)

1. **Every rate gets its k, its reliability and a true-rate season r** (the table above, per measure). Those are the stabilization points and the expert's simplest output. Usage rates stabilize within a season; efficiency rates mostly don't.
2. **There are two pulls.** One is for noise, by k. One is for drift, by the true rate's season r and by the horizon. Every method that fit the second pull won: M1 recalibrated, the ridge, drift folded into career forecasts. That is the build's base model.
3. **In-season, a drifting level for usage rates and offensive tendencies**, static for efficiency. Ranges come from the filter, widened by each player's own swing (I14).
4. **Teammates and the other consistent rates go in as inputs**, fit together with the player's own pull (a ridge). They aren't separate adjustments. The diffusion model isn't worth building: the same inputs in a ridge do better.
5. **Defense "faced" rates are schedule**, to be read through the opponent before they say anything about a defense.

### The case against

- **Many tests.** Each bet ran over 9-21 rates, so a few "clear" results are chance. H114's single pass is that size, and H113's pays sits close to it. The patterns that hold across rates (drift for usage rates, recalibration for 12 of 18, ranges for 19 of 20) are safer than any single row.
- **Season r of 0.5 picked the "consistent" measures** after method 1 had run on the same seasons. That was pre-registered, but it is still selection on the data.
- **One train/test split for drift and method 3** (before 2020 or 2022, against after). The diffusion model had only 1,100-1,500 training rows. More data might help it, though the ridge on the same rows is the fair comparison.
- **Endogeneity in H113.** A team's pass rate over expected answers its receivers' quality. Movers help, but don't settle it.
- **The routes and on-field counts come from participation,** which is post-season. An in-season build needs a stand-in (snap share times dropbacks).
- **The defense's quarter-level reliability** is a within-game opponent effect, not a finer level of detail that works.

**H113 and H114 closed by the CEO, 2026-11-25, both held as their pass rules read:** "Yes close those hunches please."

### Technical calls made here (for the CEO's veto)

- **Centring:**
  - Every player rate is centred by its position's mean that season.
  - Team rates are centred by the season's league rate.
  - In-season, rates are centred by last season's mean, which is known before the season.
- **M1's target:** the position's mean in the latest training season.
- **H113's pays:**
  - The teammates' part is put back at his next team's condition last season, times that condition's own season-to-season slope.
  - k is kept from M1, not refit on the adjusted rates.
- **H114:** no intercept, centred by position. The conditional k is M1's k times the ratio of next season's true spread around the position mean to the spread around the target.
- **Drift:**
  - One split: fit before 2020, tested 2020-2024.
  - q and q_s are chosen on a grid by likelihood.
  - Static M1 is last season plus this one so far.
  - The 80% range adds 2.5 games' drift for the 4-game horizon.
- **Method 3:**
  - One split (before 2022).
  - The twin's diagonal is set to M1's spread, and its correlations are clipped at 0.95.
  - The noise correlations come from game halves.
  - The diffusion model: 400 passes, 2 seeds, 200 draws. Next season's attempts are left out of its inputs (the leak).
- **Rest of career:**
  - k and the true rate's correlation are fit before 2011.
  - Drift is folded in as that correlation raised to each later season's distance.
