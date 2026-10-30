# Exploration: Package scaffold (`package-scaffold`)

> A light exploration (infrastructure project): a descriptive profile of the nflverse tables the package will be built around. No signal test.
> Run 2026-10-30 with [`explore/profile_nflverse.py`](explore/profile_nflverse.py), nflreadpy, all seasons.

**Verdict: GO.** Everything loads, the sizes fit a normal PC if play-by-play is handled a season at a time, and the profile found two corrections to `DATA_SOURCES.md` (below).

## The profile

| Table | Rows | Columns | Seasons | Dates | Level of detail | Memory |
|---|---|---|---|---|---|---|
| Play-by-play | 1,298,554 | 372 | 1999–2026 | `game_date` 1999-09-12 → 2026-10-29 | unique on `game_id, play_id` | **2.7 GB** if all loaded at once |
| Schedules | 7,548 | 46 | 1999–2026 | `gameday` through 2027-01-10 (all of 2026 is scheduled) | unique on `game_id` | 2 MB |
| Player stats | 483,680 | 150 | 1999–2026 | — | unique on player, season, week, season type | 346 MB |
| Team stats | 14,747 | 138 | 1999–2026 | — | unique on team, season, week, season type | 8 MB |
| Snap counts | 334,685 | 16 | **2013**–2026 | — | unique on `pfr_player_id, game_id` | 36 MB |
| Expected fantasy points | 114,581 | 159 | 2006–2026 | — | 2,284 duplicates on player and game: rows with no player id | 139 MB |
| Next Gen Stats (receiving) | 15,354 | 23 | 2016–2026 | — | unique on player, season, week, season type | 2 MB |
| PFR advanced (receiving) | 37,450 | 17 | 2018–2026 | — | unique on `pfr_player_id, game_id` | 5 MB |
| Participation | 478,989 | 26 | 2016–2025 (no `season` column) | — | unique on `nflverse_game_id, play_id` | 286 MB |
| FTN charting | 203,406 | 29 | 2022–2026 | `date_pulled` 2024-09-06 → 2026-10-29 | unique on game and play | 12 MB |
| Depth charts | 2,145,193 | 26 | 2001–2024 in `season`; 2025→ by `dt` only | `dt` 2025-08-03 → 2026-10-30 | two formats (below) | 190 MB |
| Injuries | 93,169 | 17 | 2009–2026 (`season` stored as a decimal) | `date_modified` empty from 2025 | 4 duplicates on player, season, week, game type | 10 MB |
| Weekly rosters | 926,241 | 36 | 2002–2026 | — | 17,515 duplicates on player, season, week: the same player listed twice on one team (a few traded mid-week) | 236 MB |
| Players | 24,863 | 39 | — | — | unique on `gsis_id` | 6 MB |
| Id map | 12,534 | 35 | — | — | — | 3 MB |
| ECR (`type="all"`) | 1,873,627 | 24 | — | `scrape_date` 2019-12-27 → 2026-10-30 | — | 512 MB |
| Combine | 8,968 | 18 | 2000–2026 | — | — | 1 MB |
| Draft picks | 12,927 | 36 | 1980–2026 | — | unique on season and pick | 2 MB |
| Trades | 4,975 | 11 | 2002–2026 | `trade_date` 2002-03-04 → 2026-04-17 | — | <1 MB |
| Contracts | 53,522 | 26 | — | — | — | 77 MB |
| Officials | 22,012 | 9 | 2015–2026 | — | — | 1 MB |

Play-by-play has about 46,000–50,000 plays per season (2026 so far: 18,926).

## What it means for the scaffold

- **Size:** everything together is about 5 GB in memory, more than half of it play-by-play. On disk (Parquet) it's much smaller. **Config and the data layer must work a season at a time** (ARCHITECTURE.md already partitions by season).
- **Ids aren't uniform** (CONVENTIONS.md): `player_id` vs `gsis_id` vs `player_gsis_id` vs `pfr_player_id`, and `game_id` vs `nflverse_game_id`. The data layer renames them.
- **Types aren't uniform:** injuries store `season` as a decimal, and participation has no `season` column at all.

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **FTN's `date_pulled` is not when the data was first available.** Whole seasons were re-pulled later: all of 2022–23 show 2024-09-06, and 2025 shows 2026-09-22. Using it as `known_at` would hide FTN from every backtest. For history, use game date plus FTN's lag (about 1–2 weeks). Use `date_pulled` only for our own live snapshots. | strong |
| F2 | **Snap counts start in 2013, not 2012.** | strong |
| F3 | **Depth charts come in two formats:** weekly rows with `season` and `week` through 2024, and daily snapshots with only `dt` from 2025 (1.28 million of the 2.1 million rows). The old `clean_depth_charts` handles only the first. | strong |
| F4 | **Duplicates to handle at ingest:** expected-fantasy-points rows with no player id, weekly-roster players listed twice in one week, and 4 injury duplicates. | strong |
| F5 | **Injuries have no `date_modified` from 2025.** Our known-at rule (noon ET the day before kickoff) doesn't depend on it, so nothing changes. | strong |
| F6 | **Loading all play-by-play at once takes about 2.7 GB of memory** (1.3 million plays × 372 columns). Work a season at a time. | strong |

F1 and F2 are corrected in `DATA_SOURCES.md` on this branch. F3 and F4 go to `data-layer` and `cleaning-port`.

## Next step
The [brief](BRIEF.md).
