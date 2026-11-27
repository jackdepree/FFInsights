# Night batches: where every open idea lives

> W17 (retro 5, the CEO, 2026-11-27: "We can not afford to constantly have ideas in the backlog"). Every open idea in [`IDEAS.md`](IDEAS.md) has a home. The home is either a project we will build, whose build tests it, or one of the night batches below. A night batch is a named build-chat session that runs a group of ideas overnight. An idea that fits neither is closed as "not planned", and it can be reopened. A new idea gets its home when it is written: its Status cell names the home, and this page lists it.

**How a batch runs** (the build chat, at night, from this page and the ideas' rows):
- **Odds first.** Every idea already has its odds in `IDEAS.md`. A batch adds a pass rule for each idea to its script's header before the run, and it doesn't change the odds.
- **Discovery only.** The 2016-2024 test seasons; the earlier-seasons check where the walk has them (W14); gains per season (W13). The 2025 vault stays closed.
- **Every row closes in the same commit as its result** (W9): Graduated (into a project's brief or a finding) or Killed, with one line. An idea that turns out to need more than the night goes back with a new home and the reason.
- **The report** is `projects/retro/batches/<batch>.md`. Each idea gets a start and end time, so its tokens can be charged to it (W18). The report gives one line for each idea that matched its odds, and detail for each that didn't (W16).
- **The merge** needs the CEO's yes in the morning, as with any build.

**Sorted 2026-11-27** (the CEO: "Ok let's find homes for the backlog."). There were 59 open ideas. 57 got a home and 2 closed as not planned (in `IDEAS.md`'s Killed table).

## Homes in a build

| Build | Ideas | Status |
|---|---|---|
| **`aging`** | I157 (wear in efficiency, through rushing mileage after 29), I158 (stars keep their jobs beyond their play), I188 (the pull-back null as a shared check) | Brief agreed 2026-11-27; the build runs tonight |
| **`player-opportunity`** | I5 (rookies improve in their first season), I145 (distillation into the crude forecaster: a yardstick change, so it needs the CEO's yes first), I149 (players add up to their team), I152 (role drift), I184 (expected attempts from a forecaster) | The registry's next composite; it isn't kicked off. It waits for the CEO's pick of what comes after aging |
| **`market`'s exploration** | I150 (the market's update from open to close as a target) | Waits for odds-collection's lines (free lines only) |

## The night batches

In the order Claude proposes. The first three feed player-opportunity and the yardstick most directly. Sizes are per batch: "quick" is under an hour an idea, "session" is a few hours.

| # | Batch | Ideas | Shared code and data | Size | What we expect (W16) |
|---|---|---|---|---|---|
| N1 | **Participation v2** | I11 (bye weeks over-forecast snaps), I15 (share adjusted for the game's margin), I16 (players' script tendencies), I51 (a probable starting QB), I138 (recalibrate `active` on Questionable rows), I191 (usage momentum within a season) | participation's champion and harness runner; availability's report table | A night | Participation as a well-tuned engine: most tweaks tie. About 2 of 6 pay, with I138 the likeliest |
| N2 | **Stabilization v2** | I173 (movers' pull, and where the new team adds), I183 (the opponent-adjusted faced rate), I186 (the trend for teams), I189 (k from the role, not the position) | stabilization's pulls and walks; the role table | A night | Second pulls and trends paid there before (F124), so about 2 of 4 pay, small |
| N3 | **Saved walks** | I66 (blend trees with the linear rung, context-live), I103 (trees for opportunity-quality's other horizons), I117 (trees for td-expert's other forecasts), I119 (a game's chance of 2+ touchdowns without a Poisson), I120 (a QB's season of thrown touchdowns as a mixture), I139 (the COVID reserve codes, read right) | each built expert's saved features and walks | A night (quick each) | Trees win where they won before (rushing, next game) and tie elsewhere: about 3 of 6 pay |
| N4 | **Misses after a change** | I41 (a new head coach's defense), I54 (the offense's rating lags a QB change), I56 (teams run more after a bye), I68 (a new starting QB's first games), I85 (ranges after a QB change), I148 (fast traits as a change alarm) | team-efficiency, pace, Elo and the crude forecaster's walks; I47's change flags | A night | The misses are real (they've been measured twice), but they're few games: about 2 of 6 pay, on the rows after a change only |
| N5 | **Team ratings** | I31 (series success rate), I32 (more shrinkage for pass defense), I42 (rest-of-season ranges for whole-season shifts), I115 (Elo over a rest-of-season window, with roster inputs; the CEO routed it to Elo's next build), I127 (teams hit by injuries rebound) | Elo and team-efficiency's walks; availability's games lost | A night | Elo and team-efficiency are hard to beat: about 1 to 2 of 5 pay |
| N6 | **Harness and ranges** | I1 (wider ranges where ECR's experts disagree), I45 (count the seed's luck in the no-noise interval), I52 (real but redundant traits widen ranges), I62 (a post-game mode for the shared harness), I64 (refit each week), I72 (FTN's "0 pass rushers" as missing) | `pcf.validation` and the harness | A night | Tooling more than findings: I45 and I62 change the code every later build uses (a shared-module change, so the CEO sees it before the merge) |
| N7 | **Coaches and calls** | I21 (stayers for coaches), I71 (a defense's call pattern as a scheme trait), I88 (aggressiveness as a read of strength), I93 (propensity models for the calls) | schemes-v2's tables, context's calls, the coach table | A night | Coaches' traits repeat but rarely pay (H78, I86): about 1 of 4 pays |
| N8 | **Nearest outcomes** | I81 (linemen's absences on pressure), I92 (expected yards after contact per game; the CEO's addition 2026-11-26), I99 (measure each player on the outcome nearest his job, then compose upward) | skill-over-expected's and context-retro's tables, participation's on-field lists | A night, maybe two | The AlphaGenome bet: nearer outcomes are less noisy. About 1 of 3 pays, most likely I81 |
| N9 | **Causal player value** | I77 (double machine learning for rotating players), I78 (synthetic control for each long absence), I82 (playing time as the coaches' read of skill) | participation's on-field lists, skill-over-expected's outcomes | A night, maybe two | The exploratory methods. Methods have paid less often than football claims (retro record), so about 1 of 3 pays |
| N10 | **Real but unpaid** | I141 (every real-but-unpaid measure scored on every board it wasn't built for), with the CEO's H6 inside it | `score_input` and the 19 copies; every saved measure | A night | Most measures stay unpaid; 2 to 4 of about 40 find a board where they pay |
| N11 | **After 2026** | I6 (ECR over-projects top players who play while questionable), I8 (ECR under-projects players at home) | ECR and the 2026 season | Quick | Runs once 2026's data is in (February 2027): these need a season no test has seen. About 1 of 2 holds |

## Homes in a retro

| Retro | Ideas | Why there |
|---|---|---|
| **Retro 6, step 2** | I147 (seasons won as a vault-risk test), I190 (our odds, recalibrated by our own record) | Both are about scoring our own record. I147 reads the per-season gain tables (W13) that aging's build and the batches save; I190 fits its map on retros 1-5 |

## Closed as not planned (2026-11-27)

- **I110** (train the calls' fields only where they exist) and **I111** (the pass rusher's side of the split): the CEO held them on 2026-11-22 ("No split idea for now"), and nothing has reopened the split since. They can be reopened when context's split comes back.
