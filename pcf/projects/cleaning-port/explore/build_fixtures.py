"""Build the small public test fixtures for cleaning-port from the local raw copy.

Two 2024 games (weekly depth charts) and one 2025 game (daily depth charts), with only the rows
the cleaning functions read. Public nflverse rows only, well under 1 MB (CONVENTIONS.md).

Run from pcf/:  uv run python projects/cleaning-port/explore/build_fixtures.py
"""

import polars as pl

from pcf.config import PCF_DIR
from pcf.data.sources.nflverse import scan

OUT = PCF_DIR / "tests" / "fixtures" / "cleaning_port"
GAMES_2024 = ["2024_10_DET_HOU", "2024_10_DEN_KC"]
GAME_2025 = "2025_07_LV_KC"
PBP_COLUMNS = ["game_id", "play_id", "play_type", "season", "week", "season_type", "posteam", "defteam"]
PART_COLUMNS = ["nflverse_game_id", "play_id", "offense_players", "defense_players"]
ROSTER_COLUMNS = ["season", "week", "team", "gsis_id", "position", "depth_chart_position", "full_name"]


def teams(games: list[str]) -> list[str]:
    return sorted({t for g in games for t in g.split("_")[2:]})


def plays(season: int, games: list[str]) -> tuple[pl.DataFrame, pl.DataFrame]:
    pbp = scan("pbp", [season]).filter(pl.col("game_id").is_in(games)).select(PBP_COLUMNS).collect()
    part = (
        scan("participation", [season])
        .filter(pl.col("nflverse_game_id").is_in(games))
        .select(PART_COLUMNS)
        .collect()
    )
    return pbp, part


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pbp, part = plays(2024, GAMES_2024)
    t24 = teams(GAMES_2024)
    depth = scan("depth_charts", [2024]).filter(pl.col("club_code").is_in(t24)).collect()
    rosters = (
        scan("weekly_rosters", [2024])
        .filter(pl.col("team").is_in(t24) & (pl.col("week") <= 10))
        .select(ROSTER_COLUMNS)
        .collect()
    )
    pbp.write_parquet(OUT / "pbp_2024.parquet")
    part.write_parquet(OUT / "participation_2024.parquet")
    depth.write_parquet(OUT / "depth_charts_2024.parquet")
    rosters.write_parquet(OUT / "weekly_rosters_2024.parquet")

    pbp, part = plays(2025, [GAME_2025])
    t25 = teams([GAME_2025])
    sched = (
        scan("schedules")
        .filter((pl.col("season") == 2025) & (pl.col("week") <= 7) & (pl.col("home_team").is_in(t25) | pl.col("away_team").is_in(t25)))
        .select("game_id", "season", "week", "game_type", "gameday", "gametime", "home_team", "away_team")
        .collect()
    )
    last_day = sched.filter(pl.col("game_id") == GAME_2025)["gameday"][0]
    daily = (
        scan("depth_charts", [2025])
        .filter(pl.col("team").is_in(t25) & (pl.col("dt").str.slice(0, 10) <= last_day))
        .collect()
    )
    # Keep the snapshot each team had going into each of its games: the latest before game day.
    keep = (
        sched.select("gameday", team=pl.col("home_team"))
        .vstack(sched.select("gameday", team=pl.col("away_team")))
        .filter(pl.col("team").is_in(t25))
        .join(daily.select("team", "dt").unique(), on="team")
        .filter(pl.col("dt").str.slice(0, 10) < pl.col("gameday"))
        .group_by("team", "gameday")
        .agg(pl.col("dt").max())
        .select("team", "dt")
    )
    daily = daily.join(keep, on=["team", "dt"], how="semi")
    rosters = (
        scan("weekly_rosters", [2025])
        .filter(pl.col("team").is_in(t25) & (pl.col("week") <= 7))
        .select(ROSTER_COLUMNS)
        .collect()
    )
    pbp.write_parquet(OUT / "pbp_2025.parquet")
    part.write_parquet(OUT / "participation_2025.parquet")
    daily.write_parquet(OUT / "depth_charts_2025.parquet")
    rosters.write_parquet(OUT / "weekly_rosters_2025.parquet")
    sched.write_parquet(OUT / "schedules_2025.parquet")
    total = sum(p.stat().st_size for p in OUT.glob("*.parquet"))
    print(f"fixtures: {total / 1024:.0f} KB in {OUT}")


if __name__ == "__main__":
    main()
