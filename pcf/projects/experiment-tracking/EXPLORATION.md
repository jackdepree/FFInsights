# Exploration: Experiment tracking (`experiment-tracking`)

> A light exploration (infrastructure project). It asks one question: does local MLflow do what `docs/ARCHITECTURE.md` and decision 0004 plan, on this PC? The plan is a SQLite database plus files in `data/mlflow/`, one experiment per project, a parent run per attempt with a child run per rung, and a registered model `pcf.<id>` with a `champion` alias.
> Run on 2026-11-01 with [`explore/try_mlflow.py`](explore/try_mlflow.py) in a throwaway environment (MLflow 3.17.2, scikit-learn 1.9.1), so the project's dependencies didn't change. The data was synthetic: 5,000 rows, 40 features, 6 of them real.

**Verdict: GO.** Everything in the plan works locally with no server:
- the database and model files live in one folder;
- nested runs group the ladder's rungs under an attempt;
- a model registered as `pcf.<id>` and marked `champion` loads back by its alias with identical predictions;
- `mlflow ui` shows it all in a browser.

It's fast. A run with metrics takes about 25 ms, and saving a model about 0.2 seconds after the first. The store is about 1 MB for 54 runs and two small models.

Five things shape the build. Child runs need their experiment set explicitly (F3). Telemetry is on by default (F4). Windows can block a library file the first time it loads (F6). Windows' 260-character path limit applies (F7). And "only checked runs can be registered" has to be enforced by our own code (F9).

## Findings

| # | Finding | Confidence |
|---|---|---|
| F1 | **The plan works as designed.** SQLite database plus a file folder in one place; one experiment per project; a parent run with child runs per rung (search finds the 2 children of the parent); the git commit and `train_end` as tags; `register_model` → `pcf.explore-elo` version 1 → alias `champion` → `load_model("models:/pcf.explore-elo@champion")` gives identical predictions. | strong |
| F2 | **It's fast and small.** Opening a new store takes 2.5 seconds (it creates its tables). 50 child runs with parameters and metrics take 1.2 seconds in all. Saving a model takes about 2–7 seconds the first time in a session, then 0.2 seconds. Registering, setting the alias and loading take 0.1 seconds. 54 runs plus two small models use 1.1 MB. | strong |
| F3 | **Child runs don't inherit their parent's experiment.** A nested run goes to whichever experiment is active. On the first try the parent went to the project's experiment, but both rungs went to MLflow's "Default" experiment. That wrote a stray `mlruns/` folder into the working folder (deleted). The wrapper must set the experiment, never just pass it to the parent. | strong |
| F4 | **MLflow 3 sends anonymous usage telemetry by default.** `MLFLOW_DISABLE_TELEMETRY` turns it off. PCF's runs are private (decision 0005), so the wrapper turns it off before MLflow loads. MLflow 3.17 also prints a log line addressed to AI coding agents on import; `MLFLOW_DISABLE_AGENT_HINT=1` silences it. | strong |
| F5 | **MLflow adds 86 packages and about 320 MB** to the environment, including scikit-learn, scipy and matplotlib (which the ladder needs anyway), plus a web server for the UI. There's no lighter option: `mlflow-skinny` can't use a SQLite database. | strong |
| F6 | **Windows Smart App Control is on and sometimes blocks a library file the first time it loads.** Two of the first nine runs failed with "An Application Control policy has blocked this file": once on a scipy file, once on a scikit-learn file. Each time the same files loaded fine on the next run, and the 5 runs after the second block had none. It isn't MLflow's doing. Any scheduled job that loads a newly installed or upgraded library could fail once. | medium (few tries) |
| F7 | **Windows' 260-character path limit applies** (long paths are off on this PC). MLflow's longest file is 127 characters below its environment folder. Inside the project's `.venv` that's 180 characters, which is fine. From a deep temp folder it was over 260, and `mlflow ui` couldn't start. Keep the project where it is (`Documents\GitHub\FFInsights`). | strong |
| F8 | **MLflow 3 stores models apart from runs.** A model's address is `models:/m-<id>`, not the run's. The registry links a name and version to it. On loading, MLflow warned that two packages differed from the versions it had recorded, in the same environment where it saved them. Its version capture isn't exact, so PCF records the `uv.lock` hash with every run instead. | strong |
| F9 | **MLflow has no "may this be registered?" hook.** Anyone can call `register_model` on any run. "Only runs that pass the blocking leakage checks can be registered" (decision 0004) has to be our own wrapper's rule. The checks themselves come from `validation-harness`. | strong |
