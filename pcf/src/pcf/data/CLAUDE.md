# data/ (layer 0)

Raw sources → cleaned tables with `known_at` → the `as_of` gateway. Read `docs/DATA_SOURCES.md` before touching any source.

| Folder | What belongs here |
|---|---|
| `sources/` | One module per source. **The only code that downloads or saves raw data.** |
| `clean/` | Pure cleaning functions. Ported `old/` functions: copy, golden-test, then improve (`docs/OLD_INVENTORY.md`). |
| `tables/` | Tables at each level of detail, each with keys and a UTC `known_at` |
| `tags/` | Tag tables any project can add to |
| `timeline.py`, `gateway.py`, `schemas.py` | Planned (`timeline`, `grain-tables`, `validation-harness`) |

- Fixed column names and units: `docs/CONVENTIONS.md`. Rename ids at ingest (`player_id` → `gsis_id`).
- Play-by-play is ~2.7 GB in memory if loaded whole. Work a season at a time.
- Models never import from `sources/`. They read through the gateway (`docs/ARCHITECTURE.md`, check 1).
