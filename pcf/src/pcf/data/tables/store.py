"""Saving table parts and reading a table back as it was known at a moment (decision 0008).

A part lives at `<tables zone>/<table>/<part>/season=YYYY/data.parquet`. `load` joins the parts
known at a moment onto the spine; the gateway (`validation-harness`) wraps it.
"""

import os
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.core.log import get_logger
from pcf.data.schemas import KNOWN_AT, check_parts, table

log = get_logger(__name__)

FILE = "data.parquet"


def _root(root: Path | None) -> Path:
    return root or get_config().zone("tables")


def part_dir(name: str, part: str, root: Path | None = None) -> Path:
    return _root(root) / name / part


def write_parts(
    parts: Mapping[str, pl.DataFrame],
    name: str,
    seasons: Sequence[int],
    root: Path | None = None,
) -> None:
    """Check the parts together, then write one file per part and season. Every season in
    `seasons` is replaced: a part with no rows that season has its old file removed."""
    parts = {p: df.with_columns(pl.col("known_at").cast(KNOWN_AT)) for p, df in parts.items()}
    check_parts(parts, name)
    for part, df in parts.items():
        for season in seasons:
            path = part_dir(name, part, root) / f"season={season}" / FILE
            rows = df.filter(pl.col("season") == season)
            if rows.is_empty():
                path.unlink(missing_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            rows.write_parquet(tmp)
            os.replace(tmp, path)
        log.info("%s.%s: %d rows written", name, part, df.height)


def files(
    name: str, part: str, seasons: Sequence[int] | None = None, root: Path | None = None
) -> list[Path]:
    """A part's files, oldest season first."""
    found = []
    for path in part_dir(name, part, root).glob(f"season=*/{FILE}"):
        season = int(path.parent.name.removeprefix("season="))
        if seasons is None or season in seasons:
            found.append((season, path))
    return [p for _, p in sorted(found)]


def _scan(name: str, part: str, seasons: Sequence[int] | None, root: Path | None) -> pl.LazyFrame:
    """A part over the given seasons. Seasons it has no rows for still give its columns."""
    every = files(name, part, None, root)
    if not every:
        raise FileNotFoundError(f"{name}.{part} isn't built. Run `pcf tables build {name}`.")
    chosen = every if seasons is None else files(name, part, seasons, root)
    if not chosen:
        return pl.scan_parquet(every[0]).head(0)
    return pl.concat([pl.scan_parquet(p) for p in chosen], how="diagonal_relaxed")


def load(
    name: str,
    at: datetime | None = None,
    seasons: Sequence[int] | None = None,
    parts: Sequence[str] | None = None,
    root: Path | None = None,
) -> pl.DataFrame:
    """A table as it was known at `at` (UTC; everything if None): spine rows known by then, with
    each part's columns where that part's row was known by then and empty otherwise. `known_at`
    is the spine's; each other part's is `<part>_known_at`. `parts` picks some parts (the spine
    always comes)."""
    t = table(name)
    chosen = [t.spine, *(p for p in (t.parts if parts is None else parts) if p != t.spine)]
    unknown = set(chosen) - set(t.parts)
    if unknown:
        raise ValueError(f"{name} has no parts {sorted(unknown)}. Parts: {', '.join(t.parts)}")
    if at is not None and at.tzinfo is None:
        raise ValueError("at must be timezone-aware")

    def known(part: str) -> pl.LazyFrame:
        lf = _scan(name, part, seasons, root)
        return lf if at is None else lf.filter(pl.col("known_at") <= pl.lit(at).cast(KNOWN_AT))

    out = known(t.spine)
    for part in chosen[1:]:
        rows = known(part).drop("season").rename({"known_at": f"{part}_known_at"})
        out = out.join(rows, on=t.key_names, how="left", maintain_order="left")
    return out.collect()
