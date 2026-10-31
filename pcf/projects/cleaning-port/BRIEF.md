# Brief: Port the cleaning functions (`cleaning-port`)

> An infrastructure project: no model, but one football call and one scope call for the CEO (end of page). Light exploration: [EXPLORATION.md](EXPLORATION.md).

**Status:** draft · **Layer:** 0, data (Phase 0) · **Cadence:** — (pure functions. Slot labels built from participation are retrospective only, rule m.)

## The question
Can PCF reproduce your old cleaning exactly, prove it, and then fix it? That means: who was on the field for each play, in which slot (QB1, WR2, CB1, …), for every season 2016–2026, from our own copy of nflverse.

## Why it matters
VOE, Context, fatigue, roles and participation all start from "these 22 players were on this play, in these roles". The old code did this well enough to build four models, so we keep it and prove the copy matches. But today it mislabels about 5% of players (F4), gives different answers depending on what you load (F7), and can't read 2025 or this season at all (F3).

## Terms
- **Standard terms used:** participation, depth chart, play-by-play, known_at, golden test, expectation test. See `docs/GLOSSARY.md` and `docs/CONVENTIONS.md`.
- **New terms:**
  - **Slot label:** a player's position and depth on a play, such as `WR2` or `CB1`. It's read from that team's depth chart for that game. Players on special teams only get `special`.
  - **Depth chart for a game:** through 2024, the weekly chart for that season and week. From 2025, the latest daily snapshot at or before the game's cutoff time. Kickoff is the cutoff, and `timeline` will supply it; until then, the start of game day.
  - **Reference version:** the old function, read straight from `old/code/Fatigue_Model_Prod.ipynb` when the test runs. It's never copied, so it can't drift.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `data-layer` | `scan`, `snapshot`, raw play-by-play, participation, depth charts, rosters | The inputs, a season at a time |
| `data-layer#F9` | schedules `roof` rule | nflreadpy's one cleaning step, which we have to apply ourselves |
| `package-scaffold#F3`, `#F4` | the 2025 depth-chart format, known duplicates | Goals 4 and 6 |
| `cleaning-port#F1`–`#F8` (exploration) | the reference version, the input fixes, the gaps | The plan below |
| `OLD_INVENTORY.md` | copy, test, then improve | The method |

**Already tried:** `old/` used these functions in four models. Its known problems are listed in `OLD_INVENTORY.md` and in F4, F7 and F8.

## Assumptions
- **The later version of `pivot_long_both_sides` is the reference** (F1). It labels unmatched players `special`; the earlier one dropped them.
- **Copy in pandas first, then move to Polars.** The golden test stays as the guard throughout. This adds pandas, NumPy and pyarrow as dependencies (F9), as `CONVENTIONS.md` allows for ports.
- **Depth charts are known at the start of their week** through 2024, and **at `dt`** from 2025 (`DATA_SOURCES.md`). Using the latest chart before the cutoff keeps the labels point-in-time.
- The Context and Fatigue feature code isn't cleaning (F8). It isn't ported here.

## Goals: what gets built
1. **Input preparation** (F2): join participation to play-by-play, and give `play_id` one type.
2. **The copy** (`data/clean/`): `pivot_wide_both_sides`, `clean_depth_charts`, `pivot_long_both_sides` and `get_position_groups`. Each is the same code, changed only where it must be (imports, no paths). They're logged in `OLD_INVENTORY.md`'s "Where it went".
3. **Golden tests:** the copy equals the reference version on a tiny fixture of two 2024 games (offline, under 1 MB of public rows). It also equals it on every season 2016–2024 from the local raw copy (a new `local_data` test marker, skipped by default).
4. **Improvements**, one at a time. Each gets its own commit and test, plus a note of exactly how far its output moves from the reference:
   - a. **Missing players** get a real slot label instead of `special` (question 2).
   - b. **Time-ordered, to-date depth** (F7): a week's labels use only that week and earlier, so deleting later weeks changes nothing before them.
   - c. **2025 onward** (F3): the daily snapshot format, mapped to the same position names and labels.
   - d. **Polars**, with an output identical to the improved pandas version.
   - e. Small fixes: the mislabeled comment, and a label list read from the data instead of hardcoded.
5. **Expectation tests:** 22 players per play (2016 allowed its 87%, F5), no player twice on one play, only known labels, `special` only for K/P/LS, and one QB1 per offense on at least 99% of plays.
6. **Source normalizations** (only if question 1 is B): the schedules `roof` rule (F9). Id renames to `gsis_id`/`game_id`. Team codes. The spread sign flipped to betting style. The known duplicates (`package-scaffold#F4`) removed, with their count logged. Each one fails loudly on anything unexpected.

**Not in this project:** Context and Fatigue feature code (their experts, F8). `known_at` and kickoff times (`timeline`). Tables (`grain-tables`). `moneyline_to_probability` (it moves with the odds code when `odds-collection` joins the package).

## Tests
- **Success looks like:**
  - The copy matches the reference exactly on the fixture and on 2016–2024.
  - After the improvements, `special` drops from about 5% of player-plays to K/P/LS only (under 0.5%). 2025 and 2026 get labels, with one QB1 per offense on at least 99% of plays. Deleting later weeks leaves earlier labels unchanged.
  - The Polars version equals the improved pandas version. A season takes under 10 seconds.
- **Failure looks like:** the copy can't be made to match the reference, an improvement changes rows it didn't mean to, or 2025+ labels can't be built from the daily snapshots.

## Inputs and outputs
- **Inputs:** raw play-by-play, participation (2016–2025, post-season only), depth charts (weekly through 2024, daily from 2025), weekly rosters, and schedules for the cutoff.
- **Outputs:** pure functions in `pcf.data.clean`. Slot labels from participation are **retrospective only** (rule m). Live experts use the depth chart alone, which is known before kickoff.

## How it will be used
`grain-tables` calls these functions to build the play and player-play tables. VOE, Context, fatigue, roles and participation read those tables, never these functions directly.

## Questions for the CEO
1. **How wide should this project be?** The old code holds only player-slot cleaning. The rest of PCF still needs basic source cleaning: the `data-layer` brief assigned id renames and duplicates here, and F9 adds the `roof` rule.
   - **A. Player slots only** (goals 1–5). The fastest route, but `grain-tables` then starts by writing the source cleaning itself.
   - **B. Player slots plus source normalizations** (goals 1–6). *(Recommended.)* The rules are already written in `DATA_SOURCES.md` and `CONVENTIONS.md`; this puts them in code with tests, in one place, so `grain-tables` starts on clean inputs. It adds about half a session.
   - **C. Port everything in the inventory, including the Context and Fatigue feature code** *(tempting but bad)*. It looks like more progress, but that code is expert features with a leak in it (F8). Ported now, it would land before the gateway that's meant to catch exactly that.
2. **What slot should a player get when they are on the field but not on that week's depth chart?** That's 4–6% of player-plays, mostly WRs, CBs and DL (F4).
   - **A. Fall back step by step.** *(Recommended.)* First, their slot on that team's most recent earlier chart that season (a usual WR2 missing from one week's chart stays WR2). If there isn't one, their roster position, ranked just past the deepest player listed (WR4 if WR1–3 are listed). A column records which step was used.
   - **B. Their roster position, with depth "unknown"** (`WR_x`). Simpler and honest, but a starter missing from one chart loses their depth.
   - **C. Keep `special`, as the old code did** *(tempting but bad)*. The output stays identical to the old code, but backup WRs get lumped in with kickers, and `special` stays the most common label of all.

## Plan
No ladder (no model). Inputs and the copy with golden tests first, then the improvements in order a–e, then the normalizations if B is chosen. About 1.5–2 sessions, then the results page and your merge.
