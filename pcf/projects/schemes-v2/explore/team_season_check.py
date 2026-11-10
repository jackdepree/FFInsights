"""The retrospective traits table (`team_season.charted`, decision 0026), 2026-11-10: a profile, a
football sanity list, the two tests' consistency half, and how much the fullback fix moves.

1. **Profile:** rows, games and plays per season, the league's raw rates, and where columns are
   empty.
2. **Sanity:** the top and bottom three team-seasons on a few traits with a known football story.
3. **Consistency** (`pcf.validation.consistency`): each over-expected trait per team-game, odd
   weeks against even, and season to season. Regular season, 2016-2025 (the vault season's
   participation is in the table: it describes 2025, it doesn't forecast it).
4. **The fullback fix:** how many charted neutral dropbacks change their heavy flag, by season.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/team_season_check.py
"""

# ruff: noqa: E501
from __future__ import annotations

import polars as pl

from pcf.data.clean import personnel
from pcf.data.sources.nflverse import scan
from pcf.data.tables import load
from pcf.data.tables.charted import PBP_COLUMNS
from pcf.data.tables.team_season import (
    DEFENSE,
    FACED,
    OFFENSE,
    PARTICIPATION_COLUMNS,
    charted_plays,
)
from pcf.validation.consistency import consistency

c = pl.col
SEASONS = range(2016, 2026)


def profile(ts: pl.DataFrame) -> None:
    print("== 1. Profile")
    print(f"  {ts.height} team-seasons, {ts['season'].n_unique()} seasons, known_at from {ts['known_at'].min()} to {ts['known_at'].max()}")
    league = ts.group_by("season").agg(
        n=pl.len(),
        games=c("games").mean(),
        off_plays=c("off_plays").mean(),
        **{
            k: c(k).mean()
            for k in ["off_11_rate", "off_12_rate", "off_21_rate", "off_heavy_rate", "off_pistol_rate", "off_time_to_throw",
                      "def_box", "def_man_rate", "def_two_high_rate", "def_blitz_rate", "def_rushers", "def_nickel_rate", "def_dime_rate"]
        },
    ).sort("season")
    with pl.Config(tbl_cols=20, tbl_width_chars=250, float_precision=3):
        print(league)
    empty = {k: v for k, v in ts.null_count().row(0, named=True).items() if v}
    print(f"  empty cells: {empty}")
    for o in ("prior_for",):
        assert (ts[o] == ts["season"] + 1).all()
    assert (ts["known_at"] > ts["last_kickoff"]).all(), "a row known before its last game"


def sanity(ts: pl.DataFrame) -> None:
    print("\n== 2. Sanity: top and bottom three team-seasons")
    for col in ("off_21_rate", "off_pistol_rate", "def_man_rate_oe", "def_two_high_rate_oe", "def_blitz_rate_oe", "off_time_to_throw_oe"):
        x = ts.drop_nulls(col).sort(col)
        lab = lambda d, col=col: ", ".join(f"{r['season']} {r['team']} {r[col]:+.3f}" for r in d.iter_rows(named=True))  # noqa: E731
        print(f"  {col}: top {lab(x.tail(3).reverse())} | bottom {lab(x.head(3))}")


def game_rows() -> pl.DataFrame:
    """Per team-game over-expected traits (offense, faced and defense), regular season."""
    out = []
    for s in SEASONS:
        pbp = scan("pbp", [s]).select(*PBP_COLUMNS, "season_type", "week").collect()
        part = scan("participation", [s]).select(PARTICIPATION_COLUMNS).collect()
        reg = pbp.filter(c("season_type") == "REG").select("game_id", "week").unique()
        plays = charted_plays(pbp.drop("season_type", "week"), part).join(reg, on="game_id")
        off = plays.group_by("game_id", "week", "season", team="posteam").agg(
            *(c(f"{x}_ro").mean().alias(f"{col}_oe") for col, x in OFFENSE),
            *(c(f"{x}_rl").mean().alias(f"{col}_oe") for col, x in FACED),
        )
        de = plays.group_by("game_id", team="defteam").agg(
            c(f"{x}_rl").mean().alias(f"{col}_oe") for col, x in DEFENSE
        )
        out.append(off.join(de, on=["game_id", "team"], how="full", coalesce=True))
    return pl.concat(out).with_columns(c("season").cast(pl.Int32))


def consistent(rows: pl.DataFrame) -> None:
    print("\n== 3. Consistency (over expected, per team-game; regular season 2016-2025)")
    measures = [f"{col}_oe" for col, _ in (*OFFENSE, *FACED, *DEFENSE)]
    res = consistency(rows.drop_nulls("week"), measures)
    with pl.Config(tbl_rows=30, tbl_width_chars=200, float_precision=2):
        print(res.select("measure", "week_r", "week_lo", "season_r", "season_lo", "season_hi", "unit_seasons", "season_pairs", "verdict"))


def fullback() -> None:
    print("\n== 4. The fullback fix: charted neutral plays whose heavy flag changes")
    for s in (2022, 2023, 2024, 2025):
        p = scan("participation", [s]).select("offense_personnel").collect()
        old = (
            c("offense_personnel").str.extract(r"(\d) RB").cast(pl.Int32, strict=False)
            + c("offense_personnel").str.extract(r"(\d) TE").cast(pl.Int32, strict=False)
            >= 3
        ).fill_null(False)
        x = p.select(changed=(old != personnel.heavy(c("offense_personnel"))).mean(),
                     new=personnel.heavy(c("offense_personnel")).mean(), old=old.mean())  # fmt: skip
        print(f"  {s}: {x['changed'][0]:.1%} of plays change; heavy {x['old'][0]:.1%} -> {x['new'][0]:.1%}")


def main() -> None:
    ts = load("team_season")
    profile(ts)
    sanity(ts)
    consistent(game_rows())
    fullback()


if __name__ == "__main__":
    main()
