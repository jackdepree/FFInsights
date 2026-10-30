"""How raw data is stored, whatever the source: safe writes, the manifest, change logs and
revision reports (projects/data-layer/BRIEF.md). Source modules (e.g. `nflverse`) fetch; this
module decides how what they fetch is kept.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

# Every manifest row has exactly these columns, so files from different runs always stack.
MANIFEST_SCHEMA = {
    "run_at": pl.Datetime("us", "UTC"),
    "dataset": pl.String,
    "file": pl.String,  # the upstream file name
    "season": pl.Int32,  # null for files that cover every season
    "action": pl.String,  # see ACTIONS
    "stored": pl.Boolean,  # False when only the upstream version was recorded (no file kept)
    "path": pl.String,  # relative to the raw zone, forward slashes
    "url": pl.String,
    "upstream_version": pl.String,  # sha256 digest or git blob sha: changes iff the content does
    "upstream_updated_at": pl.Datetime("us", "UTC"),
    "size_bytes": pl.Int64,
    "sha256": pl.String,
}
ACTIONS = ("new", "replaced", "change_log", "seen")

# A change log writes a full copy (a base) after this many deltas, so rebuilding a state never
# has to replay more than a season's worth of daily changes.
REBASE_EVERY = 90


def utc_stamp(at: datetime) -> str:
    """`2026-10-30 18:51:07 UTC` -> `20261030T185107Z`, the timestamp used in file names."""
    return require_utc(at).strftime("%Y%m%dT%H%M%SZ")


def parse_stamp(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)


def require_utc(at: datetime) -> datetime:
    """Timestamps are always timezone-aware (CONVENTIONS.md). Naive ones are refused."""
    if at.tzinfo is None:
        raise ValueError(f"{at} has no timezone. Pass a UTC-aware datetime.")
    return at.astimezone(UTC)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def atomic_path(dest: Path) -> Iterator[Path]:
    """Yield a temporary path next to `dest`; move it into place only if the block succeeds.

    A crash or error mid-write leaves `dest` as it was and no partial file behind.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        yield tmp
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def write_parquet_atomic(df: pl.DataFrame, dest: Path) -> None:
    with atomic_path(dest) as tmp:
        df.write_parquet(tmp)


# ---------------------------------------------------------------------------- the manifest


class Manifest:
    """An append-only log of every file a source downloaded: one Parquet file per run.

    One file per run (never rewriting old ones) keeps it append-only by construction and keeps
    git small where the manifest lives in pcf-data.
    """

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def append(
        self, rows: Sequence[dict[str, Any]], run_at: datetime, part: str = "all"
    ) -> Path | None:
        """Write one run's rows (or one part of a run, e.g. one dataset) as a new file."""
        if not rows:
            return None
        dest = self.folder / f"{utc_stamp(run_at)}_{part}.parquet"
        if dest.exists():
            raise FileExistsError(f"A manifest for this run time already exists: {dest}")
        df = pl.DataFrame(
            [{"run_at": require_utc(run_at), **r} for r in rows], schema=MANIFEST_SCHEMA
        )
        bad = set(df["action"]) - set(ACTIONS)
        if bad:
            raise ValueError(f"Unknown manifest actions: {bad}")
        write_parquet_atomic(df, dest)
        return dest

    def read(self) -> pl.DataFrame:
        files = sorted(self.folder.glob("*.parquet"))
        if not files:
            return pl.DataFrame(schema=MANIFEST_SCHEMA)
        return pl.concat([pl.read_parquet(f) for f in files], how="vertical")

    def latest_versions(self) -> dict[tuple[str, str], str]:
        """(dataset, upstream file) -> the upstream version we last fetched."""
        df = self.read().filter(pl.col("action") != "change_log")
        if df.is_empty():
            return {}
        last = df.sort("run_at").group_by("dataset", "file").last()
        return {
            (r["dataset"], r["file"]): r["upstream_version"] for r in last.iter_rows(named=True)
        }

    def data_version(self) -> str:
        """A fingerprint of every stored file as it is now. Changes when any file changes."""
        df = self.read().filter(pl.col("stored"))
        if df.is_empty():
            return "empty"
        last = df.sort("run_at").group_by("path").last().sort("path")
        text = "\n".join(f"{p}:{s}" for p, s in zip(last["path"], last["sha256"], strict=True))
        return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------- row identity

_HASH = "__pcf_row_hash"
_OCC = "__pcf_row_occurrence"


def _with_identity(df: pl.DataFrame) -> pl.DataFrame:
    """Add a content hash per row, plus which copy of that content it is (identical rows exist).

    Hashes are compared only within one process, so polars changing its hash between versions
    can't matter: both sides are always hashed by the same code.
    """
    return df.with_columns(df.hash_rows(seed=0).alias(_HASH)).with_columns(
        pl.int_range(pl.len()).over(_HASH).alias(_OCC)
    )


def diff_rows(old: pl.DataFrame, new: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Rows in `new` but not `old`, and rows in `old` but not `new`, counting duplicates.

    Both frames must have the same schema (names, order and types).
    """
    if old.schema != new.schema:
        raise ValueError("diff_rows needs identical schemas")
    a, b = _with_identity(old), _with_identity(new)
    on = [_HASH, _OCC]
    added = b.join(a.select(on), on=on, how="anti").drop(on)
    removed = a.join(b.select(on), on=on, how="anti").drop(on)
    return added, removed


# ---------------------------------------------------------------------------- change logs

_CHANGE = "__pcf_change"


class ChangeLog:
    """Dated history of a file that gets overwritten upstream (a state source).

    The first entry is a full copy (a base). Later entries hold only the rows added and removed
    since the previous state, so a daily snapshot of an 11 MB file costs kilobytes. A new base is
    written when the columns change or after REBASE_EVERY deltas.
    """

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def entries(self, at: datetime | None = None) -> list[tuple[datetime, str, Path]]:
        """(time, "base" or "delta", file), oldest first. Named `<stamp>_<kind>.parquet`."""
        found = []
        for p in self.folder.glob("*.parquet"):
            stamp, _, kind = p.stem.partition("_")
            found.append((parse_stamp(stamp), kind, p))
        found.sort()
        if at is not None:
            found = [e for e in found if e[0] <= require_utc(at)]
        return found

    def state(self, at: datetime | None = None) -> pl.DataFrame | None:
        """The file's content as of `at` (default: latest). None if nothing was recorded by then.

        Row order isn't preserved; treat the result as a set of rows.
        """
        entries = self.entries(at)
        if not entries:
            return None
        start = max(i for i, (_, kind, _) in enumerate(entries) if kind == "base")
        state = pl.read_parquet(entries[start][2]).drop(_CHANGE)
        for _, _, path in entries[start + 1 :]:
            delta = pl.read_parquet(path)
            removed = delta.filter(pl.col(_CHANGE) == "remove").drop(_CHANGE)
            added = delta.filter(pl.col(_CHANGE) == "add").drop(_CHANGE)
            if not removed.is_empty():
                counts = _with_identity(removed).group_by(_HASH).agg(pl.len().alias("__pcf_n"))
                state = (
                    _with_identity(state)
                    .join(counts, on=_HASH, how="left")
                    .filter(pl.col(_OCC) >= pl.col("__pcf_n").fill_null(0))
                    .drop(_HASH, _OCC, "__pcf_n")
                )
            state = pl.concat([state, added], how="vertical")
        return state

    def record(self, new: pl.DataFrame, at: datetime) -> Path | None:
        """Log `new` as the state at `at`. Returns the file written, or None if nothing changed."""
        at = require_utc(at)
        entries = self.entries()
        if entries and entries[-1][0] >= at:
            raise ValueError(f"Change log {self.folder} already has an entry at or after {at}")
        prev = self.state()
        kinds = [kind for _, kind, _ in entries]
        deltas_since_base = kinds[::-1].index("base") if kinds else 0

        if prev is None or prev.schema != new.schema or deltas_since_base >= REBASE_EVERY:
            dest = self.folder / f"{utc_stamp(at)}_base.parquet"
            write_parquet_atomic(new.with_columns(pl.lit("base").alias(_CHANGE)), dest)
            return dest
        dest = self.folder / f"{utc_stamp(at)}_delta.parquet"
        added, removed = diff_rows(prev, new)
        if added.is_empty() and removed.is_empty():
            return None
        delta = pl.concat(
            [
                added.with_columns(pl.lit("add").alias(_CHANGE)),
                removed.with_columns(pl.lit("remove").alias(_CHANGE)),
            ],
            how="vertical",
        )
        write_parquet_atomic(delta, dest)
        return dest


# ---------------------------------------------------------------------------- revision reports


@dataclass
class Revision:
    """What changed when a stored history file was replaced by a new upstream version."""

    dataset: str
    file: str
    rows_before: int
    rows_after: int
    columns_added: list[str] = field(default_factory=list)
    columns_removed: list[str] = field(default_factory=list)
    keyed: bool = False  # True when rows could be matched on the dataset's keys
    keys_lost: int = 0  # keyed: rows whose key disappeared
    keys_new: int = 0
    changed_columns: dict[str, int] = field(default_factory=dict)  # keyed: column -> rows changed
    rows_added: int = 0  # by content, counting duplicates
    rows_removed: int = 0
    watched_missing: list[str] = field(default_factory=list)  # info: catalog checks cover it
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def usable_keys(df: pl.DataFrame, keys: Sequence[str]) -> bool:
    """Keys work for matching when present and unique among rows where none of them is null."""
    if not keys or any(k not in df.columns for k in keys):
        return False
    rows = df.select(keys).drop_nulls()
    return rows.height == rows.unique().height


def _changed_count(joined: pl.DataFrame, col: str, old_type: pl.DataType) -> int:
    a, b = pl.col(col), pl.col(f"{col}__new")
    if joined.schema[f"{col}__new"] != old_type:
        a, b = a.cast(pl.String), b.cast(pl.String)
    try:
        return joined.select(a.ne_missing(b).sum()).item()
    except pl.exceptions.InvalidOperationError:  # types without equality: compare hashes
        return joined.select(a.hash(seed=0).ne_missing(b.hash(seed=0)).sum()).item()


def compare_versions(
    dataset: str,
    file: str,
    old: pl.DataFrame,
    new: pl.DataFrame,
    keys: Sequence[str] = (),
    watched: Sequence[str] = (),
) -> Revision:
    """The revision report for one replaced history file (projects/data-layer/BRIEF.md)."""
    rev = Revision(dataset, file, old.height, new.height)
    rev.columns_added = [c for c in new.columns if c not in old.columns]
    rev.columns_removed = [c for c in old.columns if c not in new.columns]
    rev.watched_missing = [c for c in watched if c not in new.columns]
    shared = [c for c in old.columns if c in new.columns]

    old_s, new_s = old.select(shared), new.select(shared)
    if old_s.schema == new_s.schema:
        added, removed = diff_rows(old_s, new_s)
        rev.rows_added, rev.rows_removed = added.height, removed.height
    else:  # types changed: compare as text
        added, removed = diff_rows(
            old_s.with_columns(pl.all().cast(pl.String)),
            new_s.with_columns(pl.all().cast(pl.String)),
        )
        rev.rows_added, rev.rows_removed = added.height, removed.height

    same_key_types = all(
        k in old.columns and k in new.columns and old.schema[k] == new.schema[k] for k in keys
    )
    if same_key_types and usable_keys(old, keys) and usable_keys(new, keys):
        rev.keyed = True
        k = list(keys)
        o, n = old.drop_nulls(k), new.drop_nulls(k)
        rev.keys_lost = o.join(n.select(k), on=k, how="anti").height
        rev.keys_new = n.join(o.select(k), on=k, how="anti").height
        others = [c for c in shared if c not in k]
        joined = o.select(k + others).join(n.select(k + others), on=k, how="inner", suffix="__new")
        for c in others:
            count = _changed_count(joined, c, old.schema[c])
            if count:
                rev.changed_columns[c] = count

    watched_changed = sorted(c for c in watched if rev.changed_columns.get(c))
    if watched_changed:
        rev.flags.append(f"watched columns changed: {', '.join(watched_changed)}")
    if rev.keys_lost:
        rev.flags.append(f"{rev.keys_lost} rows' keys disappeared")
    if not rev.keyed and rev.rows_after < rev.rows_before:
        rev.flags.append(f"rows dropped from {rev.rows_before} to {rev.rows_after}")
    if rev.columns_removed:
        rev.flags.append(f"columns removed: {', '.join(rev.columns_removed)}")
    return rev


def save_revisions(revisions: Sequence[Revision], folder: Path, run_at: datetime) -> Path | None:
    if not revisions:
        return None
    dest = folder / f"{utc_stamp(run_at)}.json"
    with atomic_path(dest) as tmp:
        tmp.write_text(json.dumps([r.to_dict() for r in revisions], indent=2), encoding="utf-8")
    return dest
