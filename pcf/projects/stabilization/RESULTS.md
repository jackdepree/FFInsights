# Results: Stabilization and regression (`stabilization`)

**Date:** 2026-11-26 · **Brief:** [BRIEF.md](BRIEF.md) ("The agreed brief", 2026-11-25) · **Decision:** [0052](../../docs/decisions/0052-stabilization-build.md) (37 calls; no vetoes on 1-34) · **Spot-check:** [SPOT_CHECK.md](SPOT_CHECK.md) (the second pull) · **MLflow experiment:** `stabilization`, run `9b0f405ff265454885dfed8b9d580a46` (the champion) · **History:** `outputs/stabilization/9b0f405ff265454885dfed8b9d580a46/{player_game,player_season,team_game,team_season}.parquet` · **Build reports:** [`build/`](build/) (`players.txt`, `teams.txt`, `sides.txt`, `leakage.txt`, `history.txt`, `verdicts.json`) · **Shared code:** `pcf.validation.stabilize` (the shrink, owned here) and `pcf.experts.stabilization`

## In short

For each of 20 player rates and 14 team rates (7 per side), stabilization now says how much of the rate is real after n attempts (k, the 50% point), and where it will be over the next 4 games and next season, with an 80% range. Every forecast in the saved history is made before the game or season it forecasts, from parameters fit on earlier seasons.

**What the build found:**
- **Pulling a rate toward its position by k (M1) is the base, and it's hard to beat.** Next season it beats the raw rate for all 20 player rates (by 2.7% to 42% of the squared error) and the position's average for 15 of 20 (by 3.6% to 68%); with the rungs above, the shipped forecast beats the average for 18 of 20.
- **A second pull (one slope on M1, fit on earlier seasons) helps next season for 11 of 20** (0.7% to 5.8%), not in season. The CEO's spot-check ([SPOT_CHECK.md](SPOT_CHECK.md)): leak-free, its slope steady season to season, and 91%-98% as good as a hindsight slope for 8 of the 11.
- **The ridge** (his other consistent rates and his teammates' conditions) **adds for only 3 of 20** (1.5% to 2.7%).
- **Where a rate was heading adds to where it is (the trend, rung 4, shipped):** his change over his last two seasons, added to the ridge, clears the rung below for 10 of 20 rates (1.7% to 8.9%). It was found on the same seasons it was scored on, so 2026 is its first clean test (call 35 names what pulls it back).
- **In season, a drifting level (the filter) beats static M1 for 5 of the 7 usage rates** (carries a run snap +25%) and **for 4 of 7 team offensive tendencies** (no-huddle +32%, shotgun +28%). For efficiency rates it ties or loses; they stay static.
- **The ranges hold:** every shipped 80% range covers 75% to 85% on the scored seasons.
- **Carries a run snap no longer goes above 1:** the run-snap stand-in is corrected by last season's exact ratio (I180) with a floor of his carries (call 36).

Against the brief: the expert's bar (beats the position's average and 19 shuffled copies) holds for **18 of 20 player rates next season** and **18 of 20 in season**. Two player rates ship the position's average next season, because nothing beats it: broken tackles a touch and pressured rate. Yards after contact now beats it through the trend. Four in-season rates lean on stand-ins that are too poor for participation's exact rate. The worst, run snaps, now gets I180's correction: the CEO chose that cheaper fix over a retrospective sibling. The vault stays closed (the CEO, 2026-11-26).

**A correction to the first report:** it said every leakage check passed. The first two full runs' `leakage.txt` actually ended "all passed: False", because the code scan flagged `run.py` reading the build's own reports (never data). Every other check passed. The scan now allows `run.py` that one read and nothing else, the checks were rerun, and all pass (call 37).

**Scorecard:** `build/players.txt`, `build/teams.txt`, `build/sides.txt`, `build/leakage.txt`, `build/history.txt`, MLflow run `9b0f405ff265454885dfed8b9d580a46` · **Vault:** closed (the CEO, 2026-11-26: "Keep 2025 vault closed"; odds and pass rules below, unscored) · **Versions tried:** five logged attempts: the first full run (crashed in the team history, call 34), a history rebuild stopped on purpose (call 32), `ba5c1375765a4650bce695ddb63c0dbe` (v1), the full rerun with the trend and I180 (`d835ef7928294f249059dc74f3862b2f`, its leakage logged False, call 37), and the history-only attempt `9b0f405ff265454885dfed8b9d580a46` after the checks were rerun; before them, no-log runs per section.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | Every shipped rung beats all 19 shuffled copies (every input moved to another player of the same season and position), and clears the rung below on a 90% interval from 2,000 player resamples. Where nothing clears the position's average, the average ships (2 of 20 next season, 2 of 20 in season, 11 of 28 team rows: the defense's faced tendencies and efficiency mostly) |
| Calibration and range coverage | Shipped 80% ranges: 75%-85% for every rate in the report (next 4 games 78%-85%; next season 75%-83%, catch over expected after a conformal scale), and 74%-90% by thirds of reliability and of swing. The saved history's ranges use expected attempts with a walk-forward scale (call 32): on the scored rows they cover 77%-82% before each game, 74%-90% next season (catch over expected 74%, carries a run snap 90%), and 76%-92% for teams (the defense's no-huddle 91%-92%, shotgun 88%-89%) (`build/history.txt`) |
| Leakage | All passed after a fix to the code scan (call 37; the first report wrongly said all passed while the file said False) (`build/leakage.txt`): future deletion and outcome scrambling at 8 cutoffs (0 forecasts differ in 4 measures × 8 cutoffs); next-season scrambling (0 of 750 differ); PFR's lag (0 checkpoints read a game not yet known; the lag bites at 67%-85%); known-at sanity; the code scan (3 named, expected reads, plus `run.py` reading its own reports, `read_text` only) |
| Football sanity | The 2025 priors' top and bottom players are below ("Football sanity"). The one flag (carries a run snap above 1 for lead backs) is fixed by I180 and the floor (call 36): no lead back (150+ run snaps) has a 2025 prior above 1, top 0.96 |
| CEO spot-check | The second pull ([SPOT_CHECK.md](SPOT_CHECK.md)): leak-free, steady, kept as built; 3 of its 5 bets held |

**The brief's odds, scored** (written in decision 0052 before any result; "clear" = a 90% interval that leaves out 0):

| Bet | Odds | Result | Verdict |
|---|---|---|---|
| The second pull beats M1 next season for 12+ of 20 | 55% | 11 of 20 | failed, narrowly |
| The ridge beats the rung below for 4+ of 20 (1+) | 40% (75%) | 3 of 20 (yards a route +2.7%, aDOT +1.5%, pressures a pass snap +2.4%) | failed (held) |
| The filter beats static for 4+ of 7 usage rates | 50% | 5 of 7 | held |
| The filter beats static for 4+ of 7 offensive tendencies | 65% | 4 of 7 | held |
| The bar holds next season for 16+ of 20 | 60% | 17 of 20 in v1; 18 of 20 with the trend | held |
| Every shipped range within 75%-85%, next 4 games | 50% | 18 of 18 | held |
| The same next season, before any conformal step | 35% | 16 of 17 (catch over expected 93%) | failed |
| I14's widening improves the range score for half the shipped rates (next 4 games) | 60% | 8 of 18 | failed |
| Routes stand-in close (r 0.95+) | 85% | r 0.95 and 0.97 | held |
| Run-snap stand-in close | 45% | r 0.90 | failed (as leaned) |
| Defensive pass-snap stand-in close | 55% | r 0.96 to 0.99 | held |
| At least one stand-in too poor | 40% | 4 rates (targets and yards a route, carries a run snap, targets a coverage snap) | held |
| Career: drift folded in beats M1 for 2+ of 8 | 55% | 2 (catch over expected +10.5%, completion over expected +37.1%) | held |

**After the CEO's answers** (odds in decision 0052, written before the code ran; the spot-check's five are in [SPOT_CHECK.md](SPOT_CHECK.md)):

| Bet | Odds | Result | Verdict |
|---|---|---|---|
| The trend clears the shipped rung for 12+ of 20 | 65% | 10 of 20 (+1.7% to +8.9%) | failed |
| The history's next-season coverage within 74%-90% for every rate | 75% | 74%-90% (catch over expected 74%, carries a run snap 90%) | held |
| No lead back (150+ run snaps) above 1 in his 2025 prior | 55% | I180 alone: 5 of 38 lead backs above 1 in 2024 (M1's prior up to 1.14); with the floor, 0 of 41 (the shipped prior's top 0.96) | failed (I180 alone); held with the floor, added after the look |
| At most 2 above 1 | 80% | the same | failed (I180 alone) |
| In season, carries a run snap still beats the average and its copies, and the filter beats static | 85% | +82.1% vs the average, best copy −98.4%; the filter +24.9% over the pull (was +20.1%) | held |
| Its season rate's correlation with the exact rate stays 0.918 ± 0.01 | 90% | 0.918 | held |

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
| **I152** (this build's form) his change over his last two seasons, added to the ridge | 30% clear for 1+ usage rate; 0.5%-2% | Clear for all 4 usage rates (+2.7% to +4.8%) and 16 of 20 overall (+0.7% to +7.8%) over the ridge; over the rung that ships, 10 of 20 (+1.7% to +8.9%) | **Held, and bigger than expected. Shipped as rung 4** (the CEO, 2026-11-26; call 35). Its first clean test is 2026. The original form (role table, player-opportunity) stays open |
| **I181** layered credibility (his team's rate at his position, then the position) | 35% clear for 2+ usage rates | Worse for 19 of 20 (clearly for 13); carries a run snap ties (+0.4%) | **Killed:** F37 holds; pull toward the position |
| **I173** (this build's form) a movers' own slope | 30% clear for 1+ of 20; 10% for 5+ | 1 of 20 (catch over expected +0.2%); 3 clearly worse; the shared second pull already helps movers (clearly for 9 of 20, +1.5% to +8% over M1) | **This form killed;** the row stays open for edge pressure's new-team gain on 2025-2026 |
| **I174** a target shrink slope per position | 35% over all stayers; 50% for tight ends | −0.1% (−1.8 to +1.7); tight ends −0.5% (−5.5 to +4.1); beats 14 of 19 copies | **Killed:** the one shared slope (I165) stays |
| **I104** (this build's form) this season's k, blended with the pooled k | 20% clear for 1+ efficiency rate | None clear better; 5 of 8 clearly worse (broken tackles −2.2%) | **This form killed;** B's season factor itself stays open |
| **I180** a stand-in corrected by last season's exact ratio | 60% the correlation rises 0.02+ for carries a run snap or a defensive pass-snap rate | +0.017 for carries a run snap, +0.002 to +0.005 on defense: failed narrowly. On the forecast it pays: +34% for carries a run snap, +9.6% targets a route, +6.1% yards a route | **Failed its bar, pays on the forecast. Shipped for run snaps** (the CEO, 2026-11-26: "try out the cheaper fix first"; call 36, with a floor of his carries). `stabilization-retro` stays a proposal |
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
| F121 | **M1 beats the raw rate everywhere and the position's average almost everywhere.** Next season: raw by 2.7%-42%, the average by 3.6%-68% for 15 of 20 player rates (18 of 20 with the rungs above: QB aDOT and catch rate allowed clear it only with the second pull, yards after contact only with the trend); broken tackles a touch and pressured rate tie it with every rung and ship the average. Teams next season: M1 or the pull beats the average for 7 of 14 sides; the defense's faced tendencies (k 1,500-3,000 plays) and the offense's pass rate over expected and explosive rate tie | `build/players.txt`, `build/teams.txt` | strong | Next season, 2018-2024 |
| F122 | **The second pull pays next season, not in season.** One slope on M1 (0.52-0.95) clears M1 for 11 of 20 player rates next season (+0.7% to +5.8%; QB aDOT +5.8%, aDOT allowed +5.4%, carries a run snap +5.1%) and 7 of 14 team sides (+2.5% to +11.4%). In season it clears for 2 of 20 (aDOT +0.7%, carries a run snap +0.6%) and loses for scramble rate (−1.7%) and catch over expected (−1.0%). The spot-check: its slopes stay within 0.1 of 2024's for 10 of 11, and the walk-forward fit gets 91%-98% of a hindsight slope's gain for 8 of 11 ([SPOT_CHECK.md](SPOT_CHECK.md)). Over the rest of a career, folding in drift beats M1 for catch over expected (+10.5%) and completion over expected (+37.1%) | `build/players.txt`, `build/teams.txt`, `build/sides.txt` | strong | Next season; careers ending 2010-2018 |
| F123 | **His other consistent rates and his teammates' conditions add little beyond his own pulled rate.** The ridge clears the rung below for 3 of 20 (yards a route +2.7%, pressures a pass snap +2.4%, aDOT +1.5%) and is clearly worse for 4. The ladder stops at the ridge | `build/players.txt` | strong | Next season |
| F124 | **Where a rate was heading adds to where it is.** His M1's change over his last two seasons, added to the ridge, clears it for 16 of 20 rates (+0.7% to +7.8%), and clears the rung that would otherwise ship for 10 of 20 (+1.7% to +8.9%; carries a run snap +8.9%, QB hits a pass snap +8.3%, yards after contact +7.3%, sack rate +7.0%). Shipped as rung 4 (call 35) | `build/players.txt` ("the trend (rung 4)" and I152 lines) | suggestive: found in this build on the test seasons; shipped, with 2026 its first clean test | Next season, 2018-2024 |
| F125 | **In season, usage rates and offensive tendencies drift; efficiency rates don't.** The filter beats static M1 on the next 4 games for 5 of 7 usage rates (carries a run snap +24.9% with I180, +20.1% before, targets a route +4.1%, scramble +4.1%, aDOT +1.9%, targets a coverage snap +1.7%), 2 mixed ones (QB hits a pass snap +3.5%, yards a route +2.4%), catch rate allowed (+0.8%) and offenses' no-huddle (+32%), shotgun (+28%), pass rate over expected (+12%) and success rate (+12%). Catch over expected loses 5.5%-6.1%; the other efficiency rates tie | `build/players.txt`, `build/teams.txt` | strong | Next 4 games after games 4, 8, 12, 2018-2024 |
| F126 | **Extra game-to-game noise isn't why the filter fails for efficiency rates.** A fitted noise factor stays at 1.00-1.10 (I154), a fixed extra (I182) ties it, and this season's own k (I104) is worse for 5 of 8. Efficiency rates ship static | `build/players.txt` | strong | In season |
| F127 | **Normal 80% ranges from the pull's variance plus drift are honest without much help.** 75%-85% for every shipped rate in season (78%-85%) and next season (75%-83%; only catch over expected needed a conformal scale). By thirds of reliability and of swing 70%-92%. Widening each range by the player's swing improves the range score for 8 of 18 rates in season and 9 of 17 next season (up to +4.5%) | `build/players.txt`, `build/teams.txt` | strong | Every shipped rate |
| F128 | **Snap counts stand in for participation well on defense, not for routes' level or run snaps.** Season rate r against the exact count: 0.96-0.99 for defensive pass snaps (forecasts tie the exact version), 0.95-0.97 for routes (but the forecast of the exact rate loses 10%-19%, mostly scale), 0.90 for run snaps (the forecast loses badly, −217% even rescaled). Last season's exact ratio (I180) recovers +6% to +34%, and now corrects run snaps live, with a floor of his carries (call 36) | `build/sides.txt` | strong | 2016-2024, 100+ exact attempts |
| F129 | **A defense's faced tendencies are mostly its opponents'.** Less each opponent's usual, the game split rises (pass rate over expected 0.21 → 0.32, shotgun 0.19 → 0.32) and k falls by a third to a half, but the season r doesn't rise (0.24-0.38). The defense's part is real within a season and doesn't carry to the next | `build/sides.txt` (I155) | suggestive: a description; the forecast isn't tested | Team defenses, 2006-2024 |

## The ladder

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | The position's average; the raw rate | — | The raw rate loses to the average for most rates next season |
| 1 | M1 (pulled by k) | Beats raw for 20 of 20 and the average for 15 of 20, next season (18 of 20 with the rungs above) | One k per rate, pooled over positions (F37) |
| 2 | M1 + the second pull | 11 of 20 next season, 2 of 20 in season (spot-checked) | Drift matters between seasons, not within one |
| 3 (next season) | Ridge: own pulled rate, other consistent rates (r 0.5+, chosen inside the fold), teammates' conditions | 3 of 20 | The trend (I152) is the next rung |
| 4 (next season) | The ridge plus his change over his last two seasons (the trend) | 10 of 20 over the rung that would ship (+1.7% to +8.9%) | Where a rate was heading carries; found on the test seasons, so 2026 is its first clean test (call 35) |
| 3 (in season) | The filter (a drifting level) | 5 of 7 usage, 4 of 7 offensive tendencies, 1 of 9 efficiency | Usage drifts; efficiency is static |
| Ranges | Normal, conformal only outside 75%-85%, widened by swing only where the range score improves | 75%-85% everywhere | Kept per rate in `verdicts.json` |

**What ships, per rate:**
- **Next season** (player rates):
  - the trend for 10 (targets and yards a route, aDOT, YAC over expected, carries a run snap, yards after contact, sack rate, pressures a pass snap, QB hits a pass snap, targets a coverage snap);
  - the pull for 5 (scramble, QB aDOT, completion over expected, catch rate allowed, aDOT allowed);
  - M1 for 3 (catch over expected, hit-or-sack rate, missed tackles);
  - the average for 2 (broken tackles a touch, pressured rate).
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
- **The trend (F124) ships, but it was found on the test seasons.** It was tested once with odds written first (and missed them: 10 of 20, not 12+), but it's a new rung found and chosen in the same seasons it was scored on, so its gains are a discovery result, likely a little high. 2026 is its first clean test; call 35 says what pulls it back.
- **The leakage checks were first misreported.** The first report said all passed while `leakage.txt` said False (a false flag on `run.py`'s report reads). Fixed and rerun (call 37), but the report should have read the file, not assumed.
- **I180's floor was added after the first look** (call 36). The odds for I180 alone failed (5 lead backs above 1), and the floor is the fix a football rule asks for, but it was chosen after seeing the result.
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

1. **Score the trend (F124) on 2026** against call 35's pull-back rules.
2. **`stabilization-retro`:** the exact participation counts for routes, run snaps and coverage snaps, as a retrospective sibling. I180 now corrects run snaps live; routes and coverage snaps could get the same correction. Proposed, not built (needs the CEO's sign-off).
3. **Cap the ranges of rates bounded at 0 and 1** (carries a run snap's range can reach 1.15).
4. **Expected attempts as an input:** take the attempts forecast from participation or opportunity, instead of last season's attempts, for next season's noise term.
5. **I183:** score the opponent-adjusted faced rates as a forecast of next game's faced rates.
6. **A per-position k** for rates where positions differ in noise, tested against the pooled k (rule k: pooled is simpler).

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
- **Targets a route** (300+ routes; the trend now ships): CeeDee Lamb 0.30, Malik Nabers 0.30, Nico Collins 0.29, A.J. Brown 0.29, Davante Adams 0.28; bottom: blocking tight ends (Drew Sample 0.08) and Kyren Williams. (In v1 Josh Downs and Khalil Shakir were near the top; the trend pulls them down a little.)
- **Carries a run snap** (150+ run snaps; I180 and the floor): Joe Mixon 0.96, Kareem Hunt 0.95, David Montgomery 0.95, Kenneth Walker III 0.93, Bucky Irving 0.93; bottom: fullbacks (Kyle Juszczyk 0.10, Patrick Ricard 0.06).
- **Sack rate** (300+ dropbacks; the trend now ships): Caleb Williams 8.7%, Will Levis 8.4%, Jayden Daniels and Drake Maye 7.9%, Bryce Young 7.8%; lowest: Josh Allen and Jordan Love 4.9%, Tua Tagovailoa 4.7%.
- **Completion over expected:** Joe Burrow +4.5, Jalen Hurts +4.2, Geno Smith and Jared Goff +3.7; lowest: C.J. Stroud, Aaron Rodgers, Cooper Rush.
- **Pressures a pass snap** (250+): Trey Hendrickson, Myles Garrett, Nick Bosa, Micah Parsons, Will Anderson Jr.; lowest: run-stopping tackles (Kenny Clark, Harrison Phillips).
- **Catch over expected** (60+ targets): George Kittle, Mark Andrews, Pat Freiermuth, Mike Gesicki, Amon-Ra St. Brown; lowest: Deebo Samuel, Diontae Johnson, Dontayvion Wicks.
- **Offense's shotgun rate:** Washington 91%, Indianapolis 87%; lowest Detroit 46%, Minnesota 52%, the Rams 56%. **No-huddle:** Washington 40%, far ahead.

**The one flag (rule h), fixed:** in v1, carries a run snap went above 1 for lead backs (Kareem Hunt 1.19, Joe Mixon 1.17, Derrick Henry 1.08). A back can't carry on more runs than he's on the field for. The stand-in counted his run snaps as his snap share times the team's runs, and a lead back is on the field for more of the runs than his share says (F128). Now each back's run snaps are scaled by his last season's exact ratio (I180) and floored at his carries (call 36): no lead back's 2025 prior is above 1 (top 0.96). His 80% range can still reach about 1.15, because the ranges are normal and not capped at 1; a consumer should cap them. The other lists read as football.

## The vault (2025): kept closed, odds and pass rules for the CEO

The brief planned to open it once, at the end. The CEO has kept it closed for the last builds, so it isn't opened here. If the CEO says open, the run is fixed in advance:
- **What runs:** the shipped rung of each rate, fit through 2024 exactly as the history's 2025 rows (already saved), scored on 2025's realised rates: next season from 2024 inputs, and the next 4 games after games 4, 8 and 12 of 2025.
- **Pass rules:**
  - (a) each shipped forecast beats the position's average on 2025 for 14+ of the 17 next-season rates (18 since the trend shipped; the rule was set for v1) that don't ship the average, sign only (one season is too few for intervals);
  - (b) the filter beats static M1 for 4+ of the 8 rates it ships for, in season;
  - (c) the 80% ranges cover 70%-90% for 15+ of the shipped rates;
  - (d) the trend (F124), scored once beside the ridge, adds for 10+ of 20 (now also a check on the shipped trend, call 35).
- **Odds:** (a) 75%, (b) 70%, (c) 65%, (d) 45%.
- **A failure** is reported as it is. It changes no shipped rung without a new build.

## Open questions for the CEO

Answered (the CEO, 2026-11-26): the trend ships (call 35); the run-snap stand-in gets I180's correction first (call 36) and `stabilization-retro` stays a proposal; the vault stays closed; no vetoes on calls 1-34; the spot-check is the second pull ([SPOT_CHECK.md](SPOT_CHECK.md)).

Answered after the merge (the CEO, 2026-11-26):
1. **Broken tackles and pressured rate shipping the position's average.** The CEO: "I would say that broken tackles are dependent both upon the running backs ability to break tackles and the opportunities he has - which are granted to him by his team's performance and blocking - to break them." So the plain rate mixes the back's skill with his team's blocking, and the team's part changes when the line or the team changes. That fits nothing beating the average next season. The follow-up (split broken tackles into the back's part and the team's part) joins I92 in `IDEAS.md`.
2. **A defense's faced tendencies are mostly its opponents'** (F129). The CEO: "I would expect offensive patterns to stay consistent and that defenses are more likely to match an opposing offenses patterns." That matches F129: the offense sets the tendency and the defense mostly reacts, so faced tendencies keep shipping as the opponents' mix.
