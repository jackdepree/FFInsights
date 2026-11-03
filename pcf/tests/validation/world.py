"""A synthetic league for the harness tests: six teams, four seasons of six weeks and a Super Bowl,
with Thursday, Sunday and Monday night games. Each player has a skill, so their points have signal.

Parts: `game.schedule`, `player_game.roster` (the spine, known at the start of the week),
`player_game.stats` (known 24 hours after kickoff) and `player_play.on_field` (known after the
Super Bowl, like participation).
"""

from datetime import date, timedelta

import numpy as np
import polars as pl

from pcf.data.gateway import FrameSource, Gateway
from pcf.data.timeline import calendar

c = pl.col
SEASONS = [2020, 2021, 2022, 2023]
WEEKS = 6
TEAMS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]
POSITIONS = ["QB", "RB", "WR", "TE"]
# (home, away, weekday offset from Thursday, kickoff ET): Thursday night, Sunday 1 PM, Monday night
SLOTS = [(0, 1, 0, "20:20"), (2, 3, 3, "13:00"), (4, 5, 4, "20:15")]
UTC = pl.Datetime("us", "UTC")


def schedules() -> pl.DataFrame:
    rows = []
    for season in SEASONS:
        first = date(season, 9, 7)
        thursday = first + timedelta(days=(3 - first.weekday()) % 7)
        for week in range(1, WEEKS + 1):
            shift = week % 3  # rotate who plays when
            for i, (h, a, offset, time) in enumerate(SLOTS):
                home = TEAMS[(h + 2 * shift) % 6]
                away = TEAMS[(a + 2 * shift) % 6]
                day = thursday + timedelta(days=7 * (week - 1) + offset)
                gid = f"{season}_{week:02d}_{away}_{home}"
                rows.append((gid, season, week, "REG", str(day), time, home, away, i))
        sb_day = thursday + timedelta(days=7 * (WEEKS - 1) + 3 + 14)
        rows.append(
            (f"{season}_{WEEKS + 1:02d}_AAA_BBB", season, WEEKS + 1, "SB", str(sb_day), "18:30",
             "BBB", "AAA", 9)
        )  # fmt: skip
    cols = ["game_id", "season", "week", "game_type", "gameday", "gametime", "home_team",
            "away_team", "slot"]  # fmt: skip
    return pl.DataFrame(rows, schema=cols, orient="row").with_columns(
        c("season").cast(pl.Int32), c("week").cast(pl.Int32)
    )


def offseason() -> pl.DataFrame:
    seasons = [*SEASONS, SEASONS[-1] + 1]
    return pl.DataFrame(
        {
            "season": seasons,
            "league_year_start": [date(s, 3, 12) for s in seasons],
            "combine_start": [date(s, 2, 27) for s in seasons],
            "combine_end": [date(s, 3, 3) for s in seasons],
            "draft_start": [date(s, 4, 24) for s in seasons],
            "draft_end": [date(s, 4, 26) for s in seasons],
            "preseason_start": [date(s, 8, 1) for s in seasons],
            "notes": [None] * len(seasons),
        },
        schema_overrides={"season": pl.Int32, "notes": pl.String},
    )


def cal():
    return calendar(schedules(), offseason())


def players() -> pl.DataFrame:
    rng = np.random.default_rng(7)
    rows = [(f"00-{t}{p}", t, p, float(rng.uniform(4, 22))) for t in TEAMS for p in POSITIONS]
    return pl.DataFrame(rows, schema=["gsis_id", "team", "position", "skill"], orient="row")


def frames(noise_only: bool = False, seed: int = 11) -> dict[tuple[str, str], pl.DataFrame]:
    """The world's parts. `noise_only`: points carry no player skill (no signal)."""
    k = cal()
    games = k.games.join(schedules().select("game_id", "home_team", "away_team"), on="game_id",
                         suffix="_s")  # fmt: skip
    starts = k.weeks.select("season", "week", week_start="start")
    teams = pl.concat(
        [games.select("game_id", "season", "week", "kickoff", team=c(side))
         for side in ("home_team", "away_team")]
    ).join(starts, on=["season", "week"])  # fmt: skip
    roster = teams.join(players(), on="team").select(
        "gsis_id", "game_id", c("season").cast(pl.Int32), "week", "team", "position",
        known_at=c("week_start").cast(UTC), kickoff=c("kickoff"), skill="skill",
    )  # fmt: skip
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 4, roster.height)
    points = (0 if noise_only else roster["skill"].to_numpy()) + noise + (8 if noise_only else 0)
    stats = roster.select(
        "gsis_id", "game_id", "season",
        fantasy_points_ppr=pl.Series(points.round(2)),
        known_at=(c("kickoff") + pl.duration(hours=24)).cast(UTC),
    )  # fmt: skip
    ends = dict(k.weeks.filter("super_bowl").select("season", "end").iter_rows())
    on_field = roster.select(
        "game_id", play_id=pl.lit(1, pl.Int64), gsis_id="gsis_id", season="season",
        snaps=pl.lit(1),
        known_at=c("season").replace_strict(ends, return_dtype=UTC) + pl.duration(days=30),
    )  # fmt: skip
    schedule = (
        schedules()
        .join(k.games.select("game_id", "kickoff"), on="game_id")
        .with_columns(known_at=(c("kickoff") - pl.duration(days=60)).cast(UTC))
    )
    return {
        ("game", "schedule"): schedule,
        ("player_game", "roster"): roster.drop("kickoff", "skill"),
        ("player_game", "stats"): stats,
        ("player_play", "on_field"): on_field,
    }


def gateway(noise_only: bool = False, **changes) -> Gateway:
    """The world's gateway. `changes` replace parts: {"player_game.stats": frame}."""
    parts = frames(noise_only)
    for key, frame in changes.items():
        parts[tuple(key.split("."))] = frame
    return Gateway(FrameSource(parts), cal())
