"""A whole validation run, its scorecard and its MLflow record (on a temporary store)."""

import importlib
import pkgutil

import mlflow
import polars as pl
import pytest

import pcf
from pcf.core import tracking
from pcf.core.contract import Expert, check_expert
from pcf.validation import leakage
from pcf.validation.toy import LastFour, RecentPoints
from pcf.validation.validate import record, validate

from . import world

c = pl.col


@pytest.fixture(scope="module")
def v():
    return validate(
        RecentPoints(), world.gateway(), [2022, 2023], baselines=[LastFour()], shuffles=20,
        n_cutoffs=6,
    )  # fmt: skip


def test_the_toy_passes_every_check_and_is_compared_with_its_baseline(v):
    assert v.passed, [ch for ch in v.checks if not ch.passed]
    assert v.signal.passed
    comp = v.comparisons["LastFour"]
    assert comp.rows == v.bt.scored.height and comp.verdict in ("better", "tie", "worse")
    assert v.sanity["passed"].all()
    assert {"position", "season"} <= set(v.calibration["groups"]["group"])


def test_the_scorecard_has_every_section(v):
    from pcf.validation.scorecard import render

    html = render(v)
    for section in ("Scores", "Signal and no noise", "Range coverage", "Leakage checklist",
                    "Football sanity", "Vault", "Versions tried", "CEO review"):  # fmt: skip
        assert section in html, section
    assert "LastFour" in html and "<svg" not in html  # amounts get coverage, not the chart


def test_record_logs_checks_history_and_scorecard_and_allows_registration(v, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tracking.use_store(tmp_path / "store")
    try:
        with tracking.attempt("validation-harness", train_end=v.bt.history["train_end"].max()):
            path = record(v, tmp_path / "outputs")
            run_id = tracking.active_run_id()
        run = mlflow.MlflowClient().get_run(run_id)
        assert run.data.tags["pcf.checks"] == "passed"
        assert run.data.metrics["signal_beaten"] == 20
        assert path.read_text(encoding="utf-8").startswith("<!doctype html>")
        assert (path.parent / "history.parquet").exists()
        assert v.versions_tried == 1
    finally:
        while mlflow.active_run():
            mlflow.end_run()
        tracking.use_store()


def test_a_failed_check_fails_the_validation(v):
    broken = [*v.checks[:-1], leakage.Check(4, "future_deletion", False, "planted")]
    assert not type(v)(**{**vars(v), "checks": broken}).passed


def _models() -> list[type[Expert]]:
    found = []
    for name in ("experts", "composites", "products"):
        package = importlib.import_module(f"pcf.{name}")
        for info in pkgutil.walk_packages(package.__path__, f"pcf.{name}."):
            module = importlib.import_module(info.name)
            found += [
                v for v in vars(module).values()
                if isinstance(v, type) and issubclass(v, Expert) and v.__module__ == module.__name__
            ]  # fmt: skip
    return found


@pytest.mark.parametrize("model", [RecentPoints, *_models()], ids=lambda m: m.id)
def test_every_model_meets_the_contract_and_reads_only_its_view(model):
    """Leakage checks 1 and 7 on every test run (ARCHITECTURE.md): no model in the package reads
    around the gateway or imports a random splitter."""
    check_expert(model)
    gateway, splitters = leakage.code_checks(model)
    assert gateway == [] and splitters == []


def test_the_package_has_no_random_splitter_outside_validation():
    src = pcf.__file__.rsplit("__init__", 1)[0]
    from pathlib import Path

    offenders = []
    for path in Path(src).rglob("*.py"):
        if "validation" in path.parts:
            continue
        _, splitters = leakage.scan_code(path.read_text(encoding="utf-8"))
        offenders += [f"{path.name}: {s}" for s in splitters]
    assert offenders == []
