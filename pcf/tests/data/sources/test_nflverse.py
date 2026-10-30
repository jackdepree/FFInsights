"""The refresh and readers, run offline against a fake upstream (no internet)."""

import hashlib
import io
import json
import re
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from pcf.data.sources import nflverse
from pcf.data.sources.nflverse import DATASETS, UpstreamFile, refresh, scan, snapshot

T0 = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _parquet(df: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.write_parquet(buf)
    return buf.getvalue()


def _plays(epa_last: float = 1.1) -> pl.DataFrame:
    return pl.DataFrame(
        {"game_id": ["g1", "g1", "g2"], "play_id": [1, 2, 1], "epa": [0.5, -0.2, epa_last]}
    )


class FakeUpstream:
    """In-memory upstream. Versions are content fingerprints, like nflverse's release digests."""

    def __init__(self):
        self.files: dict[tuple[str, str], bytes] = {}
        self.fail_on: set[str] = set()
        self.downloads = 0

    def put(self, dataset: str, name: str, content: pl.DataFrame | bytes) -> None:
        if isinstance(content, pl.DataFrame):
            content = _parquet(content)
        self.files[(dataset, name)] = content

    def list_files(self, ds):
        out = []
        for (d, name), content in self.files.items():
            m = ds.match(name) if d == ds.name else None
            if m:
                sha = hashlib.sha256(content).hexdigest()
                season = int(m["season"]) if ds.per_season else None
                out.append(
                    UpstreamFile(
                        d,
                        name,
                        season,
                        f"https://fake/{name}",
                        f"sha256:{sha}",
                        len(content),
                        T0,
                        sha,
                    )
                )
        return out

    def download(self, f, dest):
        self.downloads += 1
        content = self.files[(f.dataset, f.name)]
        dest.write_bytes(content[: len(content) // 2])
        if f.name in self.fail_on:
            raise ConnectionError("connection dropped mid-download")
        dest.write_bytes(content)


@pytest.fixture
def up():
    u = FakeUpstream()
    u.put("pbp", "play_by_play_2024.parquet", _plays(0.3))
    u.put("pbp", "play_by_play_2025.parquet", _plays())
    u.put(
        "players", "players.parquet", pl.DataFrame({"gsis_id": ["a", "b"], "status": ["ACT"] * 2})
    )
    return u


def _run(up, tmp_path, at=T0, **kw):
    return refresh(
        ["pbp", "players"],
        upstream=up,
        raw_dir=tmp_path / "raw",
        logs_dir=tmp_path / "logs",
        now=at,
        **kw,
    )


def _manifest(tmp_path) -> pl.DataFrame:
    return nflverse.Manifest(tmp_path / "raw" / "nflverse" / "_manifest").read()


# ---------------------------------------------------------------- the catalog


def test_catalog_names_are_unique_paths():
    assert all(re.fullmatch(r"[a-z0-9_]+", n) for n in DATASETS)
    assert len(DATASETS) == len({d.name for d in DATASETS.values()})


@pytest.mark.parametrize(
    "dataset,good,bad",
    [
        ("pbp", "play_by_play_2025.parquet", "play_by_play_2025.csv"),
        ("participation", "pbp_participation_2025.parquet", "pbp_participation_old_2023.parquet"),
        ("player_stats", "stats_player_week_2025.parquet", "stats_player_reg_2025.parquet"),
        ("rosters", "roster_2026.parquet", "roster_weekly_2026.parquet"),
        ("pfr_week_rec", "advstats_week_rec_2025.parquet", "advstats_season_rec.parquet"),
        ("pfr_season_rec", "advstats_season_rec.parquet", "advstats_week_rec_2025.parquet"),
        ("ff_opportunity", "ep_weekly_2025.parquet", "ep_pbp_pass_2025.parquet"),
        ("ecr_draft", "db_fpecr_latest.csv", "db_fpecr.parquet"),
    ],
)
def test_catalog_patterns(dataset, good, bad):
    assert DATASETS[dataset].match(good)
    assert not DATASETS[dataset].match(bad)


def test_every_state_source_in_data_sources_md_is_state():
    # DATA_SOURCES.md, "Revisions and snapshots": rosters, depth charts, injuries, rankings change.
    for name in (
        "rosters",
        "weekly_rosters",
        "depth_charts",
        "injuries",
        "players",
        "contracts",
        "schedules",
        "ecr_draft",
        "ecr_week",
        "player_ids",
    ):
        assert DATASETS[name].kind == "state", name
    for name in ("pbp", "player_stats", "snap_counts", "combine", "draft_picks", "ecr_archive"):
        assert DATASETS[name].kind == "history", name


# ---------------------------------------------------------------- the refresh


def test_first_run_fetches_everything_and_second_run_nothing(up, tmp_path):
    first = _run(up, tmp_path)
    assert len(first.downloaded) == 3
    assert (tmp_path / "raw/nflverse/pbp/season=2025/play_by_play_2025.parquet").exists()
    assert (tmp_path / "raw/nflverse/players/players.parquet").exists()

    second = _run(up, tmp_path, T0 + timedelta(hours=1))
    assert (second.downloaded, second.unchanged, up.downloads) == ([], 3, 3)


def test_every_stored_file_has_a_manifest_row(up, tmp_path):
    _run(up, tmp_path)
    raw = tmp_path / "raw" / "nflverse"
    stored = {
        p.relative_to(raw).as_posix() for p in raw.rglob("*.parquet") if "_manifest" not in p.parts
    }
    assert stored == set(_manifest(tmp_path).filter(pl.col("stored"))["path"])


def test_a_changed_file_is_replaced_with_a_revision_report(up, tmp_path):
    _run(up, tmp_path)
    up.put("pbp", "play_by_play_2025.parquet", _plays(epa_last=9.9))
    s = _run(up, tmp_path, T0 + timedelta(hours=1))
    assert s.downloaded == ["pbp/season=2025/play_by_play_2025.parquet"]
    assert s.flags == ["pbp/play_by_play_2025.parquet: watched columns changed: epa"]
    assert scan("pbp", [2025], tmp_path / "raw").collect()["epa"].to_list()[-1] == 9.9
    saved = json.loads(next((tmp_path / "logs" / "nflverse_revisions").glob("*.json")).read_text())
    assert saved[0]["changed_columns"] == {"epa": 1}


def test_an_identical_reupload_is_recognised(up, tmp_path, monkeypatch):
    _run(up, tmp_path)
    # Same bytes, but upstream reports a new version (as when a file is re-uploaded unchanged).
    real = up.list_files
    monkeypatch.setattr(
        up,
        "list_files",
        lambda ds: [
            UpstreamFile(
                f.dataset,
                f.name,
                f.season,
                f.url,
                f.version + "-reupload",
                f.size,
                f.updated_at,
                f.sha256,
            )
            for f in real(ds)
        ],
    )
    s = _run(up, tmp_path, T0 + timedelta(hours=1))
    assert s.downloaded == [] and len(s.same_bytes) == 3 and s.revisions == []


def test_a_crash_mid_download_leaves_no_partial_file_and_heals(up, tmp_path):
    up.fail_on = {"play_by_play_2025.parquet"}
    with pytest.raises(ConnectionError):
        _run(up, tmp_path)
    season = tmp_path / "raw/nflverse/pbp/season=2025"
    assert list(season.iterdir()) == []
    up.fail_on = set()
    s = _run(up, tmp_path, T0 + timedelta(hours=1))
    assert "pbp/season=2025/play_by_play_2025.parquet" in s.downloaded


def test_a_fingerprint_mismatch_is_refused(up, tmp_path, monkeypatch):
    real = up.list_files
    monkeypatch.setattr(
        up,
        "list_files",
        lambda ds: [
            UpstreamFile(
                f.dataset, f.name, f.season, f.url, f.version, f.size, f.updated_at, "0" * 64
            )
            for f in real(ds)
        ],
    )
    with pytest.raises(RuntimeError, match="fingerprint"):
        _run(up, tmp_path)


def test_dry_run_downloads_nothing(up, tmp_path):
    s = _run(up, tmp_path, dry_run=True)
    assert len(s.would_download) == 3 and up.downloads == 0
    assert not (tmp_path / "raw" / "nflverse" / "pbp").exists()


def test_seasons_filter(up, tmp_path):
    s = _run(up, tmp_path, seasons=[2025])
    assert sorted(s.downloaded) == [
        "pbp/season=2025/play_by_play_2025.parquet",
        "players/players.parquet",
    ]


def test_unknown_dataset_is_an_error(up, tmp_path):
    with pytest.raises(ValueError, match="Unknown"):
        refresh(["nope"], upstream=up, raw_dir=tmp_path)


# ---------------------------------------------------------------- state files and snapshots


def test_state_files_get_a_change_log_and_old_states_can_be_read(up, tmp_path):
    _run(up, tmp_path)
    up.put(
        "players",
        "players.parquet",
        pl.DataFrame({"gsis_id": ["a", "b"], "status": ["ACT", "INA"]}),
    )
    s = _run(up, tmp_path, T0 + timedelta(days=1))
    assert s.revisions == []  # state files are logged, not revision-reported
    assert len(s.change_logs) == 1
    raw = tmp_path / "raw"
    before = snapshot("players", T0 + timedelta(hours=1), raw_dir=raw).sort("gsis_id")
    after = snapshot("players", T0 + timedelta(days=2), raw_dir=raw).sort("gsis_id")
    assert before["status"].to_list() == ["ACT", "ACT"]
    assert after["status"].to_list() == ["ACT", "INA"]
    with pytest.raises(LookupError):
        snapshot("players", T0 - timedelta(days=1), raw_dir=raw)


def test_only_the_newest_season_of_a_per_season_state_source_is_logged(tmp_path):
    up = FakeUpstream()
    inj = pl.DataFrame({"gsis_id": ["a"], "season": [2025], "week": [1], "game_type": ["REG"]})
    up.put("injuries", "injuries_2025.parquet", inj)
    up.put("injuries", "injuries_2026.parquet", inj.with_columns(season=2026))
    s = refresh(["injuries"], upstream=up, raw_dir=tmp_path, logs_dir=tmp_path, now=T0)
    assert s.change_logs == [f"_changes/injuries/injuries_2026/{T0:%Y%m%dT%H%M%SZ}_base.parquet"]
    assert snapshot("injuries", T0, season=2026, raw_dir=tmp_path).height == 1
    with pytest.raises(ValueError, match="season"):
        snapshot("injuries", T0, raw_dir=tmp_path)


def test_snapshots_only_keeps_change_logs_not_files(up, tmp_path):
    s = _run(up, tmp_path, snapshots_only=True)
    raw = tmp_path / "raw" / "nflverse"
    assert s.checked == 1  # pbp is history, so skipped
    assert not (raw / "players" / "players.parquet").exists()
    assert snapshot("players", T0, raw_dir=tmp_path / "raw").height == 2
    again = _run(up, tmp_path, T0 + timedelta(hours=1), snapshots_only=True)
    assert again.unchanged == 1 and up.downloads == 1


def test_csv_state_files_are_read_as_text(tmp_path):
    up = FakeUpstream()
    up.put("ecr_week", "fp_latest_weekly.csv", b"fantasypros_id,pos,ecr\n1,WR,3.5\n2,RB,NA\n")
    refresh(["ecr_week"], upstream=up, raw_dir=tmp_path, logs_dir=tmp_path, now=T0)
    df = scan("ecr_week", raw_dir=tmp_path).collect()
    assert df.schema["ecr"] == pl.String
    assert df["ecr"].to_list() == ["3.5", None]


# ---------------------------------------------------------------- readers and data version


def test_scan_reads_seasons_and_aligns_columns(up, tmp_path):
    up.put("pbp", "play_by_play_2025.parquet", _plays().with_columns(new_col=1))
    _run(up, tmp_path)
    df = scan("pbp", raw_dir=tmp_path / "raw").collect()
    assert df.height == 6 and df["new_col"].null_count() == 3
    assert scan("pbp", [2024], tmp_path / "raw").collect().height == 3
    with pytest.raises(FileNotFoundError, match="pcf refresh"):
        scan("snap_counts", raw_dir=tmp_path / "raw")


def test_data_version_changes_only_when_data_does(up, tmp_path):
    raw = tmp_path / "raw"
    _run(up, tmp_path)
    v1 = nflverse.data_version(raw)
    _run(up, tmp_path, T0 + timedelta(hours=1))
    assert nflverse.data_version(raw) == v1
    up.put("pbp", "play_by_play_2024.parquet", _plays(0.0))
    _run(up, tmp_path, T0 + timedelta(hours=2))
    assert nflverse.data_version(raw) != v1


def test_refresh_writes_only_inside_its_folders(up, tmp_path):
    _run(up, tmp_path)
    assert {p.name for p in tmp_path.iterdir()} <= {"raw", "logs"}


# ---------------------------------------------------------------- the GitHub listing cache


class _Response:
    def __init__(self, status, body=None, etag=None):
        self.status_code, self._body = status, body
        self.headers = {"ETag": etag} if etag else {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class _Session:
    """Answers 304 when the caller already has the current ETag, like GitHub does."""

    def __init__(self, body, etag='"v1"'):
        self.body, self.etag, self.seen = body, etag, []

    def get(self, url, headers=None, timeout=None):
        self.seen.append(headers or {})
        if (headers or {}).get("If-None-Match") == self.etag:
            return _Response(304)
        return _Response(200, self.body, self.etag)


RELEASE = {
    "id": 1,
    "assets": [
        {
            "name": "players.parquet",
            "size": 5,
            "updated_at": "2026-10-30T13:00:00Z",
            "digest": "sha256:" + "a" * 64,
            "browser_download_url": "https://x/players.parquet",
        },
    ],
}


def test_listing_cache_sends_etag_and_reuses_unchanged_listing(tmp_path):
    cache = tmp_path / "_api_cache.json"
    first = nflverse.GitHubUpstream(token="", session=_Session(RELEASE), cache_file=cache)
    assert first.list_files(DATASETS["players"])[0].sha256 == "a" * 64
    assert first.calls == {"fresh": 1, "not_modified": 0}

    session = _Session(RELEASE)
    again = nflverse.GitHubUpstream(token="", session=session, cache_file=cache)
    assert again.list_files(DATASETS["players"])[0].name == "players.parquet"
    assert again.calls == {"fresh": 0, "not_modified": 1}
    assert session.seen[0]["If-None-Match"] == '"v1"'
    assert "Authorization" not in session.seen[0]  # no token, no header


def _assets(n):
    return [
        {
            "name": f"asset_{i}.parquet",
            "size": 1,
            "updated_at": "2026-10-30T13:00:00Z",
            "digest": "sha256:" + "a" * 64,
            "browser_download_url": f"https://x/{i}",
        }
        for i in range(n)
    ]


class _Paged(_Session):
    def __init__(self, inline, total):
        super().__init__({"id": 7, "assets": _assets(inline)})
        self.all = _assets(total)

    def get(self, url, headers=None, timeout=None):
        self.seen.append(url)
        if "page=" in url:
            page = int(url.rsplit("=", 1)[1])
            return _Response(200, self.all[(page - 1) * 100 : page * 100], '"p"')
        return _Response(200, self.body, '"r"')


def test_complete_inline_listing_needs_one_call():
    session = _Paged(inline=554, total=554)
    up = nflverse.GitHubUpstream(token="", session=session)
    assert len(up._listing(DATASETS["player_stats"])) == 554
    assert up.calls["fresh"] == 1


def test_listing_cut_at_a_round_number_is_paged():
    session = _Paged(inline=100, total=230)
    up = nflverse.GitHubUpstream(token="", session=session)
    assert len(up._listing(DATASETS["player_stats"])) == 230
    assert up.calls["fresh"] == 4  # the release, then pages 1-3


def test_rate_limit_message_says_what_to_do():
    class Limited(_Session):
        def get(self, url, headers=None, timeout=None):
            r = _Response(403)
            r.headers = {"x-ratelimit-remaining": "0"}
            return r

    up = nflverse.GitHubUpstream(token="", session=Limited(None))
    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        up.list_files(DATASETS["players"])
