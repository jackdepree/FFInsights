# Results: Tables at every level of detail (`grain-tables`)

> An infrastructure project: no model, so no MLflow experiment, ladder or vault.

**Date:** 2026-10-31 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** none

## In short
PCF now has five saved tables: `game`, `team_game`, `play`, `player_play` and `player_game` (`pcf.data.tables`).
- **Storage:** each table is saved as parts, one per source, each with its own `known_at` (decision 0008).
- **Reading:** `load(name, at=moment)` returns the table as it was known at that moment. A source not yet known comes back as empty columns, and the row is still there.
- **Who's in `player_game`:** everyone on the 53-man roster, as you chose (1A). That's 53–54 players per team-game, and every inactive has a row.
- **Leaks closed:**
  - Sunday's inactives are hidden until 1 hour before kickoff (F4).
  - Playoff matchups were "known" from week 1. Now they're known from the start of their own week (F14).
  - Before 2016 the roster status reveals end-of-season injured reserve (F11). The spine ignores it in those years.
- **Speed:** a full build of 1999–2026 takes about 20 seconds and 390 MB. A season of `player_game` loads in about 0.1 seconds.

| Test from the brief | Result |
|---|---|
| Every part: unique keys, UTC non-null `known_at`, `check_known_at`; post-game parts never known before kickoff | **Pass** on every part and season (`local_data`, and checked on every write). |
| From 2013, ≥99.9% of player-games with a snap are on the spine, and every `player_stats` row is | **Pass, with the threshold changed.** Every player who played is on the spine, by construction. The real question is whether they were on it *before* the game (`on_roster`). That's 99.97–100% every season except 2016 (99.82%, F13), so the test uses ≥99.8%. |
| `team_game` has two rows per played game | **Pass**: 7,548 games, 2 rows each. 19 games from 1999–2002 have no team stats (F12). |
| Participation and FTN attach to ≥99.5% of run and pass plays | **Pass**: participation 100% (2016–2025); FTN 99.7% (2022) and 100% (2023–2025). |
| `load` returns nothing known after the moment; deleting later rows changes nothing earlier | **Pass**: unit tests on toy tables, and real 2024 moments checked on every table but `play` (covered by the unit tests). |
| No `INA` visible earlier than 1 hour before kickoff | **Pass**: hidden at kickoff − 61 minutes, all shown at − 59 minutes. |
| Players' passing yards, rushing yards and receptions add up to the team's | **Pass**: 100% of team-games within 1 yard, except one 2012 game, 2 receptions short (F17). |
| No player has more offensive snaps than the team ran | **Not tested directly.** The team totals above and "no inactive took a snap" cover the same ground. |
| `load` under ~2 seconds per season for `player_game` | **Pass**: 0.08–0.13 seconds. |

**Tests:** 154 offline and 85 `local_data` (15 offline and 13 `local_data` new), all passing.

## Deviations from the brief
- **Pre-2016 spine** (F11). From 2016 the spine uses `ACT` and `INA` as agreed. Before 2016 it's every roster row of the team-week, since status there is the player's last of the season. It's still 53 per team-game.
- **Two more leak fixes in `timeline`**, found while building. Playoff games' facts are now known at the start of their own week (F14). And NGS rows of an unfinished season no longer need a fetch time unless they're season totals.
- **`player_play` covers run and pass plays only** (as `cleaning-port`'s `players_on_play`). Special-teams plays aren't in it.
- **Source prefixes.** NGS, PFR and ff_opportunity columns are prefixed (`ngs_rec_`, `pfr_rush_`, `ffo_`), because their names clash with player stats (`receptions`, `carries`). Everything else keeps its nflverse name.
- **The depth part matches on team as well**, and so do the injury and game-status parts: a player traded between two opponents can be on both teams' lists that week (F18).
- **Table checks are plain Polars**, not pandera as `ARCHITECTURE.md` planned: smaller, and one dependency fewer (decision 0008).

## Terms
As in the brief. All are in `docs/GLOSSARY.md`.
- **Table part:** one source's columns for a table, saved with that source's `known_at`, sharing the table's keys.
- **Spine:** the part that decides which rows a table has (`player_game`: the roster).
- **Inactive:** a player on the 53-man roster who isn't dressed for the game (`status` = `INA`, from 2019), named 90 minutes before kickoff.

## Findings
F1–F10 came from the light exploration ([EXPLORATION.md](EXPLORATION.md)). F11–F18 came from the build.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | Player-week is player-game: no team or player has two games in a week. | [EXPLORATION.md](EXPLORATION.md) | strong | table design |
| F2 | Player stats list only 71–73% of the players who played; offensive linemen and long snappers are missing. Snap counts list everyone, from 2013. | [EXPLORATION.md](EXPLORATION.md) | strong | the spine |
| F3 | Weekly rosters mark the dressed (`ACT`) and, from 2019, the game-day inactives (`INA`, 6–7 per team-game, none of whom played). | [EXPLORATION.md](EXPLORATION.md), `local_data` test | strong | the spine, injuries |
| F4 | Leak, fixed: roster `status` is known 90 minutes before kickoff, not at the start of the week. | [EXPLORATION.md](EXPLORATION.md) | strong | rosters |
| F5 | Sparse sources cover part of the player-games (ff_opportunity 21%, PFR 51%, injury reports 15%, NGS 9%). A missing row means "not in that source", not zero. | [EXPLORATION.md](EXPLORATION.md) | strong | every expert |
| F6 | Keys are unique once standardized. A few snap-count pfr ids are missing from the players file (42 in 2024). | [EXPLORATION.md](EXPLORATION.md) | strong | joins |
| F7 | Participation and FTN match 100% of run and pass plays; team stats have 2 rows per game. | [EXPLORATION.md](EXPLORATION.md) | strong | joins |
| F8 | One player-game's sources become known over four weeks, from 2 weeks before kickoff (roster) to after the Super Bowl (participation). | [EXPLORATION.md](EXPLORATION.md) | strong | table design |
| F9 | Scan quirks: NGS is one file for all seasons; `ff_opportunity`'s season is text; participation has no season. | [EXPLORATION.md](EXPLORATION.md) | strong | readers |
| F10 | Tables are small except play-by-play (311 MB of the 390 MB built). | the build | strong | storage |
| F11 | **Before 2016, a weekly roster's `status` is the player's last of the season.** Through 2014, 99.5% of player-teams have one status all season. In 2002–2015, 1,139–2,329 player-games a season with stats were marked reserve, cut or practice squad that week. In 2010, 1,363 of the 2,473 reserve rows played that week. Used as weekly status, it leaks future injured-reserve moves and drops real players from the pre-game spine. | `check_tables.py`, the build | strong | rosters 2002–2015 |
| F12 | **19 played games from 1999–2002 have no team stats**, 16 of them Jacksonville home games in 2001–2002. Their `team_game.stats` columns are empty. | `check_tables.py` | strong | team_game |
| F13 | **The spine holds 99.97–100% of the players who played before the game, every season.** Exception: 2016, at 99.82% (44 players with no roster row). | `local_data` test | strong | player_game |
| F14 | **Leak, fixed: schedules dated playoff matchups to week 1.** Facts are now known at the start of the game's own week for every non-regular-season game. | `timeline` unit test | strong | game, team_game |
| F15 | **2025+ daily depth charts list players on injured reserve:** 16% of labelled rows in 2025, against 1% in 2024. 244 of them hold a "1" label (141 in 2024). They're off the `player_game` spine, but they can push healthy players' slot labels down a number in `player_play` and the `depth` part. **Fixed after the merge:** `drop_off_roster` drops daily-chart rows whose roster status that week isn't `ACT` or `INA` (5,638 rows in 2025, 2,150 in 2026). 12% of the remaining 2025 labels moved up (7% in 2026), and 360 became a "1". | a comparison on 2024–2025; `test_depth_charts` | strong | slot labels 2025→ |
| F16 | **The 2025+ injury files have no `date_modified` column at all**, not just empty values. `standard.injuries` now adds an empty one. | the build | strong | injuries 2025→ |
| F17 | **Box scores agree across sources.** Players' passing yards, rushing yards, receptions and receiving yards sum to the team's in every team-game with team stats, except one 2012 game (2 receptions short). No inactive took a snap. | `local_data` tests | strong | player_game, team_game |
| F18 | **A player can be on both opponents' lists in one week** (traded, 2025 week 10 BUF–MIA). Parts listed by team must match the player's spine team. | the build | strong | joins |

## Pitfalls
- **Status columns that look weekly but aren't** (F11). Check whether a "weekly" field ever changes within a season before trusting it as of a week.
- **A rule that needs a fetch time for rows that don't.** The NGS rule asked for `fetched_at` for the whole unfinished season when only the season totals need it. Mask by the rows that need it.
- **Per-season files can lose columns** (F16, timeline#F15). Building a season at a time found what a full scan hid.
- **Test the joins on traded players** (F18). Keys like `(gsis_id, game_id)` look unique until a player is listed by both teams.

## Not looked at
- **Season, career and event tables** (brief): season totals belong in the reader, cut at the moment, and the event table waits for the first offseason expert. Both are registry ideas now.
- **Live correctness of roster status.** Whether nflverse posts `INA` before kickoff on game day, or only after, can't be checked from history. Collected snapshots (`snapshot("rosters", at)`) can tell, from this season on.
- **Players moving mid-week** (signed Saturday, put on injured reserve Friday). Membership is known at the start of the week, from the end-of-week file. That's a small early leak this project didn't measure.
- **Flexed game times.** `kickoff` in the schedule part is the final time, known from week 1 (timeline's "not looked at").

## Could be improved
1. ~~Drop players on injured reserve from the 2025+ daily depth charts before labelling~~ (F15): done after the merge, and `player_play` and `player_game` rebuilt for 2025→. Weekly charts (through 2024) keep them: their labels are known at the start of the week, before `status`, and they're only 1% of rows.
2. **Build the tables after each refresh** in the daily job, once experts read them.
3. **Season-to-date totals in the reader**, cut at the moment, when the first expert needs them.

## Don't redo
- Don't use pre-2016 roster `status` as a weekly fact (F11).
- Don't give a table one `known_at` per row (decision 0008).
- Don't key a team-listed source on `(gsis_id, game_id)` alone (F18).

## Interface card
Also in `registry.yaml` under `interface`.

| | |
|---|---|
| **Inputs** | The raw nflverse copy through `scan`; `cleaning-port`'s `standard` functions, `players_on_play`, `slot_labels` and depth labels; `timeline`'s calendar and known-at rules |
| **Outputs** | `pcf.data.tables`: `load(name, at, seasons, parts)`, `build(names, seasons)` (`pcf tables build`), `write_parts`. `pcf.data.schemas`: `TABLES`, `check_part`, `check_parts`. Tables: `game` (schedule, pregame, result), `team_game` (schedule, pregame, result, stats), `play` (pbp, participation, ftn), `player_play` (on_field), `player_game` (roster, game_status, injury, depth, stats, snaps, ff_opportunity, ngs, pfr). Files: `data/tables/<table>/<part>/season=YYYY/data.parquet`. |
| **Level of detail** | game; team-game; play; player-play; player-game |
| **Interval** | game, team_game, play 1999→; player_game 2002→; player_play 2016–2025. Each part covers its source's years. |
| **Cadence** | not applicable (rebuilt after each data refresh) |
| **Known at** | Each part has its own `known_at`; `load` returns the spine's as `known_at` and every other part's as `<part>_known_at`. |
| **How to use it** | Experts read through the gateway (`validation-harness`), which wraps `load`. Declare the tables in `inputs`; ask for the parts you need. An empty part column means "not known yet" or "not in that source", never zero. Use `on_roster` and `status` (2019→) for "was the player available"; snaps for "did they play". |
| **Feeds** | `validation-harness` (the gateway), `tag-tables`, every layer-1 expert |

## Open questions for the CEO
- **Approve the merge?** Nothing new to install. To rebuild the tables after a refresh: `uv run pcf tables build` (about 20 seconds).
- No football calls are needed. The F15 follow-up is done.
