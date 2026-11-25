"""Vacated opportunity exploration: the noise ceiling and H109 (pre-registered in EXPLORATION.md).

Method 1a, the proportional split (the simpler side); 1b, with or without; no change; against method 2, the
CEO's plus-minus for all players: a ridge on every player-game in the five groups, each player's share against
his own season average, inputs = each absent top teammate's share, in a pooled part per pair of groups and a
pair part per player and same-group top teammate. Scored on stayers' next-season share after departures, 90%
team bootstrap. Side bets: target and carry share; weekly absences (walk-forward).

Run from pcf/projects/vacated-opportunity/explore: PYTHONIOENCODING=utf-8 <venv python> h109_plus_minus.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import scipy.sparse as sp
import vo_common as vc
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

c = pl.col
RNG = np.random.default_rng(vc.CFG.seed)
B = 2000
GRID = [1, 3, 10, 30, 100, 300, 1000]
G = vc.GROUPS
POOL_KEYS = [f"{a}>{b}" for a in G for b in G]

pg, tg, ps = vc.load()
teams = sorted(tg["team"].unique().to_list())
TIX = {t: i for i, t in enumerate(teams)}
WB = RNG.poisson(1.0, size=(B, len(teams))).astype(float)  # team bootstrap weights

# --- absences: a top player's team-games between his first and last game, in which he had no snap
tops = ps.filter(c("top")).select(j="gsis_id", team="team", season="season", group_j="group", w_share="share", w_tgt="tgt_share", w_car="car_share", first_wk="first_wk", last_wk="last_wk")
absent = tops.join(tg.select("game_id", "team", "season", "week"), on=["team", "season"]).filter(c("week").is_between(c("first_wk"), c("last_wk")))
absent = absent.join(pg.select(j="gsis_id", game_id="game_id"), on=["j", "game_id"], how="anti")
print(f"absences of top players (games missed between his first and last game), 2016-2024: {absent.height:,}")
print("  per top player-season, by group:", absent.group_by("group_j").agg(n=pl.len()).join(tops.group_by("group_j").len(), on="group_j").with_columns(per=(c("n") / c("len")).round(2)).sort("group_j").select("group_j", "per").to_dicts())


def design(rows: pl.DataFrame, ab: pl.DataFrame, ycol: str, wcol: str):
    """rows: player-games (gsis_id, team, season, game_id, group, ycol); ab: absences with a value column wcol.
    Returns the within-player-season design (csr), y, the column keys."""
    rows = rows.with_row_index("idx")
    psk = pl.concat_str(c("gsis_id"), c("team"), c("season").cast(pl.Utf8), separator="|")
    rows = rows.with_columns(psk=psk)
    pr = rows.select("idx", "gsis_id", "team", "season", "game_id", "group", "psk").join(ab.select("j", "team", "game_id", "group_j", w=c(wcol)), on=["team", "game_id"]).filter(c("j") != c("gsis_id"))
    pool = pr.select("idx", "psk", key=c("group") + ">" + c("group_j"), val=c("w"))
    pair = pr.filter(c("group") == c("group_j")).select("idx", "psk", key=c("gsis_id") + ">" + c("j") + ">" + c("season").cast(pl.Utf8), val=c("w"))
    L = pl.concat([pool, pair]).group_by("idx", "psk", "key").agg(c("val").sum())
    n_ps = rows.group_by("psk").agg(n=pl.len())
    M = L.group_by("psk", "key").agg(s=c("val").sum()).join(n_ps, on="psk").with_columns(m=c("s") / c("n"))
    D = rows.select("idx", "psk").join(M.select("psk", "key", "m"), on="psk").join(L.select("idx", "key", "val"), on=["idx", "key"], how="left")
    D = D.with_columns(v=c("val").fill_null(0.0) - c("m"))
    pair_keys = sorted(set(D["key"].unique().to_list()) - set(POOL_KEYS))
    keys = POOL_KEYS + pair_keys
    kix = pl.DataFrame({"key": keys, "col": np.arange(len(keys))})
    D = D.join(kix, on="key")
    X = sp.csr_matrix((D["v"].to_numpy(), (D["idx"].to_numpy(), D["col"].to_numpy())), shape=(rows.height, len(keys)))
    y = rows[ycol].to_numpy() - rows.select(c(ycol).mean().over("psk")).to_series().to_numpy()
    return X, y, keys, rows


def fit(X, y, alpha, w=None):
    return Ridge(alpha=alpha, fit_intercept=False, solver="sparse_cg", max_iter=3000, tol=1e-6).fit(X, y, sample_weight=w)


def coefs(m, keys):
    return dict(zip(keys, m.coef_, strict=True))


def choose_alpha(rows, ab, ycol, wcol, label):
    X, y, keys, _ = design(rows.filter(c("season") == 2016), ab, ycol, wcol)
    errs = []
    for a in GRID:
        e = 0.0
        for tr, te in KFold(5, shuffle=True, random_state=0).split(y):
            e += ((y[te] - fit(X[tr], y[tr], a).predict(X[te])) ** 2).sum()
        errs.append(e / len(y))
    base = (y ** 2).mean()
    a = GRID[int(np.argmin(errs))]
    print(f"  {label}: CV error by penalty (2016; no-absence baseline {base:.5f}) {dict(zip(GRID, np.round(errs, 5), strict=True))} -> {a}", flush=True)
    return a


def boot_gain(err0, err1, team):
    g = err0 - err1
    ti = np.array([TIX[t] for t in team])
    W = WB[:, ti]
    bs = (W @ g) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    m0 = err0.mean()
    return g.mean() / m0, lo / m0, hi / m0


# ====================================================================== the offseason table (stayers after departures)
dep = vc.departures(ps)


def stayer_table(measure: str, pool: str):
    """measure: share | tgt_share | car_share. pool: 'group' (snap share: within the group) or 'skill' (targets and
    carries: all WR, TE and RB together). Returns one row per stayer with with-share, 1a, 1b and the next share."""
    grp = c("group") if pool == "group" else pl.lit("skill")
    d = dep if pool == "group" else dep.filter(c("group").is_in(vc.SKILL))
    d = d.with_columns(pool=grp).select("team", "season", "pool", j="gsis_id", group_j="group", wj=c(measure))
    p = ps if pool == "group" else ps.filter(c("group").is_in(vc.SKILL))
    p = p.with_columns(pool=grp)
    nxt = p.select("gsis_id", "team", season=c("season") - 1, y_next=c(measure), games_next="games")
    st = p.filter(c("season") <= 2023).join(nxt, on=["gsis_id", "team", "season"]).join(d.select("team", "season", "pool").unique(), on=["team", "season", "pool"], how="semi")
    st = st.select("gsis_id", "team", "season", "group", "pool", "y_next", "games_next", s_share=c(measure))
    # his games in s, each crossed with the departed players of his pool, flagged whether each played
    ig = pg.join(st.select("gsis_id", "team", "season", "pool"), on=["gsis_id", "team", "season"]).select("gsis_id", "team", "season", "pool", "game_id", v=c(measure))
    x = ig.join(d, on=["team", "season", "pool"]).join(pg.select(j="gsis_id", game_id="game_id", jp=pl.lit(True)), on=["j", "game_id"], how="left").with_columns(c("jp").fill_null(False))
    x = x.join(absent.select("j", "game_id", ja=pl.lit(True)), on=["j", "game_id"], how="left").with_columns(c("ja").fill_null(False))
    wg = x.group_by("gsis_id", "team", "season", "game_id").agg(allp=c("jp").all(), v=c("v").first())
    w = wg.filter(c("allp")).group_by("gsis_id", "team", "season").agg(with_=c("v").mean(), n_with=pl.len())
    st = st.join(w, on=["gsis_id", "team", "season"], how="left").with_columns(with_=c("with_").fill_null(c("s_share")), n_with=c("n_with").fill_null(0))
    # 1a: the departed shares split in proportion to the stayers' with shares
    st = st.with_columns(sumw=c("with_").sum().over("team", "season", "pool"))
    V = d.group_by("team", "season", "pool").agg(V=c("wj").sum())
    st = st.join(V, on=["team", "season", "pool"]).with_columns(alloc=c("V") * c("with_") / c("sumw").clip(1e-9))
    st = st.with_columns(m1a=(c("with_") + c("alloc")).clip(0, 1), m0=c("with_"))
    # 1b: with or without, per departed player, where he played 2+ games without him
    pj = x.group_by("gsis_id", "team", "season", "j", "wj").agg(
        mw=c("v").filter(c("jp")).mean(), mo=c("v").filter(c("ja")).mean(), no=c("ja").sum())
    pj = pj.join(st.select("gsis_id", "team", "season", "with_", "sumw"), on=["gsis_id", "team", "season"])
    pj = pj.with_columns(inc=pl.when((c("no") >= 2) & c("mw").is_not_null()).then(c("mo") - c("mw")).otherwise(c("wj") * c("with_") / c("sumw").clip(1e-9)))
    st = st.join(pj.group_by("gsis_id", "team", "season").agg(inc1b=c("inc").sum(), any_wowy=(c("no") >= 2).any()), on=["gsis_id", "team", "season"], how="left")
    st = st.with_columns(m1b=(c("with_") + c("inc1b").fill_null(0)).clip(0, 1))
    return st


# ====================================================================== method 2 fits, season by season
def pm_fits(row_groups, abs_groups, ycol, wcol, label):
    rows = pg.filter(c("group").is_in(row_groups)).select("gsis_id", "team", "season", "week", "game_id", "group", ycol)
    ab = absent.filter(c("group_j").is_in(abs_groups))
    alpha = choose_alpha(rows, ab, ycol, wcol, label)
    out = {}
    for s in range(2016, 2025):
        X, y, keys, _ = design(rows.filter(c("season") <= s), ab, ycol, wcol)
        m = fit(X, y, alpha)
        out[s] = coefs(m, keys)
    return out, alpha, rows, ab


def pm_predict(st, fits, measure, abs_groups):
    """with share + sum over the departed (any group in abs_groups) of (pooled + pair) x his share."""
    d = dep.filter(c("group").is_in(abs_groups)).select("team", "season", j="gsis_id", group_j="group", wj=c(measure))
    x = st.select("gsis_id", "team", "season", "group").join(d, on=["team", "season"])
    rows = x.to_dicts()
    inc = {}
    for r in rows:
        cf = fits[r["season"]]
        b = cf.get(f"{r['group']}>{r['group_j']}", 0.0) + cf.get(f"{r['gsis_id']}>{r['j']}>{r['season']}", 0.0)
        k = (r["gsis_id"], r["team"], r["season"])
        inc[k] = inc.get(k, 0.0) + b * r["wj"]
    add = pl.DataFrame([{"gsis_id": k[0], "team": k[1], "season": k[2], "inc2": v} for k, v in inc.items()], schema={"gsis_id": pl.Utf8, "team": pl.Utf8, "season": st["season"].dtype, "inc2": pl.Float64})
    st = st.join(add, on=["gsis_id", "team", "season"], how="left")
    return st.with_columns(m2=(c("with_") + c("inc2").fill_null(0)).clip(0, 1))


def score(st, label, by_group=True):
    y = st["y_next"].to_numpy()
    e = {k: (y - st[k].to_numpy()) ** 2 for k in ("m0", "m1a", "m1b", "m2")}
    tm = st["team"].to_numpy()
    print(f"  {label}: {st.height} stayers; squared error  no change {e['m0'].mean():.5f}, 1a {e['m1a'].mean():.5f}, 1b {e['m1b'].mean():.5f}, method 2 {e['m2'].mean():.5f}")
    g, lo, hi = boot_gain(e["m1a"], e["m2"], tm)
    print(f"    method 2 against 1a: gain {g:+.1%} of 1a's error (90% {lo:+.1%} to {hi:+.1%})")
    g0, lo0, hi0 = boot_gain(e["m0"], e["m2"], tm)
    print(f"    method 2 against no change: {g0:+.1%} (90% {lo0:+.1%} to {hi0:+.1%}); 1a against no change: {boot_gain(e['m0'], e['m1a'], tm)[0]:+.1%}; 1b against 1a: {boot_gain(e['m1a'], e['m1b'], tm)[0]:+.1%}")
    if by_group:
        for grp in st["group"].unique().sort().to_list():
            s_ = st.filter(c("group") == grp)
            if s_.height < 20:
                continue
            yy = s_["y_next"].to_numpy()
            ee = {k: (yy - s_[k].to_numpy()) ** 2 for k in ("m0", "m1a", "m2")}
            g_, lo_, hi_ = boot_gain(ee["m1a"], ee["m2"], s_["team"].to_numpy())
            print(f"      {grp}: n {s_.height}; 2 against 1a {g_:+.1%} (90% {lo_:+.1%} to {hi_:+.1%}); 2 against no change {boot_gain(ee['m0'], ee['m2'], s_['team'].to_numpy())[0]:+.1%}")
    return lo > 0


# ====================================================================== 0. the noise ceiling
print("\n=== 0. the noise ceiling")
st = stayer_table("share", "group")
nx = pg.join(st.select("gsis_id", "team", season=c("season") + 1), on=["gsis_id", "team", "season"])
half = nx.with_columns(h=c("week") % 2).group_by("gsis_id", "team", "season", "h").agg(v=c("share").mean()).pivot(on="h", index=["gsis_id", "team", "season"], values="v").drop_nulls()
half = half.join(st.select("gsis_id", "team", season=c("season") + 1, group="group"), on=["gsis_id", "team", "season"])
print("split-half r (odd against even weeks) of a stayer's next-season snap share, and its Spearman-Brown full-season value:")
for grp in G:
    h_ = half.filter(c("group") == grp)
    r = float(np.corrcoef(h_["0"], h_["1"])[0, 1])
    print(f"  {grp}: n {h_.height}, r {r:.2f}, full season {2 * r / (1 + r):.2f}")
dlt = (st["y_next"] - st["with_"]).to_numpy()
print(f"share change, with share to next season (stayers after a departure, n {st.height}): mean {dlt.mean():+.3f}, SD {dlt.std():.3f}")
for grp in G:
    s_ = st.filter(c("group") == grp)
    dd = (s_["y_next"] - s_["with_"]).to_numpy()
    al = s_["alloc"].to_numpy()
    r2 = np.corrcoef(dd, al)[0, 1] ** 2
    print(f"  {grp}: n {s_.height}, SD of change {dd.std():.3f}, mean change {dd.mean():+.3f}, 1a's allocation mean {al.mean():.3f}; r-squared of the change on the allocation {r2:.2f}")
se = tg.group_by("team", "season").agg(off=c("off_epa").mean(), de=c("def_epa").mean())
se2 = se.join(se.select("team", season=c("season") - 1, off_n="off", de_n="de"), on=["team", "season"])
print(f"team efficiency, season to season: offense EPA per play r {np.corrcoef(se2['off'], se2['off_n'])[0, 1]:.2f}, SD of change {(se2['off_n'] - se2['off']).std():.3f}; "
      f"defense r {np.corrcoef(se2['de'], se2['de_n'])[0, 1]:.2f}, SD of change {(se2['de_n'] - se2['de']).std():.3f}; SD across team-seasons {se['off'].std():.3f} and {se['de'].std():.3f}")

# ====================================================================== H109
print("\n=== H109: snap share (rows and absences: all five groups)")
fits, alpha, rows_all, ab_all = pm_fits(G, G, "share", "w_share", "snap share")
cf = fits[2023]
print("  the pooled part, through 2023 (a stayer's share change per unit of an absent top teammate's share; rows: the stayer's group, columns: the absent player's group):")
print("        " + "  ".join(f"{b:>6}" for b in G))
for a in G:
    print(f"    {a:3} " + "  ".join(f"{cf[f'{a}>{b}']:+6.3f}" for b in G))
pairs = {k: v for k, v in cf.items() if k.count(">") == 2}
pv = np.array(list(pairs.values()))
print(f"  the pair part: {len(pairs):,} pairs; SD {pv.std():.3f}; 95th abs {np.percentile(np.abs(pv), 95):.3f}")
st = pm_predict(st, fits, "share", G)
held = score(st, "snap share, all groups")
score(st.filter(c("group").is_in(vc.SKILL)), "snap share, skill groups (WR, TE, RB)", by_group=False)
score(st.filter(~c("group").is_in(vc.SKILL)), "snap share, the lines (OL, DL)", by_group=False)
print("  -> H109 (method 2 beats 1a, 90% interval above 0):", "HELD" if held else "FAILED")

# fitting noise: sign flips of the pooled part across team-bootstrap refits (through 2023)
X, y, keys, rws = design(rows_all, ab_all, "share", "w_share")
tix = np.array([TIX[t] for t in rws["team"].to_list()])
NB = 40
pc = np.array([[fit(X, y, alpha, WB[b, tix]).coef_[i] for i in range(len(POOL_KEYS))] for b in range(NB)])
same_grp = [i for i, k in enumerate(POOL_KEYS) if k.split(">")[0] == k.split(">")[1]]
flip = (np.sign(pc) != np.sign(np.array([cf[k] for k in POOL_KEYS]))).mean(0)
print(f"  fitting noise ({NB} team-bootstrap refits): pooled part's sign flips, same group {np.round(flip[same_grp], 2).tolist()} (WR, TE, RB, OL, DL); all 25 mean {flip.mean():.2f}")
print("    the same-group pooled values' 90% range: " + ", ".join(f"{G[j]} {np.percentile(pc[:, i], 5):+.3f} to {np.percentile(pc[:, i], 95):+.3f}" for j, i in enumerate(same_grp)))

# I49: does the pair part help? (method 2 with the pooled part only)
fits_pool = {s: {k: v for k, v in f.items() if k.count(">") == 1} for s, f in fits.items()}
stp = pm_predict(st.drop("inc2", "m2"), fits_pool, "share", G)
y_ = stp["y_next"].to_numpy()
g, lo, hi = boot_gain((y_ - stp["m2"].to_numpy()) ** 2, (y_ - st["m2"].to_numpy()) ** 2, st["team"].to_numpy())
print(f"  I49 (swap pairs): the pair part added to the pooled part: {g:+.1%} (90% {lo:+.1%} to {hi:+.1%})")

# ====================================================================== side bet: targets and carries
print("\n=== side bet (Claude 30%): target and carry share (rows and absences: WR, TE, RB; the pool: all three together)")
ok = []
for meas, wcol, lab in (("tgt_share", "w_tgt", "target share"), ("car_share", "w_car", "carry share")):
    f2, _, _, _ = pm_fits(vc.SKILL, vc.SKILL, meas, wcol, lab)
    s2 = pm_predict(stayer_table(meas, "skill"), f2, meas, vc.SKILL)
    if meas == "car_share":
        s2 = s2.filter(c("group") == "RB")
    ok.append(score(s2, lab + (" (RB stayers)" if meas == "car_share" else ""), by_group=meas == "tgt_share"))
print("  -> side bet (both):", all(ok))

# ====================================================================== side bet: weekly absences, walk-forward
print("\n=== side bet (Claude 50%): weekly absences, 2017-2024 (a top player absent after 2+ earlier games; his group's players that game)")
pg2 = pg.select("gsis_id", "team", "season", "week", "game_id", "group", "share")
recs = []
for s in range(2017, 2025):
    pool_cf = {k: v for k, v in fits[s - 1].items() if k.count(">") == 1}
    ps_ = pg2.filter(c("season") == s)
    ab_s = absent.filter(c("season") == s)
    for w in range(3, 19):
        a_w = ab_s.filter(c("week") == w)
        if a_w.height == 0:
            continue
        before = ps_.filter(c("week") < w)
        # the absent player's to-date share, and 2+ earlier games
        jd = before.group_by(j="gsis_id", team="team").agg(wj=c("share").mean(), nj=pl.len())
        a_w = a_w.join(jd, on=["j", "team"]).filter(c("nj") >= 2)
        if a_w.height == 0:
            continue
        now = ps_.filter(c("week") == w).join(a_w.select("team", "game_id", "j", "group_j", "wj"), left_on=["team", "game_id", "group"], right_on=["team", "game_id", "group_j"])
        if now.height == 0:
            continue
        # his to-date share in games where every absent group-mate played
        bx = before.join(now.select("gsis_id", "team", "j").unique(), on=["gsis_id", "team"]).join(before.select(j="gsis_id", game_id="game_id", jp=pl.lit(True)), on=["j", "game_id"], how="left")
        bw = bx.group_by("gsis_id", "team", "game_id").agg(allp=c("jp").is_not_null().all(), v=c("share").first()).filter(c("allp")).group_by("gsis_id", "team").agg(base=c("v").mean())
        nn = now.group_by("gsis_id", "team", "game_id", "group", "share").agg(V=c("wj").sum(), js=c("j")).join(bw, on=["gsis_id", "team"])
        nn = nn.with_columns(sumb=c("base").sum().over("team", "game_id", "group")).with_columns(m1a=(c("base") + c("V") * c("base") / c("sumb")).clip(0, 1), m0=c("base"))
        # the pair part from this season's earlier games, on the residual after the pooled part
        b_rows = before
        ab_b = ab_s.filter(c("week") < w).join(jd, on=["j", "team"]).with_columns(w_td=c("wj"))
        pair_cf = {}
        if ab_b.height > 0:
            Xb, yb, kb, _ = design(b_rows, ab_b, "share", "w_td")
            beta_pool = np.array([pool_cf.get(k, 0.0) for k in kb])
            beta_pool[len(POOL_KEYS):] = 0.0
            r = yb - Xb @ beta_pool
            ip = np.arange(len(POOL_KEYS), len(kb))
            if len(ip):
                mb = fit(Xb[:, ip], r, alpha)
                pair_cf = dict(zip([kb[i] for i in ip], mb.coef_, strict=True))
        nr = nn.explode("js").join(a_w.select("j", "team", "game_id", "wj"), left_on=["js", "team", "game_id"], right_on=["j", "team", "game_id"])
        inc = [pool_cf.get(f"{g_}>{g_}", 0.0) * wj + pair_cf.get(f"{i}>{j}>{s}", 0.0) * wj for i, j, g_, wj in zip(nr["gsis_id"], nr["js"], nr["group"], nr["wj"], strict=True)]
        nr = nr.with_columns(inc=pl.Series(inc)).group_by("gsis_id", "team", "game_id").agg(inc=c("inc").sum())
        nn = nn.join(nr, on=["gsis_id", "team", "game_id"], how="left").with_columns(m2=(c("base") + c("inc").fill_null(0)).clip(0, 1))
        recs.append(nn.select("gsis_id", "team", "game_id", "group", y_next="share", m0="m0", m1a="m1a", m2="m2").with_columns(season=pl.lit(s), week=pl.lit(w)))
wk = pl.concat(recs).with_columns(m1b=c("m1a"))
wk_held = score(wk, "weekly absences, snap share")
score(wk.filter(c("group").is_in(vc.SKILL)), "weekly, skill groups", by_group=False)
print("  -> side bet (weekly):", wk_held)
