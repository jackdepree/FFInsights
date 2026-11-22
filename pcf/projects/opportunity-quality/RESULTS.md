# Results: Opportunity quality (`opportunity-quality`)

**Date:** 2026-11-22 (built 2026-11-21 to 22) · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `opportunity-quality` · **Champion:** `eff_trees`, run `3b5fd214e10d43559ad1fd21428202e8` (pinned in the registry; no MLflow model registered, as participation) · **Decisions:** [0041](../../docs/decisions/0041-opportunity-quality.md)

## In short
Expected fantasy points per chance are now a table (`play.xfp`, `player_game.opportunity`, from situation models fit from 2009, r 0.99 with nflverse's), and both of the CEO's main outputs are built. **The forecast of opportunity** (next game's expected PPR points) is honest and useful: the trees rung beats its shuffled copies, the last-4 average by 19% of the range score, counts by 2.5% and the lasso by 1.8%; it passes the no-noise target even beside playing time (+3.7%), and adds 4% to the yardstick's crude forecast of yards. Past efficiency is part of why (H61 held again, +1.1%). **The regression measure** is calibrated but weak: a per-player kept share (method B) beat one rate per position (method A) in 2016-2024 and lost to it on the 2025 vault, so A's number ships, and the chance a gap closes almost never leaves 50-60%. The kind of chance (goal line, end zone, deep) adds nothing beyond counts at any horizon.

**Scorecard:** `outputs/opportunity-quality/eff_trees/3b5fd214e10d43559ad1fd21428202e8/scorecard.html` · **Vault (2025), opened once, 2026-11-22:** the forecast held (20 of 20 shuffles, all 10 checks, beats the lasso by 1.3%, ranges 79.9%; R22); the regression measure: B lost to A by 1.0% (R17) · **Versions tried:** 13 forecast variants on one feature set (counts, xfp, eff, eff_trees, two yards variants, six horizons) plus the measure's methods A, B, B with yards after the catch

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal | `eff_trees` beats 20 of 20 shuffled refits (`eff`, `eff_h3`, `eff_rest` 100 of 100); the regression measure 100 of 100 copies with its forecasts moved between players; the yards variants 20 of 20 |
| No noise | Next game's PPR points on targets and carries, 2019-2024: the forecast adds +13.6% of squared error, +8.7% range score against the brief's baseline (past points, targets, carries, snaps); **+3.7% (+3.4 to +4.0), +2.6% range score beside participation's playing-time inputs**. Adds value both ways |
| Beats baselines | Range score, 2016-2024: last-4 expected points −19%, counts −2.5%, the lasso (`eff`) −1.83% (−2.1 to −1.6); every 90% interval clear. Horizons: `eff_h3` beats counts by 1.23%, `eff_rest` by 0.90% |
| Calibration and range coverage | Chance of a chance: error 0.8 points, slope 1.00. If he gets one: ranges hold 79.4% (80% target), 50.0% above the median. Horizons' ranges 80.4% and 80.5%, every position 80-81%. The regression measure's chance the gap closes: error 0.9 points, slope 0.92 (backtest), 0.9 and 0.85 (vault), once recalibrated |
| Leakage | All 10 checks pass for every validated variant (25 cutoffs); the measure's windows don't move when the future is deleted (test) |
| Football sanity | The CEO's review: ⟨pending⟩. Claude's: 2024's highest forecasts (8+ games) are Kyren Williams 16.8 expected points a game (got 15.2), CeeDee Lamb 16.5 (16.9), Justin Jefferson 16.4 (16.9), Bijan Robinson 16.3 (18.1), Amon-Ra St. Brown 15.7 (15.1), Saquon Barkley 15.7 (16.9); tight ends' top tenth starts at 7.9 against 11.3 for receivers and 12.8 for backs |
| CEO spot-check | ⟨pending⟩ |

## Hunch verdicts
Copied into [`projects/HUNCHES.md`](../HUNCHES.md). The exploration's verdicts stand where the build didn't retest.

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H56 | Goal-line chances are worth the most | held; real, doesn't pay | Per chance they are (R2). Beyond counts they add nothing to next game (range score +0.00%) and add noise over the next 3 games (−0.15%) and the rest of the season (−0.25%) (R4, R19) |
| H57 | Expected points follow a player to a new team | partly (exploration; not retested) | Movers 0.52, stayers 0.67 (F7, F8) |
| H58 | Strong yards-after-catch receivers beat their expected points | unclear | A weak trait (WR 0.09 week to week); as an input to the measure it helps tight ends (+0.60% backtest, +1.62% vault), not receivers (+0.09% backtest, −0.89% vault) (R6) |
| H59 | Expected points are more consistent than efficiency | held | 0.84 against 0.13 per game week to week; per chance 0.75 against 0.02 (R3) |
| H60 | Opportunity by scheme follows movers better | failed (exploration; method C not built) | F10 |
| H61 | A player creates his own opportunity through efficiency | held, small | +1.11% of squared error (+0.87 to +1.33) on next game's expected points; first two seasons +1.47%; fitting noise 0.02 (R10, R15) |
| H62 | Players whose pattern holds across teams don't regress | failed, leaning (exploration; not retested) | F12. The build's per-player rates come from sample size alone, and lost to one rate per position on the vault (R17) |

## Terms
In `docs/GLOSSARY.md`: **chance**, **expected points of a chance** (PCF's xfp), **points over expected**, **the gap**, **kept share**, **chance the gap closes**, **chance of a chance**. The brief's "seat" wasn't needed (method C not built).

## Findings
Build findings are R1-R22; the exploration's are F1-F13.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | **The expected-points table matches nflverse's** at r 0.992 per player-game (64,795; 0.990-0.994 every season 2012-2025), means 7.94 against 8.12. The situation alone removes 6.8% of a target's squared error and 13.6% of a carry's | `build/facts.txt` | strong | RB, WR, TE, 2012 on |
| R2 | **Points per kind of chance, on the 2009-start model, are the exploration's:** an end-zone target from the 10 or closer 3.36 points (45% a touchdown), a carry inside the 2 3.18 (52%), against 1.69 for an average target and 0.63 for a carry. The td-expert pitfall (biased 2006-2008 targets) didn't move them | `build/facts.txt` | strong | 2019-2024 |
| R3 | **Expected points are a trait; efficiency per chance is noise.** Per player-game, 2012-2024: expected points 0.84 week to week, 0.75 season to season; points over expected per game 0.13 and 0.17 (weak, carried by volume); per chance 0.02 (−0.00 to 0.04) and 0.03: noise. Expected points per chance 0.75 and 0.78, deep-target share 0.42 and 0.45, goal-line share 0.17 and 0.20 | `build/facts.txt`, CONSISTENCY.md | strong | RB, WR, TE |
| R4 | **The kind of chance adds nothing beyond the count next game** (exploration F4, rechecked): goal-line carries, red-zone, end-zone and deep targets, air yards and expected touchdowns: +0.08% of squared error, +0.00% range score on next game's points; +0.05% beside the forecast; +0.04% (not clear) on next game's expected points | `build/downstream_eff_trees.txt` | strong | next game |
| R5 | **In 2016-2024, method B (a kept share per player) beat one rate per position** on the rest of the season's points over expected per chance: +1.19% of the weighted squared error (+0.95 to +1.44); RB +1.90%, WR +0.69%, TE +2.12%. A beat "all luck" by +2.71%; "it all lasts" is 38% worse than all luck. Shuffled null 100 of 100. At week 1 (next season) they tied: +0.74% (−0.39 to +1.79) | `build/regression_backtest.txt` | strong (but see R17) | 2016-2024, 20+ chances behind, 10+ ahead |
| R6 | **Yards after the catch pay for tight ends only.** Added to B: TE +0.60% (backtest), +1.62% (vault); WR +0.09% and −0.89%; RB +0.00% and −0.80%. The receivers' weight flips sign between seasons; the tight ends' is positive every season | `build/regression_*.txt` | suggestive | TE |
| R7 | **The kept share rises with chances, but B keeps too much at 200-400:** kept 0.12, 0.23, 0.36, 0.48, 0.60 at 20-50, 50-100, 100-200, 200-400, 400+ chances; seen 0.10, 0.16, 0.36, 0.36, 0.54 (backtest). On the vault, the seen shares are flat (0.21-0.25 below 400) | as R5 | strong | |
| R8 | **The chance the gap closes is honest but not sharp.** Gaps close by half or more 55% of the time. Raw, B is overconfident (error 2.7 points, slope 0.63); recalibrated on earlier seasons, 0.9 and 0.92. 72% of the chances sit between 50% and 60%, under 1% above 80% | as R5 | strong | |
| R9 | **The lasso forecast of opportunity works** (`eff`): range score 0.82 (MAE 2.56 points; average 5.03; 36% of rostered player-games get no chance); beats the last-4 average by 17.6%, counts by 0.69%, expected points without efficiency by 0.60%; 100 of 100 shuffles | the `eff` scorecard | strong | RB, WR, TE, 2016-2024 |
| R10 | **H61: efficiency earns work.** Past points over expected improve next game's expected-points forecast by +1.11% of squared error (+0.87 to +1.33), +0.60% range score; first two seasons +1.47%, veterans +0.96%; WR +1.44%, RB +0.94%, TE +0.43%. The fifth most over expected this season are forecast 0.55 expected points a game above the forecast without efficiency, and get 0.53 more; the fifth most under −0.45 and −0.56 | walks on the saved features | strong | |
| R11 | **Past expected points add little beside counts and playing time:** +0.12% of squared error (+0.01 to +0.24), +0.09% range score, 3 times the fitting noise. The exploration's F5 (+0.73%) was beside past points with no counts | as R10 | strong | |
| R12 | **Trees beat the lasso on the same inputs:** +2.75% of squared error (+2.24 to +3.27); seeds 0, 1, 2: +2.85, +2.86, +2.78 | `build/downstream_eff.txt` | strong | |
| R13 | **The forecast passes the no-noise target, also beside playing time:** next game's PPR points on targets and carries, 2019-2024: +13.6% of squared error against past points, targets, carries, snaps and position (RB +16.2%, WR +13.2%, TE +8.9%); participation's playing-time inputs alone give +10.3%, and the forecast beside them still +3.69% (+3.35 to +4.04), +2.56% range score. Past expected points alone add nothing (−0.05%; the exploration's −0.19%) | `build/downstream_eff_trees.txt` | strong | 2019-2024 |
| R14 | **On the yardstick, expected yards add about 4%.** Alone on the crude forecast of next game's yards (2019-2024): the expected receiving yards forecast +4.15% (+3.72 to +4.58), range +2.87%; expected rushing yards +4.55% (+3.68 to +5.39), range +2.58%; the trees' expected points forecast +2.1% (receiving) and +3.6% (rushing). The crude forecast already has participation's forecasts | as R13 | strong | receiving, rushing |
| R15 | **Fitting noise is small:** one training season left out moves each gain by 0.02-0.04 points of share and the no-noise gain by 0.10; trees' seeds by 0.08 | as R13 | strong | |
| R16 | **The situation model under-expects tight ends, and receivers more each year:** the average points over expected per chance, from the six earlier seasons: TE +0.09 every season; WR +0.025 (2016) rising to +0.073 (2024); RB 0 to +0.03. The measure subtracts it; the raw table doesn't | `build/regression_backtest.txt` | strong | |
| R17 | **On the 2025 vault, method B lost to one rate per position:** −0.98% (−1.19 to −0.78); TE −4.17%, RB −0.36%, WR −0.17% (not clear). A beat "all luck" by +3.24%. B's recalibrated chance the gap closes stayed calibrated (0.9 points, slope 0.85); its future-gap range held 79.0%. So A's mean ships (the brief's rule) | `build/regression_vault.txt` | strong for TE; one season | 2025 |
| R18 | **The longer horizons work:** next 3 games and rest of season, expected points per game, beat counts by 1.23% and 0.90% of the range score; 100 of 100 shuffles; ranges hold 80.4% and 80.5% | `build/forecast_eff_h3.txt`, `forecast_eff_rest.txt` | strong | 2016-2024 |
| R19 | **Goal-line work adds noise at the longer horizons:** on actual points, counts + kinds against counts: next 3 games −0.15% range score (−0.21 to −0.08), rest of season −0.25%; beside playing time −0.12% and −0.26%; on expected points neutral (−0.00%, −0.07%) | `build/horizons.txt` | strong | |
| R20 | **The trees rung passes the harness:** `eff_trees` beats 20 of 20 shuffles, the lasso by 1.83% range score (−2.1 to −1.6), all 10 leakage checks; chance of a chance error 0.8 points, slope 1.00; ranges 79.4% | the `eff_trees` scorecard | strong | |
| R21 | **The forecast's largest misses are players active while questionable** (+1.09 expected points more than forecast, +0.82 to +1.37, 1,746 rows) and the first game back from injury (+0.53); depth-chart unlisted players get 0.47 less | `eff_trees` misses | strong | idea I102 |
| R22 | **The forecast holds on the 2025 vault:** `eff_trees` range score 0.760 (MAE 2.36), beats 20 of 20 shuffles, the lasso by 1.33% (−1.7% to −0.9% in loss), all 10 leakage checks pass; chance of a chance error 1.4 points, slope 1.05; if he gets one, ranges 79.9%, 50.0% above the median | `build/forecast_eff_trees_vault.txt`, run `1f8a71d7…` | strong | 2025 (7,675 player-games) |

## The ladder
Next game's expected PPR points, 2016-2024, range score.

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | Last 4 rostered games' expected points (absences 0) | — | |
| 1a | `counts`: playing time (participation's inputs) + past targets, carries, snaps; two-part lasso | −17.0% vs rung 0 | Playing time first (participation) |
| 1b | `xfp`: + past expected points | −0.09% vs counts (R11) | Small: counts already carry it |
| 1c | `eff`: + past points over expected, per chance, yards after the catch | −0.60% vs xfp (R10) | The efficiency inputs are the gain (H61) |
| 3 | `eff_trees`: boosted trees on `eff`'s inputs | −1.83% vs eff (R20) | Interactions matter (playing time × efficiency); the next rung would be tuned trees or a blend |

The horizons stop at rung 1 (lasso; `goal_*` didn't beat `eff_*`, R19); trees there are idea I103.

## Where it misses
Lens list 2026-11-15, `eff_trees`, 2016-2024 (average miss = actual − predicted, expected points).

| Lens | Group | Rows | Average miss | 90% interval | Idea |
|---|---|---|---|---|---|
| position | WR | 29,208 | −0.08 | −0.13 to −0.04 | |
| depth | unlisted | 5,697 | −0.47 | −0.58 to −0.35 | |
| week | 10-14 | 17,715 | −0.12 | −0.17 to −0.07 | |
| team points (after) | under 17 | 17,534 | −0.28 | −0.33 to −0.24 | game script: pace and Elo next |
| margin (after) | lost by 14+ | 11,467 | −0.18 | −0.23 to −0.12 | |
| player change | first game back from injury | 1,276 | +0.53 | +0.32 to +0.75 | I102 |
| team change | first game after a bye | 2,141 | −0.30 | −0.43 to −0.17 | |
| tag | active while questionable | 1,746 | +1.09 | +0.82 to +1.37 | I102 |
| tag | rookie | 11,728 | +0.11 | +0.02 to +0.19 | |

(The snap-share lens is after the game: players on 75%+ of snaps get 1.64 more than forecast, as any forecast made before the game would.)

## The case against
1. **The regression measure is weak and changed its winner on the vault.** B beat A in nine backtest seasons and lost in 2025, almost all through tight ends. One season is one season, but the vault is the confirmation, so A ships. Whichever ships, the measure removes only 3% of "all luck"'s error, and 72% of its chances sit between 50% and 60%: a "buy low" list from it would be mostly coin flips.
2. **The no-noise pass is mostly playing time.** Against the brief's baseline it adds 13.6%; beside participation's inputs, 3.7%. The second is the honest number for a downstream user who already has participation.
3. **The yardstick's 4% looks large** for an input the crude forecast nearly has (past yards). The likeliest reason is real: expected yards are past yards with the luck taken out. The rows are lined up by moment (a forecast made after its row is refused), and the forecasts pass every leakage check, but the yardstick's own shuffled-copy check wasn't run for these columns.
4. **"Expected" isn't expected for tight ends** (R16): a model without position calls every tight end efficient by 0.09 a chance. The measure subtracts the average, but a reader of the raw table will be misled; and it may be why B fails for tight ends on the vault (idea I100).
5. **The trees champion has 20 shuffles, not 100** (the harness's 20-of-20 rule; each tree refit is slow). It beat all 20, and the lasso on the same inputs beat 100 of 100.
6. **2016-2018 are in every downstream model's training,** so the no-noise and yardstick gains are 2019-2024 only, on one set of training seasons (fitting noise 0.10).

## Pitfalls
- **A null `sack` dropped targets:** `sack != 1` drops nulls in Polars; `fill_null(0)` first.
- **Reading saved files from an expert's package fails leakage check 1,** even analysis code. The readers now live in `pcf.validation.backtest` (`save_features`, `load_features`, `latest_history`).
- **A saved feature history's step numbers count from its first season;** walking it again needs the same first season (`downstream.walk_saved`).
- **Participation's saved histories stop at 2024,** so an expert reading them can't be scored on the vault; this one recomputes participation's inputs (decision 0041).
- **A synthetic world's single season is too small for a 20-of-20 signal test** of a two-part forecast (17 of 20 on 114 rows); the test uses two seasons.

## Not looked at
- Method C (player and seat) and H60, as the CEO decided; H57 and H62 not retested.
- Pace's team volume forecasts as inputs (decision 0041, call 8).
- Half-PPR and standard: the table supports them; only PPR was validated.
- Playoff games: scored by the expected models, not validated.

## Could be improved
1. Position in the expected-points model (I100), then B against A again.
2. A skewed noise model for one chance's points over expected (I101).
3. Trees for the horizons and the yards variants (I103).
4. A known-active flag for players listed questionable, if a free source has it in time (I102; a new source needs the CEO's sign-off).

## Don't redo
- The kinds of chance beyond counts: three looks (F4, R4, R19), nothing. Retry only with a new outcome (touchdowns: td-expert).
- Past expected points beside counts: +0.12% (R11).
- A per-player kept share from sample size alone: it lost on the vault (R17). Retry only with a better noise model or position (I100, I101).

## Interface card
Also in this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | `play.pbp`; `player_game` parts roster, snaps, game_status, depth, injury, stats, opportunity through the gateway; game schedule for the horizons |
| **Outputs** | Facts: `play.xfp` and `player_game.opportunity` (`oq_` columns: chances, targets, carries, catches, yards, touchdowns and their expected values; goal-line, red-zone, end-zone and deep chances; air yards; yards after the catch over expected). Forecasts: `outputs/opportunity-quality/<variant>/<run_id>/history.parquet`: `eff_trees` (next game's expected PPR points, with `p_nonzero`, `if_nonzero_*`), `eff_h3`, `eff_rest` (per game over the next 3 and the rest of the season), `eff_rec_yards`, `eff_rush_yards`. The measure: `outputs/opportunity-quality/regression/<tag>/history.parquet` (points over expected per chance over the rest of the season: mean by method A, q10-q90; `kept_share`, `true_q10`, `true_q90`, `p_gap_closes`, `mean_B`, `gap`, `chances`) |
| **Level of detail** | play; player-game; for horizons, the game the window starts on |
| **Interval** | facts 2002 on (expected values 2012 on); forecasts and measure weekly, 2016-2024 reported plus the 2025 vault, every rostered RB, WR and TE; the measure for players with 20+ chances behind them, regular season |
| **Cadence** | in_season |
| **Known at** | facts with the play-by-play (kickoff + 1 day); forecasts and measure at the Saturday run |
| **How to use it** | Expected points per player-game as an opportunity feature (a trait, R3). The forecasts as features for points and yards, from saved histories only (rule e); beside participation the trees forecast still adds 3.7% (R13). The measure as a player-card number and a prior, not for sorting players (R8) |
| **Feeds** | td-expert, vacated-opportunity, player-opportunity, fantasy-projections; the yardstick |

## Spot-check: R17 and the luck measure (the CEO's pick, 2026-11-22)

The CEO's words: "Please spot check r17 and the luck measure. If the luck measure comes out of the spot check better than before, then we will add it to the player card." The CEO also chose B as the number to publish (their 3b), knowing the vault said A, and asked for I100 and I101 to be tried inside the spot-check (their 4c).

### Pre-registered, 2026-11-22, before any run

**What gets tried.** Two fixes, alone and together, so there are four versions of the measure: as built; I100; I101; both.
- **I100, position in the expected-points model.** The five situation models are refit with his position as one more input, on the same seasons. "Expected" then means expected for an average player *at his position* in that spot. The gaps and the future gaps are recomputed from it.
- **I101, the noise model.** A skewed distribution alone doesn't change the noise in an average of many chances (the variance of a mean is σ²/n whatever the shape). What can make B keep too much (0.45 kept against 0.25 seen at 200-400 chances on the vault) is chances that aren't independent: a player's chances in one game share a quarterback, a defense and a game plan. So I101 is tried as **game-level noise**. Per position, a factor φ is fit on the same 6 earlier seasons: how much a player's game-to-game swings exceed what independent chances would give. Every noise term (V, and the future chances' noise) is multiplied by it. φ = 1 is the build's model.
- A's mean doesn't use the noise model, so I101 changes only B and the chances. I100 changes the gaps themselves, so A and B are compared within each version, never across.

**How the winner is picked.** The 2025 vault has already been looked at once for this measure (R17), so it can't pick the winner as well as judge it. The version used for the bar is the one with the best B-against-A on 2016-2024. Ties within 0.1% go to the simpler one, in the order: as built, I101, I100, both. The vault then judges that one version. The other versions' vault numbers are reported, but they don't count toward the bar.

**"Better than before" means all three, for the picked version:**
1. **B is at least as good as A:**
   - on the 2025 vault, B against A ≥ 0.0% of the weighted squared error, with tight ends ≥ −0.5% (was −0.98% and −4.17%);
   - and B still beats A by ≥ +0.5% on 2016-2024 (was +1.19%).
2. **Calibration stays honest:** B's recalibrated chance the gap closes has a calibration error ≤ 2.0 points and a slope between 0.80 and 1.25, on the vault and on 2016-2024 (was 0.9 points and 0.85 on the vault).
3. **The chances separate players more:**
   - the share of chances between 50% and 60% falls to 60% or less (was 72% on 2016-2024, 74% on the vault);
   - and the chance's Brier skill against the training seasons' base rate is higher than the build's on the vault. Without this, spreading the chances could be noise.

**What follows:**
- All three pass: the luck measure goes on the player card.
- Any one fails: it stays off, with the reason written here.
- B is published as the CEO chose. If test 1 still fails, this section says so plainly and the CEO confirms B over A before the merge.

**Claude's odds (before any run):**

| Event | Chance | Expected size |
|---|---|---|
| Test 1 passes | 35% | B against A on the vault moves from −1.0% to about −0.3% |
| Tight ends alone pass (≥ −0.5%) | 40% | |
| Test 2 passes | 85% | |
| Test 3's 50-60% share falls to 60% or less | 15% | about 70% |
| Test 3's Brier skill rises | 45% | |
| All three pass (it goes on the card) | 8% | |
| The picked version is I101 or both | 60% | φ about 1.2-1.5 |

**Why the odds are low:** the rest of a season is about 40 chances, and over 40 chances one player's points over expected are mostly noise. A better mean moves the forecast of the gap, but it barely moves whether the gap lands on the near side of half. So the chances can't spread much without signal the measure doesn't have.

### The spot-check

⟨running⟩

## Open questions for the CEO
1. Ship method A's mean for the regression measure (the vault's verdict), or keep B because it won nine backtest seasons?
2. Is a measure whose chances sit at 50-60% worth a line on the player card, or should the card show the kept share instead?
3. Should I102 (a known-active flag for questionable players) go to the data-source list?
