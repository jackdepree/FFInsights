"""Stabilization's inputs, read once through the gateway and cached (decision 0052, call 2).

An **in-season view** declares only live parts: `play.pbp`, `player_game` roster, snaps and pfr,
and `team_game` schedule. Participation (post-season) is read only by `exact()`, through a
retrospective view, for the stand-ins' closeness report; the forecasts never see it.

- `player_games()`: one row per player-game-measure: gsis_id, game_id, season, week, kickoff,
  team, pos, group, measure, num, den, known_at (when every source the row used was out; PFR's
  rows at PFR's lag). Regular season, two-point tries left out, 2006-2024.
- `team_games()`: the same per team-game-measure and side (off, def), with the opponent.
- `conditions()`: H113's teammates' conditions per player-game, as num and den.
- `exact()`: participation's routes, run snaps and defensive pass snaps per player-game
  (2016-2024), beside the stand-ins.

**The live stand-ins** (the brief's technical call): routes = offensive snap share times the
team's dropbacks that game; run snaps = the same times its designed runs; pass snaps on defense =
defensive snap share times the dropbacks it faced. Snap counts start in 2013.

The 2025 vault stays closed: nothing here reads a season after `LAST`.
"""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.stabilization import common as K

c = pl.col
SEASONS = tuple(range(K.FIRST, K.LAST + 1))
LIVE_INPUTS = {
    "play": ("pbp",),
    "player_game": ("roster", "snaps", "pfr"),
    "team_game": ("schedule",),
}
EXACT_INPUTS = {"player_play": ("on_field",), "play": ("pbp",)}
PBP_COLS = [
    "game_id",
    "play_id",
    "season",
    "week",
    "season_type",
    "posteam",
    "defteam",
    "qtr",
    "play_type",
    "two_point_attempt",
    "qb_dropback",
    "qb_scramble",
    "sack",
    "qb_hit",
    "pass_attempt",
    "complete_pass",
    "air_yards",
    "cp",
    "cpoe",
    "yards_after_catch",
    "xyac_mean_yardage",
    "receiving_yards",
    "yards_gained",
    "receiver_player_id",
    "passer_player_id",
    "rusher_player_id",
    "shotgun",
    "no_huddle",
    "success",
    "pass_oe",
    "qb_hit_1_player_id",
    "qb_hit_2_player_id",
    "sack_player_id",
    "half_sack_1_player_id",
    "half_sack_2_player_id",
    "known_at",
]
PFR_COLS = [
    "pfr_pass_times_pressured",
    "pfr_rush_carries",
    "pfr_rush_rushing_yards_after_contact",
    "pfr_rush_rushing_broken_tackles",
    "pfr_rec_receiving_broken_tackles",
    "pfr_def_def_pressures",
    "pfr_def_def_targets",
    "pfr_def_def_completions_allowed",
    "pfr_def_def_adot",
    "pfr_def_def_missed_tackles",
    "pfr_def_def_tackles_combined",
]


def gateway(seasons=SEASONS) -> Gateway:
    return Gateway(TableSource(seasons=list(seasons)))


def live_view(seasons):
    return gateway(seasons).view(END_OF_TIME, "in_season", LIVE_INPUTS)


def _cached(name: str, build: Callable[[], pl.DataFrame], refresh: bool = False) -> pl.DataFrame:
    path = K.cache_dir() / f"{name}.parquet"
    if refresh or not path.exists():
        df = build()
        df.write_parquet(path)
        return df
    return pl.read_parquet(path)


# ---------------------------------------------------------------- one season's pieces
def plays(pbp: pl.DataFrame) -> pl.DataFrame:
    have = [x for x in PBP_COLS if x in pbp.columns]
    p = pbp.select(have).filter(
        (c("season_type") == "REG")
        & (c("two_point_attempt").fill_null(0) == 0)
        & c("play_type").is_in(["pass", "run"])
        & c("posteam").is_not_null()
    )
    return p.with_columns(
        dropback=c("qb_dropback").fill_null(0) == 1,
        run=(c("play_type") == "run") & (c("qb_scramble").fill_null(0) == 0),
        target=(c("pass_attempt").fill_null(0) == 1)
        & (c("sack").fill_null(0) == 0)
        & c("receiver_player_id").is_not_null(),
    )


def _long(d: pl.DataFrame, measure: str, num: pl.Expr, den: pl.Expr) -> pl.DataFrame:
    return d.select(
        "gsis_id",
        "game_id",
        measure=pl.lit(measure),
        num=num.cast(pl.Float64),
        den=den.cast(pl.Float64),
        known_at="known_at",
    )


def team_plays(p: pl.DataFrame) -> pl.DataFrame:
    """Per team-game: its dropbacks and designed runs on offense, and the dropbacks it faced."""
    off = p.group_by("game_id", team="posteam").agg(t_db=c("dropback").sum(), t_run=c("run").sum())
    deff = p.group_by("game_id", team="defteam").agg(t_db_faced=c("dropback").sum())
    return off.join(deff, on=["game_id", "team"], how="full", coalesce=True).fill_null(0)


def snap_rows(pg: pl.DataFrame) -> pl.DataFrame:
    """Per player-game: offensive and defensive snap shares (0-1) and when they were out."""
    s = pg.select(
        "gsis_id",
        "game_id",
        "team",
        off=c("offense_pct").fill_null(0.0),
        dfn=c("defense_pct").fill_null(0.0),
        snaps_known=c("snaps_known_at"),
    )
    if s.height and max(s["off"].max() or 0, s["dfn"].max() or 0) > 1.5:  # PFR's percent
        s = s.with_columns(c("off") / 100, c("dfn") / 100)
    return s


def season_player_games(season: int) -> pl.DataFrame:
    v = live_view([season])
    p = plays(v.table("play", seasons=[season]))
    pg = v.table("player_game", seasons=[season])
    pk = p.group_by("game_id").agg(pbp_known=c("known_at").max())
    out = []

    # receivers, from play-by-play (every target)
    t = p.filter(c("target")).rename({"receiver_player_id": "gsis_id"})
    g = (
        t.group_by("gsis_id", "game_id")
        .agg(
            n_tgt=pl.len(),
            yds=c("receiving_yards").fill_null(0).sum(),
            ay=c("air_yards").sum(),
            n_ay=c("air_yards").is_not_null().sum(),
            coe=(c("complete_pass") - c("cp")).sum(),
            n_cp=c("cp").is_not_null().sum(),
            yoe=(c("yards_after_catch") - c("xyac_mean_yardage"))
            .filter(c("complete_pass") == 1)
            .sum(),
            n_yac=(
                c("xyac_mean_yardage").is_not_null()
                & c("yards_after_catch").is_not_null()
                & (c("complete_pass") == 1)
            ).sum(),
        )
        .join(pk, on="game_id")
        .rename({"pbp_known": "known_at"})
    )
    out += [
        _long(g, "adot", c("ay"), c("n_ay")),
        _long(g, "catch_oe", c("coe"), c("n_cp")),
        _long(g, "yac_oe", c("yoe"), c("n_yac")),
    ]

    # the stand-ins: snap share times the team's plays (snap counts from 2013)
    tp = team_plays(p)
    sn = snap_rows(pg).join(tp, on=["game_id", "team"], how="inner").join(pk, on="game_id")
    sn = sn.with_columns(
        routes=c("off") * c("t_db"),
        run_snaps=c("off") * c("t_run"),
        pass_snaps=c("dfn") * c("t_db_faced"),
        known_at=pl.max_horizontal("pbp_known", "snaps_known"),
    )
    car = (
        p.filter(c("run"))
        .group_by(c("rusher_player_id").alias("gsis_id"), "game_id")
        .agg(car=pl.len())
    )
    rg = sn.join(
        g.select("gsis_id", "game_id", "n_tgt", "yds"), on=["gsis_id", "game_id"], how="left"
    ).join(car, on=["gsis_id", "game_id"], how="left")
    rg = rg.with_columns(c("n_tgt", "yds", "car").fill_null(0))
    out += [
        _long(rg, "tprr", c("n_tgt"), c("routes")),
        _long(rg, "yprr", c("yds"), c("routes")),
        _long(rg, "car_per_run", c("car"), c("run_snaps")),
    ]
    hit_cols = (
        "qb_hit_1_player_id",
        "qb_hit_2_player_id",
        "sack_player_id",
        "half_sack_1_player_id",
        "half_sack_2_player_id",
    )
    hits = (
        pl.concat([p.filter(c("dropback")).select("game_id", gsis_id=c(k)) for k in hit_cols])
        .drop_nulls("gsis_id")
        .group_by("gsis_id", "game_id")
        .agg(hits=pl.len())
    )
    hg = sn.join(hits, on=["gsis_id", "game_id"], how="left").with_columns(c("hits").fill_null(0))
    out.append(_long(hg, "hits_per_snap", c("hits"), c("pass_snaps")))

    # QBs (every dropback: the passer, or the scrambler)
    db = (
        p.filter(c("dropback"))
        .with_columns(gsis_id=pl.coalesce("passer_player_id", "rusher_player_id"))
        .drop_nulls("gsis_id")
    )
    q = (
        db.group_by("gsis_id", "game_id")
        .agg(
            n=pl.len(),
            hs=((c("qb_hit").fill_null(0) == 1) | (c("sack").fill_null(0) == 1)).sum(),
            sk=c("sack").fill_null(0).sum(),
            sc=c("qb_scramble").fill_null(0).sum(),
            ay=c("air_yards").filter(c("pass_attempt") == 1).sum(),
            n_ay=(c("air_yards").is_not_null() & (c("pass_attempt") == 1)).sum(),
            cp=c("cpoe").sum() / 100,
            n_cp=c("cpoe").is_not_null().sum(),
        )
        .join(pk, on="game_id")
        .rename({"pbp_known": "known_at"})
    )
    out += [
        _long(q, "hitsack", c("hs"), c("n")),
        _long(q, "sack", c("sk"), c("n")),
        _long(q, "scramble", c("sc"), c("n")),
        _long(q, "qb_adot", c("ay"), c("n_ay")),
        _long(q, "cpoe", c("cp"), c("n_cp")),
    ]

    # PFR (2018+), at its own known_at (the Tuesday after the following week)
    if season >= 2018:
        f = pg.select("gsis_id", "game_id", *PFR_COLS, pfr_known="pfr_known_at").drop_nulls(
            "pfr_known"
        )
        f = f.join(q.select("gsis_id", "game_id", "n"), on=["gsis_id", "game_id"], how="left")
        f = f.join(
            g.select("gsis_id", "game_id", catches="n_yac"), on=["gsis_id", "game_id"], how="left"
        )
        f = f.join(
            sn.select("gsis_id", "game_id", "pass_snaps", "known_at"),
            on=["gsis_id", "game_id"],
            how="left",
        )
        f = f.with_columns(known_at=pl.max_horizontal("pfr_known", "known_at"))
        out.append(
            _long(
                f.drop_nulls(["pfr_pass_times_pressured", "n"]),
                "pressured",
                c("pfr_pass_times_pressured"),
                c("n"),
            )
        )
        b = f.drop_nulls("pfr_rush_carries")
        out += [
            _long(
                b,
                "yaco",
                c("pfr_rush_rushing_yards_after_contact").fill_null(0),
                c("pfr_rush_carries"),
            ),
            _long(
                b,
                "broken_per_touch",
                c("pfr_rush_rushing_broken_tackles").fill_null(0)
                + c("pfr_rec_receiving_broken_tackles").fill_null(0),
                c("pfr_rush_carries") + c("catches").fill_null(0),
            ),
        ]
        d = f.drop_nulls(["pfr_def_def_targets"])
        out += [
            _long(
                f.drop_nulls(["pfr_def_def_pressures", "pass_snaps"]),
                "press_per_snap",
                c("pfr_def_def_pressures"),
                c("pass_snaps"),
            ),
            _long(
                d.drop_nulls("pass_snaps"), "tgt_per_cov", c("pfr_def_def_targets"), c("pass_snaps")
            ),
            _long(
                d,
                "catch_allowed",
                c("pfr_def_def_completions_allowed").fill_null(0),
                c("pfr_def_def_targets"),
            ),
            _long(
                d.drop_nulls("pfr_def_def_adot"),
                "adot_allowed",
                c("pfr_def_def_adot") * c("pfr_def_def_targets"),
                c("pfr_def_def_targets"),
            ),
            _long(
                f.drop_nulls("pfr_def_def_tackles_combined"),
                "missed_tackle",
                c("pfr_def_def_missed_tackles").fill_null(0),
                c("pfr_def_def_tackles_combined").fill_null(0)
                + c("pfr_def_def_missed_tackles").fill_null(0),
            ),
        ]

    long = pl.concat(out).filter(c("den") > 0).drop_nulls(["num", "known_at"])
    ros = pg.select("gsis_id", "game_id", "season", "week", "team", "position").unique(
        ["gsis_id", "game_id"]
    )
    ros = ros.with_columns(
        group=c("position").replace_strict(K.GROUP, default=None),
        pos=c("position").replace_strict(K.POS, default=None),
    ).drop("position")
    long = long.join(ros, on=["gsis_id", "game_id"], how="inner")
    want = pl.DataFrame(
        {"measure": [m.name for m in K.MEASURES], "need": [m.group for m in K.MEASURES]}
    )
    long = (
        long.join(want, on="measure")
        .filter((c("group") == c("need")) | ((c("need") == "receiver") & (c("group") == "back")))
        .drop("need")
    )
    sched = v.table("team_game", seasons=[season]).select("game_id", "team", "kickoff")
    return long.join(sched, on=["game_id", "team"], how="left")


def player_games(refresh: bool = False) -> pl.DataFrame:
    def build():
        return pl.concat([season_player_games(s) for s in SEASONS], how="diagonal_relaxed")

    return _cached("player_games", build, refresh)


# ---------------------------------------------------------------- teams
def season_team_games(season: int) -> pl.DataFrame:
    v = live_view([season])
    p = plays(v.table("play", seasons=[season]))
    sched = v.table("team_game", seasons=[season]).select("game_id", "team", "opponent", "kickoff")
    rows = []
    for side, key in (("off", "posteam"), ("def", "defteam")):
        a = p.group_by(c(key).alias("team"), "season", "week", "game_id").agg(
            hitsack_n=((c("qb_hit").fill_null(0) == 1) | (c("sack").fill_null(0) == 1))
            .filter(c("dropback"))
            .sum(),
            hitsack_d=c("dropback").sum(),
            proe_n=c("pass_oe").sum() / 100,
            proe_d=c("pass_oe").is_not_null().sum(),
            shotgun_n=c("shotgun").fill_null(0).sum(),
            shotgun_d=pl.len(),
            no_huddle_n=c("no_huddle").fill_null(0).sum(),
            no_huddle_d=pl.len(),
            explosive_n=(
                ((c("pass_attempt") == 1) & (c("yards_gained") >= 20))
                | (c("run") & (c("yards_gained") >= 10))
            ).sum(),
            explosive_d=pl.len(),
            success_n=c("success").fill_null(0).sum(),
            success_d=pl.len(),
            adot_n=c("air_yards").filter(c("pass_attempt") == 1).sum(),
            adot_d=(c("air_yards").is_not_null() & (c("pass_attempt") == 1)).sum(),
            known_at=c("known_at").max(),
        )
        rows += [
            a.select(
                "team",
                "season",
                "week",
                "game_id",
                "known_at",
                side=pl.lit(side),
                measure=pl.lit(m),
                num=c(f"{m}_n").cast(pl.Float64),
                den=c(f"{m}_d").cast(pl.Float64),
            )
            for m in K.TEAM_MEASURES
        ]
    d = pl.concat(rows).filter(c("den") > 0)
    return d.join(sched, on=["game_id", "team"], how="left")


def team_games(refresh: bool = False) -> pl.DataFrame:
    def build():
        return pl.concat([season_team_games(s) for s in SEASONS], how="diagonal_relaxed")

    return _cached("team_games", build, refresh)


# ---------------------------------------------------------------- H113's conditions
def season_conditions(season: int) -> pl.DataFrame:
    """Per player-game, his teammates' conditions as (num, den): hs (team hit-or-sack allowed a
    dropback), pr (team pass rate over expected), oc (the passers' cpoe on targets to others), op
    (the rest of the defense's PFR pressures a dropback faced), ocat (the rest of the coverage's
    PFR catches allowed a target). PFR's from 2018."""
    v = live_view([season])
    p = plays(v.table("play", seasons=[season]))
    pg = v.table("player_game", seasons=[season])
    ros = pg.select("gsis_id", "game_id", "team").unique(["gsis_id", "game_id"])
    off = p.group_by("game_id", team="posteam").agg(
        hs_n=((c("qb_hit").fill_null(0) == 1) | (c("sack").fill_null(0) == 1))
        .filter(c("dropback"))
        .sum()
        .cast(pl.Float64),
        hs_d=c("dropback").sum().cast(pl.Float64),
        pr_n=(c("pass_oe").sum() / 100).cast(pl.Float64),
        pr_d=c("pass_oe").is_not_null().sum().cast(pl.Float64),
        tcp_n=(c("cpoe") / 100).filter(c("target")).sum().cast(pl.Float64),
        tcp_d=(c("target") & c("cpoe").is_not_null()).sum().cast(pl.Float64),
    )
    mine = (
        p.filter(c("target") & c("cpoe").is_not_null())
        .group_by(c("receiver_player_id").alias("gsis_id"), "game_id")
        .agg(my_n=(c("cpoe") / 100).sum(), my_d=pl.len().cast(pl.Float64))
    )
    faced = p.group_by("game_id", team="defteam").agg(db_d=c("dropback").sum().cast(pl.Float64))
    d = (
        ros.join(off, on=["game_id", "team"], how="left")
        .join(mine, on=["gsis_id", "game_id"], how="left")
        .with_columns(c("my_n", "my_d").fill_null(0.0))
    )
    d = d.with_columns(oc_n=c("tcp_n") - c("my_n"), oc_d=c("tcp_d") - c("my_d"))
    if season >= 2018:
        f = pg.select(
            "gsis_id",
            "game_id",
            "team",
            mp=c("pfr_def_def_pressures").fill_null(0).cast(pl.Float64),
            mt=c("pfr_def_def_targets").fill_null(0).cast(pl.Float64),
            mc=c("pfr_def_def_completions_allowed").fill_null(0).cast(pl.Float64),
        )
        tf = f.group_by("game_id", "team").agg(tp=c("mp").sum(), tt=c("mt").sum(), tc=c("mc").sum())
        d = (
            d.join(f.drop("team"), on=["gsis_id", "game_id"], how="left")
            .join(tf, on=["game_id", "team"], how="left")
            .join(faced, on=["game_id", "team"], how="left")
            .with_columns(c("mp", "mt", "mc").fill_null(0.0))
            .with_columns(
                op_n=c("tp") - c("mp"),
                op_d=c("db_d"),
                ocat_n=c("tc") - c("mc"),
                ocat_d=c("tt") - c("mt"),
            )
        )
    cols = [f"{k}_{s}" for k in K.COND for s in ("n", "d")]
    for col in cols:
        if col not in d.columns:
            d = d.with_columns(pl.lit(None, dtype=pl.Float64).alias(col))
    return d.select("gsis_id", "game_id", "team", *cols)


def conditions(refresh: bool = False) -> pl.DataFrame:
    def build():
        return pl.concat([season_conditions(s) for s in SEASONS], how="diagonal_relaxed")

    return _cached("conditions", build, refresh)


# ---------------------------------------------------------------- participation's exact counts
def season_exact(season: int) -> pl.DataFrame:
    """Participation's exact routes, run snaps and pass snaps on defense per player-game (the
    retrospective view: post-season), for the stand-ins' report only."""
    v = gateway([season]).view(END_OF_TIME, "retrospective", EXACT_INPUTS)
    p = plays(v.table("play", seasons=[season])).select("game_id", "play_id", "dropback", "run")
    of = v.table("player_play", seasons=[season]).select("game_id", "play_id", "side", "gsis_id")
    of = of.unique(["game_id", "play_id", "gsis_id"]).join(p, on=["game_id", "play_id"])
    o = (
        of.filter(c("side") == "offense")
        .group_by("gsis_id", "game_id")
        .agg(routes=c("dropback").sum().cast(pl.Float64), run_snaps=c("run").sum().cast(pl.Float64))
    )
    d = (
        of.filter(c("side") == "defense")
        .group_by("gsis_id", "game_id")
        .agg(pass_snaps=c("dropback").sum().cast(pl.Float64))
    )
    return o.join(d, on=["gsis_id", "game_id"], how="full", coalesce=True).with_columns(
        season=pl.lit(season, dtype=pl.Int32)
    )


def exact(refresh: bool = False) -> pl.DataFrame:
    def build():
        return pl.concat([season_exact(s) for s in range(2016, K.LAST + 1)], how="diagonal_relaxed")

    return _cached("exact", build, refresh)
