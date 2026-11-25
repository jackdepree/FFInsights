"""The on-field counts every role measure is read from (roles-archetypes brief; decision 0048).

Per player-team-season and half (`all`, `odd` weeks, `even` weeks), on the side he played:
- `n_<cell>`: his snaps in each of 32 kinds of play, and `tn_<cell>` his team's plays of that kind
  in the games he played. A cell is pass or run (by `qb_dropback`) × early or late down (3rd and
  4th) × personnel (11, 12, heavy, other; counted from who's on the offense) × red zone or not.
- Usage counts: snaps, pass and run snaps, targets, air yards, deep (20+), behind the line and
  middle targets, carries, outside carries, tackles, solo tackles, tackle yards, sacks and hits
  (`rush`), passes defensed (`pd`), and his targets' and touches' EPA.
- `group`: his most common depth-chart position's group for the team-season (WR; TE; RB with
  FB; DL; OLB; ILB with MLB; CB; S). Used to report and compare, and to shrink, never inside
  the space.
- `known_at`: when the season's participation was known (the latest on-field `known_at`).

Per player-team-game (`game_rows`): his snaps and his team's plays, for the substitutes test.
Regular seasons only. Retrospective: read at the end of time, one season at a time, through the
gateway (participation is post-season).
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource

c = pl.col
INPUTS = {"play": ("pbp",), "player_play": ("on_field",)}
GROUP = {"WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB", "DE": "DL", "DT": "DL", "NT": "DL",
         "OLB": "OLB", "ILB": "ILB", "MLB": "ILB", "CB": "CB", "FS": "S", "SS": "S"}  # fmt: skip
OFFENSE = ("WR", "TE", "RB")
DEFENSE = ("DL", "OLB", "ILB", "CB", "S")
SIDES = {"offense": OFFENSE, "defense": DEFENSE}
KINDS, DOWNS = ("pass", "run"), ("early", "late")
PERS, ZONES = ("11", "12", "heavy", "other"), ("rz", "of")
CELLS = [f"{k}_{d}_{p}_{z}" for k in KINDS for d in DOWNS for p in PERS for z in ZONES]
HALVES = ("all", "odd", "even")
KEYS = ["gsis_id", "team", "season", "side", "group"]
TACKLE = ["solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id",
          "assist_tackle_2_player_id", "assist_tackle_3_player_id", "assist_tackle_4_player_id",
          "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id"]  # fmt: skip
SOLO = ["solo_tackle_1_player_id", "solo_tackle_2_player_id"]
RUSH = ["sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id", "qb_hit_1_player_id",
        "qb_hit_2_player_id"]  # fmt: skip
PD = ["pass_defense_1_player_id", "pass_defense_2_player_id"]
PBP = ["game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "play_type",
       "qb_dropback", "down", "yardline_100", "air_yards", "pass_location", "run_location",
       "receiver_player_id", "rusher_player_id", "complete_pass", "yards_gained", "epa",
       "two_point_attempt", *TACKLE, *RUSH, *PD]  # fmt: skip
EVENTS = ("target", "carry", "tackle", "solo", "rush", "pd")


def _plays(pbp: pl.DataFrame, of: pl.DataFrame) -> pl.DataFrame:
    """Regular-season scrimmage plays with their cell and half; personnel from who's on offense."""
    p = pbp.filter(
        (c("season_type") == "REG")
        & c("play_type").is_in(["pass", "run"])
        & (c("two_point_attempt").fill_null(0) != 1)
        & c("down").is_not_null()
    )
    pers = (
        of.filter(c("side") == "offense")
        .group_by("game_id", "play_id")
        .agg(rb=c("position").is_in(["RB", "FB"]).sum(), te=(c("position") == "TE").sum())
        .with_columns(
            pers=pl.when((c("rb") == 1) & (c("te") == 1)).then(pl.lit("11"))
            .when((c("rb") == 1) & (c("te") == 2)).then(pl.lit("12"))
            .when(c("rb") + c("te") >= 3).then(pl.lit("heavy"))
            .otherwise(pl.lit("other"))
        )
        .select("game_id", "play_id", "pers")
    )  # fmt: skip
    zone = pl.when(c("yardline_100") <= 20).then(pl.lit("rz")).otherwise(pl.lit("of"))
    return (
        p.join(pers, on=["game_id", "play_id"], how="inner")
        .with_columns(
            kind=pl.when(c("qb_dropback") == 1).then(pl.lit("pass")).otherwise(pl.lit("run")),
            downg=pl.when(c("down") >= 3).then(pl.lit("late")).otherwise(pl.lit("early")),
            half=pl.when(c("week") % 2 == 1).then(pl.lit("odd")).otherwise(pl.lit("even")),
        )
        .with_columns(cell=pl.concat_str([c("kind"), c("downg"), c("pers"), zone], separator="_"))
    )


def _events(p: pl.DataFrame) -> pl.DataFrame:
    """One row per player-play with a 0/1 column per event he was named in."""
    named = [
        p.select("game_id", "play_id", gsis_id=c("receiver_player_id"), e=pl.lit("target")),
        p.filter(c("kind") == "run").select(
            "game_id", "play_id", gsis_id=c("rusher_player_id"), e=pl.lit("carry")
        ),
    ]
    for cols, e in ((TACKLE, "tackle"), (SOLO, "solo"), (RUSH, "rush"), (PD, "pd")):
        named += [p.select("game_id", "play_id", gsis_id=c(k), e=pl.lit(e)) for k in cols]
    ev = (
        pl.concat(named).drop_nulls().unique()
        .with_columns(v=pl.lit(1, pl.Int8))
        .pivot(on="e", index=["game_id", "play_id", "gsis_id"], values="v")
    )  # fmt: skip
    for k in EVENTS:
        if k not in ev.columns:
            ev = ev.with_columns(pl.lit(None, pl.Int8).alias(k))
    return ev


def _usage() -> dict[str, pl.Expr]:
    tg = c("target") == 1
    carry = c("carry") == 1
    touch = carry | (tg & (c("complete_pass") == 1))
    return dict(
        snaps=pl.len(), pass_snaps=(c("kind") == "pass").sum(),
        run_snaps=(c("kind") == "run").sum(),
        targets=tg.sum(), air=c("air_yards").filter(tg).sum(),
        air_n=c("air_yards").filter(tg).is_not_null().sum(),
        deep=(tg & (c("air_yards") >= 20)).sum(), behind=(tg & (c("air_yards") <= 0)).sum(),
        middle=(tg & (c("pass_location") == "middle")).sum(),
        loc_n=(tg & c("pass_location").is_not_null()).sum(),
        carries=carry.sum(), outside=(carry & c("run_location").is_in(["left", "right"])).sum(),
        run_loc_n=(carry & c("run_location").is_not_null()).sum(),
        tackles=c("tackle").sum(), solo=c("solo").sum(),
        tackle_yds=c("yards_gained").filter(c("tackle") == 1).sum(),
        rush=c("rush").sum(), pd=c("pd").sum(),
        epa_tgt=c("epa").filter(tg).sum(), touches=touch.sum(),
        epa_touch=c("epa").filter(touch).sum(),
    )  # fmt: skip


def season_counts(pbp: pl.DataFrame, on_field: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """One season's counts (per player-team-season and half) and game rows, from `play.pbp`
    (PBP columns) and `player_play.on_field` (game_id, play_id, side, team, gsis_id, position,
    known_at). Pure."""
    of = on_field.with_columns(c("play_id").cast(pl.Int64))
    pbp = pbp.with_columns(c("play_id").cast(pl.Int64))
    p = _plays(pbp, of)
    of = of.join(p.select("game_id", "play_id"), on=["game_id", "play_id"], how="semi")
    season = int(p["season"].max())
    known = of["known_at"].max()
    pp = (
        of.join(
            p.select(
                "game_id",
                "play_id",
                "week",
                "kind",
                "cell",
                "half",
                "air_yards",
                "pass_location",
                "run_location",
                "complete_pass",
                "yards_gained",
                "epa",
            ),
            on=["game_id", "play_id"],
        )  # fmt: skip
        .join(_events(p), on=["game_id", "play_id", "gsis_id"], how="left")
        .with_columns([c(k).fill_null(0) for k in EVENTS])
        .with_columns(group=c("position").replace_strict(GROUP, default=None))
    )
    grp = (pp.filter(c("group").is_not_null()).group_by("gsis_id", "team")
           .agg(group=c("group").mode().sort().first()))  # fmt: skip
    pp = pp.drop("group").join(grp, on=["gsis_id", "team"], how="inner")
    pp = pp.with_columns(season=pl.lit(season, pl.Int32))
    on_cells = pp.group_by([*KEYS, "half", "cell"]).agg(n=pl.len())
    team_side = pl.concat([
        p.select("game_id", "cell", "half", team=c("posteam"), side=pl.lit("offense")),
        p.select("game_id", "cell", "half", team=c("defteam"), side=pl.lit("defense")),
    ])  # fmt: skip
    tg_cells = team_side.group_by("game_id", "team", "side", "half", "cell").agg(tn=pl.len())
    his_games = pp.select(*KEYS, "game_id").unique()
    tcount = (his_games.join(tg_cells, on=["game_id", "team", "side"])
              .group_by([*KEYS, "half", "cell"]).agg(tn=c("tn").sum()))  # fmt: skip
    cells = tcount.join(on_cells, on=[*KEYS, "half", "cell"], how="left").with_columns(
        c("n").fill_null(0)
    )
    u = pp.group_by([*KEYS, "half"]).agg(**_usage())
    weeks = p.select("game_id", "week").unique()
    out = []
    for h in HALVES:
        cc = cells if h == "all" else cells.filter(c("half") == h)
        cc = cc.group_by([*KEYS, "cell"]).agg(c("n").sum(), c("tn").sum())
        wide = cc.pivot(on="cell", index=KEYS, values=["n", "tn"])
        if h == "all":
            uu = u.drop("half").group_by(KEYS).agg(pl.all().sum())
            hg = his_games
        else:
            uu = u.filter(c("half") == h).drop("half")
            hg = his_games.join(weeks, on="game_id").filter((c("week") % 2 == 1) == (h == "odd"))
        games = hg.group_by(KEYS).agg(games=c("game_id").n_unique())
        out.append(uu.join(wide, on=KEYS, how="inner").join(games, on=KEYS, how="left")
                   .with_columns(half=pl.lit(h)))  # fmt: skip
    counts = pl.concat(out, how="diagonal_relaxed")
    for cell in CELLS:
        for pre in ("n_", "tn_"):
            if pre + cell not in counts.columns:
                counts = counts.with_columns(pl.lit(0).alias(pre + cell))
    ncols = [f"{pre}{cell}" for cell in CELLS for pre in ("n_", "tn_")]
    counts = counts.with_columns([c(k).fill_null(0).cast(pl.Int64) for k in ncols]).with_columns(
        known_at=pl.lit(known)
    )
    tgame = team_side.group_by("game_id", "team", "side").agg(team_plays=pl.len())
    game_rows = (pp.group_by([*KEYS, "game_id", "week"]).agg(snaps=pl.len())
                 .join(tgame, on=["game_id", "team", "side"]))  # fmt: skip
    return counts, game_rows


def read_season(season: int, gw: Gateway | None = None) -> tuple[pl.DataFrame, pl.DataFrame]:
    """One season's play-by-play and on-field lists through the gateway (retrospective view)."""
    g = gw or Gateway(TableSource(seasons=[season]))
    view = g.view(END_OF_TIME, "retrospective", INPUTS)
    pbp = view.table("play", seasons=[season]).select(PBP)
    of = view.table("player_play", seasons=[season]).select(
        "game_id", "play_id", "side", "team", "gsis_id", "position", "known_at"
    )
    return pbp, of


def build(seasons: Sequence[int]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Counts and game rows for these seasons, one season at a time."""
    counts, games = [], []
    for s in seasons:
        cnt, g = season_counts(*read_season(s))
        counts.append(cnt)
        games.append(g)
    return pl.concat(counts, how="diagonal_relaxed"), pl.concat(games, how="diagonal_relaxed")
