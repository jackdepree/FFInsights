"""Each final variant's latest backtest: typical miss, prediction against result (r), and for
volume the game's total (both teams) too. Test seasons 2016-2024."""

import glob
import os

import polars as pl

from pcf.data.tables.store import read_part
from pcf.experts.pace import features as F

c = pl.col
tg = read_part("team_game", "pace", seasons=range(2016, 2025)).collect()
measures = {**F.HABITS, **F.VOLUME}
rows = []
for folder in sorted(glob.glob("data/outputs/pace/*")):
    variant = os.path.basename(folder)
    runs = sorted(glob.glob(f"{folder}/*/history.parquet"), key=os.path.getmtime)
    if not runs:
        continue
    trait = next(m for m in sorted(measures, key=len, reverse=True) if variant.startswith(m))
    h = pl.read_parquet(runs[-1]).filter(c("as_of").dt.year() >= 2016)
    j = h.join(tg.select("game_id", "team", y=measures[trait][0]), on=["game_id", "team"])
    j = j.drop_nulls("y")
    row = {
        "variant": variant,
        "rows": j.height,
        "miss": (j["y"] - j["mean"]).abs().mean(),
        "r": j.select(pl.corr("mean", "y")).item(),
        "inside": j.select(((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()).item(),
    }
    if trait in F.VOLUME:
        g = j.group_by("game_id").agg(c("mean").sum(), c("y").sum(), pl.len()).filter(c("len") == 2)
        row["game_r"] = g.select(pl.corr("mean", "y")).item()
        row["game_miss"] = (g["y"] - g["mean"]).abs().mean()
    rows.append(row)
with pl.Config(tbl_rows=50, tbl_width_chars=200, float_precision=4):
    print(pl.DataFrame(rows))
