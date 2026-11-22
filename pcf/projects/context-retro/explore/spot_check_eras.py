"""The spot-check's last step: the owners yardstick (repeat with each season's league level out,
and movers' share kept) for the QB's sack measures, by provider era. Appends to build/spot_check.txt.

    python projects/context-retro/explore/spot_check_eras.py
"""

import json

import polars as pl

from pcf.experts.context_retro import plays, split
from pcf.experts.context_retro.run import cache_dir, report_dir

c = pl.col
runs = [json.loads((cache_dir() / t / "run.json").read_text()) for t in ("backtest", "vault")]
hist = pl.concat([pl.read_parquet(i["path"]) for i in runs], how="vertical_relaxed")
seasons = range(2017, 2026)
parts = split.play_parts(hist, plays.load(seasons))
pg = split.player_game(parts, split.lineman_plays(seasons))
teams = split.teams_table(seasons)
lines = ["", "== The owners yardstick by provider (QBs 150+ dropbacks both seasons, linemen 300+; repeat "
         "with each season's league level out; share kept = movers' r over stayers')"]
for label, (a, b) in {"old provider, pairs 2017-18 to 2021-22": (2017, 2022),
                      "new provider, pairs 2023-24 and 2024-25": (2023, 2025),
                      "all, pairs 2017-18 to 2024-25": (2017, 2025)}.items():
    t = split.owner_table(pg, teams, a, b)
    lines.append(f"  {label}:")
    for row in t.iter_rows(named=True):
        lines.append(f"    {row['who']} {row['measure']}: pairs {row['pairs']} (movers {row['movers']}), repeat "
                     f"{row['repeat']:+.2f} ({row['lo90']:+.2f} to {row['hi90']:+.2f}), kept "
                     f"{100 * row['share_kept']:.0f}% ({100 * row['kept_lo90']:.0f}% to "
                     f"{100 * row['kept_hi90']:.0f}%), passes {row['passes']}")
print("\n".join(lines))
with open(report_dir() / "spot_check.txt", "a", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
