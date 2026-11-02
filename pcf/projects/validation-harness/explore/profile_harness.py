"""Light exploration for validation-harness: what the harness touches, and whether its checks bite.

1. When each table part becomes known, relative to kickoff (what the gateway has to respect).
2. What a view of the world at one moment costs (`load(name, at)`), for history-sized reads.
3. How many steps a walk-forward backtest has (Tuesday-morning moments, 2016-2024).
4. A planted-leak trial of the future-deletion check (ARCHITECTURE.md, check 4) on bulk features:
   an honest "so far" feature, one that includes the current game (cleaning-port#F8), and one
   that filters by week but reads participation (known only after the Super Bowl).

Run from pcf/: .venv/Scripts/python.exe projects/validation-harness/explore/profile_harness.py
"""

import time
from datetime import timedelta

import polars as pl

from pcf.data.schemas import TABLES
from pcf.data.tables.store import files, load
from pcf.data.timeline.calendar import weeks as calendar_weeks

c = pl.col
SEASONS = list(range(2016, 2025))


def kickoffs() -> pl.DataFrame:
    return load("game", parts=["schedule"]).select("game_id", "kickoff")


def lags() -> pl.DataFrame:
    """Each part's known_at minus kickoff, in hours, over 2016-2024 (2024 only for plays)."""
    k = kickoffs()
    out = []
    for name, t in TABLES.items():
        seasons = [2024] if name in ("play", "player_play") else SEASONS
        for part in t.parts:
            paths = files(name, part, seasons)
            if not paths:
                continue
            df = (
                pl.concat([pl.scan_parquet(p).select("game_id", "known_at") for p in paths])
                .collect()
                .join(k, on="game_id")
                .with_columns(hours=(c("known_at") - c("kickoff")).dt.total_minutes() / 60)
            )
            out.append(
                df.select(
                    table=pl.lit(name),
                    part=pl.lit(part),
                    rows=pl.len(),
                    before_kickoff=(c("hours") <= 0).mean(),
                    median_h=c("hours").median(),
                    p99_h=c("hours").quantile(0.99),
                    max_days=c("hours").max() / 24,
                )
            )
    return pl.concat(out)


def timed(label: str, fn):
    start = time.perf_counter()
    out = fn()
    took = time.perf_counter() - start
    size = out.estimated_size("mb") if isinstance(out, pl.DataFrame) else 0
    rows = out.height if isinstance(out, pl.DataFrame) else 0
    print(f"  {label}: {took:.1f} s, {rows:,} rows, {size:,.0f} MB")
    return out


def moments() -> pl.DataFrame:
    """Each week's prediction moment: Tuesday 10:00 ET, or the week's start if it's later."""
    games = load("game", parts=["schedule"])
    first = games.group_by("season", "week").agg(first_kick=c("kickoff").min())
    local = c("start").dt.convert_time_zone("America/New_York")
    return (
        calendar_weeks(games)
        .join(first, on=["season", "week"])
        .sort("season", "week")
        .with_columns(
            weekday=local.dt.weekday(),
            # 10:00 ET on the week's first day (its start is midnight ET)
            moment=(local + timedelta(hours=10)).dt.convert_time_zone("UTC"),
        )
        .with_columns(before_first_game=c("moment") < c("first_kick"))
    )


# --- bulk features over a world (a dict of frames), and the deletion check ---------------------


def world(at=None, seasons=(2024,)) -> dict[str, pl.DataFrame]:
    s = list(seasons)
    return {
        "pg": load("player_game", at=at, seasons=s, parts=["stats", "snaps"]),
        "pp": load("player_play", at=at, seasons=s),
        "plays": load("play", at=at, seasons=s, parts=["pbp"]).select(
            "game_id", "play_id", "posteam", "known_at"
        ),
    }


def honest(w) -> pl.DataFrame:
    """PPR points per game in earlier games this season (shifted, so the current game is out)."""
    pg = w["pg"].sort("gsis_id", "week")
    return pg.select(
        "gsis_id",
        "game_id",
        "week",
        f=c("fantasy_points_ppr").shift(1).cum_sum().over("gsis_id")
        / c("fantasy_points_ppr").shift(1).cum_count().over("gsis_id"),
    )


def includes_current(w) -> pl.DataFrame:
    """The same, but the current game is in its own average (cleaning-port#F8)."""
    pg = w["pg"].sort("gsis_id", "week")
    return pg.select(
        "gsis_id",
        "game_id",
        "week",
        f=c("fantasy_points_ppr").cum_sum().over("gsis_id")
        / c("fantasy_points_ppr").cum_count().over("gsis_id"),
    )


def participation_by_week(w) -> pl.DataFrame:
    """Share of the team's offensive plays a player was on in earlier weeks: filtered by week, so
    it looks honest, but participation is published only after the Super Bowl."""
    pp = w["pp"].filter(c("side") == "offense")
    per_week = (
        pp.join(w["pg"].select("game_id", "week").unique(), on="game_id")
        .group_by("gsis_id", "week")
        .agg(on=pl.len())
    )
    pg = w["pg"].select("gsis_id", "game_id", "week")
    joined = pg.join(per_week, on="gsis_id", how="left", suffix="_p").filter(
        c("week_p") < c("week")
    )
    f = joined.group_by("gsis_id", "game_id").agg(f=c("on").sum())
    return pg.join(f, on=["gsis_id", "game_id"], how="left")


def deletion_check(feature, cutoffs: pl.DataFrame, full: dict) -> tuple[int, int, float]:
    """For each cutoff: features from the world truncated at it vs the full world, on the rows
    whose prediction moment is at or before the cutoff. Returns (cutoffs failed, rows differing,
    seconds)."""
    start = time.perf_counter()
    whole = feature(full)
    failed = differing = 0
    for row in cutoffs.iter_rows(named=True):
        cut = world(at=row["moment"])
        early = whole.filter(c("week") <= row["week"])
        mine = feature(cut).filter(c("week") <= row["week"])
        both = early.join(mine, on=["gsis_id", "game_id"], how="full", suffix="_cut")
        diff = both.filter(~c("f").eq_missing(c("f_cut"))).height
        failed += diff > 0
        differing += diff
    return failed, differing, time.perf_counter() - start


def main() -> None:
    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_cols(10)

    print("1. When each part is known (hours after kickoff; negative = before)")
    print(lags())

    print("\n2. A view at one moment (2024-11-05 15:00 UTC, the Tuesday of week 10)")
    at = pl.datetime(2024, 11, 5, 15, time_zone="UTC")
    at = pl.select(at).item()
    timed("player_game, all parts, 2006-2024", lambda: load("player_game", at=at, seasons=range(2006, 2025)))
    timed("player_game, stats + snaps, 2006-2024", lambda: load("player_game", at=at, seasons=range(2006, 2025), parts=["stats", "snaps"]))
    timed("play, pbp only, 2006-2024", lambda: load("play", at=at, seasons=range(2006, 2025), parts=["pbp"]))
    timed("play, pbp only, 2024", lambda: load("play", at=at, seasons=[2024], parts=["pbp"]))
    timed("player_play, 2024", lambda: load("player_play", at=at, seasons=[2024]))

    print("\n3. Walk-forward steps (Tuesday 10:00 ET each week)")
    m = moments()
    dev = m.filter(c("season").is_between(2016, 2024))
    print(dev.group_by("season").agg(weeks=pl.len()).sort("season").transpose(include_header=True))
    print(f"  steps 2016-2024: {dev.height}; week starts not on a Tuesday: "
          f"{dev.filter(c('weekday') != 2).height}; moments after the week's first game: "
          f"{dev.filter(~c('before_first_game')).height}")

    print("\n4. Planted leaks vs the future-deletion check (2024, 25 cutoffs)")
    full = world()
    cutoffs = m.filter(c("season") == 2024).sort("week")
    pick = cutoffs.gather_every(max(1, cutoffs.height // 25)).head(25)
    for name, fn in [("honest", honest), ("includes current game", includes_current),
                     ("participation by week", participation_by_week)]:
        failed, rows, took = deletion_check(fn, pick, full)
        print(f"  {name}: {failed}/{pick.height} cutoffs fail, {rows:,} rows differ, {took:.1f} s")


if __name__ == "__main__":
    main()
