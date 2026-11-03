"""Exploration for participation: is a player's share of offensive snaps predictable before
kickoff, and would knowing it fix the fantasy baselines' misses?
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/profile_participation.py

Rows: every rostered QB, RB, WR and TE, 2013-2024 (snap counts start in 2013). The outcome is the
share of the team's offensive snaps, 0 when inactive or not on the field. Fit 2013-2020, scored
2021-2024. Two information sets:
- Tuesday: earlier games' shares and this week's depth chart;
- Saturday: plus the week's injury report (game status and practice) and teammates' reports.
"""

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

from pcf.config import get_config
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.validation.backtest import targets

c = pl.col
POS = ["QB", "RB", "WR", "TE"]
SEASONS = list(range(2012, 2025))
TRAIN, TEST = range(2013, 2021), range(2021, 2025)
RUNS = {"lasso": "952ac9a00013488e9a50234dcc84554c", "ecr": "d2c338c7ece64eada6de0874beb85d11"}
STATUS = {"Out": 3, "Doubtful": 2, "Questionable": 1}
PRACTICE = {"Did Not": 2, "Limited": 1, "Full": 0}


def frame() -> pl.DataFrame:
    pg = load(
        "player_game", parts=["game_status", "snaps", "depth", "injury", "tags"], seasons=SEASONS
    ).filter(c("position").is_in(POS))
    sched = load("game", parts=["schedule"], seasons=SEASONS).select("game_id", "kickoff")
    # Game statuses start in 2019; before, a player with no snap-count row didn't play
    active = (
        pl.when(c("status").is_not_null())
        .then(c("status") != "INA")
        .otherwise(c("offense_snaps").is_not_null())
    )
    df = pg.join(sched, on="game_id").with_columns(
        share=pl.when(active).then(c("offense_pct").fill_null(0.0)).otherwise(0.0),
        active=active,
        report=c("report_status").replace_strict(STATUS, default=0, return_dtype=pl.Int8),
        practice=pl.when(c("practice_status").str.starts_with("Did Not")).then(2)
        .when(c("practice_status").str.starts_with("Limited")).then(1)
        .when(c("practice_status").str.starts_with("Full")).then(0)
        .otherwise(None).cast(pl.Int8),
        depth1=(c("depth") == 1), depth2=(c("depth") == 2), depth3=(c("depth") >= 3),
        unlisted=c("depth").is_null(),
    ).sort("gsis_id", "kickoff")  # fmt: skip
    g = ["gsis_id"]
    df = df.with_columns(
        prev=c("share").shift(1).over(g),
        prev_active=c("active").shift(1).over(g).cast(pl.Float64),
        avg3=c("share").shift(1).rolling_mean(3, min_samples=1).over(g),
        avg8=c("share").shift(1).rolling_mean(8, min_samples=1).over(g),
        new_season=c("season") != c("season").shift(1).over(g),
    ).with_columns(
        season_avg=c("share").shift(1).cum_sum().over([*g, "season"])
        / c("share").shift(1).cum_count().over([*g, "season"]),
        games=c("share").cum_count().over([*g, "season"]) - 1,
    )
    # Teammates at the same position: how many listed Out or Doubtful, how much share they had
    out = (
        df.filter(c("report") >= 2)
        .group_by("game_id", "team", "position")
        .agg(mates_out=pl.len(), mates_out_share=c("avg3").fill_null(0).sum())
    )
    df = df.join(out, on=["game_id", "team", "position"], how="left").with_columns(
        mates_out=c("mates_out").fill_null(0) - (c("report") >= 2).cast(pl.Int64),
        mates_out_share=c("mates_out_share").fill_null(0.0)
        - pl.when(c("report") >= 2).then(c("avg3").fill_null(0)).otherwise(0.0),
    )
    return df.filter((c("season") >= 2013) & c("prev").is_not_null())


TUESDAY = ["prev", "prev_active", "avg3", "avg8", "season_avg_f", "games", "new_season_f",
           "depth1", "depth2", "depth3", "unlisted", "depth_mean_f", "tag_new_team_f",
           "tag_rookie_f"]  # fmt: skip
SATURDAY = [*TUESDAY, "report", "practice_f", "practice_null", "mates_out", "mates_out_share",
            "tag_active_while_questionable_unused"]  # fmt: skip


def design(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        season_avg_f=c("season_avg").fill_nan(None).fill_null(c("avg8")),
        new_season_f=c("new_season").cast(pl.Float64),
        depth_mean_f=c("depth_mean").fill_null(5.0),
        tag_new_team_f=c("tag_new_team").fill_null(False).cast(pl.Float64),
        tag_rookie_f=c("tag_rookie").fill_null(False).cast(pl.Float64),
        practice_f=c("practice").fill_null(0).cast(pl.Float64),
        practice_null=c("practice").is_null().cast(pl.Float64),
        tag_active_while_questionable_unused=pl.lit(0.0),
        **{x: c(x).cast(pl.Float64) for x in ["depth1", "depth2", "depth3", "unlisted"]},
    ).with_columns(
        [c(x).cast(pl.Float64).fill_nan(None).fill_null(0.0) for x in SATURDAY]
    )


def mae(a, b) -> float:
    return float(np.abs(np.asarray(a) - np.asarray(b)).mean())


def predictability(df: pl.DataFrame) -> pl.DataFrame:
    d = design(df)
    tr, te = d.filter(c("season").is_in(list(TRAIN))), d.filter(c("season").is_in(list(TEST)))
    print(f"\n== Snap share, fit {TRAIN.start}-{TRAIN.stop - 1} ({tr.height:,}), "
          f"scored {TEST.start}-{TEST.stop - 1} ({te.height:,}); MAE in share points (x100)")  # fmt: skip
    rows, preds = [], {}
    for pos in POS:
        a, b = tr.filter(c("position") == pos), te.filter(c("position") == pos)
        y = b["share"].to_numpy()
        r = {"position": pos, "rows": b.height, "mean": y.mean() * 100,
             "last game": mae(y, b["prev"]) * 100, "avg3": mae(y, b["avg3"]) * 100,
             "season": mae(y, b["season_avg_f"]) * 100}  # fmt: skip
        for name, cols in [("lin Tue", TUESDAY), ("lin Sat", SATURDAY)]:
            m = LinearRegression().fit(a.select(cols).to_numpy(), a["share"].to_numpy())
            r[name] = mae(y, m.predict(b.select(cols).to_numpy()).clip(0, 1)) * 100
        r["R2 avg3"] = 1 - ((y - b["avg3"].to_numpy()) ** 2).mean() / y.var()
        for name, cols in [("gbm Tue", TUESDAY), ("gbm Sat", SATURDAY)]:
            m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=0)
            m.fit(a.select(cols).to_numpy(), a["share"].to_numpy())
            p = m.predict(b.select(cols).to_numpy()).clip(0, 1)
            r[name] = mae(y, p) * 100
            r["R2 " + name] = 1 - ((y - p) ** 2).mean() / y.var()
            preds[(pos, name)] = b.select("gsis_id", "game_id", "avg3", "report",
                                          "mates_out_share").with_columns(
                **{name.replace(" ", "_"): pl.Series(p)}
            )
        rows.append(r)
    with pl.Config(float_precision=2, tbl_width_chars=250, tbl_cols=20):
        print(pl.DataFrame(rows))
    out = []
    for name in ("gbm Tue", "gbm Sat"):
        out.append(pl.concat([preds[(p, name)] for p in POS]))
    return out[0].join(out[1].select("gsis_id", "game_id", "gbm_Sat"), on=["gsis_id", "game_id"])


def availability(df: pl.DataFrame) -> None:
    """Will the player be active? Tuesday vs Saturday information."""
    d = design(df)
    tr, te = d.filter(c("season").is_in(list(TRAIN))), d.filter(c("season").is_in(list(TEST)))
    print("\n== Active or not (all positions): share inactive in test",
          f"{1 - te['active'].mean():.1%}")
    for name, cols in [("Tuesday", TUESDAY), ("Saturday", SATURDAY)]:
        m = LogisticRegression(max_iter=5000, C=0.1).fit(tr.select(cols).to_numpy(), tr["active"])
        p = m.predict_proba(te.select(cols).to_numpy())[:, 1]
        print(f"   {name}: AUC {roc_auc_score(te['active'], p):.3f}, "
              f"Brier {brier_score_loss(te['active'], p):.4f}")


def value(preds: pl.DataFrame) -> None:
    """How much of the fantasy baselines' squared miss a pre-game share fixes, against the
    after-game share's upper bound. Corrections learned on even seasons, applied to odd, and back."""
    gw = Gateway()
    snaps = load("player_game", parts=["snaps", "game_status"], seasons=list(TEST)).select(
        "gsis_id", "game_id", "season", "position",
        actual=pl.when(c("status") == "INA").then(0.0).otherwise(c("offense_pct").fill_null(0.0)),
    )  # fmt: skip
    for variant, run in RUNS.items():
        out = get_config().zone("outputs") / "baselines" / variant / run
        h = pl.read_parquet(out / "history.parquet")
        exp = find("baselines", variant)()
        y = targets(exp, gw).select(*exp.keys(), "y")
        d = (
            h.join(y, on=exp.keys())
            .join(snaps, on=exp.keys())
            .join(preds, on=exp.keys())
            .with_columns(miss=c("y") - c("mean"))
        )
        print(f"\n== {variant}: {d.height:,} player-games {TEST.start}-{TEST.stop - 1}; share of "
              "squared miss removed by a linear correction on the snap share (cross-fitted)")  # fmt: skip
        for name, cols in [("Tuesday prediction", ["gbm_Tue"]),
                           ("Saturday prediction", ["gbm_Sat"]),
                           ("Saturday, with its parts", ["gbm_Sat", "avg3", "report",
                                                         "mates_out_share"]),
                           ("actual (after the game)", ["actual"])]:  # fmt: skip
            print(f"   {name:<24} {crossfit(d, cols):.1%}")


def crossfit(d: pl.DataFrame, cols: list[str]) -> float:
    d = d.with_columns(half=c("season") % 2)
    before = after = 0.0
    for pos in POS:
        for h in (0, 1):
            fit = d.filter((c("position") == pos) & (c("half") != h))
            app = d.filter((c("position") == pos) & (c("half") == h))
            X = lambda f: np.column_stack([f[x].to_numpy() for x in cols] + [f["mean"].to_numpy()])  # noqa: E731
            m = LinearRegression().fit(X(fit), fit["miss"].to_numpy())
            r0 = app["miss"].to_numpy() - fit["miss"].mean()
            r1 = app["miss"].to_numpy() - m.predict(X(app))
            before += (r0**2).sum()
            after += (r1**2).sum()
    return 1 - after / before


if __name__ == "__main__":
    df = frame()
    print(f"rows {df.height:,}; inactive {1 - df['active'].mean():.1%}; "
          f"active with no offensive snap {(df['active'] & (df['share'] == 0)).mean():.1%}")
    with pl.Config(float_precision=3):
        print(df.group_by("position").agg(
            mean=c("share").mean(), zero=(c("share") == 0).mean(),
            over_half=(c("share") >= 0.5).mean(), sd=c("share").std(),
        ).sort("position"))  # fmt: skip
    availability(df)
    preds = predictability(df)
    value(preds)
