# data/ (layer 0)

Raw sources → cleaned tables with `known_at` → the `as_of` gateway. Read `docs/DATA_SOURCES.md` before touching any source.

| Folder | What belongs here |
|---|---|
| `sources/` | One module per source. **The only code that downloads or saves raw data.** |
| `clean/` | Pure cleaning functions. Ported `old/` functions: copy, golden-test, then improve (`docs/OLD_INVENTORY.md`). |
| `tables/` | Tables at each level of detail, saved as parts with their own `known_at` (decision 0008): builders, the store, and `load(name, at)` |
| `tags/` | The tag catalog (`catalog.py`, one versioned rule per tag) and its builders, saved as table parts and the `drive` table. Any project can add a tag: a rule, a rate band, a test. Regenerate `docs/TAGS.md` with `python -m pcf.data.tags.page` |
| `timeline/` | The calendar (games, week windows, phases, `phase_at`), the prediction moments (`moments.py`: the weekly runs, and `kickoff` for benchmarks), the offseason dates file, and a known-at rule per dataset |
| `standings.py` | Standings, playoff seeds (the NFL tiebreakers through strength of schedule) and final-week seed locks, from results a caller passes in. Checked against every real playoff field 2002-2024 |
| `schemas.py` | The table contract: each table's keys and parts (with which are about the result, and which are post-season only), and the checks every part passes before it's written |
| `gateway.py` | The `as_of` gateway: `Gateway().view(moment, cadence, inputs)`. The only way models read data. It keeps parts in memory, hides post-season parts in season, refuses undeclared inputs, and checks upstream outputs' vintage |

- Fixed column names and units: `docs/CONVENTIONS.md`. Rename ids at ingest (`player_id` → `gsis_id`).
- Play-by-play is ~2.7 GB in memory if loaded whole. Work a season at a time.
- Models never import from `sources/`. They read through the gateway (`docs/ARCHITECTURE.md`, check 1).
