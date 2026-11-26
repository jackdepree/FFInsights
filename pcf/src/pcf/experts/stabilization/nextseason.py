"""The next-season ladder (the agreed brief, rungs 1-3 and 5; decision 0052, calls 10-14).

Every season pair: input season s (an entity-season with MIN_DEN+ attempts), target s + 1 (his
rate that season, weighted by its attempts). Everything is centred by the input season's class
mean, which is known before the target season, so the position's average is 0 and league shifts
count against every rung alike. k is fit on seasons up to s; every slope and ridge on pairs whose
target season is earlier.

The rungs:
- `avg` 0; `raw` his centred rate; `m1` = n / (n + k) of it (the shared `shrink`).
- `pull` (rung 2): m1 times one slope (the shared `second_pull`).
- `ridge` (rung 3): his m1, his other consistent rates' m1 (true-rate season r of 0.5+, chosen on
  earlier pairs only: feature selection inside the fold) and his teammates' conditions (H113's:
  last season's, and the change for a mover), standardized, no intercept, alpha by RidgeCV's own
  leave-one-out inside the training pairs.
- Ideas: `ridge_trend` (I152: his m1's change over his last two seasons added), `pull_mv` (I173:
  separate slopes for movers and stayers), `layered` (I181: pulled toward his team's rate at his
  position, itself pulled toward the position).
"""

from __future__ import annotations

import warnings

import numpy as np
import polars as pl
from sklearn.linear_model import RidgeCV

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import rates as R
from pcf.validation import stabilize as S

c = pl.col
ALPHAS = np.logspace(-3, 3, 13)


def season_m1(rows: pl.DataFrame, games: pl.DataFrame, ent: str = "gsis_id",
              cls: str = "pos") -> pl.DataFrame:  # fmt: skip
    """Per entity-season (MIN_DEN+ attempts): x (centred by its own class-season mean), n, k fit
    on seasons up to it, m1, sigma2, tau2, team, class."""
    out = []
    first = int(rows["season"].min())
    for s in range(first, K.LAST + 1):
        a = R.centred(rows.filter(c("season") == s), cls)
        if a.height == 0:
            continue
        f = R.fit_k(rows, games, s, ent, cls)
        out.append(a.with_columns(n=c("den"), k=pl.lit(f["k"]), sigma2=pl.lit(f["sigma2"]),
                                  tau2=pl.lit(f["tau2"]))  # fmt: skip
                   .with_columns(m1=S.shrink_expr("x", "n", "k")))
    return pl.concat(out)


def pairs(sm: pl.DataFrame, rows: pl.DataFrame, ent: str = "gsis_id",
          first_team: pl.DataFrame | None = None) -> pl.DataFrame:  # fmt: skip
    """Season pairs: the input season's m1 row and the target season's rate, centred by the
    input season's class mean. `first_team`: each entity-season's team in its first game (his
    next team, known before the season starts); the main team if not given."""
    nxt = rows.filter(c("den") > 0).select(ent, season=c("season") - 1, rate_next=c("num") / c("den"),
                                           w="den", team_main_next="team")  # fmt: skip
    p = sm.join(nxt, on=[ent, "season"], how="inner")
    if first_team is not None:
        ft = first_team.select(ent, season=c("season") - 1, team_next="team")
        p = p.join(ft, on=[ent, "season"], how="left").with_columns(
            team_next=pl.coalesce("team_next", "team_main_next")
        )
    else:
        p = p.with_columns(team_next=c("team_main_next"))
    return p.with_columns(y=c("rate_next") - c("mu"), target=c("season") + 1,
                          moved=c("team_next") != c("team"))  # fmt: skip


def first_teams(games: pl.DataFrame, ent: str = "gsis_id") -> pl.DataFrame:
    return games.sort(ent, "season", "week").group_by(ent, "season", maintain_order=True).agg(
        team=c("team").first()
    )


def team_parts(sm: pl.DataFrame, ent: str = "gsis_id", cls: str = "pos") -> pl.DataFrame:
    """I181: per team-class-season, its players' summed centred num and den (to leave one out)."""
    return sm.group_by("team", cls, "season").agg(t_num=(c("x") * c("n")).sum(), t_den=c("n").sum())


def team_k(sm: pl.DataFrame, cls: str = "pos") -> pl.DataFrame:
    """I181: per season, the team part's k: sigma2 over the true spread of team-class rates."""
    out = []
    for s in sorted(sm["season"].unique().to_list()):
        t = sm.filter(c("season") <= s).group_by("team", cls, "season").agg(
            num=(c("x") * c("n")).sum(), den=c("n").sum()
        )
        sig = float(sm.filter(c("season") == s)["sigma2"][0])
        tau = S.spread(t["den"].to_numpy(), (t["num"] / t["den"]).to_numpy(), sig)
        out.append((s, sig / tau))
    return pl.DataFrame({"season": [s for s, _ in out], "k_team": [k for _, k in out]},
                        schema={"season": pl.Int32, "k_team": pl.Float64})  # fmt: skip


def features(p: pl.DataFrame, others: dict[str, pl.DataFrame], cond: pl.DataFrame | None,
             team_cond: pl.DataFrame | None, sm: pl.DataFrame, parts: pl.DataFrame | None,
             kt: pl.DataFrame | None, ent: str = "gsis_id", cls: str = "pos") -> pl.DataFrame:  # fmt: skip
    """Pairs with every candidate input: `o_<measure>` (his other rates' m1 that season, 0 where
    he has none), `cond_<c>` (his teammates' condition, centred by season), `chg_<c>` (for a
    mover, his next team's condition less his own), `trend` (I152) and `layer_t` (I181)."""
    for name, o in others.items():
        p = p.join(o.select(ent, "season", c("m1").alias(f"o_{name}")), on=[ent, "season"],
                   how="left").with_columns(c(f"o_{name}").fill_null(0.0))  # fmt: skip
    if cond is not None:
        cc = [x for x in cond.columns if x.startswith("cond_")]
        p = p.join(cond, on=[ent, "season"], how="left")
        tcj = team_cond.rename({x: x.replace("cond_", "tc_") for x in cc}).rename(
            {"team": "team_next"}
        )
        p = p.join(tcj, on=["team_next", "season"], how="left")
        for x in cc:
            t = x.replace("cond_", "tc_")
            p = p.with_columns(
                c(x).fill_null(0.0),
                pl.when(c("moved")).then(c(t).fill_null(0.0) - c(x).fill_null(0.0))
                .otherwise(0.0).alias(x.replace("cond_", "chg_")),
            ).drop(t)  # fmt: skip
    prev = sm.select(ent, season=c("season") + 1, m1_prev="m1")
    p = p.join(prev, on=[ent, "season"], how="left").with_columns(
        trend=(c("m1") - c("m1_prev")).fill_null(0.0)
    ).drop("m1_prev")
    if parts is not None:
        p = p.join(parts, on=["team", cls, "season"], how="left").join(kt, on="season", how="left")
        p = p.with_columns(o_num=c("t_num") - c("x") * c("n"), o_den=c("t_den") - c("n"))
        p = p.with_columns(
            layer_t=pl.when(c("o_den") > 0)
            .then(c("o_den") / (c("o_den") + c("k_team")) * c("o_num") / c("o_den"))
            .otherwise(0.0)
        ).drop("t_num", "t_den", "o_num", "o_den")
    return p


def player_conditions(cond: pl.DataFrame, games: pl.DataFrame, keys: tuple[str, ...],
                      ent: str = "gsis_id") -> tuple[pl.DataFrame, pl.DataFrame]:  # fmt: skip
    """His teammates' conditions per season over his games of this measure (centred by season),
    and each team-season's (for his next team)."""
    g = games.select(ent, "game_id", "season").unique().join(cond, on=[ent, "game_id"])
    out = tout = None
    for k in keys:
        a = g.drop_nulls([f"{k}_n", f"{k}_d"]).filter(c(f"{k}_d") > 0)
        pv = a.group_by(ent, "season").agg(v=c(f"{k}_n").sum() / c(f"{k}_d").sum())
        tv = a.group_by("team", "season").agg(v=c(f"{k}_n").sum() / c(f"{k}_d").sum())
        lm = tv.group_by("season").agg(lm=c("v").mean())
        pv = pv.join(lm, on="season").select(ent, "season", **{f"cond_{k}": c("v") - c("lm")})
        tv = tv.join(lm, on="season").select("team", "season", **{f"cond_{k}": c("v") - c("lm")})
        out = pv if out is None else out.join(pv, on=[ent, "season"], how="full", coalesce=True)
        tout = tv if tout is None else tout.join(tv, on=["team", "season"], how="full",
                                                 coalesce=True)  # fmt: skip
    return out, tout


def _ridge(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[RidgeCV, np.ndarray]:
    sd = X.std(0)
    sd[sd == 0] = 1.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = RidgeCV(alphas=ALPHAS, fit_intercept=False).fit(X / sd, y, sample_weight=w)
    return r, sd


def chosen(p: pl.DataFrame, others: list[str], before: int, ks: dict) -> list[str]:
    """H114's consistent rates, chosen inside the fold: other measures whose true-rate season r
    on pairs with target seasons before `before` is CONSISTENT_R or more."""
    out = []
    for o in others:
        op = ks[o]
        tr = op.filter(c("target") < before)
        if tr.height < S.MIN_PAIRS:
            continue
        r = R.season_r(tr, float(tr["k"].mean()))
        if np.isfinite(r) and r >= K.CONSISTENT_R:
            out.append(o)
    return out


def rungs(p: pl.DataFrame, others: list[str], ks: dict, cond_cols: list[str]) -> pl.DataFrame:
    """Every rung's walk-forward forecast (null where not fittable yet), and each fitted rung's
    weight on his own m1 (for its range)."""
    p = p.sort("target", "gsis_id" if "gsis_id" in p.columns else "team")
    p = p.with_columns(avg=pl.lit(0.0), raw=c("x"), layered=c("layer_t") + S.shrink_expr(
        "x", "n", "k") - c("n") / (c("n") + c("k")) * c("layer_t")) if "layer_t" in p.columns \
        else p.with_columns(avg=pl.lit(0.0), raw=c("x"))  # fmt: skip
    tgt, y, w = p["target"].to_numpy(), p["y"].to_numpy(), p["w"].to_numpy()
    m1 = p["m1"].to_numpy()
    fc, b = S.second_pull(m1, y, w, tgt)
    mv = p["moved"].fill_null(False).to_numpy()
    X_mv = np.column_stack([m1 * mv, m1 * ~mv])
    fc_mv, _ = S.walk_slopes(X_mv, y, w, tgt)
    n = p.height
    ridge, ridge_t, b_ridge, used = (np.full(n, np.nan) for _ in range(4))
    for t in np.unique(tgt):
        tr, te = tgt < t, tgt == t
        if tr.sum() < 100:
            continue
        sel = chosen(p, others, t, ks)
        cols = ["m1", *[f"o_{o}" for o in sel], *cond_cols]
        X = p.select(cols).to_numpy()
        r, sd = _ridge(X[tr], y[tr], w[tr])
        ridge[te] = (X[te] / sd) @ r.coef_
        b_ridge[te] = r.coef_[0] / sd[0]
        used[te] = len(sel)
        Xt = np.column_stack([X, p["trend"].to_numpy()])
        r2, sd2 = _ridge(Xt[tr], y[tr], w[tr])
        ridge_t[te] = (Xt[te] / sd2) @ r2.coef_
    p = p.with_columns(pull=pl.Series(fc), b_pull=pl.Series(b), pull_mv=pl.Series(fc_mv),
                       ridge=pl.Series(ridge), b_ridge=pl.Series(b_ridge),
                       ridge_trend=pl.Series(ridge_t), n_consistent=pl.Series(used))  # fmt: skip
    cols = ["pull", "b_pull", "pull_mv", "ridge", "b_ridge", "ridge_trend", "n_consistent"]
    return p.with_columns(c(cols).fill_nan(None))


def ranges(p: pl.DataFrame, rung: str) -> pl.DataFrame:
    """`v_<rung>`: b^2 sigma2 / (n + k) + c + sigma2 / w, with b the rung's weight on his own m1
    (1 for m1, the slope for pull, the ridge's own coefficient) and c the drift left over, fit by
    moments on earlier targets; `scale_<rung>`: the conformal scale on earlier targets."""
    b = {"m1": pl.lit(1.0), "pull": c("b_pull"), "ridge": c("b_ridge"), "raw": pl.lit(1.0),
         "avg": pl.lit(0.0)}.get(rung, pl.lit(1.0))  # fmt: skip
    base = b**2 * c("sigma2") / (c("n") + c("k")) + c("sigma2") / c("w")
    if rung == "avg":
        base = c("tau2") + c("sigma2") / c("w")
    q = p.with_columns(_base=base, _r=c("w") * ((c("y") - c(rung)) ** 2 - base))
    tgt = q["target"].to_numpy()
    cs = np.full(q.height, np.nan)
    for t in np.unique(tgt):
        tr = q.filter((c("target") < t) & c("_r").is_not_null())
        if tr.height >= S.MIN_PAIRS:
            cs[tgt == t] = max(float(tr["_r"].sum() / tr["w"].sum()), 0.0)
    q = q.with_columns(pl.Series("_c", cs).fill_nan(None)).with_columns(
        (c("_base") + c("_c")).alias(f"v_{rung}")
    )
    sc = np.full(q.height, np.nan)
    for t in np.unique(tgt):
        tr = q.filter(c("target") < t).drop_nulls([rung, f"v_{rung}"])
        if tr.height >= S.MIN_PAIRS:
            z = ((tr["y"] - tr[rung]).abs() / tr[f"v_{rung}"].sqrt()).to_numpy()
            sc[tgt == t] = float(np.quantile(z, 0.8) / K.Z80)
    return q.with_columns(pl.Series(f"scale_{rung}", sc).fill_nan(None)).drop("_base", "_r", "_c")


def swing(sm_games: pl.DataFrame, sm: pl.DataFrame, ent: str = "gsis_id") -> pl.DataFrame:
    """I14 for next season: his games' scatter around his season rate against the noise alone
    (1 = as expected), shrunk toward 1 with SWING_WEIGHT games."""
    g = sm_games.join(sm.select(ent, "season", "rate", "sigma2"), on=[ent, "season"])
    g = g.with_columns(z2=c("den") * (c("num") / c("den") - c("rate")) ** 2 / c("sigma2"))
    s = g.group_by(ent, "season").agg(zs=c("z2").sum(), G=pl.len())
    return s.select(ent, "season", sw=(c("zs") + K.SWING_WEIGHT) / (c("G") + K.SWING_WEIGHT),
                    G=c("G").cast(pl.Float64))  # fmt: skip
