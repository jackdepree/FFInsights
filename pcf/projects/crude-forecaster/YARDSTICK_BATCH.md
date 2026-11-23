# The yardstick batch (retro 3's group D)

**Status: run, 2026-11-23** (the CEO: "Yes, start it"). Results: [RESULTS.md, "The yardstick batch"](RESULTS.md#the-yardstick-batch-2026-11-23); calls: [decision 0042](../../docs/decisions/0042-yardstick-batch.md); scripts and outputs: [`explore/yardstick_batch/`](explore/yardstick_batch/). **The CEO's answers, 2026-11-23:** spot-check (a) of I114 (held; RESULTS, "The spot-check: I114"), QB rushing published as a yardstick target, the yardstick market-free for now, no vetoes, I115 into Elo's next build.

> **The CEO, 2026-11-23:** "Ok, the build chat should do the yardstick batch, d."
>
> Retro 3 sorted the backlog (`projects/RETRO.md`, retro 3). Group D is the backlog's yardstick inputs: ideas that are each scored once against the crude forecaster. Retro 2 sorted them as one session, and nothing ran them. This page is the build chat's brief. It holds everything the session needs, so it can start from this file, the ideas' rows in `projects/IDEAS.md`, and the crude forecaster's own files (`BRIEF.md`, `RESULTS.md`, and the registry's interface card).

## What the batch is

**Discovery, not a model.** Each idea becomes one input (or, for I67 and I70, one change to the yardstick itself), scored with `pcf.baselines.crude.score_input` against the crude forecast.

**Nothing ships from this batch.** A gain says the idea is worth building into an expert, and the expert's own build decides whether it's used.

**The rule for every input** is the yardstick's own: a gain counts when its 90% interval clears zero and it beats the 19 copies of the same input shuffled within each week. Score each input alone and with participation in, as the registry's `how_to_use` says. I69's caution applies: a shuffled copy once reached +0.57%, so print the largest shuffled gain beside every row.

**Seasons:** the yardstick's own: fit from 2016, scored 2019-2024. The 2025 vault stays untouched.

**Odds:** every idea's odds are in its IDEAS.md row and were written before this batch. Don't add or change odds after a result. Retro 3 moved some odds before the batch (I84's running backs to 75%, I59 to 30%), and those are the ones to score.

## The ideas

| Idea | What to build and score | Board(s) | Claude's odds (IDEAS.md) |
|---|---|---|---|
| **I48** Garbage-time production counts for players too | A player's past yards split into garbage time and the rest (the tag table's score-and-clock rule), as two inputs, against the pooled past yards already on the board | Receiving, rushing and passing yards; next game | Medium (about 75%) that the split doesn't beat the pooled version, and garbage time's weight per yard is at least 0.8 of the rest's |
| **I59** A pass-heavy team's receivers and tight ends gain more than their own numbers say | The team's pass rate over expected (pace's `proe_shrunk`, already pinned) and schemes-v2's traits, beside the player's numbers and the offense's quality | Receiving yards, WR and TE rows only; next game and rest of season | 30% (retro 3) that 1%+ survives once the offense's quality is in |
| **I60** Availability is a third of the room in a rest-of-season forecast | A forecast of games played over the window (from participation and the injury report), as an input | The rest-of-season yards boards (players and teams) | 60% that it's worth 2+ points of a rest-of-season forecast's error |
| **I67** QB rushing yards as a yardstick target | A `rushing` target with QBs added. Report the crude forecast's share of the error removed, and participation's worth, on QB rows apart | Rushing yards; next game and next 3 | 70% that participation is worth less on QB rushing than on RB rushing; the crude forecast removes 20 to 35% of the error |
| **I70** Score participation on rows it didn't choose | The row rule from the depth chart (starter or first backup) instead of participation's own chance of a snap; then participation's added-alone gain against R3's | All player boards | 65% that participation's passing gain rises, and the others move under 1 point |
| **I75** Roster continuity as a team feature | The pre-season share of a team's plays expected to go to players who didn't play last season (week 1 depth chart, last season's snaps; players who changed teams don't count). The hindsight version is the ceiling | Team yards gained and allowed; rest of season | 50% that it adds 2%+ to the defense's rest-of-season forecast; 30% for offense |
| **I84** Each mover's usage prior from whoever owns it | Movers' first 4 games. Receivers and tight ends: the player's own old-team target share against the new team's slot. Running backs: the new backfield's carry share against the back's own | Receiving and rushing yards; next game, movers' rows | 80% that the own-share prior wins for receivers; 75% (retro 3) that the new backfield's split wins or ties for running backs; 2 to 5% on movers' rows, under 0.3% overall |
| **I114** The betting lines as yardstick inputs | The spread and the total (and the implied team total) as inputs; see the timing call below | Team yards gained and allowed (next game); players' yards (next game) | 75% that it adds 2%+ for team yards; 40% for players' yards |

## Technical calls already made (retro 3, for the CEO's veto)

- **I58 and I61 leave the batch.** Both are about touchdowns:
  - I58: a QB's red-zone carries and his rushing touchdowns.
  - I61: a throw's expected touchdowns knowing the passer.

  The yardstick is yards only (the CEO, 2026-11-15), so they go to `td-expert`'s build, which has an agreed brief. Their rows in IDEAS.md say so.
- **I48 is scored in yards,** not fantasy points, for the same reason.
- **I114's timing must be settled before it's scored.** The crude forecaster's moment is the Saturday run, but the schedule's lines are treated as known at kickoff (`docs/DATA_SOURCES.md`), so the yardstick will rightly refuse them. The build chooses one of these and logs the decision in `docs/decisions/`:
  - **(a) Lines known at the run's moment:** ESPN's opening lines (2022 on) or our collected lines (2026 only). These are few seasons, so the intervals will be wide.
  - **(b) The schedule's near-closing line,** scored with a flag as "the line at kickoff". It's a ceiling, not a usable input.
  - **(c) Both:** (b) as the ceiling and (a) as the honest number. This is Claude's recommendation.

  Never pass the kickoff line off as known at the Saturday run.

## When it's done

- **IDEAS.md:** each idea's row moves to Graduated or Killed in the same commit as its result (retro 3's W9, accepted 2026-11-23). The row gives the numbers, which of Claude's odds came true, and the input's script.
- **FINDINGS.md:** a row for each settled finding. **CONSISTENCY.md:** a row for any new measure (I75, the garbage-time split).
- **The crude forecaster's `RESULTS.md`:** a short "yardstick batch" section with one row per input.
- **Code:** reusable feature code goes in the package with tests (rule j). One-off checks stay in `projects/crude-forecaster/explore/`.
- **The merge:** the batch's technical calls are listed for the CEO's veto before it merges.
