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
