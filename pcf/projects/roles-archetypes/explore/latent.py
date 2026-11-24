"""Roles exploration: the noise ceiling, H99 (on/off against own-snap features) and H100 (the three
latent methods, with and without measurables), pre-registered in EXPLORATION.md. Also I57.

Writes <interim>/roles/latent.parquet (every row's M1 label and probability, M2 and M3 coordinates,
for the full season and each half) for the H101-H106 scripts.

Run from pcf/projects/roles-archetypes/explore: PYTHONIOENCODING=utf-8 <venv python> latent.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import roles_common as rc
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.linear_model import LinearRegression
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

c = pl.col
RNG = np.random.default_rng(rc.CFG.seed)
T = rc.CFG.zone("tables")
B = 1000
TRAIN = 2020  # fit seasons 2016-2020, applied to all
K = 6

d = rc.load(halves=True)
KEY = ["gsis_id", "team", "season"]
A = d.filter(c("half") == "all")
OD = d.filter(c("half") == "odd").join(d.filter(c("half") == "even"), on=KEY, suffix="_e")


def r(x, y, w=None):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if w is None:
        w = np.ones(len(x))
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return np.sum(w * (x - mx) * (y - my)) / np.sqrt(np.sum(w * (x - mx) ** 2) * np.sum(w * (y - my) ** 2))


# consecutive seasons: one row per player-season (his team with most snaps), group kept
one = A.sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
NX = one.join(one.with_columns(season=c("season") - 1), on=["gsis_id", "season"], suffix="_n").filter(c("group") == c("group_n"))
NX = NX.with_columns(mover=(c("team") != c("team_n")))
print(f"rows: {A.height:,} player-team-seasons; consecutive pairs {NX.height:,} ({NX['mover'].sum():,} movers); halves {OD.height:,}")

print("=" * 110)
print("0. NOISE CEILING: split-half reliability (odd weeks against even weeks), median over groups, and range")
feats0 = ["snap_share", *rc.ADJ, *rc.OO, *rc.OFF_USAGE, *rc.DEF_USAGE]
for f in feats0:
    vals = []
    for g in rc.GROUPS:
        if (f in rc.OFF_USAGE and g not in rc.OFFENSE) or (f in rc.DEF_USAGE and g in rc.OFFENSE):
            continue
        x = OD.filter(c("group") == g)
        vals.append(r(x[f], x[f + "_e"]))
    print(f"  {f:14} median {np.median(vals):.2f} (range {min(vals):.2f} to {max(vals):.2f})")
print("  efficiency (the room for H103 and H106):")
for g, num, den in (("WR", "epa_tgt", "targets"), ("TE", "epa_tgt", "targets"), ("RB", "epa_touch", "touches")):
    x = OD.filter(c("group") == g)
    m = (x[num].sum() + x[num + "_e"].sum()) / (x[den].sum() + x[den + "_e"].sum())
    a_ = (x[num] + 10 * m) / (x[den] + 10)
    b_ = (x[num + "_e"] + 10 * m) / (x[den + "_e"] + 10)
    print(f"    {g}: EPA per {'target' if den == 'targets' else 'touch'} (shrunk, 10), split-half r {r(a_, b_):.2f}; season-to-season r {r(NX.filter(c('group') == g)[num] / NX.filter(c('group') == g)[den].clip(1), NX.filter(c('group') == g)[num + '_n'] / NX.filter(c('group') == g)[den + '_n'].clip(1)):.2f} (raw)")

print("=" * 110)
print("H99: on/off against own-snap (team-adjusted), the same dimension two ways: season-to-season r (and split-half)")
pids = NX["gsis_id"].unique().to_list()
pidx = {p: i for i, p in enumerate(pids)}
ix = np.array([pidx[p] for p in NX["gsis_id"].to_list()])
Wb = RNG.poisson(1.0, size=(B, len(pids))).astype(float)[:, ix]
diffs, diffs_b, rows = [], [], []
for dim in rc.DIMS:
    for g in rc.GROUPS:
        m = (NX["group"] == g).to_numpy()
        x = NX.filter(c("group") == g)
        r_oo, r_adj = r(x[f"oo_{dim}"], x[f"oo_{dim}_n"]), r(x[f"adj_{dim}"], x[f"adj_{dim}_n"])
        h = OD.filter(c("group") == g)
        s_oo, s_adj = r(h[f"oo_{dim}"], h[f"oo_{dim}_e"]), r(h[f"adj_{dim}"], h[f"adj_{dim}_e"])
        pt = (1 / (1 + np.exp(-x["snap_share"].to_numpy()))) < 0.6
        part = (r(x.filter(pl.Series(pt))[f"oo_{dim}"], x.filter(pl.Series(pt))[f"oo_{dim}_n"]) - r(x.filter(pl.Series(pt))[f"adj_{dim}"], x.filter(pl.Series(pt))[f"adj_{dim}_n"])) if pt.sum() > 30 else np.nan
        full = (r(x.filter(pl.Series(~pt))[f"oo_{dim}"], x.filter(pl.Series(~pt))[f"oo_{dim}_n"]) - r(x.filter(pl.Series(~pt))[f"adj_{dim}"], x.filter(pl.Series(~pt))[f"adj_{dim}_n"])) if (~pt).sum() > 30 else np.nan
        rows.append((dim, g, r_adj, r_oo, s_adj, s_oo, part, full, int(pt.sum()), int((~pt).sum())))
        diffs.append(r_oo - r_adj)
        bw = Wb[:, m]
        diffs_b.append([r(x[f"oo_{dim}"], x[f"oo_{dim}_n"], w) - r(x[f"adj_{dim}"], x[f"adj_{dim}_n"], w) for w in bw[:200]])
print(f"  {'dim':6} {'group':5} {'season r: own-adj':>17} {'on/off':>7} | {'split-half: own-adj':>19} {'on/off':>7} | gain part-time / every-down (n)")
for dim, g, ra, ro, sa, so, pt, fu, npt, nfu in rows:
    print(f"  {dim:6} {g:5} {ra:17.2f} {ro:7.2f} | {sa:19.2f} {so:7.2f} | {pt:+.2f} ({npt}) / {fu:+.2f} ({nfu})")
db = np.array(diffs_b).mean(0)
est = float(np.mean(diffs))
lo, hi = np.percentile(db, [5, 95])
print(f"  -> average gain in season-to-season r, on/off minus own-snap: {est:+.3f} (90% {lo:+.3f} to {hi:+.3f}; 200 player-bootstrap draws)")
verdict = "HELD" if lo > 0 and est >= 0.02 else "FAILED" if (hi < 0 or est < 0.02) else "UNCLEAR"
print(f"  -> H99: {verdict} (held needs the interval above 0 and a gain of 0.02+)")
pts = [x[6] for x in rows if not np.isnan(x[6])]
fus = [x[7] for x in rows if not np.isnan(x[7])]
print(f"  part-time players' average gain {np.mean(pts):+.3f}; every-down {np.mean(fus):+.3f}")

print("=" * 110)
print("H100: the three methods per group (fit 2016-2020, applied to all); with and without measurables")


def fit_method(g, method, meas, drop_snap=False):
    tr = A.filter((c("group") == g) & (c("season") <= TRAIN))
    if method == "M1":
        cols = rc.ROLE_TABLE[g] + (rc.MEAS[:3] if meas else [])
    elif method in ("M2", "FA"):
        cols = rc.full_set(g, meas)
    else:
        cols = rc.CELL_SET + (rc.MEAS[:3] if meas else [])
    if drop_snap:
        cols = [k for k in cols if k != "snap_share"]
    sc = StandardScaler().fit(tr.select(cols).to_numpy())
    Xtr = sc.transform(tr.select(cols).to_numpy())
    if method == "M1":
        bics = {k: GaussianMixture(k, n_init=3, random_state=0).fit(Xtr).bic(Xtr) for k in range(2, 7)}
        k = min(bics, key=bics.get)
        mdl = GaussianMixture(k, n_init=5, random_state=0).fit(Xtr)
    elif method == "FA":
        mdl = FactorAnalysis(K, rotation="varimax", random_state=0).fit(Xtr)
    else:
        mdl = PCA(K, random_state=0).fit(Xtr)
    return cols, sc, mdl


def transform(cols, sc, mdl, df, method):
    X = sc.transform(df.select(cols).to_numpy())
    if method == "M1":
        return mdl.predict(X), mdl.predict_proba(X).max(1)
    return mdl.transform(X), None


summary, store = [], []
for g in rc.GROUPS:
    for method in ("M1", "M2", "FA", "M3"):
        for meas in (False, True):
            if method == "FA" and meas:
                continue
            cols, sc, mdl = fit_method(g, method, meas)
            dg = d.filter(c("group") == g)
            z, prob = transform(cols, sc, mdl, dg, method)
            if method == "M1":
                lab = pl.DataFrame({"lab": z, "prob": prob})
                dd = pl.concat([dg.select(*KEY, "half"), lab], how="horizontal")
                o, e = dd.filter(c("half") == "odd"), dd.filter(c("half") == "even")
                oe = o.join(e, on=KEY, suffix="_e")
                flip = float((oe["lab"] != oe["lab_e"]).mean())
                aa = dd.filter(c("half") == "all")
                nx = aa.join(aa.with_columns(season=c("season") - 1), on=["gsis_id", "season"], suffix="_n")
                change = float((nx["lab"] != nx["lab_n"]).mean())
                Xtr = sc.transform(A.filter((c("group") == g) & (c("season") <= TRAIN)).select(cols).to_numpy())
                aris = [adjusted_rand_score(mdl.predict(Xtr), GaussianMixture(mdl.n_components, n_init=1, random_state=s_).fit(Xtr).predict(Xtr)) for s_ in range(1, 21)]
                summary.append(dict(group=g, method="M1" + ("+meas" if meas else ""), k=mdl.n_components, split_flip=flip, season_change=change, ari=float(np.median(aris))))
                if not meas:
                    store.append(dd.with_columns(group=pl.lit(g)).rename({"lab": "m1_lab", "prob": "m1_prob"}))
                    cen = sc.inverse_transform(mdl.means_)
                    print(f"  {g} M1 clusters (k={mdl.n_components} by BIC): centres " + "; ".join(f"[{i}] " + ", ".join(f"{cc}={v:.2f}" for cc, v in zip(cols, cen[i], strict=True)) + f" (n={int((aa['lab'] == i).sum())})" for i in range(mdl.n_components)))
                continue
            Z = pl.DataFrame(z[:, :K], schema=[f"z{i}" for i in range(K)])
            dd = pl.concat([dg.select(*KEY, "half", "snap_share"), Z], how="horizontal")
            oe = dd.filter(c("half") == "odd").join(dd.filter(c("half") == "even"), on=KEY, suffix="_e")
            aa = dd.filter(c("half") == "all")
            one_ = aa.join(A.select(*KEY, "snaps"), on=KEY).sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
            nx = one_.join(one_.with_columns(season=c("season") - 1), on=["gsis_id", "season"], suffix="_n").with_columns(mover=c("team") != c("team_n"))
            sh = [r(oe[f"z{i}"], oe[f"z{i}_e"]) for i in range(K)]
            ss = [r(nx[f"z{i}"], nx[f"z{i}_n"]) for i in range(K)]
            st, mv = nx.filter(~c("mover")), nx.filter(c("mover"))
            kept = [r(mv[f"z{i}"], mv[f"z{i}_n"]) / r(st[f"z{i}"], st[f"z{i}_n"]) if r(st[f"z{i}"], st[f"z{i}_n"]) > 0.1 else np.nan for i in range(4)]
            snapc = [abs(r(aa[f"z{i}"], aa["snap_share"])) for i in range(K)]
            res = []  # split-half repeat of each component after snap share is regressed out
            for i in range(4):
                lr = LinearRegression().fit(oe.select("snap_share").to_numpy(), oe[f"z{i}"].to_numpy())
                lr2 = LinearRegression().fit(oe.select("snap_share_e").to_numpy(), oe[f"z{i}_e"].to_numpy())
                res.append(r(oe[f"z{i}"] - lr.predict(oe.select("snap_share").to_numpy()), oe[f"z{i}_e"] - lr2.predict(oe.select("snap_share_e").to_numpy())))
            row = dict(group=g, method=method + ("+meas" if meas else ""), split=sh, season=ss, kept=kept, snapc=snapc, resid=res, n_ok=int(sum(x >= 0.5 for x in sh)))
            if method == "M2" and not meas:
                tr = A.filter((c("group") == g) & (c("season") <= TRAIN))
                Xtr = sc.transform(tr.select(cols).to_numpy())
                congr = []
                for _ in range(200):
                    i_ = RNG.integers(0, len(Xtr), len(Xtr))
                    pb = PCA(K, random_state=0).fit(Xtr[i_])
                    congr.append([max(abs(np.dot(mdl.components_[j], pb.components_[q])) for q in range(4)) for j in range(4)])
                row["congruence"] = np.median(np.array(congr), 0).tolist()
                load = mdl.components_
                print(f"  {g} M2 PCA components (explained {mdl.explained_variance_ratio_[:K].round(2).tolist()}); top loadings: " + " | ".join(
                    f"z{j}: " + ", ".join(f"{cols[q]}{'+' if load[j, q] > 0 else '-'}" for q in np.argsort(-abs(load[j]))[:3]) for j in range(4)))
                store.append(dd.drop("snap_share").rename({f"z{i}": f"m2_z{i}" for i in range(K)}).with_columns(group=pl.lit(g)))
                # H101's sensitivity: refit without snap share
                cols2, sc2, mdl2 = fit_method(g, "M2", False, drop_snap=True)
                z2, _ = transform(cols2, sc2, mdl2, dg, "M2")
                store.append(pl.concat([dg.select(*KEY, "half"), pl.DataFrame(z2[:, :K], schema=[f"m2ns_z{i}" for i in range(K)])], how="horizontal").with_columns(group=pl.lit(g)))
            if method == "M3" and not meas:
                store.append(dd.drop("snap_share").rename({f"z{i}": f"m3_z{i}" for i in range(K)}).with_columns(group=pl.lit(g)))
            summary.append(row)

print("\n  method comparison (first 6 components): split-half r, season r, movers' kept share (first 4), |corr| with snap share, split-half after snap share removed (first 4)")
for row in summary:
    if row["method"].startswith("M1"):
        print(f"  {row['group']:4} {row['method']:8} k={row['k']} label differs between halves {row['split_flip']:.0%}, between seasons {row['season_change']:.0%}; seeds' agreement (ARI) {row['ari']:.2f}")
    else:
        extra = f"; congruence (bootstrap, first 4) {np.round(row['congruence'], 2).tolist()}" if "congruence" in row else ""
        print(f"  {row['group']:4} {row['method']:8} split {np.round(row['split'], 2).tolist()} (>=0.5: {row['n_ok']}) season {np.round(row['season'], 2).tolist()} kept {np.round(row['kept'], 2).tolist()} snap|r| {np.round(row['snapc'], 2).tolist()} resid {np.round(row['resid'], 2).tolist()}{extra}")
for meth in ("M2", "M2+meas", "FA", "M3", "M3+meas"):
    rr = [x for x in summary if x["method"] == meth]
    print(f"  {meth:8}: median over groups of the first 4 components' split-half r {np.median([np.median(x['split'][:4]) for x in rr]):.2f}; season r {np.median([np.median(x['season'][:4]) for x in rr]):.2f}; components with split-half >= 0.5 (median group) {np.median([x['n_ok'] for x in rr]):.0f} of 6; kept {np.nanmedian([np.nanmedian(x['kept']) for x in rr]):.2f}")
for meth in ("M1", "M1+meas"):
    rr = [x for x in summary if x["method"] == meth]
    print(f"  {meth:8}: median label flip between halves {np.median([x['split_flip'] for x in rr]):.0%}, between seasons {np.median([x['season_change'] for x in rr]):.0%}, seeds' ARI {np.median([x['ari'] for x in rr]):.2f}")
cons_a = np.median([x["n_ok"] for x in summary if x["method"] == "M2"]) >= 4

# H100 (b): recovering a held-out role measure, the vertical share of targeted routes
part = pl.concat([pl.read_parquet(T / "play" / "participation" / f"season={s}" / "data.parquet", columns=["game_id", "play_id", "route"]) for s in range(2016, 2025)])
pb = pl.concat([pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=["game_id", "play_id", "season", "season_type", "receiver_player_id", "posteam"]) for s in range(2016, 2025)])
rt = (part.join(pb.filter(c("season_type") == "REG"), on=["game_id", "play_id"]).filter(c("route").is_not_null() & (c("route") != "") & c("receiver_player_id").is_not_null())
      .group_by(gsis_id=c("receiver_player_id"), team=c("posteam"), season=c("season")).agg(rn=pl.len(), vert=c("route").is_in(["GO", "POST", "CORNER", "WHEEL"]).sum()))
mv = rt["vert"].sum() / rt["rn"].sum()
rt = rt.with_columns(vshare=(c("vert") + 10 * mv) / (c("rn") + 10))
M2 = pl.concat([x for x in store if "m2_z0" in x.columns]).filter(c("half") == "all")
rec = 0
print("\n  H100 (b): the vertical share of targeted routes (held out), cross-validated R² from M2's 6 components (folds by player)")
for g in ("WR", "TE", "RB"):
    x = M2.filter(c("group") == g).join(rt, on=KEY).filter(c("rn") >= 10)
    X, y = x.select([f"m2_z{i}" for i in range(K)]).to_numpy(), x["vshare"].to_numpy()
    pred = np.zeros(len(y))
    for tr_, te_ in GroupKFold(5).split(X, y, x["gsis_id"].to_numpy()):
        pred[te_] = LinearRegression().fit(X[tr_], y[tr_]).predict(X[te_])
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    rec += r2 >= 0.2
    print(f"    {g}: {x.height} player-seasons, R² {r2:.2f}")
print(f"  -> H100: (a) consistent: {cons_a}; (b) predicts roles in {rec} of 3 groups (needs 2): {'HELD' if cons_a and rec >= 2 else 'HELD IN PART' if (cons_a or rec >= 2) else 'FAILED'}")

# I57: the vertical share repeats season to season (receivers)
rw = rt.join(A.filter(c("group") == "WR").select(KEY), on=KEY).filter(c("rn") >= 20)
rw1 = rw.sort("rn", descending=True).unique(["gsis_id", "season"])
rn = rw1.join(rw1.with_columns(season=c("season") - 1), on=["gsis_id", "season"], suffix="_n")
print(f"\nI57: a receiver's vertical share of targeted routes, season to season r {r(rn['vshare'], rn['vshare_n']):.2f} ({rn.height} pairs, 20+ targeted routes both seasons)")

allst = {}
for x in store:
    k = [col for col in x.columns if col.startswith(("m1_", "m2_", "m2ns_", "m3_"))][0][:3]
    allst.setdefault(k, []).append(x)
out = None
for k, xs in allst.items():
    df = pl.concat(xs, how="diagonal_relaxed")
    out = df if out is None else out.join(df.drop("group"), on=[*KEY, "half"], how="left")
out.write_parquet(rc.O / "latent.parquet")
print("saved latent.parquet", out.shape)
