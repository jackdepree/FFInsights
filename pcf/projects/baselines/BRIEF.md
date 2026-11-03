# Brief: Baselines (`baselines`)

> The yardsticks every product must beat (rule k, VALIDATION.md §6). Exploration: [EXPLORATION.md](EXPLORATION.md). **Key decisions D1–D9 are at the end of this page, each to approve or deny.**

**Status:** agreed (2026-11-02): CEO approved D1–D9 as written · **Layer:** 0, foundation (Phase 0) · **Cadence:** in_season (the weekly-points baselines); the market benchmark is at kickoff

## The question
What does "good enough to ship" mean for a PCF projection? Build the simple and market yardsticks each product must beat, so that "beats ECR" or "beats a 4-week average" means the same thing every time, on the same games.

## Why it matters
- **The charter's success test is "at least as accurate as ECR"** for projections, and "positive CLV" for bets. Neither is measurable until ECR and the closing line are in the harness.
- **Rule k:** a product that doesn't beat its simple baselines doesn't ship; the baseline does. Without them, no product can be judged.
- **They're the first real models through the harness**, ahead of the first experts.

## Terms
- **Standard terms used:** baseline, ECR, closing line, no-vig, rolling average, lasso, walk-forward history, prediction moment, pinball loss ([`GLOSSARY.md`](../../docs/GLOSSARY.md)).
- **New terms:**
  - **Benchmark:** a baseline that comes from outside PCF (ECR, the closing line). It's scored like a model but never used as a feature before it's known.
  - **Rank-to-points curve:** the average points scored at each ECR rank in a position, fit on training weeks, which turns a ranking into a projection (F7).
  - **Kickoff moment:** a prediction moment at each game's kickoff, allowed only for benchmarks (D5).

## Builds on
| Project | What we use | Why |
|---|---|---|
| `validation-harness` | The contract, the gateway, `pcf backtest`, "beats" | Every baseline runs through it. The toy's `RecentPoints` and `LastFour` become real baselines. |
| `validation-harness#F15` | One spread for every position under-covers QBs | Baseline ranges are per position (D7) |
| `validation-harness#F3`, `odds-collection#F3` | nflverse lines are the close, known at kickoff | The market benchmark runs at kickoff (D5) |
| `grain-tables` | `player_game` stats, `game` pregame lines | The inputs |
| `data-layer` | The ECR archive (`ecr_archive`), already downloaded | ECR (D3) |
| Exploration F1–F8 | ECR timing and skill, closing-line accuracy | The design below |

**Already tried:** in `old/`, projections were never compared with ECR or the market on the same games. The toy expert shows the harness path works (validation-harness#F15).

## Assumptions
- **The archive's ECR is what FantasyPros showed that Friday.** It's a consensus of experts, scraped once a week (F1).
- **nflverse lines are the close**, close enough to stand in for the market until our own odds are a table (odds-collection#F3).
- **PPR points are the main quantity.** The averages work for any scoring format. ECR exists only for PPR (and for QBs, where formats don't matter).

## Goals
1. Weekly fantasy-points baselines that any product can name in one line (`baselines()`), on its own moments and rows.
2. ECR as a scored projection (points and ranges), honest about timing.
3. A market benchmark for sides, totals and win probability, at kickoff.
4. Each baseline's own scorecard from `pcf backtest`, with every leakage check passing.

## Tests
- **Success looks like:**
  - every baseline passes all blocking leakage checks;
  - ECR never ranks a game that kicked off before its snapshot was known (a test plants a Thursday game);
  - walk-forward, ECR-as-points beats the 4-game average at QB, WR and TE (F4 says it should);
  - the averages' q10–q90 holds 75–85% overall and 70–90% for every position (D7);
  - the market's win probabilities are calibrated within 3 points (the close should be, so this also checks our scoring code).
- **Failure looks like:** ECR-as-points losing to the 4-game average everywhere. That would mean the curve is wrong, not ECR.
- **Baselines:** this project *is* them. Signal tests don't apply to benchmarks; the averages and the lasso still get them.
- **Seasons:** training from 2006 (averages, lasso, market); ECR from 2021, so its comparisons cover 2022–2024 after a training season (F1). The vault stays shut.

## Inputs and outputs
- **Inputs:** `player_game` stats (known 24 h after kickoff), a new `player_game` part for ECR (known at the start of the day after the Friday scrape), `game` pregame lines (known at kickoff).
- **Outputs:** for each baseline, a walk-forward history in the standard schema (`mean`, `q10`, `q50`, `q90`, or a probability), and a scorecard.

## How it will be used
Every product's brief names its baselines from this project, and its scorecard shows "beats" against each one. The weekly fantasy product must beat ECR to ship. Betting products must match or beat the market benchmark.

## Plan
1. The ECR table part, with its timing test.
2. The averages and the lasso, for any fantasy scoring.
3. ECR as points.
4. The kickoff moment and the market benchmark.
5. Scorecards for all of them, RESULTS.md.

There's no ladder: baselines are rung 0 for everything else. Time box: about two sessions.

---

## Key decisions (approve or deny each)

Each one: what I decided, why, and the main alternative. Football and product calls are marked **(yours)**; the rest are technical calls I'd make unless you object.

**D1. Scope (yours): weekly fantasy points and game lines now; props, TD, rest-of-season and futures later.**
- Now: ECR, the 4-game average, the season-so-far average, last season's average and a lasso, for weekly fantasy points; the no-vig closing line for sides, totals and win probability.
- Later, with their products: props and anytime TD (they need our collected odds as a table), rest-of-season and dynasty (ECR's other pages and ADP), futures. Elo stays its own expert.
- *Alternative:* all of VALIDATION.md §6 now. Every baseline would be ready at once, but it adds an odds-table detour for products that are a year away.

**D2. The quantity (yours): fantasy points in a named scoring, PPR by default.** The averages and the lasso take the scoring as a setting (PPR, half-PPR, standard). ECR is compared in PPR only.
- *Alternative:* project stat lines (yards, catches, TDs) and score any format from them. It's more flexible, but that's product work, not a yardstick's.

**D3. ECR becomes a table part (technical).** It's a new `player_game` part, `ecr` (rank, expert spread, snapshot time), from 2021. Its known-at is the start of the day after the scrape, and it holds only games that kick off after that time. So the gateway, not each model, keeps Thursday games out (F2).
- *Alternative:* the ECR baseline reads the archive itself. It's faster to write, but it breaks "models read only through the gateway" (rule c).

**D4. Where ECR is judged (yours): the Saturday run, Sunday and Monday games, weeks 2–17, 2022–2024.** That's where an honest weekly ranking exists (F1, F2). A product beats ECR when it wins on those rows, paired.
- *Alternative:* fall back to the previous week's ECR for Thursday games. It covers every game, but it scores FantasyPros on stale rankings and flatters us.

**D5. The market benchmark runs at kickoff (technical).** I'd add a `kickoff` moment to the prediction moments that only benchmarks may declare. The gateway already hides a kickoff-time output from any model running earlier, so a closing line can never leak into a Saturday feature.
- *Alternative:* score products against the raw lines in the scorecard code, outside the harness. That's simpler, but the market would get no history, no calibration check and no ranges.

**D6. The lasso uses box-score history only (technical, flag if you disagree).** Its features: recent and season averages of points and their parts (targets, carries, yards, TDs), games played, position. No ECR and no market lines: those are benchmarks of their own, and the lines aren't known at the runs. Its penalty is tuned inside each training window.
- *Alternative:* add ECR as a feature. The lasso would get stronger, but then "beats the lasso" partly means "beats ECR" again.

**D7. Ranges are per position (technical).** q10, q50 and q90 come from training residuals per position, which fixes the toy's QB problem (validation-harness#F15). ECR's ranges are per position and rank band.

**D8. Code shape (technical).** The baselines go in a new `pcf.baselines` package: one class per baseline, written once and set to a quantity (e.g. `RollingAverage(points="ppr", games=4)`). They're registered as variants of the one project id `baselines`, and their histories are saved as `outputs/baselines/<variant>/`. A product declares them in `baselines()`, and the harness reruns them on the product's moments and rows.
- *Alternative:* one registry entry per baseline (`baseline-ecr`, `baseline-rolling`, …). That's five projects' worth of paperwork for code that's 50 lines each.

**D9. Rejected, so you can see the line (✗):** fit ECR's rank-to-points curve on all seasons at once. It would look better, but the curve would know the future.
