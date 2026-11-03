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
| I1 | Where ECR's experts disagree (a wide `ecr_sd`), results are more spread out, so ranges should widen there | baselines (Could be improved, 2) | ECR's q10–q90 coverage by `ecr_sd` band: under 80% where experts disagree, over 80% where they agree | open: inconclusive. The spread mostly tracks rank; within ranks 1–24 the widest spreads cover a little less (74–77% vs 79–82%) on few rows (miss-lenses#F6). Recheck with more seasons |

| I4 | Players active while questionable score less than box-score history says: playing hurt costs about a point | miss-lenses#F9 | A box-score model with an injury-report feature beats the same model without it, on held-out weeks; ECR, which already sees reports, shows no such miss | open |
| I5 | Rookies improve during their first season, so season averages under-project them | miss-lenses#F9 | Rookies' average miss rises with week; a weight on recent games for rookies only beats the plain average | open |

## Graduated

| # | Idea | Became |
|---|---|---|
| I2 | Once the season-so-far average is known, the last 4 games add little | Confirmed, a finding: miss-lenses#F5. The last 4 games cut the error by only 0.01–0.04 points (most at RB) |

## Killed

| # | Idea | Result |
|---|---|---|
| I3 | ECR misses more on players whose role just changed | Not for ECR: its misses are no bigger after a role change. The lasso's are (+0.61 points with a same-position teammate Out), so role changes matter for beating box-score baselines, not ECR (miss-lenses#F4) |
