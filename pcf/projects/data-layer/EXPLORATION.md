# Exploration: Data layer (`data-layer`)

> A light exploration (infrastructure project). The rows, columns and seasons of every nflverse table were already profiled in [`package-scaffold`](../package-scaffold/EXPLORATION.md). This one asks what a refresh needs to know: how big the files are, how often they change, and whether a change touches values we'd model on.
> Run 2026-10-30 with [`explore/profile_releases.py`](explore/profile_releases.py) (GitHub release metadata) and [`explore/compare_pbp_revision.py`](explore/compare_pbp_revision.py).

**Verdict: GO.** Everything is small enough to keep locally. Change detection is cheap. The one revision we could measure didn't touch any modelling column.

## How nflverse publishes
nflreadpy downloads Parquet files attached to GitHub releases (`nflverse/nflverse-data`, plus `ffverse/ffopportunity`). ECR and the id map come from raw files in `dynastyprocess/data`. So GitHub's API tells us each file's size and when it was last uploaded, without downloading anything.

## The profile

| Release | Files | Total MB | Newest upload | Past seasons re-uploaded in the last 60 days |
|---|---|---|---|---|
| Play-by-play | 28 (one per season) | 496 | 2026-10-30 | none in 60 days, but 2020, 2024 and 2025 in Aug 2026 |
| Participation | 11 | 37 | 2026-02-10 | none |
| Player stats | 111 (4 summary levels × season) | 38 | 2026-10-30 | all rebuilt 2026-08-13 |
| Team stats | 111 | 9 | 2026-10-30 | all rebuilt 2026-08-13 |
| Expected fantasy points (ffopportunity) | 63 | 110 | 2026-10-30 | 2025 |
| Depth charts | 26 | 16 | 2026-10-30 | none |
| Rosters / weekly rosters | 107 / 25 | 17 / 14 | 2026-10-30 | none |
| Snap counts | 15 | 3 | 2026-10-30 | 2020, 2025 |
| Injuries | 18 | 2 | 2026-10-30 | 2025 |
| FTN charting | 5 | 2 | 2026-10-29 | 2025 |
| PFR advanced / Next Gen Stats | 40 / 3 | 3 / 2 | 2026-10-30 | none |
| Contracts, players, schedules, draft, combine, trades, officials, teams | 1 each | 16 together | various | — |
| ECR archive (`db_fpecr`, dynastyprocess) | 1 | 40 | has an ETag | — |

**About 830 MB for everything nflverse has.** Play-by-play is 60% of it, and no single file is over 40 MB.

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **nflverse re-uploads past seasons, often months later.** Play-by-play 2020, 2024 and 2025 were re-uploaded in Aug 2026. Snap counts 2020 and 2025 were re-uploaded in Sep 2026. All player and team stats were rebuilt on 2026-08-13. A refresh must check every file, not just the current season. | strong |
| F2 | **The one re-upload we could measure changed no modelling column.** An earlier pull of 2023 play-by-play (in `old/data/`, read only) compared with today's file (re-uploaded 2026-02-12): the same 49,665 plays and 372 columns. EPA, WPA, yards, air yards and every player id are identical on every play. What changed: `surface` (12% of plays), `weather` (6%), stadium and coach names, the text play description (8%), and the credited tackler on about 6 plays. One season, one revision: suggestive, not proof. | suggestive |
| F3 | **Change detection is cheap.** About 22 API calls give every release file's size and upload time (GitHub allows 60 an hour without a key). The dynastyprocess raw files give an ETag (a fingerprint that changes when the file does). There's no need to download 830 MB to find out what changed. | strong |
| F4 | **Some sources are one file covering every season**, re-uploaded daily: Next Gen Stats (2016→ in one file), players, contracts, schedules, ECR. These are rewritten whole on refresh, which is fine because they're small. | strong |
| F5 | **nflreadpy keeps its own cache** (in memory for 24 hours by default) and reads any `NFLREADPY_*` settings from a `.env` file in the working folder. If PCF owns `raw/`, nflreadpy's cache is a second, hidden copy that doesn't know about our snapshots. | strong |

## What it means for the brief
- Keep everything nflverse has, 1999→. That's under 1 GB, and aging curves and careers need the seasons before 2006.
- History files can keep only their latest version (F2), as long as every replacement is logged and checked (F1). State files that get overwritten (players, contracts, current rankings) need dated snapshots, as `DATA_SOURCES.md` already says.
- Refresh by comparing upstream metadata to a local manifest (F3), and download straight into `raw/` (F5).

## Next step
The [brief](BRIEF.md).
