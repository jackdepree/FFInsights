"""Depth charts → a slot label (`WR2`, `CB1`, ...) per team, week and player.

Both nflverse formats end up as the same rows: weekly charts through 2024, and from 2025 the
latest daily snapshot before each game. Labels rank players within a position by their average
depth so far, as the old `clean_depth_charts` did, but in time order and to date only.
"""

from datetime import UTC

import polars as pl

from pcf.core.log import get_logger
from pcf.data.clean.standard import team

log = get_logger(__name__)

ROW_COLUMNS = ["season", "week", "team", "gsis_id", "position", "depth"]
SPECIAL = "special"

# The old position clean-up, applied in the same order (old clean_depth_charts).
WEEKLY_RENAMES = [
    ({"LOT"}, "LT"),
    ({"ROT"}, "RT"),
    ({"RDE", "LDE"}, "DE"),
    ({"RDT", "LDT"}, "DT"),
    ({"LB"}, "MLB"),
    ({"\n ", "K", "P", "LS"}, SPECIAL),
    ({"DB"}, "CB"),
]
# The old code puts the Super Bowl bye week, which has no week number, after the Super Bowl.
SUPER_BOWL_BYE_WEEK = 23

# Daily snapshots (2025→) name sides of the formation; PCF keeps the old position names.
DAILY_POSITIONS = {
    **{p: p for p in ["QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT"]},
    **{p: p for p in ["NT", "MLB", "FS", "SS"]},
    "LDE": "DE",
    "RDE": "DE",
    "LDT": "DT",
    "RDT": "DT",
    "LILB": "ILB",
    "RILB": "ILB",
    "WLB": "OLB",
    "SLB": "OLB",
    "LCB": "CB",
    "RCB": "CB",
    "NB": "CB",
}
DAILY_SPECIAL_TEAMS = "Special Teams"


def weekly_depth_rows(depth_charts: pl.DataFrame) -> pl.DataFrame:
    """Weekly-format charts (through 2024), as published → one row per team, week and player.

    Offense and defense only, as before. A player listed more than once in a week keeps their best
    (lowest) depth, then their first listing. The old code kept the first listing of any formation,
    then dropped it if that was special teams.
    """
    position = (
        pl.when(pl.col("position").is_in(["T", "G"]))
        .then(pl.coalesce(pl.col("depth_position"), pl.col("position")))
        .otherwise(pl.col("position"))
    )
    for olds, new in WEEKLY_RENAMES:
        position = pl.when(position.is_in(list(olds))).then(pl.lit(new)).otherwise(position)
    position = pl.when(position.str.contains(" ")).then(pl.lit(SPECIAL)).otherwise(position)
    return (
        depth_charts.with_row_index("listed")
        .filter(pl.col("formation").is_in(["Offense", "Defense"]))
        .select(
            pl.col("season").cast(pl.Int32),
            pl.col("week").cast(pl.Int32).fill_null(SUPER_BOWL_BYE_WEEK),
            team=team("club_code"),
            gsis_id=pl.col("gsis_id").str.strip_chars(),
            position=position,
            depth=pl.col("depth_team").cast(pl.Int32),
            listed="listed",
        )
        .pipe(_one_row_per_player_week)
    )


def daily_depth_rows(depth_charts: pl.DataFrame, cutoffs: pl.DataFrame) -> pl.DataFrame:
    """Daily snapshots (2025→) → one row per team, week and player, from the latest snapshot at
    or before each game's cutoff.

    `cutoffs` has season, week, team and cutoff (UTC) for each team's game (`game_day_cutoffs`).
    Depth is the player's rank within their spot (WR has three spots, so the second WR in each
    spot is depth 2), matching the weekly format's `depth_team`.
    """
    charts = depth_charts.filter(pl.col("pos_grp") != DAILY_SPECIAL_TEAMS).with_columns(
        team("team"), taken=pl.col("dt").str.to_datetime(time_zone="UTC")
    )
    unknown = set(charts["pos_abb"].unique()) - set(DAILY_POSITIONS)
    if unknown:
        raise ValueError(f"daily depth charts have positions PCF doesn't map: {sorted(unknown)}")
    no_id = charts.filter(pl.col("gsis_id").is_null()).height
    if no_id:
        log.info("daily depth charts: %d rows without a gsis_id dropped", no_id)

    taken = charts.select("team", "taken").unique().sort("taken")
    chosen = (
        cutoffs.select("season", "week", "team", "cutoff")
        .sort("cutoff")
        .join_asof(
            taken,
            left_on="cutoff",
            right_on="taken",
            by="team",
            strategy="backward",
            check_sortedness=False,  # both sorted above; polars can't check within groups
        )
    )
    # Games after the newest snapshot haven't happened yet. Each team's next one gets today's
    # chart (that's what a live prediction uses); later ones get nothing, since their chart
    # will still change.
    newest = taken["taken"].max()
    future = pl.col("cutoff") > newest
    chosen = chosen.filter(
        ~future | (pl.col("cutoff") == pl.col("cutoff").filter(future).min().over("team"))
    )
    missing = chosen.filter(pl.col("taken").is_null())
    if missing.height:
        log.warning("no depth chart before the cutoff for %d team-games", missing.height)
    return (
        chosen.drop_nulls("taken")
        .join(charts.drop_nulls("gsis_id"), on=["team", "taken"])
        .with_columns(
            depth=pl.col("pos_rank").rank("dense").over("team", "taken", "pos_abb", "pos_slot"),
        )
        .with_row_index("listed")
        .select(
            pl.col("season").cast(pl.Int32),
            pl.col("week").cast(pl.Int32),
            "team",
            "gsis_id",
            position=pl.col("pos_abb").replace_strict(DAILY_POSITIONS),
            depth=pl.col("depth").cast(pl.Int32),
            listed=pl.col("listed"),
        )
        .pipe(_one_row_per_player_week)
    )


def _one_row_per_player_week(rows: pl.DataFrame) -> pl.DataFrame:
    return (
        rows.drop_nulls(["gsis_id", "position", "depth"])
        .sort("depth", "listed")
        .unique(["season", "week", "team", "gsis_id"], keep="first")
        .select(ROW_COLUMNS)
        .sort("season", "week", "team", "gsis_id")
    )


def depth_labels(rows: pl.DataFrame) -> pl.DataFrame:
    """Rows from `weekly_depth_rows` / `daily_depth_rows` → a label per team, week and player.

    As in the old code, players at a position are ranked by their average depth over the season
    so far, so a steady starter outranks a one-week fill-in. The old code averaged over the rows
    in file order, which isn't calendar order, so later weeks leaked into earlier labels (F7).
    Here the average counts only that week and earlier. Ties go to this week's depth, then more
    weeks listed, then gsis_id.
    """
    season_so_far = ["gsis_id", "season"]
    return (
        rows.sort("season", "week", "gsis_id")
        .with_columns(
            weeks_listed=pl.int_range(1, pl.len() + 1).over(season_so_far),
            depth_mean=pl.col("depth").cum_sum().over(season_so_far),
        )
        .with_columns(pl.col("depth_mean") / pl.col("weeks_listed"))
        .sort(
            "depth_mean",
            "depth",
            pl.col("weeks_listed"),
            "gsis_id",
            descending=[False, False, True, False],
        )
        .with_columns(rank=pl.int_range(1, pl.len() + 1).over("season", "week", "team", "position"))
        .with_columns(position_label=pl.col("position") + pl.col("rank").cast(pl.String))
        .select(*ROW_COLUMNS, "depth_mean", "weeks_listed", "position_label")
        .sort("season", "week", "team", "position", "position_label")
    )


def game_day_cutoffs(schedules: pl.DataFrame) -> pl.DataFrame:
    """Each team's game → the start of game day in New York, as UTC: season, week, team, cutoff.

    A stand-in until `timeline` provides kickoff times. Snapshots are taken about once a day, so
    the start of game day loses at most the morning-of snapshot, and never looks past kickoff.
    """
    games = schedules.select(
        pl.col("season").cast(pl.Int32),
        pl.col("week").cast(pl.Int32),
        "home_team",
        "away_team",
        cutoff=pl.col("gameday")
        .str.to_datetime("%Y-%m-%d", time_zone="America/New_York")
        .dt.convert_time_zone(str(UTC)),
    )
    return pl.concat(
        [
            games.select("season", "week", team=pl.col(side), cutoff="cutoff")
            for side in ("home_team", "away_team")
        ]
    ).sort("season", "week", "team")
