# Results: Snap leverage (`snap-leverage`)

**Date:** 2026-11-14 · **Status:** the build failed the no-noise target, so by the CEO's rule the project is downscaled from an expert to an investigation and feature engineering (the CEO, 2026-11-14: "if it fails the no noise target then we will downscale this project from an expert to simply an investigation and feature engineering"). **The CEO's pick (2026-11-14): "(a) Part + usage part"**. `play.leverage` stays, a new post-season part `player_game.leverage_usage` is built from true participation, and the nine forecast variants left the package ([decision 0034](../../docs/decisions/0034-snap-leverage-features.md)). · **Brief:** [BRIEF.md](BRIEF.md) · **Decisions:** [0033](../../docs/decisions/0033-snap-leverage-build.md), [0034](../../docs/decisions/0034-snap-leverage-features.md) · **MLflow experiment:** `snap-leverage` · **Champion:** none

## In short
**Leverage before the snap works as a measure, but weighting a player's snaps by it doesn't forecast his playing time better than plain snap share.**
- **The no-noise target fails** (R1). Leverage share added to plain snap share makes the next 3 games' snap-share forecast worse:
  - range score +0.23% (90% interval +0.17% to +0.29%);
  - the role gap and trust over expected on top: +0.31% (+0.21% to +0.42%);
  - worse with every one of five random seeds (R2), and in every season but 2024 (R3).
- **Even forecasting leverage share itself, plain snap share does as well** (R4). Leverage share is 0.997 alike with snap share as an outcome, so there is little left for the leverage features to explain.
- **The forecasts themselves are honest.** Every variant beats 20 of 20 shuffled refits, its 80% ranges hold 79.0–79.5%, and all 9 blocking leakage checks pass (R6). They just don't beat plain.
- **What lasts:** the shared `play.leverage` part, which correlates 0.555–0.559 with a play's actual swing (R7). Also the usage measures: the passing-down role gap, which repeats and which the contract market pays for (snap-leverage#F10). And the finding that the exploration's +0.14% was about the size of the fitting noise (R5).

**Scorecards:** `data/outputs/snap-leverage/<variant>/<run_id>/scorecard.html`. **Numbers:** [explore/ladder.txt](explore/ladder.txt), [explore/seeds.txt](explore/seeds.txt), [explore/map_cost.txt](explore/map_cost.txt), [explore/map_or_setup.txt](explore/map_or_setup.txt).
**Vault (2025):** closed, not spent. Nothing ships, so there's nothing to confirm. **Versions tried:** 11 attempts in MLflow (one per variant; `snap_next3_plain` and `snap_next3_lev` twice, before and after R8's fix).

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | **Signal: pass.** All nine beat 20 of 20 shuffled refits (range score 0.048–0.050 against 0.081–0.087 shuffled). **No noise: fail.** The leverage rungs are worse than plain snap share on the CEO's target (R1, R2) |
| Calibration and range coverage | Pass. 80% ranges hold 79.0–79.5%, 49.6–50.4% land above q50; every position group and season inside the bar |
| Leakage | 9 of 9 blocking checks pass for all nine variants (after R8's fix); no feature above \|r\| 0.9 |
| Football sanity | The top forecasts are full-time QBs, linemen and safeties; the lowest are deep backups. The CEO's review is pending |
| CEO spot-check | Pending (the CEO picks after these results) |

## The ladder
Each rung against the one below on the same rows, 2020–2024, as % of the lower rung's score (+ = worse; 90% interval resampling weeks). Every rung is the same trees, so a comparison changes only the features (decision 0033, call 6).

| Target | `lev` vs `plain` (range score) | `full` vs `plain` | `full` vs `lev` | Rows |
|---|---|---|---|---|
| **Snap share, next 3 games** (the no-noise target) | **+0.231%** (+0.170 to +0.288) | **+0.311%** (+0.213 to +0.415) | +0.080% (−0.006 to +0.164) | 120,809 |
| Leverage share, next 3 games | −0.018% (−0.110 to +0.080) | +0.182% (+0.083 to +0.283) | +0.200% (+0.071 to +0.333) | 120,809 |
| Leverage share, rest of season | +0.386% (+0.275 to +0.503) | +0.341% (+0.210 to +0.477) | −0.045% (−0.118 to +0.028) | 137,209 |

The squared error tells the same story (`ladder.txt`). **The ladder stops at rung 0:** plain snap share.

## Findings
| # | Finding | Evidence | Confidence |
|---|---|---|---|
| R1 | **Leverage share, from the morning-after map, adds noise to plain snap share** on the next 3 games' snap share: range score +0.23%, squared error +0.45%. With the role gap and trust over expected: +0.31%, +0.54% | `ladder.txt` | strong |
| R2 | **Not a lucky seed.** The trees stop early on a random tenth of each training window. Over five seeds, leverage share is worse every time (+0.03% to +0.23%; mean +0.11%), and so is the full rung (+0.26% to +0.38%) | `seeds.txt` | strong |
| R3 | **No season and no position where it helps.** By season: 2020 +0.40%, 2021 +0.14%, 2022 +0.42%, 2023 +0.19%, 2024 +0.01% (even). Worst at QB (+0.91%) and RB (+0.38%). First-year players: even (−0.01%), where the exploration's gain was largest. The full rung is better only in 2024 (−0.17%, −0.31 to −0.02), the season with the most map seasons behind it | `ladder.txt` | strong (2024: suggestive) |
| R4 | **As outcomes, leverage share and snap share are nearly the same thing** (0.997 correlated per player and window). Forecasting leverage share itself, plain snap share ties the leverage rung over the next 3 games and beats it over the rest of the season (+0.39%) | smoke test; `ladder.txt` | strong |
| R5 | **The exploration's +0.14% was about the size of the fitting noise.** Rerunning the exploration's own test with nothing changed but the row order moved true leverage share's gain from +0.15% to +0.10%, and the map's from +0.15% to −0.02%. A gain that small needs several seeds before it counts | `map_or_setup.txt` (two runs) | strong |
| R6 | **The forecasts are honest:** all nine beat 20 of 20 shuffled refits, hold 79.0–79.5% in their 80% ranges, and pass every leakage check | scorecards | strong |
| R7 | **`play.leverage`**, leverage before the snap, fit each season on up to 10 earlier seasons, correlates 0.555 (2016) to 0.559 (2024) with a play's actual swing, like the exploration's (F1: 0.54–0.58) | decision 0033 | strong |
| R8 | **Sums in a varying order broke a leakage check.** A parallel join's row order varied, so the leverage measures differed between runs in the 16th digit. That was enough to flip a tree's split, and check 8 (test labels) failed on 3–21 rows at 4 of 5 steps. Fixed by summing in a fixed order; a test shuffles the input | `usage.py`; tests | strong |
| R9 | **The map measures snap share and leverage share almost exactly** (0.998 and 0.991 against true participation, 2019–2024). **The role gap and trust over expected only roughly:** 0.53 and 0.40 per player-game. Yet the map's versions repeat more week to week (0.83 against 0.77; 0.33 against 0.25), so part of their steadiness is the map's own prior (it leans on each player's past habits) | `map_cost.txt` | strong |

## Hunches: what the build adds
| # | Hunch | Exploration | The build |
|---|---|---|---|
| H45 | Weighting snaps by their stakes shows "which players a team relies on" and predicts "future playing time" (main test) | unclear, small (+0.14%) | **Failed on the main test.** Live, from the map, it adds noise (+0.23%; every seed worse; R1–R3). The secondary tests stand as the exploration found them: contracts +1.7% from the raw role gap (the passing-down role, not trust); plus-minus at the edge |
| H46–H49 | Starters trusted more; the situation trap; WR and CB; schemes | unclear / failed / unclear / failed (leaning) | Not retested |

## The case against
The strongest argument that this verdict is wrong:
1. **The build's setup is not the exploration's.**
   - **What differs:** official snap counts for plain snap share and the target; rows before every game, week 1 included; last season's shares; the harness's recency weights; the map instead of true participation.
   - **What it showed:** in one run of the exploration's own setup, the map's leverage share helped (+0.15%) (R5). So some setup might pass.
   - **Against it:** the same test, rerun, gave −0.02%. The build's honest walk-forward is worse with every seed.
2. **Too few seasons of the map.**
   - **The concern:** 2020 is fit on 2019 alone. 2024 has five map seasons behind it, and only there are both rungs even or better (R3).
   - **Why it matters:** the leverage features may need more training seasons than snap share does. One season is not a trend.
   - **What it would take to check:** rescore once 2025's map exists.
3. **One target.**
   - **The concern:** the CEO's no-noise target is snap share. Leverage measures could still help a different downstream model: contracts (+1.7% from the role gap, F10), injuries' cost (plus-minus, F11), fantasy opportunity.
   - **Why it matters:** rule k says an expert doesn't have to beat other models. Downstream feature selection decides that.
   - **What it would take to check:** that's exactly what feature engineering keeps open.
4. **Trees and near-duplicates.**
   - **The concern:** leverage share is 0.99 alike with snap share, and trees split on whichever copy is noisier by chance.
   - **What it would take to check:** a linear rung, or the leverage measure minus snap share (a cleaner new feature). The exploration's linear check agreed with the trees.

## Pitfalls
- **Sums in a varying order** fail check 8 for tree models (R8). Sort before summing, and sum within each group in that order.
- **Runs die with the session.** A computer restart and a session end each killed the backtests partway. Start long runs detached, with a progress file.
- **A column with no values crashes the trees' binning.** `lev_prev` is empty when 2019 is the only training season. The fit leaves such a column out.
- **One seed is one draw.** A gain under about 0.2% needs several seeds (R2, R5).

## Not looked at
- A linear rung, and a cleaner feature: leverage share minus snap share.
- The usage measures from true participation in a retrospective model (contracts, plus-minus): the secondary tests at build level.
- The vault: not spent, since nothing ships.

## Could be improved
1. **Test the measures downstream:** `player_game.leverage_usage` in a contract or roles model (done as feature engineering: decision 0034).
2. **Rescore when the map has more seasons** (case against 2), with five seeds.
3. **The passing-down role gap in a contract model**, within position (IDEAS I43).

## Don't redo
- Don't add leverage share beside snap share for playing-time forecasts: it's 0.99 alike, and adds noise live (R1–R4).
- Don't read the map's role gap or trust over expected as a player's own steadiness: part of it is the map's prior (R9).
- Don't trust a playing-time gain under 0.2% from one seed (R5).

## Interface card: what lasts
| | |
|---|---|
| **Inputs** | `play.pbp` (situation, WPA; the leverage model is refit each season on up to 10 earlier seasons), `play.pace` (expected pass chance), `player_play.on_field` (true participation) |
| **Outputs** | `play.leverage`: `wpa_sd` (win-chance units), `leverage` (1.0 = average snap), `high_stakes` (the top fifth of the training snaps). `player_game.leverage_usage`: `lev_side`, `lev_snaps`, `lev_snap_share`, `lev_share`, `lev_hs_share`, `lev_role_gap` (the passing-down role gap), `lev_trust_oe` (trust over expected). `pcf.data.usage`: the same measures from any on-field chances (the morning-after map, live) |
| **Level of detail** | play (runs, passes, kneels, spikes with a win chance; every season type; no two-point tries); player-game (on the side he played most) |
| **Interval** | `play.leverage` 2002–2026; `leverage_usage` 2016–2025 |
| **Cadence** | `play.leverage`: in season, after each game. `leverage_usage`: retrospective (post-season only, rule m) |
| **Known at** | `play.leverage`: with the play-by-play (after kickoff). `leverage_usage`: with participation, the day after the Super Bowl |
| **How to use it** | Weight plays by stakes, or pick high-stakes plays before the snap (not the after-the-fact `high_leverage` tag). The passing-down role gap for contracts and roles (F10, IDEAS I43). **Not** leverage share beside snap share for playing time (R1–R4). In season, the map's role gap and trust over expected are partly the map's prior (R9) |
| **Feeds** | none yet; candidates roles-archetypes, contract-motivation, dynasty-values, vacated-opportunity |

## Open questions for the CEO
1. **What does the feature engineering keep?** *The CEO, 2026-11-14: "(a) Part + usage part" (done: decision 0034).* By your rule the project is no longer an expert; the question was what stays as production features.
   - **(a) The leverage part plus a retrospective usage part** (Claude's recommendation).
     - **What stays:** `play.leverage` as it is. A new post-season part, `player_game.leverage_usage`, built from true participation: leverage share, high-stakes share, the passing-down role gap and trust over expected per player-game. The usage function moves into the shared package, so a later live model can compute the same measures from the map.
     - **What goes:** the nine forecast variants leave the package; their scorecards stay in MLflow as the investigation's record.
     - **Why:** the contract signal (+1.7%) came from true participation, and contract work runs between seasons, where post-season data is allowed.
   - **(b) Only the leverage part.** The usage measures stay as a function in the package; nothing new is built.
   - **(c) Tempting but bad: ship the leverage-share forecast anyway**, because it passes the signal test. It beats shuffled outcomes, but it adds noise against plain snap share. Higher layers would get a noisier copy of snap share labeled "trust".
2. **Your spot-check:** one finding or call for me to walk through in depth.

## Technical calls for veto
Decision 0033's eleven calls, decision 0034's seven, plus three made in this round:
- usage sums in a fixed order (R8);
- the detached runner for long backtests;
- the five-seed check (R2) as the deciding evidence beside the harness's single seed.
