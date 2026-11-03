"""The as_of gateway: the only way models read data (docs/ARCHITECTURE.md, "Point-in-time").

    gateway = Gateway()
    view = gateway.view(moment, cadence="in_season", inputs=Expert.inputs)
    plays = view.table("play")       # each part's rows known at the moment, joined on the spine

A view:
- shows each part's rows known at its moment (`known_at` ≤ the moment), like `tables.load`;
- in season, shows post-season-only parts (participation) only for finished seasons (rule m,
  leakage check 5), whatever their `known_at` says;
- refuses tables, parts and model outputs the model didn't declare;
- shows a model's outputs only where they were made by the moment, and refuses any row whose
  model was trained after it was made (`train_end` > `as_of`: the vintage rule, check 6).

A gateway keeps each part it reads in memory, so a backtest's hundreds of views cost a filter each.
Revised (snapshotted) sources have no table yet (validation-harness#F8); they'd join here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import polars as pl

from pcf.config import get_config
from pcf.data.schemas import KNOWN_AT, table
from pcf.data.tables.store import assemble, chosen_parts, read_part, visible
from pcf.data.timeline import Calendar, calendar
from pcf.data.timeline.moments import season_ends

c = pl.col
HISTORY = "history.parquet"
# The far future: a view that sees everything known so far (targets for scoring).
END_OF_TIME = datetime(2100, 1, 1, tzinfo=UTC)


class UndeclaredInput(PermissionError):
    """A model asked for a table, part or output it didn't declare in `inputs`."""


class VintageError(ValueError):
    """A model output whose model was trained after the output was made (check 6)."""


class Source(Protocol):
    def part(self, name: str, part: str) -> pl.DataFrame: ...


class TableSource:
    """The built tables: each part read once (all seasons, or `seasons`) and kept in memory."""

    def __init__(self, root: Path | None = None, seasons: Sequence[int] | None = None):
        self.root = root
        self.seasons = None if seasons is None else list(seasons)
        self._cache: dict[tuple[str, str], pl.DataFrame] = {}

    def part(self, name: str, part: str) -> pl.DataFrame:
        key = (name, part)
        if key not in self._cache:
            self._cache[key] = read_part(name, part, self.seasons, self.root).collect()
        return self._cache[key]


class FrameSource:
    """Parts given as frames, keyed by (table, part): synthetic worlds and perturbed ones."""

    def __init__(self, frames: Mapping[tuple[str, str], pl.DataFrame]):
        self.frames = dict(frames)

    def part(self, name: str, part: str) -> pl.DataFrame:
        if (name, part) not in self.frames:
            raise FileNotFoundError(f"{name}.{part} isn't in this source")
        return self.frames[(name, part)]


def stored_outputs(project_id: str, version: int) -> pl.DataFrame:
    """A registered model version's walk-forward history: `outputs/<id>/<run_id>/history.parquet`,
    with the run found from the version in MLflow."""
    from pcf.core import tracking

    run_id = tracking.version_run(project_id, version)
    return pl.read_parquet(get_config().zone("outputs") / project_id / run_id / HISTORY)


class Gateway:
    """Views of the world at moments. `source` defaults to the built tables, `cal` to the
    calendar built from `game.schedule`, `outputs` to the stored model histories."""

    def __init__(
        self,
        source: Source | None = None,
        cal: Calendar | None = None,
        outputs: Callable[[str, int], pl.DataFrame] | None = None,
    ):
        self.source = source or TableSource()
        self._cal = cal
        self.outputs = outputs or stored_outputs
        self._ends: dict[int, datetime] | None = None
        self._output_cache: dict[tuple[str, int], pl.DataFrame] = {}

    @property
    def calendar(self) -> Calendar:
        if self._cal is None:
            self._cal = calendar(self.source.part("game", "schedule"))
        return self._cal

    def finished(self, at: datetime) -> list[int]:
        """Seasons whose Super Bowl week ended by `at`."""
        if self._ends is None:
            self._ends = season_ends(self.calendar)
        return [s for s, end in self._ends.items() if end <= at]

    def output(self, project_id: str, version: int) -> pl.DataFrame:
        key = (project_id, version)
        if key not in self._output_cache:
            self._output_cache[key] = self.outputs(project_id, version)
        return self._output_cache[key]

    def view(self, at: datetime, cadence: str, inputs: Mapping[str, tuple[str, ...] | int]) -> View:
        if at.tzinfo is None:
            raise ValueError("a view's moment must be timezone-aware")
        return View(self, at, cadence, inputs)


class View:
    """The world as known at one moment, limited to a model's declared inputs."""

    def __init__(
        self,
        gateway: Gateway,
        at: datetime,
        cadence: str,
        inputs: Mapping[str, tuple[str, ...] | int],
    ):
        self._gateway = gateway
        self.at = at
        self.cadence = cadence
        self.inputs = dict(inputs)

    def table(self, name: str, seasons: Sequence[int] | None = None) -> pl.DataFrame:
        """A declared table at this moment: its spine and declared parts (`seasons`: only these)."""
        declared = self.inputs.get(name)
        if declared is None or isinstance(declared, int):
            raise UndeclaredInput(f"table {name!r} isn't in this model's inputs")
        t = table(name)
        hidden: list[int] | None = None
        if self.cadence == "in_season" and t.post_season:
            hidden = self._gateway.finished(self.at)
        frames = {}
        for part in chosen_parts(name, declared):
            frame = self._gateway.source.part(name, part).lazy()
            if seasons is not None:
                frame = frame.filter(c("season").is_in(list(seasons)))
            frame = visible(frame, self.at)
            if hidden is not None and part in t.post_season:
                frame = frame.filter(c("season").is_in(hidden))
            frames[part] = frame
        return assemble(name, frames)

    def output(self, project_id: str) -> pl.DataFrame:
        """A declared model's outputs made by this moment (`as_of` ≤ it). An in-season view sees a
        retrospective model's rows only for finished seasons (rule m)."""
        version = self.inputs.get(project_id)
        if not isinstance(version, int):
            raise UndeclaredInput(f"model {project_id!r} isn't in this model's inputs")
        df = self._gateway.output(project_id, version)
        moment = pl.lit(self.at).cast(KNOWN_AT)
        df = df.filter(c("as_of") <= moment)
        bad = df.filter(c("train_end").is_null() | (c("train_end") > c("as_of"))).height
        if bad:
            raise VintageError(
                f"{project_id} v{version}: {bad} rows were made by a model trained after them"
            )
        if self.cadence == "in_season" and "season" in df.columns:
            retro = c("cadence") == "retrospective"
            done = c("season").is_in(self._gateway.finished(self.at))
            df = df.filter(~retro | done)
        return df
