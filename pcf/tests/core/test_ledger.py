"""The prediction ledger's rules: write once, nothing after kickoff, nothing from the future, only
finished runs count, and the first forecast is the one that counts."""

import json
import subprocess
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from pcf.core import ledger

KEYS = ["gsis_id", "game_id"]
T0 = datetime(2026, 11, 12, 17, 0, tzinfo=UTC)  # Thursday noon Eastern
UTC_US = pl.Datetime("us", "UTC")


def rows(kickoffs: list[datetime], mean: float = 0.5, as_of: datetime = T0) -> pl.DataFrame:
    n = len(kickoffs)
    return pl.DataFrame(
        {
            "gsis_id": [f"00-{i:07d}" for i in range(n)],
            "game_id": [f"2026_10_G{i}" for i in range(n)],
            "as_of": [as_of] * n,
            "quantity": ["snap_share"] * n,
            "mean": [mean] * n,
            "q10": [0.1] * n,
            "q50": [0.5] * n,
            "q90": [0.9] * n,
            "model": ["participation/trees_week"] * n,
            "model_version": ["live"] * n,
            "run_id": ["r"] * n,
            "train_end": [as_of - timedelta(days=2)] * n,
            "cadence": ["in_season"] * n,
            "kickoff": kickoffs,
        },
        schema_overrides={"as_of": UTC_US, "train_end": UTC_US, "kickoff": UTC_US},
    )


def new_run(tmp_path, record="live", started=T0):
    return ledger.open_run(2026, "thu", started, "abc123", T0, record, clone=tmp_path)


def test_a_run_folder_is_made_once(tmp_path):
    new_run(tmp_path)
    with pytest.raises(FileExistsError):
        new_run(tmp_path)


def test_a_model_is_written_once_per_run(tmp_path):
    run = new_run(tmp_path)
    run.write("participation/trees_week", rows([T0 + timedelta(hours=8)]), KEYS, now=T0)
    with pytest.raises(FileExistsError):
        run.write("participation/trees_week", rows([T0 + timedelta(hours=8)]), KEYS, now=T0)


def test_live_rows_after_kickoff_are_left_out(tmp_path):
    run = new_run(tmp_path)
    later, earlier = T0 + timedelta(hours=8), T0 - timedelta(minutes=1)
    info = run.write("participation/trees_week", rows([later, earlier, T0]), KEYS, now=T0)
    assert (info["rows"], info["left_out_after_kickoff"]) == (1, 2)
    saved = pl.read_parquet(run.folder / info["file"])
    assert saved["kickoff"].to_list() == [later]
    assert saved["record"].to_list() == ["live"]


def test_a_replay_keeps_games_already_played(tmp_path):
    run = new_run(tmp_path, "replay")
    info = run.write("participation/trees_week", rows([T0 - timedelta(days=3)]), KEYS, now=T0)
    assert info["rows"] == 1
    assert run.folder.parts[-3] == "replay"


def test_a_forecast_from_the_future_is_refused(tmp_path):
    run = new_run(tmp_path)
    future = rows([T0 + timedelta(hours=8)], as_of=T0 + timedelta(hours=1))
    with pytest.raises(ledger.LedgerRefused):
        run.write("participation/trees_week", future, KEYS, now=T0)


def test_rows_must_meet_the_standard_output(tmp_path):
    run = new_run(tmp_path)
    bad = rows([T0 + timedelta(hours=8)]).with_columns(q10=pl.lit(0.95))
    with pytest.raises(ValueError, match="quantiles"):
        run.write("participation/trees_week", bad, KEYS, now=T0)


def test_published_columns_are_kept_with_the_forecast(tmp_path):
    """Elo's ratings ride with its live rows, as in its backtest history (live-experts, goal 2)."""
    run = new_run(tmp_path)
    r = rows([T0 + timedelta(hours=8)]).with_columns(home_rating=pl.lit(3.5))
    info = run.write("elo/margin", r, KEYS, now=T0, publishes=("home_rating",))
    assert pl.read_parquet(run.folder / info["file"])["home_rating"].to_list() == [3.5]


def test_a_missing_published_column_is_refused(tmp_path):
    run = new_run(tmp_path)
    with pytest.raises(ledger.LedgerRefused, match="published"):
        run.write("elo/margin", rows([T0 + timedelta(hours=8)]), KEYS, now=T0, publishes=("hfa",))


def test_close_records_each_file_and_ends_the_run(tmp_path):
    run = new_run(tmp_path)
    info = run.write("participation/trees_week", rows([T0 + timedelta(hours=8)]), KEYS, now=T0)
    path = run.close({"note": "x"})
    body = json.loads(path.read_text())
    assert body["models"]["participation/trees_week"]["sha256"] == info["sha256"]
    assert body["commit"] == "abc123"
    with pytest.raises(ledger.LedgerRefused):
        run.write("participation/active", rows([T0 + timedelta(hours=8)]), KEYS, now=T0)


def test_only_finished_runs_count_and_the_first_forecast_wins(tmp_path):
    kick = T0 + timedelta(hours=8)
    first = new_run(tmp_path)
    first.write("participation/trees_week", rows([kick], mean=0.4), KEYS, now=T0)
    first.close({})
    second = new_run(tmp_path, started=T0 + timedelta(minutes=30))
    second.write(
        "participation/trees_week", rows([kick], mean=0.6), KEYS, now=T0 + timedelta(minutes=30)
    )
    second.close({})
    unfinished = new_run(tmp_path, started=T0 - timedelta(minutes=30))
    unfinished.write("participation/trees_week", rows([kick], mean=0.9), KEYS, now=T0)
    counted = ledger.read(clone=tmp_path)
    assert counted["mean"].to_list() == [0.4]
    assert ledger.read(clone=tmp_path, counted=False).height == 2


def test_code_state_names_the_commit():
    state = ledger.code_state()
    assert len(state["commit"]) == 40
    assert isinstance(state["dirty"], list)


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


def test_a_run_is_pushed_to_the_ledger_repo(tmp_path):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", str(remote), str(seed))
    (seed / "raw").mkdir()
    (seed / "raw" / "odds.txt").write_text("not checked out by the ledger")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "seed")
    git(seed, "push", "origin", "HEAD:main")
    clone = ledger.ensure_clone(tmp_path / "clone", str(remote))
    assert not (clone / "raw").exists()
    run = ledger.open_run(2026, "thu", T0, "abc", T0, clone=clone)
    run.write("participation/trees_week", rows([T0 + timedelta(hours=8)]), KEYS, now=T0)
    run.close({})
    ledger.push(run.folder, "live run", clone=clone)
    check = tmp_path / "check"
    git(tmp_path, "clone", str(remote), str(check))
    assert (check / "ledger" / "2026" / run.name / ledger.RUN_FILE).exists()
