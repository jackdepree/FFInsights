# Exploration: Tables at every level of detail (`grain-tables`)

> A light exploration (infrastructure project). It asks four things. Which level of detail does each source come at, and do the keys line up? Who belongs in a player-game table? How well does each source join to it? And how far apart do the sources' known-at times sit within one game?
> Run on 2026-10-31 with [`explore/profile_inputs.py`](explore/profile_inputs.py) on our raw nflverse copy, using the `cleaning-port` standard functions and the `timeline` known-at rules. Seasons 2024 and 2018, plus 2016 at play level.

**Verdict: GO.** Every source joins cleanly on shared keys (`game_id`, `play_id`, `gsis_id`). Play-level sources match 100% of run and pass plays, and team stats give exactly two rows per game. Three things shape the design:
- player-week and player-game are the same thing (F1);
- no single source lists everyone who belongs in player-game (F2–F3);
- one game's sources become known anywhere from 2 weeks before kickoff to 2 weeks after it (F8).

The profile also turned up a leak in the weekly-roster known-at rule (F4).

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **Player-week is player-game.** No team plays twice in a week (1999–2026), and none of player_stats' 483,680 rows has a second game in its player's week. A separate `player_week` table would copy `player_game`. | strong |
| F2 | **Player stats cover only 71–73% of the players who played.** Snap counts list 26,572 player-games with a snap in 2024; player_stats has 18,961. The missing 27% are mostly offensive linemen, long snappers, and defenders and tight ends with no stat that game. Stats without a snap count: 14 in 2024, 0 in 2018. Snap counts start in 2013. | strong |
| F3 | **Weekly rosters list everyone dressed (`ACT`), and from 2019 the game-day inactives (`INA`).** In 2024, 26,565 of 26,572 player-games with a snap belong to `ACT` players; the other 7 have no roster row. 804 `ACT` player-games (3%) had no snap: backup QBs and the like. `INA` runs 6–7 per team-game, and none of them played. Before 2019 there's no `INA`: inactives aren't marked. Other statuses: practice squad (`DEV`), reserve lists (`RES`), cut, retired. | strong |
| F4 | **Leak: roster `status` is known about 90 minutes before kickoff, not at the start of the week.** Our rule dates weekly rosters to the start of their week (timeline). That's right for who is on the team, but from 2019 `status` holds the game-day inactive list, which teams turn in 90 minutes before kickoff. A model reading it on Wednesday would know Sunday's inactives. 969 of 2024's 3,611 inactives were listed Out or Doubtful; the rest were healthy scratches, which nothing else reveals before game day. | strong |
| F5 | **Sparse sources cover only some player-games** (share of player-games that played, 2024 / 2018): ff_opportunity 21% / 22% (offensive skill players), PFR weekly 51% / 52% (players with a pass, rush, catch or defensive stat), injury reports 16% / 14%, NGS 9% / 10% (only players who qualify that week). A missing row means "not in that source", not zero. | strong |
| F6 | **Keys are unique once standardized.** Unique keys: `(gsis_id, game_id)` in player_stats, ff_opportunity and snap counts (after mapping pfr→gsis through the players file), and `(game_id, play_id)` in play-by-play. 42 snap-count rows in 2024 (0 in 2018) have a pfr id the players file doesn't know. | strong |
| F7 | **Play level joins perfectly.** Participation matches 100% of run and pass plays in 2016 and 2024, and FTN charting (2022 on) 100% in 2024, with no FTN row missing from play-by-play. Team stats have exactly 2 rows per game, matching the schedule's 570 team-games in 2024. | strong |
| F8 | **One player-game's sources become known over four weeks.** In hours after the week's first kickoff (2024): roster 330 to 37 before; injury report up to 98 before; stats and snaps +24; NGS +33 to +155; PFR +197 to +275; FTN +336 (14 days); participation after the Super Bowl. So a single `known_at` per row would either hold box scores back 2 weeks or leak FTN and PFR. | strong |
| F9 | **Three scan quirks.** `scan("ngs_*", seasons)` returns every season (NGS is one file), so a season filter is needed. `ff_opportunity` stores `season` as text. Participation has no `season` column. | strong |
| F10 | **Sizes are small, except play-by-play.** A season of play-by-play is 49,492 rows × 372 columns, 109 MB in memory; the raw copy is 496 MB across all seasons. Player stats: 150 columns. Everything else is under 25 MB raw in total per source. Work a season at a time; nothing needs a database. | strong |

## What it means for the brief
- **Fold `player_week` into `player_game`** (F1).
- **The player-game spine needs a choice** (F2, F3): the roster (everyone who dressed or was inactive), only the players who played, or player_stats alone.
- **Each source keeps its own known-at** (F8). The question is how the tables hold them; this is a technical call for the brief to state.
- **Fix the roster rule** (F4): split membership (week start) from game status (before kickoff).
- **Handle the scan quirks in the table builders** (F9).

## Next step
The [brief](BRIEF.md).
