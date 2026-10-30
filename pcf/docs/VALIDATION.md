# Validation

> What "this model works" means, in numbers. [`ARCHITECTURE.md`](ARCHITECTURE.md) says *which* checks run. This page sets the bar each one must clear.
> Decided with the CEO on **2026-10-30**. Built by the `validation-harness` project. Every number here is a default: a brief may change one only with a stated reason, agreed with the CEO.

## The checklist

What every model must show before it's done. Each item links to its section.

| | Check | Bar | Applies to |
|---|---|---|---|
| 1 | [Vault](#1-seasons-development-vault-and-live) | Opened once, at the end, and reported as-is | All |
| 2 | [Walk-forward backtest](#2-the-walk-forward-backtest) | Time-ordered splits only | All |
| 3 | [Scores](#3-how-each-kind-of-prediction-is-scored) | Proper scores reported, with a readable one | All |
| 4 | [Signal](#5-expert-tests-signal-and-no-noise) | Beats ≥ 95 of 100 shuffled-outcome refits | Experts |
| 5 | [No noise](#5-expert-tests-signal-and-no-noise) | Doesn't make its named downstream baseline clearly worse | Experts |
| 6 | [Beats the baselines](#6-product-baselines) | 90% interval of the improvement above zero | Composites, products |
| 7 | [Calibration](#7-calibration-and-uncertainty) | Calibration error ≤ 3 points | Probabilities |
| 8 | [Range coverage](#7-calibration-and-uncertainty) | q10–q90 holds 75–85% overall, 70–90% per group | All ranges |
| 9 | [Leakage](#9-leakage-thresholds) | Every blocking check passes exactly | All |
| 10 | [Football sanity](#10-the-football-sanity-check) | Automatic rules pass, and the CEO reviewed the lists | All |
| 11 | [Scorecard](#11-the-validation-scorecard) | Saved in MLflow, linked from RESULTS.md | All |

**Explorations are lighter:** an exploration only asks "is there any signal at all?" It never touches the vault and doesn't need the full checklist.

## 1. Seasons: development, vault and live

Every time we check a model against test seasons and then tweak it, those seasons get a little less honest. So the most recent finished season is locked away until the end.

| Use | Seasons (as of 2026-10-30) | Rule |
|---|---|---|
| **Training** | 2006 → 2024 | Recency-weighted (below). A brief may start later when its data does (participation 2016, FTN 2022). |
| **Reported backtest** | 2016 → 2024 | The walk-forward results we compare models on |
| **The vault** | **2025** | Opened once per project, at the end (below) |
| **Live** | **2026** → | The prediction ledger. The truest test of all. |

**The vault rules:**
- A project opens the vault **once, during `validating`**, after the model is final. Never during exploring or building.
- The result is **reported whether good or bad**, in the scorecard and RESULTS.md.
- If the model changes after the vault is opened, its scorecard says **"vault spent"**, and the live ledger becomes its only honest test.
- Opening the vault is logged in MLflow (tag `vault_opened`, with the date), so it can't happen quietly.
- **It rolls forward every February,** after the Super Bowl: the season just finished becomes the vault, and the old vault joins training and the reported backtest.

**Props are the exception.** Prop history is deep only from 2024, and 2025 weeks 14–22 are missing. So for props:
- development uses 2022–2025, with 2022–23 marked sparse and the missing weeks excluded;
- **the vault is the 2026 live season**, from our own collected lines and the ledger.

**Recency weighting:** older seasons count less. The default is a half-life of 4 seasons (a season 4 years back counts half as much). A model may tune the half-life inside the training folds, and "no weighting" is always tried as a rung.

**Era changes:** the 17-game season (2021) means season totals aren't comparable, so models use per-game or per-play rates. Other rule changes (kickoffs, 2011 and 2024) are handled in the brief of any expert they touch.

## 2. The walk-forward backtest

**Splits come only from `pcf.validation`.** A test fails if any expert, composite or product imports a random splitter (e.g. scikit-learn's `KFold` or `train_test_split`).

| Cadence | One step | Trains on | Predicts |
|---|---|---|---|
| **in_season** | a week | every earlier season, plus this season's weeks so far | the next week |
| **retrospective** | a season | every earlier season | the next season |
| **offseason_events** | an event (combine, free agency, draft) | everything known before the event | that event's outcomes |

- **Refits:** a full refit each offseason, before week 1. In season, the model updates weekly with the new week's data. A brief may choose full weekly refits if the model is cheap.
- **The prediction moment** for each week defaults to the Tuesday-morning run (ARCHITECTURE.md). The gateway's `known_at` rules decide what's visible, so late-arriving sources (like PFR's advanced stats) are handled automatically.
- **An explicit gap** between training and test is added only when targets overlap in time (e.g. a rest-of-season target). The brief says so.
- **Tuning is nested.** Hyperparameters and feature selection are chosen by a second walk-forward *inside* each training window, never on the test weeks.

## 3. How each kind of prediction is scored

Use **proper scores** (they reward honest probabilities and honest ranges) to decide. Report a readable score alongside.

| Prediction | Main score (decides) | Readable score (reported) |
|---|---|---|
| Amounts: yards, points, receptions | **Pinball loss** averaged over q10, q50 and q90 | Mean absolute error of q50 |
| Yes/no events: win, TD, over/under | **Log loss** | Brier score, hit rate |
| Rankings: start/sit, ranks vs ECR | **Points gained:** each position-week, the fantasy points of our top N vs ECR's top N | Rank correlation by position-week |
| Bets | **Closing line value** ([section 8](#8-betting-evaluation)) | ROI, with a 90% interval |

**Hit rate alone is never the headline.** It ignores prices and confidence, and small samples make it mostly luck.

## 4. What "beats" means

- **Compare week by week.** Games in the same week are related, so both models are scored on the same weeks and compared as a paired difference.
- **Resample whole weeks** 2,000 times (a block bootstrap) to get a **90% interval** for the improvement.
  - Retrospective models have few seasons, so they resample by team or player instead. The brief says which.
- **A model beats another only if the whole 90% interval is above zero.**
- **Ties go to the simpler model** (rule k).
- **The scorecard shows how many versions were tried** (counted in MLflow), so 40 attempts are never presented as one.

## 5. Expert tests: signal and no noise

Experts don't have to beat other models (rule k), but they must pass both of these.

**Signal: does it find anything real?**
- Retrain the expert on **shuffled outcomes 100 times**, and score each on the same held-out weeks.
- **It has signal if the real expert beats at least 95 of the 100.**
- Outcomes are shuffled **within each week** (retrospective: within each season and position), so the structure of the data stays intact.
- Expensive models may use **20 shuffles and must beat all 20** (the same 5% bar).
- This doubles as leakage check 9: a model that scores well on shuffled outcomes is learning from something it shouldn't see.

**No noise: does it hurt what it feeds?**
- **Each brief names one downstream target and its simple baseline** (e.g. VOE into a rolling-average fantasy-points model). The CEO approves that choice in the brief.
- Score the baseline with and without the expert's output, using section 4.

| Result (90% interval of the change) | Verdict |
|---|---|
| Entirely better | **Adds value** |
| Includes zero | **Neutral:** passes. Downstream feature selection decides whether it's used. |
| Entirely worse | **Adds noise:** fails |

## 6. Product baselines

Composites and products must beat their simple baselines (rule k) by section 4. If they don't, the baseline ships.

| Product | Baselines it must beat |
|---|---|
| Weekly fantasy points | ECR (archived from Dec 2019), a 4-week rolling average, last season's per-game average, a lasso |
| Rest-of-season and dynasty | ECR and ADP where available, last season's per-game average |
| Player props | The closing line itself (it's the market's median), a lasso |
| Anytime TD | The no-vig market price, a player's season TD rate |
| Sides and totals | The no-vig closing line, Elo |
| Win probability | The no-vig closing moneyline, Elo |
| Futures | The market's implied probability |

## 7. Calibration and uncertainty

**Probabilities (yes/no events):**
- A calibration chart (do our 60% calls happen about 60% of the time?) with 10 bins, for every model.
- **Calibration error ≤ 3 points** overall (the average gap between predicted and actual rates, weighted by how many predictions fall in each bin).
- Calibration slope between 0.9 and 1.1. Outside that range is flagged as over- or under-confident.

**Ranges (amounts):**

| | Bar |
|---|---|
| q10–q90 holds the actual result | **75–85%** overall |
| Within each group | **70–90%**: position, season, rookies vs veterans, starters vs backups, favorites vs underdogs |
| q50 | The result lands above it about half the time (45–55%) |

- Groups with fewer than 200 predictions are reported but not judged.
- **Sharpness:** the average q10–q90 width is reported. Among models that pass coverage, the narrower one wins (ties go to the simpler).
- **Recalibration is allowed:** isotonic or Platt scaling for probabilities, and conformal adjustment for ranges. It's always fit inside the training folds, never on the test weeks.

## 8. Betting evaluation

**Closing line value is the main score.** It tells you much sooner than ROI whether an edge is real.
- **No-vig close:** take the two sides' closing prices and remove the bookmaker's margin proportionally.
  - Markets with one side only (anytime TD) use an assumed margin, stated in the brief.
  - ESPN prop history has no prices, so both sides are assumed −110 (DATA_SOURCES.md).
- **Which close:** FanDuel where we have it (The Odds API, from 2026-10-28), otherwise the best-available close (ESPN).
  - **Our FanDuel prop "close" is approximate.** It's our last snapshot, up to 14 hours before kickoff, and it's labeled that way.
- **In backtests:**
  - The test is whether our probabilities beat the no-vig close on log loss.
  - For main lines this is a very high bar. Matching the close is already good.
- **Live, from the ledger:** each bet's closing line value compares the price at our prediction time with the no-vig close. Positive means we beat the close.
- **Bets "at the open"** in history are reported separately and labeled. They're never the headline, because openers are soft and betting limits are low.

**ROI:**
- Flat one-unit stakes, with a 90% interval.
- **Never the headline below 500 bets.**
- Staking strategy (e.g. Kelly) is a product decision, never part of model evaluation (responsible use, VISION.md).

## 9. Leakage thresholds

The checks themselves are in [ARCHITECTURE.md](ARCHITECTURE.md#leakage-defense-in-depth). This is the bar for each.

| Check | Bar |
|---|---|
| Future perturbation, future deletion | Features **exactly identical**, not "close", at **25 cutoffs**: random dates plus week 1, mid-season, the trade deadline, the playoffs, the combine, free agency and draft day |
| Test-label perturbation | Test predictions exactly identical after scrambling the test fold's outcomes and refitting |
| Shuffled-target null | Section 5's signal test |
| Model vintage, cadence, gateway only, known_at sanity | Pass/fail, no tolerance |

**"Too good to be true"** alarms are flagged for review, not blocked:
- any single feature with a correlation above 0.9 with the outcome (or an AUC above 0.95);
- log loss more than 2% better than the no-vig close on game lines;
- a mean absolute error more than 10% better than ECR.

**Live vs backtest gap:** after at least 4 live weeks, a model is flagged if its live score falls outside its backtest's 90% interval on the worse side.

## 10. The football sanity check

Rule h, in two parts.

**Automatic rules** (`pcf/validation/sanity.py`). Shared rules apply to everything, and each expert adds its own:
- no negative yards, snaps, targets or probabilities;
- a team's players' target shares and carry shares add up to at most 100%;
- projected team points agree with the game total and spread;
- more opportunity never means fewer expected points, all else equal;
- probabilities for one event add up to 1 (e.g. win, lose, tie).

**The CEO's review, for every expert before it's done:**
- the top 20 and bottom 20 by its main output;
- the 10 biggest disagreements with the market or ECR.

Anything flagged gets either an explanation in RESULTS.md or a fix.

## 11. The validation scorecard

Every validation run produces a one-page HTML scorecard, saved in MLflow and linked from RESULTS.md:
- the vault status (closed, opened on date X, or spent) and the number of versions tried;
- main and readable scores against every baseline, with 90% intervals;
- the signal and no-noise results (experts);
- calibration charts and range coverage by group;
- the leakage checklist, every row pass or fail;
- the sanity results and the CEO review status.
