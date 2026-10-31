# Results: NFL timeline and known-at timestamps (`timeline`)

> An infrastructure project: no model, so no MLflow experiment, ladder or vault.

**Date:** 2026-10-31 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** none

## In short
PCF now has one calendar and a `known_at` rule for every nflverse dataset (`pcf.data.timeline`):
- **The calendar:** every game from 1999 with its kickoff in UTC, week windows that never overlap, and the offseason phases from a small dates file (CEO decision 1A).
- **`phase_at`:** says which season, phase and week any moment falls in. Today (2026-10-31) is 2026, regular season, week 8.
- **The injury leak is fixed.** The old rule ("noon ET the day before") was too early for 6–7% of 2021–2024 reports.
- **2025+ depth charts now use the last snapshot before kickoff** instead of the start of game day.
- Every test in the brief passes. One planned piece, roster cuts, isn't in the dates file (see Deviations).

| Test from the brief | Result |
|---|---|
| Every game 2000–2026 has a kickoff | **Pass.** `gametime` is published for every game from 2000; 1999's 259 games get 1 PM Eastern. |
| On 2011–2025, the first play comes within 30 minutes of kickoff for ≥99% of games | **Pass** (4,096 games; the misses are weather delays and play-by-play clock errors, F1–F2). |
| Week windows cover every game, never overlap, in order | **Pass**, every season 1999–2026. |
| Every known-at rule gives UTC, timezone-aware, non-null values on its full dataset | **Pass** for all 36 datasets (`local_data`). |
| No injury report is known before its `date_modified` | **Pass.** And 99.9%+ are known before their kickoff. |
| Future deletion changes no earlier `known_at` | **Pass** (offline tests on week windows and rules). |
| Offseason phases in order every year, draft days include the busiest pick-trade day | **Pass.** Order holds every year except 2011, where the lockout put free agency after the draft (handled). All 24 drafts 2002–2025 hold that year's busiest day for trading its picks (F13). |

**Tests:** 136 offline and 71 `local_data` (43 of them new), all passing.

## Deviations from the brief
- **No roster-cut phase.** The brief listed "camp, final roster cuts". Neither has a league-wide date in the sources I checked (camp opens team by team). The preseason phase runs from the first preseason game to week 1.
- **The combine is an event, not a phase.** It overlaps the offseason, and in some years the start of free agency. Its dates are in the file for the combine known-at rule.
- **Blank dates where no public source gave one** (F14). League-year start is missing for 2003–2009, and combine dates exist for only 6 years. A blank merges its phase into the one before. The combine rule falls back to the first day of the draft, which is later and so safe.
- **Week 1 starts two days before its first game day** (the Tuesday before a Thursday opener). There's no previous week to start from.
- **Draft picks are known the day after the draft ends**, not the day of each pick. It's simpler and leans late.

## Terms
As in the brief, plus two. All are in `docs/GLOSSARY.md`.
- **Kickoff:** a game's scheduled start in UTC (`gameday` + `gametime`, Eastern time).
- **Week window:** a season-week's span, from midnight Eastern after the previous week's last game day to midnight after its own last game day. Week 1 starts two days before its first game.
- **Phase:** `offseason`, `free_agency`, `draft`, `after_draft`, `preseason`, `regular_season`, `postseason`. Offseason phases belong to the coming season.
- **Known-at rule:** the function in `pcf.data.timeline.RULES` that gives a dataset's rows their `known_at`.
- **Offseason dates file** (new): `src/pcf/data/timeline/offseason_dates.csv`, one row per league year, typed from public sources and extended each spring.

## Findings
F1–F9 came from the light exploration ([EXPLORATION.md](EXPLORATION.md)). F10–F15 came from the build.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | Schedules' `gametime` is Eastern for every game, international ones included. The first play comes a median 2 minutes after kickoff. 1999 has no times. | [EXPLORATION.md](EXPLORATION.md), `local_data` test | strong | every kickoff |
| F2 | Actual starts can be hours late (weather), and play-by-play's clock is sometimes wrong by 3–12 hours. Use the scheduled kickoff. | [EXPLORATION.md](EXPLORATION.md) | strong | timing |
| F3 | Weeks never overlap, with at least 2 days between them, so contiguous week windows work. | [EXPLORATION.md](EXPLORATION.md), `local_data` test | strong | week windows |
| F4 | "Noon ET the day before kickoff" was too early for 6–7% of 2021–2024 injury reports (mostly Thursday games). `date_modified` is the real time; without it, kickoff − 12 h leaves 0.06% later. | [EXPLORATION.md](EXPLORATION.md) | strong | injuries |
| F5 | 2025+ depth-chart snapshots are taken in the early morning Eastern, so every game has a game-day chart before kickoff. | [EXPLORATION.md](EXPLORATION.md) | strong | depth charts |
| F6 | nflverse has almost no offseason dates (draft and combine have a year only). Trades are dated. | [EXPLORATION.md](EXPLORATION.md) | strong | offseason |
| F7 | The trades file stops at 2026-04-17: no 2026 draft-day or in-season trades. | [EXPLORATION.md](EXPLORATION.md) | strong | trades |
| F8 | Weekly rosters cover weeks 1–22, with no offseason weeks. | [EXPLORATION.md](EXPLORATION.md) | strong | rosters |
| F9 | The ECR archive has 371 dated scrapes, 2019-12 → today. | [EXPLORATION.md](EXPLORATION.md) | strong | ECR |
| F10 | **Kickoff instead of the start of game day changes 6.1% of 2025+ depth labels.** It adds 1,159 player-weeks listed only on the game-day chart (for example, game-day elevations) and drops 113. | a comparison on 2025–2026 | strong | slot labels 2025→ |
| F11 | **Next Gen Stats numbers the Super Bowl one past the schedule** (22 through 2020, 23 from 2021), because it counts the bye week. | the NGS rule | strong | NGS joins |
| F12 | **Officials keep the ids of 4 games that were moved or canceled** (three 2021 COVID postponements, 2022 BUF at CIN). They use their week's last kickoff. | the officials rule | strong | officials |
| F13 | **Every draft 2002–2025 holds that year's busiest day for trading its picks.** It cross-checks the dates file against our own data. | `local_data` test | strong | offseason dates |
| F14 | **Public sources date the offseason unevenly.** Draft days and Hall of Fame Games: every year. League-year start: 2002 and 2010→ only. Combine: 6 years. 2011's lockout put free agency after the draft; 2020 had no preseason; 2021 had no combine. | the dates file | strong | offseason experts |
| F15 | **The 2025+ depth-chart files have no `season` or `week` column**, only `dt`. Rules and joins can't assume them. | the depth-chart rule | strong | depth charts 2025→ |

## Pitfalls
- **A wrong test expectation looks like a bug.** Four test failures in the build were my own arithmetic about week windows, not code errors. Write expected times from the rule, not from memory.
- **Two formats under one dataset name.** A rule that works on a full scan (all seasons, with `season`) can fail on 2025+ files alone (F15). Test rules on each format.
- **Joins that fan out.** A team appearing twice in one week would silently duplicate injury rows. The rule now refuses that schedule.

## Not looked at
- **When each season's schedule was released**, and flexed game times. `facts_known_at` uses week 1's start, and the latest file has only the final times.
- Known-at rules for non-nflverse sources: collectors stamp their own fetch time.
- The gateway itself (`validation-harness`).

## Could be improved
1. **Fill the blank dates** (league year 2003–2009, combine 2004–2012 and 2016–2025) from a better source, such as NFL.com press releases or the NFL Record & Fact Book, if an offseason expert needs them.
2. **Per-pick draft timing** (round 1 on day 1, and so on), if a model predicts during the draft.
3. **Schedule release dates**, read from `snapshot()` history once a release happens on our watch (May 2027).

## Don't redo
- Don't use play-by-play's `time_of_day` or `start_time` as kickoff (F2).
- Don't use "noon ET the day before" for injuries (F4).
- Don't infer draft dates from trades alone: the first day is often quiet, and the trades file goes stale (F6, F7).

## Interface card
Also in `registry.yaml` under `interface`.

| | |
|---|---|
| **Inputs** | Standardized schedules, the offseason dates file, and each dataset's own timestamps (`date_modified`, `dt`, `trade_date`, `scrape_date`) |
| **Outputs** | `pcf.data.timeline`: `calendar(schedules)` → a `Calendar` with `games` (kickoff), `weeks` (windows), `phases` and `offseason`. `phase_at(cal, moment)`. `team_kickoffs(games)`. `known_at(dataset, df, cal, fetched_at)` and `RULES` (all 36 datasets). `check_known_at(df, not_before)`. |
| **Level of detail** | games, season-weeks, phases; rules keep each dataset's own rows |
| **Interval** | 1999 → the current schedule |
| **Cadence** | not applicable (pure functions; rebuild the calendar after each schedules refresh) |
| **Known at** | This project defines it. Schedules get three columns: `facts_known_at`, `lines_known_at`, `known_at`. |
| **How to use it** | Build the calendar once from `standard.schedules(...)`. Add `known_at` to every table with `known_at(dataset, df, cal)`. Pass `fetched_at` for state files (players, rosters, contracts, ids, teams) and for season totals of an unfinished season. Add the next league year's row to the dates file each spring. |
| **Feeds** | `grain-tables`, `validation-harness` (the gateway), `cleaning-port` (depth-chart kickoffs), offseason experts |

## Open questions for the CEO
- **Approve the merge?** Nothing new to install. From February 1 each year, one test fails until that year's row is added to the dates file. I can do it when you ask, or you can type the five dates yourself.
- No football calls are needed.
