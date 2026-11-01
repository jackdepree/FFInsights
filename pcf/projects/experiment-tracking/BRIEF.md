# Brief: Experiment tracking (`experiment-tracking`)

> An infrastructure project: no model, but one call for the CEO (end of page), because it decides who can change which model the weekly run uses. Answered: 1A. Light exploration: [EXPLORATION.md](EXPLORATION.md).

**Status:** agreed (2026-11-01): CEO chose 1A · **Layer:** 0, foundation (Phase 0) · **Cadence:** — (used by every model's training run)

## The question
Give PCF one small, tested way to record every training run, keep every model, and say which version of each expert is the best one, using local MLflow as decided in 0004.

## Why it matters
- **It unblocks the harness.** `validation-harness` is the last thing before the first experts, and it needs somewhere to record its checks, its scorecards and the count of versions tried.
- **It stops results being lost or cherry-picked.** VALIDATION.md requires the scorecard to show how many versions were tried, and opening the vault to leave a mark. Both need a record that every run writes to automatically.
- **It's how projects reuse each other's models.** Every later project can then:
  - load another's model by name and version;
  - see which model the weekly run uses;
  - trust that it passed the leakage checks.

## Terms
- **Standard terms used:** rung, ladder, champion, challenger, vault, scorecard, leakage check. See `docs/GLOSSARY.md` and `docs/VALIDATION.md`.
- **New terms:**
  - **Attempt:** one try at a project's model. It's a parent run in MLflow, holding one child run per rung of the ladder. Five attempts means five tries, and the scorecard says so.
  - **Registered model:** a model saved under a name, `pcf.<id>`, with numbered versions (`pcf.elo` version 3). Higher layers ask for it by name and version, never by file path.
  - **Champion / challenger:** labels (MLflow calls them aliases) on one version each. `champion` is the version the weekly run uses; `challenger` is the one being tested against it.

## Builds on
| Project | What we use | Why |
|---|---|---|
| `package-scaffold` | `pcf.config` (the `mlflow` data zone), the masking logger, the `pcf` command | Paths in one place (rule f); keys never logged |
| `experiment-tracking` exploration, F1–F9 | The plan works; set the experiment explicitly; telemetry off; checks enforced by our wrapper | The design below |
| `package-scaffold#F8` | Install hooks must stay inside `pcf/` | Nothing here may touch `old/` |
| decision 0004 | MLflow, local, `pcf.<id>`, `champion`, only checked runs registered | The contract this project builds |

**Already tried:** `old/` saved models as loose pickle files, named by hand. Nobody could tell which file was best or what data trained it. Claude's earlier idea, a manifest file per run, was set aside for MLflow in 0004.

## Assumptions
- **Every model goes through one small wrapper, `pcf.core.tracking`.** It's a technical call: projects never call MLflow directly, so its pitfalls are handled once:
  - **Set the experiment, not just the parent.** Child runs follow the active experiment (F3).
  - **Telemetry off.** MLflow sends anonymous usage data by default; PCF's runs stay private (F4).
  - **One store.** The database and files go to `data/mlflow/`, never to a stray `mlruns/` folder.
- **What every run records, automatically:**
  - the git commit, and whether there were uncommitted changes;
  - the `uv.lock` hash, since MLflow's own package capture isn't exact (F8);
  - the project id, its cadence and `train_end`.
  - The rung's takeaways note is required: a rung can't finish without one (ARCHITECTURE.md, the ladder).
- **Registering needs the checks.** MLflow lets anyone register anything (F9), so the wrapper refuses a run unless it carries a passing leakage-check record. `validation-harness` writes that record. Until the harness exists, nothing can be registered, which is fine since there are no models yet.
- **Smart App Control stays on.** It's a Windows security setting and yours, not ours to change. It sometimes blocks a library file the first time it loads (F6). Scheduled jobs will retry once on that exact error (`weekly-run`); here it's only documented.
- **Install cost:** MLflow adds 86 packages and about 320 MB (F5), including scikit-learn, scipy and matplotlib, which the ladder needs anyway.

## Goals: what gets built
1. **`pcf.core.tracking`:**
   - `attempt(project_id, ...)`: a parent run in that project's experiment, with the automatic tags above. The project id must exist in `registry.yaml`.
   - `rung(name, takeaways=...)`: a child run.
   - `log_checks(results)`: the record the harness writes.
   - `register(run, project_id)`: refuses without passing checks.
   - `set_alias(project_id, version, "champion" | "challenger")`.
   - `load_model(project_id, version=... | alias=...)`.
   - `versions_tried(project_id)`: the count for the scorecard.
   - `mark_vault_opened(run)`: the tag VALIDATION.md requires.
2. **`pcf ui`:** opens the MLflow browser view on PCF's store (about 8 seconds to start), so nobody has to remember the database address.
3. **Dependencies:** `mlflow` and `scikit-learn` added to the project, locked by `uv.lock`.
4. **Docs:** ARCHITECTURE (tracking section brought in line with what's built), CONVENTIONS (run and tag names), GLOSSARY (attempt, registered model, champion/challenger), and a decision note if the wrapper departs from 0004.

**Not in this project:** the leakage checks, backtests and scorecards (`validation-harness`); the weekly run that uses `champion` (`weekly-run`); backing up the MLflow store (still in the roadmap's queue).

## Tests
- **Success looks like:**
  - An attempt with two rungs lands entirely in the project's experiment and nothing is written outside `data/mlflow/`. (Tested in a temporary folder; tests never touch the real store.)
  - Every run carries the commit, the uncommitted-changes flag, the `uv.lock` hash and the project id. A rung without takeaways fails.
  - `register` refuses a run with no checks or a failing one, and accepts a passing one. The model loaded back by `champion` gives identical predictions.
  - `versions_tried` counts every attempt, including failed ones. An unknown project id is refused.
  - Telemetry is off in every process that imports `pcf.core.tracking`.
  - Importing `pcf` doesn't import MLflow (about 6 seconds), so data commands stay fast.
- **Failure looks like:** runs that leak out of their experiment or folder, a model that can be registered without checks, or a wrapper so heavy that projects would rather call MLflow directly.

## Inputs and outputs
- **Inputs:** `pcf.config` (the `mlflow` zone), `registry.yaml` (project ids and cadence), git and `uv.lock`.
- **Outputs:** `pcf.core.tracking` and `pcf ui`. The store: `data/mlflow/mlflow.db` plus `data/mlflow/artifacts/`.

## How it will be used
Every modelling project trains inside `with tracking.attempt("elo"):` and one `with tracking.rung("1-lasso"):` per rung. The harness writes its checks and scorecard into the run, then registers it. Higher layers read outputs through the gateway. They load a model only to score new rows or to explain it, and always by a pinned version.

## Decisions (CEO, 2026-11-01)
- **1A:** `champion` changes only through a merge the CEO approves. Claude sets the alias on the branch; the RESULTS page shows the old and new versions' scorecards side by side.

## Questions for the CEO (answered above)
1. **Who can make a model the `champion`?**
   - **Why it matters:** `champion` is the version the weekly run uses for real predictions and bets. Changing it changes what you see on Sunday.
   - **A. Only by a merge you approve** *(Recommended).* A project or an update ends with Claude setting `champion` on a branch, and the change takes effect when you approve that merge, like any code change. The RESULTS page shows the old and new versions' scorecards side by side. One approval, never a silent change.
   - **B. You approve each promotion separately**, outside merges. More control, but an extra approval for every retrain. Most of those would be routine weekly refits of the same model.
   - **C. Automatic: whatever scores best in its backtest becomes champion** *(tempting but bad).* It's hands-off. But after 40 attempts the best backtest is partly luck, and it's exactly the cherry-picking VALIDATION.md's attempt count is there to stop. A model could change under you without anyone looking at its scorecard.

## Plan
No ladder (no model). The wrapper and its tests on a temporary store first. Then `pcf ui`, the dependencies, and an end-to-end check with a toy model on the real `data/mlflow/`. About 1 session, then the results page and your merge.
