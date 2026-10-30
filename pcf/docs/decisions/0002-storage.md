# 0002: Parquet, Polars and DuckDB

**Date:** 2026-10-30 · **Decided by:** CEO (with Claude's recommendation)

**Decision:** Data is stored as Parquet in `pcf/data/` zones and processed with Polars. DuckDB adds SQL and `ASOF JOIN` over the same files. Every table carries a timezone-aware `known_at`.

**Why:** Parquet is compressed, typed and fast. nflreadpy returns Polars. DuckDB's as-of join is exactly our known-at rule, and none of this needs a server.

**Alternatives:** SQLite (no as-of joins, slow for analytics) and Postgres (a server to run). CSVs and pickles were rejected: they lose types, and pickles break between library versions, as in `old/`.

**Revisit if:** data outgrows one machine (e.g. full tracking data at scale).
