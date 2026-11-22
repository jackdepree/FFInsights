"""The forecast's inputs at a prediction moment, from the view only (decision 0041).

Two kinds:
- **Playing time:** participation's own inputs (`pcf.experts.participation.features`: past snap
  shares, this week's depth chart and injury report, teammates out, new team, rookie), reused as
  code, not as its saved forecasts, so every season 2013-2025 can be scored.
- **The ball:** a player's past chances, from the `player_game.opportunity` part, averaged over the
  games he played (a chance or an offensive snap): this season so far (`_s`, last season's when he
  has no game yet), his last 4 (`_l4`) and last season (`_ls`). Plus his points over expected per
  chance and yards after the catch over expected per catch over this season and last
  (`poe_ch2`, `yac_ch2`), with how many chances and catches they rest on.

The column sets are the ladder's rungs (`COUNTS` → `XFP` → `EFF`; `GOAL_LINE` for the horizons).
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from pcf.experts.opportunity_quality.common import FIRST_SEASON, POSITIONS, known_games
from pcf.experts.participation.features import FEATURES as PLAYING
from pcf.experts.participation.features import INPUTS as PART_INPUTS
from pcf.experts.participation.features import features as playing_time

c = pl.col
INPUTS = {"player_game": (*PART_INPUTS["player_game"], "opportunity")}
AVERAGED = ["xfp", "fp", "poe", "targets", "carries", "snaps", "xrec", "xrush", "xtd", "gl", "rz",
            "ez", "deep", "air"]  # fmt: skip
WINDOWS = ("s", "l4", "ls")


def lagged(*names: str) -> list[str]:
    return [f"{n}_{w}" for n in names for w in WINDOWS]


POSITION = ["is_wr", "is_te", "young"]
COUNTS = [*PLAYING, *POSITION, *lagged("targets", "carries", "snaps"), "games_played"]
XFP = [*COUNTS, *lagged("xfp"), "xfp_r4"]
EFF = [*XFP, *lagged("poe", "fp"), "poe_ch2", "chances2", "yac_ch2", "yac_n2", "te_yac"]
GOAL_LINE = [*EFF, *lagged("gl", "rz", "ez", "deep", "air", "xtd")]
YARDS = [*EFF, *lagged("xrec", "xrush")]
PRIOR = 30.0  # chances: poe_ch2 and yac_ch2 are pulled toward 0 by this many (a plain shrink)


def _history(known: pl.DataFrame, season: int) -> pl.DataFrame:
    """One row per player from his known games."""
    played = known.filter(c("played"))
    this = c("season") == season
    last = c("season") == season - 1
    two = c("season") >= season - 1
    agg = played.group_by("gsis_id").agg(
        *[c(v).filter(this).mean().alias(f"{v}_s") for v in AVERAGED],
        *[c(v).tail(4).mean().alias(f"{v}_l4") for v in AVERAGED],
        *[c(v).filter(last).mean().alias(f"{v}_ls") for v in AVERAGED],
        games_played=this.sum().cast(pl.Float64),
        poe2=c("poe").filter(two).sum(),
        chances2=c("chances").filter(two).sum(),
        yac2=c("yac").filter(two).sum(),
        yac_n2=c("yac_n").filter(two).sum(),
    )
    rostered = known.group_by("gsis_id").agg(xfp_r4=c("xfp").tail(4).mean())
    return agg.join(rostered, on="gsis_id", how="full", coalesce=True)


def features(view, games: pl.DataFrame, keys: Sequence[str], scoring: str = "ppr") -> pl.DataFrame:
    """A row per rostered RB, WR and TE in `games`, with every column of `GOAL_LINE` and `YARDS`
    (0 where he has no history) and the groups `position`, `played_recently`, `young`."""
    season = int(games["season"].max())
    rows = playing_time(view, games, keys).filter(c("position").is_in(POSITIONS))
    pg = view.table(
        "player_game", seasons=[s for s in (season - 1, season) if s >= FIRST_SEASON - 1]
    )
    known = (
        known_games(pg, scoring, ["offense_snaps"])
        .with_columns(snaps=c("offense_snaps").fill_null(0).cast(pl.Float64))
        .with_columns(played=(c("chances") > 0) | (c("snaps") > 0))
    )
    hist = _history(known, season)
    rows = rows.join(hist, on="gsis_id", how="left").with_columns(
        *[c(f"{v}_s").fill_null(c(f"{v}_ls")) for v in AVERAGED],
    )
    rows = rows.with_columns(
        is_wr=(c("position") == "WR").cast(pl.Float64),
        is_te=(c("position") == "TE").cast(pl.Float64),
        young=(c("exp") <= 1).cast(pl.Float64),
        poe_ch2=c("poe2").fill_null(0.0) / (c("chances2").fill_null(0.0) + PRIOR),
        yac_ch2=c("yac2").fill_null(0.0) / (c("yac_n2").fill_null(0.0) + PRIOR),
    ).with_columns(te_yac=c("is_te") * c("yac_ch2"))
    numeric = sorted({*GOAL_LINE, *YARDS})
    return rows.with_columns(
        c(x).cast(pl.Float64).fill_nan(None).fill_null(0.0) for x in numeric
    ).drop("poe2", "yac2")
