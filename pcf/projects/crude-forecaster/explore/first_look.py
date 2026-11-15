# ruff: noqa: E501
"""crude-forecaster, first look (2026-11-15). Discovery only: is there room, and what do the
CEO's hunches H50-H55 look like on a first, rough version of the crude forecaster?

- Rows: every rostered QB, RB, WR and TE in a regular-season game that participation forecast
  (2016-2024; the 2025 vault is left out), and every team-game.
- Targets: passing yards (QBs), rushing yards (RBs), receiving yards (WRs, TEs, RBs), and a
  team's yards gained (the same number is its opponent's yards allowed).
- Crude inputs, from earlier games only: averages (season so far, last 4, last season), the
  season's running total, last 4 minus the season, the spread, of yards; averages of attempts,
  first downs and touchdowns; yards per attempt.
- Model: a lasso and gradient-boosted trees, averaged (scikit-learn's trees: xgboost isn't
  installed). Walk forward by season: fit on 2016..s-1, forecast s, for s = 2019..2024.
- Experts: saved walk-forward outputs (participation, Elo, team efficiency, pace, schemes).
  Their moments differ by a few days (Tuesday or Saturday runs): fine for a first look.
- Not through the gateway or the harness: nothing here is a model beating anything.

Run from pcf/:  python projects/crude-forecaster/explore/first_look.py > projects/crude-forecaster/explore/first_look.txt
"""

from __future__ import annotations

import itertools
import math
import sys
import time

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Lasso
from sklearn.preprocessing import StandardScaler

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
FIRST, LAST = 2014, 2024  # features from 2014; modelling rows 2016-2024
TEST = range(2019, 2025)
DRAWS = 2000
RNG = np.random.default_rng(get_config().seed)
T0 = time.time()

STATS = {
    "pass": ("passing_yards", "attempts", "passing_first_downs", "passing_tds", ("QB",), 15),
    "rush": ("rushing_yards", "carries", "rushing_first_downs", "rushing_tds", ("RB",), 8),
    "rec": ("receiving_yards", "targets", "receiving_first_downs", "receiving_tds",
            ("WR", "TE", "RB"), 4),
}  # fmt: skip


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- crude inputs
def crude(df: pl.DataFrame, unit: list[str], stats: dict[str, str]) -> pl.DataFrame:
    """Per unit (a player, or a team's offense or defense), from earlier games only. `stats`:
    short name -> column; "y" is the yards, "vol" the attempts."""
    df = df.sort(*unit, "season", "week")
    us = [*unit, "season"]
    out = []
    for k, col in stats.items():
        x = c(col).fill_null(0.0).cast(pl.Float64)
        n_s = x.cum_count().over(us) - 1
        sum_s = x.cum_sum().over(us) - x
        prev = [x.shift(i).over(unit) for i in range(1, 5)]
        n4 = sum(p.is_not_null().cast(pl.Float64) for p in prev)
        out += [
            pl.when(n_s > 0).then(sum_s / n_s).alias(f"{k}_s"),
            pl.when(n4 > 0).then(sum(p.fill_null(0.0) for p in prev) / n4).alias(f"{k}_l4"),
        ]
        if k == "y":
            sq_s = (x**2).cum_sum().over(us) - x**2
            var = (sq_s - sum_s**2 / n_s) / (n_s - 1)
            out += [
                sum_s.alias("y_cum"),
                pl.when(n_s >= 2).then(var.clip(0).sqrt()).alias("y_sd"),
                n_s.cast(pl.Float64).alias("n_games"),
            ]
    df = df.with_columns(out)
    last = df.group_by(us).agg(
        *[c(col).fill_null(0.0).mean().alias(f"{k}_ls") for k, col in stats.items()],
        c(stats["y"]).fill_null(0.0).std().alias("y_ls_sd"),
        (c(stats["y"]).fill_null(0.0).sum() / c(stats["vol"]).fill_null(0.0).sum()).alias("ypa_ls"),
    ).with_columns(c("season") + 1)  # fmt: skip
    df = df.join(last, on=us, how="left")
    ysum = c(stats["y"]).fill_null(0.0).cum_sum().over(us) - c(stats["y"]).fill_null(0.0)
    vsum = c(stats["vol"]).fill_null(0.0).cum_sum().over(us) - c(stats["vol"]).fill_null(0.0)
    df = df.with_columns(
        ypa_s=pl.when(vsum > 0).then(ysum / vsum),
        y_trend=c("y_l4") - c("y_s"),
        has_ls=c("y_ls").is_not_null().cast(pl.Float64),
    )
    # week 1: the season so far is last season
    fills = [c(f"{k}_s").fill_null(c(f"{k}_ls")) for k in stats]
    return df.with_columns(*fills, c("ypa_s").fill_null(c("ypa_ls")), c("y_sd").fill_null(c("y_ls_sd")))


def groups(stats=("y", "vol", "fd", "td")) -> dict[str, list[str]]:
    g = {k: [f"{k}_s", f"{k}_l4", f"{k}_ls"] for k in stats}
    g["y"] += ["y_cum", "y_trend", "y_sd", "y_ls_sd"]
    g["other"] = ["n_games", "has_ls", "ypa_s", "ypa_ls"]
    return g


# ---------------------------------------------------------------- experts
def latest(project: str, variant: str) -> pl.DataFrame:
    folder = get_config().zone("outputs") / project / variant
    runs = sorted(
        (p for p in folder.iterdir() if (p / "history.parquet").exists()),
        key=lambda p: p.stat().st_mtime,
    )
    for run in reversed(runs):
        h = pl.read_parquet(run / "history.parquet")
        if h["game_id"].min() < str(LAST):
            return h
    raise FileNotFoundError(f"{project}/{variant}")


def team_experts(sched: pl.DataFrame) -> tuple[pl.DataFrame, dict[str, list[str]]]:
    """One row per team-game with each expert's forecast inputs, own side and opponent's."""
    base = sched.select("game_id", "team", "opponent", "home")
    feats: dict[str, list[str]] = {}
    m, t = latest("elo", "margin"), latest("elo", "total").select("game_id", exp_total="mean")
    m = m.join(t, on="game_id", how="left")
    home = m.select(
        "game_id", home=pl.lit(True), elo_own=c("home_rating"), elo_opp=c("away_rating"),
        elo_own_off=c("home_offense"), elo_opp_def=c("away_defense"), elo_margin=c("mean"),
        elo_total=c("exp_total"),
    )  # fmt: skip
    away = m.select(
        "game_id", home=pl.lit(False), elo_own=c("away_rating"), elo_opp=c("home_rating"),
        elo_own_off=c("away_offense"), elo_opp_def=c("home_defense"), elo_margin=-c("mean"),
        elo_total=c("exp_total"),
    )  # fmt: skip
    elo = pl.concat([home, away])
    feats["elo"] = [x for x in elo.columns if x.startswith("elo_")]
    base = base.join(elo, on=["game_id", "home"], how="left")

    te = latest("team-efficiency", "off_next3_ridge")
    own = te.select("game_id", "team", te_off=c("off_ridge"), te_off_pass=c("off_pass"),
                    te_off_run=c("off_run"))  # fmt: skip
    opp = te.select("game_id", opponent=c("team"), te_opp_def=c("def_ridge"),
                    te_opp_def_pass=c("def_pass"), te_opp_def_run=c("def_run"))  # fmt: skip
    base = base.join(own, on=["game_id", "team"], how="left").join(
        opp, on=["game_id", "opponent"], how="left"
    )
    feats["efficiency"] = [x for x in base.columns if x.startswith("te_")]

    feats["pace"] = []
    for v in ("plays_full", "dropbacks_full", "runs_full", "proe_shrunk", "pace_oe_shrunk"):
        h = latest("pace", v).select("game_id", "team", c("mean").alias(f"pace_{v}"))
        base = base.join(h, on=["game_id", "team"], how="left")
        feats["pace"].append(f"pace_{v}")
    h = latest("pace", "plays_full").select("game_id", opponent=c("team"), pace_opp_plays=c("mean"))
    base = base.join(h, on=["game_id", "opponent"], how="left")
    feats["pace"].append("pace_opp_plays")

    feats["schemes"] = []
    for v in ("shotgun_shrunk", "tempo_shrunk", "depth_shrunk", "pass_oe_shrunk"):
        h = latest("schemes-v2", v).select("game_id", "team", c("mean").alias(f"sch_{v}"))
        base = base.join(h, on=["game_id", "team"], how="left")
        feats["schemes"].append(f"sch_{v}")
    return base.drop("opponent", "home"), feats


# ---------------------------------------------------------------- the model
def _alpha(xtr, ytr, season_tr) -> float:
    """The lasso's penalty, picked on the last training season."""
    last = season_tr.max()
    a, b = season_tr < last, season_tr == last
    best, best_a = math.inf, 0.01
    for alpha in (0.003, 0.01, 0.03, 0.1, 0.3):
        m = Lasso(alpha=alpha * ytr.std(), max_iter=5000).fit(xtr[a], ytr[a])
        err = ((m.predict(xtr[b]) - ytr[b]) ** 2).mean()
        if err < best:
            best, best_a = err, alpha
    return best_a * ytr.std()


def walk(df: pl.DataFrame, feats: list[str], y: str = "y", seed: int = 0, parts: bool = False):
    """Walk-forward forecasts for the TEST seasons, in the frame's row order (NaN elsewhere)."""
    x = df.select(feats).to_numpy().astype(float)
    yy = df[y].to_numpy().astype(float)
    season = df["season"].to_numpy()
    out = {k: np.full(len(yy), np.nan) for k in ("mix", "lasso", "trees")}
    for s in TEST:
        tr, te = (season < s) & (season >= 2016), season == s
        if te.sum() == 0:
            continue
        xl = np.nan_to_num(x, nan=0.0)
        sc = StandardScaler().fit(xl[tr])
        xtr, xte = sc.transform(xl[tr]), sc.transform(xl[te])
        lasso = Lasso(alpha=_alpha(xtr, yy[tr], season[tr]), max_iter=5000).fit(xtr, yy[tr])
        trees = HistGradientBoostingRegressor(
            max_iter=150, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=40,
            l2_regularization=1.0, early_stopping=False, random_state=seed,
        ).fit(x[tr], yy[tr])  # fmt: skip
        out["lasso"][te], out["trees"][te] = lasso.predict(xte), trees.predict(x[te])
        out["mix"][te] = (out["lasso"][te] + out["trees"][te]) / 2
    return out if parts else out["mix"]


def gain(df: pl.DataFrame, new: np.ndarray, base: np.ndarray, y: str = "y") -> tuple[float, float, float]:
    """Share of the base's squared error the new forecast removes, with a 90% interval from
    resampling whole weeks. Positive is better."""
    yy = df[y].to_numpy().astype(float)
    ok = ~np.isnan(new) & ~np.isnan(base)
    d = pl.DataFrame({
        "w": (df["season"].to_numpy() * 100 + df["week"].to_numpy())[ok],
        "a": ((new - yy) ** 2)[ok], "b": ((base - yy) ** 2)[ok],
    }).group_by("w").agg(c("a").sum(), c("b").sum())  # fmt: skip
    a, b = d["a"].to_numpy(), d["b"].to_numpy()
    draws = RNG.multinomial(len(a), np.full(len(a), 1 / len(a)), size=DRAWS)
    boot = 1 - (draws @ a) / (draws @ b)
    lo, hi = np.quantile(boot, [0.05, 0.95])
    return float(1 - a.sum() / b.sum()), float(lo), float(hi)


def pct(g) -> str:
    return f"{100 * g[0]:+6.2f}%  (90% {100 * g[1]:+.2f} to {100 * g[2]:+.2f})"


def shapley(df: pl.DataFrame, base_feats: list[str], experts: dict[str, list[str]], tag: str):
    """Each expert's held-out gain alone, and its Shapley share over every order of adding them."""
    names = list(experts)
    preds = {}
    for r in range(len(names) + 1):
        for combo in itertools.combinations(names, r):
            fs = base_feats + [f for n in combo for f in experts[n]]
            preds[frozenset(combo)] = walk(df, fs)
        log(tag, "combos of size", r, "done")
    base = preds[frozenset()]
    n = len(names)
    print(f"  all experts together: {pct(gain(df, preds[frozenset(names)], base))}")
    print(f"  {'expert':<14}{'added alone':<44}{'Shapley share (of squared error removed)'}")
    for i in names:
        # the Shapley forecast-difference, as one pair of error vectors per coalition
        share_new, share_base, wts = [], [], []
        for r in range(n):
            for combo in itertools.combinations([x for x in names if x != i], r):
                w = math.factorial(r) * math.factorial(n - r - 1) / math.factorial(n)
                share_new.append(preds[frozenset(combo) | {i}])
                share_base.append(preds[frozenset(combo)])
                wts.append(w)
        yy = df["y"].to_numpy().astype(float)
        e_new = sum(w * (p - yy) ** 2 for w, p in zip(wts, share_new, strict=True))
        e_old = sum(w * (p - yy) ** 2 for w, p in zip(wts, share_base, strict=True))
        e_crude = (base - yy) ** 2
        ok = ~np.isnan(e_crude)
        d = pl.DataFrame({
            "w": (df["season"].to_numpy() * 100 + df["week"].to_numpy())[ok],
            "d": (e_old - e_new)[ok], "b": e_crude[ok],
        }).group_by("w").agg(c("d").sum(), c("b").sum())  # fmt: skip
        dd, bb = d["d"].to_numpy(), d["b"].to_numpy()
        draws = RNG.multinomial(len(dd), np.full(len(dd), 1 / len(dd)), size=DRAWS)
        boot = (draws @ dd) / (draws @ bb)
        sh = (dd.sum() / bb.sum(), *np.quantile(boot, [0.05, 0.95]))
        print(f"  {i:<14}{pct(gain(df, preds[frozenset({i})], base)):<44}{pct(sh)}")
    return preds


def r2(df: pl.DataFrame, pred: np.ndarray, y: str = "y", by: str | None = None) -> float:
    """Share of the squared error around the test seasons' mean (per `by` group) removed."""
    yy = df[y].to_numpy().astype(float)
    ok = ~np.isnan(pred)
    if by is None:
        m = np.full(len(yy), yy[ok].mean())
    else:
        m = df.with_columns(_ok=pl.Series(ok)).with_columns(
            m=c(y).filter(c("_ok")).mean().over(by)
        )["m"].to_numpy()
    return float(1 - ((pred - yy)[ok] ** 2).sum() / ((m - yy)[ok] ** 2).sum())


def fisher(r: float, n: int) -> str:
    if n < 5 or abs(r) >= 1:
        return f"{r:+.2f}"
    z, se = math.atanh(r), 1 / math.sqrt(n - 3)
    return f"{r:+.2f} (90% {math.tanh(z - 1.645 * se):+.2f} to {math.tanh(z + 1.645 * se):+.2f}, n {n})"


# ---------------------------------------------------------------- frames
def player_frame(src, key: str, tex: pl.DataFrame) -> pl.DataFrame:
    ycol, vcol, fcol, tcol, positions, _ = STATS[key]
    roster = src.part("player_game", "roster").filter(
        c("season").is_between(FIRST, LAST) & c("position").is_in(list(positions))
    )
    roster = roster.select("gsis_id", "game_id", "season", "week", "team", "position")
    stats = src.part("player_game", "stats").select("gsis_id", "game_id", ycol, vcol, fcol, tcol)
    snaps = src.part("player_game", "snaps").select("gsis_id", "game_id", "offense_snaps")
    sched = src.part("team_game", "schedule").select("game_id", "team", "game_type")
    df = (
        roster.join(sched, on=["game_id", "team"])
        .filter(c("game_type") == "REG")
        .join(stats, on=["gsis_id", "game_id"], how="left")
        .join(snaps, on=["gsis_id", "game_id"], how="left")
    )
    df = crude(df, ["gsis_id"], {"y": ycol, "vol": vcol, "fd": fcol, "td": tcol})
    df = df.with_columns(
        y=c(ycol).fill_null(0.0).cast(pl.Float64), vol=c(vcol).fill_null(0.0).cast(pl.Float64),
        played=c("offense_snaps").fill_null(0) > 0,
        **{f"pos_{p}": (c("position") == p).cast(pl.Float64) for p in positions},
    )  # fmt: skip
    part = latest("participation", "trees_week").select(
        "gsis_id", "game_id", part_share=c("mean"), part_active=c("p_nonzero")
    )
    return (
        df.join(part, on=["gsis_id", "game_id"])  # the rows participation forecast: 2016 on
        .join(tex, on=["game_id", "team"], how="left")
        .filter(c("season").is_between(2016, LAST))
        .sort("season", "week", "game_id", "gsis_id")
    )


def team_frame(src, tex: pl.DataFrame) -> pl.DataFrame:
    sched = src.part("team_game", "schedule").filter(
        c("season").is_between(FIRST, LAST) & (c("game_type") == "REG")
    ).select("game_id", "team", "opponent", "season", "week")  # fmt: skip
    st = src.part("team_game", "stats").select(
        "game_id", "team",
        yards=(c("passing_yards") + c("rushing_yards")).cast(pl.Float64),
        fd=(c("passing_first_downs") + c("rushing_first_downs")).cast(pl.Float64),
        td=(c("passing_tds") + c("rushing_tds")).cast(pl.Float64),
        plays=(c("attempts") + c("carries") + c("sacks_suffered")).cast(pl.Float64),
    )  # fmt: skip
    g = sched.join(st, on=["game_id", "team"])
    names = {"y": "yards", "vol": "plays", "fd": "fd", "td": "td"}
    off = crude(g, ["team"], names)
    keep = [x for x in off.columns if x not in g.columns]
    off = off.select("game_id", "team", "opponent", "season", "week",
                     *[c(k).alias(f"off_{k}") for k in keep], y=c("yards"))  # fmt: skip
    # what each defense allowed: the same numbers, filed under the opponent
    d = g.select("game_id", "season", "week", team=c("opponent"), yards="yards", fd="fd", td="td",
                 plays="plays")  # fmt: skip
    dfn = crude(d, ["team"], names)
    dfn = dfn.select("game_id", *[c(k).alias(f"def_{k}") for k in keep], opponent=c("team"))
    return (
        off.join(dfn, on=["game_id", "opponent"])
        .join(tex, on=["game_id", "team"], how="left")
        .filter(c("season").is_between(2016, LAST))
        .sort("season", "week", "game_id", "team")
    ), [f"off_{k}" for k in keep], [f"def_{k}" for k in keep]


# ---------------------------------------------------------------- the look
def main() -> None:
    src = Gateway().source
    sched = src.part("team_game", "schedule").select("game_id", "team", "opponent", "home")
    tex, tfeats = team_experts(sched)
    g = groups()
    crude_feats = [f for fs in g.values() for f in fs]
    pexperts = {"participation": ["part_share", "part_active"], **tfeats}
    frames = {k: player_frame(src, k, tex) for k in STATS}
    for k, df in frames.items():
        log(k, df.shape)

    print("crude-forecaster, first look. Regular seasons; forecasts for 2019-2024 from models fit on")
    print("2016 to the season before. 'Removed' = share of squared error removed. Discovery only.\n")

    # ---- 1. the noise ceiling, before anything else
    print("== 1. The noise ceiling (next game)")
    print(f"  {'target':<26}{'rows':>7}{'avg':>8}  {'crude removes':>14}  {'hindsight oracle':>17}"
          f"  {'trees seed noise':>17}")  # fmt: skip
    base_pred, crude_parts = {}, {}
    for k, df in frames.items():
        pos = [x for x in df.columns if x.startswith("pos_")]
        feats = crude_feats + (pos if len(pos) > 1 else [])
        parts = walk(df, feats, parts=True)
        crude_parts[k], base_pred[k] = parts, parts["mix"]
        # hindsight: his average over the season's other games (nothing could know more of him)
        orc = df.with_columns(
            o=(c("y").sum().over("gsis_id", "season") - c("y"))
            / (pl.len().over("gsis_id", "season") - 1)
        )["o"].fill_null(0.0).to_numpy()  # fmt: skip
        orc = np.where(np.isnan(parts["mix"]), np.nan, orc)
        seeds = [r2(df, walk(df, feats, seed=s)) for s in (1, 2, 3)]
        print(f"  {k + ' yards':<26}{int((~np.isnan(parts['mix'])).sum()):>7}"
              f"{df.filter(c('season') >= 2019)['y'].mean():>8.1f}  {100 * r2(df, parts['mix']):>13.1f}%"
              f"  {100 * r2(df, orc):>16.1f}%  {100 * (max(seeds) - min(seeds)):>15.2f} pts")  # fmt: skip
        log("ceiling", k)
    print("  (seed noise: the spread of 'crude removes' over three seeds of the trees.)")

    tdf, off_f, def_f = team_frame(src, tex)
    tparts = walk(tdf, off_f + def_f, parts=True)
    orc = tdf.with_columns(
        o=(c("y").sum().over("team", "season") - c("y")) / (pl.len().over("team", "season") - 1)
    )["o"].to_numpy()
    orc = np.where(np.isnan(tparts["mix"]), np.nan, orc)
    seeds = [r2(tdf, walk(tdf, off_f + def_f, seed=s)) for s in (1, 2, 3)]
    print(f"  {'team yards gained':<26}{int((~np.isnan(tparts['mix'])).sum()):>7}"
          f"{tdf.filter(c('season') >= 2019)['y'].mean():>8.1f}  {100 * r2(tdf, tparts['mix']):>13.1f}%"
          f"  {100 * r2(tdf, orc):>16.1f}%  {100 * (max(seeds) - min(seeds)):>15.2f} pts")  # fmt: skip

    print("\n== 1b. Gained against allowed (team yards, each side's own past only)")
    only_off, only_def = walk(tdf, off_f), walk(tdf, def_f)
    print(f"  the offense's past alone removes {100 * r2(tdf, only_off):.1f}%;"
          f" the defense's past alone {100 * r2(tdf, only_def):.1f}%;"
          f" both {100 * r2(tdf, tparts['mix']):.1f}%")  # fmt: skip

    print("\n== 1c. Lasso, trees and the mix (crude inputs)")
    for k, df in [*frames.items(), ("team", tdf)]:
        p = crude_parts[k] if k != "team" else tparts
        print(f"  {k:<6} lasso {100 * r2(df, p['lasso']):5.1f}%   trees {100 * r2(df, p['trees']):5.1f}%"
              f"   mix {100 * r2(df, p['mix']):5.1f}%")  # fmt: skip

    # ---- 2. H51: how much do past yards and first downs carry?
    print("\n== 2. H51: the share of what the crude model explains that past yards and first downs carry")
    for k, df in frames.items():
        pos = [x for x in df.columns if x.startswith("pos_")]
        pos = pos if len(pos) > 1 else []
        full = r2(df, base_pred[k])
        yo = r2(df, walk(df, g["y"] + pos))
        yf = r2(df, walk(df, g["y"] + g["fd"] + pos))
        print(f"  {k:<6} full {100 * full:5.1f}%   yards only {100 * yo:5.1f}% ({100 * yo / full:.0f}% of full)"
              f"   yards + first downs {100 * yf:5.1f}% ({100 * yf / full:.0f}% of full)")  # fmt: skip
        log("H51", k)

    # ---- 3. H52: which position is easiest?
    print("\n== 3. H52: by position (crude model). 'Typical miss' = mean absolute miss over the average.")
    for k, df in frames.items():
        d = df.with_columns(p=pl.Series(base_pred[k])).filter(c("p").is_not_nan())
        for label, dd in (("all rostered", d), ("played a snap", d.filter(c("played")))):
            for pos in STATS[k][4]:
                e = dd.filter(c("position") == pos)
                if e.height < 500:
                    continue
                yv, pv = e["y"].to_numpy(), e["p"].to_numpy()
                rr = 1 - ((pv - yv) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
                print(f"  {pos} {k:<5} {label:<14} rows {e.height:>6}  removed {100 * rr:5.1f}%"
                      f"  typical miss {np.abs(pv - yv).mean() / yv.mean():.2f} of the average ({yv.mean():.1f} yards)")  # fmt: skip

    # ---- 4. H50 (and methods A and C): each expert alone, and its Shapley share
    print("\n== 4. H50: what each finished expert adds (A: alone; C: Shapley over all orders)")
    for k, df in frames.items():
        pos = [x for x in df.columns if x.startswith("pos_")]
        print(f" {k} yards")
        shapley(df, crude_feats + (pos if len(pos) > 1 else []), pexperts, k)
    print(" team yards gained (no participation: it is a player forecast)")
    shapley(tdf, off_f + def_f, tfeats, "team")

    # ---- 5. H53: volume or efficiency?
    print("\n== 5. H53: do the experts improve volume (attempts) or efficiency (yards per attempt) more?")
    allx = [f for fs in pexperts.values() for f in fs]
    for k, df in frames.items():
        pos = [x for x in df.columns if x.startswith("pos_")]
        feats = crude_feats + (pos if len(pos) > 1 else [])
        vb, vx = walk(df, feats, y="vol"), walk(df, feats + allx, y="vol")
        print(f"  {k:<6} volume:     crude removes {100 * r2(df, vb, 'vol'):5.1f}%;"
              f" all experts add {pct(gain(df, vx, vb, 'vol'))}")  # fmt: skip
        e = df.filter(c("vol") >= STATS[k][5]).with_columns(eff=c("y") / c("vol"))
        eb, ex = walk(e, feats, y="eff"), walk(e, feats + allx, y="eff")
        print(f"  {k:<6} efficiency: crude removes {100 * r2(e, eb, 'eff'):5.1f}%;"
              f" all experts add {pct(gain(e, ex, eb, 'eff'))}   (games with {STATS[k][5]}+ attempts)")  # fmt: skip
        for name, fs in pexperts.items():
            gv = gain(df, walk(df, feats + fs, y="vol"), vb, "vol")
            ge = gain(e, walk(e, feats + fs, y="eff"), eb, "eff")
            print(f"         {name:<14} volume {pct(gv)}   efficiency {pct(ge)}")
        log("H53", k)

    # ---- 6. H54: do recent games carry forward beyond the averages?
    print("\n== 6. H54: recent games (last 4, and last 4 minus the season) beside the other inputs")
    recent = [f for f in crude_feats if f.endswith("_l4") or f == "y_trend"]
    for k, df in frames.items():
        pos = [x for x in df.columns if x.startswith("pos_")]
        pos = pos if len(pos) > 1 else []
        without = walk(df, [f for f in crude_feats if f not in recent] + pos)
        print(f"  {k:<6} recent inputs add {pct(gain(df, base_pred[k], without))}")
    without = walk(tdf, [f for f in off_f + def_f if not (f.endswith("_l4") or f.endswith("y_trend"))])
    print(f"  team   recent inputs add {pct(gain(tdf, tparts['mix'], without))}")

    # ---- 7. H55: is boom-or-bust a trait?
    print("\n== 7. H55: a player's game-to-game spread of yards (games he played)")
    for k, df in frames.items():
        p = df.filter(c("played")).with_columns(odd=c("week") % 2 == 1)
        half = p.group_by("gsis_id", "season", "odd").agg(
            n=pl.len(), m=c("y").mean(), sd=c("y").std()
        ).filter((c("n") >= 5) & (c("m") > 0))  # fmt: skip
        a = half.filter(c("odd")).join(half.filter(~c("odd")), on=["gsis_id", "season"], suffix="_e")
        # the spread with the average taken out: the residual of log sd on log mean
        both = pl.concat([a.select(m="m", sd="sd"), a.select(m="m_e", sd="sd_e")]).filter(c("sd") > 0)
        slope, inter = np.polyfit(np.log(both["m"].to_numpy()), np.log(both["sd"].to_numpy()), 1)
        a = a.filter((c("sd") > 0) & (c("sd_e") > 0)).with_columns(
            res=c("sd").log() - (inter + slope * c("m").log()),
            res_e=c("sd_e").log() - (inter + slope * c("m_e").log()),
        )
        raw = np.corrcoef(a["sd"].to_numpy(), a["sd_e"].to_numpy())[0, 1]
        net = np.corrcoef(a["res"].to_numpy(), a["res_e"].to_numpy())[0, 1]
        seas = p.group_by("gsis_id", "season").agg(n=pl.len(), m=c("y").mean(), sd=c("y").std()).filter(
            (c("n") >= 8) & (c("m") > 0) & (c("sd") > 0)
        ).with_columns(res=c("sd").log() - (inter + slope * c("m").log()))  # fmt: skip
        nx = seas.join(seas.with_columns(c("season") - 1), on=["gsis_id", "season"], suffix="_n")
        raw_s = np.corrcoef(nx["sd"].to_numpy(), nx["sd_n"].to_numpy())[0, 1]
        net_s = np.corrcoef(nx["res"].to_numpy(), nx["res_n"].to_numpy())[0, 1]
        print(f"  {k:<6} odd against even weeks: raw {fisher(raw, a.height)}; average taken out {fisher(net, a.height)}")
        print(f"         season to next season:  raw {fisher(raw_s, nx.height)}; average taken out {fisher(net_s, nx.height)}")
        pos = [x for x in df.columns if x.startswith("pos_")]
        pos = pos if len(pos) > 1 else []
        without = walk(df, [f for f in crude_feats if f not in ("y_sd", "y_ls_sd")] + pos)
        print(f"         as inputs to the middle, the spread adds {pct(gain(df, base_pred[k], without))}")
        d = df.with_columns(p=pl.Series(base_pred[k])).filter(c("p").is_not_nan() & c("y_sd").is_not_null())
        miss, pv, sd = np.abs(d["y"].to_numpy() - d["p"].to_numpy()), d["p"].to_numpy(), d["y_sd"].to_numpy()
        res_m = miss - np.polyval(np.polyfit(pv, miss, 2), pv)
        res_s = sd - np.polyval(np.polyfit(pv, sd, 2), pv)
        print(f"         for the range: his spread so far against the size of the miss, the forecast held fixed: r {fisher(np.corrcoef(res_m, res_s)[0, 1], d.height)}")

    # ---- 8. play level: how much of one play's yards can anything explain?
    print("\n== 8. Play level: a single run or pass play's yards (fit 2016-2021, scored 2022-2024)")
    pbp = src.part("play", "pbp").filter(
        c("season").is_between(2016, LAST) & ((c("pass") == 1) | (c("rush") == 1))
        & c("yards_gained").is_not_null() & c("down").is_not_null()
    ).select("game_id", "season", "posteam", "defteam", "yards_gained", "down", "ydstogo",
             "yardline_100", "qtr", "half_seconds_remaining", "score_differential", "shotgun",
             "xpass", "pass")  # fmt: skip
    tm = tdf.select("game_id", posteam=c("team"), off_ypp=c("off_y_s") / c("off_vol_s"),
                    def_ypp=c("def_y_s") / c("def_vol_s"))  # fmt: skip
    pbp = pbp.join(tm, on=["game_id", "posteam"], how="left")
    sit = ["down", "ydstogo", "yardline_100", "qtr", "half_seconds_remaining", "score_differential",
           "shotgun", "xpass"]  # fmt: skip
    tr, te = pbp.filter(c("season") <= 2021), pbp.filter(c("season") >= 2022)
    yt, ye = tr["yards_gained"].to_numpy().astype(float), te["yards_gained"].to_numpy().astype(float)
    for label, fs in (("the situation before the snap", sit),
                      ("+ both teams' yards per play so far", [*sit, "off_ypp", "def_ypp"]),
                      ("+ knowing run or pass (not known before the snap)", [*sit, "off_ypp", "def_ypp", "pass"])):  # fmt: skip
        m = HistGradientBoostingRegressor(max_iter=150, learning_rate=0.06, max_leaf_nodes=31,
                                          random_state=0).fit(tr.select(fs).to_numpy().astype(float), yt)  # fmt: skip
        pr = m.predict(te.select(fs).to_numpy().astype(float))
        print(f"  {label:<52} removes {100 * (1 - ((pr - ye) ** 2).sum() / ((ye - yt.mean()) ** 2).sum()):.2f}%"
              f"  ({te.height} plays)")  # fmt: skip
    log("done")


if __name__ == "__main__":
    main()
