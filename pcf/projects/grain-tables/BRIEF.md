# Brief: Tables at every level of detail (`grain-tables`)

> An infrastructure project: no model, but one call for the CEO (end of page), because it decides who counts as "playing" in a game. Light exploration: [EXPLORATION.md](EXPLORATION.md).

**Status:** draft · **Layer:** 0, data (Phase 0) · **Cadence:** — (rebuilt after each data refresh)

## The question
Turn the cleaned sources into a few saved tables, one per level of detail: play, player-game, team-game and game. Every row is keyed by shared ids, and every piece of it says when it became known.

## Why it matters
Every expert in layer 1 reads its data from these tables, through the `as_of` gateway. Right now each one would have to join a dozen raw sources itself, and each would get the known-at times slightly wrong in its own way. Doing the joins once, with tests, means one place to get rule c right. The exploration already found one leak to fix on the way: weekly rosters reveal Sunday's inactives from the start of the week (F4).

## Terms
- **Standard terms used:** known_at, as_of, gateway, level of detail, kickoff, week window, known-at rule, depth label, state source. See `docs/GLOSSARY.md`.
- **New terms:**
  - **Table part:** one source's columns for a table, saved on their own with that source's `known_at`. For example, `player_game` has a stats part (known kickoff + 1 day), an NGS part (the day after the week ends) and a PFR part (about 9 days later). The parts share the table's keys.
  - **Spine:** the list of keys a table has a row for (the `player_game` spine is every player-game PCF tracks). Parts attach to it, and a part with no row for a key leaves its columns empty.
  - **Inactive:** a player on the 53-man roster who isn't dressed for the game. Teams name them 90 minutes before kickoff (roster `status` = `INA` from 2019).

## Builds on
| Project | What we use | Why |
|---|---|---|
| `data-layer` | `scan`, `snapshot`, the raw copy | The inputs |
| `cleaning-port` | `standard.*` (ids, team codes), `players_on_play`, depth labels, `slot_labels` | Clean input for every part |
| `timeline` | `calendar`, `known_at` rules for every dataset, `check_known_at` | Every part's `known_at` |
| `cleaning-port#F17`, `#F18` | Snap counts map pfr→gsis through the players file; empty and repeated rows are dropped in `standard` | Clean keys (F6) |
| `timeline#F4`, `#F10`, `#F11` | Injury rule, depth charts at kickoff, NGS Super Bowl week | Already in the rules |
| `grain-tables#F1`–`#F10` (exploration) | One game a week, the spine, sparse sources, known-at spread, the roster leak | The plan below |

**Already tried:** `old/` built one wide frame per model, joining on season and week with no timestamps. It worked for training but couldn't say what was known when.

## Assumptions
- **Player-week is player-game** (F1). There's no `player_week` table. NGS, which comes by week, attaches to the player's game that week.
- **Each source keeps its own `known_at`** (F8). A technical call, logged in `docs/decisions/0008-table-parts.md`:
  - **Chosen: table parts.** Each table is saved as one part per source, each with its own `known_at`. `tables.load("player_game", at=moment)` joins the parts known at that moment onto the spine. A part not yet known comes back as empty columns, never as a missing row. The gateway (`validation-harness`) wraps this reader.
  - **Alternative: one wide table with a `known_at` per column group.** It gives the same answer, but every refresh rewrites the whole table, and the reader has to know which columns go with which timestamp.
  - **Tempting but bad: one `known_at` per row.** If it's the latest source's time, box scores are held back two weeks behind FTN. If it's the earliest, PFR, NGS and FTN leak into predictions made before they existed.
- **Roster `status` becomes known 1 hour before kickoff** (F4). Teams turn in inactives 90 minutes before kickoff, so this leans late by 30 minutes. Membership (who is on the team) stays at the start of the week. The roster known-at rule splits in two.
- **Season, career and event tables wait.** A season total is only safe if it's cut at the moment the model asks, so totals belong in the reader, built from `player_game`. Storing them invites leakage. The offseason event table (draft, combine, trades, contracts) waits for the first `offseason_events` expert that needs it. Both go back in the registry as ideas.
- **Seasons:** play from 1999, game and team-game from 1999, player-game from 2002 (weekly rosters start then). Each part covers its source's own years: snaps from 2013, NGS 2016, PFR 2018, FTN 2022, participation 2016–2025.

## Goals: what gets built
1. **`game`:** one row per game, from schedules and the calendar. Three parts: facts (week 1 start), lines (kickoff), result (kickoff + 1 day).
2. **`team_game`:** two rows per game. The schedule part (opponent, home or away, rest days) and the team-stats part (kickoff + 1 day).
3. **`play`:** one row per play. The play-by-play part (kickoff + 1 day), the participation part (formation, coverage, players on the field: after the Super Bowl) and the FTN part (+14 days).
4. **`player_play`:** one row per player on the field per play, from participation, with each player's slot label (`cleaning-port`). Known after the Super Bowl, like participation.
5. **`player_game`:** the spine (question 1), then the parts: roster (membership at week start, status 1 hour before kickoff), injury report (its own rule), depth label (the chart at kickoff), stats, snaps and ff_opportunity (kickoff + 1 day), NGS (the day after the week ends), and PFR (about 9 days later).
6. **The reader:** `tables.load(name, at=None, parts=None, seasons=None)` joins the parts known at `at` onto the spine. `tables.build(name, seasons)` writes each part to `data/tables/<name>/<part>/season=YYYY/`.
7. **Fixes on the way:** the roster rule split (F4); NGS read a season at a time and `ff_opportunity`'s text season (F9); the stale `CONVENTIONS.md` line that says snap counts map through `load_ff_playerids` (it's the players file, `cleaning-port#F17`).

**Not in this project:** the gateway itself and the leakage-check suite (`validation-harness`), tag tables (`tag-tables`), and the season, career and event tables (above).

## Tests
- **Success looks like:**
  - **Contract:** every part has unique keys, and a UTC, timezone-aware, non-null `known_at` that passes `check_known_at`. No part from a game is known before that game's kickoff, except the roster, injury and depth parts.
  - **Spine:** from 2013, at least 99.9% of player-games with a snap are on the spine, and so is every `player_stats` row.
  - **Joins:** `team_game` has two rows for every played game. Participation and FTN parts attach to at least 99.5% of run and pass plays in their years.
  - **Point in time:** for any moment, `load` returns no value from a part known after it. Deleting every source row known after a moment changes nothing `load` returns at that moment.
  - **Roster leak closed:** no `INA` status is visible earlier than 1 hour before kickoff.
  - **Football sanity:** for each team-game, the players' passing yards, rushing yards and receptions add up to the team's. No player has more offensive snaps than their team ran plays.
- **Failure looks like:** parts that can't be joined without losing rows, a reader too slow to call for every training week (over about 2 seconds per season for `player_game`), or a cross-source total that doesn't add up and can't be explained.

## Inputs and outputs
- **Inputs:** the raw nflverse copy through `scan`, the `standard` functions, the timeline calendar and rules, depth labels.
- **Outputs:** Parquet parts under `data/tables/`, partitioned by season. `pcf.data.tables`: `build`, `load`, and one builder per table. Table schemas in `pcf.data.schemas` (keys, types, `known_at`).

## How it will be used
Every layer-1 expert declares the tables it reads (`inputs = ["play", "player_game"]`) and gets them through the gateway at a moment. Retrospective experts (`voe-retro`) read the participation and FTN parts; in-season experts get those columns empty until they're known.

## Questions for the CEO
1. **Who gets a row in `player_game`?**
   - **Why it matters:** this is the list of players PCF makes a game prediction for, and learns from. A player missing from it can never be predicted to sit out, or to play.
   - **A. Everyone on the 53-man roster that week** *(Recommended).* From the weekly roster: everyone dressed, plus the inactives (from 2019), plus anyone who played without a roster row (7 player-games in 2024). About 27,400 player-games a season (F3).
     - A player who sits gets a row with zero snaps. So "will he play?" can be learned and predicted, and a star ruled out on Sunday morning shows up as a zero, not as a gap.
     - Before 2019 inactives aren't marked (F3): they show up as players with no snap, known the day after the game.
     - Practice squad and injured reserve stay out, but their status is in the roster part.
   - **B. Only players who played** (a snap or a stat, about 26,600 a season). It's the box score exactly. But every row in training played, so a model never sees a player sit, and a product has to add the others back.
   - **C. Players with a stat line** *(tempting but bad).* The familiar fantasy box score. But it drops 27% of the players who played (F2), every offensive lineman and most special-teamers, and the snap, participation and line experts lose their rows.

## Plan
No ladder (no model). Schemas and the reader first, with the point-in-time tests on toy tables. Then `game` and `team_game`, then `play` and `player_play`, then `player_game` and its parts, then the roster rule fix and the sanity tests on real data. About 2 sessions, then the results page and your merge.
