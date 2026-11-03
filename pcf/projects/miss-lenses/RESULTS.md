# Results: Miss lenses (`miss-lenses`)

**Date:** 2026-11-03 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** none (a tool, not a model) · **Champion:** none

## In short
Every player-game scorecard now has a **"Where it misses"** section: seven fixed lenses (list of 2026-11-03) plus at most five tags that stand out, each report stamped with when it was measured, which lens list and which scoring it used. `pcf misses <id> --variant <v>` does the same for any saved run. On all four box-score baselines and ECR, the same story holds for the share of error explained: **the misses come from playing time, team scoring and QB efficiency, which are known only after the game, not from any pre-game tag** (F1, F2, F10). That points the next expert at `participation` or team scoring. The CEO's spot-check found more underneath: real but small pre-game biases, effects that grow with the projection, and two candidate blind spots in ECR (F11–F13).

**Scorecard:** n/a · **Vault:** not opened · **Versions tried:** n/a

| Check | Result |
|---|---|
| The report runs on any player-game history in under a minute | Pass: 4 s for the lasso (52,472 rows), 1 s for ECR |
| It reproduces the exploration on the lasso and ECR | Pass: every share and top group matches F1–F3 |
| A planted lens is found; noise in many small groups is not | Pass (`tests/validation/test_misses.py`) |
| After-game lenses are labelled everywhere | Pass: "after" in the table and the report; tags follow their football timing |
| Every report is dated | Pass: `measured_at`, `lens_list`, `method`, `run_id` on every row of misses.parquet |
| CEO spot-check (2026-11-03): what the report measures, why ECR shows few pre-game flags, and whether pairs of conditions miss differently | Done: F11–F13. Home and a teammate Out are now scanned with the tags; pairs are a discovery check for each review, not on every scorecard |

## Terms
As in the brief, now in `docs/GLOSSARY.md`: **miss**, **bias share**, **spread share**, **diagnostic lens**. **Lens list** and **scoring method** are named by the date they were agreed (D7).

## Findings
Exploration findings F1–F7 are in [EXPLORATION.md](EXPLORATION.md). These continue from them.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F8 | **The lens report is cheap:** 4 seconds on 52,472 player-games, so it runs on every scorecard and on any saved run. | `pcf misses` on the baselines | strong | player-game models |
| F9 | **Scanning 20 tags at a 90% bar flags about 2 by chance, so a tag must clear 99% to be shown.** At that bar no tag stands out for ECR. For every box-score baseline, **players active while questionable score 1.1 to 1.4 points below projection**, and the averages under-project rookies (+0.4 to +0.6). Those became ideas I4 and I5. | misses.parquet of the four baselines | strong | box-score models |
| F11 | **A small share can still be a real bias.** Single pre-game conditions are clearly off for the lasso (starters +0.42, a same-position teammate Out +0.68, new team −0.42, questionable −1.10, home +0.20, big favorite +0.52 points), yet each removes under 0.5% of the squared miss, because one player-game's miss is about ±5.5 points. The share says how much of the error a lens fixes; the interval says whether it's real. | `explore/interactions.py` | strong | every model |
| F12 | **Pairs of conditions miss differently from the sum of their parts, mostly by projection size.** For the lasso, 10 of 131 pairs clear a Bonferroni bar and replicate in even and odd seasons: starters with a backup QB −0.98 beyond the two alone, top-third players who are big favorites +0.95, questionable top-third players −1.17, rookies in the top third −0.69. Effects grow with the projection: they multiply rather than add. For ECR one of 80 survives: **top-third players active while questionable score 0.84 below ECR** (240 player-games; −2.04 extra in 2022 and 2024, −0.91 in 2023). | `explore/interactions.py` | medium (week clustering ignored; the replication check guards) | weekly fantasy points |
| F13 | **ECR has a pre-game blind spot: home players score 0.28 points above it** (6,559 player-games, 99% interval +0.03 to +0.54), found once home was scanned with the tags. Primetime (−0.31) and a teammate Out (+0.28) point the same way below the 99% bar. | the ECR report | medium (3 seasons) | ECR, Sunday and Monday games |
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
- **Home isn't a tag,** so the first version never scanned it. Conditions that matter but aren't tags go in `misses.EXTRA` (home, a teammate Out).
- **Season and position can't be cross-fitted** (each half of the seasons sees different seasons; every lens is measured within position). They're shown as groups with shares of 0.

## Not looked at
- **Game-level models** (sides, totals): their lens list comes with the first one.
- **Ranges by lens.** Coverage by group is already on the scorecard; it isn't split by these lenses.
- **Lenses for half-PPR and standard scoring.** The lens frame works for them; no model has been run.

## Could be improved
1. **The pair scan (`explore/interactions.py`) as part of each review (D5),** not on every scorecard: 130 pairs per run would flag noise.
2. **A pre-game expectation for each after-game lens** (expected snap share, expected team points) to measure how much of each miss a feature could fix. That's the next experts' job.
3. **Lens reports in MLflow** as metrics, so they can be compared across runs in the browser view.

## Don't redo
- Don't scan all 52 tags on every model: the fixed list plus the 99% flag is enough (F1, F9).
- Don't read an after-game lens as a feature (D4).

## Interface card
Also in `registry.yaml`.

| | |
|---|---|
| **Inputs** | A player-game walk-forward history (`mean`) with its outcomes; through the source: `player_game` roster, depth, snaps, tags and tags_result; `team_game` tags and tags_result; `game` schedule and result |
| **Outputs** | `pcf.validation.misses`: `report`, `lens_frame`, `from_history`, `save`, `Misses`, `LENSES`, `EXTRA`, `LENS_LIST`, `METHOD`. `misses.parquet` (and `misses.html` from `pcf misses`) next to each run's history; the scorecard's "Where it misses" section |
| **Level of detail** | player-game |
| **Interval** | whatever the model's history covers |
| **Cadence** | n/a (runs with every validation) |
| **Known at** | n/a: diagnosis after the fact; lenses never feed a model |
| **How to use it** | Read the section on the scorecard and copy it into RESULTS.md's "Where it misses". Each pattern worth chasing becomes a line in IDEAS.md. For a saved run: `pcf misses <id> --variant <v>`. To change the list, add a new dated list (D5, D7), never edit the old one |
| **Feeds** | every player-game RESULTS.md; IDEAS.md |

## Open questions for the CEO
None. D5 (review each season and on each important new model) and D7 (everything dated) are your calls, already recorded.
