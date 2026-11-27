"""Aging, method 3 (EXPLORATION.md, exploratory): career phases as hidden states. The HMM against its simple twin,
H117's "told apart in advance" half, H119 (late-career comebacks) and I153 (historical analogs).

Run from pcf/:  python projects/aging/explore/m3_phases.py   (writes m3_phases.txt)

Rows are survivors' season pairs at the four offensive positions with efficiency in both seasons: the change in pulled
usage and pulled efficiency from s to s + 1. Technical calls: one model for all four positions (changes standardized by
position on seasons before 2010); the hidden-state model is refit every three target seasons (2010, 2013, ... 2022).
"""

# ruff: noqa: E501
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

os.environ["AGING_FORM"] = "smooth"
sys.path.insert(0, str(Path(__file__).parent))
import m1_curves as m1  # noqa: E402
from aging_common import OFF, Say, pairs, wls  # noqa: E402
from m2_load import fmt, pooled  # noqa: E402

c = pl.col
RNG = np.random.default_rng(3)
say = Say(Path(__file__).with_suffix(".txt"))
K = 5
NAMES = ["rising", "steady", "usage-only decline", "full decline", "efficiency rebound"]
INIT = np.array([[1.0, 0.3], [0.0, 0.0], [-1.0, 0.0], [-1.0, -1.0], [-0.3, 1.0]])


def band(age):
    return np.where(age < 26, 0, np.where(age < 30, 1, 2))


# ---------------------------------------------------------------- the hidden-state model
def logemit(X, mu, var):
    return -0.5 * (((X[:, None, :] - mu[None]) ** 2) / var[None] + np.log(2 * np.pi * var[None])).sum(-1)


def forward(le, bands, pi, A):
    """Scaled forward pass for one sequence; returns filtered probabilities and the log likelihood."""
    T = len(le)
    al = np.zeros((T, K))
    ll = 0.0
    for t in range(T):
        p = pi if t == 0 else al[t - 1] @ A[bands[t]]
        m = le[t].max()
        a = p * np.exp(le[t] - m)
        s = a.sum()
        al[t] = a / s
        ll += np.log(s) + m
    return al, ll


def fit_hmm(seqs, iters=25):
    """EM for a Gaussian (diagonal) hidden Markov model whose transitions depend on the age band at each step."""
    mu, var = INIT.copy(), np.ones((K, 2))
    pi = np.full(K, 1 / K)
    A = np.tile(np.full((K, K), 0.1) + np.eye(K) * 0.5, (3, 1, 1))
    A /= A.sum(-1, keepdims=True)
    for _ in range(iters):
        S0, S1, S2, N = np.zeros(K), np.zeros((K, 2)), np.zeros((K, 2)), np.zeros(K)
        Xi = np.zeros((3, K, K)) + 1e-3
        P0 = np.zeros(K) + 1e-3
        for X, b in seqs:
            le = logemit(X, mu, var)
            al, _ = forward(le, b, pi, A)
            T = len(X)
            be = np.ones((T, K))
            em = np.exp(le - le.max(1, keepdims=True))
            for t in range(T - 2, -1, -1):
                v = A[b[t + 1]] @ (em[t + 1] * be[t + 1])
                be[t] = v / v.sum()
            g = al * be
            g /= g.sum(1, keepdims=True)
            for t in range(T - 1):
                x = al[t][:, None] * A[b[t + 1]] * (em[t + 1] * be[t + 1])[None]
                Xi[b[t + 1]] += x / x.sum()
            P0 += g[0]
            N += g.sum(0)
            S1 += g.T @ X
            S2 += g.T @ X**2
        mu = S1 / N[:, None]
        var = np.maximum(S2 / N[:, None] - mu**2, 0.05)
        pi = P0 / P0.sum()
        A = Xi / Xi.sum(-1, keepdims=True)
    return mu, var, pi, A


def obs_table(d):
    """Survivor pairs at the offensive positions with efficiency both seasons: changes standardized by position."""
    x = d.filter(c("pos").is_in(OFF) & ~c("gone") & c("pu2").is_not_null() & c("pe").is_not_null() & c("pe2").is_not_null() & (c("n2") > 0))
    x = x.with_columns(du=c("pu2") - c("pu"), de=c("pe2") - c("pe"), T=c("season") + 1, wde=2 / (1 / c("e_den").clip(1) + 1 / c("n2").clip(1)))
    sd = x.filter(c("T") < 2010).group_by("pos").agg(sdu=c("du").std(), sde=c("de").std())
    x = x.join(sd, on="pos").with_columns(zu=c("du") / c("sdu"), ze=c("de") / c("sde"), age1=c("age") + 1)
    return x.sort("gsis_id", "T")


def sequences(x, upto):
    """Each player's runs of consecutive target seasons up to `upto` (inclusive)."""
    z = x.filter(c("T") <= upto).with_columns(run=(c("T").diff().over("gsis_id").fill_null(1) != 1).cum_sum().over("gsis_id"))
    out = {}
    for (pid, run), g in z.group_by(["gsis_id", "run"], maintain_order=True):
        out.setdefault(pid, []).append((g.select("zu", "ze").to_numpy(), band(g["age1"].to_numpy()), g["T"].to_numpy()))
    return out


def hmm_forecasts(x):
    """For each target season T (2010-2024): the state chances after his last pair (ending T-1), the next state's
    chances by his age band, and the forecast change (the mix of the states' means), in standardized units."""
    rows = []
    for T in range(2010, 2025):
        if T in (2010, 2013, 2016, 2019, 2022):
            seqs = [s[:2] for v in sequences(x, T - 1).values() for s in v if len(s[0]) >= 1]
            mu, var, pi, A = fit_hmm(seqs)
            fits = (mu, var, pi, A)
            if T == 2022:
                last_fit = fits
        mu, var, pi, A = fits
        te = x.filter(c("T") == T)
        prev = sequences(x.filter(c("gsis_id").is_in(te["gsis_id"].implode())), T - 1)
        for r in te.iter_rows(named=True):
            filt = None
            for X, b, Ts in prev.get(r["gsis_id"], []):
                if Ts[-1] == T - 1:
                    al, _ = forward(logemit(X, mu, var), b, pi, A)
                    filt = al[-1]
            nxt = (filt @ A[band(np.array([r["age1"]]))[0]]) if filt is not None else pi
            f = nxt @ mu
            rows.append({"gsis_id": r["gsis_id"], "T": T, "h_zu": f[0], "h_ze": f[1], **{f"p{k}": (filt[k] if filt is not None else np.nan) for k in range(K)},
                         **{f"q{k}": nxt[k] for k in range(K)}, "has_prev": filt is not None})
    return pl.DataFrame(rows), last_fit


def main() -> None:
    d = pairs()
    x = obs_table(d)
    say("# Method 3: career phases as hidden states (2026-11-25)", "",
        f"Survivor pairs at QB, RB, WR and TE with efficiency in both seasons: {x.height:,} ({x['gsis_id'].n_unique():,} players). Each is a change in pulled usage and pulled",
        "efficiency, standardized by position. A five-state Gaussian hidden Markov model with transitions by age band (under 26, 26-29, 30+), started at rising, steady,",
        "usage-only decline, full decline and efficiency rebound, then learned by EM; one model for the four positions, refit every three target seasons.", "")
    H, (mu, var, pi, A) = hmm_forecasts(x)
    say("## The states the model learned (fit on targets before 2022; standardized changes)", "",
        "| Start | Mean usage change | Mean efficiency change | Spread (usage, efficiency) | Stay chance: under 26, 26-29, 30+ |", "|---|---|---|---|---|")
    for k in range(K):
        say(f"| {NAMES[k]} | {mu[k, 0]:+.2f} | {mu[k, 1]:+.2f} | {np.sqrt(var[k, 0]):.2f}, {np.sqrt(var[k, 1]):.2f} | {A[0, k, k]:.2f}, {A[1, k, k]:.2f}, {A[2, k, k]:.2f} |")
    reb = int(np.argmax(mu[:, 1] - mu[:, 0]))  # the state with the most efficiency gain against usage: read as the rebound
    say("", f"The rebound state (the most efficiency gain for its usage change): {NAMES[reb]} as started.", "")

    # ---------------- the twin and the analogs
    x = x.sort("gsis_id", "T").with_columns(
        l1u=c("zu").shift(1).over("gsis_id"), l1e=c("ze").shift(1).over("gsis_id"), l2u=c("zu").shift(2).over("gsis_id"), l2e=c("ze").shift(2).over("gsis_id"),
        lT=c("T").shift(1).over("gsis_id"))
    x = x.with_columns([pl.when(c("lT") == c("T") - 1).then(c(v)).otherwise(0.0).fill_null(0.0).alias(v) for v in ("l1u", "l1e", "l2u", "l2e")])
    x = x.join(H, on=["gsis_id", "T"], how="left")
    out = []
    for T in range(2010, 2025):
        tr, te = x.filter(c("T") < T), x.filter(c("T") == T)
        L = ["l1u", "l1e", "l2u", "l2e"]
        km = KMeans(K, n_init=5, random_state=0).fit(tr.select(L).to_numpy())
        ctr, cte = km.labels_, km.predict(te.select(L).to_numpy())

        def des(z, cl):
            a = (z["age1"].clip(21, 36).to_numpy() - 27) / 5
            return np.column_stack([*(cl == k for k in range(K)), a, a**2, a**3]).astype(float)

        def age_only(z):
            a = (z["age1"].clip(21, 36).to_numpy() - 27) / 5
            return np.column_stack([np.ones(z.height), a, a**2, a**3])

        def levels(z, extra=None):
            # the fair floor: age plus the same inputs the analogs see (his levels and last changes), linear
            a = (z["age1"].clip(21, 36).to_numpy() - 27) / 5
            cols = [np.ones(z.height), a, a**2, a**3, z["pu"].to_numpy() / 0.05, z["pe"].to_numpy() / 0.1, z["l1u"].to_numpy(), z["l1e"].to_numpy()]
            return np.column_stack(cols + ([] if extra is None else extra)).astype(float)

        pr = {}
        for kind, y, w in (("u", "zu", None), ("e", "ze", "wde")):
            W = tr[w].to_numpy() if w else np.ones(tr.height)
            b = wls(des(tr, ctr), tr[y].to_numpy(), W, 1e-3)
            pr[f"t_{kind}"] = des(te, cte) @ b
            b0 = wls(age_only(tr), tr[y].to_numpy(), W, 1e-3)
            pr[f"a_{kind}"] = age_only(te) @ b0
            b2 = wls(levels(tr), tr[y].to_numpy(), W, 1e-3)
            pr[f"l_{kind}"] = levels(te) @ b2
            b3 = wls(levels(tr, [*(ctr == k for k in range(K))]), tr[y].to_numpy(), W, 1e-3)
            pr[f"lt_{kind}"] = levels(te, [*(cte == k for k in range(K))]) @ b3
            okh = tr["h_zu"].is_not_null().to_numpy()
            if okh.sum() > 200:
                b4 = wls(levels(tr.filter(pl.Series(okh)), [tr.filter(pl.Series(okh))[f"h_z{kind}"].to_numpy()]), tr[y].to_numpy()[okh], W[okh], 1e-3)
                pr[f"lh_{kind}"] = levels(te, [te[f"h_z{kind}"].fill_null(0).to_numpy()]) @ b4
            else:
                pr[f"lh_{kind}"] = pr[f"l_{kind}"]
            # the hidden-state forecast with the same age terms beside it (a side reading)
            Ht = np.column_stack([age_only(tr), tr[f"h_z{kind}"].fill_null(0).to_numpy()]) if tr["h_zu"].is_not_null().sum() > 200 else None
            if Ht is not None:
                ok = tr["h_zu"].is_not_null().to_numpy()
                b1 = wls(Ht[ok], tr[y].to_numpy()[ok], W[ok], 1e-3)
                pr[f"ha_{kind}"] = np.column_stack([age_only(te), te[f"h_z{kind}"].fill_null(0).to_numpy()]) @ b1
            else:
                pr[f"ha_{kind}"] = pr[f"a_{kind}"]
        # I153: the 20 nearest past player-seasons on age, levels and last changes
        F = ["age1", "pu", "pe", "l1u", "l1e"]
        M = tr.select(F).to_numpy()
        m_, s_ = M.mean(0), M.std(0) + 1e-9
        Mz, Q = (M - m_) / s_, (te.select(F).to_numpy() - m_) / s_
        dist = ((Q[:, None, :] - Mz[None]) ** 2).sum(-1)
        nn = np.argpartition(dist, 20, axis=1)[:, :20]
        pr["n_u"] = tr["zu"].to_numpy()[nn].mean(1)
        pr["n_e"] = tr["ze"].to_numpy()[nn].mean(1)
        out.append(te.with_columns(**{k: pl.Series(v) for k, v in pr.items()}, cl=pl.Series(cte)))
    Fx = pl.concat(out)

    say("## The hidden-state model against its twin (walk-forward, targets 2010-2024; pooled over the four positions, each weighing the same)", "",
        "The twin: k-means (5 clusters) on his last two seasons' changes, plus a smooth age term. Age only: the smooth age term alone. Scores are on standardized changes",
        "(efficiency weighted by the harmonic mean of both seasons' opportunities).", "",
        "| Comparison | Usage change | Efficiency change |", "|---|---|---|")
    fs = {}
    for kind, y, w in (("u", "zu", None), ("e", "ze", "wde")):
        fs[kind] = {p: Fx.filter(c("pos") == p).with_columns(y=c(y), w=(c(w) if w else pl.lit(1.0)), hmm=c(f"h_z{kind}"), twin=c(f"t_{kind}"), age=c(f"a_{kind}"),
                                                            hage=c(f"ha_{kind}"), nbr=c(f"n_{kind}"),
                                                            lev=c(f"l_{kind}"), levt=c(f"lt_{kind}"), levh=c(f"lh_{kind}")) for p in OFF}
    res = {}
    for new, old, label in (("hmm", "twin", "Hidden states against the twin"), ("twin", "age", "The twin against age only"), ("hmm", "age", "Hidden states against age only"),
                            ("hage", "age", "Hidden states plus age against age only"), ("nbr", "twin", "I153 analogs against the twin"), ("nbr", "age", "I153 analogs against age only"),
                            ("lev", "age", "Levels (age, his levels and last changes, linear) against age only"), ("levh", "lev", "Levels plus the hidden-state forecast against levels"),
                            ("levt", "lev", "Levels plus the twin's clusters against levels"), ("nbr", "lev", "I153 analogs against levels (the same inputs, linear)")):
        r = [pooled(fs[k], new, old) for k in ("u", "e")]
        res[(new, old)] = r
        say(f"| {label} | {fmt(r[0])} | {fmt(r[1])} |")
    hm = res[("hmm", "twin")]
    say("", f"The bet (the hidden-state model beats the twin clearly, usage or efficiency): {'yes' if hm[0][1] > 0 or hm[1][1] > 0 else 'no'}.", "")

    # ---------------- H117: told apart in advance
    peaks = dict(p.split(":") for p in (m1.CACHE / "peaks.txt").read_text().split(","))
    dec = Fx.filter((c("age") >= c("pos").replace_strict({k: int(v) for k, v in peaks.items()}, return_dtype=pl.Float64)) & (c("u2") <= c("u") * 2 / 3) & (c("e_den") >= 10) & (c("n2") >= 10))
    dec = dec.with_columns(kept=(c("de") >= 0).cast(pl.Int32), star1=(c("star") == "star").cast(pl.Float64), mil=(c("cm_pass") + c("cm_rush")).log1p())
    base = ["age", "pu", "pe", "l1u", "l1e", "star1", "mil"]
    pc = [f"p{k}" for k in range(K)]
    say("## H117, the \"told apart in advance\" half", "",
        f"Usage decliners (as in method 1) with an efficiency change in both seasons: {dec.height}. Kept efficiency: {dec['kept'].mean():.0%}. A logistic on what is known before the",
        "decline season (age, usage and efficiency levels, last season's changes, star status, mileage; then the model's state chances added), walk-forward by target season.", "")
    pa, pb = [], []
    for T in range(2010, 2025):
        tr, te = dec.filter(c("T") < T), dec.filter(c("T") == T)
        if tr.height < 60 or te.height == 0:
            continue
        for cols, store in ((base, pa), (base + pc, pb)):
            A_ = np.nan_to_num(tr.select(cols).fill_null(0).to_numpy().astype(float))
            m_, s_ = A_.mean(0), A_.std(0) + 1e-9
            lg = LogisticRegression(C=0.5, max_iter=2000).fit((A_ - m_) / s_, tr["kept"].to_numpy())
            store.append(te.select("gsis_id", "kept").with_columns(p=pl.Series(lg.predict_proba((np.nan_to_num(te.select(cols).fill_null(0).to_numpy().astype(float)) - m_) / s_)[:, 1])))
    for nm, store in (("without the states", pa), ("with the states", pb)):
        z = pl.concat(store)
        ids = z["gsis_id"].unique().to_numpy()
        grp = {i: np.flatnonzero(z["gsis_id"].to_numpy() == i) for i in ids}
        yv, pv = z["kept"].to_numpy(), z["p"].to_numpy()
        bs = []
        for _ in range(500):
            ix = np.concatenate([grp[i] for i in RNG.choice(ids, len(ids))])
            if 0 < yv[ix].mean() < 1:
                bs.append(roc_auc_score(yv[ix], pv[ix]))
        say(f"- {nm}: held-out AUC {roc_auc_score(yv, pv):.3f} (90% {np.quantile(bs, 0.05):.3f} to {np.quantile(bs, 0.95):.3f}), {z.height} decline seasons.")

    # ---------------- H119: late-career comebacks
    # the leftover: next season's centred efficiency less method 1's age-model forecast (smooth form), for survivors with efficiency
    ef = []
    for pos in OFF:
        r_ = m1.rows(d, pos, "e")
        ef.append(m1.walk(r_, {"age": {"int": 1, "x": 1, "age": 1}}, 2010).select("gsis_id", "T", "y", "w", "age", left=c("y") - c("age")))
    ef = pl.concat(ef)
    # a full-decline season: from s-1 to s, pulled usage and efficiency both fell, at or past the position's usage peak
    fd = x.select("gsis_id", "pos", "age1", T=c("T") + 1, fd_u=c("du"), fd_e=c("de"))
    fd = fd.filter((c("fd_u") < 0) & (c("fd_e") < 0) & (c("age1") >= c("pos").replace_strict({k: int(v) for k, v in peaks.items()}, return_dtype=pl.Float64)))
    L = ef.join(fd.select("gsis_id", "T", "fd_u", "fd_e"), on=["gsis_id", "T"], how="left").with_columns(full=c("fd_u").is_not_null())
    L = L.join(Fx.select("gsis_id", "T", *[f"q{k}" for k in range(K)], "t_e", "n_e"), on=["gsis_id", "T"], how="left")
    say("", "## H119: late-career comebacks", "",
        "After a full-decline season (pulled usage and efficiency both fell from s-1 to s, at or past the position's usage peak), is next season's efficiency above what method 1's",
        "age model already expects (its own pull-back included)? The leftover is next season's centred efficiency less that forecast, weighted by next season's opportunities.", "")
    for nm, z in (("after a full decline", L.filter(c("full"))), ("every other season", L.filter(~c("full")))):
        ids = z["gsis_id"].unique().to_numpy()
        pp = z.group_by("gsis_id").agg(a=(c("w") * c("left")).sum(), b=c("w").sum())
        a_, b_ = pp["a"].to_numpy(), pp["b"].to_numpy()
        idx = RNG.integers(0, len(a_), (1000, len(a_)))
        bs = a_[idx].sum(1) / b_[idx].sum(1)
        say(f"- {nm}: {z.height} seasons, mean leftover {a_.sum() / b_.sum():+.4f} EPA an opportunity (90% {np.quantile(bs, 0.05):+.4f} to {np.quantile(bs, 0.95):+.4f}); share above 0: {(z['left'] > 0).mean():.0%}")
    zf = L.filter(c("full") & c(f"q{reb}").is_not_null())
    for nm, col in (("the rebound state's chance", f"q{reb}"), ("the twin's efficiency forecast", "t_e"), ("the analogs' efficiency forecast", "n_e")):
        v, lft = zf[col].to_numpy(), zf["left"].to_numpy()
        ids = zf["gsis_id"].to_numpy()
        u_ = np.unique(ids)
        grp = {i: np.flatnonzero(ids == i) for i in u_}
        bs = []
        for _ in range(1000):
            ix = np.concatenate([grp[i] for i in RNG.choice(u_, len(u_))])
            bs.append(np.corrcoef(v[ix], lft[ix])[0, 1])
        say(f"- Forecastable? {nm} against the leftover, after full declines (held out, {zf.height}): correlation {np.corrcoef(v, lft)[0, 1]:+.3f} (90% {np.nanquantile(bs, 0.05):+.3f} to {np.nanquantile(bs, 0.95):+.3f})")

    # ---------------- the case against: is it the pull-back again?
    say("", "## Checks: is it the pull-back?", "",
        "H117's label (efficiency change at or above 0) and H119's leftover both carry the pull-back to the mean: a season that was high falls next season, and one that was low",
        "rises, from noise alone. Three checks.", "")
    # (a) H117 with this season's pulled efficiency alone
    za = []
    for T in range(2010, 2025):
        tr, te = dec.filter(c("T") < T), dec.filter(c("T") == T)
        if tr.height < 60 or te.height == 0:
            continue
        lg = LogisticRegression(max_iter=2000).fit(tr.select("pe").to_numpy(), tr["kept"].to_numpy())
        za.append(te.select("kept").with_columns(p=pl.Series(lg.predict_proba(te.select("pe").to_numpy())[:, 1])))
    za = pl.concat(za)
    say(f"- H117 with his pulled efficiency this season alone: held-out AUC {roc_auc_score(za['kept'].to_numpy(), za['p'].to_numpy()):.3f}.")
    # (b) H117 with the label taken beyond the age model's expectation: kept = next season's efficiency at or above method 1's forecast
    db = dec.join(ef.select("gsis_id", "T", "left"), on=["gsis_id", "T"], how="inner").with_columns(kept=(c("left") >= 0).cast(pl.Int32))
    zb = []
    for T in range(2010, 2025):
        tr, te = db.filter(c("T") < T), db.filter(c("T") == T)
        if tr.height < 60 or te.height == 0:
            continue
        A_ = np.nan_to_num(tr.select(base + pc).fill_null(0).to_numpy().astype(float))
        m_, s_ = A_.mean(0), A_.std(0) + 1e-9
        lg = LogisticRegression(C=0.5, max_iter=2000).fit((A_ - m_) / s_, tr["kept"].to_numpy())
        zb.append(te.select("gsis_id", "kept").with_columns(p=pl.Series(lg.predict_proba((np.nan_to_num(te.select(base + pc).fill_null(0).to_numpy().astype(float)) - m_) / s_)[:, 1])))
    zb = pl.concat(zb)
    ids = zb["gsis_id"].to_numpy()
    u_ = np.unique(ids)
    grp = {i: np.flatnonzero(ids == i) for i in u_}
    yv, pv = zb["kept"].to_numpy(), zb["p"].to_numpy()
    bs = [roc_auc_score(yv[ix], pv[ix]) for ix in (np.concatenate([grp[i] for i in RNG.choice(u_, len(u_))]) for _ in range(500))]
    say(f"- H117 with the label beyond expectation (next season's efficiency at or above the age model's forecast; kept: {yv.mean():.0%}): held-out AUC {roc_auc_score(yv, pv):.3f} "
        f"(90% {np.quantile(bs, 0.05):.3f} to {np.quantile(bs, 0.95):.3f}), {zb.height} decline seasons, every input and the state chances.")
    # (c) H119 against a forecast that knows his own history (method 2's H: age, this season, his last two seasons, years in the league)
    import m2_load as m2

    dh = d.with_columns(entry=pl.coalesce(c("entry"), c("season")))
    eh = pl.concat([m2.walk(m2.rows(dh, pos, "e"), {"H": ["age", "hist"]}, 2010).select("gsis_id", "T", "w", lefth=c("y") - c("H")) for pos in OFF])
    Lh = eh.join(L.select("gsis_id", "T", "full"), on=["gsis_id", "T"], how="inner")
    for nm, z in (("after a full decline", Lh.filter(c("full"))), ("every other season", Lh.filter(~c("full")))):
        pp = z.group_by("gsis_id").agg(a=(c("w") * c("lefth")).sum(), b=c("w").sum())
        a_, b_ = pp["a"].to_numpy(), pp["b"].to_numpy()
        idx = RNG.integers(0, len(a_), (1000, len(a_)))
        bs = a_[idx].sum(1) / b_[idx].sum(1)
        say(f"- H119 against a forecast that knows his last two seasons, {nm}: {z.height} seasons, mean leftover {a_.sum() / b_.sum():+.4f} (90% {np.quantile(bs, 0.05):+.4f} to {np.quantile(bs, 0.95):+.4f})")
    say.save()


if __name__ == "__main__":
    main()
