"""`player_game.on_field_pace`: each player's team rates on and off the field in a game
(player-pace brief; exploration F1-F4; decision 0029). Pure: built from saved parts.

From who was on the field on each play (`player_play.on_field`, participation: post-season, 2016
on) and pace's per-play measures (`play.pace`), regular and post-season snaps with a pass rate
over expected. Per player-game, on the side he played most:
- `onf_side`: offense or defense. A defender's rates are what the offense did with him on.
- `onf_plays`, `onf_team_plays`: his plays and the offense's plays in the game.
- `onf_proe_on`, `onf_proe_off`: PCF's pass rate over expected on and off his plays.
- `onf_pm_proe`: on minus off, and `onf_w_proe`, its weight, n_on * n_off / n_team (the weight a
  difference of two means earns; 0 when he never sat out, and then the plus-minus is null).
- `onf_pm_proe_pers`: the same within personnel groupings: each play's PROE less the offense's
  season average for its `offense_personnel` (F4: backs' plus-minus is their package).
- `onf_pace_on`, `onf_pace_off`, `onf_pm_pace`, `onf_w_pace`: the same for pace over expected,
  on the snaps it's measured on.

Known when participation is: the day after the Super Bowl.
"""

from __future__ import annotations

import polars as pl

c = pl.col
KEYS = ["gsis_id", "game_id"]
PLAY_COLUMNS = ["game_id", "play_id", "posteam", "pcf_pass_oe", "pace_oe", "offense_personnel"]
ON_FIELD_COLUMNS = ["game_id", "play_id", "season", "side", "gsis_id", "known_at"]


def _diff(on_sum: str, on_n: str, team_sum: str, team_n: str) -> tuple[pl.Expr, pl.Expr, pl.Expr]:
    off_n = c(team_n) - c(on_n)
    on = pl.when(c(on_n) > 0).then(c(on_sum) / c(on_n))
    off = pl.when(off_n > 0).then((c(team_sum) - c(on_sum)) / off_n)
    weight = pl.when((c(on_n) > 0) & (off_n > 0)).then(c(on_n) * off_n / c(team_n)).otherwise(0.0)
    return on, off, weight


def player_pace_rows(plays: pl.DataFrame, on_field: pl.DataFrame) -> pl.DataFrame:
    """One row per player-game: `plays` is one row per snap (PLAY_COLUMNS, from `play.pace`,
    `play.pbp` and `play.participation`); `on_field` one row per player on a play
    (ON_FIELD_COLUMNS)."""
    p = plays.filter(c("pcf_pass_oe").is_not_null() & c("posteam").is_not_null())
    season_of = on_field.select("game_id", "season").unique("game_id")
    p = p.join(season_of, on="game_id", how="inner").with_columns(
        c("offense_personnel").fill_null("unknown")
    )
    p = p.with_columns(
        proe_pers=c("pcf_pass_oe")
        - c("pcf_pass_oe").mean().over("posteam", "season", "offense_personnel")
    )
    team = p.group_by("game_id", "posteam").agg(
        n_team=pl.len(),
        s_team=c("pcf_pass_oe").sum(),
        s_team_pers=c("proe_pers").sum(),
        np_team=c("pace_oe").count(),
        sp_team=c("pace_oe").sum(),
    )
    rows = on_field.join(
        p.select("game_id", "play_id", "posteam", "pcf_pass_oe", "proe_pers", "pace_oe"),
        on=["game_id", "play_id"],
        how="inner",
    )
    per = rows.group_by(*KEYS, "side").agg(
        c("season").first(),
        c("posteam").mode().first(),
        known_at=c("known_at").max(),
        n_on=pl.len(),
        s_on=c("pcf_pass_oe").sum(),
        s_on_pers=c("proe_pers").sum(),
        np_on=c("pace_oe").count(),
        sp_on=c("pace_oe").sum(),
    )
    # a player on both sides in one game keeps the side he played most
    per = per.sort("n_on", "side", descending=[True, False]).unique(KEYS, keep="first")
    d = per.join(team, on=["game_id", "posteam"], how="inner")
    proe_on, proe_off, w_proe = _diff("s_on", "n_on", "s_team", "n_team")
    pers_on, pers_off, _ = _diff("s_on_pers", "n_on", "s_team_pers", "n_team")
    pace_on, pace_off, w_pace = _diff("sp_on", "np_on", "sp_team", "np_team")
    return (
        d.with_columns(
            onf_proe_on=proe_on,
            onf_proe_off=proe_off,
            onf_w_proe=w_proe,
            onf_pm_proe_pers=pers_on - pers_off,
            onf_pace_on=pace_on,
            onf_pace_off=pace_off,
            onf_w_pace=w_pace,
        )
        .with_columns(
            onf_pm_proe=c("onf_proe_on") - c("onf_proe_off"),
            onf_pm_pace=c("onf_pace_on") - c("onf_pace_off"),
        )
        .select(
            *KEYS,
            *[
                c(x).cast(pl.Float64)
                for x in (
                    "onf_proe_on",
                    "onf_proe_off",
                    "onf_pm_proe",
                    "onf_w_proe",
                    "onf_pm_proe_pers",
                    "onf_pace_on",
                    "onf_pace_off",
                    "onf_pm_pace",
                    "onf_w_pace",
                )
            ],
            season=c("season").cast(pl.Int32),
            onf_side=c("side"),
            onf_plays=c("n_on").cast(pl.Int32),
            onf_team_plays=c("n_team").cast(pl.Int32),
            known_at=c("known_at"),
        )
        .sort(KEYS)
    )


# Roster positions to the groups the exploration measured (F3, F8)
GROUPS = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
    "OL": "OL", "T": "OL", "G": "OL", "C": "OL",
    "DL": "DL", "DE": "DL", "DT": "DL", "NT": "DL",
    "LB": "LB", "OLB": "LB", "ILB": "LB", "MLB": "LB",
    "DB": "DB", "CB": "DB", "S": "DB", "SS": "DB", "FS": "DB",
}  # fmt: skip
SEASON_COLUMNS = [
    "onf_side", "onf_group", "onf_team", "onf_games", "onf_plays", "onf_proe_on",
    "onf_pm_proe", "onf_w_proe", "onf_pm_proe_pers", "onf_pm_pace", "onf_w_pace", "last_kickoff",
]  # fmt: skip


def _weighted(value: str, weight: str) -> pl.Expr:
    w = pl.when(c(value).is_not_null()).then(c(weight)).otherwise(0.0)
    return pl.when(w.sum() > 0).then((c(value).fill_null(0.0) * w).sum() / w.sum())


def player_season_rows(
    games: pl.DataFrame, roster: pl.DataFrame, kickoffs: pl.DataFrame
) -> pl.DataFrame:
    """`player_season.on_field_pace`: one row per player and season from his
    `player_game.on_field_pace` rows (`games`), his roster rows (gsis_id, game_id, team,
    position) and the games' kickoffs (game_id, kickoff): his side and position group (most
    plays), team (most plays), games, plays, each plus-minus as the weighted average of his games
    (the weights summed), and his last game's kickoff (`last_kickoff`, for leakage check 2). Known
    when the season's last row is: the day after the Super Bowl."""
    games = games.join(kickoffs.select("game_id", "kickoff"), on="game_id", how="left")
    g = games.join(
        roster.select("gsis_id", "game_id", "team", "position"),
        on=["gsis_id", "game_id"],
        how="left",
    ).with_columns(onf_group=c("position").replace_strict(GROUPS, default="other"))
    top = lambda col: c(col).sort_by(c("onf_plays")).last()  # noqa: E731
    return (
        g.group_by("gsis_id", "season")
        .agg(
            onf_side=top("onf_side"),
            onf_group=top("onf_group"),
            onf_team=top("team"),
            onf_games=pl.len().cast(pl.Int32),
            onf_plays=c("onf_plays").sum().cast(pl.Int32),
            onf_proe_on=_weighted("onf_proe_on", "onf_plays"),
            onf_pm_proe=_weighted("onf_pm_proe", "onf_w_proe"),
            onf_w_proe=c("onf_w_proe").sum(),
            onf_pm_proe_pers=_weighted("onf_pm_proe_pers", "onf_w_proe"),
            onf_pm_pace=_weighted("onf_pm_pace", "onf_w_pace"),
            onf_w_pace=c("onf_w_pace").sum(),
            last_kickoff=c("kickoff").max(),
            known_at=c("known_at").max(),
        )
        .with_columns(c("season").cast(pl.Int32))
        .select("gsis_id", "season", *SEASON_COLUMNS, "known_at")
        .sort("gsis_id", "season")
    )
