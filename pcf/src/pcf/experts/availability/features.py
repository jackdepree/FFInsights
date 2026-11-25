"""Availability's inputs at a prediction moment, from the view only (decision 0047).

One row per player on a roster or a health reserve list for each regular-season game predicted
at this moment (`roster_week`), with:
- **this week:** the state (`common.STATES`), the final report's status, practice and body part,
  and how many games he's been in this state;
- **his record:** proneness (named in-game injuries per scrimmage snap over his position's rate,
  shrunk by credibility: half weight at 2 expected injuries), past health absences and listings,
  his recovery length (games per past absence spell, shrunk toward his position's), whether this
  body part is one that repeats (H94) and was listed before;
- **exposure:** log snaps, touches and tackles made over his last game and last 4, this season's
  snaps, and a recency-weighted sum of snaps (half-life 2 games; the H96 follow-up's G and E);
- **the window:** the games left in his team's season, the next week it plays;
- **sequences** for the chain and the hidden health state: this season's past games as symbols.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.experts.availability.common import (
    CREDIBILITY,
    FIRST_HISTORY,
    GROUPS,
    RECOVERY_K,
    REPEATERS,
    STATUS,
    position_rates,
    practice_code,
    report,
    schedule,
    timeline,
)

c = pl.col
HALF_LIFE_GAMES = 2.0
LAST = 17  # team games: the exploration's repeat window
NUMERIC = [
    "st_l", "st_o", "st_r", "dur", "status", "practice", "no_practice",
    "part_soft", "part_hamstring", "part_knee", "part_ankle", "part_concussion", "part_shoulder",
    "part_not_injury", "part_other", "repeat_part", "part_before",
    "proneness", "credibility", "named_c", "absent17", "listed17", "absent_rate_c",
    "absent_s", "played_s", "games_s", "recovery", "spells_c", "streak", "since_absent",
    "last_played", "last_share", "last_absent", "last_named", "last_state_o", "last_state_r",
    "log_snaps1", "log_snaps4", "log_touches4", "log_tackles4", "log_snaps_s", "ewma_snaps",
    "age", "age2", "week_no", "left", "no_history",
    *[f"g_{g}" for g in GROUPS],
]  # fmt: skip
# One symbol per past game for the hidden health state (method 3): what was seen that game.
SYMBOLS = "0123456789"


def _symbol() -> pl.Expr:
    """0-2 not listed (played with his usual share or more than half of it, played less, no
    snap); 3-4 listed (played, didn't); 5-6 Out or Doubtful (played, didn't); 7 reserve."""
    low = c("share") < 0.5 * c("usual").fill_null(0.0)
    return (
        pl.when(c("reserve")).then(pl.lit("7"))
        .when(c("state") == "o").then(pl.when(c("played")).then(pl.lit("5")).otherwise(pl.lit("6")))
        .when(c("state") == "l").then(pl.when(c("played")).then(pl.lit("3")).otherwise(pl.lit("4")))
        .when(~c("played")).then(pl.lit("2"))
        .when(low).then(pl.lit("1"))
        .otherwise(pl.lit("0"))
    )  # fmt: skip


def _record(tl: pl.DataFrame, season: int) -> pl.DataFrame:
    """One row per player from his record before the moment."""
    # his usual share: the mean of his earlier played games this season (known before each game)
    played_share = pl.when(c("played")).then(c("share")).otherwise(None)
    tl = tl.with_columns(
        usual=(played_share.fill_null(0.0).cum_sum() - played_share.fill_null(0.0))
        .over("gsis_id", "season")
        / (c("played").cast(pl.Float64).cum_sum() - c("played").cast(pl.Float64))
        .over("gsis_id", "season")
        .replace(0.0, None),
    ).with_columns(symbol=_symbol(), prac=c("practice").cast(pl.String).fill_null("3"))
    # spells of health absence: a run of absent games
    tl = tl.with_columns(
        start=c("absent") & ~c("absent").shift(1).over("gsis_id").fill_null(False)
    )
    this = c("season") == season
    weights = np.power(0.5, np.arange(8)[::-1] / HALF_LIFE_GAMES)
    absent_i = c("absent").cast(pl.Int32)
    agg = tl.group_by("gsis_id").agg(
        snaps_c=c("snaps").sum(),
        named_c=c("named").sum().cast(pl.Float64),
        position_l=c("position").last(),
        absent_c=c("absent").filter(c("season") >= 2016).sum().cast(pl.Float64),
        games_c16=(c("season") >= 2016).sum().cast(pl.Float64),
        spells_c=c("start").sum().cast(pl.Float64),
        absent17=c("absent").tail(LAST).sum().cast(pl.Float64),
        listed17=c("listed").tail(LAST).sum().cast(pl.Float64),
        absent_s=c("absent").filter(this).sum().cast(pl.Float64),
        played_s=c("played").filter(this).sum().cast(pl.Float64),
        games_s=this.sum().cast(pl.Float64),
        snaps_s=c("snaps").filter(this).sum(),
        streak=absent_i.reverse().cum_min().sum().cast(pl.Float64),
        since_absent=(~c("absent")).cast(pl.Int32).reverse().cum_min().sum().cast(pl.Float64),
        any_absent=c("absent").any(),
        last_played=c("played").last().cast(pl.Float64),
        last_share=c("share").last(),
        last_absent=c("absent").last().cast(pl.Float64),
        last_named=c("named").last().cast(pl.Float64),
        last_state=c("state").last(),
        last_season=c("season").last(),
        last_week=c("week").last(),
        state_run=c("state").reverse().rle().first().struct.field("len").cast(pl.Float64),
        snaps1=c("snaps").last(),
        snaps4=c("snaps").tail(4).sum(),
        touches4=c("touches").tail(4).sum(),
        tackles4=c("tackles").tail(4).sum(),
        ewma=c("snaps").tail(8),
        parts17=c("part").tail(LAST).drop_nulls(),
        recent_parts=c("part").tail(3).drop_nulls(),
        obs_seq=c("symbol").filter(this).str.join(""),
        prac_seq=c("prac").filter(this).str.join(""),
    )
    agg = agg.with_columns(
        ewma_snaps=c("ewma").map_elements(
            lambda s: float(np.dot(weights[-len(s):], np.asarray(s))) if len(s) else 0.0,
            return_dtype=pl.Float64,
        ),
        since_absent=pl.when(c("any_absent")).then(c("since_absent")).otherwise(99.0),
    ).drop("ewma", "any_absent")
    # his recovery: games per past spell, shrunk toward his position's (RECOVERY_K spells)
    pos_recovery = (
        agg.filter(c("spells_c") > 0)
        .group_by("position_l")
        .agg(pos_rec=c("absent_c").sum() / c("spells_c").sum())
    )
    agg = agg.join(pos_recovery, on="position_l", how="left").with_columns(
        recovery=(c("absent_c") + RECOVERY_K * c("pos_rec").fill_null(2.0))
        / (c("spells_c") + RECOVERY_K)
    )
    rates = position_rates(tl)
    agg = agg.join(rates, left_on="position_l", right_on="position", how="left").with_columns(
        expected=c("snaps_c") * c("rate").fill_null(0.0)
    )
    z = c("expected") / (c("expected") + CREDIBILITY)
    return agg.with_columns(
        credibility=z.fill_nan(0.0),
        proneness=pl.when(c("expected") > 0)
        .then(z * c("named_c") / c("expected") + (1 - z))
        .otherwise(1.0),
        absent_rate_c=pl.when(c("games_c16") > 0).then(c("absent_c") / c("games_c16")),
    )


def _this_week(view, games: pl.DataFrame, sched: pl.DataFrame) -> pl.DataFrame:
    """The rows predicted, with what's known of this week: roster_week rows for the games, their
    final report (if posted by the moment), and the window."""
    ids = games["game_id"].implode()
    rw = view.table("roster_week", seasons=games["season"].unique().to_list()).filter(
        c("game_id").is_in(ids)
    ).rename({"status": "roster_status"})
    pg = view.table("player_game", seasons=games["season"].unique().to_list()).filter(
        c("game_id").is_in(ids)
    )
    pg = report(pg).select("gsis_id", "game_id", "status", "practice", "part", "listed",
                           "birth_date")  # fmt: skip
    nxt = sched.with_columns(
        next_week=c("week").shift(-1).over("team", "season"),
        left=(c("n_games") - c("gi")).cast(pl.Float64),
    ).select("game_id", "team", "gi", "n_games", "next_week", "left", "kickoff")
    rows = (
        rw.join(nxt, on=["game_id", "team"], how="inner")
        .join(pg, on=["gsis_id", "game_id"], how="left")
        .with_columns(
            c("status").fill_null(0), c("listed").fill_null(False),
        )  # fmt: skip
    )
    return rows.with_columns(
        state=pl.when(c("reserve")).then(pl.lit("r"))
        .when(c("status") >= 2).then(pl.lit("o"))
        .when(c("listed")).then(pl.lit("l"))
        .otherwise(pl.lit("h")),
        age=(c("kickoff").dt.date() - c("birth_date")).dt.total_days() / 365.25,
    )  # fmt: skip


def features(view, games: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """A row per player on a roster or a health reserve list for each game in `games` (regular
    season), including players with no earlier game."""
    season = int(games["season"].max())
    sched = schedule(view, range(FIRST_HISTORY, season + 1))
    rows = _this_week(view, games, sched)
    if rows.is_empty():
        return rows
    tl = timeline(view, season, sched)
    tl = tl.join(rows.select("gsis_id").unique(), on="gsis_id", how="semi")
    rec = _record(tl, season) if tl.height else None
    if rec is not None:
        rows = rows.join(rec, on="gsis_id", how="left")
    else:
        rows = rows.with_columns(pl.lit(None).alias(x) for x in ("last_season", "obs_seq"))
    same_season = c("last_season") == c("season")
    birth_age = c("age").fill_null(26.0)
    part = c("part")
    rows = rows.with_columns(
        no_history=c("snaps_c").is_null().cast(pl.Float64),
        # the run of this state continues from last game only within the season
        dur=pl.when(same_season & (c("last_state") == c("state")))
        .then(c("state_run") + 1)
        .otherwise(1.0),
        repeat_part=part.is_in(list(REPEATERS) + ["soft", "hamstring", "knee"]).fill_null(False),
        part_before=pl.when(part.is_not_null())
        .then(c("parts17").list.contains(part) & ~c("recent_parts").list.contains(part))
        .otherwise(False)
        .fill_null(False),
        age=birth_age,
        age2=(birth_age - 26.0) ** 2,
        week_no=c("week").cast(pl.Float64),
        log_snaps1=c("snaps1").fill_null(0.0).log1p(),
        log_snaps4=c("snaps4").fill_null(0.0).log1p(),
        log_touches4=c("touches4").fill_null(0.0).log1p(),
        log_tackles4=c("tackles4").fill_null(0.0).log1p(),
        log_snaps_s=pl.when(same_season).then(c("snaps_s")).otherwise(0.0).log1p(),
        ewma_snaps=c("ewma_snaps").fill_null(0.0).log1p(),
        no_practice=c("practice").is_null().cast(pl.Float64),
        practice=c("practice").cast(pl.Float64),
        status=c("status").cast(pl.Float64),
        last_state_o=(c("last_state") == "o").fill_null(False).cast(pl.Float64),
        last_state_r=(c("last_state") == "r").fill_null(False).cast(pl.Float64),
        **{f"st_{s}": (c("state") == s).cast(pl.Float64) for s in ("l", "o", "r")},
        **{f"part_{p}": (part == p).fill_null(False).cast(pl.Float64)
           for p in ("soft", "hamstring", "knee", "ankle", "concussion", "shoulder",
                     "not_injury", "other")},
        **{f"g_{g}": (c("position") == g).cast(pl.Float64) for g in GROUPS},
        # this season's record, or none yet
        absent_s=pl.when(same_season).then(c("absent_s")).otherwise(0.0),
        played_s=pl.when(same_season).then(c("played_s")).otherwise(0.0),
        games_s=pl.when(same_season).then(c("games_s")).otherwise(0.0),
        obs_seq=pl.when(same_season).then(c("obs_seq")).otherwise(pl.lit("")),
        prac_seq=pl.when(same_season).then(c("prac_seq")).otherwise(pl.lit("")),
    )  # fmt: skip
    rows = rows.with_columns(
        c("repeat_part", "part_before").cast(pl.Float64),
        obs_seq=c("obs_seq").fill_null(""),
        prac_seq=c("prac_seq").fill_null(""),
        grp=pl.when(c("position").is_in(list(GROUPS))).then(c("position")).otherwise(pl.lit("ST")),
    )
    keep = [*keys, "season", "week", "team", "position", "grp", "state", "reserve", "gi",
            "n_games", "next_week", "last_week", "obs_seq", "prac_seq", "part"]  # fmt: skip
    return rows.select(
        *keep, *[c(x).cast(pl.Float64).fill_nan(None).fill_null(0.0) for x in NUMERIC]
    ).with_columns(c("proneness").replace(0.0, 1.0))


def report_code(status: int) -> str:
    """For tests: a report status's name."""
    return {v: k for k, v in STATUS.items()}.get(status, "")


__all__ = ["NUMERIC", "SYMBOLS", "features", "practice_code"]
