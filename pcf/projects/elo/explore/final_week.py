"""The CEO's spot-check of F3 (2026-11-07): is Elo's final-week gap to the close really teams
resting starters?

1. The gap to the close by part of the season, with a 90% interval (resampled by game), and the
   second-to-last week as a control: if ratings simply go stale late in the season, it shows there.
2. Final-week games split by whether either team's usual QB rested (on the roster, not listed
   Out or Doubtful, under half the snaps; or listed Out or Doubtful): how much of the gap each
   group holds.
3. For the resting team: did Elo overrate it (actual minus forecast, from its side)? And the close?
4. The other explanations: cold games (under 32°F), and how much of the gap the 10 worst games
   hold.

Elo's forecasts are the validated `margin` history (pull 0.4). 2016-2024. Rest is measured after
the game (snap counts), so it explains misses; it's not a feature.
Run from pcf/: .venv/Scripts/python.exe projects/elo/explore/final_week.py
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

c = pl.col
RUN = "3963e4d79a6e4b67a181507df11efa61"
RNG = np.random.default_rng(20261107)


def frame() -> tuple[pl.DataFrame, pl.DataFrame]:
    s = Gateway().source
    g = C.games()
    pregame = s.part("game", "pregame").select("game_id", "spread_line")
    temp = s.part("game", "result").select("game_id", "temp")
    h = pl.read_parquet(get_config().zone("outputs") / "elo" / "margin" / RUN / "history.parquet")
    last = g.filter(c("game_type") == "REG").group_by("season").agg(last=c("week").max())
    d = (
        h.select("game_id", elo="mean")
        .join(g.select("game_id", "season", "week", "game_type", "home_team", "away_team", "home_score", "away_score"), on="game_id")
        .join(pregame, on="game_id")
        .join(temp, on="game_id", how="left")
        .join(last, on="season")
        .with_columns(y=(c("home_score") - c("away_score")).cast(pl.Float64))
        .with_columns(
            e_elo=(c("y") - c("elo")).abs(),
            e_close=(c("y") - c("spread_line")).abs(),
            part=pl.when(c("game_type") != "REG").then(pl.lit("playoffs"))
            .when(c("week") == c("last")).then(pl.lit("final week"))
            .when(c("week") == c("last") - 1).then(pl.lit("second-to-last week"))
            .otherwise(pl.lit("other weeks")),
        )
        .with_columns(gap=c("e_elo") - c("e_close"))
    )  # fmt: skip
    return d, C.qb_rest(g).select("game_id", "team", "sat", "listed_out")


def interval(x: np.ndarray) -> tuple[float, float, float]:
    boots = RNG.choice(x, (4000, len(x))).mean(axis=1)
    return float(x.mean()), float(np.quantile(boots, 0.05)), float(np.quantile(boots, 0.95))


def row(name: str, e: pl.DataFrame) -> None:
    m, lo, hi = interval(e["gap"].to_numpy())
    print(f"   {name:<42}{e.height:>6}{e['e_elo'].mean():>8.2f}{e['e_close'].mean():>8.2f}{m:>+8.2f}  ({lo:+.2f} to {hi:+.2f})")


def head() -> None:
    print(f"   {'':<42}{'games':>6}{'Elo':>8}{'close':>8}{'gap':>8}  90% interval")


def main() -> None:
    d, rest = frame()
    print("== 1. Elo's mean miss minus the close's, by part of the season (2016-2024)")
    head()
    for part in ("other weeks", "second-to-last week", "final week", "playoffs"):
        row(part, d.filter(c("part") == part))

    fin = d.filter(c("part") == "final week")
    r = rest.with_columns(rested=c("sat") | c("listed_out"))
    home = r.rename({"team": "home_team", "rested": "h_rest", "sat": "h_sat"}).drop("listed_out")
    away = r.rename({"team": "away_team", "rested": "a_rest", "sat": "a_sat"}).drop("listed_out")
    fin = (
        fin.join(home, on=["game_id", "home_team"], how="left")
        .join(away, on=["game_id", "away_team"], how="left")
        .with_columns(c("h_rest", "a_rest", "h_sat", "a_sat").fill_null(False))
        .with_columns(any_rest=c("h_rest") | c("a_rest"), any_sat=c("h_sat") | c("a_sat"))
    )
    total = fin["gap"].sum()
    print("\n== 2. Final week, by whether a usual QB rested (measured after the game)")
    head()
    for name, f in (("a usual QB sat healthy", c("any_sat")),
                    ("a usual QB sat or was listed Out/Doubtful", c("any_rest")),
                    ("no usual QB missing", ~c("any_rest"))):  # fmt: skip
        e = fin.filter(f)
        row(name, e)
        print(f"   {'':<42}  share of the final week's excess: {e['gap'].sum() / total:.0%}")

    print("\n== 3. The resting team's points against each forecast, from its side (+ = it did better)")
    side = pl.concat([
        fin.filter(c("h_rest")).select(elo=c("y") - c("elo"), close=c("y") - c("spread_line")),
        fin.filter(c("a_rest")).select(elo=-(c("y") - c("elo")), close=-(c("y") - c("spread_line"))),
    ])  # fmt: skip
    for col in ("elo", "close"):
        m, lo, hi = interval(side[col].to_numpy())
        print(f"   against {col:<6}{m:+.1f} points ({lo:+.1f} to {hi:+.1f}), {side.height} resting team-games")

    print("\n== 4. Other explanations")
    head()
    row("final week, under 32°F", fin.filter(c("temp") < 32))
    row("final week, 32°F or warmer (domes: no temp)", fin.filter(~(c("temp") < 32).fill_null(False)))
    top = fin.sort("gap", descending=True).head(10)
    print(f"   the 10 worst final-week games hold {top['gap'].sum() / total:.0%} of the final week's excess; "
          f"without them the gap is {fin.sort('gap', descending=True).tail(fin.height - 10)['gap'].mean():+.2f}")  # fmt: skip
    print(top.select("game_id", "elo", close="spread_line", actual="y", h_rest="h_rest", a_rest="a_rest", gap=c("gap").round(1)))


if __name__ == "__main__":
    main()
