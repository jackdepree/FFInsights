# Brief: NFL timeline and known-at timestamps (`timeline`)

> An infrastructure project: no model, but one scope call for the CEO (end of page). Light exploration: [EXPLORATION.md](EXPLORATION.md).

**Status:** agreed (2026-10-31): CEO chose 1A · **Layer:** 0, data (Phase 0) · **Cadence:** — (pure functions over schedules and each source's own timestamps)

## The question
When did each thing in football happen, and when could PCF have known about it? One calendar covers games, weeks and offseason phases, and every row of every source gets a `known_at` timestamp.

## Why it matters
Rule c (no information from after kickoff) is only as good as `known_at`. The tables (`grain-tables`) and the `as_of` gateway (`validation-harness`) both wait on this project. Without it, every table would carry a guessed timestamp. The exploration already found one rule that leaks: the injury rule is too early for about 6% of recent reports (F4).

## Terms
- **Standard terms used:** known_at, as_of, gateway, leakage, snapshot, state source and history source, cadence. See `docs/GLOSSARY.md`.
- **New terms:**
  - **Kickoff:** the scheduled start of a game in UTC, from schedules (`gameday` + `gametime`, which is US Eastern time: F1). Not the actual start, which can be hours late (F2).
  - **Week window:** the span a season-week covers, from the day after the previous week's last game to the end of its own last game day (F3). Rows "known at the start of the week" use its first moment.
  - **Phase:** a named stretch of the calendar: regular season, postseason, and offseason phases (league year and free agency, combine, draft, camp, preseason, roster cuts). Offseason phases depend on question 1.
  - **Known-at rule:** the function that gives a source's rows their `known_at`. Each rule in `DATA_SOURCES.md` becomes one.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `data-layer` | `scan`, `snapshot`, raw schedules and every source | The inputs |
| `cleaning-port` | `standard.schedules` (team codes), `game_day_cutoffs` | Clean input. Its stand-in cutoff gets replaced by kickoff (F5). |
| `package-scaffold#F1`, `#F5` | FTN's `date_pulled` isn't first availability; injuries lose `date_modified` from 2025 | Two rules that can't trust a column |
| `odds-collection#F3` | Schedule lines sit near the close | Lines in schedules are known at kickoff |
| `data-layer#F11` | Schedules change within minutes | Flexed game times are only in the latest file, and in `snapshot()` from October 2026 |
| `timeline#F1`–`#F9` (exploration) | Kickoff, week windows, the injury leak, missing offseason dates | The plan below |

**Already tried:** nothing. `old/` worked by season and week only, with no timestamps.

## Assumptions
- **Every game uses its final scheduled kickoff.** A flexed game's time changes about 12 days before, and history keeps only the final time. That affects "is it a prime-time game" as a feature two weeks out. It doesn't affect `known_at`, which only needs the time the game was played.
- **1999 has no game times** (F1). Its games get 1:00 PM Eastern, the most common slot. Little uses 1999: depth charts start in 2001 and weekly rosters in 2002.
- **Injury reports** (F4): `known_at` is `date_modified` where it exists, since that's when the report was last changed. Where it doesn't (2009 and 2025+), it's **kickoff − 12 hours**. Only 0.06% of 2010–2024 reports were modified later than that. This replaces "noon ET the day before" in `DATA_SOURCES.md`, which leaks on 6–7% of rows in 2021–2024.
- **Every other rule stays as `DATA_SOURCES.md` has it.** Where a source has its own timestamp (`dt`, `scrape_date`, `trade_date`), a test checks that the rule is never earlier than that timestamp.
- **Times are UTC and timezone-aware** (`CONVENTIONS.md`). Day-based rules ("kickoff + 1 day", "the start of the week") are worked out in Eastern time, the league's own clock, then converted to UTC.

## Goals: what gets built
1. **Games:** one row per game, 1999→: `game_id`, season, week, `game_type`, kickoff (UTC), from schedules.
2. **Week windows:** one row per season-week: start and end (UTC), and its phase (regular season or postseason).
3. **Offseason phases:** depending on question 1.
4. **`phase_at(moment)`:** which season, week and phase a moment falls in. The gateway uses it to know what "now" means.
5. **Known-at rules** in `pcf.data.timeline`: one function per source in the nflverse catalog, each adding a `known_at` column. The injury rule is fixed (assumption above).
6. **Depth-chart cutoff at kickoff:** `cleaning-port`'s daily-snapshot cutoff moves from the start of game day to kickoff (F5). Measure how many labels change.
7. **A `known_at` sanity check** (leakage check 2 in `ARCHITECTURE.md`): no missing or timezone-less `known_at`, and no row "known" before its event happened (a stat known before its game).

**Not in this project:** the `as_of` gateway itself (`validation-harness`), the tables (`grain-tables`), and known-at rules for non-nflverse sources (each collector stamps its own fetch time already).

## Tests
- **Success looks like:**
  - Every game from 2000 to 2026 has a kickoff. On 2011–2025, play-by-play's first play comes within 30 minutes of it for at least 99% of games (F1).
  - Week windows cover every game, never overlap, and are in order.
  - Every known-at rule gives UTC, timezone-aware, non-null values on its full dataset, and is never earlier than the source's own timestamp where one exists.
  - No injury report is "known" before its `date_modified`.
  - Future deletion: deleting later rows changes no earlier `known_at`.
  - Offseason phases (if question 1 is A) are in order every year (combine → free agency → draft → camp → cuts → week 1), and the draft days include the busiest pick-trade days (F6).
- **Failure looks like:** a rule that can't be made both safe (never early) and useful (not days late), or offseason phases that can't be dated.

## Inputs and outputs
- **Inputs:** schedules, and each source's own timestamp columns (injuries, depth charts, trades, ECR). For question 1A, a small file of offseason dates.
- **Outputs:** pure functions in `pcf.data.timeline`: `games`, `weeks`, `phases`, `phase_at`, one known-at function per source, and the sanity check. No saved tables. `grain-tables` saves them.

## How it will be used
`grain-tables` adds `known_at` to every table with these rules. The gateway (`validation-harness`) uses `phase_at` and `known_at` to show a model only what was known at a moment. The `offseason_events` experts (prospects, free agency, the draft) use the offseason phases.

## Decisions (CEO, 2026-10-31)
- **1A:** offseason dates come from a small dates file kept in the repo, filled once and checked against our data, then one row added each spring (a test fails from February if it's missing).

## Questions for the CEO (answered above)
1. **Where should the offseason dates come from?**
   - **Why it matters:** `offseason_events` experts update at the combine, free agency, trades and the draft. To keep their backtests honest, PCF needs to know, for example, that free agency comes before the draft in every year. nflverse has no such dates (F6).
   - **A. A small dates file kept in the repo.** *(Recommended.)*
     - One row per year from 2002: league year start (free agency), combine, draft days, camp, final roster cuts.
     - I fill it once from public sources and check it against our data (draft days against the trade spikes, week 1 against schedules).
     - Then it's one row a year, added each spring. A test fails from February if next year's row is missing, so it can't be forgotten.
     - The cost: five or six dates typed by hand once a year. Rule b bans recurring manual *downloads*, and this is a borderline case, so it's your call.
   - **B. Only what the data gives.** Week windows and the season's start and end come from schedules, and the draft roughly from trade spikes. The rest of the offseason is one undivided stretch. Fully automatic, but free agency and the draft blur together, and the trades file goes stale (F7).
   - **C. "Week 0" for the whole offseason** *(tempting but bad).* It's simple, and it's the registry's own fallback. But February to September collapse into one moment, so a "June" prediction could see the draft and September cuts as already known. That's leakage in exactly the experts that need the offseason.

## Plan
No ladder (no model). Games, weeks and `phase_at` first, then the known-at rules and their tests, then the depth-chart cutoff, then the offseason phases. About 1–1.5 sessions, then the results page and your merge.
