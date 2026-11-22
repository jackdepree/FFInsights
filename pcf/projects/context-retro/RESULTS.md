# Results: Context, the retrospective chain and the blame split (`context-retro`)

**Date:** 2026-11-21 · **Brief:** the last section of [`../context-v2/BRIEF.md`](../context-v2/BRIEF.md) ("The brief, after the exploration"; agreed 2026-11-21) · **Exploration:** [`../context-v2/EXPLORATION.md`](../context-v2/EXPLORATION.md) · **Build notes:** [BUILD.md](BUILD.md) · **Decision:** [0040](../../docs/decisions/0040-context-retro.md) · **MLflow experiment:** `context-retro` · **Champion:** `pcf.context-retro` version 1 (run `2eae75f5a6744689b17cba1b978cb9fa`: each outcome's shipped rungs fitted through 2025 inside the provider rule, trained through 2026-02-22; a retrospective expert has no live output)

## In short
For every dropback from 2017, the expert gives two expectations made after the season: one from what was known before the snap (**E0**: the situation and both sides' calls, coverage included) and one given the play's real pressure (**E1**). It covers six outcomes. Every E0 beats all 20 shuffled copies of itself, and the training mean, on held-out seasons, and every chance is calibrated. Given the pressure, sack's log loss falls 31% (28% to 34% in every season; the brief's bar was 25%), and to 35% on the vault. From the two it splits each sack over expected into a **pressure part** and an **after-pressure part**. Out of sample, the after-pressure part is the QB's: it repeats 0.42 from season to season, and QBs who change teams keep 99% of it; linemen keep 2%. That passes the brief's test. H88's downstream test is **unclear** by the pre-registered rule, and in substance it doesn't pay. No season prior, from either expert, helps the crude forecaster's yards: all four arms make it worse, on every board.

**Scorecard:** MLflow `context-retro`, backtest run `7ca46aa82fe344b98e6fd1e0c534260c`; reports in [`build/`](build/) (`backtest.txt`, `vault.txt`, `split.txt`, `split_vault.txt`, `qb_pairs.txt`, `h88.txt`, `misses_backtest.txt`, `sanity.txt`) · **Vault:** opened 2026-11-21 (run `86a9ba81aac0474787955692131ce177`), scoring the rungs chosen on 2017-2024 (`--fixed-from backtest`); results in R10 · **Versions tried:** 8 smoke runs on 2023-2024 (6 finished, 2 crashed; two were before the coverage fix, BUILD.md), then 1 backtest on 2017-2024, the vault, and the champion. Each run holds the ladder's 3 rungs per mode and the 20 null refits.

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise | Every E0 beats the training mean (the whole 90% interval of the paired difference by week, 8 held-out seasons) and all 20 refits on outcomes shuffled within each week, on its mean (log loss for a chance, squared error for an amount). E1 beats E0 for 5 of 5 outcomes (pressure has no E1); for depth of target only by 0.2% |
| Calibration and range coverage | Pooled over 2017-2024 every chance passes: error 0.27 to 1.05 points, slope 0.92 to 1.00. By season the level drifts where the provider changes: pressure 6.7 points off in 2018, 4.8 in 2023 (R8). Ranges: q10-q90 hold 78.3% to 84.9% overall and 70.6% to 85.6% by season (all inside 70-90%). On the vault: sack before the snap fails its slope (0.84) and dropback yards given the pressure holds 85.5% (just past 85%); the rest pass (R10) |
| Leakage | `check_point_in_time` (2024, 4 games rebuilt from views at their own `as_of`): largest gap 0.0 in every field; a view one second before participation's 2024 release has 0 rows with any participation field (45,905 at release). Every training row is known before the test season's first `as_of` (the runner refuses otherwise); 0 history rows have a `train_end` at or after their `as_of`, backtest and vault |
| Football sanity (CEO review: pending) | Lists in `build/sanity.txt` (2024). After a pressure, best: Lamar Jackson, Josh Allen, Jordan Love, Bo Nix; worst: Will Levis, Jalen Hurts, Caleb Williams. The pressure part, best: Goff, Winston, Kyler Murray, Tua (quick throwers); worst: Stroud, Wilson, Mahomes. Linemen line up by team: Jacksonville's and Detroit's lines best on the pressure part, Houston's worst (R9) |
| CEO spot-check (pending) | Candidates in "Open questions" below |

## Hunch verdicts
Copied into [`projects/HUNCHES.md`](../HUNCHES.md). H86 and H87 were held at the exploration; the build adds held-out numbers, 2017-2024, walk-forward. H88 is the CEO's to close.

| # | Hunch | Verdict | Evidence, with its size |
|---|---|---|---|
| H86 | Condition the rest of a play on its own outcomes (given a pressure, what happens next) | **held** (real: yes; pays: as the blame split, not as a forecast) | Given the real pressure, over E0: sack log loss −31.1% (every season 28.1% to 34.2%; vault 34.5%), time to throw −7.1%, dropback yards −4.9%, completion −2.3%, depth of target −0.2%. Sack's share of squared error 1.4% → 15.4%. Its use is the split (R5) |
| H87 | Play action and screens are calls; quick passing is strategy | **held** (unchanged) | Play action and screens are among E0's top fields for pressure and completion (FTN, from 2022). The quick-pass label as a call was not built (the brief kept time to throw an outcome) |
| H88 | Gains in the context expert carry downstream, almost exponentially | **unclear** by the pre-registered rule (real: a little; pays: no) | Retro's season priors against live's on the crude forecaster: better on team yards rest of season (+0.58% of live's squared error, +0.23 to +0.94), worse on passing rest of season (−0.17%, −0.33 to −0.01), level on the two next-game boards. But every arm, plain included, makes the crude forecast worse on every board (passing next −0.6% to −1.0%; team rest −5.2% to −9.2%): season priors from last season are noise to it (R7) |

**Claude's side bets on H88, scored:** retro beats live on at least 1 board (25%): **yes**. An expectation arm clears zero over crude on passing next game (30%): no. The plain arm within the interval of both expectation arms on all four boards (70%): no (live and retro are both clearly worse than plain on passing next game, and retro clearly better on team rest). Retro+ beats retro on any board (20%): no.

## Terms
Into `docs/GLOSSARY.md`: **E0** (the expectation before the snap), **E1** (given the real pressure), **pressure part** (E1 − E0 on a sack chance), **after-pressure part** (sack − E1), **the provider rule**.

## Findings
Cited as `context-retro#R<n>`. Held out over 2017-2024 (pressure and time to throw 2018-2024 train within a provider), walk-forward, refit each season.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| R1 | **Before the snap, every outcome has real signal, small for the yes-or-no ones.** Share of squared error removed against the training mean: time to throw 10.7%, depth of target 9.3%, pressure 4.1% (log loss 3.4%), completion 3.2% (2.5%), dropback yards 1.6%, sack 1.4% (3.1%). All beat 20 of 20 shuffles | `build/backtest.txt` | strong | dropbacks 2017-2024 |
| R2 | **The calls charted from 2022-2023 are most of what's forecastable for how a pass is thrown.** Depth of target: 3.9% to 6.5% in 2017-2022, 19.9% and 19.3% in 2023-2024 (FTN's screens and play action, participation's coverage on dropbacks). Time to throw: 7.4% to 8.9%, then 16.5% and 17.5%. The pressure and the sack barely change | `build/backtest.txt`, by season | strong | before and after 2022-2023 |
| R3 | **Given the real pressure, sack's log loss falls 31%, in every season.** 28.1% to 34.2% by season (the brief: 25%+ in every one); vault 34.5%. The rest, given the pressure: time to throw 7.1%, dropback yards 4.9%, completion 2.3%, depth 0.2% | `build/backtest.txt`, `vault.txt` | strong | |
| R4 | **The ladder: trees everywhere but the sack.** Sack ships logistic before the snap and given the pressure (trees level before the snap, worse given it). Dropback yards' linear rung is worse than the mean (a heavy-tailed amount); its trees beat the mean. No chance needed recalibrating | `build/backtest.txt` | strong | |
| R5 | **What happens after a pressure is the QB's, out of sample** (the brief's test, passed; F33 replicated on walk-forward chances). After-pressure part per dropback: QB repeat 0.42 (0.30 to 0.52), movers keep 99% (0.30 to 1.75; 36 movers); a lineman's repeat 0.29, kept 2% (−0.48 to 0.49). The pressure part: QB repeat 0.46, kept 39% (−0.08 to 0.97); a lineman's 0.20, kept −2%. QB sacks per pressure 0.41, kept 104% | `build/split.txt` | strong (QB after-pressure), medium (pressure part) | QBs 150+ dropbacks, linemen 300+, 2017-2024 |
| R6 | **A lineman's sack numbers are his team's.** Every lineman measure repeats 0.20 to 0.32, but linemen who move keep 0% to 26% of it. His totals follow his QB and his line-mates (in `sanity.txt` a line's five rank together) | `build/split.txt`, `sanity.txt` | strong | |
| R7 | **Season priors don't help the crude forecaster, whichever expectation they use** (H88). Over the crude forecast alone, every arm is worse on every board: passing next −0.6% (plain) to −1.0% (retro); passing rest −1.4% to −2.8%; team next −0.5% to −0.7%; team rest −5.2% (retro) to −9.2% (retro+). The better expectation matters a little at season level: retro is better than live on team rest (+0.58%), worse on passing rest (−0.17%). Adding the split's parts (retro+) is worse again on both rest-of-season boards | `build/h88.txt` | strong (no pay), weak (retro vs live) | the crude forecaster's yards boards, 2019-2024 |
| R8 | **Pressure's level moves with the provider, season by season.** Pressure's average miss is +6.7 points in 2018 and −4.7 in 2023; time to throw −0.14 s in 2023 (its first new-provider season, trained on the old one). Pooled calibration passes; by season it doesn't. Anyone comparing seasons takes each season's league level out first (as decision 0038 does) | `build/misses_backtest.txt`, calibration by season in `results.json` | strong | pressure, time to throw |
| R9 | **The split passes the football read.** 2024: Lamar Jackson and Josh Allen best after a pressure (−3.6 and −3.5 sacks per 100 dropbacks); Will Levis, Hurts and Caleb Williams worst (+3.2, +2.5, +2.4). Quick throwers have the best pressure part (Goff −0.9, Tua −0.8); Stroud the worst (+1.9) | `build/sanity.txt` | medium (one season, a read) | |
| R10 | **The vault (2025) holds the signal and its size.** Every E0 beats all 20 shuffles; shares near the backtest's last seasons (time to throw 17.7%, depth 17.4%, pressure 4.5%, completion 4.4%, dropback yards 1.6%, sack 1.3%); given the pressure, sack −34.5%. Two narrow misses: sack before the snap has a slope of 0.84 (overconfident; 2024 was 0.84 too), and dropback yards given the pressure holds 85.5% of its ranges (too wide by half a point) | `build/vault.txt` | strong | 2025 |
| R11 | **On the vault pair the QB split doesn't repeat, and neither do plain sacks.** 2024 to 2025: the after-pressure part −0.04 (31 QBs, −0.35 to 0.32). But plain sacks per dropback repeats only 0.14 that pair too, the lowest of eight (the others 0.26 to 0.65); the after-pressure part ran 0.23 to 0.61 in 2017-2023. A low-repeat pair, not a model change; one pair of 31 QBs has an interval of about ±0.35 | `build/split_vault.txt`, `qb_pairs.txt` | medium | |
| R12 | **The coverage trap: before 2023 participation leaves coverage empty on every sack.** Trees read "no coverage, so a sack" (sack before the snap worse than the average, slope −0.68, in the first smoke run). Fixed by reading coverage on dropbacks only from 2023; pass attempts are clean | BUILD.md | strong | participation 2018-2022 |

## The ladder
Per outcome and mode; a rung is kept only if it beats the one kept below it on the whole 90% interval of the paired difference by week.

| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| E0-0 | training mean (recency-weighted) | — | the base every share is read against |
| E0-1 | linear / logistic on the fields | beats the mean for 5 of 6 (not dropback yards) | the calls carry it; sack ships here |
| E0-2 | trees (context-live's settings) | beats linear for pressure, time to throw, depth, completion; beats the mean for dropback yards; level for sack | trees for the amounts and most chances |
| E1-0 | the pressure alone | — | most of the given-pressure gain for the sack |
| E1-1 | linear on the fields plus the pressure | beats E1-0 for all 5 except dropback yards | sack ships here |
| E1-2 | trees on the fields plus the pressure | beats E1-1 for 4 of 5 (worse for sack) | |

## Where it misses
Play-level lenses (context-live's list, plus the pressure and the top tenth); `build/misses_backtest.txt`. The player-game lens list (miss-lenses D1) isn't for play outputs.

| Lens | Group | Rows | Average miss (actual − expected) | 90% interval | Idea |
|---|---|---|---|---|---|
| season | pressure, 2018 | 19,727 | +6.7 points | clear of zero | R8: the provider's level |
| season | pressure, 2023 | 21,740 | −4.7 points | clear of zero | R8 |
| screen | depth of target, screens 2022-2024 | 5,858 | −3.45 yards | clear | I97: 2022's models never saw the flag (−10.2 yards in 2022, −0.4 in 2023-2024) |
| screen | time to throw, screens | 5,848 | −0.34 s | clear | I97 |
| top tenth | sack given the pressure, top tenth | 16,312 | −1.4 points | clear | the highest chances are a little high (the vault's slope) |

## The case against
- **The given-pressure gain is not a forecast, and was never meant to be.** E1 knows something from after the snap. Its 31% says the pressure explains sacks, which a coach would tell you for free. What's new is the split, and the split rests on E1 being right for each QB's situation. If E1 is biased for QBs who hold the ball (the expectation doesn't know who the passer is), the after-pressure part credits or blames them for it. That is the claim, but it is also the risk.
- **The QB's after-pressure trait rests on about 30 QBs a season pair.** Pooled, 199 pairs and 36 movers; the share kept's interval is 0.30 to 1.75. On the vault pair it didn't repeat at all (R11). The plain sack rate failed the same way that year, which points at the year, but a reader should know the trait's evidence is eight pairs of about 30.
- **Pressure is participation's charting, and it changes.** Two providers, a level that moves 5-7 points by season (R8), and a flag empty on sacks before 2023 (fixed by counting a sack as a pressure). The split inherits all of that. Any provider change after 2025 needs a fresh look before the split is trusted.
- **H88's "unclear" is generous.** Every arm hurts the crude forecaster, so "retro beats live on one board" means "retro hurts less on one board". A stricter reading is "failed: season priors from either expert don't pay". The pre-registered rule says unclear, so that is the verdict, but the CEO should read it as no pay.
- **The vault's two misses are small but real:** sack's slope 0.84 (and 2024's was 0.84 too) says sack chances before the snap are too spread out in recent seasons. A user reading sack E0 above about 12% should shrink it.

## Pitfalls
- **Empty on sacks.** Participation's old provider leaves the pressure flag and coverage empty on every sack before 2023. Anything keyed on "missing" learns the sack. Check missingness by outcome before using any participation field.
- **A field that starts mid-history.** FTN's screen and play-action flags start in 2022; the 2022 test season's models were trained without them and miss screens' depth by 10 yards. A field must exist in the training seasons, not just the test one.
- **A plain YAML colon broke the full test suite** (the registry's summary). Quote summaries.
- **Two builds claimed the same numbers** (decision 0041, ideas I100+) in the shared notes; they crossed and were swapped to match the other build's note. Read the sibling notes again just before writing numbers.

## Not looked at
- Rushing plays (context-live has them); routes (participation's route is the target's only, context-v2's first look).
- Splitting the other outcomes (completion given the pressure, the QB's yards after a pressure). Only the sack was split, as the brief asked.
- Defensive players' parts (the pass rushers who made the pressure): idea I98.
- A per-season level adjustment for pressure inside the model (R8): left as a reading rule.

## Could be improved
1. **Train the calls' fields only on seasons that have them** (I97): depth of target and time to throw on 2022+ for FTN's flags, so the first season with a flag isn't blind to it.
2. **The pass rusher's side of the split** (I98): the pressure part per defender, for skill-over-expected's pass rushers.
3. **Recalibrate sack before the snap on recent seasons** (its slope 0.84 in 2024 and 2025).
4. **Use the split's QB after-pressure part as a QB trait downstream** (for qb-talent and line-play), not as a yards prior (R7). Idea I99: it forecasts next season's sacks per dropback better than the plain rate.

## Don't redo
- Season priors of over-expected rates on the crude forecaster's yards boards: no arm pays, whichever expectation (R7).
- Coverage on dropbacks before 2023 (R12).
- Trees for sack chances (R4).

## Interface card
Also copied into this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | play.pbp, play.ftn, play.participation (retrospective view, from 2016; outcomes pressure and time to throw, and the call fields rushers, box, coverage) |
| **Outputs** | `outputs/context-retro/<run_id>/history.parquet`: the standard schema keyed game_id, play_id; quantities `pressure_e0`, `time_to_throw_e0/_e1`, `sack_e0/_e1`, `air_yards_e0/_e1`, `completion_e0/_e1`, `dropback_yards_e0/_e1`, and `sack_pressure_part`, `sack_after_part`; mean the chance or expected value, q10-q90 its range (equal to the chance for a chance); model_version the shipped rung. Beside it `player_game.parquet`: per passer and lineman per game, dropbacks, pressures, sacks, over_e0, after_part, pressure_part |
| **Level of detail** | play (dropbacks; depth and completion on attempts); player-game for the split |
| **Interval** | every dropback, 2017-2024 walk-forward (backtest run 7ca46aa8), 2025 from the vault run 86a9ba81 |
| **Cadence** | retrospective |
| **Known at** | the day after the Super Bowl (participation's release), for the whole season |
| **How to use it** | A completed season's QB after-pressure part as a trait (it is the QB's: R5); a lineman's parts are his team's (R6), so don't credit a lineman with them. Never an input to an in-season forecast except as last season's prior (rule m), and as a yards prior it doesn't pay (R7). Take each season's league level out before comparing pressure across seasons (R8) |
| **Feeds** | skill-over-expected (QB sacks), qb-talent, line-play; context-live stays the in-season expert |

## Open questions for the CEO
1. **H88: unclear by the rule, no pay in substance.** Close it as unclear, or as failed (the stricter reading)? It's your hunch to close.
2. **The football sanity lists** (`build/sanity.txt`, 2024): do Lamar Jackson and Josh Allen as the best after a pressure, and Levis, Hurts and Caleb Williams as the worst, match what you saw?
3. **The spot-check:** which one should I walk through? Candidates:
   - the vault pair's failed repeat (R11);
   - the coverage trap and its fix (R12);
   - why every season prior hurts the crude forecaster (R7);
   - the split's arithmetic on a few real sacks.
