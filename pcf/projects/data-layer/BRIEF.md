# Brief: Data layer (`data-layer`)

> An infrastructure project: no model and no football calls, but two storage questions for the CEO (end of page). Light exploration: [EXPLORATION.md](EXPLORATION.md).

**Status:** draft (2026-10-30) · **Layer:** 0, data (Phase 0) · **Cadence:** — (the refresh itself is scheduled by `weekly-run`)

## The question
Can PCF hold its own copy of every nflverse file, keep it current with one re-runnable command, and always know what changed upstream and when?

## Why it matters
Every table and model reads from this copy. If it silently changes underneath a backtest, results can't be reproduced or trusted. And if a state file is overwritten upstream (a player's team or status, contracts, this week's rankings), what was true on a past date is lost unless we keep it.

## Terms
- **Standard terms used:** release asset (a file attached to a GitHub release, the way nflverse publishes), ETag (a fingerprint a web server returns that changes when the file does), idempotent (running it twice gives the same result as running it once), Parquet. See `docs/GLOSSARY.md`.
- **New terms:**
  - **History source:** a file whose rows describe past events and only grow or get corrected (play-by-play, stats, snaps). We keep its latest version.
  - **State source:** a file that describes "how things are now" and is overwritten (players, rosters, contracts, current rankings, schedules with lines). We keep a dated snapshot each time it changes.
  - **Manifest:** an append-only log of every file we've downloaded: where from, its upstream upload time, size, content fingerprint (SHA-256), and when we fetched it.
  - **Revision report:** when a history file is replaced, what changed (rows added or removed, which columns changed on how many rows). It flags a change to a **watched column** (one models use, like EPA or a player id).
  - **Data version:** a fingerprint of the manifest at a moment. MLflow logs it with every run (`experiment-tracking`), so a result can be tied to the exact data it saw.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `package-scaffold` | config zones (`raw/`), masking logger, the `pcf` command | The refresh writes only where config says and logs safely |
| `package-scaffold#F3`, `#F4`, `#F6` | depth-chart formats, duplicates, play-by-play memory | Raw stays exactly as fetched; reading is lazy and a season at a time |
| `data-layer#F1`–`#F5` | re-uploads, revision content, cheap change detection | The design below |
| `odds-collection` | the `raw/<source>/season=YYYY/` layout | Same layout for nflverse |
| `DATA_SOURCES.md` | "Revisions and snapshots" rule | History sources keep the latest; changing sources keep snapshots |

**Already tried:** `old/` downloaded CSVs by hand into `old/data/` with no record of when, which is why F2 can't say exactly when its copy was pulled.

## Assumptions
- **Everything nflverse publishes, 1999→ (about 830 MB).** Training starts in 2006, but aging and career models need earlier seasons, and the cost is small.
- **Download the release files directly, not through nflreadpy's loaders.** `raw/` should hold the file exactly as published, with our own manifest and snapshots. nflreadpy stays the reference: a network test checks every file we fetch matches what its loader returns. Its cache is turned off for our refresh (F5).
- **History sources keep only their latest version, safe because of F2,** with every replacement logged in the manifest and checked by the revision report.
- **State sources keep a snapshot only when their content changes** (deduplicated by fingerprint), current season only. At a weekly refresh that's roughly 25 MB a week, under 1 GB a season.
- No keys needed. A GitHub token is optional (raises the rate limit), read through `get_secret`.

## Goals: what gets built
1. **A source catalog** (`data/sources/nflverse.py`): every nflverse dataset in `DATA_SOURCES.md`, plus expected fantasy points, the id map and ECR. For each: where it's published, one file per season or one file total, first season, and whether it's a history or state source.
2. **`pcf refresh`:** compares upstream metadata to the manifest and downloads only new or changed files into `raw/nflverse/<dataset>/season=YYYY/`. Options: `--dataset`, `--seasons`, `--dry-run` (show what would change), `--force`. The first run pulls everything. It ends with a short summary: files checked, downloaded, unchanged, revised.
3. **The manifest** (`raw/nflverse/_manifest.parquet`, append-only) and a `data_version()` function.
4. **Snapshots for state sources:** `raw/nflverse/<dataset>/snapshots/<file>@<fetched UTC>.parquet`, written only when the fingerprint changes.
5. **The revision report:** when a history file is replaced, compare old and new on their key columns before the old one is deleted. Record rows added and removed, plus every changed column with its row count. **Flag** (in the summary and the log) when a watched column changes, or when a past season loses rows.
6. **Readers for the layers above:** `scan(dataset, seasons=None)` returns a lazy Polars frame over the latest files (a season at a time, F6). `snapshot(dataset, at)` returns the latest snapshot taken at or before a moment. Only `timeline`, `cleaning-port` and the tables use them. Experts never do (leakage check 1).
7. **Safe downloads:** timeouts, retries with backoff, and writes to a temporary file, renamed into place only once complete, so a crash never leaves half a file.

**Not in this project:** `known_at` and the calendar (`timeline`), renaming ids and fixing duplicates (`cleaning-port`), tier 2–4 sources (each needs your sign-off), and the schedule itself (`weekly-run`).

## Tests
- **Success looks like:**
  - From an empty `raw/`, `pcf refresh` fetches everything (under 1 GB). A second run straight after downloads **0 files** and finishes in under a minute.
  - For every dataset, reading our copy gives the same rows and columns as nflreadpy's loader (network test, a sample of seasons).
  - With a fake server (offline tests): a changed file is re-downloaded and an unchanged one isn't, a crash mid-download leaves no partial file, and two different versions of a state file give two snapshots while identical ones give one.
  - The revision report catches a planted change to `epa` in a test fixture and flags it. It also flags a past season that loses rows.
  - `data_version()` changes when any file changes, and only then.
  - Nothing is written outside `pcf/data/`, and nothing in `pcf/data/` is tracked by git.
- **Failure looks like:** a second refresh that re-downloads unchanged files, any file in `raw/` with no manifest row, or a replaced history file with no revision report.

## Inputs and outputs
- **Inputs:** nflverse release files, the ffopportunity release, dynastyprocess ECR and id-map files.
- **Outputs:** `pcf/data/raw/nflverse/` (latest files plus snapshots), the manifest, revision reports in `logs/`, and the readers `scan`, `snapshot` and `data_version`.

## How it will be used
For now, run `pcf refresh` by hand. `weekly-run` schedules it later. `timeline` and `cleaning-port` read through `scan` and `snapshot`. `experiment-tracking` logs `data_version()` with every run.

## Questions for the CEO
1. **Where should state snapshots live?** Snapshots of overwritten files can't be re-downloaded later, the same as odds. Rule g says that kind of data belongs in the private `pcf-data` repo.
   - **A. Local only for now** (in `pcf/data/raw/`), backed up to `pcf-data` once `weekly-run` exists. Simplest. But anything collected before then is lost if this PC dies, and nothing is collected while the PC is off.
   - **B. A small GitHub Actions job, separate from the odds collector, that snapshots the state files daily into `pcf-data`.** *(Recommended.)* It runs with the PC off, like the odds collection, and leaves `collect-odds.yml` untouched. It costs one more workflow file, and it reuses the existing `PCF_DATA_TOKEN`.
   - **C. Commit snapshots into this repo** *(tempting but bad)*: simple, but it puts data in the public repo (rule g) and bloats git with ~1 GB a season.
2. **How do we handle nflverse correcting past seasons?**
   - **A. Take the latest, log it, flag watched columns.** *(Recommended.)* The one measured re-upload touched no modelling column (F2). A flag tells us if that ever changes. Backtests always run on the best-known data.
   - **B. Keep every version of every file**, so any old result can be re-run on exactly its data. Fully reproducible, but about 1–2 GB a year, and every run has to pin a data version.
   - **C. Freeze history at the first download** *(tempting but bad)*: perfectly stable, but it keeps known errors forever and drifts away from the numbers everyone else uses.

## Plan
No ladder (no model). Build the catalog and offline tests first, then the refresh, then a full first pull with the network tests. About one session, then the results page and your merge.
