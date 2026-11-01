"""The tracking wrapper, on a temporary MLflow store (tests never touch data/mlflow/)."""

import shutil
import subprocess
import sys
from datetime import UTC, datetime

import mlflow
import numpy as np
import pytest
from sklearn.linear_model import LinearRegression

from pcf.core import tracking

PROJECT = "elo"  # a real registry id; the store is temporary

X = np.arange(20, dtype=float).reshape(10, 2)
Y = X @ [1.0, 2.0]


@pytest.fixture(scope="session")
def empty_db(tmp_path_factory):
    """An empty store's database, built once: creating its tables takes 1–2 seconds."""
    root = tmp_path_factory.mktemp("empty_store")
    tracking.use_store(root)
    mlflow.MlflowClient().search_experiments()  # creates the tables
    return root / "mlflow.db"


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch, empty_db):
    monkeypatch.chdir(tmp_path)  # a stray ./mlruns would land here (experiment-tracking#F3)
    (tmp_path / "store").mkdir()
    shutil.copy(empty_db, tmp_path / "store" / "mlflow.db")
    tracking.use_store(tmp_path / "store")
    yield tmp_path
    while mlflow.active_run():
        mlflow.end_run()
    assert not (tmp_path / "mlruns").exists()
    assert not (tmp_path / "mlartifacts").exists()


def _attempt_with_model(checks=None):
    train_end = datetime(2024, 2, 12, tzinfo=UTC)
    with tracking.attempt(PROJECT, train_end=train_end) as parent, tracking.rung("1-linear") as r:
        tracking.log_model(LinearRegression().fit(X, Y))
        r.takeaways("both features matter")
        if checks is not None:
            tracking.log_checks(checks)
        run_id = r.run.info.run_id
    return parent.info.run_id, run_id


def test_an_attempt_and_its_rungs_stay_in_the_project_experiment():
    parent_id, child_id = _attempt_with_model()
    client = mlflow.MlflowClient()
    experiment = client.get_experiment_by_name(PROJECT)
    child = client.get_run(child_id)
    assert child.info.experiment_id == experiment.experiment_id
    assert child.data.tags["mlflow.parentRunId"] == parent_id
    assert (tracking._store / "artifacts" / PROJECT).is_dir()


def test_every_attempt_carries_its_provenance():
    parent_id, _ = _attempt_with_model()
    tags = mlflow.MlflowClient().get_run(parent_id).data.tags
    assert tags["pcf.project"] == PROJECT
    assert tags["pcf.cadence"] == "in_season"
    assert len(tags["pcf.git_commit"]) == 40
    assert tags["pcf.git_dirty"] in ("true", "false")
    assert len(tags["pcf.uv_lock"]) == 64
    assert tags["pcf.train_end"] == "2024-02-12T00:00:00+00:00"


def test_a_rung_without_takeaways_fails():
    with (
        pytest.raises(ValueError, match="without takeaways"),
        tracking.attempt(PROJECT),
        tracking.rung("0-baseline"),
    ):
        pass


def test_unknown_projects_and_naive_times_are_refused():
    with pytest.raises(KeyError, match="no project"), tracking.attempt("not-a-project"):
        pass
    with (
        pytest.raises(ValueError, match="timezone"),
        tracking.attempt(PROJECT, train_end=datetime(2024, 2, 12)),
    ):
        pass


def test_rungs_need_an_attempt_and_attempts_dont_nest():
    with pytest.raises(RuntimeError, match="no active run"), tracking.rung("x"):
        pass
    with (
        tracking.attempt(PROJECT),
        pytest.raises(RuntimeError, match="nest"),
        tracking.attempt(PROJECT),
    ):
        pass


@pytest.mark.parametrize("checks", [None, {}, {"vault_untouched": True, "no_future": False}])
def test_register_refuses_a_run_without_passing_checks(checks):
    _, run_id = _attempt_with_model(checks)
    with pytest.raises(PermissionError, match="leakage checks"):
        tracking.register(PROJECT, run_id)


def test_a_checked_model_registers_and_loads_back_by_version_and_alias():
    _, run_id = _attempt_with_model({"vault_untouched": True, "no_future": True})
    version = tracking.register(PROJECT, run_id)
    assert version == 1
    tracking.set_challenger(PROJECT, version)
    assert tracking.alias_version(PROJECT, tracking.CHALLENGER) == 1
    assert tracking.alias_version(PROJECT) is None  # no champion until the registry says so
    for model in (
        tracking.load_model(PROJECT, version=1),
        tracking.load_model(PROJECT, alias=tracking.CHALLENGER),
    ):
        assert np.allclose(model.predict(X), Y)
    with pytest.raises(ValueError, match="exactly one"):
        tracking.load_model(PROJECT)


def test_register_refuses_another_projects_run():
    _, run_id = _attempt_with_model({"no_future": True})
    with pytest.raises(ValueError, match="belongs to"):
        tracking.register("pace", run_id)


def test_champions_come_from_the_registry_file(tmp_path):
    _, run_id = _attempt_with_model({"no_future": True})
    tracking.register(PROJECT, run_id)
    path = tmp_path / "registry.yaml"
    path.write_text("projects:\n  - id: elo\n    champion: 1\n  - id: pace\n", encoding="utf-8")
    assert tracking.sync_champions(path, require_main=False) == {PROJECT: 1}
    assert tracking.alias_version(PROJECT) == 1
    path.write_text("projects:\n  - id: elo\n    champion: 7\n", encoding="utf-8")
    with pytest.raises(mlflow.exceptions.MlflowException):
        tracking.sync_champions(path, require_main=False)  # no version 7
    assert tracking.alias_version(PROJECT) == 1


def test_champions_sync_only_on_main(tmp_path, monkeypatch):
    monkeypatch.setattr(tracking, "_git", lambda *args: "pcf/some-branch")
    with pytest.raises(PermissionError, match="only on main"):
        tracking.sync_champions(tmp_path / "registry.yaml")


def test_every_attempt_counts_failed_ones_too():
    assert tracking.versions_tried(PROJECT) == 0
    _attempt_with_model()
    with pytest.raises(ZeroDivisionError), tracking.attempt(PROJECT):
        raise ZeroDivisionError
    assert tracking.versions_tried(PROJECT) == 2


def test_opening_the_vault_marks_the_run_and_the_experiment():
    with tracking.attempt(PROJECT) as run:
        tracking.mark_vault_opened(PROJECT)
    client = mlflow.MlflowClient()
    assert "pcf.vault_opened" in client.get_run(run.info.run_id).data.tags
    assert "pcf.vault_opened" in client.get_experiment_by_name(PROJECT).tags


def test_telemetry_is_off():
    from mlflow.telemetry.utils import is_telemetry_disabled

    assert is_telemetry_disabled()


def test_importing_pcf_does_not_import_mlflow():
    code = "import sys, pcf, pcf.cli, pcf.data.tables; print('mlflow' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
