"""The build's per-game counts (skill-over-expected brief; decision 0051, calls 1-6).

One long table, one row per player-game and trait: `gsis_id, game_id, season, week, team,
trait, num, den`. A trait's season rate is sum(num) / sum(den). Beside it, the main team and
main position per player-season (`pcf.validation.owners.main_team`), and the line's team-game
rows (`team, game_id, season, week, num, den` of pressure over expected, trait `line_poe`).

Read through the gateway, a retrospective view at the end of time, one season at a time
(participation and the on-field map are post-season), regular season only, 2016-2024; PFR's
charted measures from 2018. The 2025 vault is never read. Cached in `<interim>/skill_over_expected/`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource

c = pl.col
SEASONS = tuple(range(2016, 2025))  # participation's span; the 2025 vault closed (the CEO)
PFR_FIRST = 2018
INPUTS = {"play": ("pbp", "participation"), "player_play": ("on_field",),
          "player_game": ("roster", "pfr")}  # fmt: skip
TACKLE = ["solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id",
          "assist_tackle_2_player_id", "assist_tackle_3_player_id", "assist_tackle_4_player_id",
          "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id"]  # fmt: skip
PBP = ["game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "down",
       "ydstogo", "qb_dropback", "pass_attempt", "sack", "complete_pass", "cp", "air_yards",
       "rush_attempt", "qb_scramble", "yards_gained", "passer_player_id",
       "receiver_player_id", "rusher_player_id", *TACKLE]  # fmt: skip
OL = ["C", "LT", "RT", "LG", "RG", "G", "T"]
COLS = ["gsis_id", "game_id", "season", "week", "team", "trait", "num", "den"]


def cache_dir() -> Path:
    path = get_config().zone("interim") / "skill_over_expected"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _long(frame: pl.DataFrame, trait: str, num: pl.Expr, den: pl.Expr) -> pl.DataFrame:
    return frame.select("gsis_id", "game_id", "season", "week", "team",
                        trait=pl.lit(trait), num=num.cast(pl.Float64),
                        den=den.cast(pl.Float64))  # fmt: skip


def plays(pbp: pl.DataFrame, part: pl.DataFrame) -> pl.DataFrame:
    """Regular-season plays with participation's pressure (a sack counts as a pressure: before
    2023 the flag is empty on every sack, idea I90's trap), time to throw and rushers."""
    p = pbp.filter(c("season_type") == "REG").with_columns(c("play_id").cast(pl.Int64))
    pa = part.select("game_id", c("play_id").cast(pl.Int64), "was_pressure", "time_to_throw",
                     "number_of_pass_rushers")  # fmt: skip
    p = p.join(pa, on=["game_id", "play_id"], how="left")
    pres = pl.when(c("sack") == 1).then(1.0).otherwise(c("was_pressure").cast(pl.Float64))
    return p.with_columns(pres=pres)


def offense_counts(p: pl.DataFrame, pfr: pl.DataFrame) -> pl.DataFrame:
    """QB, receiver and runner traits per player-game (module docstring)."""
    out = []
    att = p.filter((c("pass_attempt") == 1) & (c("sack") == 0) & c("cp").is_not_null())
    wr = att.drop_nulls("receiver_player_id").group_by(
        gsis_id="receiver_player_id", game_id="game_id", season="season", week="week",
        team="posteam").agg(num=c("complete_pass").sum(), den=pl.len())  # fmt: skip
    out.append(_long(wr, "catch_rate", c("num"), c("den")))
    db = p.filter(c("qb_dropback") == 1).drop_nulls("passer_player_id")
    db = db.with_columns(
        air=pl.when((c("pass_attempt") == 1) & (c("sack") == 0)).then(c("air_yards")),
    )
    qb = db.group_by(gsis_id="passer_player_id", game_id="game_id", season="season",
                     week="week", team="posteam").agg(
        sacks=c("sack").sum(), drop=pl.len(), air=c("air").sum(), n_air=c("air").count(),
        ttt=c("time_to_throw").sum(), n_ttt=c("time_to_throw").count(),
        pres=c("pres").sum(), n_pres=c("pres").count(),
        sacks_flag=c("sack").filter(c("pres").is_not_null()).sum(),
    )  # fmt: skip
    out += [_long(qb, "qb_sack_rate", c("sacks"), c("drop")),
            _long(qb, "qb_depth", c("air"), c("n_air")),
            _long(qb, "qb_ttt", c("ttt"), c("n_ttt")),
            _long(qb, "qb_press_rate", c("pres"), c("n_pres")),
            _long(qb, "qb_sack_per_press", c("sacks_flag"), c("pres"))]  # fmt: skip
    ru = p.filter((c("rush_attempt") == 1) & (c("qb_scramble") == 0)).drop_nulls(
        "rusher_player_id"
    )
    ru = ru.with_columns(tacklers=pl.sum_horizontal([c(k).is_not_null().cast(pl.Int32)
                                                    for k in TACKLE]))  # fmt: skip
    ru = ru.with_columns(after=((c("yards_gained") > 0) & (c("tacklers") > 0)).cast(pl.Int32))
    rb = ru.group_by(gsis_id="rusher_player_id", game_id="game_id", season="season",
                     week="week", team="posteam").agg(
        after=c("after").sum(), multi=(c("after") * (c("tacklers") >= 2)).sum(),
        carries=pl.len())  # fmt: skip
    out.append(_long(rb, "rb_multi_after", c("multi"), c("after")))
    out.append(_long(rb, "rb_carries", c("carries"), pl.lit(1)))  # the carry floor's count
    pf = rb.join(pfr, on=["gsis_id", "game_id"], how="inner").filter(c("pcar") > 0)
    out += [_long(pf, "rb_yac", c("yac"), c("pcar")), _long(pf, "rb_bt", c("bt"), c("pcar"))]
    return pl.concat(out)


def defense_counts(p: pl.DataFrame, of: pl.DataFrame, pfr: pl.DataFrame) -> pl.DataFrame:
    """Pass-rush, role and coverage traits per player-game, on the dropbacks he was on the
    field for (the on-field map)."""
    drop = p.filter(c("qb_dropback") == 1).select("game_id", "play_id", "season", "week")
    on = (of.filter(c("side") == "defense").join(drop, on=["game_id", "play_id"])
          .group_by("gsis_id", "game_id", "season", "week", "team").agg(nd=pl.len()))  # fmt: skip
    d = on.join(pfr, on=["gsis_id", "game_id"], how="inner")
    d = d.with_columns(c("press", "sacks", "tgt", "cmp", "ints").fill_null(0))
    d = d.with_columns(air=(c("adot") * c("tgt")).fill_null(0),
                       nadot=pl.when(c("adot").is_not_null()).then(c("tgt")).otherwise(0))  # fmt: skip
    return pl.concat([
        _long(d, "press_rate", c("press"), c("nd")),
        _long(d, "def_sack_rate", c("sacks"), c("nd")),
        _long(d, "rush_share", c("press"), c("press") + c("tgt")),
        _long(d, "on_dropbacks", c("nd"), pl.lit(1)),  # the dropback floor's count
        _long(d, "catch_allowed", c("cmp"), c("tgt")),
        _long(d, "int_rate", c("ints"), c("tgt")),
        _long(d, "depth_against", c("air"), c("nadot")),
    ])  # fmt: skip


def lineman_counts(p: pl.DataFrame, of: pl.DataFrame) -> pl.DataFrame:
    """An offensive lineman's team's pressure and sacks on the dropbacks he was on the field for
    (the brief's "ignore" row: a lineman's on-field rate is his line's)."""
    d = p.filter((c("qb_dropback") == 1) & c("pres").is_not_null()).select(
        "game_id", "play_id", "season", "week", "pres", "sack")
    o = of.filter((c("side") == "offense") & c("position").is_in(OL)).select(
        "game_id", "play_id", "gsis_id", "team")
    g = o.join(d, on=["game_id", "play_id"]).group_by(
        "gsis_id", "game_id", "season", "week", "team").agg(
        pres=c("pres").sum(), sacks=c("sack").sum(), n=pl.len())
    return pl.concat([_long(g, "ol_press_rate", c("pres"), c("n")),
                      _long(g, "ol_sack_rate", c("sacks"), c("n"))])  # fmt: skip


def line_counts(p: pl.DataFrame) -> pl.DataFrame:
    """The line's pressure over expected per team-game: pressure (sacks counted) less a
    situation expectation (season x down x distance band x rushers, the exploration's), less
    the defense's own habit (its season's residual, leaving this play out)."""
    d = p.filter((c("qb_dropback") == 1) & c("pres").is_not_null())
    d = d.with_columns(
        dist=pl.when(c("ydstogo") <= 3).then(0).when(c("ydstogo") <= 7).then(1).otherwise(2),
        rush=c("number_of_pass_rushers").fill_null(-1).clip(-1, 7),
    )
    d = d.with_columns(res=c("pres") - c("pres").mean().over("season", "down", "dist", "rush"))
    n_def = pl.len().over("defteam", "season")
    d = d.with_columns(poe=c("res") - (c("res").sum().over("defteam", "season") - c("res"))
                       / (n_def - 1))  # fmt: skip
    return d.group_by(team="posteam", game_id="game_id", season="season", week="week").agg(
        num=c("poe").sum(), den=pl.len().cast(pl.Float64)
    ).with_columns(trait=pl.lit("line_poe"), gsis_id=c("team"))


def season_counts(season: int, gateway: Gateway | None = None):
    """One season's (player-game counts, line team-game counts, roster rows, on-field snap
    counts, the season's known-at: participation's latest)."""
    gw = gateway or Gateway(TableSource(seasons=[season]))
    v = gw.view(END_OF_TIME, "retrospective", INPUTS)
    pl_ = v.table("play", seasons=[season])
    p = plays(pl_.select(PBP), pl_.select("game_id", "play_id", "was_pressure",
                                         "time_to_throw", "number_of_pass_rushers"))  # fmt: skip
    pg = v.table("player_game", seasons=[season])
    of = v.table("player_play", seasons=[season]).with_columns(c("play_id").cast(pl.Int64))
    roster = pg.select("gsis_id", "game_id", "season", "team", "position")
    pfr = pg.select(
        "gsis_id", "game_id",
        press=c("pfr_def_def_pressures"), sacks=c("pfr_def_def_sacks"),
        tgt=c("pfr_def_def_targets"), cmp=c("pfr_def_def_completions_allowed"),
        ints=c("pfr_def_def_ints"), adot=c("pfr_def_def_adot"),
        pcar=c("pfr_rush_carries"), yac=c("pfr_rush_rushing_yards_after_contact"),
        bt=c("pfr_rush_rushing_broken_tackles"),
    )  # fmt: skip
    games = offense_counts(p, pfr.select("gsis_id", "game_id", "pcar", "yac", "bt")
                           if season >= PFR_FIRST else pfr.clear().select(
                               "gsis_id", "game_id", "pcar", "yac", "bt"))  # fmt: skip
    games = pl.concat([games, lineman_counts(p, of)])
    if season >= PFR_FIRST:
        games = pl.concat([games, defense_counts(p, of, pfr)])
    line = line_counts(p)
    snaps = (of.select("gsis_id", "season", "position").drop_nulls()
             .group_by("gsis_id", "season", "position").agg(n=pl.len()))  # fmt: skip
    known = pl.DataFrame({"season": [season], "known_at": [of["known_at"].max()]})
    return games, line, roster, snaps, known


def main_teams(roster: pl.DataFrame, snaps: pl.DataFrame) -> pl.DataFrame:
    """`pcf.validation.owners.main_team` on snap counts (`n` per player-season-position)
    instead of one row per snap: the same ties (alphabetical), far fewer rows."""
    def most(frame, by, value, name, weight=None):
        g = frame.group_by(*by, value).agg(n=pl.len() if weight is None else c(weight).sum())
        return (g.sort([*by, "n", value], descending=[False] * len(by) + [True, False])
                .group_by(by, maintain_order=True).first().select(*by, c(value).alias(name)))
    key = ["gsis_id", "season"]
    out = (most(roster, key, "team", "team")
           .join(most(roster, key, "position", "roster_pos"), on=key, how="left")
           .join(most(snaps, key, "position", "field_pos", "n"), on=key, how="left"))
    return out.select(pid="gsis_id", season="season", team="team",
                      position=pl.coalesce("field_pos", "roster_pos")).sort("pid", "season")


def build(seasons: Sequence[int] = SEASONS) -> dict[str, pl.DataFrame]:
    g, ln, ro, sn, kn = [], [], [], [], []
    for s in seasons:
        a, b, r, n, k = season_counts(s)
        kn.append(k)
        g.append(a)
        ln.append(b)
        ro.append(r)
        sn.append(n)
    roster, snaps = pl.concat(ro), pl.concat(sn)
    teams = main_teams(roster, snaps)
    games = pl.concat(g).filter(c("den") > 0).select(COLS)
    return {"games": games, "line": pl.concat(ln).select(COLS), "teams": teams,
            "known": pl.concat(kn)}


def load(refresh: bool = False) -> dict[str, pl.DataFrame]:
    """The cached counts (built on the first call)."""
    names = ("games", "line", "teams", "known")
    paths = {k: cache_dir() / f"{k}.parquet" for k in names}
    if refresh or not all(p.exists() for p in paths.values()):
        out = build()
        for k, f in out.items():
            f.write_parquet(paths[k])
    return {k: pl.read_parquet(p) for k, p in paths.items()}
