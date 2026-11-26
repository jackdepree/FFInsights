# Results: Stabilization and regression (`stabilization`)

**Date:** 2026-11-26 · **Brief:** [BRIEF.md](BRIEF.md) ("The agreed brief", 2026-11-25) · **Decision:** [0052](../../docs/decisions/0052-stabilization-build.md) (34 calls, for the CEO's veto) · **MLflow experiment:** `stabilization`, run `ba5c1375765a4650bce695ddb63c0dbe` ("stabilization v1") · **History:** `outputs/stabilization/ba5c1375765a4650bce695ddb63c0dbe/{player_game,player_season,team_game,team_season}.parquet` · **Build reports:** [`build/`](build/) (`players.txt`, `teams.txt`, `sides.txt`, `leakage.txt`, `history.txt`, `verdicts.json`) · **Shared code:** `pcf.validation.stabilize` (the shrink, owned here) and `pcf.experts.stabilization`

## In short

For each of 20 player rates and 14 team rates (7 per side), stabilization now says how much of the rate is real after n attempts (k, the 50% point), and where it will be over the next 4 games and next season, with an 80% range. Every forecast in the saved history is made before the game or season it forecasts, from parameters fit on earlier seasons.

**What the build found:**
- **Pulling a rate toward its position by k (M1) is the base, and it's hard to beat.** Next season it beats the raw rate for all 20 player rates (by 4.7% to 42% of the squared error) and the position's average for 17 of 20 (by 2% to 70%).
- **A second pull (one slope on M1, fit on earlier seasons) helps next season for 11 of 20** (0.6% to 5.8%), not in season.
- **The ridge** (his other consistent rates and his teammates' conditions) **adds for only 3 of 20** (1.5% to 2.7%), so the ladder stops there.
- **In season, a drifting level (the filter) beats static M1 for 5 of the 7 usage rates** (carries a run snap +20%) and **for 4 of 7 team offensive tendencies** (no-huddle +32%, shotgun +28%). For efficiency rates it ties or loses; they stay static.
- **The ranges hold:** every shipped 80% range covers 75% to 85% on the scored seasons.
- **A new lead, not shipped:** a player's change over his last two seasons (I152's trend) adds beyond the ridge for 16 of 20 rates (0.7% to 7.8%).

Against the brief: the expert's bar (beats the position's average and 19 shuffled copies) holds for **17 of 20 player rates next season** and **18 of 20 in season**. Three player rates ship the position's average, because nothing beats it: yards after contact, broken tackles a touch and pressured rate. Two of the three live stand-ins for participation's exact counts are too poor for some rates, so a retrospective sibling (`stabilization-retro`) is proposed, not built. The vault stays closed. Odds and pass rules for it are below, for the CEO to decide.

**Scorecard:** `build/players.txt`, `build/teams.txt`, `build/sides.txt`, `build/leakage.txt`, `build/history.txt`, MLflow run `ba5c1375765a4650bce695ddb63c0dbe` · **Vault:** closed, not opened (the CEO has kept it closed; odds and pass rules below) · **Versions tried:** three logged attempts: the first full run (crashed in the team history, call 34), a history rebuild stopped on purpose (call 32) and `ba5c1375765a4650bce695ddb63c0dbe`; before them, no-log runs per section.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | Every shipped rung beats all 19 shuffled copies (every input moved to another player of the same season and position), and clears the rung below on a 90% interval from 2,000 player resamples. Where nothing clears the position's average, the average ships (3 of 20 next season, 2 of 20 in season, 11 of 28 team rows: the defense's faced tendencies and efficiency mostly) |
| Calibration and range coverage | Shipped 80% ranges: 75%-85% for every rate in the report (next 4 games 78%-85%; next season 75%-83%, catch over expected after a conformal scale), and 74%-90% by thirds of reliability and of swing. The saved history's ranges use expected attempts with a walk-forward scale (call 32): on the scored rows they cover 77%-82% before each game, 74%-90% next season (catch over expected 74%, carries a run snap 90%), and 76%-92% for teams (the defense's no-huddle 91%-92%, shotgun 88%-89%) (`build/history.txt`) |
| Leakage | All passed (`build/leakage.txt`): future deletion and outcome scrambling at 8 cutoffs (0 forecasts differ in 4 measures × 8 cutoffs); next-season scrambling (0 of 750 differ); PFR's lag (0 checkpoints read a game not yet known; the lag bites at 67%-85%); known-at sanity; the code scan (3 named, expected reads) |
| Football sanity | The 2025 priors' top and bottom players are below ("Football sanity"). One flag: carries a run snap above 1 for lead backs, from the run-snap stand-in (F128). Awaiting the CEO's review |
| CEO spot-check | Pending: the CEO picks one |

**The brief's odds, scored** (written in decision 0052 before any result; "clear" = a 90% interval that leaves out 0):

| Bet | Odds | Result | Verdict |
|---|---|---|---|
| The second pull beats M1 next season for 12+ of 20 | 55% | 11 of 20 | failed, narrowly |
| The ridge beats the rung below for 4+ of 20 (1+) | 40% (75%) | 3 of 20 (yards a route +2.7%, aDOT +1.5%, pressures a pass snap +2.4%) | failed (held) |
| The filter beats static for 4+ of 7 usage rates | 50% | 5 of 7 | held |
| The filter beats static for 4+ of 7 offensive tendencies | 65% | 4 of 7 | held |
| The bar holds next season for 16+ of 20 | 60% | 17 of 20 | held |
| Every shipped range within 75%-85%, next 4 games | 50% | 18 of 18 | held |
| The same next season, before any conformal step | 35% | 16 of 17 (catch over expected 93%) | failed |
| I14's widening improves the range score for half the shipped rates (next 4 games) | 60% | 8 of 18 | failed |
| Routes stand-in close (r 0.95+) | 85% | r 0.95 and 0.97 | held |
| Run-snap stand-in close | 45% | r 0.90 | failed (as leaned) |
| Defensive pass-snap stand-in close | 55% | r 0.96 to 0.99 | held |
| At least one stand-in too poor | 40% | 4 rates (targets and yards a route, carries a run snap, targets a coverage snap) | held |
| Career: drift folded in beats M1 for 2+ of 8 | 55% | 2 (catch over expected +10.5%, completion over expected +37.1%) | held |

## Hunch verdicts

The brief's hunches (H113, H114) were closed at the exploration by the CEO, both held. The build adds evidence and changes neither:

| # | Hunch | Verdict | The build's evidence |
|---|---|---|---|
| H113 | Teammates prop rates up or hold them down | held (unchanged) | The teammates' conditions are in the ridge, which adds for only 3 of 20 rates next season (1.5%-2.7%): real, small |
| H114 | A consistent measure sets where the others regress to | held (unchanged) | His other consistent rates (season r 0.5+) are in the same ridge. Same 3 of 20; the ridge picks 0.7 to 5 of them per rate |

## Ideas tested in the build

Odds were written in `IDEAS.md` before each result. Rows closed in the same commit as this file.

| Idea | Odds before | Result | Closed as |
|---|---|---|---|
| **I154** a game-noise factor for efficiency rates | 55%: factor > 1.2 for catch over expected and the filter then ties static for 3 of 4 | Factor 1.10 for catch over expected, 1.00-1.07 elsewhere; catch over expected still loses 5.5% (−6.8 to −4.2). 3 of 4 tie or beat static, but with a factor of 1, so the factor isn't the reason | **Killed:** the extra game noise isn't what breaks the filter for catch over expected |
| **I182** the extra noise as a fixed amount | 40% | Ties I154 (within 0.1% for 3 of 4); the same 3 of 4 tie static | **Killed** |
| **I155** a defense's faced rates, less its opponents' usual | 60% the game split rises above 0.3 for 1+ rate; 30% for pass rate over expected | Split up for 6 of 7 (pass rate over expected 0.21 → 0.32, shotgun 0.19 → 0.32, success 0.38 → 0.44); k falls a third to a half; season r doesn't rise (0.30 → 0.27 and 0.24) | **Held (real), pays untested.** Graduated into CONSISTENCY; the forecast test is I183 |
| **I156** the second pull elsewhere | 50% it helps 1+ shipped expert clearly | skill-over-expected: 2 of 15 trait-groups (its build). Opportunity-quality's method B: ties (−0.2%, −0.7 to +0.4); tight ends −0.5% | **Graduated:** `pcf.validation.stabilize.second_pull`, used by both experts; B keeps its own shrink |
| **I152** (this build's form) his change over his last two seasons, added to the ridge | 30% clear for 1+ usage rate; 0.5%-2% | Clear for all 4 usage rates (+2.7% to +4.8%) and 16 of 20 overall (+0.7% to +7.8%) | **Held, and bigger than expected.** Not shipped in v1 (a question for the CEO); the original form (role table, player-opportunity) stays open |
| **I181** layered credibility (his team's rate at his position, then the position) | 35% clear for 2+ usage rates | Worse for 17 of 20 (clear for 14); carries a run snap ties (+0.4%) | **Killed:** F37 holds; pull toward the position |
| **I173** (this build's form) a movers' own slope | 30% clear for 1+ of 20; 10% for 5+ | 1 of 20 (catch over expected +0.2%); 3 clearly worse; the shared second pull already helps movers (+1% to +8% over M1 for 13 of 20) | **This form killed;** the row stays open for edge pressure's new-team gain on 2025-2026 |
| **I174** a target shrink slope per position | 35% over all stayers; 50% for tight ends | −0.1% (−1.8 to +1.7); tight ends −0.5% (−5.5 to +4.1); beats 14 of 19 copies | **Killed:** the one shared slope (I165) stays |
| **I104** (this build's form) this season's k, blended with the pooled k | 20% clear for 1+ efficiency rate | None clear better; 5 of 8 clearly worse (broken tackles −2.2%) | **This form killed;** B's season factor itself stays open |
| **I180** a stand-in corrected by last season's exact ratio | 60% the correlation rises 0.02+ for carries a run snap or a defensive pass-snap rate | +0.017 for carries a run snap, +0.002 to +0.005 on defense: failed narrowly. On the forecast it pays: +34% for carries a run snap, +9.6% targets a route, +6.1% yards a route | **Failed its bar, pays on the forecast.** Graduated into the stabilization-retro proposal |
| **I5** (this build's form) rookies' usage rises in their first season | 55% static M1's mean miss is clearly positive for targets a route | −0.0003 targets a route (−0.0051 to +0.0041); none of 4 usage rates clearly positive | **This form failed;** the original (fantasy points) stays open |
| **I14** widening by swing (graduated earlier) | 60% for half the shipped rates | 8 of 18 in season, 9 of 17 next season (up to +4.5% of the range score) | Kept where it clears (`ranges.widened` in `verdicts.json`) |

**Considered and not run** (open ideas read for this build):
- **I32** (pass defense needs more shrinkage than run defense): team-efficiency's EPA ratings, not a rate here. Its next build.
- **I42** (rest-of-season ranges for whole-season shifts): team-efficiency's ranges. The rest-of-season side horizon here covers 74%-90% for teams, so the problem may be smaller for rates.
- **I52** (real but redundant traits in the ranges): needs other experts' traits beside each range. I14's swing is the one range term tested here.
- **I9, I10, I11** (movers, no depth-chart slot, byes): participation's snap-share forecasts, not these rates.
- **I15, I16** (script-adjusted share, script tendencies): participation's target.
- **I21** (coach stayers) and H26's restart for coaches: coach changes aren't in the build's inputs, and the filter's new-season reset (q_s) already lets a rate jump.
- **I31** (series success rate): a drive-level team trait for pace, not a rate here.
- **I41, I54** (a new coach's defense, the QB-change lag): team-efficiency's EPA.
- **I64** (refit weekly): the filter updates after every game; its parameters are refit by season, as context-live's.
- **I93** (propensity models): schemes' calls.
- **I141** (the night build for real-but-unpaid measures): its own build.
- **I153** (historical analogs): player-opportunity's build.

## Terms

Copied into `docs/GLOSSARY.md`:
- **k, the 50% point (the CEO's LD50):** the attempts at which a rate is half signal and half noise. Reliability at n attempts is n / (n + k). Fit per rate on every position pooled, refit each season on seasons before it.
- **M1:** the rate pulled toward its position's mean by k: (n × rate + k × mean) / (n + k).
- **The second pull:** one slope on M1, fit walk-forward on earlier seasons' pairs. It pulls further where a season's reliability overstates next season's (talent drifts).
- **The filter:** a drifting level per player (a local-level Kalman filter). It moves by q a game and by q_s at a new season, both shares of the true spread, fit on training seasons.
- **Swing:** how much a player's games have scattered around his level, against the noise alone (1 = as expected), shrunk toward 1 with 20 games' weight.
- **A live stand-in:** an in-season count built from snap counts for a count only participation has after the season. Routes ≈ offensive snap share × the team's dropbacks; run snaps the same with runs; a defender's pass snaps ≈ his snap share × dropbacks faced.
- **Usage, mixed and efficiency rates:** how a player is used (targets a route, aDOT), how well it goes against expected (catch over expected), or both (yards a route).

## Findings

Numbered for citing as `stabilization#F120`. The detail is in `build/players.txt` and `build/teams.txt`.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F120 | **Usage rates become real within a few weeks; efficiency rates take seasons.** k: carries a run snap 4 run snaps, aDOT 17 targets, targets a route 48 routes, scramble rate 69 dropbacks; catch over expected 136 targets, yards after contact 149 carries, missed tackle rate 220 chances, broken tackles 255 touches. A typical season is 95% real for carries a run snap and 19% for missed tackles | `build/players.txt`, the noise-ceiling table | strong | 20 player rates, 2006-2024 |
| F121 | **M1 beats the raw rate everywhere and the position's average almost everywhere.** Next season: raw by 4.7%-42%, the average by 2%-70% for 17 of 20 player rates; it ties the average for yards after contact, broken tackles a touch and pressured rate, which ship the average. Teams next season: M1 or the pull beats the average for 7 of 14 sides; the defense's faced tendencies (k 1,500-3,000 plays) and the offense's pass rate over expected and explosive rate tie | `build/players.txt`, `build/teams.txt` | strong | Next season, 2018-2024 |
| F122 | **The second pull pays next season, not in season.** One slope on M1 (0.52-0.95) clears M1 for 11 of 20 player rates next season (+0.6% to +5.8%; QB aDOT +5.8%, aDOT allowed +5.4%, carries a run snap +4.9%) and 7 of 14 team sides (+2.5% to +11.4%). In season it clears for 2 of 18 (+0.7%, +0.8%) and loses for scramble rate (−1.7%). Over the rest of a career, folding in drift beats M1 for catch over expected (+10.5%) and completion over expected (+37.1%) | `build/players.txt`, `build/teams.txt`, `build/sides.txt` | strong | Next season; careers ending 2010-2018 |
| F123 | **His other consistent rates and his teammates' conditions add little beyond his own pulled rate.** The ridge clears the rung below for 3 of 20 (yards a route +2.7%, pressures a pass snap +2.4%, aDOT +1.5%) and is clearly worse for 4. The ladder stops at the ridge | `build/players.txt` | strong | Next season |
| F124 | **Where a rate was heading adds to where it is.** His M1's change over his last two seasons, added to the ridge, clears it for 16 of 20 rates (+0.7% to +7.8%; QB hits a pass snap +7.8%, scramble rate +6.1%, targets a coverage snap +4.8%) | `build/players.txt` (I152 lines) | suggestive: found in this build on the test seasons, not shipped, not yet seen on new seasons | Next season, 2018-2024 |
| F125 | **In season, usage rates and offensive tendencies drift; efficiency rates don't.** The filter beats static M1 on the next 4 games for 5 of 7 usage rates (carries a run snap +20.1%, targets a route +4.1%, scramble +4.1%, aDOT +1.9%, targets a coverage snap +1.7%), 2 mixed ones (QB hits a pass snap +3.5%, yards a route +2.4%), catch rate allowed (+0.8%) and offenses' no-huddle (+32%), shotgun (+28%), pass rate over expected (+12%) and success rate (+12%). Catch over expected loses 5.5%-6.1%; the other efficiency rates tie | `build/players.txt`, `build/teams.txt` | strong | Next 4 games after games 4, 8, 12, 2018-2024 |
| F126 | **Extra game-to-game noise isn't why the filter fails for efficiency rates.** A fitted noise factor stays at 1.00-1.10 (I154), a fixed extra (I182) ties it, and this season's own k (I104) is worse for 5 of 8. Efficiency rates ship static | `build/players.txt` | strong | In season |
| F127 | **Normal 80% ranges from the pull's variance plus drift are honest without much help.** 75%-85% for every shipped rate in season (78%-85%) and next season (75%-83%; only catch over expected needed a conformal scale). By thirds of reliability and of swing 70%-92%. Widening each range by the player's swing improves the range score for 8 of 18 rates in season and 9 of 17 next season (up to +4.5%) | `build/players.txt`, `build/teams.txt` | strong | Every shipped rate |
| F128 | **Snap counts stand in for participation well on defense, not for routes' level or run snaps.** Season rate r against the exact count: 0.96-0.99 for defensive pass snaps (forecasts tie the exact version), 0.95-0.97 for routes (but the forecast of the exact rate loses 10%-19%, mostly scale), 0.90 for run snaps (the forecast loses badly, −217% even rescaled). Last season's exact ratio (I180) recovers +6% to +34% | `build/sides.txt` | strong | 2016-2024, 100+ exact attempts |
| F129 | **A defense's faced tendencies are mostly its opponents'.** Less each opponent's usual, the game split rises (pass rate over expected 0.21 → 0.32, shotgun 0.19 → 0.32) and k falls by a third to a half, but the season r doesn't rise (0.24-0.38). The defense's part is real within a season and doesn't carry to the next | `build/sides.txt` (I155) | suggestive: a description; the forecast isn't tested | Team defenses, 2006-2024 |

## The ladder

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | The position's average; the raw rate | — | The raw rate loses to the average for most rates next season |
| 1 | M1 (pulled by k) | Beats raw for 20 of 20 and the average for 17 of 20, next season | One k per rate, pooled over positions (F37) |
| 2 | M1 + the second pull | 11 of 20 next season, 2 of 18 in season | Drift matters between seasons, not within one |
| 3 (next season) | Ridge: own pulled rate, other consistent rates (r 0.5+, chosen inside the fold), teammates' conditions | 3 of 20 | Ladder stops; the trend (I152) is the next rung to try |
| 3 (in season) | The filter (a drifting level) | 5 of 7 usage, 4 of 7 offensive tendencies, 1 of 9 efficiency | Usage drifts; efficiency is static |
| 4 | Ranges: normal, conformal only outside 75%-85%, widened by swing only where the range score improves | 75%-85% everywhere | Kept per rate in `verdicts.json` |

**What ships, per rate:**
- **Next season** (player rates):
  - the pull for 8 (targets a route, carries a run snap, scramble, QB aDOT, completion over expected, targets a coverage snap, catch rate allowed, aDOT allowed);
  - the ridge for 3 (yards a route, aDOT, pressures a pass snap);
  - M1 for 6 (catch over expected, YAC over expected, hit-or-sack rate, sack rate, QB hits a pass snap, missed tackles);
  - the average for 3 (yards after contact, broken tackles a touch, pressured rate).
- **In season:**
  - the filter for 8 (targets a route, yards a route, aDOT, carries a run snap, scramble, QB hits a pass snap, targets a coverage snap, and catch rate allowed with the factor at 1);
  - M1 for 10;
  - the average for 2.
- **Teams next season:** the pull for 5 (offense's hit-or-sack, no-huddle, success, aDOT; defense's explosive rate allowed), M1 for 2 (shotgun, both sides), the average for 7.
- **Teams in season:** the filter for 4 (offense's pass rate over expected, shotgun, no-huddle, success), the pull for 2, M1 for 4, the average for 4 (the defense's pass rate over expected faced, explosive, success and aDOT allowed).

## Where it misses

The fixed miss-lenses (`pcf.validation.misses`) weren't run. This expert's outputs are rates, not the yards the lenses read (see "Not looked at"). Two misses stand out from the report itself:
- **Efficiency rates in season:** catch over expected's filter loses 5.5% to static, so the drift it reads is noise.
- **The next-season ranges on expected attempts:** a player's attempts usually fall the next season, so ranges built on last season's attempts are too narrow. Raw coverage was 68%-80%; the history now scales them walk-forward (call 32), to 74%-90%. Team ranges come out wide for the faced tendencies (up to 92%): their scale is fit on few rows a season.

## The case against

- **Ranges in the history aren't the ranges the report scored.** The report scored ranges on the realised attempts of the next 4 games or next season, which aren't known in advance. The history uses expected attempts, plus a scale fit on earlier seasons' misses. Its coverage is reported (`build/history.txt`), not tuned. A downstream user who knows the real attempts should rebuild the noise term from them.
- **The trend (F124) was found on the test seasons.** It was tested once with odds written first, but it's a new rung found in the same seasons it was scored on, so it's a discovery result. 2025 (the vault) or 2026 would confirm it.
- **The stand-ins carry the in-season rates for routes and run snaps.** For carries a run snap, targets and yards a route, and targets a coverage snap, the in-season rate measures something close to, but not exactly, the participation rate. They are fine as their own rates, but they shouldn't be read as participation's.
- **The filter's grid hits an edge for three offensive tendencies.** q_s reached 1.0 for pass rate over expected, shotgun and no-huddle (call 6), so the filter there may be slightly held back. Its gains are already large (+12% to +32%).
- **Seven test seasons, one k per rate.** Gains are read on 2018-2024, every season scored once, with the same seasons used to choose between rungs. Rule k's tie rule and the copies guard against luck, not against a choice that fit those seasons.
- **I155 is a description, not a forecast.** The adjusted faced rates aren't scored on any target.
- **One pooled k per rate.** F37 says one pull per position is enough, but k is pooled over positions too. A position with a different noise level (tight ends' catch over expected) is pulled by the same k.
- **The PFR measures** (pressured rate, pressures a pass snap and others) are scored on 2019-2024 only, five or six seasons.

## Pitfalls

- **A season's majority class is a look-ahead in season.** It's known only when the season ends. Use the class of his first game (call 23).
- **PFR's rows are known a week late.** Read them with an as-of join on `known_at` ≤ the next kickoff (call 7). The lag applies at 67%-85% of checkpoints.
- **A column computed after the season loop can silently use the last season's parameters.** The history's reliability did (call 33). Compute per-season columns inside the loop.
- **Expected attempts understate next season's noise** (call 32).
- **Stand-ins can be right by order and wrong by level.** Compare them on the forecast of the exact rate, not only by correlation.

## Not looked at

- The vault (2025): closed.
- The miss-lenses and the yards yardstick: the outputs are rates, and the yardstick reads them only through a linear board, where a rescale washes out (decision 0051 call 28). The first consumer's build is the place to score them.
- Diffusion, quarter-level reliability for defenses, trees (the brief).
- Rates beyond the exploration's 20 and 14; touchdowns (F64, F68 say they're dice).
- H26's restart for a new coach; the new-season reset only.

## Could be improved

1. **Ship the trend (F124)** as rung 4 next season, after a check on new seasons.
2. **`stabilization-retro`:** the exact participation counts for routes, run snaps and coverage snaps, as a retrospective sibling. Or, cheaper, I180's correction as a live prior. Proposed, not built (needs the CEO's sign-off).
3. **Expected attempts as an input:** take the attempts forecast from participation or opportunity, instead of last season's attempts, for next season's noise term.
4. **I183:** score the opponent-adjusted faced rates as a forecast of next game's faced rates.
5. **A per-position k** for rates where positions differ in noise, tested against the pooled k (rule k: pooled is simpler).

## Don't redo

- The diffusion model and a per-player k (the exploration).
- A game-noise factor or fixed extra for efficiency rates' filter (F126).
- Layered credibility toward the team's position rate (I181), and per-position slopes for movers or for vacated targets (I173's form, I174).
- This season's own k for efficiency rates (I104's form).

## Interface card

Also in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `play.pbp`, `player_game` (roster, snaps, PFR at its lag), `team_game` (schedule), through an in-season view; participation through a retrospective view for the stand-ins' report only |
| **Outputs** | `outputs/stabilization/<run_id>/`: `player_game.parquet` (`<rate>_next4`, keyed `gsis_id`, `game_id`), `player_season.parquet` (`<rate>_next_season`, keyed `gsis_id`, `season` = the target season, with `input_season`), `team_game.parquet` and `team_season.parquet` (`off_<rate>`, `def_<rate>`, keyed `team`). Standard schema: `mean` the rate, `q10`-`q90` the 80% range, plus `rung`, attempts (`N` or `n`), `k`, `reliability`, `swing`, `range_scale` |
| **Level of detail** | Player-game and team-game (before each game 2-17), player-season and team-season |
| **Interval** | In season the next 4 games' rate; next season the season's rate. 2006-2024, plus 2025's priors (from 2024 and earlier) |
| **Cadence** | in_season |
| **Known at** | `as_of` = the next kickoff (in season; PFR at its lag); 1 September of the target season (next season) |
| **How to use it** | As a pulled rate and its range (a feature or a prior). `reliability` says how much is the player's own. Train only on the history (rule e). Rows where `rung` is `avg` carry the position's mean: the player's own rate adds nothing there. The stand-in rates aren't participation's (F128) |
| **Feeds** | The shared shrink feeds skill-over-expected now. The history is for VOE, player-opportunity, qb-talent, td-expert, the game simulator and the crude forecaster |

## Football sanity

The 2025 priors (next season from 2024 and earlier; `player_season`, `season` 2025), top and bottom by `mean`:
- **Targets a route** (300+ routes): Josh Downs 0.30, Malik Nabers 0.29, Khalil Shakir 0.29, CeeDee Lamb 0.28, Nico Collins 0.28; bottom: blocking tight ends and Derrick Henry.
- **Sack rate** (300+ dropbacks): Will Levis 9.3%, Caleb Williams 9.0%, Jalen Hurts 7.9%; lowest: Bo Nix, Jordan Love, Josh Allen 3.9%.
- **Completion over expected:** Joe Burrow +4.5, Jalen Hurts +4.2, Geno Smith and Jared Goff +3.7; lowest: C.J. Stroud, Aaron Rodgers, Cooper Rush.
- **Pressures a pass snap** (250+): Trey Hendrickson, Myles Garrett, Nick Bosa, Micah Parsons, Will Anderson Jr.; lowest: run-stopping tackles (Kenny Clark, Harrison Phillips).
- **Catch over expected** (60+ targets): George Kittle, Mark Andrews, Pat Freiermuth, Mike Gesicki, Amon-Ra St. Brown; lowest: Deebo Samuel, Diontae Johnson, Dontayvion Wicks.
- **Offense's shotgun rate:** Washington 91%, Indianapolis 87%; lowest Detroit 46%, Minnesota 52%, the Rams 56%. **No-huddle:** Washington 40%, far ahead.

**One flag (rule h): carries a run snap goes above 1** for lead backs (Kareem Hunt 1.19, Joe Mixon 1.17, Derrick Henry 1.08). A back can't carry on more runs than he's on the field for. The stand-in counts his run snaps as his snap share times the team's runs, and a lead back is on the field for more of the runs than his share says, so the stand-in undercounts (F128). Read this rate as a carry-share marker, not as a true rate, until the exact counts or I180's correction replace the stand-in. The other lists read as football.

## The vault (2025): kept closed, odds and pass rules for the CEO

The brief planned to open it once, at the end. The CEO has kept it closed for the last builds, so it isn't opened here. If the CEO says open, the run is fixed in advance:
- **What runs:** the shipped rung of each rate, fit through 2024 exactly as the history's 2025 rows (already saved), scored on 2025's realised rates: next season from 2024 inputs, and the next 4 games after games 4, 8 and 12 of 2025.
- **Pass rules:**
  - (a) each shipped forecast beats the position's average on 2025 for 14+ of the 17 next-season rates that don't ship the average, sign only (one season is too few for intervals);
  - (b) the filter beats static M1 for 4+ of the 8 rates it ships for, in season;
  - (c) the 80% ranges cover 70%-90% for 15+ of the shipped rates;
  - (d) the trend (F124), scored once beside the ridge, adds for 10+ of 20.
- **Odds:** (a) 75%, (b) 70%, (c) 65%, (d) 45%.
- **A failure** is reported as it is. It changes no shipped rung without a new build.

## Open questions for the CEO

1. **Should the trend (where a player's rate was heading) join the shipped next-season forecast?** It's the biggest gain found (16 of 20 rates), but it was found in this build's test seasons.
2. **Should `stabilization-retro` be built** (participation's exact routes, run snaps and coverage snaps, updated between seasons)? Or should we first try the cheaper I180 correction as a live prior? Four in-season rates lean on stand-ins that are too poor for participation's exact rate.
3. **Open the vault?** The odds and pass rules are above.
4. **Is yards after contact (and broken tackles, pressured rate) shipping the position's average right, football-wise?** The number says nothing beats the average next season. Is there a football reason a runner's contact numbers shouldn't carry?
5. **A defense's faced tendencies are mostly its opponents'** (F129). Does that match what you see: do some defenses really push offenses into shotgun or passing?
