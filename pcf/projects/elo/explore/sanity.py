"""The football sanity check for Elo (VALIDATION.md §10), from the saved validation runs.

1. The three forecasts agree with each other: implied team points (total ± margin) / 2 are never
   negative, and the win chance is above 50% exactly when the margin favors the home team.
2. Range coverage for favorites and underdogs (by the forecast), and by the Elo's own size.
3. The 10 biggest disagreements with the close, on the margin and the total, for the CEO's review.

Run from pcf/: .venv/Scripts/python.exe projects/elo/explore/sanity.py
"""

# ruff: noqa: E501
from __future__ import annotations

import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
RUNS = {
    "margin": "3963e4d79a6e4b67a181507df11efa61",
    "total": "417b504c3ce84c748d0b541e4de3fcc4",
    "win": "ba61e29527324c26bd40f13c49582e23",
}


def history(variant: str) -> pl.DataFrame:
    folder = get_config().zone("outputs") / "elo" / variant / RUNS[variant]
    return pl.read_parquet(folder / "history.parquet")


def main() -> None:
    pl.Config.set_tbl_rows(30)
    pl.Config.set_tbl_width_chars(200)
    pl.Config.set_tbl_hide_dataframe_shape(True)
    src = Gateway().source
    games = (
        src.part("game", "schedule").select("game_id", "home_team", "away_team")
        .join(src.part("game", "result").select("game_id", "home_score", "away_score"), on="game_id")
        .join(src.part("game", "pregame").select("game_id", "spread_line", "total_line"), on="game_id")
    )  # fmt: skip
    m = history("margin").select("game_id", margin="mean", m10="q10", m90="q90")
    t = history("total").select("game_id", total="mean")
    w = history("win").select("game_id", win="mean")
    d = m.join(t, on="game_id").join(w, on="game_id").join(games, on="game_id")
    d = d.with_columns(
        home_pts=(c("total") + c("margin")) / 2,
        away_pts=(c("total") - c("margin")) / 2,
        y=c("home_score") - c("away_score"),
    )
    print(f"== 1. Agreement, {d.height:,} games")
    print(f"   lowest implied team points: {min(d['home_pts'].min(), d['away_pts'].min()):.1f}")
    bad = d.filter((c("win") > 0.5) != (c("margin") > 0))
    print(f"   win chance on the other side of 50% from the margin: {bad.height} games")
    if bad.height:
        print(bad.select("game_id", "margin", "win").sort(c("margin").abs(), descending=True).head(10))

    print("\n== 2. Range coverage (margin) by who Elo favors")
    cov = d.with_columns(
        inside=(c("y") >= c("m10")) & (c("y") <= c("m90")),
        side=pl.when(c("margin").abs() < 3).then(pl.lit("within 3"))
        .when(c("margin").abs() < 7).then(pl.lit("3 to 7"))
        .otherwise(pl.lit("7 or more")),
        home=pl.when(c("margin") > 0).then(pl.lit("home favored")).otherwise(pl.lit("away favored")),
    )  # fmt: skip
    for by in ("side", "home"):
        print(cov.group_by(by).agg(rows=pl.len(), inside=c("inside").mean().round(3)).sort(by))

    print("\n== 3. Biggest disagreements with the close")
    for name, col, line in (("margin", "margin", "spread_line"), ("total", "total", "total_line")):
        y = "y" if name == "margin" else "actual_total"
        top = (
            d.with_columns(actual_total=c("home_score") + c("away_score"), gap=c(col) - c(line))
            .sort(c("gap").abs(), descending=True)
            .head(10)
            .select("game_id", elo=c(col).round(1), close=line, gap=c("gap").round(1), actual=y)
        )
        closer = top.select(((c("actual") - c("elo")).abs() < (c("actual") - c("close")).abs()).sum()).item()
        print(f"   {name}: Elo was closer in {closer} of 10")
        print(top)
    all_closer = d.select(
        elo_closer=((c("y") - c("margin")).abs() < (c("y") - c("spread_line")).abs()).mean()
    ).item()
    print(f"   every game: Elo's margin was closer than the close in {all_closer:.1%}")


if __name__ == "__main__":
    main()
