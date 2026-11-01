"""Light exploration for experiment-tracking: does local MLflow do what ARCHITECTURE.md plans?

Runs in a throwaway environment, so the project's dependencies don't change:

    uv run --no-project --python 3.12 --with mlflow --with scikit-learn --with polars \
        python projects/experiment-tracking/explore/try_mlflow.py <empty folder>

Checks: a SQLite store with file artifacts on Windows, one experiment per project, a parent run
with a child run per rung, the git commit as a tag, a registered model `pcf.<id>` with a
`champion` alias loaded back by alias, the time each step takes, and the disk it uses.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
t0 = time.time()
import mlflow  # noqa: E402
import numpy as np  # noqa: E402
from mlflow import MlflowClient  # noqa: E402
from sklearn.dummy import DummyRegressor  # noqa: E402
from sklearn.linear_model import LassoCV  # noqa: E402
from sklearn.metrics import mean_absolute_error  # noqa: E402

print(f"import mlflow + sklearn: {time.time() - t0:.1f}s, mlflow {mlflow.__version__}")
print("telemetry module:", hasattr(mlflow, "telemetry"))
print("telemetry env vars:", [v for v in dir(mlflow.environment_variables) if "TELEMETRY" in v])

root = Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
db = root / "mlflow.db"
uri = f"sqlite:///{db.as_posix()}"
artifacts = (root / "artifacts").as_uri()
mlflow.set_tracking_uri(uri)
mlflow.set_registry_uri(uri)

t = time.time()
client = MlflowClient()
name = "pcf-explore-elo"
exp = client.get_experiment_by_name(name)
exp_id = exp.experiment_id if exp else client.create_experiment(name, artifact_location=artifacts)
print(f"create store + experiment: {time.time() - t:.1f}s")
# Child runs go to the *active* experiment, not their parent's: without this they land in
# "Default" and write ./mlruns in the working folder (first run of this script).
mlflow.set_experiment(experiment_id=exp_id)

rng = np.random.default_rng(0)
X = rng.normal(size=(5000, 40))
y = X[:, :6] @ rng.normal(size=6) + rng.normal(size=5000)
train, test = slice(0, 4000), slice(4000, None)
commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

t = time.time()
with mlflow.start_run(experiment_id=exp_id, run_name="attempt-1") as parent:
    mlflow.set_tags({"git_commit": commit, "train_end": "2024-02-11T23:30:00Z"})
    for rung, model in [("0-baseline", DummyRegressor()), ("1-lasso", LassoCV(cv=5))]:
        with mlflow.start_run(run_name=rung, nested=True) as child:
            r = time.time()
            model.fit(X[train], y[train])
            mae = mean_absolute_error(y[test], model.predict(X[test]))
            mlflow.log_params({"rung": rung, "n_features": X.shape[1]})
            mlflow.log_metric("mae", mae)
            mlflow.log_text(f"{rung}: mae {mae:.3f}", "takeaways.md")
            info = mlflow.sklearn.log_model(model, name="model")
            print(f"  {rung}: mae {mae:.3f}, logged in {time.time() - r:.1f}s")
            last = (child.info.run_id, info.model_uri)
print(f"parent + 2 child runs with models: {time.time() - t:.1f}s")

t = time.time()
with mlflow.start_run(run_name="attempt-2-small-runs"):
    for i in range(50):
        with mlflow.start_run(run_name=f"week-{i}", nested=True):
            mlflow.log_params({"week": i, "alpha": 0.1})
            mlflow.log_metrics({"mae": 1.0 + i / 100, "coverage": 0.8})
print(f"50 small child runs (params + metrics): {time.time() - t:.1f}s")

t = time.time()
version = mlflow.register_model(last[1], "pcf.explore-elo")
client.set_registered_model_alias("pcf.explore-elo", "champion", version.version)
loaded = mlflow.sklearn.load_model("models:/pcf.explore-elo@champion")
same = np.allclose(loaded.predict(X[test]), LassoCV(cv=5).fit(X[train], y[train]).predict(X[test]))
print(f"register + alias + load by alias: {time.time() - t:.1f}s, same predictions: {same}")
print("model uri:", last[1])

runs = mlflow.search_runs([exp_id], output_format="list")
print("runs in experiment:", len(runs))
child = [r for r in runs if r.data.tags.get("mlflow.parentRunId") == parent.info.run_id]
print("children of the parent:", len(child))

size = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
print(f"disk: {size / 1e6:.1f} MB in {sum(1 for _ in root.rglob('*'))} files; db {db.stat().st_size / 1e6:.1f} MB")
print("top level:", sorted(p.name for p in root.iterdir()))
print("stray mlruns/ mlartifacts/ in cwd:", [p for p in ("mlruns", "mlartifacts") if Path(p).exists()])
