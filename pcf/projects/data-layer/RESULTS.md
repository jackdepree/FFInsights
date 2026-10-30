# Results: Data layer (`data-layer`)

> An infrastructure project: no model, so no MLflow experiment, ladder or vault.

**Date:** 2026-10-30 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** none

## In short
PCF now keeps its own copy of all of nflverse: 36 datasets, 408 files, 786 MB. One command, `pcf refresh`, keeps it current, and a repeat run with nothing new takes 5 seconds and downloads nothing. Every file is logged in a manifest. History files that nflverse corrects get a revision report. State files that nflverse overwrites are recorded as change logs, by a daily Actions job into `pcf-data` once this is merged. Every test in the brief passes. One design change: change logs instead of full daily copies, to keep `pcf-data` small (decision [0007](../../docs/decisions/0007-state-change-logs.md)).

| Test from the brief | Result |
|---|---|
| From an empty `raw/`, `pcf refresh` fetches everything (under 1 GB) | **Pass, 786 MB.** It took three runs, because GitHub's hourly limit cut the first two short (F8). Each run picked up where the last stopped (F12). |
| A second run straight after downloads 0 files, in under a minute | **Pass.** 0 of 408 files, 5 seconds, 22 API calls. |
| Our copy reads the same as nflreadpy's loader | **Pass** for the 10 datasets compared on 2025 (play-by-play, participation, player stats, snaps, injuries, FTN, players, contracts, expected fantasy points, schedules). Schedules matches once nflreadpy's one cleaning rule is applied (F9). |
| Catalog keys and watched columns exist, and keys are unique | **Pass** for all 36 datasets on their 2025 file. |
| Fake server: changed file re-downloaded, unchanged not; a crash leaves no partial file; two state versions give two records, identical ones give one | **Pass** (offline tests). |
| The revision report flags a planted `epa` change, and a past season losing rows | **Pass** (offline tests). No history file was re-uploaded during the build, so no real report exists yet. |
| `data_version()` changes when a file changes, and only then | **Pass** (offline test). Today's value: `010527c70b3509f2`. |
| Nothing written outside `pcf/data/`, nothing in it tracked by git | **Pass.** An offline test checks writes, and `git check-ignore` confirms `pcf/data/` is ignored. |
| Football sanity | Not applicable (no football output). |

**Tests:** 83 offline and 82 network, all passing. The network tests that list every release first failed on a wrong assumption of mine (F13); the code was right, the test was fixed, and a size check was added to every download.

## Terms
As in the brief, with one change. **Change log** is new: how state files are stored, as a full copy, then the rows added or removed at each change. The brief said "dated snapshot". `snapshot(dataset, at)` still returns the file as it was at a moment, so the term keeps its meaning for every reader. All terms are in `docs/GLOSSARY.md`.

## Findings
F1–F5 came from the light exploration. F6–F13 came from the build.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | nflverse re-uploads past seasons months later. Check every file, not just the current season. | [EXPLORATION.md](EXPLORATION.md) | strong | every refresh |
| F2 | One measured play-by-play re-upload (2023) changed no modelling column. | [EXPLORATION.md](EXPLORATION.md) | suggestive | revision policy |
| F3 | Change detection is cheap: one listing per release gives every file's size and upload time, and a SHA-256 for recent uploads (F13). | [EXPLORATION.md](EXPLORATION.md), F7 | strong | refresh |
| F4 | Next Gen Stats, players, contracts, schedules and ECR are single all-season files. | [EXPLORATION.md](EXPLORATION.md) | strong | catalog |
| F5 | nflreadpy has its own cache and reads `NFLREADPY_*` from `.env`. | [EXPLORATION.md](EXPLORATION.md) | strong | anyone calling nflreadpy |
| F6 | **Without a token, a "not modified" (304) reply still counts against GitHub's limit.** One conditional request moved the allowance from 60 to 59. GitHub's docs say 304s are free with a token (not measured here). The listing cache saves bandwidth, not calls. | a measured request | strong | GitHub API use |
| F7 | **A release's inline asset list is already complete** (554 assets inline, the same 554 when paged). Paging anyway cost 28 extra calls. A full check is now 22 calls, so without a token it fits about twice an hour. | the call log | strong | GitHub API use |
| F8 | **The 60-call allowance ran out sooner than our own calls explain.** Two readings a minute apart disagreed (10 and 59 remaining), so it seems shared, or counted per server. Plan for fewer than 60. A token removes the problem (Actions has one). | `rate_limit` readings | suggestive | local refreshes |
| F9 | **nflreadpy's loaders return the published file unchanged, except schedules.** There it nulls any `roof` value other than dome, outdoors, closed or open. 26 games are published with `""`. Our raw copy keeps `""`, so `cleaning-port` must apply the same rule. | network test | strong | schedules, `cleaning-port` |
| F10 | **All of nflverse is 786 MB; play-by-play is 496 MB of it (63%).** Expected fantasy points (pass, rush, total) are 110 MB, the ECR archive 40 MB. | the manifest | strong | storage |
| F11 | **State files change within minutes.** Schedules was re-uploaded 14 minutes after the first pull: one moneyline moved (DAL at IND, 190 → 185). Its change-log entry is 15 KB, against a 355 KB full copy. The ten state files' first full copies total 15 MB. | `_changes/schedules/` | strong | `snapshot()`, line history |
| F12 | **A refresh stopped mid-way heals on the next run.** The rate limit stopped the first pull after 120 files. The next full run counted 119 files as unchanged, fetched the other 289, and fetched nothing twice. (A crash in the middle of a download is covered by an offline test: no partial file is left.) | the manifest, offline test | strong | refresh |
| F13 | **Most files have no SHA-256 from GitHub.** 278 of 408 files (473 MB), everything uploaded before July 2025, predate GitHub's digests. They're versioned by upload time and size, and every download is checked against the published size (all 408 matched). The other 126 are also checked by SHA-256. The 4 dynastyprocess files use git's own fingerprint. | the manifest, a network test | strong | refresh |

## Pitfalls
- **Assumed free calls weren't free** (F6), and assumed every file had a SHA-256 (F13). Measure an API's limits before designing around them.
- **"Matches nflreadpy" isn't always byte for byte.** Check each loader's code for cleaning steps (F9).
- **Upstream changes during a run.** Schedules changed between two runs 14 minutes apart (F11). Tests comparing our copy with a fresh download can fail for that reason alone. Rerun before suspecting the code.

## Not looked at
- **A real revision report.** No history file was re-uploaded during the build. The first one will show up in `logs/nflverse_revisions/`.
- **The Actions job running in Actions.** Scheduled jobs run only from `main`. It was simulated locally: a first run writes 15 MB of full copies, and a run with nothing new writes nothing.
- Whether 304s are free with a token (GitHub's docs say yes).
- Years before 2006 and tiers 2–4 sources: out of scope.

## Could be improved
1. Store only the fields we use in `_api_cache.json` (7.5 MB now).
2. Once the Actions job has run for a few weeks, measure `pcf-data`'s real growth against the estimate (0.1–0.2 GB a year). Lower the full-copy interval if needed.
3. Track nflverse's line movement in schedules with `snapshot()`, as a free history of spreads and totals for `odds-collection`.

## Don't redo
- Don't page release assets unless the inline list ends on a round number (F7).
- Don't load through nflreadpy for storage: raw keeps the published file, and cleaning happens in `cleaning-port` (F9).
- Don't store full daily copies of state files in git (decision 0007).

## Interface card
Also in `registry.yaml` under `interface`.

| | |
|---|---|
| **Inputs** | nflverse-data and ffopportunity GitHub releases, dynastyprocess ECR and id-map files (36 datasets, `DATASETS` in `pcf.data.sources.nflverse`) |
| **Outputs** | `raw/nflverse/`: the latest files, the manifest, and change logs for state files. Readers: `scan(dataset, seasons)` (lazy Polars), `snapshot(dataset, at)` (a state file as it was at a moment), `data_version()`. The `pcf refresh` command. The `snapshot-nflverse` Actions job. |
| **Level of detail** | as published: one file per dataset per season, or one file in total |
| **Interval** | on demand (`weekly-run` schedules it later). State files daily, through Actions. |
| **Cadence** | not applicable |
| **Known at** | Raw files carry no `known_at` (`timeline` adds it). The manifest records when each file was fetched, and change logs when each change was first seen. |
| **How to use it** | Read a season at a time through `scan`. Use `snapshot(dataset, at)` for state files as of a moment. Only `timeline`, `cleaning-port` and the tables read sources. Experts never do (leakage check 1). Log `data_version()` with every run. |
| **Feeds** | `timeline`, `cleaning-port`, `experiment-tracking` |

## Open questions for the CEO
- **Approve the merge?** The daily job starts only from `main`. It uses the `PCF_DATA_TOKEN` secret that `collect-odds` already uses, and its first run adds about 15 MB to `pcf-data`.
- No other decisions are needed. A GitHub token for local refreshes is optional (F8). Without one, a full check fits about twice an hour.
