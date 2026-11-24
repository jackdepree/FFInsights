"""Roles exploration, second look: H108, outcomes attributed by responsibility (pre-registered in EXPLORATION.md).

Every regular-season pass or run 2016-2024; the offense's WR, TE and RB on the field (participation); the play's
EPA. Target group: the targeted receiver or the ball carrier; everyone else on the field is support. Per season,
ridge with offense and defense team fixed effects:
  A  plain plus-minus: one value per player on the field (the simpler side);
  B1 by responsibility: a value when he's the target and one when he's support, weighted by his own mix;
  B2 by latent identity: plain plus-minus plus the play's summed pooled coordinates (the role's part) .
Test: movers' (300+ plays both seasons, a new team) season-to-season r of each credit; 90% player bootstrap of
B minus A. Pays: a team-season's average of last season's credits on the field against this season's offensive
EPA per play, beyond last season's.

Run from pcf/projects/roles-archetypes/explore: PYTHONIOENCODING=utf-8 <venv python> h108_credit.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import roles_common as rc
import scipy.sparse as sp
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

c = pl.col
T = rc.CFG.zone("tables")
RNG = np.random.default_rng(rc.CFG.seed)
B = 2000
K = 6
MIN_PLAYS = 300
SEASONS = range(2016, 2025)
GRID = [30, 100, 300, 1000, 3000, 10000]
SKILL = {"WR": "WR", "TE": "TE", "RB": "RB", "FB": "RB"}

pooled = pl.read_parquet(rc.O / "pooled.parquet").filter(c("half") == "all")
zc = [f"pz{i}" for i in range(K)]


def season_data(s: int):
    p = pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=[
        "game_id", "play_id", "season_type", "posteam", "defteam", "play_type", "down", "receiver_player_id", "rusher_player_id", "epa", "two_point_attempt"])
    p = p.filter((c("season_type") == "REG") & c("play_type").is_in(["pass", "run"]) & (c("two_point_attempt") != 1) & c("down").is_not_null() & c("epa").is_not_null())
    p = p.with_columns(tgt=pl.when(c("receiver_player_id").is_not_null()).then(c("receiver_player_id")).otherwise(c("rusher_player_id")))
    of = pl.read_parquet(T / "player_play" / "on_field" / f"season={s}" / "data.parquet", columns=["game_id", "play_id", "side", "team", "gsis_id", "position"])
    of = of.filter((c("side") == "offense") & c("position").is_in(list(SKILL)))
    p = p.with_row_index("row")
    of = of.join(p.select("game_id", "play_id", "row", "tgt"), on=["game_id", "play_id"], how="inner").with_columns(is_t=(c("gsis_id") == c("tgt")).fill_null(False))
    z = pooled.filter(c("season") == s).sort("gsis_id").unique(["gsis_id", "team"], keep="first")
    of = of.join(z.select("gsis_id", "team", *zc), on=["gsis_id", "team"], how="left").with_columns([c(x).fill_null(0.0) for x in zc])
    return p, of


def design(p, of, kind):
    n = p.height
    players = sorted(of["gsis_id"].unique().to_list())
    pix = {g: i for i, g in enumerate(players)}
    rows = of["row"].to_numpy()
    cols = np.array([pix[g] for g in of["gsis_id"].to_list()])
    np_ = len(players)
    if kind == "B1":
        cols = cols * 2 + (~of["is_t"].to_numpy()).astype(int)  # 2i: target, 2i+1: support
        Xp = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, 2 * np_))
    else:
        Xp = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, np_))
    teams = sorted(set(p["posteam"].to_list()) | set(p["defteam"].to_list()))
    tix = {t: i for i, t in enumerate(teams)}
    Xo = sp.csr_matrix((np.ones(n), (np.arange(n), [tix[t] for t in p["posteam"].to_list()])), shape=(n, len(teams)))
    Xd = sp.csr_matrix((np.ones(n), (np.arange(n), [tix[t] for t in p["defteam"].to_list()])), shape=(n, len(teams)))
    blocks = [Xp, Xo, Xd]
    if kind == "B2":
        Zs = np.zeros((n, K))
        np.add.at(Zs, rows, of.select(zc).to_numpy())
        blocks.append(sp.csr_matrix(Zs))
    return sp.hstack(blocks).tocsr(), players


def fit(X, y, alpha):
    return Ridge(alpha=alpha, solver="sparse_cg", max_iter=2000, tol=1e-5).fit(X, y)


# --- the penalty, chosen once on 2016 per model
p16, of16 = season_data(2016)
y16 = p16["epa"].to_numpy()
ALPHA = {}
for kind in ("A", "B1", "B2"):
    X, _ = design(p16, of16, kind)
    errs = []
    for a in GRID:
        e = 0.0
        for tr, te in KFold(5, shuffle=True, random_state=0).split(y16):
            m = fit(X[tr], y16[tr], a)
            e += ((y16[te] - m.predict(X[te])) ** 2).sum()
        errs.append(e / len(y16))
    ALPHA[kind] = GRID[int(np.argmin(errs))]
    print(f"{kind}: CV error by penalty {dict(zip(GRID, np.round(errs, 5), strict=True))} -> {ALPHA[kind]}", flush=True)

# --- credits per player-season
recs = []
team_ep = []
for s in SEASONS:
    p, of = season_data(s)
    y = p["epa"].to_numpy()
    team_ep.append(p.group_by("posteam").agg(epa=c("epa").mean()).select(team=c("posteam"), season=pl.lit(s), epa=c("epa")))
    nplay = of.group_by("gsis_id").agg(n=pl.len(), n_t=c("is_t").sum(), team=c("team").mode().first())
    out = nplay.with_columns(season=pl.lit(s), mix=c("n_t") / c("n"))
    zmean = of.group_by("gsis_id").agg([c(x).mean() for x in zc])
    out = out.join(zmean, on="gsis_id", how="left")
    for kind in ("A", "B1", "B2"):
        X, players = design(p, of, kind)
        m = fit(X, y, ALPHA[kind])
        npl = len(players)
        if kind == "A":
            v = pl.DataFrame({"gsis_id": players, "A": m.coef_[:npl]})
        elif kind == "B1":
            v = pl.DataFrame({"gsis_id": players, "B1_t": m.coef_[0:2 * npl:2], "B1_s": m.coef_[1:2 * npl:2]})
        else:
            gamma = m.coef_[-K:]
            v = pl.DataFrame({"gsis_id": players, "B2_own": m.coef_[:npl]})
            print(f"  {s} B2's role weights (EPA per play per unit of each coordinate): {np.round(gamma, 4).tolist()}", flush=True)
        out = out.join(v, on="gsis_id", how="left")
    gamma_expr = sum(float(g) * c(x) for g, x in zip(gamma, zc, strict=True))
    out = out.with_columns(B1=c("mix") * c("B1_t") + (1 - c("mix")) * c("B1_s"), B2_role=gamma_expr).with_columns(B2=c("B2_role") + c("B2_own"))
    recs.append(out)
cr = pl.concat(recs)
team_ep = pl.concat(team_ep)

# --- the repeat test
big = cr.filter(c("n") >= MIN_PLAYS)
nx = big.select("gsis_id", season=c("season") - 1, team_n=c("team"), **{f"{k}_n": c(k) for k in ["A", "B1", "B1_t", "B1_s", "B2", "B2_own", "B2_role"]})
pr = big.join(nx, on=["gsis_id", "season"])
mv, st = pr.filter(c("team") != c("team_n")), pr.filter(c("team") == c("team_n"))
print(f"\nplayer-season pairs with {MIN_PLAYS}+ plays both seasons: {pr.height:,} (movers {mv.height}, stayers {st.height})")


def wcorr(x, y, w):
    mx, my = (w * x).sum(1) / w.sum(1), (w * y).sum(1) / w.sum(1)
    dx, dy = x - mx[:, None], y - my[:, None]
    return (w * dx * dy).sum(1) / np.sqrt((w * dx * dx).sum(1) * (w * dy * dy).sum(1))


def repeat(df, k):
    return float(np.corrcoef(df[k].to_numpy(), df[k + "_n"].to_numpy())[0, 1])


print("  season-to-season r:  credit          movers  stayers")
for k, nm in [("A", "A plain plus-minus"), ("B1", "B1 by responsibility"), ("B1_t", "  B1 target value"), ("B1_s", "  B1 support value"),
              ("B2", "B2 by latent identity"), ("B2_own", "  B2 his own part"), ("B2_role", "  B2 the role's part")]:
    print(f"    {nm:28} {repeat(mv, k):+.2f}   {repeat(st, k):+.2f}")
u, inv = np.unique(mv["gsis_id"].to_numpy(), return_inverse=True)
W = RNG.poisson(1.0, size=(B, len(u)))[:, inv].astype(float)
res = {}
for k in ("A", "B1", "B1_t", "B2", "B2_own"):
    res[k] = wcorr(np.broadcast_to(mv[k].to_numpy(), W.shape), np.broadcast_to(mv[k + "_n"].to_numpy(), W.shape), W)
held = False
for k in ("B1", "B2", "B2_own"):
    dlt = res[k] - res["A"]
    lo, hi = np.nanpercentile(dlt, [5, 95])
    print(f"  movers: {k} minus A {repeat(mv, k) - repeat(mv, 'A'):+.2f} (90% {lo:+.2f} to {hi:+.2f})")
    if k in ("B1", "B2") and lo > 0:
        held = True
lo, hi = np.nanpercentile(res["B1_t"], [5, 95])
print(f"  side bet: B1's target value for movers r {repeat(mv, 'B1_t'):+.2f} (90% {lo:+.2f} to {hi:+.2f}); Claude 50% for 0.2+")
print("  -> H108:", "HELD" if held else "FAILED")

# --- pays: last season's credits on the field against this season's offense
print("\npays: a team-season's average of last season's credits on the field, against this season's offensive EPA per play, beyond last season's")
rows = []
for s in list(SEASONS)[1:]:
    p, of = season_data(s)
    prev = cr.filter(c("season") == s - 1).select("gsis_id", "A", "B1", "B2", "B2_own")
    o = of.join(prev, on="gsis_id", how="left").with_columns([c(k).fill_null(0.0) for k in ("A", "B1", "B2", "B2_own")])
    per_play = o.group_by("row").agg([c(k).sum() for k in ("A", "B1", "B2", "B2_own")])
    pp = p.select("row", team=c("posteam")).join(per_play, on="row", how="left").fill_null(0.0)
    rows.append(pp.group_by("team").agg([c(k).mean() for k in ("A", "B1", "B2", "B2_own")]).with_columns(season=pl.lit(s)))
tm = pl.concat(rows).join(team_ep, on=["team", "season"]).join(team_ep.select("team", season=c("season") + 1, epa_prev=c("epa")), on=["team", "season"])


def partial(y, x, z):
    Z = np.column_stack([np.ones(len(z)), z])
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
    return float(np.corrcoef(rx, ry)[0, 1])


yv, zv = tm["epa"].to_numpy(), tm["epa_prev"].to_numpy()
print(f"  team-seasons {tm.height}; last season's EPA per play alone: r {np.corrcoef(yv, zv)[0, 1]:.2f}")
for k in ("A", "B1", "B2", "B2_own"):
    x = tm[k].to_numpy()
    bs = []
    for _ in range(B):
        ix = RNG.integers(0, len(yv), len(yv))
        bs.append(partial(yv[ix], x[ix], zv[ix]))
    lo, hi = np.percentile(bs, [5, 95])
    print(f"  {k:6}: partial r {partial(yv, x, zv):+.3f} (90% {lo:+.3f} to {hi:+.3f})")
