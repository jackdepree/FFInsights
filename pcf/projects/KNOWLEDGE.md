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
| `package-scaffold#F7` | ruff 0.17+ also formats Python code blocks inside Markdown, and rewrote a doc when unscoped. Keep ruff limited to `src/` and `tests/`. | strong | [RESULTS.md](package-scaffold/RESULTS.md) |
| `package-scaffold#F8` | `nbstripout --install` writes a repo-wide `*.ipynb` pattern into `.git/info/attributes` that overrides `.gitattributes` and reaches `old/`. Install with `--attributes pcf/.venv/nbstripout-attributes`. | strong | [RESULTS.md](package-scaffold/RESULTS.md) |
| `package-scaffold#F9` | Claude's deny rule `Edit(/old/**)` blocks Edit, Write and NotebookEdit in `old/`, but not shell commands. For those, rule a and `git status` are still the guard. | strong | [RESULTS.md](package-scaffold/RESULTS.md) |
