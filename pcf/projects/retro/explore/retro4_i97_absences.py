# ruff: noqa: E501
"""Retro 4, group A: I97's data check. Are there enough quasi-random absences in the free data?

I97 (Claude, 2026-11-21): games a player missed for reasons unrelated to how he or his team was playing are the
closest thing football has to a randomized knockout. Odds before the test: 50% that the free data mark too few such
games to say; 40% a clear QB slope; 20% any other group.

This is only the data check (counts), not the test. The weekly roster status codes, read from who carries them:
- R59: Reserve/COVID-19 (2020-2021);
- R40: Reserve/Suspended (a fixed suspension: Watson 2022, 11 weeks);
- R30: Reserve/Suspended by the commissioner, indefinite (Ridley 2022, gambling).
R62 (2020's opt-outs) is a whole-season choice made before the season, so it's counted apart.

A "regular" is a player who was his team's top player at his group that season (vacated's top k: WR 2, TE 1, RB 1,
OL 5, DL 3) or its most-used QB, and had played for the team earlier that season.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro4_i97_absences.py > projects/retro/explore/retro4_i97_absences.txt
"""

import os
from pathlib import Path

import polars as pl

c = pl.col
T = Path(os.environ["PCF_DATA_DIR"]) / "tables"
S = range(2016, 2025)


def rd(p, cols=None):
    return pl.concat([pl.read_parquet(T / p / f"season={s}" / "data.parquet", columns=cols) for s in S], how="diagonal_relaxed")


st = rd("roster_week/status", ["gsis_id", "season", "week", "team", "position", "status", "status_code"])
print("== status codes present, by season (share of rows with a code)")
print(st.group_by("season").agg(coded=c("status_code").is_not_null().mean(), rows=pl.len()).sort("season"))

QR = {"R59": "COVID list", "R40": "suspended", "R30": "suspended, indefinite", "R62": "opted out (2020)"}
q = st.filter(c("status_code").is_in(list(QR))).with_columns(why=c("status_code").replace_strict(QR))
print("\n== player-weeks on each list, by season")
print(q.group_by("season", "why").len().sort("season", "why"))

# regulars: the team's most-used QB, and vacated's top players at the other groups
ros = rd("player_game/roster", ["gsis_id", "game_id", "season", "week", "team", "position"])
sn = rd("player_game/snaps", ["gsis_id", "game_id", "offense_snaps", "defense_snaps"]).join(ros.select("gsis_id", "game_id", "season", "week", "team"), on=["gsis_id", "game_id"])
ps = pl.read_parquet(Path(os.environ["PCF_DATA_DIR"]) / "interim" / "vacated" / "ps.parquet")
top = ps.filter(c("top")).select("gsis_id", "team", "season", "group", "first_wk")
qb = ros.filter(c("position") == "QB").join(sn.select("gsis_id", "game_id", "offense_snaps"), on=["gsis_id", "game_id"], how="left").with_columns(c("offense_snaps").fill_null(0))
qb = qb.group_by("gsis_id", "team", "season").agg(snaps=c("offense_snaps").sum(), first_wk=c("week").filter(c("offense_snaps") > 0).min())
qb = qb.sort("snaps", descending=True).group_by("team", "season").head(1).with_columns(group=pl.lit("QB")).select("gsis_id", "team", "season", "group", "first_wk")
reg = pl.concat([top, qb], how="diagonal_relaxed")

played = sn.filter((c("offense_snaps") > 0) | (c("defense_snaps") > 0)).select("gsis_id", "season", "week").unique()
miss = q.join(reg, on=["gsis_id", "team", "season"]).filter(c("week") > c("first_wk")).join(played, on=["gsis_id", "season", "week"], how="anti")
print("\n== regulars' games missed while on a list (after his first game for the team that season)")
print(miss.group_by("why", "group").agg(games=pl.len(), players=c("gsis_id").n_unique()).sort("why", "group"))
print("\n== QBs: games, players, and who")
qbm = miss.filter(c("group") == "QB").group_by("gsis_id", "team", "season", "why").agg(games=pl.len()).sort("season")
print(qbm)
print("\n== totals: quasi-random games missed by regulars", miss.filter(c("why") != "opted out (2020)").height, "; QB games", miss.filter((c("group") == "QB") & (c("why") != "opted out (2020)")).height)
# for scale: all games missed by regulars between first and last game, any reason (vacated's absence count)
print("for scale: vacated's absences of top players (any reason), 2016-2024: 2,737 games")
