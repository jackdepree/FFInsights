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

## Findings
Numbered so other projects can cite them as `<id>#F1`. One claim each.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | | MLflow run `<run_id>` / chart | strong / suggestive / weak | positions, seasons, situations |

## The ladder
| Rung | Method | Result vs the rung below | Takeaway carried forward |
|---|---|---|---|
| 0 | baseline | — | |

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
