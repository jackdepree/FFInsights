"""Measure the built tables: spine coverage, join rates, cross-source totals, timing and speed.

Run from pcf/ after `pcf tables build`:  uv run python projects/grain-tables/explore/check_tables.py
"""

import sys
import time
from datetime import timedelta

import polars as pl

from pcf.data.tables import load

STATS = ["passing_yards", "rushing_yards", "receptions", "receiving_yards"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_width_chars(200)
    rows = []
    for season in range(2002, 2027):
        t = time.time()
        pg = load("player_game", seasons=[season])
        took = time.time() - t
        snapped = pg.filter(
            pl.sum_horizontal("offense_snaps", "defense_snaps", "st_snaps").fill_null(0) > 0
        )
        played = pg.filter(pl.col("stats_known_at").is_not_null() | pl.col("snaps_known_at").is_not_null())
        tg = load("team_game", seasons=[season], parts=["stats"])
        sums = (
            pg.group_by("game_id", "team")
            .agg(pl.col(STATS).sum())
            .join(tg.select("game_id", "team", *STATS), on=["game_id", "team"], suffix="_team")
        )
        match = {s: round(((sums[s] - sums[f"{s}_team"]).abs() <= 1).mean(), 4) for s in STATS}
        rows.append(
            {
                "season": season,
                "rows": pg.height,
                "per_team_game": round(pg.height / pg.select("game_id", "team").n_unique(), 1),
                "played_on_roster": round(played["on_roster"].mean(), 4) if played.height else None,
                "snapped": snapped.height,
                "no_snap_share": round(1 - snapped.height / pg.height, 3) if snapped.height else None,
                "inactive": pg.filter(pl.col("status") == "INA").height,
                **{f"sum_{k}": v for k, v in match.items()},
                "load_s": round(took, 2),
            }
        )
    print(pl.DataFrame(rows))

    print("\n## play joins")
    for season in (2016, 2020, 2022, 2024, 2025):
        play = load("play", seasons=[season])
        rp = play.filter(pl.col("play_type").is_in(["run", "pass"]))
        print(season, "run/pass:", rp.height,
              "| participation:", round(rp["participation_known_at"].is_not_null().mean(), 4),
              "| ftn:", round(rp["ftn_known_at"].is_not_null().mean(), 4))

    print("\n## team_game rows per game, result rows")
    tg = load("team_game")
    print(tg.group_by("game_id").len()["len"].value_counts().rows(),
          "| played games missing stats:", tg.filter(pl.col("points_for").is_not_null() & pl.col("stats_known_at").is_null()).select("game_id").n_unique())

    print("\n## point in time: a 2024 Sunday")
    kick = load("game", seasons=[2024]).filter(pl.col("game_id") == "2024_10_DEN_KC")["kickoff"].item()
    for label, at in [("kickoff - 2h", kick - timedelta(hours=2)), ("kickoff", kick), ("+1 day", kick + timedelta(days=1, minutes=1))]:
        g = load("player_game", at=at, seasons=[2024]).filter(pl.col("game_id") == "2024_10_DEN_KC")
        later = [c for c in g.columns if c.endswith("known_at") and g[c].drop_nulls().gt(at).any()]
        print(label, "| rows:", g.height, "| status known:", g["status"].is_not_null().sum(),
              "| stats known:", g["stats_known_at"].is_not_null().sum(), "| any later known_at:", later)


if __name__ == "__main__":
    main()
