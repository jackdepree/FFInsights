# Results: vacated opportunity (`vacated-live`, `vacated-offseason`)

**Date:** 2026-11-26 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **Calls:** [decision 0050](../../docs/decisions/0050-vacated-opportunity-build.md) · **MLflow:** experiments `vacated-live` (run `67156fc9`) and `vacated-offseason` (run `8e8a9eb0`) · **Detail:** `build/` (every number below is in one of its reports) · **Odds before the tests:** `build/PREREG.md`

## In short

**Within a season it works.** When a top player is likely out (the Saturday run's chance he plays), the CEO's plus-minus beats no change on every share:
- snap share by 33%, with every group clear;
- target share by 9%;
- carry share by 24%.

It beats all 19 shuffled copies on each. Participation already carries almost all of the snap signal, but beside opportunity-quality the targets and carries add 4% and 13%. It counts on the yardstick for receiving and rushing yards.

**Between seasons it works for snaps, and for targets only once shrunk.** The changes the in-season rates give are about twice too big between seasons. Scaled down by a slope fit on earlier seasons (I165), the forecast beats no change over all stayers:
- snap share by 13.5%;
- target share by 2.8%.

Carry share ties, so no change ships for carries. **The choice model (method 3) loses to the plus-minus** in both experts.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | vacated-live beats 19 of 19 shuffled copies on each share (copies' best +1.5%, +0.2%, +1.3%). vacated-offseason beats 19 of 19 where the group was left empty and on the lines. On the lines the copies come close (+12.1% against +12.4%): mostly a general shift, see the case against |
| Calibration | Live slopes: snap 0.95, target 0.79 (below the 0.85-1.15 band; recalibrating doesn't help, I160), carry 0.98. Offseason raw slopes: 0.63, 0.46 and 0.45, which the shrink fixes by construction |
| Range coverage (q10-q90, aim 75-85%) | Live (swing ranges): 76.4%, 79.4%, 76.8%. Offseason: 79.0%, 81.9%, 76.3% |
| Leakage | Point-in-time tests on the grid. Saturday knowledge only (availability's rows with `as_of` ≤ kickoff). Rates from completed seasons; the pair part from earlier games. Every rostered player is forecast, so the yardstick can't see who sat (decision 0050, call 8). Vault closed |
| Football sanity (CEO review, 2026-11-26) | no vetoes; the CEO approved the target gain shipping |
| CEO spot-check (2026-11-26) | the shrink on target share: still ships (below) |

## Hunch verdicts

The brief's hunches (H109-H112) were closed in the exploration (the CEO, 2026-11-24). The build made no new hunches. The ideas it tested are below and in `IDEAS.md`.

## Terms

- **No change:** a player's mean share in the earlier games (or last season's games) where every current top player of his pool played. The bar.
- **Expected absence:** (1 − the chance he plays) × his share to date, from the Saturday run's knowledge.
- **The pooled rate:** the share of an absent player's share that one teammate of a given group gains, per pair of groups (WR>WR and so on), refit each completed season.
- **The pair part:** this season's extra for one teammate and one absent player, from earlier games.
- **Left empty / intake:** between seasons, whether a top player came in at the group (a top player elsewhere last season, or a pick 1-64).
- **The gated forecast:** the plus-minus where the group was left empty and for the lines; no change where a top player came in.
- **The shrunk forecast:** no change plus the gated change times a slope fit on earlier seasons.
- **Unclaimed share:** of a team-game's vacated share in a group, the part the teammates who played didn't absorb.

## Findings

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | The plus-minus with the Saturday chance he plays beats no change on next game's share for the absent player's teammates: snap +33.0% (30.2 to 35.8), target +8.8% (7.6 to 10.0), carry +24.3% (19.1 to 30.3). The hindsight ceiling is +39.7%, +10.1% and +27.2%, so it reaches 83-89% of the room | `build/live_ladder.txt`; 21,425 / 13,740 / 3,965 scored rows | strong | 2017-2024, all five groups (snap) and the skill groups |
| F2 | Snap share by group, against no change: DL +24.9%, OL +32.9%, RB +42.3%, TE +50.1%, WR +29.9%, all clear of 0 | `live_ladder.txt` | strong | in season |
| F3 | **The pair part pays:** this season's pair-specific extra on top of the pooled rate removes 18.8% of the pooled part's error on snaps, 1.6% on targets and 8.8% on carries (I49) | `live_ladder.txt` | strong | in season, weekly |
| F4 | **One rate per pair of groups; teams and coaches don't differ** beyond it: team rates lose 0.3-0.7%, coach rates 0.25-0.36% | `live_ladder.txt` | strong | in season |
| F5 | The same-group transfer rates through 2024 (share of the absent player's share, per teammate). Snap: WR .164, TE .280, RB .249, OL .083, DL .090. Target: WR .168, TE .194, RB .216. Carry: RB .267. On average a team-game's teammates absorb 0.35 of 0.56 vacated share; 0.20 goes unclaimed (to players outside the group's regulars, or not filled) | `live_history.txt`; `rates.parquet`, `unclaimed.parquet` | strong (league trait) | 2013-2024 |
| F6 | **Participation already has the snap signal:** beside participation's next-game share the change adds +0.20% (0.04 to 0.38). Beside opportunity-quality's expected points it adds +4.1% on targets (3.3 to 4.7) and +12.6% on carries (10.4 to 15.2) | `live_checks.txt` | strong | in season, skill groups |
| F7 | On the yardstick (next game, beside participation) it counts: receiving +0.25% (0.15 to 0.35), rushing +1.30% (0.76 to 1.85); copies about 0 | `live_yardstick.txt` | strong | 2019-2024 boards |
| F8 | A sudden absence transfers a little more: the first game of an absence spell has a higher same-group rate than later games for WR, RB and OL together, +0.018 (0.012 to 0.025) (I164). COVID-list absences transfer more than injury absences for WR, RB and OL (I143) | `live_ideas.txt`, `live_checks.txt` | suggestive | in season |
| F9 | **Between seasons the in-season rates overshoot by about half:** slopes of the actual change on the forecast change are 0.63 (skill snaps left empty), 0.77 (lines), 0.46 (targets) and 0.45 (carries). Shrunk by a slope fit on earlier seasons, the forecast beats no change where the group was left empty: snap +25.1% (16.0 to 34.3), target +5.1% (0.9 to 8.4); carry +3.2% ties (I165) | `build/offseason.txt` | strong (snap), suggestive (target) | week-1 rosters, 2017-2024 |
| F10 | **Intake decides it** (I125 confirmed): where a top player came in, the plus-minus is worse than no change (snap −26.7%, target −19.2%), so the gate keeps no change there | `offseason.txt` | strong | between seasons, skill groups |
| F11 | The usual way, splitting the departed share in proportion to the stayers' shares, is far worse than no change (−32% snap, −97% target, −64% carry over all stayers) | `offseason.txt` | strong | between seasons |
| F12 | **The choice model loses:** a nested logit (groups as nests, on who was on the field) beats no change in season (targets +1.9%, carries +16.8%) but loses to the plus-minus (−7.6%, −9.8%), and badly between seasons. Wide receivers are closer substitutes for each other than for TEs and RBs (λ 0.55-0.85 in all 9 seasons), but that doesn't improve the forecast (+0.12%, a tie) | `build/choice.txt`, `offseason.txt` | strong (loses), suggestive (the WR nest) | 2016-2024 |
| F13 | Role-table closeness to the departed player doesn't say which stayer receives (I126, I136): Z vs P ties on snap, target and carry share where the group was left empty | `offseason.txt` | strong (ties) | between seasons |
| F14 | Between seasons, beside the rest-of-season incumbents: on snaps participation has it (+1.3%, a tie); on targets the change adds +3.9% beside opportunity-quality (2.1 to 5.6). On the season yardstick it counts on receiving yards +0.59% (0.05 to 1.20), copies' best +0.23%; not on rushing | `offseason.txt` | suggestive | week 1, 2019-2024 boards |

## The ladder

vacated-live (against no change unless named; snap / target / carry):

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 1 | no change | — | it's biased low late in the season (players' shares grow), which the trees later fix |
| 2 | pooled rates (completed seasons) | +17.6% / +7.3% / +17.0% | one rate per pair of groups; pooled alone overshoots on snaps (slope 1.42) |
| 3 | + the pair part (this season) | +18.8% / +1.6% / +8.8% | **the champion**; slopes 0.95 / 0.79 / 0.98 |
| 4 | team or coach rates | −0.7% to −0.25% | stops: one rate per pair of groups |
| 5 | trees on the residual | +17.3% / +6.0% / +2.7%, of which the absence inputs add +2.8% / +0.7% / +1.9% | not shipped: the gain is no change's bias, which participation already fixes (I161) |
| — | choice model (method 3) | −7.6% / — / −9.8% vs rung 3 | the plus-minus wins (the brief's tie rule already favoured it) |

vacated-offseason (over all stayers): no change → gated plus-minus (snap +11.6%, target +0.4% tie, carry −3.8% tie) → shrunk (snap +13.5%, target +2.8%, carry +2.2% tie). Champions: shrunk for snap and target, no change for carry.

## Where it misses

Not run through `pcf.validation.misses` yet. The ranges' coverage by group and cell is in `live_ladder.txt` and `offseason.txt`: RBs' offseason ranges hold 75-76%, the lowest.

## The case against

- **No change is a weak bar in season.** It's biased low late in the season, and trees with no absence inputs remove much of that error too. The gain that is really the absence's is what the trees can't add (+2.8% / +0.7% / +1.9%) plus the rate's direct effect. Against participation, the real incumbent, the snap gain is only +0.20%.
- **The offseason lines' gain is mostly a level shift.** Shuffled departures reach +12.1% against the real +12.4%. Stayers on the lines gain share the next season whoever left, so a team-specific claim rests on about 0.3 points.
- **The offseason samples are small:** 305 snap rows and 902 target rows left empty. The target result (+2.8% over all stayers, +5.1% left empty) clears 0 by under a point, and its shrink slope was chosen on the same kind of rows (walk-forward, but the slopes are steady, so it's close to a fit).
- **The week-1 roster isn't the live event.** Live runs after free agency and the draft see a thinner roster (camp cuts haven't happened), so departures and intake will differ from the backtest.
- **The exploration found more** on targets left empty (+11.4%) than the build's unshrunk +0.8%. The build's no change uses games where every departed pool-mate played, and its rates are fit through s with the pair part. The difference wasn't tracked down.
- **The choice model may be under-built,** not wrong: one representative play, snap share as the on-field chance, carries' nests at the grid's floor. A per-play counterfactual could do better. As built, it loses clearly.

## Pitfalls

- Forecasting only players who played leaked who sat into the yardstick's zero-fill (fixed; it had overstated receiving by half).
- Reserve-list players aren't in availability's history and fell back to the report; read `roster_week` first.
- A player traded to his next opponent appears on both sides of one game; key player-games on team too.
- Trees "active" on a hindsight flag leaked; use only the expected absence.

## Not looked at

- I9 (the team's unclaimed share as an input for movers' first games: odds written, not run).
- I122 (the vacancy blend for newcomers) is outside these experts, which forecast stayers.
- Runs after free agency and the draft (live only, by the brief).
- Air yards and red-zone chances as further opportunity (the CEO: "targets and carries should be the bedrock").
- The 2025 vault (kept closed).

## Could be improved

1. Give participation the live expert's change as an input, rather than stacking it: participation already has the snap signal.
2. Shrink the offseason change per group rather than per pool (TE gains most, WR least).
3. A per-play choice model, to tell whether method 3 failed or only this version of it.
4. Run the unclaimed share (I9) as an input for movers.

## Don't redo

- Team or coach transfer rates (F4).
- Role-table closeness for who receives between seasons (F13, I126, I136).
- The proportional split (F11).
- Recalibrating the live change (I160).
- The first game back as its own input (I55).

## Interface card

| | |
|---|---|
| **Inputs** | player_game (roster, snaps, stats, injury), team_game (schedule, opening_coach), roster_week; availability/next_logit v1, participation/trees_week v1 and lasso_rest v1, opportunity-quality/eff_trees v1 and eff_rest v1, roles-archetypes v1 (checks only) |
| **Outputs** | `outputs/vacated-live/67156fc9…/history.parquet` (also `unclaimed.parquet`, `rates.parquet`) and `outputs/vacated-offseason/8e8a9eb0…/history.parquet`. Quantities `snap_share`, `target_share`, `carry_share`: mean, q10, q50, q90, `no_change`, `change` |
| **Level of detail** | live: player-game, every rostered player in the five groups; offseason: stayer-team-season |
| **Interval** | live weekly from each player's second game, 2014-2024 (scored 2017-2024); offseason at week 1, 2016-2024 (scored 2017-2024) |
| **Cadence** | live in_season; offseason offseason_events |
| **Known at** | live: the Saturday run (12:00 ET); offseason: the event's roster (the backtest: week 1) |
| **How to use it** | Read `change` as a feature (it's what adds beside the incumbents), not the mean as a forecast. Snap shares: participation has most of it in season. Targets and carries: use it beside opportunity-quality. Offseason carries: the mean is no change |
| **Feeds** | participation (input candidate), opportunity-quality, player-opportunity, fantasy-projections; the yardstick |

## The CEO's spot-check: the shrink on target share (2026-11-26)

The odds were written first (`build/PREREG.md`); the detail is in `build/spot_target_shrink.txt`.

**Verdict: it still ships.** It's small and real: it beats no change in all 8 seasons, beats all 19 shuffled copies, and doesn't depend on the exact slope. It's close to zero in two ways: no single season clears 0 except 2021, and without 2021 the interval touches 0.

1. **How the slope is fit, and whether it's known in time.**
   - It's one number: how much of the plus-minus's predicted rise actually happened, a slope through zero of (actual − no change) on (the plus-minus − no change).
   - It's fit on the skill-position stayers left empty in earlier seasons only. The forecast for 2020 reads the pairs 2015→2016 to 2018→2019, all finished before 2020's week 1.
   - Where a top player came in, the forecast is no change. So yes, it's known in time, by construction (*held*).
2. **How steady it is:** 0.66 for 2017 (one season of history, 144 rows), then 0.48-0.55 every season after. The hindsight slope over every season is 0.54. The plus-minus predicts about twice the rise that happens.
3. **The result:**
   - over all 1,397 stayers: +2.8% (+0.5% to +4.8%) against no change;
   - over the 902 left empty: +5.1% (+0.9% to +8.4%);
   - unshrunk, the plus-minus ties no change (+0.4%, −3.9% to +4.0%).
4. **Its size in football terms:** it moves 64% of the stayers by about +0.6 points of target share, roughly 3-4 targets over a season. On those rows the actual rise was +0.7 points. It's a small, nearly uniform lift for the players left behind, not a reshuffle of who gets what.
5. **By season:** positive in all 8 (+0.6% to +8.3%), but only 2021 clears 0 on its own (+8.3%). I bet 55% on 6 or more positive (*held*).
6. **By position:**
   - TE +5.4% (+2.9% to +8.2%), the only group that clears 0 on its own;
   - WR +2.0% and RB +2.1% tie.

   Of the error removed, TEs carry 45%, WRs 42% and RBs 14%. I bet 55% on TEs carrying the largest gain (*held*, narrowly by share).
7. **How close to zero:**
   - dropping each season in turn, the interval stays above 0 in 7 of 8 drops;
   - without 2021 it's +2.1% (−0.3% to +4.1%).

   I bet 40% on all 8 (*failed*).
8. **The slope's cost:**
   - the hindsight slope gains only +0.18% over the walk-forward one (I bet 70% on under 1 point: *held*);
   - fixed slopes of 0.25 or 0.5 give +2.2% and +3.0%, both clear;
   - 0.75 ties, and 1.0 (no shrink) ties.

   So the result doesn't hang on the exact slope, only on shrinking by about half.
9. **No noise:** rebuilt end to end with each season's departures moved to another team (the slope refit each time), the copies reach a best of +1.58% and a mean of +0.77%. The real +2.82% beats all 19 (I bet 85%: *held*). Left empty: real +5.07%, copies' best +2.85%.

   About a quarter of the gain (the copies' mean, +0.8%) is the general lift stayers get whoever left. The rest, about 2 points, comes from which teammates left.

**What would change the answer:**
- a 2025 season like 2017 or 2023 (+0.6%, +0.7%) would pull the interval toward 0;
- the live roster after free agency and the draft would also change it, since its intake flag will differ from week 1's.

## Open questions for the CEO (answered 2026-11-26)

The CEO's words: "No vetoes on decision 0050. No I think vacated live can keep the snap change for now. Yes the 2.8% between season target gain ship. Can yo please spot check the shrink on target?"

1. **Spot-check:** the shrink on target share (below).
2. **Participation doesn't take vacated-live's change for now;** vacated-live keeps its snap change.
3. **The +2.8% between-season target gain ships.**

## After the merge (2026-11-26)

The CEO, word for word: "Yes that is a great idea for shrinkage later. Ideas are almost always good, as long as we have the ability to test them or to at least check if we can test it and if an idea is not extremely redundant. Yes we can check it by hand as long as you walk me through it, then I can help!"

- **I174** (a target shrink per position between seasons, mostly tight ends) is open in `IDEAS.md`.
- **The first live vacated-offseason run** (after free agency and the draft, 2027) gets a hand check against week 1's roster, walked through with the CEO: which top players count as "came in", which groups count as left empty, and the stayers whose forecast moved most.
