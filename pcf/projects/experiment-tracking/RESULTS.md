# Results: Experiment tracking (`experiment-tracking`)

> An infrastructure project: no model, so no ladder, scorecard or vault.

**Date:** 2026-11-01 · **Brief:** [BRIEF.md](BRIEF.md) · **Exploration:** [EXPLORATION.md](EXPLORATION.md) · **MLflow experiment:** `experiment-tracking` (one smoke-test attempt) · **Champion:** none

## In short
PCF now has `pcf.core.tracking`, a small wrapper over local MLflow that every modelling project trains through.
- **Recording:** an attempt is a parent run and each rung a child run, all in the project's own experiment. Every attempt records the git commit, uncommitted changes, the `uv.lock` hash, cadence and `train_end`.
- **Takeaways are required:** a rung that ends without its takeaways fails.
- **Registering needs the checks:** only a run whose leakage checks passed can become a version of `pcf.<id>`. The checks come from `validation-harness`.
- **The champion is set by merge** (your decision 1A). It's written in `registry.yaml` and copied to MLflow by `pcf champions` on `main` only.
- **Commands:** `pcf ui` opens the browser view (about 8 seconds), and `pcf champions` syncs the champions.

| Test from the brief | Result |
|---|---|
| An attempt with two rungs lands in the project's experiment; nothing is written outside `data/mlflow/` | **Pass**: unit tests on a temporary store check no `mlruns/` appears, and the end-to-end attempt on the real store wrote only `data/mlflow/`. |
| Every run carries the commit, uncommitted-changes flag, `uv.lock` hash and project id; a rung without takeaways fails | **Pass** |
| `register` refuses no checks or failing checks, accepts passing ones; `champion` loads identical predictions | **Pass**: refused with no checks, with an empty set, and with one failing check. Loading by version and by alias gives the same predictions. The champion is only set through `registry.yaml` (F11). |
| `versions_tried` counts every attempt, failed ones too; unknown project ids refused | **Pass** |
| Telemetry off in every process that imports the wrapper | **Pass** (`is_telemetry_disabled()`) |
| Importing `pcf` doesn't import MLflow | **Pass**: `pcf`, `pcf.cli` and `pcf.data.tables` load without it. |

**Tests:** 171 offline (16 new) and 85 `local_data`, all passing. The offline suite now takes about 14 seconds instead of 3.5, almost all of it loading MLflow (F14).

## Deviations from the brief
- **The champion lives in `registry.yaml`, not only in MLflow** (F11). Setting MLflow's alias directly would take effect at once on this PC, before any merge. So the version is written as `champion: N` under the project in `registry.yaml`, and `pcf champions` copies it to MLflow, refusing to run off `main` or with uncommitted registry changes. Claude can still set `challenger` directly. Decision note 0009.
- **A small `pcf.core.registry` reader** (`projects`, `project`) was added to check project ids. `registry-tooling` will grow it; it isn't a second copy.
- **pyarrow's floor dropped from 26 to 25**, because MLflow requires pyarrow below 26 (F12). No PCF code imports pyarrow directly, and all 85 real-data tests pass on 25.0.1.
- **`log_model` states the package list** instead of letting MLflow guess it (F10).
- **Only scikit-learn models for now.** `log_model` refuses other libraries until the first project needs one, then gets a branch for it.

## Terms
As in the brief. All are in `docs/GLOSSARY.md`: **attempt**, **registered model**, and **champion / challenger** (updated).

## Findings
F1–F9 came from the light exploration ([EXPLORATION.md](EXPLORATION.md)). F10–F14 came from the build.

| # | Finding | Evidence | Confidence | Applies to |
|---|---|---|---|---|
| F1 | Local MLflow does what ARCHITECTURE.md planned: SQLite plus files, nested runs, `pcf.<id>`, `champion` loaded back by alias. | [EXPLORATION.md](EXPLORATION.md) | strong | tracking |
| F2 | It's fast and small: about 25 ms a run with metrics; 1.1 MB for 54 runs and two models. | [EXPLORATION.md](EXPLORATION.md) | strong | tracking |
| F3 | Child runs follow the active experiment, not their parent's. Unset, they go to "Default" and write a stray `mlruns/`. | [EXPLORATION.md](EXPLORATION.md), unit test | strong | every modelling project |
| F4 | MLflow 3 sends usage telemetry by default; `MLFLOW_DISABLE_TELEMETRY` turns it off. | [EXPLORATION.md](EXPLORATION.md), unit test | strong | privacy |
| F5 | MLflow adds 86 packages and about 320 MB, including scikit-learn, scipy and matplotlib. | [EXPLORATION.md](EXPLORATION.md) | strong | setup |
| F6 | Windows Smart App Control is on here and sometimes blocks a newly installed library file once (2 of the first 9 runs); it loads on the next try. None during the build. | [EXPLORATION.md](EXPLORATION.md) | medium | scheduled jobs |
| F7 | Windows' 260-character path limit applies; MLflow's longest file is 180 characters inside the project's `.venv`. | [EXPLORATION.md](EXPLORATION.md) | strong | setup |
| F8 | MLflow 3 stores models apart from runs (`models:/m-<id>`), and its guessed package versions aren't exact. | [EXPLORATION.md](EXPLORATION.md) | strong | model reuse |
| F9 | MLflow lets anyone register anything; "checked runs only" is our wrapper's rule. | [EXPLORATION.md](EXPLORATION.md) | strong | registration |
| F10 | **MLflow's package guess takes about 7 seconds a model.** It loads the model in a new process to see what it imports. Stating the list makes saving instant. That took the new tests from 78 seconds to 12, together with copying a ready-made empty database per test instead of building one (1–2 seconds each). | profile of one test | strong | `log_model`, tests |
| F11 | **MLflow's store isn't in git, so an alias set there takes effect at once.** "Champion by merge" needs the champion written in a file that's reviewed: `registry.yaml`. | design | strong | champions |
| F12 | **MLflow 3.17.2 requires pyarrow below 26.** The project's floor was 26 only because that was newest when it was set. | `uv add` | strong | dependencies |
| F13 | **MLflow 3.17 saves scikit-learn models with skops**, a safe format that doesn't run code on loading, unlike pickle. | the end-to-end attempt | strong | model reuse |
| F14 | **Importing MLflow takes about 5 seconds.** The wrapper keeps it out of `import pcf`, but the offline tests went from 3.5 to about 14 seconds. | test timings | strong | tests |

## Pitfalls
- **Never pass the experiment only to the parent run** (F3). The wrapper sets it; projects shouldn't start runs themselves.
- **Don't let MLflow guess packages** (F10): it's slow and inexact.
- **Don't move a uv environment folder.** Its launchers point at the old path and fail ("uv trampoline failed"). Recreate it instead.
- **Don't set `champion` in MLflow by hand** (F11). The next `pcf champions` would put it back to what `registry.yaml` says.

## Not looked at
- **A model's walk-forward history and outputs.** They're saved under `outputs/` by the expert contract (`validation-harness`), not here.
- **Libraries other than scikit-learn** (XGBoost, PyMC). They get added when the first project needs them.
- **Backing up `data/mlflow/`.** Still in the roadmap's queue: it's on one PC with no backup.
- **Running the browser view while a model trains.** SQLite allows one writer at a time; a reader during training should be fine but wasn't tested.

## Could be improved
1. **The weekly run should call `sync_champions` first** (`weekly-run`), and retry once when Windows blocks a file (F6).
2. **Add more model libraries to `log_model`** as the ladder reaches trees and Bayesian models.
3. **Move the MLflow-dependent tests behind a marker** if the offline suite's 14 seconds starts to hurt (F14).

## Don't redo
- Don't choose between MLflow and a manifest file again (decision 0004).
- Don't store the champion only in MLflow (F11, decision 0009).
- Don't infer model requirements (F10).

## Interface card
Also in `registry.yaml` under `interface`.

| | |
|---|---|
| **Inputs** | `pcf.config` (the `mlflow` zone, `REGISTRY_FILE`, `UV_LOCK`), `registry.yaml` (ids, cadence, `champion`), git |
| **Outputs** | `pcf.core.tracking`: `attempt`, `rung` (with `.takeaways`), `log_model`, `log_checks`, `register`, `set_challenger`, `sync_champions`, `alias_version`, `load_model`, `versions_tried`, `mark_vault_opened`, `use_store`, `experiment`. `pcf.core.registry`: `projects`, `project`. Commands `pcf ui` and `pcf champions`. Store: `data/mlflow/mlflow.db` and `data/mlflow/artifacts/<id>/`. |
| **Level of detail** | one run per attempt and per rung; one registered model per project |
| **Interval** | from 2026-11-01 |
| **Cadence** | not applicable (used whenever a model trains) |
| **Known at** | not applicable. Runs record `train_end`, the last `known_at` in their training data. |
| **How to use it** | Train inside `with tracking.attempt(id, train_end=...)` and one `with tracking.rung("1-lasso") as r` per rung; call `tracking.log_model(model)` and `r.takeaways(...)`. The harness calls `log_checks` and `register`. To make version N the champion, write `champion: N` under the project in `registry.yaml` on the branch; after the CEO merges, run `pcf champions` on `main`. Load models by pinned version for training, by `champion` in the weekly run. |
| **Feeds** | `validation-harness`, every modelling project, `weekly-run`, `scorecards` |

## Open questions for the CEO
- **Approve the merge?** It adds MLflow and scikit-learn to the project (86 packages, about 320 MB; `uv sync` installs them).
- No football calls are needed.
