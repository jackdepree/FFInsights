"""The in-season ladder (the agreed brief, rungs 1, 2, 4 and 5; decision 0052, calls 5-9).

For each test season T (2018-2024), everything is fit on seasons before T: k (sigma2, tau2), the
filter's q and q_s (and I154's phi, I182's omega), the second pull's slope per checkpoint and the
ranges' drift term. Each forecast is made after a player's game 4, 8 or 12 of the season, at the
kickoff of his next game, from the games known by then (PFR's rows at PFR's lag), and scored on
his next 4 games' rate (and, as a side horizon, the rest of his season's), weighted by their
attempts. Rates are centred by last season's class mean, known before the season.

The rungs (centred, so the position's average is 0):
- `avg`: 0, the position's average last season.
- `raw`: his rate this season so far.
- `m1`: static M1: last season's and this season's attempts pooled, pulled by k, no drift.
- `pull`: the second pull, by horizon: m1 times one slope per checkpoint, fit on earlier seasons.
- `filt`: the local-level filter (`drift`), plain; `filt_phi` with I154's factor; `filt_om` with
  I182's fixed extra.
- `m1_k104`: I104's form: static M1 with k blended with this season's own (weeks up to the
  checkpoint).

Ranges (80%, normal): `v_m1`, `v_pull` = slope^2 x sigma2 / (N + k) + c + sigma2 / w, with c the
drift left over, fit by moments on earlier seasons; `v_filt*` = P + q (H + 1) / 2 + noise / w.
`sw` is I14's swing factor (his games' squared surprises so far, shrunk toward 1 with 20 games).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K
from pcf.experts.stabilization import drift as F
from pcf.experts.stabilization import rates as R
from pcf.validation import stabilize as S

c = pl.col
INPUTS = ("m1", "m1_v", "N", "raw", "m", "P", "m_phi", "P_phi", "m_om", "P_om", "swing", "G",
          "m1_k104", "k104")  # fmt: skip


def centred_games(games: pl.DataFrame, rows: pl.DataFrame, ent: str, cls: str) -> pl.DataFrame:
    """His games, each centred by last season's mean of his class that season (his own season's
    mean only where no last season exists, the first season)."""
    means = R.class_means(rows, cls)
    last = means.select(cls, season=c("season") + 1, mu_last="mu")
    own = means.rename({"mu": "mu_own"})
    sc = rows.select(ent, "season", cls_s=c(cls))
    g = games.join(sc, on=[ent, "season"]).drop(cls).rename({"cls_s": cls})
    g = g.join(last, on=[cls, "season"], how="left").join(own, on=[cls, "season"], how="left")
    g = g.with_columns(mu=pl.coalesce("mu_last", "mu_own")).drop_nulls("mu")
    return g.select(ent, "season", "week", "game_id", "kickoff", "known_at", cls, "num", "den",
                    "mu", d=c("num") / c("den") - c("mu"), n="den")  # fmt: skip


def checkpoints(st: pl.DataFrame, ent: str, cls: str, k: float, sigma2: float, lagged: bool,
                tau2: float) -> pl.DataFrame:  # fmt: skip
    """One row per entity-season-checkpoint (after his game g, at his next game's kickoff): the
    inputs read from the games known by then, and the targets (next 4 games, rest of season)."""
    g = st.sort(ent, "season", "week").with_columns(
        gi=pl.int_range(1, pl.len() + 1).over(ent, "season"),
        G_season=pl.len().over(ent, "season"),
        nd=c("n") * c("d"),
    )
    g = g.with_columns(
        cn=c("n").cum_sum().over(ent, "season"),
        cnd=c("nd").cum_sum().over(ent, "season"),
        zsum=c("z2").cum_sum().over(ent),
        cnt=pl.int_range(1, pl.len() + 1).over(ent),
        next_kick=c("kickoff").shift(-1).over(ent, "season"),
    )
    tot = g.group_by(ent, "season").agg(pn=c("n").sum(), pnd=c("nd").sum(), tn=c("n").sum(),
                                        tnd=c("nd").sum())  # fmt: skip
    g = g.join(tot.select(ent, season=c("season") + 1, pn="pn", pnd="pnd"), on=[ent, "season"],
               how="left").with_columns(c("pn", "pnd").fill_null(0.0))  # fmt: skip
    g = g.join(tot.select(ent, "season", "tn", "tnd"), on=[ent, "season"])
    # the targets: next H games, and the rest of the season
    H = K.HORIZON
    g = g.with_columns(
        cn_h=c("cn").shift(-H).over(ent, "season"),
        cnd_h=c("cnd").shift(-H).over(ent, "season"),
    )
    cp = g.filter(c("gi").is_in(list(K.CHECKPOINTS)) & c("next_kick").is_not_null())
    cp = cp.with_columns(
        w=c("cn_h") - c("cn"), y=(c("cnd_h") - c("cnd")) / (c("cn_h") - c("cn")),
        w_rest=c("tn") - c("cn"), y_rest=(c("tnd") - c("cnd")) / (c("tn") - c("cn")),
        rest_games=c("G_season") - c("gi"),
    )  # fmt: skip
    # the state known at the next kickoff: this game's, or (PFR at its lag) an earlier one
    if lagged:
        known = g.select(ent, "season", "known_at", "gi", "cn", "cnd", "m", "P", "m_phi", "P_phi",
                         "m_om", "P_om", "zsum", "cnt").sort("known_at")  # fmt: skip
        cp = cp.drop("cn", "cnd", "m", "P", "m_phi", "P_phi", "m_om", "P_om", "zsum", "cnt")
        cp = cp.sort("next_kick").join_asof(
            known.rename({"season": "season_k", "gi": "gi_k"}), left_on="next_kick",
            right_on="known_at", by=ent, strategy="backward", suffix="_k",
        )  # fmt: skip
        same = c("season_k") == c("season")
        cp = cp.with_columns(
            cn=pl.when(same).then(c("cn")).otherwise(0.0),
            cnd=pl.when(same).then(c("cnd")).otherwise(0.0),
            gi_known=pl.when(same).then(c("gi_k")).otherwise(0),
        )
    else:
        cp = cp.with_columns(gi_known=c("gi"))
    N = c("pn") + c("cn")
    return cp.with_columns(
        N=N, m1=(c("pnd") + c("cnd")) / (N + k), m1_v=sigma2 / (N + k),
        raw=pl.when(c("cn") > 0).then(c("cnd") / c("cn")).otherwise(None),
        swing=c("zsum") / c("cnt"), G=c("cnt").cast(pl.Float64),
    ).select(ent, "season", "week", cls, "gi", "gi_known", "w", "y", "w_rest", "y_rest",
             "rest_games", "N", "m1", "m1_v", "raw", "m", "P", "m_phi", "P_phi", "m_om", "P_om",
             "swing", "G")  # fmt: skip


def k104(games_c: pl.DataFrame, ent: str, T: int, sigma2: float, tau2: float, lagged: bool,
         n_train: float) -> dict[int, float]:  # fmt: skip
    """I104's k per checkpoint for season T: this season's true spread from games in weeks up to
    the checkpoint (one earlier for PFR's lag), blended with the pooled spread by player-seasons
    (this season's against an average training season's)."""
    out = {}
    s = games_c.filter(c("season") == T)
    for g in K.CHECKPOINTS:
        wk = s.filter(c("week") <= (g - 1 if lagged else g))
        r = wk.group_by(ent).agg(num=c("nd_raw").sum(), den=c("n").sum())
        r = r.filter(c("den") >= R.MIN_DEN).with_columns(x=c("num") / c("den"))
        if r.height < 30:
            out[g] = sigma2 / tau2
            continue
        t_s = S.spread(r["den"].to_numpy(), r["x"].to_numpy(), sigma2)
        ws = r.height / (r.height + n_train)
        out[g] = sigma2 / (ws * t_s + (1 - ws) * tau2)
    return out


def season_frame(games: pl.DataFrame, rows: pl.DataFrame, T: int, ent: str = "gsis_id",
                 cls: str = "pos", lagged: bool = False, efficiency: bool = False,
                 L: F.Padded | None = None, gc: pl.DataFrame | None = None) -> tuple[pl.DataFrame, dict]:  # fmt: skip
    """Every season's checkpoint rows, with parameters fit on seasons before T (the test season's
    rows are the ones scored; earlier seasons' rows train the slopes and the ranges)."""
    kk = R.fit_k(rows, games, T - 1, ent, cls)
    sigma2, tau2, k = kk["sigma2"], kk["tau2"], kk["k"]
    gc = centred_games(games, rows, ent, cls) if gc is None else gc
    L = F.pad(gc.filter(c("season") <= T), ent) if L is None else L
    par = F.fit(L, sigma2, tau2, T, "plain")
    st = F.states(L, par, sigma2, tau2)
    par_phi = par_om = par
    if efficiency:
        par_phi = F.fit(L, sigma2, tau2, T, "factor")
        par_om = F.fit(L, sigma2, tau2, T, "fixed")
    s1 = F.states(L, par_phi, sigma2, tau2).select(ent, "season", "week", m_phi="m", P_phi="P")
    s2 = F.states(L, par_om, sigma2, tau2).select(ent, "season", "week", m_om="m", P_om="P")
    st = st.join(s1, on=[ent, "season", "week"]).join(s2, on=[ent, "season", "week"])
    cp = checkpoints(st, ent, cls, k, sigma2, lagged, tau2)
    cp = cp.filter(c("season") <= T)
    # I104: this season's k, blended
    n_train = rows.filter((c("season") < T) & (c("den") >= R.MIN_DEN)).group_by("season").len()
    n_train = float(n_train["len"].mean()) if n_train.height else 1.0
    kb = k104(gc.with_columns(nd_raw=c("n") * c("d")), ent, T, sigma2, tau2, lagged, n_train)
    kb_col = pl.col("gi").replace_strict({g: kb[g] for g in K.CHECKPOINTS}, default=k)
    cp = cp.with_columns(k104=pl.when(c("season") == T).then(kb_col).otherwise(pl.lit(k)))
    cp = cp.with_columns(m1_k104=c("m1") * (c("N") + k) / (c("N") + c("k104")))
    info = {"sigma2": sigma2, "tau2": tau2, "k": k, "par": par, "par_phi": par_phi,
            "par_om": par_om}  # fmt: skip
    return cp, info


def rungs(cp: pl.DataFrame, info: dict, horizon: str = "next") -> pl.DataFrame:
    """The fitted rungs and every range, walk-forward by season (slopes and the drift term from
    earlier seasons' rows at the same checkpoint)."""
    sigma2, k = info["sigma2"], info["k"]
    if horizon == "rest":
        cp = cp.filter(c("rest_games") >= K.HORIZON).with_columns(y=c("y_rest"), w=c("w_rest"))
        Hs = c("rest_games").cast(pl.Float64)
    else:
        Hs = pl.lit(float(K.HORIZON))
    cp = cp.filter(c("w") > 0).with_columns(avg=pl.lit(0.0))
    out = []
    for g in K.CHECKPOINTS:
        a = cp.filter(c("gi") == g).sort("season")
        if a.height == 0:
            continue
        s, y, w = a["season"].to_numpy(), a["y"].to_numpy(), a["w"].to_numpy()
        m1 = a["m1"].to_numpy()
        fc, b = S.second_pull(m1, y, w, s)
        a = a.with_columns(pull=pl.Series(fc), b_pull=pl.Series(b)).with_columns(
            c("pull", "b_pull").fill_nan(None)
        )
        # the drift left over (c), fit on earlier seasons by moments, for m1 and pull
        for name, slope in (("m1", pl.lit(1.0)), ("pull", c("b_pull"))):
            base = slope**2 * c("m1_v") + sigma2 / c("w")
            resid = a.select(r=c("w") * ((c("y") - c(name)) ** 2 - base), w="w",
                             season="season")  # fmt: skip
            cs = np.full(a.height, np.nan)
            for t in np.unique(s):
                tr = resid.filter((c("season") < t) & c("r").is_not_null())
                if tr.height >= S.MIN_PAIRS:
                    cs[s == t] = max(float(tr["r"].sum() / tr["w"].sum()), 0.0)
            a = a.with_columns(pl.Series(f"c_{name}", cs).fill_nan(None)).with_columns(
                (base + c(f"c_{name}")).alias(f"v_{name}")
            )
        out.append(a)
    a = pl.concat(out)
    for suf, par in (("", info["par"]), ("_phi", info["par_phi"]), ("_om", info["par_om"])):
        noise = par["phi"] * sigma2 / c("w") + par["omega"] / Hs
        a = a.with_columns((c(f"P{suf}") + par["q"] * (Hs + 1) / 2 + noise).alias(f"v_filt{suf}"),
                           c(f"m{suf}").alias(f"filt{suf}"))  # fmt: skip
    sw = (c("G") * c("swing") + K.SWING_WEIGHT) / (c("G") + K.SWING_WEIGHT)
    a = a.with_columns(sw=sw, k=pl.lit(k), reliability=c("N") / (c("N") + k))
    # the conformal scale per range, from earlier seasons' rows at the same checkpoint
    s, gi = a["season"].to_numpy(), a["gi"].to_numpy()
    for mean in ("m1", "pull", "filt", "filt_phi", "filt_om"):
        for wide in ("", "_sw"):
            v = c(f"v_{mean}") * (c("sw") if wide else 1.0)
            z = a.select(((c("y") - c(mean)).abs() / v.sqrt()).alias("z"))["z"].to_numpy()
            sc = np.full(a.height, np.nan)
            for t in np.unique(s):
                for g in K.CHECKPOINTS:
                    tr = (s < t) & (gi == g) & np.isfinite(z)
                    if tr.sum() >= S.MIN_PAIRS:
                        sc[(s == t) & (gi == g)] = np.quantile(z[tr], 0.8) / K.Z80
            a = a.with_columns(pl.Series(f"scale_{mean}{wide}", sc).fill_nan(None))
    return a
