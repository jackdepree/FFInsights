# Brief: Validation harness (`validation-harness`)

> An infrastructure project: the machinery behind [`docs/VALIDATION.md`](../../docs/VALIDATION.md) and the leakage checks in [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md). The bars themselves were agreed on 2026-10-30. This brief only decides how they're built. **Two calls for the CEO (end of page).** Light exploration: [EXPLORATION.md](EXPLORATION.md).

**Status:** draft · **Layer:** 0, foundation (Phase 0) · **Cadence:** — (used by every model's cadence)

## The question
Build the one way every PCF model is fed, tested and judged. A model sees the world only as it was at its prediction moment, is backtested week by week, and passes or fails the same leakage, signal, calibration and "beats" tests. The result lands on one scorecard.

## Why it matters
- **It unblocks about 15 projects.** Every first expert (Elo, team efficiency, pace, environment, stabilization, Context, participation), plus baselines and season tables, depends on it.
- **Leaks are subtle** (F2): a feature that honestly says "earlier games" still used Monday night's stats at a Tuesday-morning moment. Only a check against the gateway catches that, and it has to exist before the first model, not after.
- **Same tests, comparable results.** Without one harness, each expert would score, split and bootstrap its own way, and "beats" would mean something different every time.

## Terms
- **Standard terms used:** known_at, as_of, gateway, leakage, walk-forward history, train_end and the vintage rule, vault, shuffled null, no-noise test, scorecard, week window, cadence (`docs/GLOSSARY.md`).
- **New terms:**
  - **Prediction moment:** the exact time a prediction is made, e.g. 10:00 ET on the first day of week 10's window. The gateway shows the model only what was known by then. See question 1.
  - **View:** what the gateway returns for one moment: the tables and expert outputs a model declared, filtered to what was known then. It knows its moment and cadence.
  - **Cutoff:** a moment at which a leakage check compares a model's features with and without the data that came after it.
  - **Planted leak:** a deliberately leaky toy model kept in the tests. Every blocking check must catch its planted leak and pass the honest twin, so a check that silently stops working fails the build.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `grain-tables` | `load(name, at)`, the parts and their `known_at` | The gateway wraps it (F9) |
| `timeline` | Week windows, phases, `phase_at` | Prediction moments and the 25 cutoffs (combine, free agency, draft day, trade deadline) |
| `experiment-tracking` | `attempt`, `rung`, `log_checks`, `register`, `versions_tried`, `mark_vault_opened` | Check results gate registration; the scorecard counts attempts |
| `tag-tables` | Football timing, the "so far" rule (tag-tables#F8, #F10) | The same before/after logic, now for features |
| `cleaning-port#F8`, `#F12` | Two real leaks from `old/` | Become planted leaks in the tests |
| exploration F1–F10 | Part timing, view cost, the Monday-night leak, the closing-line timing | The design below |

**Already tried:** `old/` validated each notebook its own way, with random splits in places and "so far" features that included the current play (cleaning-port#F8). Nothing was shared or checked.

## Assumptions (technical calls, Claude's; say if you disagree)
- **The expert contract comes first** (`core/contract.py`, F10). It has `id`, `cadence`, `grain`, `inputs` (tables with their parts, and expert outputs), `features(view)`, `fit`, `predict`, `explain`, and the standard output schema (`mean`, `q10`, `q50`, `q90`, `train_end`, …). A test checks that `inputs` matches `depends_on` in the registry.
- **The gateway** (`data/gateway.py`) wraps `load` and returns a view. It refuses undeclared inputs, enforces the cadence rule (in-season sees post-season-only data only from finished seasons), reads expert outputs only where `train_end` < the moment (check 6), and leaves room for snapshots (F8: no user yet).
- **Features are defined per moment; bulk is an optional speed-up.** `features(view)` at one moment is the definition. An expert may also offer a faster bulk version for its whole history, accepted only if it matches the per-moment version exactly at 25 cutoffs. Views are cheap enough (0.5–2 s each, F5) that per-moment is the safe default.
  - *Rejected:* bulk "so far" features trusted by reading the code. The exploration's honest-looking feature leaked (F2).
- **Splits come only from `pcf.validation.splits`:** walk-forward by week (in-season), season (retrospective) or event (offseason). Tuning is nested inside each training window. A test fails any expert, composite or product that imports a random splitter.
- **The blocking leakage checks 1–9 each get a planted leak** that they must catch, plus an honest twin they must pass. `tracking.log_checks` records the results, so `register` refuses a model that failed.
- **The scores and comparisons follow VALIDATION.md exactly:** pinball, log loss, Brier, MAE, points gained, the week-block bootstrap (2,000 draws, 90% interval), shuffled null (100, or 20 for expensive models), no-noise verdicts, calibration error and slope, range coverage by group, sharpness, and the "too good to be true" flags.
- **The scorecard** is one HTML page per validation run, saved in MLflow.
- **A toy expert proves the whole path end to end:** a 4-week rolling average of PPR points, run through the gateway, backtested 2016–2024, scored and put on a scorecard. It isn't the `baselines` project, just the harness's own test.

## Goals
1. Any expert can be written against one contract and gets the gateway, backtest, checks and scorecard for free.
2. Every blocking check catches its planted leak and passes the honest twin, in the test suite (offline on synthetic data, and on the local data).
3. A full in-season backtest of a simple model over 2016–2024 (193 steps) with every check runs in under 15 minutes on the PC.

## Tests
- **Success looks like:**
  - each of checks 1–9 fails its planted leak and passes its honest twin;
  - the toy expert's scorecard has every section of VALIDATION.md §11 filled;
  - its 4-week average of PPR points stays within a few percent of a hand-computed one;
  - the backtest runs within the time goal.
- **Failure looks like:** a check that can't tell a planted leak from its twin, or a backtest too slow to run on every model (then: cache views, sample cutoffs, say so).
- **Seasons:** as in VALIDATION.md §1 (training 2006→, reported 2016–2024, vault 2025). The harness enforces the vault: opening it requires an explicit call that's logged in MLflow.

## Inputs and outputs
- **Inputs:** the built tables (`load`), the calendar, the registry, MLflow.
- **Outputs:**
  - `pcf.core.contract`;
  - `pcf.data.gateway`;
  - `pcf.validation`: `splits`, `scores`, `compare` (bootstrap and "beats"), `nulls` (signal and no-noise), `calibration`, `leakage`, `sanity`, `scorecard`, and `backtest`, which runs an expert's walk-forward and writes its history to `outputs/<id>/<version>/`;
  - `pcf backtest <id>`.

## How it will be used
Every expert, composite and product from here on is written against the contract and validated with `pcf backtest <id>`. `baselines` is next: its rolling averages, Vegas lines and lasso go through this harness first.

## Plan
1. The contract and the gateway.
2. Splits and the backtest runner, with the toy expert.
3. Leakage checks 1–9, each with its planted leak.
4. Scores, comparisons, nulls, calibration and sanity.
5. The scorecard and `pcf backtest`.

There's no model ladder: this is infrastructure. Time box: about two working sessions.

**Not in this project:**
- **Betting evaluation** (no-vig close, CLV): our odds aren't a table yet. It comes with `baselines` or `market`.
- **The live-vs-backtest gap** (check 11): it needs the prediction ledger.

---

## Questions for the CEO

### 1. When does a prediction happen?
**Why it matters:** the moment decides what every model may use. The exploration found the planned Tuesday-morning moment can't see last Monday night's stats (F2): they count as known 24 hours after kickoff. It can't see the week's closing spreads and totals either: nflverse's lines are the close, known at kickoff (F3).

| | Option | Good | Cost |
|---|---|---|---|
| **A** | **Tuesday 10:00 ET only** (as planned) | Earliest projections, in time for waivers | The 2 teams from Monday night are a game behind in every feature. No closing lines. |
| **B** | **Wednesday 10:00 ET only** | Last week is complete for everyone | A day later, after many waivers have run |
| **C (recommended)** | **The three weekly runs as named moments**: Tuesday, Wednesday and Saturday, each at its run time. Each model declares which it's backtested at. Experts default to Tuesday, and products choose (waivers: Tuesday; Sunday start/sit and props: Saturday). A game is always predicted at the latest run before its kickoff, so Thursday games never get Saturday's run. | Backtests match exactly how each product will be used live. No change to any known-at rule. | A little more harness code. Closing lines still come only from our collected odds, not from nflverse. |
| ✗ | **Tuesday, but count Monday night as known** (loosen the 24-hour rule) | The backtest looks slightly better | Unproven: if nflverse publishes late, live is worse than the backtest and nobody notices until the ledger shows it. |

### 2. How much goes into this project?
**Why it matters:** the harness is the biggest Phase 0 piece left. Building too little means each expert patches gaps its own way. Building too much delays the first expert.

| | Option | Good | Cost |
|---|---|---|---|
| **A (recommended)** | **Everything a model needs to be "done"**: contract, gateway, splits, backtest, scores, beats, signal and no-noise, calibration and coverage, leakage checks 1–9 with flags, sanity rules, scorecard. Betting evaluation and the live-vs-backtest gap wait for odds tables and the ledger. | The first expert can finish properly. The pieces still to come need data we don't have yet. | About two sessions |
| **B** | **All of VALIDATION.md,** betting evaluation included | Nothing left for later | Needs an odds table first: a detour into odds-collection before any expert |
| **C** | **The minimum:** gateway, splits and leakage checks; scores, calibration and the scorecard later | The first expert starts sooner | The first expert can't be "done", and the missing pieces get built in a hurry inside it |
| ✗ | **Build the harness inside the first expert (Elo)** | Fast start | The harness ends up shaped like Elo, and every later expert works around it |
