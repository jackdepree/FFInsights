"""The seed-locked flag through the harness (2026-11-07): the validated `margin` and `win` runs with
`lock_diff` against the same runs without it (pull 0.4), game by game, 2016-2024.

1. Margin: mean miss, range score and q10-q90 coverage, overall and by part of the season, with
   the paired change (with lock minus without) and a 90% interval resampled by game.
2. The gap to the close by part of the season, before and after.
3. Win: log loss, calibration error and slope, before and after, and the final week alone.

Run from pcf/: .venv/Scripts/python.exe projects/elo/explore/lock_validated.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import carryover as C  # noqa: E402

from pcf.config import get_config  # noqa: E402
from pcf.data.gateway import Gateway  # noqa: E402
from pcf.validation import calibration as K  # noqa: E402
from pcf.validation import scores as S  # noqa: E402

c = pl.col
MARGIN = {"without": "3963e4d79a6e4b67a181507df11efa61", "with": "21082e26cec94ea1920081554197d201"}
WIN = {"without": "ba61e29527324c26bd40f13c49582e23", "with": "b811be4301f54f1491bfce1ef29e06d5"}
RNG = np.random.default_rng(20261107)
PARTS = ("other weeks", "second-to-last week", "final week", "playoffs")


def history(variant: str, run: str) -> pl.DataFrame:
    return pl.read_parquet(get_config().zone("outputs") / "elo" / variant / run / "history.parquet")


def games() -> pl.DataFrame:
    g = C.games()
    pre = Gateway().source.part("game", "pregame").select("game_id", "spread_line", "home_moneyline", "away_moneyline")
    last = g.filter(c("game_type") == "REG").group_by("season").agg(last=c("week").max())
    odds = lambda m: pl.when(m > 0).then(100 / (m + 100)).otherwise(-m / (-m + 100))  # noqa: E731
    return (
        g.select("game_id", "season", "week", "game_type", "home_score", "away_score")
        .join(pre, on="game_id").join(last, on="season")
        .with_columns(
            margin=(c("home_score") - c("away_score")).cast(pl.Float64),
            won=pl.when(c("home_score") > c("away_score")).then(1.0)
            .when(c("home_score") < c("away_score")).then(0.0).otherwise(0.5),
            p_close=odds(c("home_moneyline")) / (odds(c("home_moneyline")) + odds(c("away_moneyline"))),
            part=pl.when(c("game_type") != "REG").then(pl.lit("playoffs"))
            .when(c("week") == c("last")).then(pl.lit("final week"))
            .when(c("week") == c("last") - 1).then(pl.lit("second-to-last week"))
            .otherwise(pl.lit("other weeks")),
        )
    )  # fmt: skip


def interval(x: np.ndarray) -> str:
    boots = RNG.choice(x, (4000, len(x))).mean(axis=1)
    return f"{x.mean():+.3f} ({np.quantile(boots, 0.05):+.3f} to {np.quantile(boots, 0.95):+.3f})"


def margin_frame(g: pl.DataFrame) -> pl.DataFrame:
    d = g
    for k, run in MARGIN.items():
        h = history("margin", run).select("game_id", *(pl.col(q).alias(f"{q}_{k}") for q in ("mean", "q10", "q50", "q90")))
        d = d.join(h, on="game_id")
        d = d.with_columns(
            pl.mean_horizontal(S.pinball(c("margin"), c(f"{q}_{k}"), lvl) for q, lvl in S.QUANTILE_LEVELS.items()).alias(f"range_{k}"),
            (c("margin") - c(f"mean_{k}")).abs().alias(f"miss_{k}"),
            c("margin").is_between(c(f"q10_{k}"), c(f"q90_{k}")).alias(f"in_{k}"),
        )
    return d.with_columns(miss_close=(c("margin") - c("spread_line")).abs())


def main() -> None:
    g = games()
    d = margin_frame(g)
    print(f"== 1. Margin, with the lock flag against without ({d.height} games, 2016-2024)")
    print(f"   {'':<22}{'games':>6}{'miss w/o':>10}{'miss with':>10}   change in mean miss         change in range score       coverage w/o, with")
    for name, e in [("all games", d), *[(p, d.filter(c("part") == p)) for p in PARTS]]:
        dm = (e["miss_with"] - e["miss_without"]).to_numpy()
        dr = (e["range_with"] - e["range_without"]).to_numpy()
        print(f"   {name:<22}{e.height:>6}{e['miss_without'].mean():>10.3f}{e['miss_with'].mean():>10.3f}   {interval(dm):<28}{interval(dr):<28}{e['in_without'].mean():.1%}, {e['in_with'].mean():.1%}")
    print(f"   range score overall: without {d['range_without'].mean():.4f}, with {d['range_with'].mean():.4f}")

    print("\n== 2. Elo's mean miss minus the close's, by part of the season")
    for name, e in [("all games", d), *[(p, d.filter(c("part") == p)) for p in PARTS]]:
        print(f"   {name:<22}without {(e['miss_without'] - e['miss_close']).mean():+.2f}   with {interval((e['miss_with'] - e['miss_close']).to_numpy())}")

    print("\n== 3. Win chance")
    w = g.filter(c("won") != 0.5)
    for k, run in WIN.items():
        w = w.join(history("win", run).select("game_id", pl.col("mean").alias(f"p_{k}")), on="game_id")
    w = w.with_columns(**{f"ll_{k}": S.log_loss("won", f"p_{k}") for k in (*WIN, "close")})
    for name, e in [("all games", w), ("final week", w.filter(c("part") == "final week"))]:
        print(f"   {name} ({e.height} games): log loss without {e['ll_without'].mean():.4f}, with {e['ll_with'].mean():.4f}, "
              f"close {e['ll_close'].mean():.4f}; change {interval((e['ll_with'] - e['ll_without']).to_numpy())}")
    for k in WIN:
        e = w.rename({f"p_{k}": "mean", "won": "y"})
        print(f"   calibration {k}: error {K.calibration_error(K.probability_table(e)):.2f} points, slope {K.calibration_slope(e):.3f}")


if __name__ == "__main__":
    main()
