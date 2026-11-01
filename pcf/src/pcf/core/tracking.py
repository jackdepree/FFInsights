"""Experiment tracking: every training run, every model, and which version is the champion.

A thin wrapper over local MLflow (decision 0004). Projects never call MLflow to start runs or
register models, so its pitfalls are handled once (experiment-tracking#F3, #F4, #F9):

    with tracking.attempt("elo", train_end=cutoff):
        with tracking.rung("1-lasso") as r:
            model = fit(...)
            tracking.log_model(model)
            r.takeaways("lasso kept 6 of 40 features; ...")

- **Attempt:** a parent run in the project's experiment. Every attempt counts, failed ones too.
- **Rung:** a child run per rung of the ladder. It can't finish without its takeaways.
- **Register:** only a run whose leakage checks passed (`log_checks`, written by the harness).
- **Champion:** written in `registry.yaml` and merged with the CEO's approval (CEO decision 1A,
  experiment-tracking brief). `sync_champions` copies it to MLflow's `champion` alias, on `main`
  only. Claude may set `challenger` directly.

The store is `data/mlflow/` (`mlflow.db` plus `artifacts/`). Importing this module imports MLflow
(about 6 seconds), so only modelling code imports it.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Before MLflow loads: no usage data leaves the PC (#F4), and no log line aimed at AI agents.
os.environ.setdefault("MLFLOW_DISABLE_TELEMETRY", "true")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow  # noqa: E402
import mlflow.sklearn  # noqa: E402
from mlflow import MlflowClient  # noqa: E402
from mlflow.entities import Run  # noqa: E402
from mlflow.exceptions import MlflowException  # noqa: E402

from pcf import config  # noqa: E402
from pcf.core import registry  # noqa: E402
from pcf.core.log import get_logger  # noqa: E402

log = get_logger(__name__)

CHAMPION = "champion"
CHALLENGER = "challenger"
TAG = "pcf."  # every tag PCF writes starts with this
KIND_ATTEMPT = "attempt"
KIND_RUNG = "rung"
CHECKS_PASSED = "passed"
CHECKS_FAILED = "failed"

_store: Path | None = None


def model_name(project_id: str) -> str:
    """The registered model's name: `pcf.<id>`."""
    return f"pcf.{project_id}"


def use_store(root: Path | None = None) -> str:
    """Point MLflow at a store (default: the `mlflow` data zone) and return its address."""
    global _store
    _store = Path(root or config.get_config().zone("mlflow")).resolve()
    _store.mkdir(parents=True, exist_ok=True)
    uri = f"sqlite:///{(_store / 'mlflow.db').as_posix()}"
    mlflow.set_tracking_uri(uri)
    mlflow.set_registry_uri(uri)
    return uri


def _client() -> MlflowClient:
    if _store is None:
        use_store()
    return MlflowClient()


def experiment(project_id: str) -> str:
    """The project's experiment id, created on first use, and made the active experiment.

    Child runs go to the active experiment, not their parent's (#F3), so it's set here.
    """
    registry.project(project_id)  # refuses ids that aren't in registry.yaml
    client = _client()
    found = client.get_experiment_by_name(project_id)
    if found is None:
        location = (_store / "artifacts" / project_id).as_uri()
        experiment_id = client.create_experiment(project_id, artifact_location=location)
    else:
        experiment_id = found.experiment_id
    mlflow.set_experiment(experiment_id=experiment_id)
    return experiment_id


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=config.PCF_DIR, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def _uv_lock_hash() -> str:
    lock = config.UV_LOCK
    return hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else "missing"


def _active(kind: str | None = None) -> Run:
    active = mlflow.active_run()
    if active is None:
        raise RuntimeError("no active run: call this inside `tracking.attempt(...)`")
    run = _client().get_run(active.info.run_id)
    if kind is not None and run.data.tags.get(f"{TAG}kind") != kind:
        raise RuntimeError(f"the active run isn't an {kind}")
    return run


@contextmanager
def attempt(
    project_id: str,
    *,
    train_end: datetime | None = None,
    name: str | None = None,
    params: Mapping[str, Any] | None = None,
) -> Iterator[Run]:
    """One try at a project's model: a parent run with the tags every run must carry.

    `train_end` is the last `known_at` in the training data (ARCHITECTURE.md, check 6). A run
    that raises is kept, marked FAILED, and still counts in `versions_tried`.
    """
    if mlflow.active_run() is not None:
        raise RuntimeError("attempts don't nest: end the active run first")
    if train_end is not None and train_end.tzinfo is None:
        raise ValueError("train_end must be timezone-aware (UTC)")
    entry = registry.project(project_id)
    experiment_id = experiment(project_id)
    status = _git("status", "--porcelain")
    tags = {
        f"{TAG}project": project_id,
        f"{TAG}kind": KIND_ATTEMPT,
        f"{TAG}cadence": ",".join(entry.get("cadence") or ["n/a"]),
        f"{TAG}git_commit": _git("rev-parse", "HEAD") or "unknown",
        f"{TAG}git_dirty": "unknown" if status is None else str(bool(status)).lower(),
        f"{TAG}uv_lock": _uv_lock_hash(),  # MLflow's own package capture isn't exact (#F8)
    }
    if train_end is not None:
        tags[f"{TAG}train_end"] = train_end.astimezone(UTC).isoformat()
    with mlflow.start_run(experiment_id=experiment_id, run_name=name, tags=tags) as run:
        if params:
            mlflow.log_params(dict(params))
        yield run


@dataclass
class Rung:
    """The open child run of one rung. Call `takeaways` before it ends."""

    run: Run
    notes: list[str] = field(default_factory=list)

    def takeaways(self, text: str) -> None:
        """What the next rung should know (ARCHITECTURE.md, the ladder). Saved as takeaways.md."""
        if not text.strip():
            raise ValueError("takeaways can't be empty")
        self.notes.append(text.strip())
        mlflow.log_text("\n\n".join(self.notes), "takeaways.md")


@contextmanager
def rung(name: str, params: Mapping[str, Any] | None = None) -> Iterator[Rung]:
    """One rung of the ladder, as a child run of the active attempt.

    Fails if it ends without takeaways, so no rung's lesson is lost.
    """
    parent = _active(KIND_ATTEMPT)
    tags = {
        f"{TAG}project": parent.data.tags[f"{TAG}project"],
        f"{TAG}kind": KIND_RUNG,
        f"{TAG}rung": name,
    }
    with mlflow.start_run(run_name=name, nested=True, tags=tags) as run:
        if params:
            mlflow.log_params(dict(params))
        step = Rung(run)
        yield step
        if not step.notes:
            raise ValueError(f"rung {name!r} ended without takeaways: call .takeaways(...)")


def log_model(model: Any, example: Any = None) -> str:
    """Save a fitted scikit-learn model in the active run and return its address.

    Other libraries (XGBoost, PyMC) get a branch here when the first project needs them.
    The package list is given, not inferred: MLflow's guess loads the model in a new process
    (7 seconds a model) and isn't exact (#F8). The attempt's `uv.lock` hash pins the rest.
    """
    run = _active()
    import sklearn
    from sklearn.base import BaseEstimator

    if not isinstance(model, BaseEstimator):
        raise NotImplementedError(f"tracking.log_model has no flavor for {type(model).__name__}")
    info = mlflow.sklearn.log_model(
        model,
        name="model",
        input_example=example,
        pip_requirements=[f"scikit-learn=={sklearn.__version__}"],
    )
    _client().set_tag(run.info.run_id, f"{TAG}model_uri", info.model_uri)
    return info.model_uri


def log_checks(results: Mapping[str, bool], run_id: str | None = None) -> bool:
    """Record leakage-check results on a run (default: the active one). Written by the harness.

    Each check becomes a 1/0 metric `check_<name>`, the whole set is saved as checks.json, and the
    run is tagged passed only if there was at least one check and every one passed.
    """
    run_id = run_id or _active().info.run_id
    client = _client()
    for check, ok in results.items():
        client.log_metric(run_id, f"check_{check}", float(bool(ok)))
    client.log_text(run_id, json.dumps(dict(results), indent=2), "checks.json")
    passed = bool(results) and all(results.values())
    client.set_tag(run_id, f"{TAG}checks", CHECKS_PASSED if passed else CHECKS_FAILED)
    return passed


def register(project_id: str, run_id: str | None = None) -> int:
    """Register a run's model as a new version of `pcf.<id>`. Refuses unless its checks passed.

    MLflow itself lets anything be registered (#F9); this is the only door PCF uses.
    """
    run = _client().get_run(run_id) if run_id else _active()
    tags = run.data.tags
    if tags.get(f"{TAG}project") != project_id:
        raise ValueError(f"run {run.info.run_id} belongs to {tags.get(f'{TAG}project')!r}")
    if tags.get(f"{TAG}checks") != CHECKS_PASSED:
        raise PermissionError(
            f"run {run.info.run_id} hasn't passed its leakage checks "
            f"({tags.get(f'{TAG}checks', 'none recorded')}): it can't be registered"
        )
    if f"{TAG}model_uri" not in tags:
        raise ValueError(f"run {run.info.run_id} has no model: call tracking.log_model first")
    version = mlflow.register_model(
        tags[f"{TAG}model_uri"], model_name(project_id), tags={f"{TAG}run_id": run.info.run_id}
    )
    log.info("registered %s version %s", model_name(project_id), version.version)
    return int(version.version)


def set_challenger(project_id: str, version: int) -> None:
    """Mark a version as the challenger. The champion is set only by `sync_champions`."""
    _client().set_registered_model_alias(model_name(project_id), CHALLENGER, str(version))


def alias_version(project_id: str, alias: str = CHAMPION) -> int | None:
    """The version an alias points to, or None if it isn't set."""
    try:
        return int(_client().get_model_version_by_alias(model_name(project_id), alias).version)
    except MlflowException:
        return None


def sync_champions(path: Path | None = None, require_main: bool = True) -> dict[str, int]:
    """Set each model's `champion` alias to the version `registry.yaml` names (`champion: 3`).

    The registry is reviewed and merged like code, so a champion changes only when the CEO
    approves a merge (decision 1A). Runs on `main` with a committed registry only, unless
    `require_main` is False (tests).
    """
    if require_main:
        branch = _git("rev-parse", "--abbrev-ref", "HEAD")
        if branch != "main":
            raise PermissionError(f"champions sync only on main (this is {branch!r})")
        if _git("status", "--porcelain", "--", str(path or config.REGISTRY_FILE)):
            raise PermissionError("registry.yaml has uncommitted changes")
    client = _client()
    synced = {}
    for project_id, entry in registry.projects(path).items():
        if "champion" not in entry:
            continue
        version = int(entry["champion"])
        current = alias_version(project_id)
        if current != version:
            client.get_model_version(model_name(project_id), str(version))  # must exist
            client.set_registered_model_alias(model_name(project_id), CHAMPION, str(version))
            log.info("%s champion: version %s (was %s)", model_name(project_id), version, current)
        synced[project_id] = version
    return synced


def load_model(project_id: str, version: int | None = None, alias: str | None = None) -> Any:
    """Load a registered model by exact version (training pins one) or by alias, not both."""
    if (version is None) == (alias is None):
        raise ValueError("give exactly one of version or alias")
    _client()
    name = model_name(project_id)
    uri = f"models:/{name}/{version}" if version is not None else f"models:/{name}@{alias}"
    return mlflow.sklearn.load_model(uri)


def versions_tried(project_id: str) -> int:
    """How many attempts the project has made, failed ones included (VALIDATION.md section 4)."""
    client = _client()
    found = client.get_experiment_by_name(project_id)
    if found is None:
        return 0
    attempts = f"tags.`{TAG}kind` = '{KIND_ATTEMPT}'"
    return len(client.search_runs([found.experiment_id], attempts, max_results=50_000))


def mark_vault_opened(project_id: str, run_id: str | None = None) -> None:
    """Tag the run, and its project's experiment for good, as having opened the vault.

    VALIDATION.md section 1: opening the vault can't happen quietly. The experiment keeps the date
    it was first opened.
    """
    run_id = run_id or _active().info.run_id
    client = _client()
    today = datetime.now(UTC).date().isoformat()
    client.set_tag(run_id, f"{TAG}vault_opened", today)
    found = client.get_experiment_by_name(project_id)
    if found is not None and f"{TAG}vault_opened" not in found.tags:
        client.set_experiment_tag(found.experiment_id, f"{TAG}vault_opened", today)
