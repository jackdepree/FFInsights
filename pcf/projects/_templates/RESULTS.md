# Results: <project name> (`<id>`)

> Written by Claude **when the project is done**. One page plus the interface card. Copy to `projects/<id>/RESULTS.md`.
> Its job: a later project can build on this without redoing it or repeating its mistakes.

**Date:** · **Brief:** [BRIEF.md](BRIEF.md) · **MLflow experiment:** `<id>` · **Champion:** `pcf.<id>` version N

## In short
Two or three sentences: what we learned and whether it worked against the brief's tests.

**Scorecard:** link (MLflow) · **Vault:** result, opened on date (or "spent") · **Versions tried:** N

| Check (docs/VALIDATION.md) | Result |
|---|---|
| Signal / no noise, or beats baselines | |
| Calibration and range coverage | |
| Leakage | |
| Football sanity (CEO review date) | |
| CEO spot-check (date): what was checked | |

## Hunch verdicts
Each hunch from the brief, and any unconventional bet made along the way. Copied into [`projects/HUNCHES.md`](../HUNCHES.md).

| # | Hunch | Verdict (held / failed / unclear) | Evidence, with its size |
|---|---|---|---|
| H1 | | | |

## Terms
The project's terms as they ended up: anything new, or anything whose definition changed since the brief. These are copied into `docs/GLOSSARY.md`.

## Findings
Numbered so other projects can cite them as `<id>#F1`. One claim each.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | | MLflow run `<run_id>` / chart | strong / suggestive / weak | positions, seasons, situations |

## The ladder
| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | baseline | — | |

## Where it misses
*Models only.* Where the errors cluster, so they become new problems to solve. Copy it from the scorecard's "Where it misses" section (`pcf.validation.misses`; `pcf misses <id>` for a saved run). Kept short on purpose:
- the fixed lenses, with the date of the lens list used (miss-lenses D1);
- plus at most 5 other tags whose average miss is clearly not zero (99% interval: about 20 tags are scanned), largest first.

Each pattern worth chasing becomes a line in `projects/IDEAS.md`.

| Lens | Group | Rows | Average miss (actual − predicted) | 90% interval | Idea |
|---|---|---|---|---|---|

## The case against
The strongest argument that this result is wrong or overstated: a leak no check covers, too few seasons, a lucky stretch, a score that flatters it. And what it would take to check. Written before asking to merge, so the CEO approves with it in view.

## Pitfalls
What went wrong or nearly did, so the next project avoids it.

## Not looked at
What we deliberately skipped or ran out of time for.

## Could be improved
The best next steps, most promising first.

## Don't redo
What a future project should *not* repeat, unless it's deliberately retrying (and why it would).

## Interface card
Also copied into this project's `interface` block in `registry.yaml`.

| | |
|---|---|
| **Inputs** | tables and expert outputs (with versions) |
| **Outputs** | `outputs/<id>/<version>/`: quantities, with mean, q10, q50, q90 |
| **Level of detail** | e.g. player-game |
| **Interval** | e.g. weekly, from week 2 |
| **Cadence** | in_season / retrospective / offseason_events |
| **Known at** | when each output is available |
| **How to use it** | e.g. as a feature, as a prior, or not below N snaps |
| **Feeds** | which projects use it |

## Open questions for the CEO
The questions this project raised that need a football or product call.
