# Ideas: hypotheses to test

> The discovery loop's inbox (CLAUDE.md, "Two loops"). The CEO and Claude both add lines. Claude checks them cheaply, in batches, and records the answer here.

**How this differs from the registry and the roadmap:**

| | Registry and roadmap | Ideas |
|---|---|---|
| Holds | Projects: work with a brief, code, results and dependencies | Hypotheses: claims about football or our models that might be true |
| Size | Days to weeks | Minutes to an hour to check |
| Question | What are we building, and when? | What might be true, and how would we know? |
| Ends | Done, with an interface card | Killed (with a one-line result), folded into a project's brief, or grown into a project of its own |

- **An idea that survives a cheap check graduates:** into an existing project's brief, or into the registry as a new project.
- **A killed idea stays here with its result,** so nobody checks it twice.
- **A cheap check is discovery, not proof.** It never counts as a model beating anything; only the harness does that.

Each line: the claim, where it came from (a CEO hunch, a project's misses, a disagreement with ECR or the market), and what result would say it's real.

## Open

| # | Idea | Source | How we'd know | Status |
|---|---|---|---|---|
| I1 | Where ECR's experts disagree (a wide `ecr_sd`), results are more spread out, so ranges should widen there | baselines (Could be improved, 2) | ECR's q10–q90 coverage by `ecr_sd` band: under 80% where experts disagree, over 80% where they agree | open |
| I2 | Once the season-so-far average is known, the last 4 games add little | baselines#F11 | A lasso with both: the last-4 coefficient near zero, and dropping it doesn't hurt held-out pinball | open |
| I3 | ECR misses more on players whose role just changed (a teammate out, a new starter) than on settled roles: information ECR may lack | Claude, 2026-11-03 | ECR's average miss by the depth-chart and injury tags of the player and their teammates | open |

## Graduated

| # | Idea | Became |
|---|---|---|

## Killed

| # | Idea | Result |
|---|---|---|
