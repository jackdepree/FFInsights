# 0007: State snapshots are change logs

**Date:** 2026-10-30 · **Decided by:** Claude (technical call, while building `data-layer`)

**Decision:** Files that nflverse overwrites (players, rosters, depth charts, injuries, contracts, schedules, current ECR, the id map) are recorded as change logs. A change log is a full copy once, then at each change only the rows added or removed. A fresh full copy is written after 90 changes, or when the columns change. `snapshot(dataset, at)` rebuilds the file as it was at any moment. A day with no change writes nothing.

**Why:** The CEO chose a daily Actions job writing into the private `pcf-data` git repo (data-layer brief, decision 1B). A full copy of the ten state files is 15 MB, so daily copies would add about 5 GB a year to that repo's history, which git never shrinks. On the first real change, a moved moneyline in the schedule, the change log stored a 15 KB delta instead of a 355 KB copy. Expected growth is about 0.1–0.2 GB a year, most of it the quarterly full copies.

**Alternatives:**
- Full dated copies (what the brief first said): the simplest to read, but too large for git at a daily cadence.
- Keyed diffs (changed cells only): smaller still, but several state files have no reliable unique key (weekly rosters list some players twice, `package-scaffold#F4`). Whole-row diffs work on any file.

**Revisit if:** `pcf-data` passes 1 GB, or replaying a change log becomes slow. Then lower the full-copy interval, or move the change logs to a storage service built for large files.
