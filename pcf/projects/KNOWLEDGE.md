# Knowledge index

> Every finding from every project, in one place. **Read this before helping write any brief**, so new work builds on what we know instead of repeating it.
> Findings are cited as `<project>#F<n>`. Each row links to its source. Kept by hand until `registry-tooling` generates it from the RESULTS.md files.
> Findings from an exploration (not yet a finished project) are marked *(exploration)*: useful, but less tested.

| Finding | Claim | Confidence | Source |
|---|---|---|---|
| `odds-collection#F1` *(exploration)* | ESPN's "current" prop line on a completed game is the pre-game closing line, not an in-game value ("current" is only 1–12% closer to results than "open"). Its `lastUpdated` is not when the line was set. | suggestive | [EXPLORATION.md](odds-collection/EXPLORATION.md) |
| `odds-collection#F2` *(exploration)* | ESPN has no prop lines for 2025 weeks 14–22 (the ESPN BET → DraftKings switch). Exclude those weeks from prop backtests. | strong | [EXPLORATION.md](odds-collection/EXPLORATION.md) |
| `odds-collection#F3` *(exploration)* | nflverse schedule spreads and totals sit near the close (matching ESPN's close in 45–84% of games), so treat them as known at kickoff. | strong | [EXPLORATION.md](odds-collection/EXPLORATION.md), [DATA_SOURCES.md](../docs/DATA_SOURCES.md) |
| `odds-collection#F4` *(exploration)* | ESPN's 2022 game-line format differs from later seasons. The parser needs a fix before 2022 game lines are used. | strong | [EXPLORATION.md](odds-collection/EXPLORATION.md) |
| `package-scaffold#F1` *(exploration)* | FTN's `date_pulled` records the latest re-pull, not first availability (2022–23 all show 2024-09-06). For history, FTN is known at kickoff + 14 days. | strong | [EXPLORATION.md](package-scaffold/EXPLORATION.md) |
| `package-scaffold#F2` *(exploration)* | Snap counts start in 2013, not 2012. | strong | [EXPLORATION.md](package-scaffold/EXPLORATION.md) |
| `package-scaffold#F3` *(exploration)* | Depth charts switch format in 2025: daily `dt` snapshots with no `season` or `week`. The old `clean_depth_charts` handles only the weekly format. | strong | [EXPLORATION.md](package-scaffold/EXPLORATION.md) |
| `package-scaffold#F4` *(exploration)* | Duplicates to handle at ingest: expected-fantasy-points rows with no player id, weekly-roster players listed twice in a week, 4 injury rows. | strong | [EXPLORATION.md](package-scaffold/EXPLORATION.md) |
| `package-scaffold#F5` *(exploration)* | Injuries have no `date_modified` from 2025. The known-at rule (noon ET the day before kickoff) doesn't depend on it. | strong | [EXPLORATION.md](package-scaffold/EXPLORATION.md) |
| `package-scaffold#F6` *(exploration)* | Loading all play-by-play at once takes about 2.7 GB of memory (1.3 million plays × 372 columns). Work a season at a time. | strong | [EXPLORATION.md](package-scaffold/EXPLORATION.md) |
| `data-layer#F1` *(exploration)* | nflverse re-uploads past seasons months later (play-by-play 2020/2024/2025 in Aug 2026; all player and team stats rebuilt 2026-08-13). A refresh must check every file, not just the current season. | strong | [EXPLORATION.md](data-layer/EXPLORATION.md) |
| `data-layer#F2` *(exploration)* | A 2023 play-by-play re-upload changed no modelling column (EPA, WPA, yards, air yards, player ids identical on all 49,665 plays). Only surface, weather, stadium, coach, play text and ~6 tackle credits changed. | suggestive | [EXPLORATION.md](data-layer/EXPLORATION.md) |
| `data-layer#F3` *(exploration)* | Change detection is cheap: ~22 GitHub API calls give every nflverse file's size and upload time; dynastyprocess files have ETags. All of nflverse is about 830 MB. | strong | [EXPLORATION.md](data-layer/EXPLORATION.md) |
| `data-layer#F4` *(exploration)* | Next Gen Stats, players, contracts, schedules and ECR are single all-season files re-uploaded daily, so they're rewritten whole. | strong | [EXPLORATION.md](data-layer/EXPLORATION.md) |
| `data-layer#F5` *(exploration)* | nflreadpy has its own cache (memory, 24 h) and reads `NFLREADPY_*` settings from a `.env` in the working folder. | strong | [EXPLORATION.md](data-layer/EXPLORATION.md) |
| `package-scaffold#F7` | ruff 0.17+ also formats Python code blocks inside Markdown, and rewrote a doc when unscoped. Keep ruff limited to `src/` and `tests/`. | strong | [RESULTS.md](package-scaffold/RESULTS.md) |
| `package-scaffold#F8` | `nbstripout --install` writes a repo-wide `*.ipynb` pattern into `.git/info/attributes` that overrides `.gitattributes` and reaches `old/`. Install with `--attributes pcf/.venv/nbstripout-attributes`. | strong | [RESULTS.md](package-scaffold/RESULTS.md) |
| `package-scaffold#F9` | Claude's deny rule `Edit(/old/**)` blocks Edit, Write and NotebookEdit in `old/`, but not shell commands. For those, rule a and `git status` are still the guard. | strong | [RESULTS.md](package-scaffold/RESULTS.md) |
| `data-layer#F6` | Without a token, GitHub counts a "not modified" (304) reply against the 60-an-hour limit (measured). ETag caching saves bandwidth, not calls. | strong | [RESULTS.md](data-layer/RESULTS.md) |
| `data-layer#F7` | A release's inline asset list is complete (554 inline = 554 paged). A full nflverse check is 22 API calls. | strong | [RESULTS.md](data-layer/RESULTS.md) |
| `data-layer#F8` | The unauthenticated allowance ran out sooner than our own calls explain (it seems shared). Plan for fewer than 60 an hour; a token fixes it. | suggestive | [RESULTS.md](data-layer/RESULTS.md) |
| `data-layer#F9` | nflreadpy loaders return published files unchanged, except schedules: it nulls `roof` values outside dome/outdoors/closed/open (26 games have `""`). `cleaning-port` must do the same. | strong | [RESULTS.md](data-layer/RESULTS.md) |
| `data-layer#F10` | All of nflverse is 786 MB (408 files); play-by-play is 496 MB of it. | strong | [RESULTS.md](data-layer/RESULTS.md) |
| `data-layer#F11` | State files change within minutes (a schedule moneyline moved between runs 14 minutes apart). A change-log entry was 15 KB against a 355 KB full copy. | strong | [RESULTS.md](data-layer/RESULTS.md) |
| `data-layer#F12` | A refresh stopped mid-way heals on the next run, fetching nothing twice. | strong | [RESULTS.md](data-layer/RESULTS.md) |
| `data-layer#F13` | 278 of 408 nflverse files (all uploaded before July 2025) have no SHA-256 on GitHub. They're versioned by upload time and size, and downloads are checked by size. | strong | [RESULTS.md](data-layer/RESULTS.md) |
| `cleaning-port#F1` | The old `pivot_long_both_sides` has two versions; the later one (unmatched players → `special`) is the reference. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F2` | The old slot functions run on our raw copy for 2016–2024 once participation is joined to play-by-play and `play_id` is cast to one type (float in older play-by-play). | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F3` | The old slot functions fail on 2025+ (daily depth-chart snapshots). `daily_depth_rows` handles them. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F4` | 4–6% of on-field players aren't on that week's depth chart; the old code labels them `special`, so old `special` is mostly real WRs, CBs and DL. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F5` | 2016 participation lists 11 players a side on only 87% of run and pass plays (99.9% in 2020 and 2024). | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F6` | Depth charts and play-by-play number playoff weeks the same way; the Super Bowl bye week has no number. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F7` | The old depth order depends on which rows are loaded and averages them in file order. Golden tests must feed both versions identical input. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F8` | The old Context and Fatigue data prep is expert features, not cleaning, and `rolling_pass_over_expected` includes the current play (a leak). | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F9` | The legacy copy needs pandas, NumPy and pyarrow (now dependencies). | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F10` | The old code cuts player lists at 11 a side and turns padding into a player called `'None'`. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F11` | nflverse sources disagree on team codes. Play-by-play uses each franchise's current code for every season (LV, LAC, LA); others use OAK, SD, STL, ARZ, BLT, CLV, HST, LAR, LVR, JAC. Recode at ingest (`standard.team`), or joins on `team` drop 3–6% of 2016–2019 rows. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F12` | The old depth order leaks later weeks: removing weeks 6+ changes 19–22% of its weeks 1–5 labels. Don't train on old slot labels. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F13` | With the step-by-step fallback, 94–99% of player-plays are labelled from that week's chart, at most 0.11% are `unknown`, `special` is under 0.03%, and no label repeats on one side of a play. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F14` | QB1 is the season's established starter, so ~17% of offense plays have no QB1 (a backup in, or a new starter whose average hasn't caught up). At least one QB is on the field on 99%+ of plays. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F15` | 2025+ daily depth charts: 27,764 rows have no `gsis_id`. Games after the newest snapshot get a chart only if they're the team's next game. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F16` | Participation sometimes lists one player twice on one side (373 in 2019); keep the first. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F17` | Map snap counts' PFR id to `gsis_id` through nflverse's `players` file (99.93%), not dynastyprocess's id map (82%). | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `cleaning-port#F18` | `player_stats` has an empty row per season-week (id `"0"` or null); `ff_opportunity` one repeated player-game (2013). Both dropped in `standard`. | strong | [RESULTS.md](cleaning-port/RESULTS.md) |
| `timeline#F1` | Schedules' `gametime` is US Eastern for every game, international ones included; the first play comes a median 2 minutes after kickoff. 1999 has no times. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F2` | Actual starts can be hours late, and play-by-play's clock is sometimes wrong by 3–12 hours. Use the scheduled kickoff. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F3` | NFL weeks never overlap (at least 2 days apart), so contiguous week windows cover every moment of a season. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F4` | "Noon ET the day before kickoff" was too early for 6–7% of 2021–2024 injury reports (mostly Thursday games). Use `date_modified`; without it, kickoff − 12 h. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F5` | 2025+ depth-chart snapshots are taken in the early morning Eastern, so each game has a game-day chart before kickoff. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F6` | nflverse has almost no offseason dates (draft and combine: year only). Trades are dated. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F7` | The nflverse trades file stops at 2026-04-17: no 2026 draft-day or in-season trades. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F8` | Weekly rosters cover weeks 1–22 only, with no offseason weeks. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F9` | The ECR archive has 371 dated scrapes from 2019-12. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F10` | Using kickoff instead of the start of game day changes 6.1% of 2025+ depth labels (+1,159 game-day listings). | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F11` | Next Gen Stats numbers the Super Bowl one past the schedule (22 through 2020, 23 from 2021). | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F12` | Officials keep the ids of 4 moved or canceled games (2021 COVID postponements, 2022 BUF at CIN). | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F13` | Every draft 2002–2025 holds that year's busiest day for trading its picks: a check of the dates file against our data. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F14` | Public sources date the offseason unevenly: draft and Hall of Fame Game every year, league-year start 2002 and 2010→, combine 6 years. 2011 had free agency after the draft. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `timeline#F15` | The 2025+ depth-chart files have no `season` or `week` column, only `dt`. | strong | [RESULTS.md](timeline/RESULTS.md) |
| `grain-tables#F1` | Player-week is player-game: no team or player has two games in one week. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F2` | Player stats list only 71–73% of the players who played (no offensive linemen or long snappers). Snap counts list everyone, from 2013. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F3` | Weekly rosters mark the dressed (`ACT`) and, from 2019, the game-day inactives (`INA`, 6–7 per team-game, none of whom played). | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F4` | Roster `status` is known 90 minutes before kickoff, not at the start of the week: now `status_known_at` = kickoff − 1 hour. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F5` | Sparse sources cover part of the player-games (ff_opportunity 21%, PFR 51%, injury reports 15%, NGS 9%). A missing row means "not in that source", not zero. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F6` | Player-game and play keys are unique once standardized; a few snap-count pfr ids are missing from the players file. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F7` | Participation and FTN match 100% of run and pass plays; team stats have 2 rows per game. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F8` | One player-game's sources become known over four weeks, from the roster (before the week) to participation (after the Super Bowl). Hence one `known_at` per source, not per row. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F9` | `scan` doesn't filter NGS by season (one file); `ff_opportunity`'s season is text; participation has no season. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F10` | The built tables are 390 MB, 311 MB of it play-by-play. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F11` | Before 2016 a weekly roster's `status` is the player's last of the season (a December IR move shows from week 1). Don't use it as a weekly fact. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F12` | 19 played games from 1999–2002 have no team stats, 16 of them Jacksonville home games in 2001–2002. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F13` | The roster spine holds 99.97–100% of the players who played before the game, every season except 2016 (99.82%). | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F14` | Schedules dated playoff matchups to week 1. Their facts are now known at the start of their own week. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F15` | 2025+ daily depth charts list players on injured reserve (16% of labelled rows, 1% in 2024), which can push healthy players' slot labels down. Fixed: `drop_off_roster` keeps only `ACT` and `INA` players (and those with no roster row). | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F16` | The 2025+ injury files have no `date_modified` column at all. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F17` | Players' passing, rushing and receiving totals sum to the team's in every team-game with team stats but one. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
| `grain-tables#F18` | A player traded between two opponents can be on both teams' lists that week; team-listed parts must match on team too. | strong | [RESULTS.md](grain-tables/RESULTS.md) |
