# Results: the touchdown expert (`td-expert`)

**Date:** 2026-11-24 (built the same day) · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **Build plan and odds:** [BUILD.md](BUILD.md) (written before any result) · **MLflow experiment:** `td-expert` · **Decision:** [0043](../../docs/decisions/0043-td-expert.md) · **Reports:** `build/` (facts, walks, ideas, regression, one per harness run)

## In short
Touchdowns are now a table: every chance's expected touchdown (`play.xtd`, scrambles included), every drive's touchdown chance (`drive.td_chance`), and per player-game and team-game the sums, the luck measure and near misses. Six forecasts are built and validated: players' rushing and receiving touchdowns, a quarterback's thrown touchdowns and a team's touchdowns, each for next game and for the rest of the season, with the chance of at least one.

The headline is the brief's bet on method: **forecasting from chances (method A) is not better than forecasting from volume (method B)**. A ties B for players next game, beats it for thrown touchdowns next game (+0.19%), and loses everywhere over the rest of the season (players −1.25%, thrown −10.1%: whether he keeps playing is the story there, and volume knows it better). **Trees on B's inputs win for players next game** (+0.57% over B, +3.0% for QBs). **A quarterback's red-zone carries are the one red-zone input that pays** (I58 held: +10.6% of the squared error on QBs' rest-of-season touchdowns). The team's ceiling is large (61% of next game's error knowing every red-zone trip's chance), but the market-free team forecast gets 6.5% of it.

**Champions** (`registry.yaml`):

| Forecast | Champion | Run (2016-2024) | Signal | Against rung 0 (season rate), Poisson log loss | Against the other method |
|---|---|---|---|---|---|
| Players, next game | `skill_next_volume_trees` | `7b6321a2…` | 20 of 20 | +3.5% (walk) | trees beat B +0.57% (+0.39 to +0.74), A +0.54% |
| Players, rest of season | `skill_rest_volume+qb_rz` | `756d21f9…` | 20 of 20 | +10.6% (walk) | B beats A +1.25%; + QBs' red-zone carries +0.37% (+0.30 to +0.45) |
| Thrown, next game | `thrown_next_chances` (A) | `63479e9a…` | 20 of 20 | +2.2% | A beats B +0.19% (+0.01 to +0.37) |
| Thrown, rest of season | `thrown_rest_volume` (B) | `eb589a2b…` | 20 of 20 | +37.9% | B beats A +10.1% |
| Teams, next game | `team_next_volume` (B) | `1005eb29…` | 20 of 20 | +0.60% (+0.34 to +0.85) | B beats A +0.19% |
| Teams, rest of season | `team_rest_volume` (B) | `fa0a9e01…` | 20 of 20 | +0.88% (+0.24 to +1.47) | tie (A −0.29%, −0.64 to +0.07): B ships, decision 0043 call 21 (for veto) |

**Vault (2025), opened once, 2026-11-24:** ⟨vault⟩ · **Versions tried:** 24 variants (3 families × 2 horizons × 3 rungs, trees, 5 side variants), one recalibration fix and one ordering fix (decision 0043, calls 18-19), on 6 saved feature histories.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal | Every harness run beats its shuffled copies: 100 of 100 (the first players' run), 20 of 20 for every other (20-of-20 rule; decision 0043 call 20) |
| No noise (A at least as good as B) | Players next game: tie (+0.03%, −0.07 to +0.13); thrown next game: A better; every rest-of-season and teams next game: A worse; teams rest: tie. So A ships only for thrown next game (R4, R10, R11) |
| Beats baselines | Every champion beats rung 0 (the season rate) with its interval clear of 0 |
| Calibration and range | Next game, chance of 1+: players (the trees champion) error 0.42 points, slope 1.04; thrown 2.4, slope 1.04; teams 3.0, slope 1.15 (fails the slope). Chance of 2+: players 0.21 points, slope 0.92 (passes; B and A: slope 0.89); thrown 3.4 points, slope 0.86; teams 5.1 points (one game's touchdowns are less spread than a Poisson count: I119). Rest of season: the chances fail under a Poisson count (players' 1+ error 8 points, thrown 16; the season's total spreads wider: I116). The Poisson q10-q90 range is reported only (R6) |
| Leakage | All 10 checks pass for every champion (25 cutoffs). Check 8 caught an ordering bug in A's stage 1 (not a leak; fixed and tested; decision 0043 call 19) and check 1 an import in the build's own checks (fixed) |
| Football sanity | Claude's: 2024's highest next-game forecasts (8+ games, A's run): Saquon Barkley 0.90 touchdowns a game (scored 1.00), Kyren Williams 0.82 (0.94), Joe Mixon 0.70 (0.88), Jonathan Taylor 0.69 (0.86); QBs Jalen Hurts 0.49 (1.00), Josh Allen 0.43 (0.70); WRs Justin Jefferson 0.56 (0.56), CeeDee Lamb 0.55 (0.40); TEs Sam LaPorta 0.36 (0.47), Travis Kelce 0.34 (0.21) (R16). The CEO's review: ⟨pending⟩ |
| CEO spot-check | ⟨pending⟩ |

## Hunch verdicts
Copied into [`projects/HUNCHES.md`](../HUNCHES.md).

| # | Hunch | Verdict | Real? | Pays? |
|---|---|---|---|---|
| H67 | "touchdown allocation will be closely tied to scheme and play calling tendencies" | held in part (exploration); build: real, doesn't pay | Yes: the goal-to-go pass share is a team trait (0.30 week to week, 0.29 season to season) and the exploration found it shapes who scores | No: beside volume and the offense's quality, the calling adds −0.01% next game and −0.03% over the rest of the season; QBs +0.19% next game (R8) |
| H68 | "the combination of explosive play rate and red zone opportunities will be the strongest predictors of rest of season touchdown totals" | failed (exploration and build) | No for RB, WR, TE: red-zone chances are volume by another name | No: −0.02% beside volume (non-QBs). The exception is QBs' red-zone carries, +3.3% of the log loss (I58, R5, R9) |

## Terms
New ones in [GLOSSARY.md](../../docs/GLOSSARY.md): expected touchdowns (xtd), touchdowns over expected, the luck measure, the drive chance, the drive-aware hindsight, near miss, count forecast, Poisson log loss.

## Findings

**R1. The team's room is large, and the drive-aware hindsight measures it.** Regular season 2016-2024, 4,734 team-games (2.41 touchdowns a game, spread 1.39), share of squared error removed against the plain average (`build/facts.txt`, 3):

| Knowing | Next game | Rest of season (after weeks 4, 8, 12) |
|---|---|---|
| Where every drive started (the drive model at its first snap) | −6.8% | 49.2% |
| How many drives and red-zone trips (a straight line) | 27.5% | |
| **Each red-zone trip's chance at the 20, and every long touchdown (drive-aware)** | **60.8%** (dice left: 38.8%) | **89.4%** (dice left: 7.4%) |
| Every chance's expected touchdowns, summed (F21's, double counts) | 12.1% | 78.5% |

O1 (65%: 40%+ next game; expected 50% and 75%) held, larger than said; O2 (80%: the chance-sum is worse) held. Players with a chance, next game: knowing that game's chances removes 36.0% (dice 63%); QBs with 10+ throws, thrown touchdowns: 21.2% (dice 78%).

**R2. Expected touchdowns are calibrated, once scrambles count as carries.** 2016-2024 (fit on earlier seasons), 292,037 chances, 11,984 touchdowns against 11,658 expected: error 0.21 points by tenth, slope 1.03; log loss 0.101 against 0.247+ for 20 shuffled copies. RB, WR, TE targets slope 1.05, carries 1.03; QB carries (td-expert's own model) 0.88, 878 against 887; throws by passer 1.05. By season, touchdowns over expected run 0.99 to 1.08 (2018-2020 high). nflverse marks a scramble rush 0 and pass 1: without them 32 of 2023's 496 rushing touchdowns were missing (the pitfall below).

**R3. The drive model is honest, and near misses are a description.** At the first snap (54,730 drives) error 1.27 points, slope 0.97; at the first snap inside the 20 (16,510 drives, 30%), scored 56.2% against 53.6% said, slope 0.96. Field-goal drives came closest at 46.2% on average; those that reached the 20 at 54.8% (75% passed 50%); touchdown drives peaked at 61.2%. Near misses per game are noise (0.04 week to week); per field-goal drive, a state (0.11, 0.07). O19 (85%) held.

**R4. Players: volume forecasts touchdowns as well as chances do; trees do better.** Next game, 59,819 played player-games 2016-2024; share of squared error removed against the rows' own average: rate 9.3%, B 11.8%, A 11.7%, trees 12.1%. Poisson log loss: B beats rung 0 by 2.95% (+2.59 to +3.30); **A ties B, +0.03% (−0.07 to +0.13)**, worse for RBs (−0.37%), better for WRs (+0.19%) and TEs (+0.35%); **trees beat B by 0.57% (+0.39 to +0.74)** and A by 0.54%, most for QBs (+3.0%) and RBs (+1.1%). Rest of season (75,865 rows): rate 34.8%, B 44.5%, A 43.6%; **A loses to B by 1.25% (−1.49 to −1.03)**, every position and every season. O3 (60%) held (inside its ±0.2%); O4 (25%) failed as expected; O5 (55%) failed; O22 (35%: trees +0.3%) held. Likely reason: stage 1 forecasts next game's chances assuming he plays; over a season, whether he plays and keeps his role is most of the room (I60), and volume's playing-time inputs carry it.

**R5. A quarterback's red-zone carries forecast his rushing touchdowns (I58 held).** Beside B, QBs' rows: rest of season **+3.34% of the log loss (+2.66 to +3.97), +10.6% of the squared error (+7.2 to +13.7)**, everyone +0.37%; next game +0.92% (+0.42 to +1.42), +1.6% of the squared error. It is in the shipped rest-of-season forecast. O17 (70%: 2%+) held (rest of season; next game under the bar).

**R6. A Poisson count is right for one player's game after a recalibration; it is too narrow over a season and too wide for 2+ in a game.** The first run failed the chance of 1+ (1.55 points, slope 1.12): the Poisson regression's mean was too high at both ends and low in the middle. A recalibration of the mean on the latest 20% of the training window (decision 0043 call 18) fixed it: 0.26 points, slope 1.01 (O11, 85%, held; the trees champion 0.42, 1.04). The chance of 2+ stays slightly too sure for the Poisson regressions (slope 0.89 players, 0.86 thrown: O12, 65%, failed at 3.4 points; the trees champion passes at 0.92): one game's touchdowns are a sum of small chances, less spread than a Poisson (I119). Over the rest of the season the Poisson is too sure the other way (players' 1+ error 8 points, slope 0.79; thrown 16, 0.45): whether he plays spreads the total (I116). Publish the means there, not the chances.

**R7. Knowing the passer doesn't change a throw's expected touchdowns (I61 killed).** The passer's thrown touchdowns over expected per throw before this season (shrunk by 300 throws) and his offense's EPA per play beside the situation: +0.04% of the log loss per throw (164,099 throws). Past thrown touchdowns still add to the rest of the season beside the expected ones: +4.13% (−0.81 to +8.92) with the plain expected, +4.06% (−1.05 to +8.77) with the passer-aware (987 rows; a straight line, not the exploration's lasso and trees, which found +5.5%). O18 (50%) failed. The QB's keep is his, not his offense's in the throw's situation.

**R8. The calling near the goal line adds nothing beside volume (H67, build).** The offense's goal-to-go pass share and pass rate over expected, removed from B: −0.01% next game (−0.03 to +0.01), −0.03% rest of season (−0.06 to −0.01); QBs +0.19% next game, TEs −0.08%. O15 (30%) failed.

**R9. Red-zone chances add nothing beside volume (H68, build).** Inside-20 and inside-10 chances beside B, non-QBs, rest of season: −0.02% (−0.05 to −0.00); RB −0.06%, WR −0.04%, TE +0.05%. O16 (15%) failed as expected.

**R10. Thrown touchdowns: chances win next game, volume over the season.** Next game, 5,630 QB-games: rate 10.1%, B 13.9%, A 14.3%; **A beats B by 0.19% (+0.01 to +0.37)** (O6, 50%, held) and rung 0 by 2.2%. Rest of season: B removes 65.8%, A 59.2%; **B beats A by 10.1% (−12.0 to −8.4)**, 8 of 9 seasons: a QB's season is whether he keeps starting.

**R11. Teams: a market-free forecast gets a small part of the room.** Next game (4,952 team-games): rate 4.2%, B 6.5%, A 5.7%; B beats rung 0 by 0.60%, A loses to B by 0.19% (O7, 50%, failed). Rest of season: rate 77.3%, B and A 77.9% (the games left carry it); A ties B (−0.29%, −0.64 to +0.07; O8, 45%, held as a tie), B beats rung 0 by 0.88%. Against R1's 61% ceiling, 6.5% next game says the team's touchdowns need a better team input: the opening total is the obvious one (I118).

**R12. The regression measure: players keep about a tenth, and it doesn't beat keeping none clearly.** Tested seasons 2016-2024, each fit on the 6 season pairs before (`build/regression_backtest.txt`). Rushing and receiving (2,209 player-seasons with 30+ chances): kept share QB 0.01, RB 0.16, TE 0.10, WR 0.09; against keep-none +0.38% (−1.07 to +1.91), against keep-all +51.4%. Thrown (308 QB-seasons with 150+ throws): kept 0.17; against keep-none −1.01% (−4.90 to +2.29), keep-all +49.3%. Keeping all is badly wrong; between keeping none and a tenth the data can't tell. O13 (75%) and O14 (50%) failed. The forecast's own shrinkage (100 chances, 300 throws) is the same idea at a level the backtest prefers.

**R13. The luck measure: a player's season total over expected is almost pure dice.** Player-seasons with a dice spread over 0.7 (3,128): touchdowns over expected in dice spreads have a spread of 1.04 (pure dice 1.00); 5.1% beyond 2 (dice 5%). Luck is 75% of the spread in totals for players expecting 2 to 4 touchdowns, 72% for 4 to 7, 38% for 7+. QB-seasons' thrown touchdowns: 1.15, a little more than dice (the one place a skill shows). The average touchdown came on a chance worth 29%; 22% came on chances under 10%. Christian McCaffrey's 26 in 2023 (playoffs in) on 17.7 expected had a 1.7% chance.

**R14. Consistency** (`pcf.validation.consistency`; [CONSISTENCY.md](../CONSISTENCY.md)): expected touchdowns a game 0.55 week to week, 0.57 season to season (trait); touchdowns over expected 0.03 and 0.05 (QB, WR, TE noise; RB 0.06, weak); the luck measure noise; thrown touchdowns over expected per throw 0.15 and 0.11 (the one touchdown efficiency that repeats); team touchdowns over the hindsight 0.21 and 0.15 (finishing from the 20, a trait). O20 (85%) held.

**R15. The vault (2025).** ⟨vault⟩

**R16. Football sanity.** See the table above: the top of every list is the backs and quarterbacks who run near the goal line; tight ends top out at about a third of a touchdown a game. Over the season, 2024's highest rest-of-season forecasts made before week 9 (`skill_rest_volume+qb_rz`; Poisson q10-q90 in brackets): Kyren Williams 9.5 (6 to 14; scored 6), Jalen Hurts 7.3 (4 to 11; 7), Saquon Barkley 7.1 (4 to 11; 9), Bijan Robinson 6.1 (3 to 9; 10), D'Andre Swift 6.0 (3 to 9; 2), CeeDee Lamb 5.6 (2), Jahmyr Gibbs 5.5 (3 to 9; 13). Sensible names; the misses (Gibbs, Swift) are the season-long spread R6 says a Poisson understates.

## The ladder

| Rung | Method | Players next game (log loss vs rung below) | Takeaway carried forward |
|---|---|---|---|
| 0 | `rate`: touchdowns a game, this season and last, shrunk to the position's rate by 4 games, times the games | — | |
| 1 | `volume` (B): Poisson regression on yards, chances, snaps, past touchdowns, playing time (participation's inputs), the team and the opponent | +2.95% | Volume carries touchdowns (exploration F2); playing time first (participation) |
| 1 | `chances` (A): stage 1 next game's expected touchdowns by kind and zone; stage 2 corrections | tie with B (+0.03%) | The kind of chance adds nothing beyond its count (opportunity-quality F4), again |
| 3 | `volume_trees`: boosted trees, Poisson loss, B's inputs | +0.57% over B | QBs and RBs gain: the rushing side bends (I117 tries trees elsewhere) |

## Where it misses
Lens list 2026-11-15, the players' next-game champion (`skill_next_volume_trees`), 2016-2024 (average miss = actual − forecast, touchdowns a player-game; the average forecast is 0.20).

| Lens | Group | Rows | Average miss | 90% interval | Known | Idea |
|---|---|---|---|---|---|---|
| tag | big favorite | 3,809 | +0.030 | +0.012 to +0.047 | before | the line (I118): 15% more touchdowns than said |
| tag | trap game | 2,930 | +0.025 | +0.004 to +0.046 | before | |
| tag | backup QB starts | 9,138 | −0.019 | −0.028 to −0.011 | before | the QB's availability as an input |
| team change | QB changed in season, games 1-4 | 14,175 | −0.015 | −0.021 to −0.010 | before | as above (F5) |
| player change | rookie, weeks 1-4 | 2,189 | +0.013 | +0.002 to +0.023 | before | |
| position | QB | 6,058 | +0.012 | +0.004 to +0.019 | before | |
| depth | unlisted | 3,496 | −0.012 | −0.022 to −0.001 | before | |
| home | home | 29,980 | +0.011 | +0.005 to +0.016 | before | |
| team points (after) | 31+ | 13,484 | +0.129 | +0.125 to +0.134 | after | game script: the line |
| margin (after) | won by 14+ | 10,776 | +0.090 | +0.085 to +0.096 | after | |
| snap share (after) | under 25% | 17,716 | −0.052 | −0.055 to −0.050 | after | as any forecast made before the game |

The pattern: the forecast knows who the player is but not the game it's in. The betting lines (big favorites, then the after-game team points and margin) are the clearest missing input.

## The case against
1. **The rest-of-season and team chances aren't calibrated,** so the product for anytime-scorer chances is next game only (players and QBs), and even there the chance of 2+ is a little too sure. A user who reads a rest-of-season "chance of 10+ touchdowns" from a Poisson will be misled (R6).
2. **The recalibration is a fix found on the backtest.** It was added after the first run failed calibration, and every rung got it, so it can't favour one method; but it is a choice made after seeing 2016-2024. The vault is its honest test ⟨vault⟩.
3. **A's loss over the season may be a design choice, not a verdict on chances.** Stage 1 assumes he plays; a stage 1 that forecast his chances including absences might close the gap. The brief's A was "chances, then corrections"; what lost is that A.
4. **The team forecast is weak** (6.5% next game) because it is market-free on purpose; anyone using it beside the betting total will find it adds little. The ceiling (R1) says the room is there.
5. **Most runs have 20 shuffled copies, not 100** (decision 0043 call 20): every champion beat all 20.
6. **The players' A runs were made before the ordering fix.** Their scorecards stand (check 8 passed); their reported comparisons come from walks after the fix (the same to 0.02%).
7. **The regression measure is a null result** in the backtest: 30+ chances and a kept share per position can't separate a tenth from nothing (R12).

## Pitfalls
- **Scrambles are rush 0, pass 1 in nflverse.** A `rush == 1` filter drops them (32 of 2023's 496 rushing touchdowns); count any run with a rusher. Opportunity-quality's filter has the same trap, harmless there because it scores no QBs.
- **An unordered join before a positional split changes the fit.** `unique` and `join` don't keep order by default in Polars; a penalty picked on the "latest 20%" by position then moves between runs (leakage check 8 caught it).
- **A rest-of-season window over the schedule needs the schedule's games once:** the REG schedule has two rows per game (one per team), which doubled the windows until `unique`.
- **A Poisson regression extrapolates in log space:** its biggest forecasts overshoot. Recalibrate, or use trees.
- **An expert's package may not import the table builders** (leakage check 1), even analysis code: the build's checks carry their own small Poisson-binomial.

## Not looked at
- Method C (player and seat), as the CEO decided.
- Explosive-play rate in the build (the exploration's 0.0% beside volume stands).
- Playoff games as forecast targets (the facts include them; the forecasts are regular season next games and windows).
- Two-point conversions, defensive and return touchdowns.

## Could be improved
1. A spread that fits a rest-of-season total (I116) and one game's 2+ (I119).
2. Trees for the other forecasts (I117).
3. The opening total for teams (I118; a market input: the CEO's call).
4. A stage 1 that includes absences, then A against B again over the season.

## Don't redo
- Red-zone chances beside volume for RB, WR, TE: three looks (exploration F2-F4, H68's build, opportunity-quality F4), nothing.
- The calling beside volume and the offense (H67's build).
- A passer-aware throw model for thrown touchdowns' keep (I61).
- The chance-sum as the team ceiling (F21; R1).

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `play.pbp`, `play.xfp` (opportunity-quality's expected touchdowns), `drive.summary`; `player_game` parts roster, snaps, game_status, depth, injury, stats, opportunity, touchdowns; `team_game` touchdowns, efficiency, tendencies; the schedule for windows |
| **Outputs** | Facts: `play.xtd` (tdx_ columns: kind, player, position, passer, team, yard line, air yards, xtd, td, source), `drive.td_chance` (p_start, p_rz, p_peak, reached the 20, field-goal try, hindsight), `player_game.touchdowns` and `team_game.touchdowns` (counts, touchdowns and expected by kind and zone, thrown, dice spreads, luck z, the chance of at least that many; teams: drives, red-zone trips, the hindsight, near misses). Forecasts: `outputs/td-expert/<variant>/<run_id>/history.parquet`, quantities `td_rush_rec`, `td_thrown`, `td_team` (next game) and `*_rest` (rest of the regular season): the mean count, Poisson q10/q50/q90 |
| **Level of detail** | play; drive; player-game; team-game; forecasts per player (or team) and the game a window starts on |
| **Interval** | facts 2012 on (expected touchdowns; drive chances 2006 on); forecasts weekly, 2016-2024 reported plus the 2025 vault, every rostered QB, RB, WR, TE and every team |
| **Cadence** | in_season |
| **Known at** | facts with the play-by-play (kickoff + 1 day); forecasts at the Saturday run |
| **How to use it** | Next game: the mean and the chance of 1+ = 1 − exp(−mean) (calibrated for players and QBs); the chance of 2+ a little too sure (R6). Rest of season: the mean only. Expected touchdowns a game as a feature (a trait); touchdowns over expected is noise except a QB's thrown (R14). The luck measure looking back only. From saved histories only (rule e) |
| **Feeds** | TD-scorer props, fantasy-projections, player-opportunity; candidates vacated-opportunity |

## Open questions for the CEO
⟨in the report⟩
