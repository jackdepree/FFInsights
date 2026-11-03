"""Exploration for miss-lenses: which tags and categories explain the most of the baselines'
misses? Run from pcf/: .venv/Scripts/python.exe projects/miss-lenses/explore/profile_misses.py

For each lens (a way to split player-games into groups), on the walk-forward rows:
- bias: the share of the squared miss that a per-group correction removes, cross-fitted (group
  means from even seasons applied to odd seasons and back), so noise can't flatter a lens;
- spread: the same for the size of the miss (|actual - predicted|): where misses are bigger;
- the group with the largest average miss (200+ rows), with a 90% interval resampled by week.
"""

from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.tables.store import load

c = pl.col
OUT = get_config().zone("outputs") / "baselines"
RUNS = {"lasso": "952ac9a00013488e9a50234dcc84554c", "ecr": "d2c338c7ece64eada6de0874beb85d11"}
MIN_ROWS = 200
rng = np.random.default_rng(0)


def history(variant: str) -> pl.DataFrame:
    h = pl.read_parquet(OUT / variant / RUNS[variant] / "history.parquet")
    return h.select("gsis_id", "game_id", "mean", "q10", "q90")


def frame(seasons: list[int]) -> pl.DataFrame:
    keys = ["gsis_id", "game_id"]
    pg = load(
        "player_game",
        parts=["stats", "game_status", "injury", "depth", "tags", "tags_result", "snaps", "ecr"],
        seasons=seasons,
    )
    tg = load("team_game", parts=["tags", "tags_result"], seasons=seasons)
    res = load("game", parts=["result"], seasons=seasons).select(
        "game_id", "home_team", "home_score", "away_score"
    )
    team = tg.select(
        "game_id", "team", "home", "kickoff",
        *[x for x in tg.columns if x.startswith("tag_")],
    )  # fmt: skip
    opp = tg.select(
        "game_id", team="opponent", opp_backup_qb=c("tag_backup_qb_start")
    )
    # A same-position teammate listed Out (role may open up)
    out = (
        pg.filter(c("report_status") == "Out")
        .group_by("game_id", "team", "position")
        .agg(teammate_out=pl.len())
    )
    df = (
        pg.filter(c("fantasy_points_ppr").is_not_null() & c("stats_known_at").is_not_null())
        .join(team, on=["game_id", "team"], how="left")
        .join(opp, on=["game_id", "team"], how="left")
        .join(out, on=["game_id", "team", "position"], how="left")
        .join(res, on="game_id", how="left")
    )
    margin = pl.when(c("team") == c("home_team")).then(
        c("home_score") - c("away_score")
    ).otherwise(c("away_score") - c("home_score"))
    pts = pl.when(c("team") == c("home_team")).then(c("home_score")).otherwise(c("away_score"))
    age = (c("kickoff").dt.date() - c("birth_date").cast(pl.Date)).dt.total_days() / 365.25
    return df.with_columns(
        y=c("fantasy_points_ppr"),
        week_band=pl.when(c("week") == 1).then(pl.lit("1"))
        .when(c("week") <= 4).then(pl.lit("2-4"))
        .when(c("week") <= 9).then(pl.lit("5-9"))
        .when(c("week") <= 14).then(pl.lit("10-14"))
        .otherwise(pl.lit("15+")),
        experience=pl.when(c("years_exp") == 0).then(pl.lit("0"))
        .when(c("years_exp") == 1).then(pl.lit("1"))
        .when(c("years_exp") <= 4).then(pl.lit("2-4"))
        .when(c("years_exp") <= 8).then(pl.lit("5-8"))
        .otherwise(pl.lit("9+")),
        age_band=(age // 3 * 3).clip(21, 33).cast(pl.Int32).cast(pl.String),
        depth_band=c("depth").clip(1, 3).cast(pl.Int32).cast(pl.String).fill_null("unlisted"),
        injury_report=c("report_status").fill_null("not listed"),
        teammate_out=c("teammate_out").is_not_null(),
        # After the game (diagnostic: they explain misses but can't be features)
        snap_share=pl.when(c("offense_pct") < 0.25).then(pl.lit("<25%"))
        .when(c("offense_pct") < 0.5).then(pl.lit("25-50%"))
        .when(c("offense_pct") < 0.75).then(pl.lit("50-75%"))
        .when(c("offense_pct").is_not_null()).then(pl.lit("75%+")),
        team_margin=pl.when(margin >= 14).then(pl.lit("won by 14+"))
        .when(margin <= -14).then(pl.lit("lost by 14+"))
        .otherwise(pl.lit("within 13")),
        team_points=pl.when(pts < 17).then(pl.lit("<17"))
        .when(pts < 24).then(pl.lit("17-23"))
        .when(pts < 31).then(pl.lit("24-30"))
        .otherwise(pl.lit("31+")),
    ).select(*keys, "week", "y", *LENSES_BEFORE, *LENSES_AFTER, "ecr_sd",
             "ecr_rank")  # fmt: skip


LENSES_BEFORE = [
    "position", "week_band", "season", "experience", "age_band", "depth_band", "injury_report",
    "teammate_out", "home", "tag_new_team", "tag_revenge_game", "tag_first_game_back",
    "tag_active_while_questionable", "tag_primetime", "tag_short_week", "tag_off_bye",
    "tag_divisional", "tag_home_underdog", "tag_big_favorite", "tag_trap_game",
    "tag_backup_qb_start", "opp_backup_qb",
]  # fmt: skip
LENSES_AFTER = ["snap_share", "team_margin", "team_points", "tag_weather_game",
                "tag_positive_cpoe_game"]  # fmt: skip


def crossfit_share(df: pl.DataFrame, lens: str, col: str) -> float:
    """Share of the squared deviation of `col` removed by group means fitted on the other
    half of the seasons (by position too, so a lens isn't credited for position)."""
    d = df.drop_nulls(lens).with_columns(half=c("season") % 2)
    by = list(dict.fromkeys(["position", lens]))
    base = d.with_columns(m0=c(col).mean().over("position", "half"))
    means = base.group_by(*by, "half").agg(g=(c(col) - c("m0")).mean(), n=pl.len())
    other = means.with_columns(half=1 - c("half")).filter(c("n") >= 30)
    j = base.join(other.drop("n"), on=[*by, "half"], how="left").with_columns(
        g=c("g").fill_null(0.0)
    )
    before = ((j[col] - j["m0"]) ** 2).sum()
    after = ((j[col] - j["m0"] - j["g"]) ** 2).sum()
    return float(1 - after / before)


def top_group(df: pl.DataFrame, lens: str) -> tuple:
    d = df.drop_nulls(lens)
    g = d.group_by(lens).agg(n=pl.len(), m=c("r").mean()).filter(c("n") >= MIN_ROWS)
    if g.is_empty():
        return (None, 0, np.nan, np.nan, np.nan)
    best = g.sort(c("m").abs(), descending=True).row(0, named=True)
    rows = d.filter(c(lens) == best[lens]).group_by("season", "week").agg(
        s=c("r").sum(), n=pl.len()
    )
    s, n = rows["s"].to_numpy(), rows["n"].to_numpy()
    w = rng.multinomial(len(s), np.ones(len(s)) / len(s), size=1000)
    boot = (w @ s) / (w @ n)
    lo, hi = np.quantile(boot, [0.05, 0.95])
    return (best[lens], best["n"], best["m"], lo, hi)


def profile(variant: str, seasons: list[int]) -> pl.DataFrame:
    df = history(variant).join(frame(seasons), on=["gsis_id", "game_id"])
    df = df.with_columns(r=c("y") - c("mean"), a=(c("y") - c("mean")).abs())
    print(f"\n== {variant}: {df.height:,} player-games, {seasons[0]}-{seasons[-1]}")
    out = []
    for lens in LENSES_BEFORE + LENSES_AFTER:
        if df[lens].null_count() == df.height:
            continue
        d = df.with_columns(_g=c(lens).cast(pl.String))
        grp, n, m, lo, hi = top_group(d, "_g")
        out.append({
            "lens": lens,
            "when": "before" if lens in LENSES_BEFORE else "after",
            "bias_pct": 100 * crossfit_share(d, "_g", "r"),
            "spread_pct": 100 * crossfit_share(d, "_g", "a"),
            "top_group": grp, "rows": n, "avg_miss": m, "lo": lo, "hi": hi,
        })  # fmt: skip
    t = pl.DataFrame(out).sort("bias_pct", descending=True)
    with pl.Config(tbl_rows=40, tbl_cols=12, float_precision=2, tbl_width_chars=200):
        print(t)
    return df


def ideas(ecr: pl.DataFrame, seasons: list[int]) -> None:
    # I1: does ECR's expert spread say where outcomes are wider?
    d = ecr.drop_nulls("ecr_sd").with_columns(
        sd_band=c("ecr_sd").qcut(4, labels=["low", "mid-low", "mid-high", "high"])
        .over("position")
    )  # fmt: skip
    i1 = d.group_by("position", "sd_band").agg(
        n=pl.len(),
        inside=((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean() * 100,
        mae=c("a").mean(),
    ).sort("position", "sd_band")
    print("\n== I1: ECR coverage and MAE by expert-spread band (per position quartiles)")
    with pl.Config(tbl_rows=20, float_precision=1):
        print(i1)
    # I1 again, holding the rank fixed: experts disagree more lower down the ranks
    d2 = d.with_columns(rank_band=pl.when(c("ecr_rank") <= 12).then(pl.lit("1-12"))
                        .when(c("ecr_rank") <= 24).then(pl.lit("13-24")).otherwise(pl.lit("25+")))
    i1b = d2.group_by("rank_band", "sd_band").agg(
        n=pl.len(), inside=((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean() * 100
    ).sort("rank_band", "sd_band")
    print("   coverage by rank band and spread band")
    with pl.Config(tbl_rows=20, float_precision=1):
        print(i1b)

    # I2: once the season-so-far average is known, do the last 4 games add anything?
    roll = pl.read_parquet(OUT / "rolling4" / "ee8cd336323a4b6a8606d66620c89a87" / "history.parquet")
    sea = pl.read_parquet(OUT / "season" / "3e6ce7e70f5d447490fba59764db4b4c" / "history.parquet")
    j = (
        roll.select("gsis_id", "game_id", last4="mean")
        .join(sea.select("gsis_id", "game_id", season_avg="mean"), on=["gsis_id", "game_id"])
        .join(frame(list(range(2016, 2025))).select("gsis_id", "game_id", "season", "week",
                                                    "position", "y"),
              on=["gsis_id", "game_id"])
        .filter(c("week") >= 5)  # both averages are about the same before week 5
        .drop_nulls()
    )  # fmt: skip
    train, test = j.filter(c("season") <= 2020), j.filter(c("season") > 2020)
    print("\n== I2: weeks 5+, fit 2016-2020, scored 2021-2024 (MAE)")
    for pos in ["QB", "RB", "WR", "TE"]:
        tr, te = train.filter(c("position") == pos), test.filter(c("position") == pos)
        res = {}
        for name, cols in {"season": ["season_avg"], "last4": ["last4"],
                           "both": ["season_avg", "last4"]}.items():  # fmt: skip
            X = np.column_stack([np.ones(tr.height), *[tr[x].to_numpy() for x in cols]])
            beta = np.linalg.lstsq(X, tr["y"].to_numpy(), rcond=None)[0]
            Xt = np.column_stack([np.ones(te.height), *[te[x].to_numpy() for x in cols]])
            res[name] = (np.abs(te["y"].to_numpy() - Xt @ beta).mean(), beta)
        b = res["both"][1]
        print(f"   {pos}: season {res['season'][0]:.3f} · last4 {res['last4'][0]:.3f} · both "
              f"{res['both'][0]:.3f} (weights: season {b[1]:.2f}, last4 {b[2]:.2f}) n={te.height}")

    # I3: does ECR miss more when a role just changed?
    print("\n== I3: ECR's misses when a role changes (avg miss, MAE, rows)")
    for lens in ["teammate_out", "tag_first_game_back", "tag_new_team", "tag_backup_qb_start",
                 "opp_backup_qb", "injury_report"]:  # fmt: skip
        g = ecr.drop_nulls(lens).group_by("position", lens).agg(
            n=pl.len(), avg_miss=c("r").mean(), mae=c("a").mean()
        ).sort("position", lens)
        with pl.Config(tbl_rows=30, float_precision=2):
            print(lens)
            print(g)


if __name__ == "__main__":
    lasso = profile("lasso", list(range(2016, 2025)))
    ecr = profile("ecr", [2022, 2023, 2024])
    ideas(ecr, [2022, 2023, 2024])
