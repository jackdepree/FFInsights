"""Light exploration for `grain-tables`: sizes, keys and join rates of the sources each table needs.

1. Rows and columns per season for each source (2024), and the size of the raw files.
2. Is player-week the same as player-game? Teams and players with two games in one week.
3. Who belongs in player_game: players with snaps, with stats, on the active roster.
4. Join rates at player-game for every player source, on 2024 and 2018.
5. Join rates at play level: participation and FTN against play-by-play.
6. Team-game: team_stats against schedules.
7. When each player-game source is known, relative to kickoff (timeline rules).

Run from pcf/:  uv run python projects/grain-tables/explore/profile_inputs.py
"""

import sys
from datetime import UTC, datetime

import polars as pl

from pcf.config import get_config
from pcf.data.clean import standard
from pcf.data.sources.nflverse import scan
from pcf.data.timeline import calendar, known_at

SEASON = 2024


def sizes() -> None:
    print("\n## 1. Rows, columns and raw size per source")
    raw = get_config().zone("raw") / "nflverse"
    out = []
    for name in [
        "pbp",
        "participation",
        "ftn_charting",
        "player_stats",
        "team_stats",
        "snap_counts",
        "ff_opportunity",
        "ngs_receiving",
        "pfr_week_rec",
        "injuries",
        "weekly_rosters",
        "depth_charts",
    ]:
        lf = scan(name, [SEASON])
        if name.startswith("ngs"):  # one file for every season: scan doesn't filter it
            lf = lf.filter(pl.col("season") == SEASON)
        cols = lf.collect_schema().names()
        rows = lf.select(pl.len()).collect().item()
        mb = sum(f.stat().st_size for f in (raw / name).rglob("*.parquet")) / 1e6
        out.append(
            {"source": name, "rows_2024": rows, "columns": len(cols), "raw_mb_all": round(mb)}
        )
    print(pl.DataFrame(out))


def one_game_a_week() -> None:
    print("\n## 2. Player-week vs player-game")
    s = scan("schedules").collect()
    teams = pl.concat(
        [s.select("season", "week", team=pl.col(t)) for t in ("home_team", "away_team")]
    )
    print(
        "team-weeks with 2+ games:",
        teams.group_by("season", "week", "team").len().filter(pl.col("len") > 1).height,
    )
    ps = scan("player_stats").select("player_id", "season", "week", "game_id").collect()
    print(
        "player_stats rows:",
        ps.height,
        "| player-weeks with 2+ games:",
        ps.group_by("player_id", "season", "week").len().filter(pl.col("len") > 1).height,
        "| null game_id:",
        ps["game_id"].null_count(),
    )


def player_game_sources(season: int) -> None:
    print(f"\n## 3-4. Player-game sources, {season}")
    players = scan("players").select("pfr_id", "gsis_id").collect()
    stats = standard.player_stats(scan("player_stats", [season]).collect()).select(
        "gsis_id", "game_id", "position_group"
    )
    snaps = standard.snap_counts(scan("snap_counts", [season]).collect(), players).select(
        "gsis_id", "game_id", "position", "offense_snaps", "defense_snaps", "st_snaps"
    )
    snapped = snaps.filter(
        (pl.col("offense_snaps") + pl.col("defense_snaps") + pl.col("st_snaps")) > 0
    ).drop_nulls("gsis_id")
    games = (
        scan("schedules")
        .filter(pl.col("season") == season)
        .select("game_id", "week", "home_team", "away_team")
        .collect()
    )
    rosters = standard.weekly_rosters(scan("weekly_rosters", [season]).collect())
    active = rosters.filter(pl.col("status") == "ACT").select("gsis_id", "week", "team")
    team_games = pl.concat(
        [games.select("game_id", "week", team=pl.col(t)) for t in ("home_team", "away_team")]
    )
    active_games = active.join(team_games, on=["week", "team"]).select("gsis_id", "game_id")
    spine = pl.concat(
        [stats.select("gsis_id", "game_id"), snapped.select("gsis_id", "game_id")]
    ).unique()
    print(
        "player-games with stats:",
        stats.height,
        "| with snaps > 0:",
        snapped.height,
        "| union:",
        spine.height,
        "| active-roster player-games:",
        active_games.height,
    )
    print(
        "snapped but no stats row:",
        snapped.join(stats, on=["gsis_id", "game_id"], how="anti")
        .group_by("position")
        .len()
        .sort("len", descending=True)
        .head(8)
        .rows(),
    )
    print(
        "stats but no snaps row:", stats.join(snapped, on=["gsis_id", "game_id"], how="anti").height
    )

    rows = []

    def rate(name: str, other: pl.DataFrame, on: list[str]) -> None:
        keys = spine.join(games.select("game_id", "week"), on="game_id")
        hit = keys.join(other.select(on).unique(), on=on, how="semi").height
        rows.append(
            {"source": name, "rows": other.height, "spine_matched": round(hit / keys.height, 4)}
        )

    rate("player_stats", stats, ["gsis_id", "game_id"])
    rate("snap_counts (snaps > 0)", snapped, ["gsis_id", "game_id"])
    ffo = standard.ff_opportunity(scan("ff_opportunity", [season]).collect())
    rate("ff_opportunity", ffo, ["gsis_id", "game_id"])
    ngs = pl.concat(
        [
            scan(f"ngs_{k}")
            .filter(pl.col("season") == season)
            .select(gsis_id="player_gsis_id", week="week")
            .collect()
            for k in ("passing", "receiving", "rushing")
        ]
    ).filter(pl.col("week") > 0)
    rate("ngs (any)", ngs, ["gsis_id", "week"])
    pfr = pl.concat(
        [
            scan(f"pfr_week_{k}", [season]).select("pfr_player_id", "game_id").collect()
            for k in ("pass", "rush", "rec", "def")
        ]
    ).join(players.rename({"pfr_id": "pfr_player_id"}), on="pfr_player_id", how="left")
    rate("pfr_week (any)", pfr.drop_nulls("gsis_id"), ["gsis_id", "game_id"])
    inj = standard.injuries(scan("injuries", [season]).collect()).drop_nulls("gsis_id")
    rate("injuries (any report)", inj, ["gsis_id", "week"])
    rate("weekly_rosters (any)", rosters.drop_nulls("gsis_id"), ["gsis_id", "week"])
    print(pl.DataFrame(rows))
    print("pfr rows with no gsis_id:", pfr["gsis_id"].null_count(), "of", pfr.height)


def play_level(season: int) -> None:
    print(f"\n## 5. Play-level joins, {season}")
    pbp = (
        scan("pbp", [season])
        .select("game_id", "play_id", "play_type")
        .collect()
        .with_columns(pl.col("play_id").cast(pl.Int64))
    )
    part = (
        scan("participation", [season])
        .select(game_id="nflverse_game_id", play_id="play_id")
        .collect()
    )
    part = part.with_columns(pl.col("play_id").cast(pl.Int64))
    runpass = pbp.filter(pl.col("play_type").is_in(["run", "pass"]))
    print(
        "plays:",
        pbp.height,
        "run/pass:",
        runpass.height,
        "| participation rows:",
        part.height,
        "| run/pass with participation:",
        round(runpass.join(part, on=["game_id", "play_id"], how="semi").height / runpass.height, 4),
    )
    if season >= 2022:
        ftn = (
            scan("ftn_charting", [season])
            .select(game_id="nflverse_game_id", play_id=pl.col("nflverse_play_id").cast(pl.Int64))
            .collect()
        )
        print(
            "ftn rows:",
            ftn.height,
            "| run/pass with ftn:",
            round(
                runpass.join(ftn, on=["game_id", "play_id"], how="semi").height / runpass.height, 4
            ),
            "| ftn rows not in pbp:",
            ftn.join(pbp, on=["game_id", "play_id"], how="anti").height,
        )


def team_game(season: int) -> None:
    print(f"\n## 6. Team-game, {season}")
    ts = standard.standard_teams(scan("team_stats", [season]).collect(), "team")
    s = scan("schedules").filter(pl.col("season") == season).collect()
    print(
        "team_stats rows:",
        ts.height,
        "| schedule team-games:",
        2 * s.height,
        "| team_stats rows per game:",
        ts.group_by("game_id").len()["len"].value_counts().rows(),
    )


def timing(season: int) -> None:
    print(f"\n## 7. When player-game sources are known (hours after kickoff), {season}")
    cal = calendar(standard.schedules(scan("schedules").collect()))
    kick = cal.games.select("game_id", "season", "week", "kickoff")
    rows = []
    for name, cols in [
        ("injuries", None),
        ("weekly_rosters", None),
        ("player_stats", ["game_id"]),
        ("snap_counts", ["game_id"]),
        ("ngs_receiving", ["season", "week"]),
        ("pfr_week_rec", ["season", "week"]),
        ("ftn_charting", ["nflverse_game_id"]),
    ]:
        lf = (
            scan(name, [season]).filter(pl.col("season") == season)
            if name.startswith("ngs")
            else scan(name, [season])
        )
        df = lf.collect() if cols is None else lf.select(cols).collect()
        if name == "injuries":
            df = standard.injuries(df)
        out = known_at(name, df, cal, fetched_at=datetime.now(UTC))
        if "game_id" in out.columns:
            j = out.join(kick, on="game_id")
        elif "nflverse_game_id" in out.columns:
            j = out.join(kick, left_on="nflverse_game_id", right_on="game_id")
        else:
            first = kick.group_by("season", "week").agg(kickoff=pl.col("kickoff").min())
            j = out.with_columns(
                pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32)
            ).join(first, on=["season", "week"])
        h = (j["known_at"] - j["kickoff"]).dt.total_hours()
        rows.append({"source": name, "median_h": h.median(), "min_h": h.min(), "max_h": h.max()})
    print(pl.DataFrame(rows))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pl.Config.set_tbl_width_chars(200)
    pl.Config.set_tbl_rows(30)
    sizes()
    one_game_a_week()
    player_game_sources(SEASON)
    player_game_sources(2018)  # PFR weekly files start in 2018
    play_level(SEASON)
    play_level(2016)
    team_game(SEASON)
    timing(SEASON)


if __name__ == "__main__":
    main()
