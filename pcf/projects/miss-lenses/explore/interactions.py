"""Spot-check (CEO, 2026-11-03): do pairs of pre-game conditions miss differently from what each
condition alone says? Run from pcf/: .venv/Scripts/python.exe projects/miss-lenses/explore/interactions.py

For each pair of common pre-game conditions A and B, on each model's held-out player-games:
    miss (centred within position) ~ A + B + A×B
The A×B coefficient is the extra miss when both hold, beyond adding up A and B. A pair counts only
if it clears a Bonferroni bar over all the pairs tested (90% for the whole family) and has the same
sign in even and odd seasons.
"""

from itertools import combinations

import numpy as np
import polars as pl
from scipy.stats import norm

from pcf.config import get_config
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.validation.backtest import targets
from pcf.validation.misses import lens_frame

c = pl.col
RUNS = {"lasso": "952ac9a00013488e9a50234dcc84554c", "ecr": "d2c338c7ece64eada6de0874beb85d11"}
MIN_BOTH = 150
FAMILY = 0.10
CONDITIONS = [
    "tag_rookie", "tag_new_team", "tag_revenge_game", "tag_first_game_back",
    "tag_active_while_questionable", "tag_primetime", "tag_short_week", "tag_off_bye",
    "tag_divisional", "tag_home_underdog", "tag_big_favorite", "tag_trap_game",
    "tag_backup_qb_start", "opp_backup_qb", "home", "teammate_out", "starter", "top_third",
]  # fmt: skip


def base(variant: str, gw: Gateway) -> pl.DataFrame:
    out = get_config().zone("outputs") / "baselines" / variant / RUNS[variant]
    h = pl.read_parquet(out / "history.parquet")
    exp = find("baselines", variant)()
    y = targets(exp, gw).select(*exp.keys(), "y")
    df = h.join(y, on=exp.keys()).join(lens_frame(gw.source), on=exp.keys())
    seasons = sorted(df["season"].unique().to_list())
    inj = load("player_game", parts=["injury"], seasons=seasons)
    out_ = (
        inj.filter(c("report_status") == "Out")
        .group_by("game_id", "team", "position")
        .agg(teammate_out=pl.lit(True))
    )
    tg = load("team_game", parts=["schedule", "tags"], seasons=seasons)
    home = tg.select("game_id", "team", "home")
    opp = tg.select("game_id", team="opponent", opp_backup_qb="tag_backup_qb_start")
    return (
        df.join(out_, on=["game_id", "team", "position"], how="left")
        .join(home, on=["game_id", "team"], how="left")
        .join(opp, on=["game_id", "team"], how="left")
        .with_columns(
            miss=c("y") - c("mean"),
            teammate_out=c("teammate_out").fill_null(False),
            starter=c("depth") == 1,
            # Where the model's own projection sits in its position that week
            top_third=c("mean").rank(descending=True).over("season", "week", "position")
            <= c("mean").count().over("season", "week", "position") / 3,
        )
        .with_columns(miss=c("miss") - c("miss").mean().over("position"))
    )


def ols(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if np.linalg.matrix_rank(X) < X.shape[1]:  # one condition implies the other (trap ⊂ favorite)
        return np.full(X.shape[1], np.nan), np.full(X.shape[1], np.nan)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    cov = np.linalg.inv(X.T @ X) * (resid @ resid) / (len(y) - X.shape[1])
    return beta, np.sqrt(np.diag(cov))


def pairs(df: pl.DataFrame, variant: str) -> pl.DataFrame:
    conds = [x for x in CONDITIONS if x in df.columns]
    d = df.select("season", "miss", *[c(x).cast(pl.Boolean).fill_null(False) for x in conds])
    rows = []
    for a, b in combinations(conds, 2):
        both = d[a] & d[b]
        if both.sum() < MIN_BOTH:
            continue
        res = {"a": a, "b": b, "rows_both": int(both.sum())}
        for name, sub in [("all", d), ("even", d.filter(c("season") % 2 == 0)),
                          ("odd", d.filter(c("season") % 2 == 1))]:  # fmt: skip
            A, B = sub[a].to_numpy().astype(float), sub[b].to_numpy().astype(float)
            X = np.column_stack([np.ones(len(A)), A, B, A * B])
            beta, se = ols(sub["miss"].to_numpy(), X)
            res[f"inter_{name}"], res[f"z_{name}"] = beta[3], beta[3] / se[3]
            if name == "all":
                res["miss_both"] = float(sub.filter(both)["miss"].mean())
                res["a_alone"], res["b_alone"] = beta[1], beta[2]
        rows.append(res)
    t = pl.DataFrame(rows).drop_nans("z_all")
    bar = norm.ppf(1 - FAMILY / 2 / t.height)
    t = t.with_columns(
        survives=(c("z_all").abs() > bar) & (c("inter_even").sign() == c("inter_odd").sign())
    ).sort(c("z_all").abs(), descending=True)
    print(f"\n== {variant}: {df.height:,} player-games, {t.height} pairs tested, "
          f"Bonferroni |z| > {bar:.2f}; {t['survives'].sum()} survive")  # fmt: skip
    with pl.Config(tbl_rows=12, tbl_cols=12, float_precision=2, tbl_width_chars=220,
                   fmt_str_lengths=30):  # fmt: skip
        print(t.select("a", "b", "rows_both", "a_alone", "b_alone", "inter_all", "z_all",
                       "inter_even", "inter_odd", "miss_both", "survives").head(12))  # fmt: skip
    return t


def singles(df: pl.DataFrame, variant: str) -> None:
    conds = [x for x in CONDITIONS if x in df.columns]
    rows = []
    for a in conds:
        m = df.filter(c(a).cast(pl.Boolean).fill_null(False))
        if m.height < MIN_BOTH:
            continue
        se = df["miss"].std() / np.sqrt(m.height)
        rows.append({"condition": a, "rows": m.height, "miss": m["miss"].mean(),
                     "z": m["miss"].mean() / se})  # fmt: skip
    with pl.Config(tbl_rows=20, float_precision=2):
        print(f"   {variant}: single conditions (miss vs the model's average)")
        print(pl.DataFrame(rows).sort(c("z").abs(), descending=True))


if __name__ == "__main__":
    gw = Gateway()
    for v in RUNS:
        df = base(v, gw)
        singles(df, v)
        pairs(df, v)
