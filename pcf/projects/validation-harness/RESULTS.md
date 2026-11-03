# Results: Validation harness (`validation-harness`)

**Date:** 2026-11-02 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `validation-harness` · **Champion:** none (infrastructure; the toy expert isn't registered)

## In short
Every PCF model now has one way to be fed, tested and judged. It is written against one contract (`pcf.core.contract.Expert`) and sees the world only through the `as_of` gateway, at its prediction moment (Tuesday, Wednesday or Saturday run, CEO decision 1C). It is backtested week by week, and `pcf backtest <id>` puts it on one scorecard. Every blocking leakage check catches a planted leak and passes its honest twin, offline and on the real tables. The toy expert's full 2016–2024 validation took 7 minutes, against a 15-minute goal.

**Scorecard:** `outputs/validation-harness/b0a137569a3c48f997131d2cbe4cfdb3/scorecard.html` (also in MLflow) · **Vault:** not opened · **Versions tried:** 1

The brief's tests:

| Test | Result |
|---|---|
| Each check catches its planted leak and passes its honest twin | Pass. Checks 1–8 and 10: 26 tests on a synthetic league, plus the Monday-night leak on 2024 (`tests/validation/test_leakage.py`, `test_harness_built.py`). Check 9 (shuffled null) is tested against a model with no signal. |
| The toy's scorecard fills every VALIDATION.md §11 section | Pass, except betting evaluation and the live gap (out of scope, CEO decision 2A) |
| Its 4-game average matches a hand count | Pass: exact on 300 sampled 2024 rows, counted from kickoff + 24 hours |
| The full backtest with every check runs in under 15 minutes | Pass: 7 minutes for 403 moments, 100 shuffled refits and 25 cutoffs (F16) |

The toy expert's own scorecard (2016–2024, illustration only):

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise, beats baseline | Pass. It beat 100 of 100 shuffled refits (pinball 1.533 vs 1.88–1.91), and it beats its last-4 baseline: pinball −0.086, 90% interval −0.091 to −0.080, over 52,472 player-games. No-noise needs a downstream target, so it's not judged here. |
| Calibration and range coverage | Fail, honestly: q10–q90 holds 80.7% overall (bar 75–85%) and 49.6% land above q50, but QBs are at 69.0% (bar 70%) (F15) |
| Leakage | Pass: 9 of 9 blocking checks, and the too-good flag is clear. Checks 3 and 4 compared 14,107 rows at 25 cutoffs. |
| Football sanity (CEO review date) | Pass: 0 rows with q10 > q50 or q50 > q90. PPR points can be negative (interceptions), so no non-negative rule. The lowest predictions are backup QBs at −0.9.; CEO review pending (it's a toy) |

## Terms
As in the brief, now in `docs/GLOSSARY.md`: **prediction moment**, **view**, **cutoff**, **planted leak**, **expert contract**. One addition:
- **Fallback moment:** 10:00 ET on the first day of a week window, used when no allowed run comes before a game's kickoff (F11).

## Findings
Exploration findings F1–F10 are in [EXPLORATION.md](EXPLORATION.md). These continue from them.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F11 | **Every game since 1999 has a moment before kickoff at every run.** Weeks that start mid-week have no Tuesday run before their first games. 121 games fall back for Tuesday and 59 for Wednesday, none for Saturday: the 1999–2001 week 1s (Friday starts), 2010 week 17, 2020 weeks 6, 13 and 14, 2021 week 16. | `test_every_game_since_1999_has_a_moment_before_kickoff` | strong | all in-season models |
| F12 | **A refit must see its training rows in one fixed order.** Polars joins don't keep row order, and least squares on the same rows in a different order differs in the last digits. That was enough to fail the test-label check (8) on 4–6 rows. `walk` now sorts training rows by (`as_of`, keys). | test-label check on 2024, before and after | strong | every fit |
| F13 | **Leakage comparisons need a tolerance, 1e-9 relative.** The honest bulk features and the per-moment ones differ in the last digit, because the same numbers are summed in a different order. No real leak is that small: the planted ones move features by 1e-3 or more. The CEO agreed on 2026-11-02 (question 1), and VALIDATION.md §9 says so. | `leakage._differing`, the honest twins | strong | checks 3, 4, 8 |
| F14 | **Per-moment features are affordable.** A view from memory costs about 0.18 s. The toy's 403 moments (2006–2024, 73,173 predictions reported) take 77 s of features and 3.3 s of fitting. Most of the full validation's time is in the 100 shuffled refits and the 25 cutoffs. | the full run's log | strong | per-moment experts (decision 0011) |
| F15 | **The toy is a fair test of the scorecard, not a model to keep.** It beats its last-4 baseline, but its ranges are too narrow for QBs (69% inside q10–q90, bar 70%), so its scorecard fails range coverage. One residual spread for every position under-covers the highest scorers. | debug run on 2024; the full 2016–2024 run: pinball −0.086 (−0.091 to −0.080), QB coverage 69.0%, RB 81.4%, WR 79.8%, TE 88.1% | strong | every amount model: ranges per group |
| F16 | **The full run fits the time goal.** The toy's full validation (2016–2024, the last-4 baseline, 100 shuffled refits, all 10 checks at 25 cutoffs) took 7 minutes against a 15-minute goal: 77 s of per-moment features, 3.3 s of walk-forward fitting, about 5.5 minutes for the baseline, the shuffles and the checks. A model with costlier fits would use 20 shuffles (VALIDATION.md). | the full run's log | strong | every model |

## The ladder
None: this is infrastructure. The toy and its baseline exist only to run every path end to end.

## Pitfalls
- **"Earlier games" isn't "known".** A bulk feature built from earlier games used Monday night's stats at a Tuesday 10:00 moment (F2). The deletion check catches it, and it stays in the tests as a planted leak.
- **The post-season part on the spine.** A table whose first part is post-season-only keeps its time as `known_at`, not `<part>_known_at`. The cadence check first looked for the wrong column.
- **Non-deterministic order** (F12) can look like a leak. Sort before any fit that reads row order.
- **Week 9 isn't always there.** The synthetic league has 6 weeks; the mid-season cutoff falls back to the median regular week.

## Not looked at
- **Betting evaluation** (no-vig close, CLV) and the **live-vs-backtest gap** (check 11): they wait for an odds table and the prediction ledger (CEO decision 2A).
- **Snapshotted sources** (F8): the gateway has room for them, but no table uses one yet.
- **Recalibration helpers:** the scorecard reports miscalibration; it doesn't fix it.
- **Retrospective and offseason models end to end:** their moments, steps and cadence rule are built and tested, but no real expert of those cadences ran through the harness yet.

## Could be improved
1. **Faster views** for play-level models: a 1.8 GB play-by-play view is 0.5 s (F5), so a 19-season per-moment history is minutes, not seconds. Caching per-season frames would help.
2. **Ranges per group** in a shared helper, since the toy shows one spread under-covers QBs (F15).
3. **Parallel shuffles:** the 100 shuffled refits are independent.
4. **Cutoffs at the actual trade deadline** from the calendar, instead of week 9 as an approximation.

## Don't redo
- Don't trust a bulk "so far" feature by reading its code. Define features per moment (decision 0011), and let the harness compare.
- Don't write a splitter: `pcf.validation.splits` is the only one, and a test scans for others.
- Don't call `load` from a model. Declare inputs, and read them from the view.

## Interface card
Also in `registry.yaml`.

| | |
|---|---|
| **Inputs** | grain-tables and tag-tables parts through the gateway; the calendar (timeline); `registry.yaml`; MLflow (experiment-tracking) |
| **Outputs** | `pcf.core.contract` (`Expert`, `check_expert`, `check_output`, `find`); `pcf.data.gateway` (`Gateway`, `View`, `TableSource`, `FrameSource`); `pcf.data.timeline.moments`; `pcf.validation` (splits, backtest, scores, compare, nulls, calibration, leakage, sanity, scorecard, validate, toy). Each validation writes `outputs/<id>/<run_id>/history.parquet` (standard schema) and `scorecard.html`, and logs metrics, checks and the scorecard in MLflow. |
| **Level of detail** | any table (the model's grain) |
| **Interval** | training from 2006, reported 2016–2024, vault 2025 |
| **Cadence** | serves in_season, retrospective and offseason_events models |
| **Known at** | a view at moment t shows each part's rows with `known_at` ≤ t; post-season parts only for finished seasons in season; expert outputs with `as_of` ≤ t and `train_end` ≤ `as_of` |
| **How to use it** | Subclass `Expert`, declare `inputs` (table: parts; model: version), `run` and `quantity`, write `features(view, games)`, `target`, `fit` and `predict`, then run `pcf backtest <id>`. Never read tables directly. Add `features_history` only for speed: it must match the per-moment features. A new leakage check gets a planted leak and an honest twin in `tests/validation/planted.py`. |
| **Feeds** | every expert, composite and product; `baselines` next |

## Open questions for the CEO
1. **Answered (CEO, 2026-11-02): yes.** VALIDATION.md §9 now allows it. **May leakage comparisons allow a rounding tolerance (1e-9 relative)?** VALIDATION.md says features must be "exactly identical" with and without the future. Summing the same numbers in a different order changes the last digit (F13), so "exactly" fails honest models. Real leaks are a million times larger. Recommended: yes, and VALIDATION.md §9 says so.
2. **Nothing else blocks.** The toy's QB coverage (F15) is a finding for later models, not a decision.
