# Results: Miss lenses (`miss-lenses`)

**Date:** 2026-11-03 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** none (a tool, not a model) · **Champion:** none

## In short
Every player-game scorecard now has a **"Where it misses"** section: seven fixed lenses (list of 2026-11-03) plus at most five tags that stand out, each report stamped with when it was measured, which lens list and which scoring it used. `pcf misses <id> --variant <v>` does the same for any saved run. On all four box-score baselines and ECR, the same story holds: **the misses come from playing time, team scoring and QB efficiency, which are known only after the game, not from any pre-game tag** (F1, F2, F10). That points the next expert at `participation` or team scoring.

**Scorecard:** n/a · **Vault:** not opened · **Versions tried:** n/a

| Check | Result |
|---|---|
| The report runs on any player-game history in under a minute | Pass: 4 s for the lasso (52,472 rows), 1 s for ECR |
| It reproduces the exploration on the lasso and ECR | Pass: every share and top group matches F1–F3 |
| A planted lens is found; noise in many small groups is not | Pass (`tests/validation/test_misses.py`) |
| After-game lenses are labelled everywhere | Pass: "after" in the table and the report; tags follow their football timing |
| Every report is dated | Pass: `measured_at`, `lens_list`, `method`, `run_id` on every row of misses.parquet |
| CEO spot-check (date): what was checked | pending |

## Terms
As in the brief, now in `docs/GLOSSARY.md`: **miss**, **bias share**, **spread share**, **diagnostic lens**. **Lens list** and **scoring method** are named by the date they were agreed (D7).

## Findings
Exploration findings F1–F7 are in [EXPLORATION.md](EXPLORATION.md). These continue from them.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F8 | **The lens report is cheap:** 4 seconds on 52,472 player-games, so it runs on every scorecard and on any saved run. | `pcf misses` on the baselines | strong | player-game models |
| F9 | **Scanning 20 tags at a 90% bar flags about 2 by chance, so a tag must clear 99% to be shown.** At that bar no tag stands out for ECR. For every box-score baseline, **players active while questionable score 1.1 to 1.4 points below projection**, and the averages under-project rookies (+0.4 to +0.6). Those became ideas I4 and I5. | misses.parquet of the four baselines | strong | box-score models |
| F10 | **The same lenses lead for every baseline.** Snap share explains 2.9–7.9% of the squared miss, team points 4.7–6.6%, QB efficiency 7.6–10.8% of QBs'. Depth explains 4.5–5.6% of the miss size. Pre-game lenses stay under 0.5% for all five models. | the rolling, season, lasso and ECR reports | strong | weekly fantasy points |

## Where it misses
Not applicable: this project is the tool. Its first reports are in F9–F10, and in each baseline's `misses.html`.

## The case against
- **The after-game lenses explain misses partly by construction.** Fantasy points are made of playing time and team scoring, so of course those explain misses. What they show is *which part* of the outcome nobody predicts well, not that a feature exists that would fix it. The test for that is the next expert, through the harness.
- **Two model families, one quantity.** The list was chosen on averages, a lasso and ECR, all PPR. A tree or simulator may miss elsewhere; D5 (review on each important new model) is the guard.
- **Small shares are noisy.** Differences below about half a point of share (0.5%) between lenses shouldn't be read as a ranking.
- **The top group's 90% interval doesn't allow for picking the largest of several groups,** so it's a little optimistic. The flagged tags use 99% for that reason.

## Pitfalls
- **A tag's "false" group is everyone else,** so its average miss is just the model's overall bias. Tags are judged on the rows they fire on, against the model's average at the same positions.
- **Season and position can't be cross-fitted** (each half of the seasons sees different seasons; every lens is measured within position). They're shown as groups with shares of 0.

## Not looked at
- **Game-level models** (sides, totals): their lens list comes with the first one.
- **Ranges by lens.** Coverage by group is already on the scorecard; it isn't split by these lenses.
- **Lenses for half-PPR and standard scoring.** The lens frame works for them; no model has been run.

## Could be improved
1. **A pre-game expectation for each after-game lens** (expected snap share, expected team points) to measure how much of each miss a feature could fix. That's the next experts' job.
2. **Lens reports in MLflow** as metrics, so they can be compared across runs in the browser view.

## Don't redo
- Don't scan all 52 tags on every model: the fixed list plus the 99% flag is enough (F1, F9).
- Don't read an after-game lens as a feature (D4).

## Interface card
Also in `registry.yaml`.

| | |
|---|---|
| **Inputs** | A player-game walk-forward history (`mean`) with its outcomes; through the source: `player_game` roster, depth, snaps, tags and tags_result; `team_game` tags and tags_result; `game` schedule and result |
| **Outputs** | `pcf.validation.misses`: `report`, `lens_frame`, `from_history`, `save`, `Misses`, `LENSES`, `LENS_LIST`, `METHOD`. `misses.parquet` (and `misses.html` from `pcf misses`) next to each run's history; the scorecard's "Where it misses" section |
| **Level of detail** | player-game |
| **Interval** | whatever the model's history covers |
| **Cadence** | n/a (runs with every validation) |
| **Known at** | n/a: diagnosis after the fact; lenses never feed a model |
| **How to use it** | Read the section on the scorecard and copy it into RESULTS.md's "Where it misses". Each pattern worth chasing becomes a line in IDEAS.md. For a saved run: `pcf misses <id> --variant <v>`. To change the list, add a new dated list (D5, D7), never edit the old one |
| **Feeds** | every player-game RESULTS.md; IDEAS.md |

## Open questions for the CEO
None. D5 (review each season and on each important new model) and D7 (everything dated) are your calls, already recorded.
