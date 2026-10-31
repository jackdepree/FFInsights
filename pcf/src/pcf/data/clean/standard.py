"""PCF's standard names, codes and signs for each nflverse source (docs/CONVENTIONS.md).

Pure functions: a published table in, the same table with fixed id names, one set of team codes,
betting-style spreads and known duplicates removed. Each raises on anything it doesn't expect
instead of passing it through.
"""

import polars as pl

from pcf.core.log import get_logger

log = get_logger(__name__)

# The 32 codes play-by-play uses for every season. Play-by-play gives a franchise its current
# code throughout (the 2017 Raiders are LV), so that's the standard: one franchise, one code.
TEAMS = frozenset(
    [
        "ARI",
        "ATL",
        "BAL",
        "BUF",
        "CAR",
        "CHI",
        "CIN",
        "CLE",
        "DAL",
        "DEN",
        "DET",
        "GB",
        "HOU",
        "IND",
        "JAX",
        "KC",
        "LA",
        "LAC",
        "LV",
        "MIA",
        "MIN",
        "NE",
        "NO",
        "NYG",
        "NYJ",
        "PHI",
        "PIT",
        "SEA",
        "SF",
        "TB",
        "TEN",
        "WAS",
    ]
)
# Other codes nflverse sources use for the same franchises (cleaning-port results, F11).
TEAM_CODES = {
    "OAK": "LV",
    "LVR": "LV",
    "RAI": "LV",
    "SD": "LAC",
    "SDG": "LAC",
    "SDC": "LAC",
    "STL": "LA",
    "SL": "LA",
    "LAR": "LA",
    "RAM": "LA",
    "ARZ": "ARI",
    "AZ": "ARI",
    "PHO": "ARI",
    "PHX": "ARI",
    "BLT": "BAL",
    "CLV": "CLE",
    "HST": "HOU",
    "JAC": "JAX",
    "GNB": "GB",
    "GBP": "GB",
    "KAN": "KC",
    "KCC": "KC",
    "NOR": "NO",
    "NOS": "NO",
    "NWE": "NE",
    "NEP": "NE",
    "SFO": "SF",
    "TAM": "TB",
    "TBB": "TB",
}
# Values in team columns that aren't a team: free agents, and PFR's "played for 2 or 3 teams".
NOT_A_TEAM = frozenset({"", "FA", "FA*", "2TM", "3TM"})

# nflreadpy's load_schedules keeps only these roof values and nulls the rest (data-layer#F9).
ROOFS = ["dome", "outdoors", "closed", "open"]


def team(column: str) -> pl.Expr:
    """A team column in PCF's codes. Non-teams (FA, 2TM, "") become null."""
    col = pl.col(column)
    return (
        pl.when(col.is_in(list(NOT_A_TEAM)))
        .then(None)
        .otherwise(col.replace(TEAM_CODES))
        .alias(column)
    )


def standard_teams(df: pl.DataFrame, *columns: str) -> pl.DataFrame:
    """Recode team columns, raising on any code that isn't one of the 32 afterwards."""
    out = df.with_columns(team(c) for c in columns)
    for c in columns:
        bad = set(out[c].drop_nulls().unique()) - TEAMS
        if bad:
            raise ValueError(f"{c}: team codes PCF doesn't know: {sorted(bad)}")
    return out


def _drop(df: pl.DataFrame, keep: pl.Expr, what: str) -> pl.DataFrame:
    out = df.filter(keep)
    if out.height < df.height:
        log.info("%s: dropped %d rows", what, df.height - out.height)
    return out


def schedules(df: pl.DataFrame) -> pl.DataFrame:
    """Team codes, nflreadpy's roof rule, and `home_spread` in betting style.

    nflverse's `spread_line` is positive when the home team is favored. Betting style is the
    reverse (home -3.5 = favored by 3.5), so `home_spread = -spread_line`. `spread_line` itself
    keeps its nflverse meaning (CONVENTIONS.md: nflverse columns keep their names and scales).
    """
    return standard_teams(df, "home_team", "away_team").with_columns(
        roof=pl.when(pl.col("roof").is_in(ROOFS)).then(pl.col("roof")),
        home_spread=-pl.col("spread_line"),
    )


def player_stats(df: pl.DataFrame) -> pl.DataFrame:
    """`player_id` → `gsis_id`, and team codes. Each season-week has one unnamed row with no
    player id and no stats (id "0" in 1999-2000, null after); those are dropped."""
    df = _drop(
        df, pl.col("player_id").is_not_null() & (pl.col("player_id") != "0"), "player_stats rows"
    )
    return standard_teams(df.rename({"player_id": "gsis_id"}), "team", "opponent_team")


def ff_opportunity(df: pl.DataFrame) -> pl.DataFrame:
    """Expected fantasy points: rows with no player id dropped (they can't be joined to anyone,
    package-scaffold#F4), one row per player-game, `player_id` → `gsis_id`, `posteam` → `team`."""
    df = _drop(df, pl.col("player_id").is_not_null(), "ff_opportunity rows without a player id")
    out = standard_teams(df.rename({"player_id": "gsis_id", "posteam": "team"}), "team")
    # One 2013 player has two slightly different rows in two games; the first is kept.
    once = out.unique(["gsis_id", "game_id"], keep="first", maintain_order=True)
    if once.height < out.height:
        log.info("ff_opportunity: dropped %d repeated player-games", out.height - once.height)
    return once


def snap_counts(df: pl.DataFrame, players: pl.DataFrame) -> pl.DataFrame:
    """Team codes, and `gsis_id` added through nflverse's `players` file (snap counts only carry
    PFR's id). That file maps 99.9% of rows; dynastyprocess's id map only 82%, since it covers
    fantasy players. Unmapped players keep a null `gsis_id`, and their share is logged."""
    ids = (
        players.select(pfr_player_id="pfr_id", gsis_id="gsis_id")
        .drop_nulls()
        .unique("pfr_player_id", keep="first", maintain_order=True)
    )
    out = standard_teams(df, "team", "opponent").join(ids, on="pfr_player_id", how="left")
    missing = out["gsis_id"].is_null().mean()
    if missing:
        log.info("snap_counts: %.2f%% of rows have no gsis_id", 100 * missing)
    return out


def injuries(df: pl.DataFrame) -> pl.DataFrame:
    """Team codes, integer season and week, and one report per player, team and week.

    A player traded during a week keeps one row per team. When a team files two reports for a
    player in one week (package-scaffold#F4), the later `date_modified` is kept: it's the status
    going into the game. `date_modified` stays on the row so `timeline` can apply its own known-at
    rule. From 2025 `date_modified` is empty, and the last listed row is kept.
    """
    key = ["season", "week", "game_type", "team", "gsis_id"]
    out = standard_teams(
        df.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32)), "team"
    ).with_row_index("listed")
    deduped = (
        pl.concat(
            [
                out.filter(pl.col("gsis_id").is_not_null())
                .sort("date_modified", "listed", nulls_last=False)
                .unique(key, keep="last"),
                out.filter(pl.col("gsis_id").is_null()),  # no id: nothing to match them on
            ]
        )
        .sort("listed")
        .drop("listed")
    )
    if deduped.height < out.height:
        log.info("injuries: kept the latest of %d repeated reports", out.height - deduped.height)
    return deduped


# Statuses in the order a duplicated weekly-roster row is kept (package-scaffold#F4).
ROSTER_STATUS_ORDER = ["ACT", "RES", "INA", "DEV", "PUP", "EXE", "SUS"]


def weekly_rosters(df: pl.DataFrame) -> pl.DataFrame:
    """Team codes, and one row per player, team and week.

    nflverse lists some players twice on one team in a week, usually once active and once as
    cut or traded. The row with the earliest status in ROSTER_STATUS_ORDER is kept (active
    first), then the first listed.
    """
    key = ["season", "week", "team", "gsis_id"]
    rank = pl.col("status").replace_strict(
        {s: i for i, s in enumerate(ROSTER_STATUS_ORDER)},
        default=len(ROSTER_STATUS_ORDER),
        return_dtype=pl.Int32,
    )
    out = standard_teams(df, "team").with_row_index("listed")
    deduped = (
        pl.concat(
            [
                out.filter(pl.col("gsis_id").is_not_null())
                .sort(rank, "listed")
                .unique(key, keep="first"),
                out.filter(pl.col("gsis_id").is_null()),  # no id: nothing to match them on
            ]
        )
        .sort("listed")
        .drop("listed")
    )
    if deduped.height < out.height:
        log.info("weekly_rosters: dropped %d repeated rows", out.height - deduped.height)
    return deduped


def participation(df: pl.DataFrame) -> pl.DataFrame:
    """`nflverse_game_id` → `game_id`, and team codes."""
    return standard_teams(df.rename({"nflverse_game_id": "game_id"}), "possession_team")
