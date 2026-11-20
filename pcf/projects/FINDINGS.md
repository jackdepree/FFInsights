# Findings

> **Status:** started 2026-11-20 (retro 2, W5, the CEO's direction), with the rows retro 2's backlog batch settled. **The first full fill**, from every finished project, is still to do. The rule is in `pcf/CLAUDE.md`, "The findings table".

The CEO, 2026-11-20: "things need to aggregate, just like it needs to be hierarchical, or else you and I will basically miss the findings, or at least it would take a lot of effort to go and look for it."

**Settled only.** The CEO, 2026-11-20: "keep the findings table to just settled stuff, just things that you can trace back, through some sort of finding or idea or project, and be like, okay, that's where we figured it out. Those were the assumptions. That's the methodology. That was the goal." Every row names its source, where the method and the assumptions are written down. When two rows disagree, the one with the weaker trail is marked unclear and the conflict is noted in both.

This page is the top level. Below it: each project's `BRIEF.md` and `EXPLORATION.md` (the detail), [CONSISTENCY.md](CONSISTENCY.md) (does a measure repeat), [HUNCHES.md](HUNCHES.md) and [IDEAS.md](IDEAS.md) (the bets and their verdicts), [RETRO.md](RETRO.md) (the patterns across them).

## Use and ignore, by level

So far from retro 2's batch only; the first full fill adds the rest.

| Level | Use | Ignore |
|---|---|---|
| **Receivers and tight ends** | Target share and target depth: they are the player's, and travel when he moves (F1) | High-stakes ("clutch") performance as a separate skill (F3) |
| **Running backs** | For a back who moves, his new backfield's split, not his own old carry share (F2) | His past carry share as his own trait when he changes teams (F2); clutch (F3) |
| **Running backs and tight ends** | Their script tendency (more or fewer snaps by game margin) as a trait that repeats (F4); not yet shown to help a forecast | |
| **Quarterbacks** | | Clutch (F3) |
| **Teams** | An in-season change of starting QB as a signal that the team will do worse than its rating in the next 4 games (F5); a seed lock in the final week, carried into the first playoff game's playing time (F6) | Betting against the line on change games alone (F7); extra snaps for young players on eliminated teams (F8) |

## The table

One row per finding. Discovery means a look at past seasons that isn't a forecast gain yet (it never counts as a model beating anything; CLAUDE.md).

| # | Finding | Level | Consistent? | Predicts what, by how much | Holds where / not where | Verdict | From |
|---|---|---|---|---|---|---|---|
| F1 | **Target share and target depth belong to the player.** A receiver or tight end who changes teams keeps most of his season-to-season repeat | Player (WR, TE, RB targets) | Stayers repeat 0.74 (share) and 0.77 (depth); movers 0.65 and 0.66 | His old rate outweighs the new team's slot: weights 0.60 against 0.15 (share), 0.65 against 0.03 (depth) | 2016-2024; 40+ targets in both seasons; 150 and 132 movers | Held (discovery) | I53, retro 2 (`retro/explore/retro2_repeat.py`) |
| F2 | **A running back's carry share belongs mostly to his backfield.** A back who moves keeps about a third of the repeat; goal-line share keeps about half of a weaker one | Player (RB) | Stayers 0.68 (carry share), 0.51 (goal line); movers 0.24, 0.28 | His old rate's weight 0.24; the new slot's 0.02 (so neither carries much: the new room's split does) | 2016-2024; 50+ carries in both seasons; 78 movers | Held (discovery). Who owns it is open (I86, H78). The CEO's explanation: a back "has to thrive within opportunities, and the team around them has to create the opportunities"; a receiver creates his own (RETRO.md, retro 2, section 8) | I53, retro 2 |
| F3 | **There is no clutch trait.** EPA on high-stakes plays beyond a player's other plays doesn't repeat season to season | Player (QB, RB, receivers) | QBs 0.08 (null's 95th percentile 0.09), RBs 0.00, receivers -0.01; ordinary EPA repeats 0.37 (QB), 0.21 (receivers) | Nothing | 2016-2024; snap-leverage's high-stakes flag | Held (no trait), as baseball finds | I44, retro 2 |
| F4 | **Script tendencies repeat for running backs and tight ends, not receivers.** The slope of a player's snap share on his team's final margin | Player (RB, TE) | RB 0.25, TE 0.29 (beyond all 100 shuffles); WR 0.01 | Untested as a forecast (I16, step 2) | 2016-2024; 8+ games and a 25%+ share; final margin as the script (an outcome, so not a pre-game input as is) | Held (repeats; discovery) | I16, retro 2 |
| F5 | **After an in-season change of starting QB, teams do worse than forecast for 4 games, and no better after.** Our offense rating is 0.039 EPA a play too high; Elo's margin 1.8 points too high; the closing line 1.0 point too high | Team | 9 of 9 seasons (team-efficiency, Elo), 13 of 19 (the line) | The size of the miss above; a fix is untested (I54, I68) | 2016-2024 (our experts), 2006-2024 (the line); every in-season starter change, a backup's or the starter's return. **Corrects I47**, which compared these games only with the same teams' other games after a change and read a rebound from game 5 that isn't there against all teams (+0.008, not clear) | Held (discovery) | I47 and I54, retro 2 (`retro/explore/retro2_i47_recheck.py`); I83 (`retro2_i83_line.py`) |
| F6 | **Rested starters come back in the playoffs.** On a team that was seed-locked in the final week, regulars play 9.2 points of share more than participation forecast in the first playoff game, and fill-ins 9.7 less | Player, on teams with a lock | 7 of 9 seasons (regulars), 9 of 9 (fill-ins) | 9 to 10 points of snap share, both ways | 2016-2024; 102 regular and 192 fill-in rows; a fix is untested | Held (discovery) | I17, retro 2 (`retro/explore/retro2_incentives.py`) |
| F7 | **The closing spread can't be beaten on change games alone.** Against a new head coach in games 1-4: 51.1%; against a team after an in-season QB change, games 1-4: 50.9%; on it from game 5: 50.0% | Team-game, betting | Both halves near 50% (2006-2015, 2016-2024) | No edge against 52.4% | 2006-2024, regular season; directions fixed from I47 before the run. The line's 1-point miss (F5) is in the average margin, not the cover | Held (no edge) | I83, retro 2 |
| F8 | **Young players on eliminated teams don't get extra snaps in the final week** beyond what participation forecasts | Player, final week | | +0.3 points of share (-1.3 to +2.1) | 2016-2024; the final week only (the last three weeks are untested) | Held (no effect) | I46, retro 2 |
