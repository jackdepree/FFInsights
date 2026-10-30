"""nflverse: the catalog of every file we keep, the refresh that keeps it current, and readers.

Files are downloaded exactly as nflverse publishes them (GitHub release assets, plus a few
dynastyprocess files that nflreadpy also reads), not through nflreadpy's loaders, so `raw/` holds
the real bytes with our own manifest. nflreadpy stays the reference: the network tests check
that our copy reads back the same as its loaders (projects/data-layer/BRIEF.md).

Layout under the raw zone:
    nflverse/<dataset>/season=YYYY/<file>     one file per season
    nflverse/<dataset>/<file>                 one file covering every season
    nflverse/_changes/<dataset>/<file stem>/  change logs of state files (store.ChangeLog)
    nflverse/_manifest/                       every download (store.Manifest)
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

import polars as pl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pcf import __version__
from pcf.config import get_config, get_secret
from pcf.core.log import get_logger
from pcf.data.sources.store import (
    ChangeLog,
    Manifest,
    Revision,
    atomic_path,
    compare_versions,
    require_utc,
    save_revisions,
    sha256_file,
)

log = get_logger(__name__)

NFLVERSE = "nflverse/nflverse-data"
FFOPPORTUNITY = "ffverse/ffopportunity"
DYNASTYPROCESS = "dynastyprocess/data"


@dataclass(frozen=True)
class Dataset:
    """One kind of file we keep.

    `kind` follows DATA_SOURCES.md: a **history** file only grows or gets corrected, so we keep
    its latest version and write a revision report when it's replaced. A **state** file is
    overwritten upstream ("how things are now"), so every version is kept in a change log. For
    per-season state datasets only the newest season is state; older seasons are history.
    """

    name: str
    repo: str
    where: str  # a release tag, or a folder in the repo for raw files
    pattern: str  # regex the whole file name must match; (?P<season>...) for per-season files
    kind: Literal["history", "state"]
    keys: tuple[str, ...] = ()  # unique row keys, for column-level revision reports
    watched: tuple[str, ...] = ()  # columns models use: a change in a revision gets flagged
    raw_file: bool = False  # a plain file in the repo, not a release asset

    @property
    def per_season(self) -> bool:
        return "(?P<season>" in self.pattern

    def match(self, file_name: str) -> re.Match[str] | None:
        return re.fullmatch(self.pattern, file_name)


def _seasonal(prefix: str) -> str:
    return rf"{prefix}_(?P<season>\d{{4}})\.parquet"


PLAY_KEYS = ("game_id", "play_id")
PLAYER_WEEK_KEYS = ("player_id", "season", "week", "season_type")

_DATASETS = [
    # ------------------------------------------------------------ plays and games
    Dataset(
        "pbp", NFLVERSE, "pbp", _seasonal("play_by_play"), "history", PLAY_KEYS,
        watched=(
            "play_type", "posteam", "down", "ydstogo", "yardline_100", "yards_gained", "epa",
            "wpa", "air_yards", "yards_after_catch", "complete_pass", "touchdown",
            "passer_player_id", "rusher_player_id", "receiver_player_id",
        ),
    ),
    Dataset(
        "participation", NFLVERSE, "pbp_participation", _seasonal("pbp_participation"),
        "history", ("nflverse_game_id", "play_id"),
        watched=("offense_players", "defense_players", "route", "defense_coverage_type",
                 "time_to_throw", "was_pressure"),
    ),
    Dataset(
        "ftn_charting", NFLVERSE, "ftn_charting", _seasonal("ftn_charting"), "history",
        ("nflverse_game_id", "nflverse_play_id"),
        watched=("is_play_action", "is_screen_pass", "is_rpo", "n_blitzers", "n_pass_rushers"),
    ),
    Dataset(
        "schedules", NFLVERSE, "schedules", r"games\.parquet", "state", ("game_id",),
        watched=("gameday", "gametime", "home_team", "away_team", "home_score", "away_score",
                 "spread_line", "total_line"),
    ),
    Dataset("officials", NFLVERSE, "officials", r"officials\.parquet", "history",
            ("game_id", "official_id")),
    Dataset("teams", NFLVERSE, "teams", r"teams_colors_logos\.parquet", "history", ("team_abbr",)),
    # ------------------------------------------------------------ players and usage
    # Weekly stats only: the season-level files are sums of the weekly ones.
    Dataset(
        "player_stats", NFLVERSE, "stats_player", _seasonal("stats_player_week"), "history",
        PLAYER_WEEK_KEYS,
        watched=("completions", "attempts", "passing_yards", "passing_tds", "carries",
                 "rushing_yards", "rushing_tds", "receptions", "targets", "receiving_yards",
                 "receiving_tds", "fantasy_points_ppr"),
    ),
    Dataset(
        "team_stats", NFLVERSE, "stats_team", _seasonal("stats_team_week"), "history",
        ("team", "season", "week", "season_type"),
        watched=("passing_yards", "rushing_yards", "passing_tds", "rushing_tds"),
    ),
    Dataset(
        "snap_counts", NFLVERSE, "snap_counts", _seasonal("snap_counts"), "history",
        ("pfr_player_id", "game_id"),
        watched=("offense_snaps", "offense_pct", "defense_snaps", "defense_pct", "st_snaps"),
    ),
    *(
        Dataset(f"ngs_{t}", NFLVERSE, "nextgen_stats", rf"ngs_{t}\.parquet", "history",
                ("player_gsis_id", "season", "week", "season_type"))
        for t in ("passing", "receiving", "rushing")
    ),
    *(
        Dataset(f"pfr_week_{t}", NFLVERSE, "pfr_advstats", _seasonal(f"advstats_week_{t}"),
                "history", ("pfr_player_id", "game_id"))
        for t in ("pass", "rush", "rec", "def")
    ),
    # PFR's season files carry columns the weekly ones don't, so they're kept too.
    *(
        Dataset(f"pfr_season_{t}", NFLVERSE, "pfr_advstats", rf"advstats_season_{t}\.parquet",
                "history")
        for t in ("pass", "rush", "rec", "def")
    ),
    Dataset("ff_opportunity", FFOPPORTUNITY, "latest-data", _seasonal("ep_weekly"), "history",
            ("player_id", "season", "week")),
    Dataset("ff_opportunity_pass", FFOPPORTUNITY, "latest-data", _seasonal("ep_pbp_pass"),
            "history", PLAY_KEYS),
    Dataset("ff_opportunity_rush", FFOPPORTUNITY, "latest-data", _seasonal("ep_pbp_rush"),
            "history", PLAY_KEYS),
    Dataset("depth_charts", NFLVERSE, "depth_charts", _seasonal("depth_charts"), "state"),
    Dataset(
        "weekly_rosters", NFLVERSE, "weekly_rosters", _seasonal("roster_weekly"), "state",
        ("gsis_id", "season", "week"), watched=("team", "status"),
    ),
    Dataset("rosters", NFLVERSE, "rosters", _seasonal("roster"), "state", ("gsis_id", "season"),
            watched=("team", "status", "position")),
    Dataset("players", NFLVERSE, "players", r"players\.parquet", "state", ("gsis_id",),
            watched=("position", "status")),
    # ------------------------------------------------------------ health, people, offseason
    Dataset(
        "injuries", NFLVERSE, "injuries", _seasonal("injuries"), "state",
        ("gsis_id", "season", "week", "game_type"),
        watched=("report_status", "practice_status"),
    ),
    Dataset("combine", NFLVERSE, "combine", r"combine\.parquet", "history"),
    Dataset("draft_picks", NFLVERSE, "draft_picks", r"draft_picks\.parquet", "history",
            ("season", "pick")),
    Dataset("trades", NFLVERSE, "trades", r"trades\.parquet", "history"),
    Dataset("contracts", NFLVERSE, "contracts", r"historical_contracts\.parquet", "state"),
    # ------------------------------------------------------------ rankings and ids
    Dataset("ecr_archive", DYNASTYPROCESS, "files", r"db_fpecr\.parquet", "history",
            raw_file=True),
    Dataset("ecr_draft", DYNASTYPROCESS, "files", r"db_fpecr_latest\.csv", "state",
            raw_file=True),
    Dataset("ecr_week", DYNASTYPROCESS, "files", r"fp_latest_weekly\.csv", "state",
            ("fantasypros_id", "pos"), raw_file=True),
    Dataset("player_ids", DYNASTYPROCESS, "files", r"db_playerids\.csv", "state", raw_file=True),
]  # fmt: skip
DATASETS: dict[str, Dataset] = {d.name: d for d in _DATASETS}


# ---------------------------------------------------------------------------- upstream


@dataclass(frozen=True)
class UpstreamFile:
    dataset: str
    name: str
    season: int | None
    url: str
    version: str  # changes iff the content does: "sha256:..." for releases, "blob:..." for raw
    size: int
    updated_at: datetime | None = None
    sha256: str | None = None  # the published fingerprint, checked after download


class Upstream(Protocol):
    def list_files(self, dataset: Dataset) -> list[UpstreamFile]: ...
    def download(self, file: UpstreamFile, dest: Path) -> None: ...


class GitHubUpstream:
    """Lists and downloads files from GitHub. 22 API calls for the whole catalog.

    Without a token GitHub allows 60 API calls an hour, so a full check fits about twice an hour.
    - `cache_file` remembers each listing with its ETag, so an unchanged release isn't sent again.
      Measured: without a token a "not modified" reply still counts against the limit. With a
      token it doesn't (GitHub's docs), which makes repeat checks free.
    - GITHUB_TOKEN, if set, raises the limit to 5,000 (Actions provides one automatically).
    Downloads don't count against the limit.
    """

    API = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        session: requests.Session | None = None,
        cache_file: Path | None = None,
    ) -> None:
        self.token = token if token is not None else get_secret("GITHUB_TOKEN")
        self.session = session or _session()
        self.cache_file = cache_file
        self._cache: dict[str, dict] = {}
        if cache_file and cache_file.exists():
            self._cache = json.loads(cache_file.read_text(encoding="utf-8"))
        self._listings: dict[tuple[str, str], list[dict]] = {}
        self.calls = {"fresh": 0, "not_modified": 0}

    def _api(self, url: str) -> Any:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        cached = self._cache.get(url)
        if cached:
            headers["If-None-Match"] = cached["etag"]
        r = self.session.get(url, headers=headers, timeout=(10, 60))
        if r.status_code == 304 and cached:
            self.calls["not_modified"] += 1
            return cached["body"]
        if r.status_code in (403, 429) and r.headers.get("x-ratelimit-remaining") == "0":
            raise RuntimeError(
                "GitHub API rate limit reached (60 calls an hour without a token). Wait for it to "
                "reset, or set GITHUB_TOKEN. Files already fetched are kept; the next run resumes."
            )
        r.raise_for_status()
        self.calls["fresh"] += 1
        body = r.json()
        if self.cache_file and r.headers.get("ETag"):
            self._cache[url] = {"etag": r.headers["ETag"], "body": body}
            with atomic_path(self.cache_file) as tmp:
                tmp.write_text(json.dumps(self._cache), encoding="utf-8")
        return body

    def _listing(self, dataset: Dataset) -> list[dict]:
        key = (dataset.repo, dataset.where)
        if key not in self._listings:
            if dataset.raw_file:
                items = self._api(f"{self.API}/repos/{dataset.repo}/contents/{dataset.where}")
                self._listings[key] = items
            else:
                release = self._api(
                    f"{self.API}/repos/{dataset.repo}/releases/tags/{dataset.where}"
                )
                assets = release["assets"]
                # The inline list is complete (measured: 554 assets inline, the same 554 paged),
                # so page only if it ends on a round number, where it might have been cut short.
                if assets and len(assets) % 100 == 0:
                    assets, page = [], 1
                    while True:
                        batch = self._api(
                            f"{self.API}/repos/{dataset.repo}/releases/{release['id']}/assets"
                            f"?per_page=100&page={page}"
                        )
                        assets += batch
                        if len(batch) < 100:
                            break
                        page += 1
                self._listings[key] = assets
        return self._listings[key]

    def list_files(self, dataset: Dataset) -> list[UpstreamFile]:
        out = []
        for item in self._listing(dataset):
            m = dataset.match(item["name"])
            if not m:
                continue
            season = int(m["season"]) if dataset.per_season else None
            if dataset.raw_file:
                out.append(
                    UpstreamFile(
                        dataset.name,
                        item["name"],
                        season,
                        item["download_url"],
                        f"blob:{item['sha']}",
                        item["size"],
                    )
                )
                continue
            updated = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
            # GitHub only started publishing digests in mid-2025; older uploads (most of the
            # catalog) are versioned by upload time and size instead.
            digest = item.get("digest") or ""
            sha = digest.removeprefix("sha256:") if digest.startswith("sha256:") else None
            version = digest or f"{item['updated_at']}|{item['size']}"
            out.append(
                UpstreamFile(
                    dataset.name,
                    item["name"],
                    season,
                    item["browser_download_url"],
                    version,
                    item["size"],
                    updated,
                    sha,
                )
            )
        return sorted(out, key=lambda f: (f.season or 0, f.name))

    def download(self, file: UpstreamFile, dest: Path) -> None:
        with self.session.get(file.url, stream=True, timeout=(10, 300)) as r:
            r.raise_for_status()
            with dest.open("wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = f"pcf/{__version__} (+https://github.com/jackdepree/FFInsights)"
    return s


# ---------------------------------------------------------------------------- refresh


@dataclass
class RefreshSummary:
    checked: int = 0
    unchanged: int = 0
    downloaded: list[str] = field(default_factory=list)
    same_bytes: list[str] = field(default_factory=list)  # re-uploaded upstream, identical content
    would_download: list[str] = field(default_factory=list)  # dry run
    change_logs: list[str] = field(default_factory=list)
    revisions: list[Revision] = field(default_factory=list)

    @property
    def flags(self) -> list[str]:
        return [f"{r.dataset}/{r.file}: {flag}" for r in self.revisions for flag in r.flags]

    def text(self) -> str:
        lines = [
            f"checked {self.checked} files: {len(self.downloaded)} downloaded, "
            f"{self.unchanged} unchanged, {len(self.same_bytes)} re-uploaded with identical "
            f"content, {len(self.change_logs)} change-log entries, "
            f"{len(self.revisions)} revised"
        ]
        if self.would_download:
            lines.append(f"dry run: would download {len(self.would_download)} files")
            lines += [f"  {p}" for p in self.would_download]
        for r in self.revisions:
            cols = ", ".join(f"{c} ({n})" for c, n in list(r.changed_columns.items())[:6])
            lines.append(
                f"  revised {r.dataset}/{r.file}: rows {r.rows_before}->{r.rows_after}"
                + (f"; changed: {cols}" if cols else "")
            )
        lines += [f"  FLAG {f}" for f in self.flags]
        return "\n".join(lines)


def local_path(file: UpstreamFile) -> str:
    """Where a file lives under `raw/nflverse/`, with forward slashes."""
    if file.season is None:
        return f"{file.dataset}/{file.name}"
    return f"{file.dataset}/season={file.season}/{file.name}"


def read_file(path: Path) -> pl.DataFrame:
    """Read one raw file. CSVs are read as text, so types never shift between versions."""
    if path.suffix == ".csv" or path.name.endswith(".csv.part"):
        return pl.read_csv(path, infer_schema_length=0, null_values=["NA", ""])
    return pl.read_parquet(path)


def _stem(file_name: str) -> str:
    return file_name.split(".")[0]


def refresh(
    datasets: Iterable[str] | None = None,
    seasons: Iterable[int] | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
    snapshots_only: bool = False,
    upstream: Upstream | None = None,
    raw_dir: Path | None = None,
    logs_dir: Path | None = None,
    now: datetime | None = None,
) -> RefreshSummary:
    """Download every new or changed file. Safe to rerun: unchanged files are never fetched again.

    `snapshots_only` (for the Actions job writing to pcf-data) keeps only the change logs of
    state files, not the files themselves.
    """
    cfg = get_config()
    root = (raw_dir or cfg.zone("raw")) / "nflverse"
    logs = (logs_dir or cfg.zone("logs")) / "nflverse_revisions"
    run_at = require_utc(now or datetime.now(UTC)).replace(microsecond=0)
    manifest = Manifest(root / "_manifest")
    known = manifest.latest_versions()
    if upstream is None:
        # No API cache in snapshots-only runs: it would be committed to pcf-data every day.
        upstream = GitHubUpstream(cache_file=None if snapshots_only else root / "_api_cache.json")
    names = list(datasets) if datasets else list(DATASETS)
    unknown = [n for n in names if n not in DATASETS]
    if unknown:
        raise ValueError(f"Unknown datasets: {unknown}. Known: {', '.join(DATASETS)}")
    season_filter = set(seasons) if seasons else None
    summary = RefreshSummary()

    for name in names:
        ds = DATASETS[name]
        if snapshots_only and ds.kind != "state":
            continue
        files = upstream.list_files(ds)
        if not files:
            raise RuntimeError(f"No upstream files found for {name}: has nflverse renamed them?")
        newest = max((f.season for f in files if f.season is not None), default=None)
        rows: list[dict] = []
        for f in files:
            if season_filter and f.season is not None and f.season not in season_filter:
                continue
            is_state = ds.kind == "state" and (f.season is None or f.season == newest)
            if snapshots_only and not is_state:
                continue
            summary.checked += 1
            rel = local_path(f)
            dest = root / rel
            if (
                not force
                and known.get((ds.name, f.name)) == f.version
                and (snapshots_only or dest.exists())
            ):
                summary.unchanged += 1
                continue
            if dry_run:
                summary.would_download.append(rel)
                continue
            rows += _fetch_one(
                ds, f, rel, dest, root, is_state, snapshots_only, run_at, upstream, summary
            )
        # One manifest file per dataset per run: a crash loses at most the dataset in progress,
        # and the next run heals it (the file's version is unknown, so it's fetched and matched).
        manifest.append(rows, run_at, part=ds.name)

    save_revisions(summary.revisions, logs, run_at)
    if isinstance(upstream, GitHubUpstream):
        log.info(
            "GitHub API calls: %d changed, %d not modified (%s)",
            upstream.calls["fresh"],
            upstream.calls["not_modified"],
            "free with a token" if upstream.token else "each still counts without a token",
        )
    for flag in summary.flags:
        log.warning("revision flag: %s", flag)
    return summary


def _fetch_one(
    ds: Dataset,
    f: UpstreamFile,
    rel: str,
    dest: Path,
    root: Path,
    is_state: bool,
    snapshots_only: bool,
    run_at: datetime,
    upstream: Upstream,
    summary: RefreshSummary,
) -> list[dict]:
    base = {
        "dataset": ds.name,
        "file": f.name,
        "season": f.season,
        "path": rel,
        "url": f.url,
        "upstream_version": f.version,
        "upstream_updated_at": f.updated_at,
        "size_bytes": f.size,
    }
    rows = []
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        upstream.download(f, tmp)
        # Files uploaded before mid-2025 have no SHA-256 upstream; their size still catches a
        # download cut short.
        if f.size and tmp.stat().st_size != f.size:
            raise RuntimeError(f"{rel}: downloaded {tmp.stat().st_size} bytes, expected {f.size}")
        sha = sha256_file(tmp)
        if f.sha256 and sha != f.sha256:
            raise RuntimeError(f"{rel}: downloaded content doesn't match nflverse's fingerprint")
        log.info("fetched %s (%.1f MB)", rel, tmp.stat().st_size / 1e6)

        if snapshots_only:
            rows.append({**base, "action": "seen", "stored": False, "sha256": sha})
        elif dest.exists() and sha256_file(dest) == sha:
            summary.same_bytes.append(rel)
            rows.append({**base, "action": "seen", "stored": True, "sha256": sha})
        else:
            existed = dest.exists()
            if existed and not is_state:
                old, new = read_file(dest), read_file(tmp)
                summary.revisions.append(
                    compare_versions(ds.name, f.name, old, new, ds.keys, ds.watched)
                )
            os.replace(tmp, dest)
            summary.downloaded.append(rel)
            action = "replaced" if existed else "new"
            rows.append({**base, "action": action, "stored": True, "sha256": sha})

        if is_state:
            content = read_file(tmp if snapshots_only else dest)
            change = ChangeLog(root / "_changes" / ds.name / _stem(f.name)).record(content, run_at)
            if change is not None:
                change_rel = change.relative_to(root).as_posix()
                summary.change_logs.append(change_rel)
                rows.append(
                    {
                        **base,
                        "action": "change_log",
                        "stored": True,
                        "path": change_rel,
                        "size_bytes": change.stat().st_size,
                        "sha256": sha256_file(change),
                    }
                )
    finally:
        tmp.unlink(missing_ok=True)
    return rows


# ---------------------------------------------------------------------------- readers
# For timeline, cleaning and the tables only. Experts never read these (leakage check 1).


def _root(raw_dir: Path | None) -> Path:
    return (raw_dir or get_config().zone("raw")) / "nflverse"


def files(
    dataset: str, seasons: Sequence[int] | None = None, raw_dir: Path | None = None
) -> list[Path]:
    """The latest local files of a dataset, oldest season first."""
    ds = DATASETS[dataset]
    found = []
    for p in (_root(raw_dir) / dataset).rglob("*"):
        m = ds.match(p.name) if p.is_file() else None
        if m and (seasons is None or not ds.per_season or int(m["season"]) in seasons):
            found.append(p)
    return sorted(found)


def scan(
    dataset: str, seasons: Sequence[int] | None = None, raw_dir: Path | None = None
) -> pl.LazyFrame:
    """A lazy frame over a dataset's latest files, as published. Columns that differ between
    seasons are aligned (missing ones become null), so filter or select before collecting."""
    paths = files(dataset, seasons, raw_dir)
    if not paths:
        raise FileNotFoundError(
            f"No local files for {dataset}. Run `pcf refresh --dataset {dataset}`."
        )
    frames = [
        pl.scan_csv(p, infer_schema_length=0, null_values=["NA", ""])
        if p.suffix == ".csv"
        else pl.scan_parquet(p)
        for p in paths
    ]
    return pl.concat(frames, how="diagonal_relaxed")


def snapshot(
    dataset: str, at: datetime, season: int | None = None, raw_dir: Path | None = None
) -> pl.DataFrame:
    """A state file as it was at `at` (UTC), rebuilt from its change log. Row order isn't kept."""
    ds = DATASETS[dataset]
    if ds.kind != "state":
        raise ValueError(f"{dataset} is a history source; read it with scan()")
    folder = _root(raw_dir) / "_changes" / dataset
    stems = sorted(p.name for p in folder.glob("*") if p.is_dir())
    if ds.per_season:
        if season is None:
            raise ValueError(f"{dataset} has one file per season: pass season=")
        stems = [s for s in stems if s.endswith(f"_{season}")]
    if len(stems) != 1:
        raise LookupError(f"No change log for {dataset} (season {season}) under {folder}")
    state = ChangeLog(folder / stems[0]).state(at)
    if state is None:
        raise LookupError(f"Nothing recorded for {dataset} at or before {at}")
    return state


def data_version(raw_dir: Path | None = None) -> str:
    """A fingerprint of every nflverse file we hold. MLflow logs it with every run."""
    return Manifest(_root(raw_dir) / "_manifest").data_version()
