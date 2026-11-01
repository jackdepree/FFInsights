# 0009: The champion is set in registry.yaml and changes only by merge

**Date:** 2026-11-01 · **Decided by:** CEO (who may change it: 1A in the `experiment-tracking` brief), Claude (how it's enforced)

**Decision:** A model's `champion` changes only through a merge the CEO approves. The version is written under the project in `registry.yaml` (`champion: 3`), on the project's branch, with the old and new scorecards side by side in its RESULTS page. After the merge, `pcf champions` copies it to MLflow's `champion` alias; it refuses to run off `main` or with uncommitted registry changes. Claude may set `challenger` directly. Every model goes through `pcf.core.tracking`, which also refuses to register a run without passing leakage checks.

**Why:** `champion` decides what the weekly run predicts and bets. MLflow's store is local and not in git (experiment-tracking#F11), so an alias set there takes effect at once, before anyone reviews it. A line in `registry.yaml` is reviewed and merged like code.

**Alternatives:** the CEO approving each promotion separately (an extra step for every routine refit); promoting automatically on the best backtest (rejected: after many attempts the best backtest is partly luck, the cherry-picking VALIDATION.md's attempt count is there to stop).

**Revisit if:** routine weekly refits of an unchanged model need a new version each week. Then the weekly run could refit in place, and only a change of method would need a merge.
