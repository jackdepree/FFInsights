# 0008: Tables are saved as parts, one per source, each with its own known_at

**Date:** 2026-10-31 · **Decided by:** Claude (technical call, while building `grain-tables`)

**Decision:** Each table (`play`, `player_game`, ...) is saved as several parts that share its keys. The first part is the spine: it decides which rows the table has. Every other part holds one source's columns with that source's `known_at`, and attaches to the spine. `tables.load(name, at=moment)` keeps only part rows known at the moment and joins them onto the spine. A part not yet known leaves its columns empty, and the row is still there. Each part's `known_at` comes back as `<part>_known_at`. Parts are Parquet files at `data/tables/<table>/<part>/season=YYYY/data.parquet`. Table checks are plain Polars functions in `pcf.data.schemas`, not pandera: they're small, and that saves a dependency.

**Why:** one player-game's sources become known over four weeks (grain-tables#F8): the roster before the game, box scores the next day, NGS after the week, PFR about 9 days later, FTN 14 days later, participation after the Super Bowl. A table needs to hold them all without either holding the early ones back or letting the late ones leak.

**Alternatives:**
- One wide table with a `known_at` column per group of columns. It gives the same answer, but every refresh rewrites the whole table, and the reader has to know which columns go with which timestamp.
- One `known_at` per row (tempting but bad). The latest source's time holds box scores back two weeks; the earliest leaks PFR, NGS and FTN.

**Revisit if:** `load` gets too slow for walk-forward training (over about 2 seconds per season for `player_game`). Then cache the assembled table per moment, or move the join into DuckDB.
