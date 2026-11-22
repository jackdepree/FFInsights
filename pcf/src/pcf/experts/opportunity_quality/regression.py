"""The regression measure (the CEO's design: "the chance that a player will actually bridge the
gap between their expected fantasy points and their efficiency"; decision 0041).

Before each of a player's regular-season games:
- **The gap:** his points over expected per chance over this season so far and last season (the
  window), with `n` chances behind it.
- **What is kept,** from parameters fit on earlier seasons only:
  - **Method A** (one pull-back rate per position): next = μ + k·(gap − μ), with k the weighted
    slope of later gaps on earlier ones.
  - **Method B** (a rate per player, partial pooling): k = τ² / (τ² + V), where τ² is how much
    players' true levels differ at his position and V the noise in his gap from `n` chances
    (V = Σ σ²_kind · n_kind / n², σ² the spread of one chance's points over expected).
  - **Method B with inputs** (the CEO's call 3, position and yards after the catch): B, plus his
    yards-after-the-catch points over expected per target shrunk the same way, times a weight per
    position fit on earlier seasons.
- **The range for his true level:** B's posterior, q10-q90.
- **The forecast of his future gap** over the chances he is expected to get in the rest of the
  season, with a range, and **the chance the gap closes by half or more** (his future gap ends on
  the near side of half his current gap).

Everything is a weighted quantity per chance; weights are chances. The functions are pure.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.experts.opportunity_quality.common import weights

c = pl.col
MIN_WINDOW = 20  # chances in the window for a row to get a measure
MIN_FUTURE = 10  # chances in the rest of the season for a row to be scored
MIN_SEASON = 30  # chances in a training player-season for τ²
TRAIN_SEASONS = 6  # earlier seasons the parameters are fit on
TAU2_FLOOR = 1e-4
Z90 = 1.2815515655446004  # the 90th percentile of a standard normal
METHODS = ("luck", "same", "A", "B", "B_yac")


def chance_spread(xfp_plays: pl.DataFrame, scoring: str = "ppr") -> pl.DataFrame:
    """The `play.xfp` part (regular season) → per season, position and kind: chances, the mean and
    mean square of one chance's points over expected, and for targets the same for its yards after
    the catch points over expected (0 if incomplete)."""
    rec, yard, td = weights(scoring)
    p = xfp_plays.filter(c("oq_catch_exp").is_not_null()).with_columns(
        poe=rec * (c("oq_catch") - c("oq_catch_exp")) + yard * (c("oq_yards") - c("oq_yards_exp"))
        + td * (c("oq_td") - c("oq_td_exp")),
        yac=yard * c("oq_yac_oe").fill_null(0.0),
    )  # fmt: skip
    return p.group_by("season", position="oq_position", kind="oq_kind").agg(
        n=pl.len(), m1=c("poe").mean(), m2=(c("poe") ** 2).mean(),
        y1=c("yac").mean(), y2=(c("yac") ** 2).mean(),
    )  # fmt: skip


def windows(pg: pl.DataFrame) -> pl.DataFrame:
    """Regular-season player-games (gsis_id, game_id, season, week, position, targets, carries,
    chances, poe, yac) → one row per game with the window before it (this season so far and last
    season: n, n_t, n_c, poe, yac, games) and the rest of the season from it (m, poe_f, games
    left). Oldest first."""
    pg = pg.sort("gsis_id", "season", "week")
    us = ["gsis_id", "season"]
    sums = ["chances", "targets", "carries", "poe", "yac"]
    before = pg.with_columns(
        *[(c(x).cum_sum().over(us) - c(x)).alias(f"cs_{x}") for x in sums],
        cs_games=(pl.int_range(pl.len()).over(us)).cast(pl.Float64),
        tot_chances=c("chances").sum().over(us),
        tot_poe=c("poe").sum().over(us),
        games_left=(pl.len().over(us) - pl.int_range(pl.len()).over(us)).cast(pl.Float64),
    )
    last = (
        pg.group_by(us)
        .agg(*[c(x).sum().alias(f"ls_{x}") for x in sums], ls_games=pl.len().cast(pl.Float64))
        .with_columns(c("season") + 1)
    )
    out = before.join(last, on=us, how="left").with_columns(
        c([f"ls_{x}" for x in sums] + ["ls_games"]).fill_null(0.0)
    )
    return out.select(
        "gsis_id",
        "game_id",
        "season",
        "week",
        "position",
        n=c("cs_chances") + c("ls_chances"),
        n_t=c("cs_targets") + c("ls_targets"),
        n_c=c("cs_carries") + c("ls_carries"),
        poe_w=c("cs_poe") + c("ls_poe"),
        yac_w=c("cs_yac") + c("ls_yac"),
        games_w=c("cs_games") + c("ls_games"),
        m=c("tot_chances") - c("cs_chances"),
        poe_f=c("tot_poe") - c("cs_poe"),
        games_left="games_left",
    ).with_columns(
        gap=c("poe_w") / c("n"),
        yac_gap=c("yac_w") / c("n_t"),
        future=c("poe_f") / c("m"),
        m_exp=c("n") / c("games_w") * c("games_left"),
    )


def _pooled(spread: pl.DataFrame, seasons: Sequence[int]) -> pl.DataFrame:
    """σ² (one chance's spread around its position's level) per position and kind, and the yards
    after the catch's for targets, over the training seasons."""
    s = spread.filter(c("season").is_in(list(seasons)))
    return s.group_by("position", "kind").agg(
        m1=(c("m1") * c("n")).sum() / c("n").sum(), m2=(c("m2") * c("n")).sum() / c("n").sum(),
        y1=(c("y1") * c("n")).sum() / c("n").sum(), y2=(c("y2") * c("n")).sum() / c("n").sum(),
    ).with_columns(sigma2=c("m2") - c("m1") ** 2, ysigma2=c("y2") - c("y1") ** 2)  # fmt: skip


def _noise(rows: pl.DataFrame, sig: pl.DataFrame) -> pl.DataFrame:
    """V (the noise in a gap from its chances) and Vy (in a yards-after-the-catch gap)."""
    t = sig.filter(c("kind") == "target").select("position", s_t="sigma2", s_y="ysigma2")
    k = sig.filter(c("kind") == "carry").select("position", s_c="sigma2")
    return (
        rows.join(t, on="position", how="left")
        .join(k, on="position", how="left")
        .with_columns(
            V=(c("n_t") * c("s_t") + c("n_c") * c("s_c").fill_null(c("s_t"))) / c("n") ** 2,
            Vy=c("s_y") / c("n_t"),
            s_mix=(c("n_t") * c("s_t") + c("n_c") * c("s_c").fill_null(c("s_t"))) / c("n"),
        )
    )


def player_seasons(pg: pl.DataFrame) -> pl.DataFrame:
    """Regular-season player-games → whole player-seasons: chances by kind, the season's gap and
    its yards-after-the-catch gap per target."""
    return (
        pg.group_by("gsis_id", "season")
        .agg(
            position=c("position").last(),
            n=c("chances").sum(),
            n_t=c("targets").sum(),
            n_c=c("carries").sum(),
            poe=c("poe").sum(),
            yac=c("yac").sum(),
        )  # fmt: skip
        .filter(c("n") > 0)
        .with_columns(gap=c("poe") / c("n"), yac_gap=c("yac") / c("n_t"))
    )


def fit(win: pl.DataFrame, ps: pl.DataFrame, spread: pl.DataFrame, season: int) -> dict:
    """Every method's parameters for `season`, from the `TRAIN_SEASONS` seasons before it only:
    per position μ and τ² (from whole player-seasons, each gap against its own noise), A's rate k
    and residual spread, and for yards after the catch μ_y, τ²_y and B with inputs' weight γ
    (from earlier seasons' scored moments)."""
    seasons = list(range(season - TRAIN_SEASONS, season))
    sig = _pooled(spread, seasons)
    params: dict = {"season": season, "seasons": seasons, "sigma": sig, "pos": {}}
    rows = _noise(ps.filter(c("season").is_in(seasons)), sig)
    for pos in sorted(rows["position"].unique().to_list()):
        d = rows.filter((c("position") == pos) & (c("n") >= MIN_SEASON))
        if d.height < 30:
            continue
        w, x = d["n"].to_numpy(), d["gap"].to_numpy()
        mu = float(np.sum(w * x) / np.sum(w))
        tau2 = max(float(np.mean((x - mu) ** 2 - d["V"].to_numpy())), TAU2_FLOOR)
        dy = d.filter(c("n_t") >= MIN_SEASON)
        xy, wy = dy["yac_gap"].to_numpy(), dy["n_t"].to_numpy()
        mu_y = float(np.sum(wy * xy) / np.sum(wy)) if len(xy) else 0.0
        tau2_y = TAU2_FLOOR
        if len(xy):
            tau2_y = max(float(np.mean((xy - mu_y) ** 2 - dy["Vy"].to_numpy())), TAU2_FLOOR)
        params["pos"][pos] = {"mu": mu, "tau2": tau2, "mu_y": mu_y, "tau2_y": tau2_y}
    moments = predict_b(scored(win.filter(c("season").is_in(seasons))), params)
    for pos, pp in params["pos"].items():
        d = moments.filter(c("position") == pos)
        if d.height < 50:
            pp |= {"kA": 0.0, "resid_A": TAU2_FLOOR, "gamma": 0.0}
            continue
        w = d["m"].to_numpy()
        dx = d["gap"].to_numpy() - pp["mu"]
        dy = d["future"].to_numpy() - pp["mu"]
        kA = float(np.sum(w * dx * dy) / np.sum(w * dx * dx))
        noise = d["s_mix"].to_numpy() / d["m"].to_numpy()
        resid_A = max(float(np.sum(w * ((dy - kA * dx) ** 2 - noise)) / np.sum(w)), TAU2_FLOOR)
        left = d["future"].to_numpy() - d["mean_B"].to_numpy()
        z = d["yac_shrunk"].to_numpy()
        gamma = float(np.sum(w * z * left) / np.sum(w * z * z)) if np.sum(w * z * z) > 0 else 0.0
        pp |= {"kA": kA, "resid_A": resid_A, "gamma": gamma}
    return params


def scored(win: pl.DataFrame) -> pl.DataFrame:
    """The rows that get a measure and can be scored: enough chances before and after."""
    return win.filter((c("n") >= MIN_WINDOW) & (c("m") >= MIN_FUTURE) & (c("n_t") > 0))


def predict_b(rows: pl.DataFrame, params: dict) -> pl.DataFrame:
    """Rows with B's kept share and mean (and the yac gap shrunk), before A's and γ's fit."""
    pos = pl.DataFrame(
        [
            {"position": k, **{x: v[x] for x in ("mu", "tau2", "mu_y", "tau2_y")}}
            for k, v in params["pos"].items()
        ]  # fmt: skip
    )
    out = _noise(rows, params["sigma"]).join(pos, on="position", how="inner")
    return out.with_columns(
        k_B=c("tau2") / (c("tau2") + c("V")),
        k_y=c("tau2_y") / (c("tau2_y") + c("Vy")),
    ).with_columns(
        mean_B=c("mu") + c("k_B") * (c("gap") - c("mu")),
        yac_shrunk=c("k_y") * (c("yac_gap").fill_null(c("mu_y")) - c("mu_y")),
    )


def _norm_cdf(z: np.ndarray) -> np.ndarray:
    return 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))


def measure(rows: pl.DataFrame, params: dict) -> pl.DataFrame:
    """The measure for `rows` (from `windows`): each method's forecast of the future gap, B's
    kept share, the range for his true level, the future gap's range over his expected chances,
    and each method's chance that the gap closes by half or more."""
    pos = pl.DataFrame(
        [
            {"position": k, "kA": v["kA"], "resid_A": v["resid_A"], "gamma": v["gamma"]}
            for k, v in params["pos"].items()
        ]  # fmt: skip
    )
    out = predict_b(rows, params).join(pos, on="position", how="inner")
    m = pl.max_horizontal(c("m_exp"), pl.lit(1.0))
    out = out.with_columns(
        mean_luck=c("mu"),
        mean_same=c("gap"),
        mean_A=c("mu") + c("kA") * (c("gap") - c("mu")),
        mean_B_yac=c("mu") + c("k_B") * (c("gap") - c("mu")) + c("gamma") * c("yac_shrunk"),
        post_sd=(c("k_B") * c("V")).sqrt(),
        sd_A=(c("resid_A") + c("s_mix") / m).sqrt(),
        sd_B=(c("k_B") * c("V") + c("s_mix") / m).sqrt(),
    ).with_columns(
        true_q10=c("mean_B") - Z90 * c("post_sd"),
        true_q90=c("mean_B") + Z90 * c("post_sd"),
        future_q10=c("mean_B") - Z90 * c("sd_B"),
        future_q50=c("mean_B"),
        future_q90=c("mean_B") + Z90 * c("sd_B"),
        half=c("gap") / 2,
    )
    for meth, sd in (("A", "sd_A"), ("B", "sd_B"), ("B_yac", "sd_B")):
        z = ((out["half"] - out[f"mean_{meth}"]) / out[sd]).to_numpy()
        below = _norm_cdf(z)
        p = np.where(out["gap"].to_numpy() >= 0, below, 1 - below)
        out = out.with_columns(pl.Series(f"p_close_{meth}", p))
    return out


def closed() -> pl.Expr:
    """Whether the gap closed by half or more: the future gap on the near side of half of it."""
    return pl.when(c("gap") >= 0).then(c("future") < c("half")).otherwise(c("future") > c("half"))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_platt(p: np.ndarray, closed_: np.ndarray) -> tuple[float, float]:
    """Platt scaling of the chance the gap closes: intercept and slope on its logit, fit on rows
    the parameters were fit on (earlier seasons only; VALIDATION.md section 7 allows it)."""
    from sklearn.linear_model import LogisticRegression

    m = LogisticRegression(C=1e6, max_iter=2000).fit(_logit(p).reshape(-1, 1), closed_.astype(int))
    return float(m.intercept_[0]), float(m.coef_[0, 0])


def platt(cal: tuple[float, float], p: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-(cal[0] + cal[1] * _logit(p))))
