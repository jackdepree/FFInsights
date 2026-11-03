"""Two CEO questions on the participation exploration (2026-11-03):
1. Do past box-score stats (targets, carries, yards, completions, sacks, efficiency, special
   teams snaps, experience) predict next game's snap share beyond past snap shares?
2. How predictable is participation over longer horizons: the next 3 and 9 games, and the rest
   of the season?
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/box_and_horizons.py

Same rows and split as profile_participation.py: rostered QB/RB/WR/TE, fit 2013-2020, scored
2021-2024, Saturday's information. Every stat is shifted one game, so only earlier games count.
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

from pcf.data.tables.store import load

sys.path.insert(0, str(Path(__file__).parent))
from profile_participation import POS, SATURDAY, SEASONS, TEST, TRAIN, design, frame  # noqa: E402

c = pl.col
BOX = ["targets", "target_share", "receptions", "receiving_yards", "carries", "rushing_yards",
       "attempts", "completions", "passing_yards", "sacks_suffered", "fantasy_points_ppr",
       "offense_snaps", "st_pct", "team_snaps"]  # fmt: skip
EFFICIENCY = ["epa_per_play", "yards_per_touch"]
HORIZONS = {"next game": 1, "next 3": 3, "next 9": 9, "rest of season": None}


def with_box(df: pl.DataFrame) -> pl.DataFrame:
    stats = load("player_game", parts=["stats", "snaps"], seasons=SEASONS).select(
        "gsis_id", "game_id", *BOX[:-3], "offense_snaps", "st_pct", "passing_epa",
        "rushing_epa", "receiving_epa",
        team_snaps=c("offense_snaps") / c("offense_pct"),
    )  # fmt: skip
    g = ["gsis_id"]
    df = (
        df.join(stats, on=["gsis_id", "game_id"], how="left")
        .with_columns([c(x).fill_null(0.0).fill_nan(0.0) for x in [*BOX, "passing_epa",
                       "rushing_epa", "receiving_epa"]])  # fmt: skip
        .with_columns(
            plays=c("attempts") + c("carries") + c("targets"),
            epa=c("passing_epa") + c("rushing_epa") + c("receiving_epa"),
            yards=c("rushing_yards") + c("receiving_yards"),
            touches=c("carries") + c("receptions"),
        )
        .sort("gsis_id", "kickoff")
    )
    roll = lambda x, n: c(x).shift(1).rolling_sum(n, min_samples=1).over(g)  # noqa: E731
    df = df.with_columns(
        *[c(x).shift(1).rolling_mean(3, min_samples=1).over(g).alias(f"{x}_3") for x in BOX],
        *[c(x).shift(1).rolling_mean(8, min_samples=1).over(g).alias(f"{x}_8") for x in BOX],
        epa_per_play=roll("epa", 8) / roll("plays", 8),
        yards_per_touch=roll("yards", 8) / roll("touches", 8),
        age=(c("kickoff").dt.date() - c("birth_date")).dt.total_days()
        / 365.25,
        exp=c("years_exp").cast(pl.Float64),
        draft=c("draft_number").cast(pl.Float64).fill_null(300.0),
    )
    return df


BOX_FEATURES = [*[f"{x}_{n}" for x in BOX for n in (3, 8)], *EFFICIENCY, "age", "exp", "draft"]


def with_horizons(df: pl.DataFrame) -> pl.DataFrame:
    """Each horizon's outcome: the average share over this and the next h-1 of the player's
    rostered games in the same season. Rows without h games left in the season are dropped for
    that horizon (null), so a player cut mid-season leaves the window early (see the caveat)."""
    g = ["gsis_id", "season"]
    df = df.sort("gsis_id", "kickoff").with_columns(
        left=c("share").cum_count(reverse=True).over(g),
        rest=c("share").cum_sum(reverse=True).over(g) / c("share").cum_count(reverse=True).over(g),
    )
    out = {}
    for name, h in HORIZONS.items():
        if h is None:
            out[name] = pl.when(c("left") >= 4).then(c("rest"))
        elif h == 1:
            out[name] = c("share")
        else:
            fwd = c("share").reverse().rolling_mean(h, min_samples=h).reverse().over(g)
            out[name] = pl.when(c("left") >= h).then(fwd)
    return df.with_columns(**{f"y_{k}": v for k, v in out.items()})


def r2(y, p) -> float:
    return 1 - ((y - p) ** 2).mean() / y.var()


def fit(a, b, cols, ycol):
    m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=0)
    m.fit(a.select(cols).to_numpy(), a[ycol].to_numpy())
    return m.predict(b.select(cols).to_numpy()).clip(0, 1), m


def prep(df):
    d = design(df).with_columns(
        [c(x).cast(pl.Float64).fill_nan(None).fill_null(0.0) for x in BOX_FEATURES]
    )
    return d.filter(c("season").is_in(list(TRAIN))), d.filter(c("season").is_in(list(TEST)))


def box_value(df):
    tr, te = prep(df)
    print("\n== Q1. Next game's share: do box-score stats add to past shares? (Saturday info)")
    rows = []
    for pos in POS:
        a, b = tr.filter(c("position") == pos), te.filter(c("position") == pos)
        y = b["share"].to_numpy()
        p0, _ = fit(a, b, SATURDAY, "share")
        p1, _ = fit(a, b, [*SATURDAY, *BOX_FEATURES], "share")
        played = (b["avg8"] > 0).to_numpy()
        rows.append({"position": pos, "rows": b.height, "R2 shares": r2(y, p0),
                     "R2 + box": r2(y, p1), "gain": r2(y, p1) - r2(y, p0),
                     "MAE shares": np.abs(y - p0).mean() * 100,
                     "MAE + box": np.abs(y - p1).mean() * 100,
                     "R2 shares (played)": r2(y[played], p0[played]),
                     "R2 + box (played)": r2(y[played], p1[played])})  # fmt: skip
    with pl.Config(float_precision=3, tbl_width_chars=250, tbl_cols=20):
        print(pl.DataFrame(rows))
    # Which box features matter: drop-one-group on the pooled WR+RB+TE model
    a, b = tr.filter(c("position") != "QB"), te.filter(c("position") != "QB")
    y = b["share"].to_numpy()
    full, _ = fit(a, b, [*SATURDAY, *BOX_FEATURES], "share")
    groups = {
        "usage (targets, carries, receptions, target share)": ["targets", "target_share",
                                                                "receptions", "carries"],
        "yards and fantasy points": ["receiving_yards", "rushing_yards", "fantasy_points_ppr"],
        "snap counts and team pace": ["offense_snaps", "team_snaps"],
        "special teams share": ["st_pct"],
        "passing (attempts, completions, sacks)": ["attempts", "completions", "passing_yards",
                                                   "sacks_suffered"],
    }  # fmt: skip
    print("\n   RB/WR/TE pooled: R2 lost when a group is removed (full model "
          f"{r2(y, full):.3f})")
    for name, xs in groups.items():
        drop = {f"{x}_{n}" for x in xs for n in (3, 8)}
        cols = [x for x in [*SATURDAY, *BOX_FEATURES] if x not in drop]
        p, _ = fit(a, b, cols, "share")
        print(f"   {name:<52} {r2(y, full) - r2(y, p):+.4f}")
    for name, cols in [("efficiency (EPA/play, yards/touch)", EFFICIENCY),
                       ("age, experience, draft slot", ["age", "exp", "draft"])]:  # fmt: skip
        p, _ = fit(a, b, [x for x in [*SATURDAY, *BOX_FEATURES] if x not in cols], "share")
        print(f"   {name:<52} {r2(y, full) - r2(y, p):+.4f}")


def horizons(df):
    tr, te = prep(with_horizons(df))
    cols = [*SATURDAY, *BOX_FEATURES]
    print("\n== Q2. Longer horizons: average share over the window, R2 on 2021-2024")
    rows = []
    for pos in POS:
        for name in HORIZONS:
            ycol = f"y_{name}"
            a = tr.filter((c("position") == pos) & c(ycol).is_not_null())
            b = te.filter((c("position") == pos) & c(ycol).is_not_null())
            y = b[ycol].to_numpy()
            p, _ = fit(a, b, cols, ycol)
            rows.append({"position": pos, "horizon": name, "rows": b.height,
                         "sd of outcome": y.std() * 100,
                         "R2 last game": r2(y, b["prev"].to_numpy()),
                         "R2 avg3": r2(y, b["avg3"].to_numpy()),
                         "R2 season avg": r2(y, b["season_avg_f"].to_numpy()),
                         "R2 model": r2(y, p),
                         "MAE model": np.abs(y - p).mean() * 100})  # fmt: skip
    with pl.Config(float_precision=3, tbl_width_chars=250, tbl_cols=20, tbl_rows=40):
        print(pl.DataFrame(rows))


if __name__ == "__main__":
    df = with_box(frame())
    print(f"rows {df.height:,}")
    box_value(df)
    horizons(df)
