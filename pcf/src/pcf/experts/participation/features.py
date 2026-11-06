"""The participation models' inputs at a prediction moment, from the view only: a player's past
shares (with and without absences), this week's depth chart and injury report, teammates' reports,
team changes and past box-score stats (brief D5). The rookie and new-team tags are known only an
hour before kickoff, so both are worked out here from what's known on Saturday."""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from pcf.experts.participation.common import FIRST_SEASON, known_shares

c = pl.col
POSITIONS = ("QB", "RB", "WR", "TE")
INPUTS = {"player_game": ("snaps", "game_status", "depth", "injury", "stats")}
STATUS = {"Out": 3, "Doubtful": 2, "Questionable": 1}
OUT = 2  # Doubtful or worse: not expected to play
BOX = ["targets", "carries", "receiving_yards", "rushing_yards", "attempts", "fantasy_points_ppr",
       "st_pct"]  # fmt: skip
EPA = ["passing_epa", "rushing_epa", "receiving_epa"]
PLAYS = ["attempts", "carries", "targets"]
FEATURES = [
    "last_game", "last3", "last8", "season_avg", "active_last", "active3", "active8",
    "missed_streak", "was_active", "games", "no_history", "new_season", "last_season_active",
    "no_last_season", "depth1", "depth2", "depth3", "unlisted", "depth_mean", "new_team",
    "changed_team",
    "rookie",
    "report", "practice", "no_practice", "mates_out", "mates_out_share",
]  # fmt: skip
CAREER = ["career", "career_active"]
EXTRA = [*[f"{s}_{n}" for s in BOX for n in (3, 8)], "epa_per_play", "age", "exp", "draft"]
BACK = ["back", "back_career"]  # the lasso can't find this interaction itself (F9)
WEEK = ["week_no", "final_week", "final_wins"]  # the week of the season, and resting starters (F29)


def _win_rates(view, season: int) -> pl.DataFrame:
    """Each team's win rate in this season's regular-season games known at this moment."""
    g = view.table("game", seasons=[season]).filter(
        (c("game_type") == "REG") & c("home_score").is_not_null()
    )
    margin = (c("home_score") - c("away_score")).cast(pl.Float64)
    sides = pl.concat(
        [g.select(team="home_team", margin=margin), g.select(team="away_team", margin=-margin)]
    )
    won = c("margin").gt(0).cast(pl.Float64) + 0.5 * c("margin").eq(0).cast(pl.Float64)
    return sides.group_by("team").agg(win_rate=won.mean())


def with_week(view, games: pl.DataFrame, rows: pl.DataFrame) -> pl.DataFrame:
    """The week of the season, the last regular-season week, and that times the team's win rate so
    far: a stand-in for having clinched, since seeding isn't in our tables (F29, F30). Reads `game`
    with the `result` part, so an untouched win rate is 0.5 until a team's first result is known."""
    season = int(games["season"].max())
    sched = view.table("game", seasons=[season])
    last = sched.filter(c("game_type") == "REG")["week"].max()
    this = sched.filter(c("game_id").is_in(games["game_id"].implode())).select(
        "game_id", "week", "game_type"
    )
    final = ((c("week") == last) & (c("game_type") == "REG")).cast(pl.Float64)
    return (
        rows.join(this, on="game_id", how="left")
        .join(_win_rates(view, season), on="team", how="left")
        .with_columns(
            week_no=c("week").cast(pl.Float64),
            final_week=final,
            final_wins=final * c("win_rate").fill_null(0.5),
        )
        .drop("week", "game_type", "win_rate")
    )


def _history(known: pl.DataFrame, season: int) -> pl.DataFrame:
    """One row per player from their known games."""
    played = c("share").filter(c("active"))
    this = c("season") == season
    return known.group_by("gsis_id").agg(
        last_game=c("share").last(),
        last3=c("share").tail(3).mean(),
        last8=c("share").tail(8).mean(),
        season_avg=c("share").filter(this).mean(),
        active_last=played.last(),
        active3=played.tail(3).mean(),
        active8=played.tail(8).mean(),
        career=c("share").mean(),
        career_active=played.mean(),
        last_season_active=c("share").filter(c("active") & (c("season") == season - 1)).mean(),
        missed_streak=c("active").cast(pl.Int8).reverse().cum_max().eq(0).sum().cast(pl.Float64),
        was_active=c("active").last().cast(pl.Float64),
        games=c("share").len().cast(pl.Float64),
        new_season=(~this.any()).cast(pl.Float64),
        last_team=c("team").last(),
        last_season_team=c("team").filter(c("season") == season - 1).last(),
        last_depth=c("depth").drop_nulls().last(),
        last_depth_mean=c("depth_mean").drop_nulls().last(),
        **{f"{s}_{n}": c(s).fill_null(0.0).tail(n).mean() for s in BOX for n in (3, 8)},
        epa=c("epa").tail(8).sum(),
        plays=c("plays").tail(8).sum(),
    )


def _this_week(pg: pl.DataFrame, games: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """The rows predicted: every offensive skill player on the spine, with what's known of them."""
    kickoff = games.select("game_id", "kickoff")
    return (
        pg.filter(c("position").is_in(POSITIONS))
        .join(kickoff, on="game_id")
        .select(
            *keys, "team", "position", "depth", "depth_mean",
            rookie=(c("season") == c("rookie_year")).fill_null(False).cast(pl.Float64),
            report=c("report_status").replace_strict(STATUS, default=0, return_dtype=pl.Float64),
            practice=pl.when(c("practice_status").str.starts_with("Did Not")).then(2.0)
            .when(c("practice_status").str.starts_with("Limited")).then(1.0)
            .when(c("practice_status").str.starts_with("Full")).then(0.0),
            age=(c("kickoff").dt.date() - c("birth_date")).dt.total_days() / 365.25,
            exp=c("years_exp").cast(pl.Float64),
            draft=c("draft_number").cast(pl.Float64),
        )
    )  # fmt: skip


def features(view, games: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """A row per rostered QB, RB, WR and TE in `games`, including players with no earlier game.
    The chart for this game may be hidden (daily charts are known at kickoff, from 2025), so the
    player's last known chart stands in."""
    season = int(games["season"].max())
    pg = view.table("player_game", seasons=list(range(FIRST_SEASON, season + 1)))
    known = known_shares(
        pg.with_columns(
            epa=pl.sum_horizontal(c(x).fill_null(0.0) for x in EPA),
            plays=pl.sum_horizontal(c(x).fill_null(0).cast(pl.Float64) for x in PLAYS),
        ),
        ["team", "depth", "depth_mean", *BOX, "epa", "plays"],
    )
    rows = _this_week(pg.filter(c("game_id").is_in(games["game_id"].implode())), games, keys).join(
        _history(known, season), on="gsis_id", how="left"
    )
    rows = rows.with_columns(
        no_history=c("games").is_null().cast(pl.Float64),
        no_last_season=c("last_season_active").is_null().cast(pl.Float64),
        no_practice=c("practice").is_null().cast(pl.Float64),
        depth=pl.coalesce("depth", "last_depth"),
        depth_mean=pl.coalesce("depth_mean", "last_depth_mean"),
    )
    # Same-position teammates listed Out or Doubtful, and the share they've been taking
    mates = (
        rows.filter(c("report") >= OUT)
        .group_by("game_id", "team", "position")
        .agg(n=pl.len(), taken=c("last3").fill_null(0.0).sum())
    )
    out = c("report") >= OUT
    rows = (
        rows.join(mates, on=["game_id", "team", "position"], how="left")
        .with_columns(
            mates_out=c("n").fill_null(0).cast(pl.Float64) - out.cast(pl.Float64),
            mates_out_share=c("taken").fill_null(0.0)
            - pl.when(out).then(c("last3").fill_null(0.0)).otherwise(0.0),
            season_avg=pl.coalesce("season_avg", "last8"),
            depth1=(c("depth") == 1).fill_null(False).cast(pl.Float64),
            depth2=(c("depth") == 2).fill_null(False).cast(pl.Float64),
            depth3=(c("depth") >= 3).fill_null(False).cast(pl.Float64),
            unlisted=c("depth").is_null().cast(pl.Float64),
            depth_mean=c("depth_mean").fill_null(5.0),
            new_team=(c("team") != c("last_season_team")).fill_null(False).cast(pl.Float64),
            changed_team=(c("team") != c("last_team")).fill_null(False).cast(pl.Float64),
            draft=c("draft").fill_null(300.0),
            back=(c("missed_streak") > 0).fill_null(False).cast(pl.Float64),
            played_recently=(c("last8") > 0).fill_null(False),
        )
        .with_columns(
            back_career=c("back") * c("career_active").fill_null(0.0),
            epa_per_play=pl.when(c("plays") > 0).then(c("epa") / c("plays")),
        )
    )
    numeric = [*FEATURES, *CAREER, *EXTRA, *BACK]
    return rows.with_columns(c(x).cast(pl.Float64).fill_nan(None).fill_null(0.0) for x in numeric)
