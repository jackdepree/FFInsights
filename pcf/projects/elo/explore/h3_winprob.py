"""H3: does a game's average win probability across its plays say more than the final margin?

1. Each game's average home win probability over its plays (nflverse `home_wp`, the model
   without the betting line), turned into points by a straight line fit on 2002-2015 margins.
2. Repeatability: odd-week against even-week team-season averages, next to the margin's.
3. The rating: rung 1 (margin Elo, half pull) learning from a blend, w x margin + (1 - w) x the
   win-probability points, against rung 1. Step size and w tuned on 2002-2015; reported on
   2016-2024 and on 2020-2024, the seasons the win-probability model wasn't fit on
   (tag-tables#F4).

The vault (2025) isn't read. Run from pcf/:
.venv/Scripts/python.exe projects/elo/explore/h3_winprob.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import ladder as L  # noqa: E402

from pcf.data.tables.store import read_part  # noqa: E402

c = pl.col


def avg_wp() -> pl.DataFrame:
    return (
        read_part("play", "pbp", seasons=list(range(L.FIRST, L.LAST + 1)))
        .select("game_id", "home_wp")
        .filter(c("home_wp").is_not_null() & c("home_wp").is_not_nan())
        .group_by("game_id")
        .agg(wp=c("home_wp").mean(), plays=pl.len())
        .collect()
    )


def split_half(g: pl.DataFrame, col: str) -> float:
    reg = g.filter(c("game_type") == "REG")
    tg = pl.concat(
        [
            reg.select("season", "week", team="home_team", v=c(col)),
            reg.select("season", "week", team="away_team", v=-c(col)),
        ]
    )
    h = tg.group_by("season", "team", odd=c("week") % 2 == 1).agg(c("v").mean())
    j = h.filter(c("odd")).join(h.filter(~c("odd")), on=["season", "team"], suffix="_e")
    return float(np.corrcoef(j["v"], j["v_e"])[0, 1])


def main() -> None:
    g = L.games().join(avg_wp(), on="game_id", how="left")
    print(f"games without win probability: {g['wp'].null_count()}")
    priors = L.season_priors(g)
    tune = g.filter(c("season").is_between(L.TUNE_FROM, L.REPORT_FROM - 1))
    x, y = (tune["wp"] - 0.5).to_numpy(), tune["margin"].to_numpy()
    b = float((x * y).sum() / (x * x).sum())
    print(f"points per unit of average win probability above 0.5: {b:.1f}")
    # the 3 games without play-by-play fall back to their margin
    g = g.with_columns(wp_pts=((c("wp") - 0.5) * b).fill_null(c("margin")))
    r = float(np.corrcoef(g["wp_pts"], g["margin"])[0, 1])
    print(f"game-level correlation of win-probability points and margin: {r:.3f}")
    print(
        f"split-half r: margin {split_half(g, 'margin'):.3f}, "
        f"win-probability points {split_half(g, 'wp_pts'):.3f}"
    )

    names = []
    for w in (0.0, 0.25, 0.5, 0.75):
        name = f"blend_{w}"
        g = g.with_columns((w * c("margin") + (1 - w) * c("wp_pts")).alias(name))
        names.append(name)
    grid_k = (0.05, 0.06, 0.07, 0.08, 0.09)

    print("\nRATINGS: each blend at its tuned step size (w = weight on the margin)")
    for lo in (L.REPORT_FROM, 2020):
        print(f" reported {lo}-{L.LAST}")
        for name in names:
            grid = [{"k": k, "pull": 0.5, "signal": name} for k in grid_k]
            L.show(name, L.versus_rung1(g, priors, "margin_pull", grid, lo=lo))
        grid = [{"k": k, "pull": 0.5, "signal": n} for k in grid_k for n in names]
        L.show("w and step tuned together", L.versus_rung1(g, priors, "margin_pull", grid, lo=lo))


if __name__ == "__main__":
    main()
