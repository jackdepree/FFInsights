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
| I6 | ECR over-projects top players who play while questionable (−0.84 points; the pair stands out where neither alone does) | miss-lenses#F12, CEO spot-check | On new seasons, ECR's miss for top-third questionable players stays below zero; a product using the injury report beats ECR on those rows | open |
| I7 | Game conditions multiply a player's projection rather than add to it (big favorite, backup QB, home) | miss-lenses#F12 | A model with projection × condition terms, or trees, beats the lasso on held-out weeks | open |
| I8 | ECR under-projects players at home by about 0.3 points | miss-lenses#F13 | The miss holds in 2025+ live weeks, and a home term on top of ECR improves held-out pinball | open |
| I9 | Players new to a team are over-projected for snaps by about 2.3 points of share in their first 4 games, and their old team's history doesn't fix it; the role they're walking into might (who left, whose snaps are open). First look, 2026-11-04: room inputs help movers and career share doesn't (participation#F21); regulars in the room are over-projected too | participation#F9, CEO question | A vacated-snaps input reduces the error on those rows in the harness | open |
| I10 | Players with no depth-chart slot are over-projected for snaps by 3.3 points of share (largest in 2016), so a roster-status or practice-squad input might fix it | participation (Where it misses) | The miss shrinks in the harness, and holds after 2016 | open |
| I11 | Players coming off a bye are over-projected for snaps by 0.7 points of share | participation (Where it misses) | A bye term improves held-out pinball, or the miss is gone on new seasons | open |
| I12 | A pre-trained tabular model (Google's TabFM, 2026) might beat trees, most likely on small groups such as movers and rookies. Its weights are non-commercial and non-production, so at most a benchmark | CEO question, 2026-11-04 | On the same rows as next-game trees, for one position and one season, its absolute error beats trees' by more than the paired interval | open |
| I13 | The week of the season and the last week (times win rate) improve next-game share, and the gain survives the harness and the fantasy test | CEO question, 2026-11-05; participation#F29, F30 | A variant with them beats `trees_top` by more than the paired interval, passes the leakage checks, and top teams' last-week starters are no longer over-projected | Partly confirmed, 2026-11-05: the variant wins (participation#F33), but those starters are still over-projected (F35) |
| I14 | Ranges should widen with how much a player's share swings, as they do for players on the injury report | participation#F32 | Residuals per swing band even out coverage on games played, without worse pinball | open |
| I15 | Past share is partly game script, so a share earned in a blowout says less about the next game. Past share adjusted for each game's final margin should beat raw past share | CEO idea, 2026-11-05; participation#F31 | A script-adjusted recent share beats `trees_week` on held-out pinball by more than the paired interval | open |
| I16 | Players have script tendencies: some gain snaps when trailing, others when leading. A player's tendency times the next game's expected script should move their forecast, which an average effect across players can't show (F29 tested only that) | CEO idea, 2026-11-05 | First, tendencies hold up from one season to the next (a player's tendency correlates across seasons). Only then, the interaction beats `trees_week` on the players with strong tendencies | open |
| I17 | A player's share in the final regular-season week should count for little in playoff forecasts, because of rested starters and their fill-ins | participation#F36 | Discounting that game, or giving the model the change that week, cuts playoff error for those players by more than the paired interval | open |
| I18 | Wednesday and Friday games would gain from a run at noon on game day, as Thursday's did: their final report isn't in nflverse's file by the run they use now. 15 games since 2016, and 5 left in 2026 | prediction-ledger (decision 0016) | Range score on Wednesday and Friday rows with that moment, against the current one (220 rows, so a wide interval). Worth doing only if it's cheap in `weekly-run` | open |
| I19 | Game forecasts in the last regular-season week should know who has nothing to play for: teams locked into their seed or out of the race rest starters. Elo misses those games by 1.38 points more than the close, against 0.24 in other weeks | elo#F3 | A "locked or eliminated" flag, known before the run, cuts Elo's final-week margin miss by more than the paired interval (144 games, so a wide one). Pairs with I17 (rested starters' shares). **First look (2026-11-07, `elo/explore/carryover.py`, discovery only):** teams with a .800+ win rate going into the final week score 5.5 points (± 3.4) below Elo's rating-only forecast, against 1.4 above it in weeks 10 to the second-last; .700–.799 teams show nothing (+2.1 ± 3.1), rating rank 1–4 a little (−2.2 ± 2.8). Their usual QB sits healthy 43% of the time (13+ wins), against 5.6% in other weeks. The cheap flag is the record, not the rating; the exact one is "seed locked" from the standings | open, signal found |

## Graduated

| # | Idea | Became |
|---|---|---|
| I2 | Once the season-so-far average is known, the last 4 games add little | Confirmed, a finding: miss-lenses#F5. The last 4 games cut the error by only 0.01–0.04 points (most at RB) |

## Killed

| # | Idea | Result |
|---|---|---|
| I3 | ECR misses more on players whose role just changed | Not for ECR: its misses are no bigger after a role change. The lasso's are (+0.61 points with a same-position teammate Out), so role changes matter for beating box-score baselines, not ECR (miss-lenses#F4) |
