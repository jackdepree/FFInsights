# 0017: How the prediction ledger keeps its records

**Date:** 2026-11-07 · **Decided by:** Claude (technical call, while building `prediction-ledger`)

**Decision:**
- **Where:** a sparse clone of the private `pcf-data` repo at `data/pcf-data/` (config `[ledger]`), holding only `ledger/` and `replay/`. Each run is committed and pushed as it finishes, using the PC's own git sign-in.
- **Files:** one folder per run, `ledger/<season>/<UTC stamp>_<day>/`. Each folder holds one Parquet file per model and `run.json`, written last. The JSON holds each file's sha256, the code commit and branch, when the data was pulled, when nflverse last changed the injury, roster and schedule files, the input check, timings and any model that failed.
- **Write once:** the folder is created only if it doesn't exist, and each file is opened for exclusive creation. Nothing in the ledger code can overwrite or delete.
- **Kickoff:** a live run leaves out rows whose game has kicked off by the moment they're written, and counts them in `run.json`. A row whose `as_of` is later than its write time is refused.
- **What counts:** for each model and row, the first forecast in a finished run (one with `run.json`). Reruns are kept but never replace it, so no forecast can be chosen after the fact.
- **Traceable rows:** each row has the standard output (model, `as_of`, `train_end`) plus `kickoff`, `record`, `ledger_run`, `written_at`, `commit` and `pulled_at`. Empty market columns are ready for products.
- **Clean code only:** a live run refuses to start if `src/`, `config.toml`, `uv.lock` or `pyproject.toml` has uncommitted changes, since its commit wouldn't describe the code that ran.
- **Same code as the backtest:** the live run calls `feature_history`, `targets` and `fit_at`, the function the walk now uses to fit. On week 9's Thursday game it matches the backtest's forecast (`explore/live_matches_walk.py`).
- **Replays:** remade forecasts for played weeks go under `replay/` with `record = "replay"`, never under `ledger/`.
- **Late injury file:** on a Thursday or Saturday run, if nflverse's injury file hasn't changed yet that day, the run re-checks it every 10 minutes. It gives up an hour after starting or 45 minutes before the first kickoff, whichever is sooner, and the record says whether the file was in.
- **Trial runs:** a run with `--no-push` goes to `data/ledger/trial/`, never the `pcf-data` clone, so an unpushed run can't be mistaken for a record.

**Why:** the ledger can't be rebuilt, and its value is that nobody, including us, could have changed it. Pushing to GitHub adds a timestamp we don't control. Write-once files and a first-forecast-counts rule make "rerun until it looks good" impossible without it showing. Reusing the harness's own code means the live record tests the model we validated, not a copy of it.

**Alternatives:**
- One growing Parquet file per season, appended each run: fewer files, but every append rewrites history, which is what the ledger mustn't do.
- A database such as SQLite: easy to query, but it's a binary file that git can't diff, and a single bad write could damage past rows.
- Allowing reruns to replace a forecast (tempting, bad): handy after a bug, but it would let a better-looking forecast replace a worse one. A bad run is corrected by a new run and a note, not an overwrite.

**Revisit if:** the ledger grows past what a git repo handles comfortably (about 1 GB), or a product needs its forecasts faster than a push allows.
