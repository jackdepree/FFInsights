"""Shared table code for the vacated-opportunity exploration (EXPLORATION.md, "The terms"). Explore code only.

build() writes <interim>/vacated/:
  pg.parquet    one row per player-team-game he played (snaps > 0) in the five groups, regular season 2016-2024:
                share (snap share 0-1), targets, carries, the team's targets and carries that game, tgt_share, car_share
  games.parquet one row per team-game (regular season): off_epa, def_epa, pressure allowed and made (counts and rate)
  ps.parquet    one row per player-team-season: games, share (mean over his games), tgt/car share, first/last week,
                rank in group by snaps, top flag, age at season start
"""

# ruff: noqa: E501
from __future__ import annotations

import polars as pl

from pcf.config import get_config

c = pl.col
CFG = get_config()
T = CFG.zone("tables")
O = CFG.zone("interim") / "vacated"
SEASONS = range(2016, 2025)
GROUP = {"WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB", "OL": "OL", "T": "OL", "G": "OL", "C": "OL", "DL": "DL"}
TOPK = {"WR": 2, "TE": 1, "RB": 1, "OL": 5, "DL": 3}
GROUPS = list(TOPK)
OFFENSE = {"WR", "TE", "RB", "OL"}
SKILL = ["WR", "TE", "RB"]


def _read(path: str, seasons=SEASONS, columns=None) -> pl.DataFrame:
    return pl.concat([pl.read_parquet(T / path / f"season={s}" / "data.parquet", columns=columns) for s in seasons], how="diagonal_relaxed")


def build() -> None:
    O.mkdir(parents=True, exist_ok=True)
    sch = pl.concat([pl.read_parquet(f) for f in (T / "team_game" / "schedule").rglob("*.parquet")], how="diagonal_relaxed")
    reg = sch.filter((c("game_type") == "REG") & c("season").is_in(list(SEASONS))).select("game_id", "team", "season", "week").unique()

    ros = _read("player_game/roster", columns=["gsis_id", "game_id", "season", "week", "team", "position", "birth_date", "entry_year"])
    ros = ros.with_columns(group=c("position").replace_strict(GROUP, default=None)).filter(c("group").is_not_null())
    ros = ros.join(reg.select("game_id", "team"), on=["game_id", "team"], how="semi")
    # one group per player-team-season: his most common listed position
    pgrp = ros.group_by("gsis_id", "team", "season").agg(group=c("group").mode().first(), birth_date=c("birth_date").first(), entry_year=c("entry_year").first())

    sn = _read("player_game/snaps", columns=["gsis_id", "game_id", "offense_snaps", "offense_pct", "defense_snaps", "defense_pct"])
    st = _read("player_game/stats", columns=["gsis_id", "game_id", "targets", "carries"])
    g = ros.select("gsis_id", "game_id", "season", "week", "team").unique(["gsis_id", "game_id"]).join(pgrp, on=["gsis_id", "team", "season"])
    g = g.join(sn, on=["gsis_id", "game_id"], how="inner").join(st, on=["gsis_id", "game_id"], how="left").with_columns(c("targets").fill_null(0), c("carries").fill_null(0))
    off = c("group").is_in(list(OFFENSE))
    g = g.with_columns(
        snaps=pl.when(off).then(c("offense_snaps")).otherwise(c("defense_snaps")).fill_null(0),
        share=pl.when(off).then(c("offense_pct")).otherwise(c("defense_pct")).fill_null(0.0),
    ).filter(c("snaps") > 0)
    if g["share"].max() > 1.5:
        g = g.with_columns(share=c("share") / 100)
    # the team's targets and carries that game (every player, all positions)
    allst = _read("player_game/stats", columns=["gsis_id", "game_id", "targets", "carries"])
    allros = _read("player_game/roster", columns=["gsis_id", "game_id", "team"]).unique(["gsis_id", "game_id"])
    tt = allst.join(allros, on=["gsis_id", "game_id"]).group_by("game_id", "team").agg(team_targets=c("targets").sum(), team_carries=c("carries").sum())
    g = g.join(tt, on=["game_id", "team"], how="left").with_columns(
        tgt_share=c("targets") / c("team_targets").clip(1), car_share=c("carries") / c("team_carries").clip(1))
    g = g.select("gsis_id", "game_id", "season", "week", "team", "group", "snaps", "share", "targets", "carries", "team_targets", "team_carries", "tgt_share", "car_share")
    g.write_parquet(O / "pg.parquet")

    # team-games: efficiency and pressure
    pace = pl.concat([pl.read_parquet(f) for f in (T / "team_game" / "pace").rglob("*.parquet")], how="diagonal_relaxed").select("game_id", "team", "epa_per_play", "def_epa_per_play")
    pbp = _read("play/pbp", columns=["game_id", "play_id", "season_type", "posteam", "defteam", "qb_dropback", "sack"]).filter((c("season_type") == "REG") & (c("qb_dropback") == 1))
    par = _read("play/participation", columns=["game_id", "play_id", "was_pressure"])
    d = pbp.join(par, on=["game_id", "play_id"], how="left").with_columns(
        known=c("was_pressure").is_not_null() | (c("sack") == 1), pr=(c("was_pressure").fill_null(False) | (c("sack") == 1)).cast(pl.Int32))
    d = d.filter(c("known"))
    pa = d.group_by("game_id", "posteam").agg(pa_n=pl.len(), pa=c("pr").sum()).rename({"posteam": "team"})
    pm = d.group_by("game_id", "defteam").agg(pm_n=pl.len(), pm=c("pr").sum()).rename({"defteam": "team"})
    tg = reg.join(pace, on=["game_id", "team"], how="left").join(pa, on=["game_id", "team"], how="left").join(pm, on=["game_id", "team"], how="left")
    tg = tg.rename({"epa_per_play": "off_epa", "def_epa_per_play": "def_epa"}).with_columns([c(x).fill_null(0) for x in ("pa_n", "pa", "pm_n", "pm")])
    tg.write_parquet(O / "games.parquet")

    # player-team-seasons
    ps = g.group_by("gsis_id", "team", "season", "group").agg(
        games=pl.len(), snaps=c("snaps").sum(), share=c("share").mean(), tgt_share=c("tgt_share").mean(), car_share=c("car_share").mean(),
        first_wk=c("week").min(), last_wk=c("week").max())
    ps = ps.with_columns(rank=c("snaps").rank("ordinal", descending=True).over("team", "season", "group"))
    ps = ps.with_columns(top=c("rank") <= c("group").replace_strict(TOPK, return_dtype=pl.Int64))
    ps = ps.join(pgrp.select("gsis_id", "team", "season", "birth_date", "entry_year"), on=["gsis_id", "team", "season"], how="left")
    ps = ps.with_columns(age=(pl.date(c("season"), 9, 1) - c("birth_date").cast(pl.Date)).dt.total_days() / 365.25)
    ps.write_parquet(O / "ps.parquet")


def load():
    return pl.read_parquet(O / "pg.parquet"), pl.read_parquet(O / "games.parquet"), pl.read_parquet(O / "ps.parquet")


def departures(ps: pl.DataFrame) -> pl.DataFrame:
    """Top players on T in s with no snap for T in s + 1 (s up to 2023)."""
    nxt = ps.select("gsis_id", "team", season=c("season") - 1).unique()
    top = ps.filter(c("top") & (c("season") <= 2023))
    return top.join(nxt, on=["gsis_id", "team", "season"], how="anti")


if __name__ == "__main__":
    build()
    pg, tg, ps = load()
    print(f"pg {pg.shape}, games {tg.shape}, ps {ps.shape}")
    print(pg.group_by("group").agg(n=pl.len(), share=c("share").mean().round(3)).sort("group"))
    print(ps.filter(c("top")).group_by("group").agg(n=pl.len(), share=c("share").mean().round(3), games=c("games").mean().round(1)).sort("group"))
    dep = departures(ps)
    print("departures by group:", dep.group_by("group").len().sort("group").to_dicts())
    print("team-games with pressure counted, by season:", tg.group_by("season").agg(pa_n=c("pa_n").sum(), rate=(c("pa").sum() / c("pa_n").sum()).round(3)).sort("season").to_dicts())
    print("null off_epa:", tg["off_epa"].null_count(), "age null:", ps["age"].null_count())
