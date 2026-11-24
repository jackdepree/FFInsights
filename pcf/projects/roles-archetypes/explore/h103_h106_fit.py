"""Roles exploration: H103 (roles and schemes fit) and H106 (archetype against the defense's scheme),
pre-registered in EXPLORATION.md.

H103: WR, TE, RB player-seasons. Side bet first: do M1 labels cluster on the team's scheme traits
(multinomial, cross-validated log loss against teams shuffled)? Then the fit test: EPA per target (WR, TE)
or per touch (RB), volume-weighted; model A = label + scheme traits + his prior-season efficiency (flag if
none); model B = A + label x scheme traits; leave-one-season-out; 90% team-season bootstrap of B's gain.

H106: WR and TE player-games with 3+ targets, 2019-2024. EPA per target that game against his prior-season
M1 label and efficiency, the opponent's prior-season pass EPA allowed per dropback and its defensive traits
over expected (box, man, two-high, blitz). A = main effects; B = A + label x the four traits. Walk-forward
by season (2020-2024 scored), target-weighted squared error, 90% game-week bootstrap.

Run from pcf/projects/roles-archetypes/explore: PYTHONIOENCODING=utf-8 <venv python> h103_h106_fit.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import roles_common as rc
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

c = pl.col
T = rc.CFG.zone("tables")
RNG = np.random.default_rng(rc.CFG.seed)
B = 2000
SEASONS = range(2016, 2025)
OFF_TRAITS = ["off_11_rate_oe", "off_12_rate_oe", "off_heavy_rate_oe", "off_time_to_throw_oe", "off_pistol_rate_oe", "proe", "team_adot"]
DEF_TRAITS = ["def_box_oe", "def_man_rate_oe", "def_two_high_rate_oe", "def_blitz_rate_oe"]
EPS = 1e-9


def boot(gain: np.ndarray, w: np.ndarray, cl: np.ndarray) -> tuple[float, float, float]:
    u, inv = np.unique(cl, return_inverse=True)
    W = RNG.poisson(1.0, size=(B, len(u)))[:, inv].astype(float) * w
    bs = (W @ gain) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    return float((w * gain).sum() / w.sum()), float(lo), float(hi)


def fit_pred(Xtr, ytr, wtr, Xte):
    sc = StandardScaler().fit(Xtr)
    m = Ridge(alpha=1.0).fit(sc.transform(Xtr), ytr, sample_weight=wtr)
    return m.predict(sc.transform(Xte))


def design(df: pl.DataFrame, labs: list[int], traits: list[str], main: list[str], inter: bool) -> np.ndarray:
    L = [(df["lab"] == k).cast(pl.Float64).to_numpy() for k in labs[1:]]
    cols = [*L, *[df[t].to_numpy() for t in traits], *[df[m].to_numpy() for m in main]]
    if inter:
        cols += [l_ * df[t].to_numpy() for l_ in L for t in traits]
    return np.column_stack(cols).astype(float)


def in_sample(df, labs, traits, main, ycol, wcol, clcol, name):
    """In-sample interactions with a cluster bootstrap (marked retroactive, one of many tried)."""
    X = design(df, labs, traits, main, True)
    y, w = df[ycol].to_numpy(), df[wcol].to_numpy().astype(float)
    nb = X.shape[1] - (len(labs) - 1) * len(traits)
    sd = X.std(0)
    X[:, sd < 1e-8], sd[sd < 1e-8] = 0.0, 1.0  # a constant column (e.g. every row has a prior) is dropped
    Xs = np.column_stack([np.ones(len(y)), X / sd])

    def coef(ix):
        Wd = w[ix]
        A = Xs[ix] * Wd[:, None]
        return np.linalg.lstsq(A.T @ Xs[ix] + 1e-6 * np.eye(Xs.shape[1]), A.T @ y[ix], rcond=None)[0]

    full = coef(np.arange(len(y)))
    u, inv = np.unique(df[clcol].to_numpy(), return_inverse=True)
    reps = []
    for _ in range(300):
        pick = RNG.integers(0, len(u), len(u))
        cnt = np.bincount(pick, minlength=len(u))
        ix = np.repeat(np.arange(len(y)), cnt[inv])
        reps.append(coef(ix))
    reps = np.array(reps)
    lo, hi = np.percentile(reps, [5, 95], axis=0)
    names = [f"label{k} x {t}" for k in labs[1:] for t in traits]
    clear = [(names[j - 1 - nb], full[j], lo[j], hi[j]) for j in range(1 + nb, Xs.shape[1]) if lo[j] > 0 or hi[j] < 0]
    print(f"  {name}: in-sample interactions with a clear 90% interval: {len(clear)} of {len(names)}"
          + "".join(f"\n    {n}: {b:+.3g} EPA per SD ({a:+.3g} to {z:+.3g})" for n, b, a, z in clear))
    return len(clear), len(names)


# --- team traits
charted = pl.concat([pl.read_parquet(T / "team_season" / "charted" / f"season={s}" / "data.parquet") for s in SEASONS], how="diagonal_relaxed")
pbp = pl.concat([pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=[
    "game_id", "season", "season_type", "week", "posteam", "defteam", "play_type", "qb_dropback", "pass_oe", "air_yards", "receiver_player_id", "epa", "two_point_attempt"])
    for s in SEASONS]).filter((c("season_type") == "REG") & c("play_type").is_in(["pass", "run"]) & (c("two_point_attempt") != 1))
team_off = pbp.group_by(team=c("posteam"), season=c("season")).agg(proe=c("pass_oe").mean(), team_adot=c("air_yards").filter(c("receiver_player_id").is_not_null()).mean())
team_def = pbp.filter(c("qb_dropback") == 1).group_by(team=c("defteam"), season=c("season")).agg(def_pass_epa=c("epa").mean())
traits = charted.select("team", "season", *OFF_TRAITS[:5], *DEF_TRAITS).join(team_off, on=["team", "season"]).join(team_def, on=["team", "season"])

# --- player-seasons and labels
lat = pl.read_parquet(rc.O / "latent.parquet").filter((c("half") == "all") & c("group").is_in(["WR", "TE", "RB"]))
cnt = pl.read_parquet(rc.O / "counts.parquet").filter(c("half") == "all")
# prior-season efficiency, shrunk toward the group's mean (20 targets or touches), from every row he had
eff = cnt.group_by("gsis_id", "season", "group").agg(c("epa_tgt").sum(), c("targets").sum(), c("epa_touch").sum(), c("touches").sum())
mu = eff.group_by("group").agg(mt=c("epa_tgt").sum() / c("targets").sum(), mo=c("epa_touch").sum() / c("touches").sum())
eff = eff.join(mu, on="group").with_columns(
    prior_eff=pl.when(c("group") == "RB").then((c("epa_touch") + 20 * c("mo")) / (c("touches") + 20)).otherwise((c("epa_tgt") + 20 * c("mt")) / (c("targets") + 20)))
eff_prev = eff.select("gsis_id", season=c("season") + 1, prior_eff=c("prior_eff"))
ps = (lat.join(cnt.select("gsis_id", "team", "season", "targets", "touches", "epa_tgt", "epa_touch"), on=["gsis_id", "team", "season"])
      .join(traits, on=["team", "season"]).join(eff_prev, on=["gsis_id", "season"], how="left")
      .with_columns(has_prior=c("prior_eff").is_not_null().cast(pl.Float64), lab=c("m1_lab"),
                    ts=pl.concat_str([c("team"), c("season").cast(pl.Utf8)]))
      .with_columns(c("prior_eff").fill_null(0.0),
                    vol=pl.when(c("group") == "RB").then(c("touches")).otherwise(c("targets")),
                    y=pl.when(c("group") == "RB").then(c("epa_touch") / c("touches").clip(1)).otherwise(c("epa_tgt") / c("targets").clip(1)))
      .filter(c("vol") > 0))

print("=" * 100)
print("H103 side bet: do roles cluster on schemes? (multinomial of M1 labels on the team's scheme traits, 5-fold CV)")
for gg in ["WR", "TE", "RB"]:
    d = ps.filter(c("group") == gg)
    X = d.select(OFF_TRAITS).to_numpy()
    y = d["lab"].to_numpy()

    def cvll(X_, y_=y):
        out = []
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(X_, y_):
            sc = StandardScaler().fit(X_[tr])
            m = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(X_[tr]), y_[tr])
            p = m.predict_proba(sc.transform(X_[te]))
            out.append(-np.log(np.clip(p[np.arange(len(te)), np.searchsorted(m.classes_, y_[te])], EPS, 1)))
        return np.concatenate(out).mean()

    real = cvll(X)
    # teams shuffled: each row gets another row's team traits (whole team-season blocks permuted)
    ts = d["ts"].to_numpy()
    u, inv = np.unique(ts, return_inverse=True)
    shuf = []
    for _ in range(50):
        perm = RNG.permutation(len(u))
        first = {k: i for i, k in enumerate(inv)}
        rows = np.array([first[perm[j]] for j in inv])
        shuf.append(cvll(X[rows]))
    shuf = np.array(shuf)
    print(f"  {gg}: n {d.height}, CV log loss {real:.4f}; teams shuffled {shuf.mean():.4f} (5-95% {np.percentile(shuf, 5):.4f} to {np.percentile(shuf, 95):.4f}); "
          f"real better than {np.mean(real < shuf):.0%} of shuffles")

print("\n" + "=" * 100)
print("H103 fit test: does a role's efficiency depend on the scheme? (B = A + label x scheme, leave-one-season-out)")
allg, allw, allcl = [], [], []
for gg in ["WR", "TE", "RB"]:
    d = ps.filter(c("group") == gg)
    labs = sorted(d["lab"].unique().to_list())
    y, w, seas = d["y"].to_numpy(), d["vol"].to_numpy().astype(float), d["season"].to_numpy()
    XA = design(d, labs, OFF_TRAITS, ["prior_eff", "has_prior"], False)
    XB = design(d, labs, OFF_TRAITS, ["prior_eff", "has_prior"], True)
    pa, pb = np.zeros(len(y)), np.zeros(len(y))
    for s in np.unique(seas):
        tr, te = seas != s, seas == s
        pa[te] = fit_pred(XA[tr], y[tr], w[tr], XA[te])
        pb[te] = fit_pred(XB[tr], y[tr], w[tr], XB[te])
    gain = (y - pa) ** 2 - (y - pb) ** 2
    est, lo, hi = boot(gain, w, d["ts"].to_numpy())
    mse_a = (w * (y - pa) ** 2).sum() / w.sum()
    print(f"  {gg}: n {d.height}, labels {len(labs)}; weighted MSE A {mse_a:.5f}; B's gain {est:+.6f} ({est / mse_a:+.2%} of A; 90% {lo:+.6f} to {hi:+.6f})")
    allg.append(gain), allw.append(w), allcl.append(d["ts"].to_numpy())
    in_sample(d, labs, OFF_TRAITS, ["prior_eff", "has_prior"], "y", "vol", "ts", gg)
est, lo, hi = boot(np.concatenate(allg), np.concatenate(allw), np.concatenate(allcl))
print(f"  pooled (WR, TE, RB): B's gain {est:+.6f} (90% {lo:+.6f} to {hi:+.6f})")
print("  -> H103 (fit):", "HELD" if lo > 0 else "FAILED")

# ---------------------------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("H106: archetype against the defense's scheme (WR, TE player-games with 3+ targets, 2019-2024)")
pg = (pbp.filter(c("receiver_player_id").is_not_null() & (c("season") >= 2019))
      .group_by("game_id", "season", "week", "posteam", "defteam", gsis_id=c("receiver_player_id")).agg(tg=pl.len(), epa=c("epa").sum())
      .filter(c("tg") >= 3).with_columns(y=c("epa") / c("tg")))
lab_prev = (pl.read_parquet(rc.O / "latent.parquet").filter(c("half") == "all")
            .join(cnt.select("gsis_id", "team", "season", "snaps"), on=["gsis_id", "team", "season"])
            .sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
            .select("gsis_id", "group", season=c("season") + 1, lab=c("m1_lab")))
opp = traits.select("season", "def_pass_epa", *DEF_TRAITS, defteam=c("team")).with_columns(season=c("season") + 1)
gm = (pg.join(lab_prev, on=["gsis_id", "season"], how="inner").filter(c("group").is_in(["WR", "TE"]))
      .join(eff_prev, on=["gsis_id", "season"], how="left").join(opp, on=["defteam", "season"], how="inner")
      .with_columns(has_prior=c("prior_eff").is_not_null().cast(pl.Float64), gw=pl.concat_str([c("season").cast(pl.Utf8), c("week").cast(pl.Utf8)], separator="_"))
      .with_columns(c("prior_eff").fill_null(0.0)).drop_nulls(DEF_TRAITS))
allg, allw, allcl = [], [], []
for gg in ["WR", "TE"]:
    d = gm.filter(c("group") == gg)
    labs = sorted(d["lab"].unique().to_list())
    y, w, seas = d["y"].to_numpy(), d["tg"].to_numpy().astype(float), d["season"].to_numpy()
    XA = design(d, labs, DEF_TRAITS, ["prior_eff", "has_prior", "def_pass_epa"], False)
    XB = design(d, labs, DEF_TRAITS, ["prior_eff", "has_prior", "def_pass_epa"], True)
    keep = seas >= 2020
    pa, pb = np.zeros(len(y)), np.zeros(len(y))
    for s in range(2020, 2025):
        tr, te = seas < s, seas == s
        pa[te] = fit_pred(XA[tr], y[tr], w[tr], XA[te])
        pb[te] = fit_pred(XB[tr], y[tr], w[tr], XB[te])
    gain = ((y - pa) ** 2 - (y - pb) ** 2)[keep]
    est, lo, hi = boot(gain, w[keep], d["gw"].to_numpy()[keep])
    mse_a = (w[keep] * (y[keep] - pa[keep]) ** 2).sum() / w[keep].sum()
    print(f"  {gg}: player-games {d.height:,} (scored {keep.sum():,}); weighted MSE A {mse_a:.4f}; B's gain {est:+.6f} ({est / mse_a:+.3%} of A; 90% {lo:+.6f} to {hi:+.6f})")
    allg.append(gain), allw.append(w[keep]), allcl.append(d["gw"].to_numpy()[keep])
    in_sample(d, labs, DEF_TRAITS, ["prior_eff", "has_prior", "def_pass_epa"], "y", "tg", "gw", gg)
est, lo, hi = boot(np.concatenate(allg), np.concatenate(allw), np.concatenate(allcl))
print(f"  pooled (WR, TE): B's gain {est:+.6f} (90% {lo:+.6f} to {hi:+.6f})")
print("  -> H106:", "HELD" if lo > 0 else "FAILED")
