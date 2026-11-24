"""The touchdown forecasts' inputs at a prediction moment, from the view only (decision 0043).

**Players** (every rostered QB, RB, WR and TE in the games predicted):
- **Playing time:** participation's own inputs (`pcf.experts.participation.features`: past snap
  shares, this week's depth chart and injury report, teammates out, new team, rookie), reused as
  code, like opportunity-quality's.
- **His own record:** per game he played, this season so far (`_s`, last season's when he has no
  game yet), his last 4 (`_l4`) and last season (`_ls`): touchdowns, expected touchdowns, chances
  (and by kind: carries, targets, inside the 20, inside the 10, inside the 5, into the end zone;
  a QB's red-zone carries), yards, snaps; a QB's throws, thrown touchdowns and expected ones,
  passing yards. His touchdowns over expected over this season and last, per chance and per
  throw, shrunk toward 0 (`tdoe_ch`, `thrown_tdoe`), with what they rest on.
- **His team and opponent** (this season so far, last season's before the first game): the
  team's touchdowns, expected touchdowns and drive-aware hindsight a game, its EPA a play, its
  calling (the pass share of its chances inside the 10, neutral pass rate over expected); his
  share of the team's chances inside the 10; the opponent's touchdowns and expected touchdowns
  allowed a game.
- `last_game_id`, `last_xtd`, `last_thrown_xtd`: his most recent game played and its expected
  touchdowns. Method A's first stage learns next game's expected touchdowns from them (a later
  row's `last_xtd` is an earlier row's next game), so it never sees an outcome after the moment.

**Teams:** the same team and opponent record, with last 4 and last season windows, home or away.
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from pcf.experts.participation.features import FEATURES as PLAYING
from pcf.experts.participation.features import INPUTS as PART_INPUTS
from pcf.experts.participation.features import features as playing_time
from pcf.experts.td_expert.common import (
    FIRST_XTD,
    POSITIONS,
    known_player_games,
    known_team_games,
)

c = pl.col
TEAM_PARTS = ("touchdowns", "efficiency", "tendencies", "openers")
INPUTS = {
    "player_game": (*PART_INPUTS["player_game"], "touchdowns"),
    "team_game": TEAM_PARTS,
}
TEAM_INPUTS = {"team_game": TEAM_PARTS}
WINDOWS = ("s", "l4", "ls")
AVERAGED = ["td", "xtd", "chances", "carries", "targets", "yards", "snaps", "rz", "i10", "gl",
            "ez", "rz_carries", "throws", "thrown_td", "thrown_xtd", "pass_yards",
            "rz_throws"]  # fmt: skip
TEAM_AVERAGED = ["td", "xtd", "hind", "rz_trips", "drives", "chances"]
TDOE_PRIOR = 100.0  # chances: his touchdowns over expected per chance are pulled toward 0
THROWN_PRIOR = 300.0  # throws (EXPLORATION F22: about 1,280 before his own rate is worth half)


def lagged(*names: str, windows: Sequence[str] = WINDOWS) -> list[str]:
    return [f"{n}_{w}" for n in names for w in windows]


POSITION = ["is_qb", "is_wr", "is_te"]
TEAM = ["team_td_s", "team_xtd_s", "team_hind_s", "team_epa_s", "team_i10_pass", "team_pass_oe",
        "opp_td_allowed", "opp_xtd_allowed", "opp_epa_allowed"]  # fmt: skip
# Rung 0 (`rate`): his touchdowns and games over this season and last
RATE = ["td2", "games2", "thrown_td2"]
# Method B (`volume`): volume, his touchdowns, playing time, the team and opponent
VOLUME = [*PLAYING, *POSITION, *lagged("yards", "chances", "snaps", "td"), "games_played",
          *TEAM]  # fmt: skip
VOLUME_THROWN = [*PLAYING, *lagged("pass_yards", "throws", "thrown_td", "snaps"),
                 "games_played", *TEAM]  # fmt: skip
# Method A, stage 1 (`chances`): next game's expected touchdowns from his chances and playing time
STAGE1 = [*PLAYING, *POSITION, *lagged("xtd", "chances", "carries", "targets", "rz", "i10", "gl",
          "ez", "rz_carries", "snaps"), "games_played", "team_xtd_s", "opp_xtd_allowed"]  # fmt: skip
STAGE1_THROWN = [*PLAYING, *lagged("thrown_xtd", "throws", "rz_throws", "snaps"), "games_played",
                 "team_xtd_s", "opp_xtd_allowed"]  # fmt: skip
# Method A, stage 2: the small corrections (EXPLORATION F5, F16, F21, F22)
CORRECTIONS = [*POSITION, "tdoe_ch", "team_epa_s", "team_i10_pass", "team_pass_oe", "i10_share",
               "opp_td_allowed", "opp_epa_allowed"]  # fmt: skip
CORRECTIONS_THROWN = ["thrown_tdoe", "team_epa_s", "team_i10_pass", "team_pass_oe",
                      "opp_td_allowed", "opp_epa_allowed"]  # fmt: skip
# I58: a QB's red-zone carries beside volume (only QBs' rows carry them)
QB_RZ = ["qb_rz_carries_s", "qb_rz_carries_ls"]
# H68 (build): red-zone chances and explosive... beside volume: red-zone chances only (F2-F4)
RED_ZONE = lagged("rz", "i10")
# H67 (build): the team's calling, alone
CALLING = ["team_i10_pass", "team_pass_oe"]
NUMERIC = sorted({*VOLUME, *VOLUME_THROWN, *STAGE1, *STAGE1_THROWN, *CORRECTIONS,
                  *CORRECTIONS_THROWN, *QB_RZ, *RED_ZONE, *RATE, "xtd2", "chances2",
                  "thrown_xtd2", "throws2", "last_xtd", "last_thrown_xtd",
                  "games_left"})  # fmt: skip
TEAM_OWN = [*lagged(*TEAM_AVERAGED), "team_epa_s", "team_epa_ls", "team_i10_pass",
            "team_pass_oe", "games_played", "home"]  # fmt: skip
TEAM_OPP = ["opp_td_allowed", "opp_xtd_allowed", "opp_epa_allowed", "opp_hind_allowed"]
TEAM_RATE = ["td2", "games2"]
TEAM_VOLUME = [*TEAM_OWN, *TEAM_OPP]
# I118 (the CEO, 2026-11-24): ESPN's opening line for the game, known at the run (2023 on): the
# total around 44 and the team's expected margin; 0 and a flag where there's none, so the line's
# weight is learned on the rows that have one
LINE = ["line_total", "line_margin", "has_line"]
LINE_CENTER = 44.0
TEAM_STAGE1 = [*lagged("xtd", "hind", "rz_trips", "drives", "chances"), "team_epa_s",
               "games_played", "home", "opp_xtd_allowed", "opp_hind_allowed"]  # fmt: skip
TEAM_CORRECTIONS = ["team_epa_s", "team_i10_pass", "team_pass_oe", "tdoe_g", "opp_td_allowed",
                    "opp_epa_allowed"]  # fmt: skip
TEAM_NUMERIC = sorted({*TEAM_VOLUME, *TEAM_STAGE1, *TEAM_CORRECTIONS, *TEAM_RATE, *LINE, "xtd2",
                       "last_xtd", "games_left"})  # fmt: skip


# ---------------------------------------------------------------- the team side
def _season_means(df: pl.DataFrame, key: str, season: int, cols: Sequence[str],
                  prefix: str) -> pl.DataFrame:  # fmt: skip
    """Per `key`: the mean a game of each column this season so far, else last season's."""
    this, last = c("season") == season, c("season") == season - 1
    return df.group_by(key).agg(
        *[pl.coalesce(c(x).filter(this).mean(), c(x).filter(last).mean()).alias(f"{prefix}{x}")
          for x in cols],
    )  # fmt: skip


def team_context(view, season: int) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(each team's record, each team's defense) from the team-games known at this moment,
    this season so far (last season's before its first game)."""
    tg = known_team_games(view.table("team_game", seasons=[season - 1, season]))
    this, last = c("season") == season, c("season") == season - 1
    two = c("season") >= season - 1
    own = tg.group_by("team").agg(
        *[pl.coalesce(c(x).filter(this).mean(), c(x).filter(last).mean()).alias(f"{x}_s")
          for x in TEAM_AVERAGED],
        *[c(x).tail(4).mean().alias(f"{x}_l4") for x in TEAM_AVERAGED],
        *[c(x).filter(last).mean().alias(f"{x}_ls") for x in TEAM_AVERAGED],
        team_epa_s=pl.coalesce(c("epa").filter(this).sum() / c("plays").filter(this).sum(),
                               c("epa").filter(last).sum() / c("plays").filter(last).sum()),
        team_epa_ls=c("epa").filter(last).sum() / c("plays").filter(last).sum(),
        team_i10_pass=c("i10_targets").filter(two).sum()
        / (c("i10_targets") + c("i10_carries")).filter(two).sum(),
        team_i10_chances_s=pl.coalesce((c("i10_targets") + c("i10_carries")).filter(this).mean(),
                                       (c("i10_targets") + c("i10_carries")).filter(last).mean()),
        team_pass_oe=pl.coalesce(c("pass_oe").filter(this).mean(), c("pass_oe").filter(last).mean()),
        games_played=this.sum().cast(pl.Float64),
        td2=c("td").filter(two).sum(), xtd2=c("xtd").filter(two).sum(),
        games2=two.sum().cast(pl.Float64),
        last_game_id=c("game_id").last(), last_xtd=c("xtd").last(),
    )  # fmt: skip
    defense = tg.group_by(team="opponent").agg(
        opp_td_allowed=pl.coalesce(c("td").filter(this).mean(), c("td").filter(last).mean()),
        opp_xtd_allowed=pl.coalesce(c("xtd").filter(this).mean(), c("xtd").filter(last).mean()),
        opp_hind_allowed=pl.coalesce(c("hind").filter(this).mean(), c("hind").filter(last).mean()),
        opp_epa_allowed=pl.coalesce(c("epa").filter(this).sum() / c("plays").filter(this).sum(),
                                    c("epa").filter(last).sum() / c("plays").filter(last).sum()),
    )  # fmt: skip
    return own, defense


def _opponents(view, games: pl.DataFrame) -> pl.DataFrame:
    """Each team in `games`: its opponent, home or away, and `games_left`, its regular-season
    games from this one to the season's end (the schedule is known in advance; 0 in the
    playoffs). The rest-of-season forecasts' exposure."""
    season = int(games["season"].max())
    sched = view.table("team_game", seasons=[season]).select(
        "game_id", "team", "opponent", "home", "week", "game_type"
    )
    reg = sched.filter(c("game_type") == "REG").select("team", reg_week="week")
    these = sched.filter(c("game_id").is_in(games["game_id"].implode()))
    left = (
        these.join(reg, on="team", how="left")
        .group_by("game_id", "team")
        .agg(games_left=((c("reg_week") >= c("week")) & (c("game_type") == "REG")).sum())
    )
    return these.join(left, on=["game_id", "team"], how="left").with_columns(
        games_left=c("games_left").fill_null(0).cast(pl.Float64)
    )


# ---------------------------------------------------------------- players
def _history(known: pl.DataFrame, season: int) -> pl.DataFrame:
    """One row per player from his known games."""
    played = known.filter(c("played"))
    this, last, two = c("season") == season, c("season") == season - 1, c("season") >= season - 1
    return played.group_by("gsis_id").agg(
        *[c(v).filter(this).mean().alias(f"{v}_s") for v in AVERAGED],
        *[c(v).tail(4).mean().alias(f"{v}_l4") for v in AVERAGED],
        *[c(v).filter(last).mean().alias(f"{v}_ls") for v in AVERAGED],
        games_played=this.sum().cast(pl.Float64),
        games2=two.sum().cast(pl.Float64),
        **{f"{v}2": c(v).filter(two).sum() for v in ("td", "xtd", "chances", "thrown_td",
                                                     "thrown_xtd", "throws")},
        last_game_id=c("game_id").last(),
        last_xtd=c("xtd").last(),
        last_thrown_xtd=c("thrown_xtd").last(),
    )  # fmt: skip


def features(view, games: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """A row per rostered QB, RB, WR and TE in `games`, with every column of `NUMERIC` (0 where
    he has no history), `position`, `team` and `last_game_id`."""
    season = int(games["season"].max())
    rows = playing_time(view, games, keys).filter(c("position").is_in(POSITIONS))
    pg = view.table("player_game", seasons=[s for s in (season - 1, season) if s >= FIRST_XTD])
    hist = _history(known_player_games(pg), season)
    rows = rows.join(hist, on="gsis_id", how="left").with_columns(
        *[c(f"{v}_s").fill_null(c(f"{v}_ls")) for v in AVERAGED],
    )
    own, defense = team_context(view, season)
    opp = _opponents(view, games).select("game_id", "team", "opponent", "games_left")
    own = own.select(
        "team", team_td_s="td_s", team_xtd_s="xtd_s", team_hind_s="hind_s",
        team_epa_s="team_epa_s", team_i10_pass="team_i10_pass", team_pass_oe="team_pass_oe",
        team_i10_chances_s="team_i10_chances_s",
    )  # fmt: skip
    rows = (
        rows.join(opp, on=["game_id", "team"], how="left")
        .join(own, on="team", how="left")
        .join(defense.rename({"team": "opponent"}), on="opponent", how="left")
    )
    is_qb = c("position") == "QB"
    rows = rows.with_columns(
        is_qb=is_qb.cast(pl.Float64),
        is_wr=(c("position") == "WR").cast(pl.Float64),
        is_te=(c("position") == "TE").cast(pl.Float64),
        tdoe_ch=(c("td2").fill_null(0.0) - c("xtd2").fill_null(0.0))
        / (c("chances2").fill_null(0.0) + TDOE_PRIOR),
        thrown_tdoe=(c("thrown_td2").fill_null(0.0) - c("thrown_xtd2").fill_null(0.0))
        / (c("throws2").fill_null(0.0) + THROWN_PRIOR),
        i10_share=pl.when(c("team_i10_chances_s") > 0)
        .then(c("i10_s") / c("team_i10_chances_s")).otherwise(0.0),
        qb_rz_carries_s=pl.when(is_qb).then(c("rz_carries_s")).otherwise(0.0),
        qb_rz_carries_ls=pl.when(is_qb).then(c("rz_carries_ls")).otherwise(0.0),
    )  # fmt: skip
    return rows.with_columns(
        c(x).cast(pl.Float64).fill_nan(None).fill_null(0.0) for x in NUMERIC
    ).with_columns(c("last_game_id").fill_null(""))


# ---------------------------------------------------------------- teams
def openers(view, season: int) -> pl.DataFrame:
    """The opening line of each team-game the view knows this season (I118): `line_total` (the
    total less 44), `line_margin` (the team's expected margin) and `has_line`."""
    o = view.table("team_game", seasons=[season]).filter(c("open_total").is_not_null())
    return o.select(
        "game_id", "team", line_total=c("open_total") - LINE_CENTER,
        line_margin=-c("open_spread"), has_line=pl.lit(1.0),
    )  # fmt: skip


def team_features(view, games: pl.DataFrame, keys: Sequence[str]) -> pl.DataFrame:
    """A row per team in `games`, with every column of `TEAM_NUMERIC` and `last_game_id`."""
    season = int(games["season"].max())
    rows = _opponents(view, games).select(
        *keys, "opponent", "games_left", home=c("home").cast(pl.Float64)
    )
    own, defense = team_context(view, season)
    rows = rows.join(own, on="team", how="left").join(
        defense.rename({"team": "opponent"}), on="opponent", how="left"
    )
    rows = rows.join(openers(view, season), on=["game_id", "team"], how="left")
    rows = rows.with_columns(
        *[c(f"{v}_s").fill_null(c(f"{v}_ls")) for v in TEAM_AVERAGED],
        tdoe_g=(c("td2").fill_null(0.0) - c("xtd2").fill_null(0.0)) / (c("games2").fill_null(0.0)
                                                                        + 8.0),
    )  # fmt: skip
    return rows.with_columns(
        c(x).cast(pl.Float64).fill_nan(None).fill_null(0.0) for x in TEAM_NUMERIC
    ).with_columns(c("last_game_id").fill_null(""))
