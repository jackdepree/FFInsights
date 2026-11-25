"""Availability build: the football sanity check (rule h). 2024, the week 9 run: the skill players
with the most expected games of health absence over the rest of the season (rest_chain's saved
history), and what happened; and the five teams with the largest snap-weighted games lost.

Run from pcf/: <venv python> projects/availability/build/sanity_run.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.availability import checks as K

c = pl.col
OUT = Path(__file__).with_name("sanity.txt")
lines = []
h = pl.read_parquet(K.cache_dir() / "hist_rest_chain.parquet")
f = pl.read_parquet(K.cache_dir() / "features.parquet").select(*K.KEYS, "season", "week", "team", "state", "status", "part")
names = Gateway().view(END_OF_TIME, "in_season", {"player_game": ("roster",)}).table("player_game", seasons=[2024]).select("gsis_id", "full_name").unique("gsis_id")
x = h.join(f.drop("season", "state"), on=K.KEYS).filter((c("season") == 2024) & (c("week") == 9) & c("position").is_in(["QB", "RB", "WR", "TE"]))
x = x.join(names, on="gsis_id", how="left")
lines.append("2024, week 9 run: QB/RB/WR/TE not on a reserve list, most expected games of health absence over the rest of the season (rest_chain)")
for r in x.filter(c("state") != "r").sort("mean", descending=True).head(12).iter_rows(named=True):
    lines.append(f"  {r['full_name']:<22} {r['position']} {r['team']}  state {r['state']} ({r['part']})  expected {r['mean']:.1f} of {r['n_window']:.0f} (q10 {r['q10']:.0f}, q90 {r['q90']:.0f}); missed {r['y']:.0f}")
lines.append("  and the healthiest-looking starters' spread: share of healthy rows with q90 of 0 games: "
             f"{x.filter(c('state') == 'h').select((c('q90') == 0).mean()).item():.2f}")
a = pl.read_parquet(K.cache_dir() / "agl.parquet").group_by("team", "season").agg(c("agl").sum())
lines.append("\nSnap-weighted games lost, the most and least per season (2016-2024)")
for s in (2022, 2023, 2024):
    t = a.filter(c("season") == s).sort("agl", descending=True)
    lines.append(f"  {s}: most " + ", ".join(f"{r['team']} {r['agl']:.0f}" for r in t.head(3).iter_rows(named=True))
                 + "; least " + ", ".join(f"{r['team']} {r['agl']:.0f}" for r in t.tail(3).iter_rows(named=True)))
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
