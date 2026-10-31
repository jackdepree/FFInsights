# data/ (layer 0)

Raw sources → cleaned tables with `known_at` → the `as_of` gateway. Read `docs/DATA_SOURCES.md` before touching any source.

| Folder | What belongs here |
|---|---|
| `sources/` | One module per source. **The only code that downloads or saves raw data.** |
| `clean/` | Pure cleaning functions. Ported `old/` functions: copy, golden-test, then improve (`docs/OLD_INVENTORY.md`). |
| `tables/` | Tables at each level of detail, saved as parts with their own `known_at` (decision 0008): builders, the store, and `load(name, at)` |
| `tags/` | Tag tables any project can add to |
| `timeline/` | The calendar (games, week windows, phases, `phase_at`), the offseason dates file, and a known-at rule per dataset |
| `schemas.py` | The table contract: each table's keys and parts, and the checks every part passes before it's written |
| `gateway.py` | Planned (`validation-harness`): wraps `tables.load` |

- Fixed column names and units: `docs/CONVENTIONS.md`. Rename ids at ingest (`player_id` → `gsis_id`).
- Play-by-play is ~2.7 GB in memory if loaded whole. Work a season at a time.
- Models never import from `sources/`. They read through the gateway (`docs/ARCHITECTURE.md`, check 1).
