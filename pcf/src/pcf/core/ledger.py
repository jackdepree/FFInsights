"""The prediction ledger (projects/prediction-ledger/BRIEF.md): every forecast made before kickoff,
kept where it can't quietly change.

- **One folder per run**, `<record>/<season>/<stamp>_<label>/`, created once: a second run with the
  same name fails instead of writing into it.
- **One file per model**, opened for exclusive creation, so nothing is ever overwritten. `run.json`
  is written last, with each file's sha256. A folder without `run.json` didn't finish, and its
  rows are never counted.
- **No forecast after kickoff.** Rows for games that have started are left out of a live run and
  counted in `run.json`. A row whose `as_of` is later than the moment it's written is refused.
- **Every row can be traced:** model, code commit, training cutoff, when the data was pulled.
- **Replays** (forecasts remade later, `record="replay"`) go under `replay/`, never `ledger/`.
- **Counted:** a model's first finished live forecast for a row. Later reruns are kept but never
  replace it, so nothing can be picked after the fact.

The root is a sparse clone of the private `pcf-data` repo (config `[ledger]`), and `push` commits
and pushes a run, so GitHub's own record says when it existed. Nothing football-specific lives
here: the live run is `pcf.validation.live`.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from pcf.config import PCF_DIR, get_config
from pcf.core.contract import OUTPUT_SCHEMA, SPIKE_PARTS, UTC_TIME, check_output
from pcf.core.log import get_logger

log = get_logger(__name__)
c = pl.col

RECORDS = ("live", "replay")
RUN_FILE = "run.json"
# What the ledger adds to the standard output. The market columns stay empty until a product
# brings its line (brief: closing line value is measured there).
LEDGER_COLUMNS: dict[str, pl.DataType] = {
    "kickoff": UTC_TIME,
    "record": pl.String(),
    "ledger_run": pl.String(),
    "written_at": UTC_TIME,
    "commit": pl.String(),
    "pulled_at": UTC_TIME,
    "market_line": pl.Float64(),
    "market_price": pl.Float64(),
    "market_book": pl.String(),
    "market_at": UTC_TIME,
}
# Code whose changes would change a forecast. A live run refuses to start if any is uncommitted.
CODE_PATHS = ("src", "config.toml", "uv.lock", "pyproject.toml")


class LedgerRefused(RuntimeError):
    """A write the ledger won't make: a forecast from the future, or a live run of code that isn't
    committed."""


def stamp(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def root(record: str = "live", clone: Path | None = None) -> Path:
    if record not in RECORDS:
        raise ValueError(f"record must be one of {RECORDS}")
    base = clone or get_config().ledger_clone
    return base / ("ledger" if record == "live" else "replay")


def file_name(model: str) -> str:
    """`participation/trees_week` -> `participation__trees_week.parquet`."""
    return model.replace("/", "__") + ".parquet"


def code_state(repo: Path = PCF_DIR) -> dict[str, Any]:
    """The commit this code is at, its branch, and the uncommitted files that would change a
    forecast."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    dirty = git("status", "--porcelain", "--", *CODE_PATHS).splitlines()
    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": [line[3:] for line in dirty],
    }


@dataclass
class Run:
    """One run's folder. `write` each model's rows, then `close` with the run's details."""

    folder: Path
    record: str
    started: datetime
    commit: str
    pulled_at: datetime | None
    files: dict[str, dict[str, Any]] = field(default_factory=dict)
    closed: bool = False

    @property
    def name(self) -> str:
        return self.folder.name

    def write(
        self,
        model: str,
        rows: pl.DataFrame,
        keys: list[str],
        kind: str = "amount",
        now: datetime | None = None,
        publishes: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Write one model's forecasts: the standard output plus `kickoff`, and the columns the
        expert `publishes` for higher layers (Elo's ratings). Live rows for games that have kicked
        off by now are left out. Returns what was written and left out."""
        if self.closed:
            raise LedgerRefused(f"{self.name} is closed")
        now = (now or datetime.now(UTC)).astimezone(UTC)
        if rows.filter(c("as_of") > now).height:
            raise LedgerRefused(f"{model}: rows with as_of after the moment they're written")
        if "kickoff" not in rows.columns or rows["kickoff"].null_count():
            raise LedgerRefused(f"{model}: every row needs its kickoff")
        late = rows.filter(c("kickoff") <= now) if self.record == "live" else rows.clear()
        keep = rows.filter(c("kickoff") > now) if self.record == "live" else rows
        missing = [x for x in publishes if x not in rows.columns]
        if missing:
            raise LedgerRefused(f"{model}: published columns missing: {', '.join(missing)}")
        check_output(
            keep.drop([x for x in (*LEDGER_COLUMNS, *publishes) if x in keep.columns]), keys, kind
        )
        extra = {k: v for k, v in SPIKE_PARTS.items() if k in keep.columns}
        out = keep.with_columns(
            record=pl.lit(self.record),
            ledger_run=pl.lit(self.name),
            written_at=pl.lit(now),
            commit=pl.lit(self.commit),
            pulled_at=pl.lit(self.pulled_at),
            **{k: pl.lit(None) for k in LEDGER_COLUMNS if k.startswith("market_")},
        ).select(
            *keys,
            *(c(k).cast(v) for k, v in {**OUTPUT_SCHEMA, **extra, **LEDGER_COLUMNS}.items()),
            *publishes,
        )
        path = self.folder / file_name(model)
        with path.open("xb") as f:  # exclusive: an existing file is never replaced
            out.write_parquet(f)
        info = {
            "file": path.name,
            "rows": out.height,
            "left_out_after_kickoff": late.height,
            "games": out["game_id"].n_unique() if "game_id" in out.columns else None,
            "written_at": now.isoformat(),
            "sha256": _sha256(path),
        }
        if late.height:
            log.warning("%s: %d rows left out, their games had kicked off", model, late.height)
        self.files[model] = info
        return info

    def close(self, details: dict[str, Any]) -> Path:
        """Write `run.json`, which marks the run finished. Nothing more can be written."""
        body = {
            "run": self.name,
            "record": self.record,
            "started": self.started.isoformat(),
            "finished": datetime.now(UTC).isoformat(),
            "commit": self.commit,
            "pulled_at": self.pulled_at.isoformat() if self.pulled_at else None,
            "models": self.files,
            **details,
        }
        path = self.folder / RUN_FILE
        with path.open("x", encoding="utf-8") as f:
            json.dump(body, f, indent=2, default=str)
        self.closed = True
        return path


def open_run(
    season: int,
    label: str,
    started: datetime,
    commit: str,
    pulled_at: datetime | None,
    record: str = "live",
    clone: Path | None = None,
) -> Run:
    """A new run folder. Fails if one with this name exists."""
    folder = root(record, clone) / str(season) / f"{stamp(started)}_{label}"
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.mkdir(exist_ok=False)
    return Run(folder, record, started.astimezone(UTC), commit, pulled_at)


def read(record: str = "live", clone: Path | None = None, counted: bool = True) -> pl.DataFrame:
    """Every finished run's rows. `counted` keeps only each model's first forecast per row."""
    base = root(record, clone)
    frames = []
    for done in sorted(base.glob(f"*/*/{RUN_FILE}")):
        for path in sorted(done.parent.glob("*.parquet")):
            frames.append(pl.read_parquet(path))
    if not frames:
        return pl.DataFrame()
    rows = pl.concat(frames, how="diagonal_relaxed")
    if not counted:
        return rows
    keys = [k for k in ("gsis_id", "game_id", "team", "season") if k in rows.columns]
    return rows.sort("written_at").unique([*keys, "model", "quantity"], keep="first")


# ------------------------------------------------------------------------- the pcf-data clone


def _git(clone: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def ensure_clone(clone: Path | None = None, remote: str | None = None) -> Path:
    """A sparse clone of pcf-data holding only `ledger/` and `replay/`, made if missing, and
    brought up to date. Uses the PC's own git sign-in; no key passes through PCF."""
    cfg = get_config()
    clone = clone or cfg.ledger_clone
    if not (clone / ".git").exists():
        clone.parent.mkdir(parents=True, exist_ok=True)
        _git(
            clone.parent,
            "clone",
            "--filter=blob:none",
            "--sparse",
            remote or cfg.ledger_remote,
            clone.name,
        )
        _git(clone, "sparse-checkout", "set", "ledger", "replay")
    _git(clone, "pull", "--rebase", "--quiet")
    return clone


def push(folder: Path, message: str, clone: Path | None = None) -> str:
    """Commit one run's folder to pcf-data and push it. Returns the pcf-data commit."""
    clone = clone or get_config().ledger_clone
    _git(clone, "add", "--sparse", str(folder.relative_to(clone)))
    _git(clone, "commit", "--quiet", "-m", message)
    _git(clone, "pull", "--rebase", "--quiet")
    _git(clone, "push", "--quiet")
    return _git(clone, "rev-parse", "HEAD")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
