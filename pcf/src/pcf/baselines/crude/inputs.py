"""Inputs for the yardstick batch (`projects/crude-forecaster/YARDSTICK_BATCH.md`): each idea's
input on a board's rows, ready for `yardstick.score_input`.

Every input is made only from what was known at its row's moment (`as_of`, the Saturday run),
except the ones named `*_hindsight` or `*_kickoff`, which are ceilings and say so:
- `garbage_split` (I48): a player's past yards in garbage time (the tag table's rule);
- `availability` (I60): a forecast of the share of games a player plays, from his games so far,
  last season's and this week's injury report; `availability_hindsight`, the share he did play;
- `continuity` (I75): the share of a team's week-1 starters, or (hindsight) of its season's snaps,
  that went to players with no snap the season before (movers count as having played);
- `mover_priors` (I84): a mover's first-4-games prior from his own old share, or from his new
  team's slot;
- `lines` (I114): the spread and total, as the team's expected margin, the game total and the
  team's implied points; `kickoff` (the schedule's near-closing line, a ceiling) or `open`
  (ESPN's opening lines, 2023 on in our data: known at the run).

They read the tables through the gateway at the end of time and apply each row's moment
themselves (a row's moment differs within one call), so each builder filters by `known_at`.
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway

c = pl.col
OFFENSE = ("QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT")
DEFENSE = ("DE", "DT", "NT", "OLB", "ILB", "MLB", "CB", "SS", "FS")
SKILL = ("QB", "RB", "WR", "TE")
# I60's forecast of games played: this season's rate shrunk toward last season's by this many
# games, and a newcomer's last-season rate (no NFL games last season).
SHRINK_GAMES = 4.0
NEWCOMER_RATE = 0.8
FIRST_GAMES = 4  # I84: a mover's first games with his new team
YARDS = {
    "passing": ("passer_player_id", "passing_yards"),
    "rushing": ("rusher_player_id", "rushing_yards"),
    "receiving": ("receiver_player_id", "receiving_yards"),
    "qb_rushing": ("rusher_player_id", "rushing_yards"),
}


def _view(gateway: Gateway | None, inputs: dict) -> object:
    return (gateway or Gateway()).view(END_OF_TIME, "retrospective", inputs)


def _seasons(rows: pl.DataFrame) -> list[int]:
    s = rows["season"].unique().to_list()
    return sorted({*s, *(x - 1 for x in s)})


# ---------------------------------------------------------------- the shared averaging
def prior_average(
    rows: pl.DataFrame, games: pl.DataFrame, unit: str, cols: Sequence[str], prefix: str = ""
) -> pl.DataFrame:
    """Per row (unit, season, as_of): each column's per-game average over the unit's games of
    this season known by the row's moment (`<prefix><col>_s`), and over last season
    (`_ls`). As the crude inputs do, `_s` falls back to `_ls` before his first game, and a unit
    with no games gets 0. `games`: unit, season, known_at and the columns, one row per game."""
    r = rows.select(unit, "season", "as_of").unique()
    this = (
        r.join(games, on=[unit, "season"], how="inner")
        .filter(c("known_at") <= c("as_of"))
        .group_by(unit, "season", "as_of")
        .agg(c(col).mean().alias(f"{prefix}{col}_s") for col in cols)
    )
    last = games.group_by(unit, "season").agg(
        c(col).mean().alias(f"{prefix}{col}_ls") for col in cols
    )
    last = last.with_columns(c("season") + 1)
    out = r.join(this, on=[unit, "season", "as_of"], how="left").join(
        last, on=[unit, "season"], how="left"
    )
    out = out.with_columns(
        *[c(f"{prefix}{col}_ls").fill_null(0.0) for col in cols],
    ).with_columns(c(f"{prefix}{col}_s").fill_null(c(f"{prefix}{col}_ls")) for col in cols)
    return rows.join(out, on=[unit, "season", "as_of"], how="left")


# ---------------------------------------------------------------- I48: garbage time
def player_game_garbage(
    target: str, seasons: Sequence[int], gateway: Gateway | None = None
) -> pl.DataFrame:
    """Each player-game's yards for a target split into garbage time (the tag table's rule:
    4th quarter with a 17+ point margin, or 3rd with 28+) and the rest, regular season, from the
    play-by-play. Columns gsis_id, game_id, season, known_at, gt (garbage yards), rest."""
    who, yards = YARDS[target]
    view = _view(gateway, {"play": ("pbp", "tags")})
    out = []
    for s in seasons:  # a season at a time (play-by-play is large)
        p = view.table("play", seasons=[s])
        known = "pbp_known_at" if "pbp_known_at" in p.columns else "known_at"
        p = p.filter((c("season_type") == "REG") & c(who).is_not_null()).select(
            "game_id", "season", gsis_id=who, y=c(yards).fill_null(0).cast(pl.Float64),
            garbage=c("tag_garbage_time").fill_null(False), known_at=c(known),
        )  # fmt: skip
        out.append(
            p.group_by("gsis_id", "game_id", "season").agg(
                gt=c("y").filter(c("garbage")).sum(),
                rest=c("y").filter(~c("garbage")).sum(),
                known_at=c("known_at").max(),
            )
        )
    return pl.concat(out)


def garbage_split(
    rows: pl.DataFrame, target: str, gateway: Gateway | None = None, garbage=None
) -> pl.DataFrame:
    """I48's input on a player board's rows (gsis_id, game_id, season, as_of): his garbage-time
    yards per game this season so far and last season (`gt_y_s`, `gt_y_ls`). Beside the board's
    pooled averages, the lasso's weight on them is the garbage yard's weight minus the rest's."""
    garbage = garbage if garbage is not None else player_game_garbage(target, _seasons(rows),
                                                                       gateway)  # fmt: skip
    out = prior_average(rows, garbage.rename({"gt": "y"}), "gsis_id", ["y"], prefix="gt_")
    return out.select("gsis_id", "game_id", "gt_y_s", "gt_y_ls")


# ---------------------------------------------------------------- I60: availability
def _played(gateway: Gateway | None, seasons: Sequence[int]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Player-games of the skill positions (roster rows, regular season) with whether he took an
    offensive snap, and the team's regular-season schedule with each game's week index."""
    view = _view(gateway, {"player_game": ("roster", "snaps", "injury"),
                           "team_game": ("schedule",)})  # fmt: skip
    pg = view.table("player_game", seasons=seasons)
    tg = view.table("team_game", seasons=seasons).filter(c("game_type") == "REG")
    sched = tg.select("game_id", "team", "season", "week", "kickoff").sort("team", "season", "week")
    sched = sched.with_columns(i=pl.int_range(pl.len()).over("team", "season"),
                               n=pl.len().over("team", "season"))  # fmt: skip
    pg = pg.filter(c("position").is_in(list(SKILL))).join(
        sched.select("game_id", "team"), on=["game_id", "team"], how="inner"
    )
    return pg, sched


def availability(
    rows: pl.DataFrame, gateway: Gateway | None = None, hindsight: bool = False
) -> pl.DataFrame:
    """I60's input on a player board's rows (gsis_id, game_id, team, season, week, as_of, and
    the board's `y_s`): a crude forecast of the share of his team's games he plays,
    `av_rate` = (games played this season so far + 4 × last season's rate) / (team games so far
    + 4) (a newcomer's last-season rate is 0.8); `av_y` = y_s × av_rate (yards per game played
    times games played); this week's final injury report (`av_q` questionable or doubtful,
    `av_dnp` limited or no practice); `av_out_s`, the share of this season's weeks so far he was
    listed out or doubtful. Known at the Saturday run: the report is final by then.

    `hindsight`: instead, the share of the window's games (this one to the season's end) he did
    play (`av_true`, `av_true_y`): a ceiling, never known at the run."""
    seasons = _seasons(rows)
    pg, sched = _played(gateway, seasons)
    took = pg.select(
        "gsis_id", "game_id", "season", "week", "team",
        snap=(c("offense_snaps").fill_null(0) > 0).cast(pl.Float64),
        out=c("report_status").is_in(["Out", "Doubtful"]).fill_null(False).cast(pl.Float64),
    )  # fmt: skip
    keys = ["gsis_id", "game_id"]
    if hindsight:
        r = rows.select(*keys, "team", "season", "week", "y_s").join(
            sched.select("game_id", "team", "i", "n"), on=["game_id", "team"], how="left"
        )
        weekly = took.group_by("gsis_id", "season", "week").agg(c("snap").max())
        windows = r.join(sched.select("team", "season", w_week="week", w_i="i"),
                         on=["team", "season"]).filter(c("w_i") >= c("i"))  # fmt: skip
        played = (
            windows.join(weekly.rename({"week": "w_week"}), on=["gsis_id", "season", "w_week"],
                         how="left")
            .group_by(keys)
            .agg(av_true=c("snap").fill_null(0).mean())
        )  # fmt: skip
        return r.join(played, on=keys, how="left").select(
            *keys, "av_true", av_true_y=c("y_s") * c("av_true")
        )
    r = rows.select(*keys, "team", "season", "week", "as_of", "y_s")
    # this season: his games played (any team) and the team's games, before this week
    so_far = (
        r.join(
            took.select("gsis_id", "season", w="week", snap="snap", out="out"),
            on=["gsis_id", "season"],
            how="left",
        )  # fmt: skip
        .filter(c("w").is_null() | (c("w") < c("week")))
        .group_by(keys)
        .agg(played_s=c("snap").fill_null(0).sum(), out_s=c("out").fill_null(0).sum())
    )
    team_s = r.join(sched.select("team", "season", w="week"), on=["team", "season"]).filter(
        c("w") < c("week")
    ).group_by(keys).agg(n_team_s=pl.len())  # fmt: skip
    last = (
        took.group_by("gsis_id", "season")
        .agg(played_ls=c("snap").sum())
        .with_columns(c("season") + 1)
    )
    n_last = sched.group_by("team", "season").agg(n_ls=pl.len()).group_by("season").agg(
        c("n_ls").max()
    ).with_columns(c("season") + 1)  # fmt: skip
    view = _view(gateway, {"player_game": ("injury",)})
    inj = view.table("player_game", seasons=seasons).select(
        *keys, inj_known="injury_known_at", status="report_status",
        practice="practice_status",
    )  # fmt: skip
    out = (
        r.join(so_far, on=keys, how="left")
        .join(team_s, on=keys, how="left")
        .join(last, on=["gsis_id", "season"], how="left")
        .join(n_last, on="season", how="left")
        .join(inj, on=keys, how="left")
        .with_columns(c("played_s", "out_s", "n_team_s").fill_null(0))
        .with_columns(
            rate_ls=pl.when(c("played_ls").fill_null(0) > 0)
            .then(c("played_ls") / c("n_ls"))
            .otherwise(NEWCOMER_RATE),
            known=c("inj_known").is_not_null() & (c("inj_known") <= c("as_of")),
        )
        .with_columns(
            av_rate=(c("played_s") + SHRINK_GAMES * c("rate_ls")) / (c("n_team_s") + SHRINK_GAMES),
            av_q=(c("known") & c("status").is_in(["Questionable", "Doubtful"])).cast(pl.Float64),
            av_dnp=(c("known") & c("practice").str.contains("(?i)did not|limited"))
            .fill_null(False)
            .cast(pl.Float64),
            av_out_s=pl.when(c("n_team_s") > 0).then(c("out_s") / c("n_team_s")).otherwise(0.0),
        )
        .with_columns(av_y=c("y_s") * c("av_rate"))
    )
    return out.unique(keys).select(*keys, "av_rate", "av_y", "av_q", "av_dnp", "av_out_s")


def team_availability(
    team_rows: pl.DataFrame, gateway: Gateway | None = None, hindsight: bool = False
) -> pl.DataFrame:
    """I60 for a team board's rows (game_id, team, season, week, as_of): the week's depth-chart
    starting QB's `av_rate` (`tav_qb`) and the mean over its starting QB, RBs, WRs and TEs
    (`tav_skill`), each from `availability` (a starter's own yards average isn't needed here).
    `hindsight`: the same with the share they did play (`tav_qb_true`, `tav_skill_true`)."""
    seasons = _seasons(team_rows)
    view = _view(gateway, {"player_game": ("roster", "depth")})
    pg = view.table("player_game", seasons=seasons)
    starters = pg.filter(
        (c("depth") == 1) & c("depth_position").is_in(list(SKILL))
    ).join(team_rows.select("game_id", "team", "season", "week", "as_of"),
           on=["game_id", "team", "season", "week"], how="inner")  # fmt: skip
    starters = starters.select("gsis_id", "game_id", "team", "season", "week", "as_of",
                               "depth_position", y_s=pl.lit(0.0))  # fmt: skip
    a = availability(starters, gateway, hindsight)
    col = "av_true" if hindsight else "av_rate"
    s = starters.join(a, on=["gsis_id", "game_id"], how="left")
    suffix = "_true" if hindsight else ""
    return s.group_by("game_id", "team").agg(
        c(col).filter(c("depth_position") == "QB").mean().alias(f"tav_qb{suffix}"),
        c(col).mean().alias(f"tav_skill{suffix}"),
    )


# ---------------------------------------------------------------- I75: roster continuity
def continuity(gateway: Gateway | None = None, seasons: Sequence[int] = range(2014, 2025)
               ) -> pl.DataFrame:  # fmt: skip
    """I75 per team-season: the share of its week-1 depth-chart starters (offense, defense) who
    took no NFL snap the season before (`off_new_pre`, `def_new_pre`: known at week 1's start);
    and, in hindsight, the share of its season's offensive or defensive snaps that went to such
    players (`off_new_hindsight`, `def_new_hindsight`: a ceiling). A player who changed teams
    counts as having played. Columns team, season and those four."""
    seasons = list(seasons)
    every = sorted({*seasons, *(s - 1 for s in seasons)})
    view = _view(gateway, {"player_game": ("roster", "snaps", "depth"),
                           "team_game": ("schedule",)})  # fmt: skip
    pg = view.table("player_game", seasons=every)
    tg = view.table("team_game", seasons=every).filter(c("game_type") == "REG")
    pg = pg.join(tg.select("game_id", "team"), on=["game_id", "team"], how="inner")
    snaps = pg.group_by("gsis_id", "season").agg(
        snaps=(c("offense_snaps").fill_null(0) + c("defense_snaps").fill_null(0)).sum()
    )
    prev = snaps.filter(c("snaps") > 0).select("gsis_id", season=c("season") + 1, played=pl.lit(1))
    first = tg.group_by("team", "season").agg(week1=c("week").min())
    d = pg.join(first, on=["team", "season"]).filter((c("week") == c("week1")) & (c("depth") == 1))
    d = d.select("gsis_id", "team", "season", "depth_position").unique(
        ["gsis_id", "team", "season"]
    )
    d = d.join(prev, on=["gsis_id", "season"], how="left").with_columns(
        new=c("played").is_null().cast(pl.Float64)
    )
    pre = d.group_by("team", "season").agg(
        off_new_pre=c("new").filter(c("depth_position").is_in(list(OFFENSE))).mean(),
        def_new_pre=c("new").filter(c("depth_position").is_in(list(DEFENSE))).mean(),
    )
    h = pg.join(prev, on=["gsis_id", "season"], how="left").with_columns(new=c("played").is_null())
    hind = h.group_by("team", "season").agg(
        off_new_hindsight=c("offense_snaps").fill_null(0).filter(c("new")).sum()
        / c("offense_snaps").fill_null(0).sum(),
        def_new_hindsight=c("defense_snaps").fill_null(0).filter(c("new")).sum()
        / c("defense_snaps").fill_null(0).sum(),
    )
    return pre.join(hind, on=["team", "season"], how="full", coalesce=True).filter(
        c("season").is_in(seasons)
    )


def team_continuity(team_rows: pl.DataFrame, cont: pl.DataFrame, gateway=None) -> pl.DataFrame:
    """I75 on a team board's rows (game_id, team, season): the offense's own continuity
    (`off_new_*`) and the opposing defense's (`def_new_*`), whose yards allowed this row is."""
    view = _view(gateway, {"team_game": ("schedule",)})
    opp = view.table("team_game", seasons=_seasons(team_rows)).select("game_id", "team", "opponent")
    r = team_rows.select("game_id", "team", "season").join(opp, on=["game_id", "team"], how="left")
    off = cont.select("team", "season", "off_new_pre", "off_new_hindsight")
    dfn = cont.select(opponent="team", season="season", def_new_pre="def_new_pre",
                      def_new_hindsight="def_new_hindsight")  # fmt: skip
    return (
        r.join(off, on=["team", "season"], how="left")
        .join(dfn, on=["opponent", "season"], how="left")
        .drop("opponent", "season")
    )


# ---------------------------------------------------------------- I84: movers' priors
def mover_priors(rows: pl.DataFrame, target: str, gateway: Gateway | None = None) -> pl.DataFrame:
    """I84 on a player board's rows (gsis_id, game_id, team, season, position, n_games, ypa_ls):
    for a mover (his team isn't the one he played most for last season) in his first 4 games
    this season, two priors for his volume per game, each in yards (× his own last-season yards
    per target or carry, `ypa_ls`), and 0 for everyone else:
    - `mv_own_y`: his own last-season share of his old team's volume (targets of pass attempts;
      carries of the team's carries) × his new team's volume per game last season;
    - `mv_slot_y`: the share his new team gave last season to the player at his slot: its k-th
      biggest share at his position, k his rank on the new team's depth chart going into the
      game (depth, then label), × the same volume.
    `mv_flag` marks the rows. Receiving: WRs and TEs; rushing: RBs."""
    vol, team_vol, positions = {
        "receiving": ("targets", "attempts", ("WR", "TE")),
        "rushing": ("carries", "carries", ("RB",)),
    }[target]
    seasons = _seasons(rows)
    view = _view(gateway, {"player_game": ("roster", "stats", "depth"),
                           "team_game": ("schedule", "stats")})  # fmt: skip
    pg = view.table("player_game", seasons=seasons)
    tg = view.table("team_game", seasons=seasons).filter(c("game_type") == "REG")
    pg = pg.join(tg.select("game_id", "team"), on=["game_id", "team"], how="inner")
    played = pg.filter(c("stats_known_at").is_not_null())
    # last season: each player's main team and his share of its volume in the games he played
    by_team = played.group_by("gsis_id", "season", "team", "position").agg(
        g=pl.len(), v=c(vol).fill_null(0).sum(), games=c("game_id")
    )
    tv = tg.select("game_id", "team", tv=c(team_vol).fill_null(0))
    share = by_team.explode("games").rename({"games": "game_id"}).join(
        tv, on=["game_id", "team"], how="left"
    ).group_by("gsis_id", "season", "team", "position").agg(
        g=c("g").first(), v=c("v").first(), tv=c("tv").sum()
    ).with_columns(share=pl.when(c("tv") > 0).then(c("v") / c("tv")).otherwise(0.0))  # fmt: skip
    main = share.sort("g", "v", descending=True).unique(["gsis_id", "season"], keep="first")
    main = main.select("gsis_id", season=c("season") + 1, old_team="team", own_share="share")
    team_pg = (
        tg.group_by("team", "season").agg(vol_pg=c(team_vol).mean()).with_columns(c("season") + 1)
    )
    # the new team's slots last season: its players' season shares at a position, biggest first
    season_share = (
        played.group_by("gsis_id", "season", "team", "position")
        .agg(v=c(vol).fill_null(0).sum())
        .join(tg.group_by("team", "season").agg(tv=c(team_vol).sum()), on=["team", "season"])
    )
    slots = season_share.with_columns(share=c("v") / c("tv")).sort("share", descending=True)
    slots = slots.with_columns(k=pl.int_range(1, pl.len() + 1).over("team", "season", "position"))
    slots = slots.select("team", "position", "k", "share", season=c("season") + 1)
    # his rank on the new team's depth chart going into the game
    depth = pg.filter(c("depth").is_not_null() & c("position").is_in(list(positions))).select(
        "gsis_id", "game_id", "team", "position", "depth",
        label=c("position_label").str.extract(r"(\d+)$").cast(pl.Int32, strict=False).fill_null(9),
    ).sort("depth", "label").with_columns(
        k=pl.int_range(1, pl.len() + 1).over("game_id", "team", "position")
    ).select("gsis_id", "game_id", "k")  # fmt: skip
    r = rows.select("gsis_id", "game_id", "team", "season", "position", "n_games", "ypa_ls")
    r = r.join(main, on=["gsis_id", "season"], how="left").with_columns(
        mv_flag=(
            c("old_team").is_not_null() & (c("old_team") != c("team"))
            & (c("n_games") < FIRST_GAMES) & c("position").is_in(list(positions))
        ).cast(pl.Float64)
    )  # fmt: skip
    r = r.join(team_pg, on=["team", "season"], how="left").join(
        depth, on=["gsis_id", "game_id"], how="left"
    )
    r = r.join(slots, on=["team", "season", "position", "k"], how="left", suffix="_slot")
    ypa = c("ypa_ls").fill_null(0)
    on = c("mv_flag") > 0
    return r.select(
        "gsis_id", "game_id", "mv_flag",
        mv_own_y=pl.when(on).then(c("own_share") * c("vol_pg") * ypa).otherwise(0.0).fill_null(0.0),
        mv_slot_y=pl.when(on).then(c("share").fill_null(0.0) * c("vol_pg") * ypa).otherwise(0.0)
        .fill_null(0.0),
    )  # fmt: skip


# ---------------------------------------------------------------- I114: the lines
def espn_openers(path=None) -> pl.DataFrame:
    """ESPN's opening lines per regular-season game (parsed by the odds collection, already in
    our data): the median over books (live-odds feeds left out) of the home spread and the total.
    Columns game_id, open_home_spread (betting sign: negative when the home team is favored),
    open_total. 2022 has no opening values in ESPN's history; 2023 has them for most games."""
    path = path or get_config().zone("interim") / "espn_odds" / "game_lines.parquet"
    g = pl.read_parquet(path).filter(
        (c("seasontype") == 2) & ~c("provider_name").str.contains("(?i)live")
    )
    return (
        g.group_by("game_id")
        .agg(open_home_spread=c("open_home_spread").median(), open_total=c("open_total").median())
        .filter(c("open_home_spread").is_not_null() & c("open_total").is_not_null())
    )


def lines(rows: pl.DataFrame, kind: str = "kickoff", gateway: Gateway | None = None,
          openers: pl.DataFrame | None = None) -> pl.DataFrame:  # fmt: skip
    """I114 on a board's rows (game_id, team, and any other keys): the team's expected margin
    (`ln_margin`), the game total (`ln_total`) and its implied points (`ln_implied` = total / 2
    + margin / 2).

    - `kind="kickoff"`: the schedule's line, which sits near the close and is known at kickoff
      (DATA_SOURCES): **a ceiling, never known at the Saturday run**.
    - `kind="open"`: ESPN's opening line where we have it (known at the run: openers are posted
      early in the week), and the kickoff line elsewhere. Only rows with an opener are honest;
      the others can train the lasso (their lines were all known before any later season's fit)
      and must be left out of the scoring (`opener_rows`)."""
    view = _view(gateway, {"team_game": ("schedule", "pregame")})
    tg = view.table("team_game", seasons=_seasons(rows)).select(
        "game_id", "team", "home", spread="spread", total="total_line"
    )
    if kind == "open":
        op = openers if openers is not None else espn_openers()
        tg = tg.join(op, on="game_id", how="left").with_columns(
            spread=pl.when(c("open_home_spread").is_not_null())
            .then(pl.when(c("home")).then(c("open_home_spread")).otherwise(-c("open_home_spread")))
            .otherwise(c("spread")),
            total=pl.coalesce(c("open_total"), c("total")),
        )
    elif kind != "kickoff":
        raise ValueError(f"lines: kind {kind!r} is 'kickoff' or 'open'")
    tg = tg.select("game_id", "team", ln_margin=-c("spread"), ln_total=c("total")).with_columns(
        ln_implied=c("ln_total") / 2 + c("ln_margin") / 2
    )
    out = rows.select(*[k for k in ("gsis_id", "game_id") if k in rows.columns], "team").join(
        tg, on=["game_id", "team"], how="left"
    )
    return out.drop("team") if "gsis_id" in rows.columns else out  # a team board's keys keep it


def opener_rows(rows: pl.DataFrame, openers: pl.DataFrame | None = None) -> pl.DataFrame:
    """The board rows (keys) whose game has an ESPN opener: the only rows `lines(kind="open")`
    is honest on."""
    op = openers if openers is not None else espn_openers()
    keys = [k for k in rows.columns if k in ("gsis_id", "game_id", "team")]
    return rows.select(*keys).join(op.select("game_id"), on="game_id", how="semi")


__all__ = [
    "availability", "continuity", "espn_openers", "garbage_split", "lines", "mover_priors",
    "opener_rows", "player_game_garbage", "prior_average", "team_availability",
    "team_continuity",
]  # fmt: skip
