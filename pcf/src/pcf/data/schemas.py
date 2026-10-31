"""The table contract (docs/ARCHITECTURE.md, "Storage"; decision 0008).

Each table is saved as parts that share its keys. The first part is the spine: it decides which
rows the table has. Every other part holds one source's columns with that source's `known_at`.
Every part has the keys, an Int32 `season` and a UTC `known_at`, and is checked before it's written.
"""

from collections.abc import Mapping
from dataclasses import dataclass

import polars as pl

from pcf.data.timeline import check_known_at

# Columns every part has besides its keys.
PART_COLUMNS = ("season", "known_at")
KNOWN_AT = pl.Datetime("us", "UTC")


@dataclass(frozen=True)
class Table:
    name: str
    keys: tuple[tuple[str, pl.DataType], ...]
    parts: tuple[str, ...]  # the spine first

    @property
    def key_names(self) -> list[str]:
        return [k for k, _ in self.keys]

    @property
    def spine(self) -> str:
        return self.parts[0]


_GAME = ("game_id", pl.String)
_TEAM = ("team", pl.String)
_PLAY = ("play_id", pl.Int64)
_PLAYER = ("gsis_id", pl.String)

TABLES: dict[str, Table] = {
    t.name: t
    for t in [
        Table("game", (_GAME,), ("schedule", "pregame", "result")),
        Table("team_game", (_GAME, _TEAM), ("schedule", "pregame", "result", "stats")),
        Table("play", (_GAME, _PLAY), ("pbp", "participation", "ftn")),
        Table("player_play", (_GAME, _PLAY, _PLAYER), ("on_field",)),
        Table(
            "player_game",
            (_PLAYER, _GAME),
            (
                "roster",
                "game_status",
                "injury",
                "depth",
                "stats",
                "snaps",
                "ff_opportunity",
                "ngs",
                "pfr",
            ),
        ),
    ]
}


def table(name: str) -> Table:
    if name not in TABLES:
        raise ValueError(f"no table {name!r}. Tables: {', '.join(TABLES)}")
    return TABLES[name]


def check_part(df: pl.DataFrame, name: str, part: str) -> None:
    """One part against the contract: its table's keys with their types and no nulls, unique
    keys, an Int32 `season` with no nulls, and a valid `known_at` (leakage check 2)."""
    t = table(name)
    if part not in t.parts:
        raise ValueError(f"{name} has no part {part!r}. Parts: {', '.join(t.parts)}")
    where = f"{name}.{part}"
    for col, dtype in (*t.keys, ("season", pl.Int32)):
        if col not in df.columns:
            raise ValueError(f"{where}: no {col} column")
        if df.schema[col] != dtype:
            raise ValueError(f"{where}: {col} is {df.schema[col]}, not {dtype}")
        if df[col].null_count():
            raise ValueError(f"{where}: {df[col].null_count()} rows have no {col}")
    dupes = df.select(t.key_names).is_duplicated().sum()
    if dupes:
        raise ValueError(f"{where}: {dupes} rows share their keys")
    check_known_at(df)


def check_parts(parts: Mapping[str, pl.DataFrame], name: str) -> None:
    """Parts built together: each passes `check_part`, no column comes from two parts, and every
    part's keys are on the spine."""
    t = table(name)
    shared = {*t.key_names, *PART_COLUMNS}
    owner: dict[str, str] = {}
    for part, df in parts.items():
        check_part(df, name, part)
        for col in set(df.columns) - shared:
            if col in owner:
                raise ValueError(f"{name}: {col} is in both {owner[col]} and {part}")
            owner[col] = part
    if t.spine in parts:
        spine = parts[t.spine].select(t.key_names)
        for part, df in parts.items():
            off = df.join(spine, on=t.key_names, how="anti").height
            if off:
                raise ValueError(f"{name}.{part}: {off} rows aren't on the spine")
