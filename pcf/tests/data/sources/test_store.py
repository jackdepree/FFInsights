from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from pcf.data.sources import store
from pcf.data.sources.store import (
    ChangeLog,
    Manifest,
    atomic_path,
    compare_versions,
    diff_rows,
    utc_stamp,
)

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _sorted(df: pl.DataFrame) -> pl.DataFrame:
    return df.sort(df.columns)


def _row(**kw):
    base = {
        "dataset": "pbp",
        "file": "play_by_play_2025.parquet",
        "season": 2025,
        "action": "new",
        "stored": True,
        "path": "pbp/season=2025/play_by_play_2025.parquet",
        "url": "https://example.test/x",
        "upstream_version": "sha256:aaa",
        "upstream_updated_at": T0,
        "size_bytes": 10,
        "sha256": "aaa",
    }
    return base | kw


# ---------------------------------------------------------------- safe writes


def test_atomic_path_keeps_old_file_on_error(tmp_path):
    dest = tmp_path / "f.txt"
    dest.write_text("old")
    with pytest.raises(RuntimeError), atomic_path(dest) as tmp:
        tmp.write_text("half")
        raise RuntimeError("crash mid-write")
    assert dest.read_text() == "old"
    assert list(tmp_path.iterdir()) == [dest]


def test_atomic_path_replaces_on_success(tmp_path):
    dest = tmp_path / "sub" / "f.txt"
    with atomic_path(dest) as tmp:
        tmp.write_text("new")
    assert dest.read_text() == "new"


def test_naive_timestamps_are_refused():
    with pytest.raises(ValueError):
        utc_stamp(datetime(2026, 10, 30))


# ---------------------------------------------------------------- manifest


def test_manifest_round_trip_and_latest_versions(tmp_path):
    m = Manifest(tmp_path)
    m.append([_row()], T0, part="pbp")
    m.append(
        [_row(action="replaced", upstream_version="sha256:bbb", sha256="bbb")], T0 + timedelta(1)
    )
    assert m.read().height == 2
    assert m.latest_versions() == {("pbp", "play_by_play_2025.parquet"): "sha256:bbb"}


def test_manifest_is_append_only(tmp_path):
    m = Manifest(tmp_path)
    m.append([_row()], T0, part="pbp")
    with pytest.raises(FileExistsError):
        m.append([_row()], T0, part="pbp")
    with pytest.raises(ValueError):
        m.append([_row(action="deleted")], T0 + timedelta(1))


def test_data_version_changes_only_when_stored_content_changes(tmp_path):
    m = Manifest(tmp_path)
    assert m.data_version() == "empty"
    m.append([_row()], T0)
    v1 = m.data_version()
    # A version-only record (nothing stored) and an identical re-upload don't change it.
    m.append([_row(action="seen", stored=False, sha256="zzz")], T0 + timedelta(1))
    m.append([_row(action="seen")], T0 + timedelta(2))
    assert m.data_version() == v1
    m.append([_row(action="replaced", sha256="bbb")], T0 + timedelta(3))
    assert m.data_version() != v1


# ---------------------------------------------------------------- row diffs and change logs


def test_diff_rows_counts_duplicates():
    old = pl.DataFrame({"a": [1, 1, 2]})
    new = pl.DataFrame({"a": [1, 2, 2, 3]})
    added, removed = diff_rows(old, new)
    assert sorted(added["a"]) == [2, 3]
    assert removed["a"].to_list() == [1]


def test_change_log_rebuilds_every_past_state(tmp_path):
    log = ChangeLog(tmp_path)
    v1 = pl.DataFrame({"id": [1, 2, 3], "team": ["A", "B", "C"]})
    v2 = pl.DataFrame({"id": [1, 2, 4], "team": ["A", "X", "D"]})  # changed, removed, added
    v3 = pl.DataFrame({"id": [1, 1, 2], "team": ["A", "A", "X"]})  # an exact duplicate row
    assert log.record(v1, T0).name.endswith("_base.parquet")
    assert log.record(v1, T0 + timedelta(hours=1)) is None  # unchanged: nothing written
    assert log.record(v2, T0 + timedelta(hours=2)).name.endswith("_delta.parquet")
    log.record(v3, T0 + timedelta(hours=3))
    assert len(log.entries()) == 3

    assert _sorted(log.state(T0 + timedelta(minutes=90))).equals(_sorted(v1))
    assert _sorted(log.state(T0 + timedelta(hours=2))).equals(_sorted(v2))
    assert _sorted(log.state()).equals(_sorted(v3))
    assert log.state(T0 - timedelta(hours=1)) is None


def test_change_log_deltas_are_small(tmp_path):
    log = ChangeLog(tmp_path)
    big = pl.DataFrame({"id": range(50_000), "status": ["ACT"] * 50_000})
    log.record(big, T0)
    one_change = pl.when(pl.col("id") == 7).then(pl.lit("INA")).otherwise("status")
    log.record(big.with_columns(status=one_change), T0 + timedelta(1))
    delta = pl.read_parquet(log.entries()[-1][2])
    assert delta.height == 2  # one row removed, one added


def test_change_log_rebases_on_schema_change_and_after_many_deltas(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "REBASE_EVERY", 2)
    log = ChangeLog(tmp_path)
    t = T0
    for i in range(4):
        log.record(pl.DataFrame({"id": [i]}), t := t + timedelta(hours=1))
    assert [kind for _, kind, _ in log.entries()] == ["base", "delta", "delta", "base"]
    log.record(pl.DataFrame({"id": [9], "extra": ["x"]}), t + timedelta(hours=1))
    assert log.entries()[-1][1] == "base"
    assert log.state().columns == ["id", "extra"]


def test_change_log_handles_an_empty_file_and_refuses_going_back(tmp_path):
    log = ChangeLog(tmp_path)
    log.record(pl.DataFrame({"id": []}, schema={"id": pl.Int64}), T0)
    log.record(pl.DataFrame({"id": [1]}), T0 + timedelta(1))
    assert log.state()["id"].to_list() == [1]
    with pytest.raises(ValueError):
        log.record(pl.DataFrame({"id": [2]}), T0)


def test_change_log_supports_list_columns(tmp_path):
    # Contracts carry list columns.
    log = ChangeLog(tmp_path)
    v1 = pl.DataFrame({"id": [1, 2], "history": [[1, 2], [3]]})
    v2 = pl.DataFrame({"id": [1, 2], "history": [[1, 2], [3, 4]]})
    log.record(v1, T0)
    log.record(v2, T0 + timedelta(1))
    assert _sorted(log.state().with_columns(pl.col("history").list.len().alias("n"))).equals(
        _sorted(v2.with_columns(pl.col("history").list.len().alias("n")))
    )


# ---------------------------------------------------------------- revision reports

PLAYS = pl.DataFrame(
    {
        "game_id": ["g1", "g1", "g2"],
        "play_id": [1, 2, 1],
        "epa": [0.5, -0.2, 1.1],
        "desc": ["a", "b", "c"],
    }
)


def test_revision_flags_a_planted_epa_change():
    new = PLAYS.with_columns(epa=pl.Series([0.5, -0.2, 9.9]))
    rev = compare_versions("pbp", "f", PLAYS, new, ("game_id", "play_id"), ("epa",))
    assert rev.keyed
    assert rev.changed_columns == {"epa": 1}
    assert rev.flags == ["watched columns changed: epa"]


def test_revision_of_unwatched_text_is_not_flagged():
    new = PLAYS.with_columns(desc=pl.Series(["a", "B", "c"]))
    rev = compare_versions("pbp", "f", PLAYS, new, ("game_id", "play_id"), ("epa",))
    assert rev.changed_columns == {"desc": 1}
    assert rev.flags == []


def test_revision_flags_lost_rows_with_and_without_keys():
    keyed = compare_versions("pbp", "f", PLAYS, PLAYS.head(2), ("game_id", "play_id"))
    assert keyed.keys_lost == 1 and keyed.flags
    keyless = compare_versions("combine", "f", PLAYS, PLAYS.head(2))
    assert not keyless.keyed
    assert keyless.flags == ["rows dropped from 3 to 2"]


def test_revision_falls_back_when_keys_are_not_unique():
    dup = pl.concat([PLAYS, PLAYS.head(1)])
    rev = compare_versions("pbp", "f", dup, dup, ("game_id", "play_id"))
    assert not rev.keyed
    assert (rev.rows_added, rev.rows_removed) == (0, 0)


def test_revision_handles_type_and_column_changes():
    new = PLAYS.with_columns(pl.col("play_id").cast(pl.Float64)).drop("desc").with_columns(x=1)
    rev = compare_versions("pbp", "f", PLAYS, new, ("game_id", "play_id"), ("epa", "gone"))
    assert rev.columns_added == ["x"]
    assert rev.columns_removed == ["desc"]
    assert rev.watched_missing == ["gone"]
    assert rev.flags == ["columns removed: desc"]
