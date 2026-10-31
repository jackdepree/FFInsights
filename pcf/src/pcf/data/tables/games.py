"""The `game` and `team_game` tables, from schedules and team stats.

Schedules hold three kinds of field, known at three times (`timeline` schedules rule): facts at
schedule release (playoff games: the start of their week), lines at kickoff, results the day
after. Starting QBs, coaches and the referee are in the pregame part: known at kickoff, leaning
late. Weather (`temp`, `wind`) is measured at the game, so it's in the result.
"""

import polars as pl

from pcf.data.clean import standard
from pcf.data.tables.frames import on_spine, team_games
from pcf.data.timeline import Calendar, known_at

FACTS = [
    "week",
    "game_type",
    "gameday",
    "weekday",
    "gametime",
    "kickoff",
    "home_team",
    "away_team",
    "location",
    "old_game_id",
    "gsis",
    "nfl_detail_id",
    "pfr",
    "pff",
    "espn",
    "ftn",
    "away_rest",
    "home_rest",
    "div_game",
    "roof",
    "surface",
    "stadium_id",
    "stadium",
]
PREGAME = [
    "spread_line",
    "home_spread",
    "total_line",
    "away_moneyline",
    "home_moneyline",
    "away_spread_odds",
    "home_spread_odds",
    "under_odds",
    "over_odds",
    "away_qb_id",
    "home_qb_id",
    "away_qb_name",
    "home_qb_name",
    "away_coach",
    "home_coach",
    "referee",
]
RESULT = ["away_score", "home_score", "result", "total", "overtime", "temp", "wind"]
# Per team, from the home and away columns.
TEAM_PREGAME = ["moneyline", "spread_odds", "qb_id", "qb_name", "coach"]
TEAM_FACTS = ["rest"]
# Team stats columns that the schedule part already has.
TEAM_STATS_DROP = ["week", "season_type", "opponent_team"]


def _schedules(schedules: pl.DataFrame, cal: Calendar) -> pl.DataFrame:
    """Standardized schedules with kickoff and the three known-at columns."""
    out = known_at("schedules", schedules, cal).join(
        cal.games.select("game_id", "kickoff"), on="game_id", how="left"
    )
    return out.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))


def game_parts(schedules: pl.DataFrame, cal: Calendar) -> dict[str, pl.DataFrame]:
    """`standard.schedules` rows → the `game` parts: schedule (the spine), pregame, result."""
    s = _schedules(schedules, cal)
    return {
        "schedule": s.select("game_id", "season", *FACTS, known_at="facts_known_at"),
        "pregame": s.select("game_id", "season", *PREGAME, known_at="lines_known_at"),
        "result": s.filter(pl.col("home_score").is_not_null()).select(
            "game_id", "season", *RESULT, known_at="known_at"
        ),
    }


def _per_team(s: pl.DataFrame, columns: list[str]) -> pl.DataFrame:
    """Home and away columns (`home_x`, `away_x`) → one row per team with `x`."""
    sides = []
    for side in ("home", "away"):
        sides.append(
            s.select(
                "game_id",
                team=pl.col(f"{side}_team"),
                **{c: pl.col(f"{side}_{c}") for c in columns},
            )
        )
    return pl.concat(sides)


def team_game_parts(
    schedules: pl.DataFrame, cal: Calendar, team_stats: pl.DataFrame | None = None
) -> dict[str, pl.DataFrame]:
    """`standard.schedules` rows (+ raw team stats) → the `team_game` parts: schedule (the
    spine), pregame, result, stats. Spreads are betting style for each team (−3.5 = favored)."""
    s = _schedules(schedules, cal)
    keys = ["game_id", "team"]
    spine = (
        team_games(cal.games)
        .join(_per_team(s, TEAM_FACTS), on=keys, how="left")
        .join(s.select("game_id", "div_game", known_at="facts_known_at"), on="game_id")
    )
    pregame = (
        spine.select(*keys, "season", "home")
        .join(_per_team(s, TEAM_PREGAME), on=keys, how="left")
        .join(
            s.select("game_id", "home_spread", "total_line", known_at="lines_known_at"),
            on="game_id",
        )
        .with_columns(spread=pl.when("home").then("home_spread").otherwise(-pl.col("home_spread")))
        .drop("home", "home_spread")
    )
    scored = s.filter(pl.col("home_score").is_not_null())
    result = (
        spine.select(*keys, "season")
        .join(_per_team(scored, ["score"]), on=keys)
        .join(
            _per_team(
                scored.rename({"home_team": "away_team", "away_team": "home_team"}), ["score"]
            ).rename({"score": "points_against"}),
            on=keys,
        )
        .join(scored.select("game_id", "known_at"), on="game_id")
        .rename({"score": "points_for"})
        .with_columns(margin=pl.col("points_for") - pl.col("points_against"))
    )
    parts = {"schedule": spine, "pregame": pregame, "result": result}
    if team_stats is not None:
        stats = known_at(
            "team_stats", standard.standard_teams(team_stats, "team", "opponent_team"), cal
        ).with_columns(pl.col("season").cast(pl.Int32))
        parts["stats"] = on_spine(stats.drop(TEAM_STATS_DROP), spine, keys, "team_game.stats")
    return parts
