"""Roles exploration: build the player-season counts every test reads (pre-registered in EXPLORATION.md).

Writes <interim>/roles/:
- counts.parquet: per player-team-season and half ("all", "odd", "even" weeks): his snaps and his team's
  plays (in games he played) in each of 32 kinds of play (pass or run x early or late down x personnel
  11, 12, heavy, other x red zone or not), and his usage counts (targets, air yards, carries, tackles, ...).
- games.parquet: per player-team-game his snaps and his team's plays (for H101).
- measurables.parquet: height, weight and the 40 per player.
Regular seasons 2016-2024 (the 2025 vault untouched). Personnel is counted from who's on the field.

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import polars as pl

from pcf.config import get_config

c = pl.col
CFG = get_config()
T = CFG.zone("tables")
RAW = CFG.zone("raw") / "nflverse"
O = CFG.zone("interim") / "roles"
O.mkdir(parents=True, exist_ok=True)
SEASONS = range(2016, 2025)
GROUP = {"WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB", "DE": "DL", "DT": "DL", "NT": "DL", "OLB": "OLB",
         "ILB": "ILB", "MLB": "ILB", "CB": "CB", "FS": "S", "SS": "S"}

TACKLE = ["solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id", "assist_tackle_2_player_id",
          "assist_tackle_3_player_id", "assist_tackle_4_player_id", "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id"]
SOLO = ["solo_tackle_1_player_id", "solo_tackle_2_player_id"]
RUSH = ["sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id", "qb_hit_1_player_id", "qb_hit_2_player_id"]
PD = ["pass_defense_1_player_id", "pass_defense_2_player_id"]
PBP = ["game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "play_type", "qb_dropback", "down", "yardline_100",
       "air_yards", "pass_location", "run_location", "receiver_player_id", "rusher_player_id", "complete_pass", "yards_gained", "epa",
       "two_point_attempt", *TACKLE, *RUSH, *PD]

out_counts, out_games = [], []
for s in SEASONS:
    p = pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=PBP)
    p = p.filter((c("season_type") == "REG") & c("play_type").is_in(["pass", "run"]) & (c("two_point_attempt") != 1) & c("down").is_not_null())
    of = pl.read_parquet(T / "player_play" / "on_field" / f"season={s}" / "data.parquet", columns=["game_id", "play_id", "side", "team", "gsis_id", "position"])
    of = of.join(p.select("game_id", "play_id"), on=["game_id", "play_id"], how="semi")
    # personnel from who's on the offense
    pers = (of.filter(c("side") == "offense").group_by("game_id", "play_id")
            .agg(rb=c("position").is_in(["RB", "FB"]).sum(), te=(c("position") == "TE").sum())
            .with_columns(pers=pl.when((c("rb") == 1) & (c("te") == 1)).then(pl.lit("11"))
                          .when((c("rb") == 1) & (c("te") == 2)).then(pl.lit("12"))
                          .when(c("rb") + c("te") >= 3).then(pl.lit("heavy")).otherwise(pl.lit("other")))
            .select("game_id", "play_id", "pers"))
    p = p.join(pers, on=["game_id", "play_id"], how="inner").with_columns(
        kind=pl.when(c("qb_dropback") == 1).then(pl.lit("pass")).otherwise(pl.lit("run")),
        downg=pl.when(c("down") >= 3).then(pl.lit("late")).otherwise(pl.lit("early")),
        rz=(c("yardline_100") <= 20),
        half=pl.when(c("week") % 2 == 1).then(pl.lit("odd")).otherwise(pl.lit("even")),
    ).with_columns(cell=pl.concat_str([c("kind"), c("downg"), c("pers"), pl.when(c("rz")).then(pl.lit("rz")).otherwise(pl.lit("of"))], separator="_"))
    # events per player-play
    ev = pl.concat([
        p.select("game_id", "play_id", gsis_id=c("receiver_player_id"), e=pl.lit("target")),
        p.filter(c("kind") == "run").select("game_id", "play_id", gsis_id=c("rusher_player_id"), e=pl.lit("carry")),
        *[p.select("game_id", "play_id", gsis_id=c(k), e=pl.lit("tackle")) for k in TACKLE],
        *[p.select("game_id", "play_id", gsis_id=c(k), e=pl.lit("solo")) for k in SOLO],
        *[p.select("game_id", "play_id", gsis_id=c(k), e=pl.lit("rush")) for k in RUSH],
        *[p.select("game_id", "play_id", gsis_id=c(k), e=pl.lit("pd")) for k in PD],
    ]).drop_nulls().unique().with_columns(v=pl.lit(1, pl.Int8)).pivot(on="e", index=["game_id", "play_id", "gsis_id"], values="v")
    for k in ["target", "carry", "tackle", "solo", "rush", "pd"]:
        if k not in ev.columns:
            ev = ev.with_columns(pl.lit(None, pl.Int8).alias(k))
    pp = (of.join(p.select("game_id", "play_id", "week", "posteam", "kind", "cell", "half", "air_yards", "pass_location", "run_location",
                           "complete_pass", "yards_gained", "epa"), on=["game_id", "play_id"])
          .join(ev, on=["game_id", "play_id", "gsis_id"], how="left")
          .with_columns([c(k).fill_null(0) for k in ["target", "carry", "tackle", "solo", "rush", "pd"]])
          .with_columns(group=c("position").replace_strict(GROUP, default=None)))
    # the player's group for the season: his most common position's group
    grp = pp.filter(c("group").is_not_null()).group_by("gsis_id", "team").agg(group=c("group").mode().first())
    pp = pp.drop("group").join(grp, on=["gsis_id", "team"], how="inner").with_columns(season=pl.lit(s))
    tg = c("target") == 1
    usage = dict(
        snaps=pl.len(), pass_snaps=(c("kind") == "pass").sum(), run_snaps=(c("kind") == "run").sum(),
        targets=tg.sum(), air=c("air_yards").filter(tg).sum(), air_n=c("air_yards").filter(tg).is_not_null().sum(),
        deep=(tg & (c("air_yards") >= 20)).sum(), behind=(tg & (c("air_yards") <= 0)).sum(),
        middle=(tg & (c("pass_location") == "middle")).sum(), loc_n=(tg & c("pass_location").is_not_null()).sum(),
        catches=(tg & (c("complete_pass") == 1)).sum(), carries=c("carry").sum(),
        outside=((c("carry") == 1) & c("run_location").is_in(["left", "right"])).sum(), run_loc_n=((c("carry") == 1) & c("run_location").is_not_null()).sum(),
        tackles=c("tackle").sum(), solo=c("solo").sum(), tackle_yds=c("yards_gained").filter(c("tackle") == 1).sum(),
        rush=c("rush").sum(), pd=c("pd").sum(),
        epa_tgt=c("epa").filter(tg).sum(), epa_touch=c("epa").filter((c("carry") == 1) | (tg & (c("complete_pass") == 1))).sum(),
        touches=((c("carry") == 1) | (tg & (c("complete_pass") == 1))).sum(),
    )
    keys = ["gsis_id", "team", "season", "side", "group"]
    # his on-field counts by cell (wide)
    on_cells = pp.group_by([*keys, "half", "cell"]).agg(n=pl.len())
    # his team's plays by cell, in games he played
    team_side = pl.concat([p.select("game_id", "play_id", "cell", "half", team=c("posteam"), side=pl.lit("offense")),
                           p.select("game_id", "play_id", "cell", "half", team=c("defteam"), side=pl.lit("defense"))])
    tg_cells = team_side.group_by("game_id", "team", "side", "half", "cell").agg(tn=pl.len())
    his_games = pp.select(*keys, "game_id").unique()
    tcount = his_games.join(tg_cells, on=["game_id", "team", "side"]).group_by([*keys, "half", "cell"]).agg(tn=c("tn").sum())
    cells = tcount.join(on_cells, on=[*keys, "half", "cell"], how="left").with_columns(c("n").fill_null(0))
    u = pp.group_by([*keys, "half"]).agg(**usage)
    for h in ("all", "odd", "even"):
        cc = cells if h == "all" else cells.filter(c("half") == h)
        cc = cc.group_by([*keys, "cell"]).agg(c("n").sum(), c("tn").sum())
        wide = cc.pivot(on="cell", index=keys, values=["n", "tn"])
        uu = (u.drop("half").group_by(keys).agg(pl.all().sum()) if h == "all" else u.filter(c("half") == h).drop("half"))
        games = (his_games.join(p.select("game_id", "week").unique(), on="game_id").filter(pl.lit(True) if h == "all" else ((c("week") % 2 == 1) == (h == "odd")))
                 .group_by(keys).agg(games=c("game_id").n_unique()))
        out_counts.append(uu.join(wide, on=keys, how="inner").join(games, on=keys, how="left").with_columns(half=pl.lit(h)))
    # per game, for H101: his snaps and his team's plays
    tgame = team_side.group_by("game_id", "team", "side").agg(team_plays=pl.len())
    g = pp.group_by([*keys, "game_id", "week"]).agg(snaps=pl.len()).join(tgame, on=["game_id", "team", "side"])
    out_games.append(g)
    print(s, "player-plays", pp.height, "player-team-seasons", u.select(keys).unique().height, flush=True)

counts = pl.concat(out_counts, how="diagonal_relaxed")
ncols = [k for k in counts.columns if k.startswith("n_") or k.startswith("tn_")]
counts = counts.with_columns([c(k).fill_null(0) for k in ncols])
counts.write_parquet(O / "counts.parquet")
pl.concat(out_games).write_parquet(O / "games.parquet")

pl_ = pl.read_parquet(RAW / "players" / "players.parquet", columns=["gsis_id", "pfr_id", "height", "weight"])
cb = pl.read_parquet(RAW / "combine" / "combine.parquet", columns=["pfr_id", "forty", "ht", "wt"]).drop_nulls("pfr_id").unique("pfr_id")
m = pl_.join(cb, on="pfr_id", how="left").select("gsis_id", height=c("height").cast(pl.Float64), weight=c("weight").cast(pl.Float64), forty=c("forty"))
m.write_parquet(O / "measurables.parquet")
a = counts.filter(c("half") == "all")
print(f"\nplayer-team-seasons (all): {a.height:,}; with 200+ snaps: {a.filter(c('snaps') >= 200).height:,}")
print(a.filter(c("snaps") >= 200).group_by("group").len().sort("group"))
print("cells:", len([k for k in ncols if k.startswith("n_")]))
mm = m.join(a.filter(c("snaps") >= 200).select("gsis_id").unique(), on="gsis_id", how="semi")
print("measurables among them: height", f"{mm['height'].is_not_null().mean():.1%}", "weight", f"{mm['weight'].is_not_null().mean():.1%}", "forty", f"{mm['forty'].is_not_null().mean():.1%}")
