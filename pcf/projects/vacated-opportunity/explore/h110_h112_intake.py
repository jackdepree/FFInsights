"""Vacated opportunity exploration: H110 (an absence's efficiency cost brings intake) and H112 (bringing in a top
player against leaving the group empty), pre-registered in EXPLORATION.md. 90% team bootstrap throughout.

Run from pcf/projects/vacated-opportunity/explore: PYTHONIOENCODING=utf-8 <venv python> h110_h112_intake.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import vo_common as vc

c = pl.col
RNG = np.random.default_rng(vc.CFG.seed)
B = 2000
G = vc.GROUPS

pg, tg, ps = vc.load()
teams = sorted(tg["team"].unique().to_list())
TIX = {t: i for i, t in enumerate(teams)}
WB = RNG.poisson(1.0, size=(B, len(teams))).astype(float)
tops = ps.filter(c("top"))
ab = tops.select("gsis_id", "team", "season", "first_wk", "last_wk").join(tg.select("game_id", "team", "season", "week"), on=["team", "season"]).filter(c("week").is_between(c("first_wk"), c("last_wk")))
ab = ab.join(pg.select("gsis_id", "game_id"), on=["gsis_id", "game_id"], how="anti").select("gsis_id", "team", "season", "game_id", missed=pl.lit(True))
played = pg.select("gsis_id", "team", "season", "game_id", missed=pl.lit(False)).join(tops.select("gsis_id", "team", "season"), on=["gsis_id", "team", "season"], how="semi")
gm = pl.concat([ab, played]).join(tg, on=["game_id", "team", "season"])
cost = gm.group_by("gsis_id", "team", "season", "missed").agg(n=pl.len(), off=c("off_epa").mean(), de=c("def_epa").mean(), pa=c("pa").sum() / c("pa_n").sum(), pm=c("pm").sum() / c("pm_n").sum())
cp = cost.filter(~c("missed")).join(cost.filter(c("missed")), on=["gsis_id", "team", "season"], suffix="_m").filter((c("n") >= 2) & (c("n_m") >= 2))
cp = cp.join(tops.select("gsis_id", "team", "season", "group", "age"), on=["gsis_id", "team", "season"])
off = c("group").is_in(list(vc.OFFENSE))
cp = cp.with_columns(
    eff_cost=pl.when(off).then(c("off") - c("off_m")).otherwise(c("de_m") - c("de")),
    grp_cost=pl.when(c("group") == "OL").then(c("pa_m") - c("pa")).when(c("group") == "DL").then(c("pm") - c("pm_m")).otherwise(None),
).filter(c("season") <= 2023)

# intake at the group next season: players new to the team who played for it at that group
on_team = ps.select("gsis_id", "team", "season").unique()
nxt = ps.select("gsis_id", "team", "group", "snaps", "rank", season=c("season") - 1).filter(c("season") <= 2023)
new = nxt.join(on_team, on=["gsis_id", "team", "season"], how="anti")
grp_snaps = nxt.group_by("team", "season", "group").agg(g_snaps=c("snaps").sum())
intake = new.group_by("team", "season", "group").agg(n_new=pl.len(), new_snaps=c("snaps").sum(), new_top=(c("rank") <= c("group").replace_strict(vc.TOPK, return_dtype=pl.Int64)).any())
intake = grp_snaps.join(intake, on=["team", "season", "group"], how="left").with_columns(c("n_new").fill_null(0), c("new_snaps").fill_null(0), c("new_top").fill_null(False)).with_columns(new_share=c("new_snaps") / c("g_snaps"))
dep = vc.departures(ps)
nleft = dep.group_by("team", "season", "group").agg(n_left=pl.len())
cp = cp.join(intake, on=["team", "season", "group"], how="left").join(nleft, on=["team", "season", "group"], how="left").with_columns(c("n_left").fill_null(0))
cp = cp.join(dep.select("gsis_id", "team", "season", left=pl.lit(1.0)), on=["gsis_id", "team", "season"], how="left").with_columns(c("left").fill_null(0.0))
cp = cp.with_columns(((c("eff_cost") - c("eff_cost").mean().over("group")) / c("eff_cost").std().over("group")).alias("z_eff"),
                     ((c("grp_cost") - c("grp_cost").mean().over("group")) / c("grp_cost").std().over("group")).alias("z_grp")).drop_nulls(["n_new", "age"])


def wls(y, X, w):
    Xw = X * w[:, None]
    return np.linalg.solve(X.T @ Xw + 1e-9 * np.eye(X.shape[1]), Xw.T @ y)


def reg(df, ycol, xcols, label):
    gd = [(df["group"] == g).cast(pl.Float64).to_numpy() for g in df["group"].unique().sort().to_list()[1:]]
    X = np.column_stack([np.ones(df.height), *[df[x].to_numpy().astype(float) for x in xcols], *gd])
    y = df[ycol].to_numpy().astype(float)
    b = wls(y, X, np.ones(len(y)))
    ti = np.array([TIX[t] for t in df["team"].to_list()])
    bs = np.array([wls(y, X, WB[k, ti]) for k in range(B)])
    print(f"  {label} (n {df.height}; mean {y.mean():.3f}):")
    out = {}
    for i, x in enumerate(xcols, start=1):
        lo, hi = np.percentile(bs[:, i], [5, 95])
        print(f"    {x:6}: {b[i]:+.3f} (90% {lo:+.3f} to {hi:+.3f})")
        out[x] = (b[i], lo, hi)
    return out


print("=== H110: an absence's efficiency cost, and next offseason's intake at that group")
print(f"rows (top player-seasons with 2+ games played and 2+ missed, 2016-2023): {cp.height}; by group {cp.group_by('group').len().sort('group').to_dicts()}")
print(f"  the efficiency cost (EPA per play, worse without him, positive = worse): mean {cp['eff_cost'].mean():+.4f}, SD {cp['eff_cost'].std():.3f}; by group "
      + ", ".join(f"{g} {cp.filter(c('group') == g)['eff_cost'].mean():+.4f}" for g in G))
print(f"  how much of the cost is noise: games missed per row, median {cp['n_m'].median():.0f}; a game's EPA per play SD {tg['off_epa'].std():.3f}")
X = ["z_eff", "left", "age", "n_left"]
r1 = reg(cp, "n_new", X, "newcomers at the group (count)")
r2 = reg(cp, "new_share", X, "newcomers' share of the group's snaps")
print("  -> H110 (efficiency cost on the intake count, interval above 0):", "HELD" if r1["z_eff"][1] > 0 else "FAILED")
print("  -> side bet, he left (85%):", r1["left"][1] > 0)
ln = cp.filter(c("group").is_in(["OL", "DL"])).drop_nulls("z_grp")
print("  the lines' own outcome (OL pressure allowed, DL pressure made; reported):")
reg(ln, "n_new", ["z_grp", "left", "age", "n_left"], "OL and DL newcomers (count) on the pressure cost")
print("  by group, the efficiency cost on the intake count (reported):")
for g in G:
    s_ = cp.filter(c("group") == g)
    yv = s_["n_new"].to_numpy().astype(float)
    Xg = np.column_stack([np.ones(s_.height), s_["z_eff"].to_numpy(), s_["left"].to_numpy(), s_["age"].to_numpy(), s_["n_left"].to_numpy()])
    b = wls(yv, Xg, np.ones(len(yv)))
    ti = np.array([TIX[t] for t in s_["team"].to_list()])
    bs = np.array([wls(yv, Xg, WB[k, ti])[1] for k in range(B)])
    print(f"    {g}: n {s_.height}, {b[1]:+.3f} (90% {np.percentile(bs, 5):+.3f} to {np.percentile(bs, 95):+.3f})")

# ====================================================================== H112
print("\n=== H112: after a departure, bringing in a top player against leaving the group empty")
se = tg.group_by("team", "season").agg(off=c("off_epa").mean(), de=c("def_epa").mean(), pa=c("pa").sum() / c("pa_n").sum(), pm=c("pm").sum() / c("pm_n").sum())
se2 = se.join(se.select("team", season=c("season") - 1, off_n="off", de_n="de", pa_n="pa", pm_n="pm"), on=["team", "season"])
h = nleft.join(intake.select("team", "season", "group", "new_top"), on=["team", "season", "group"]).join(se2, on=["team", "season"])
h = h.with_columns(
    d_eff=pl.when(c("group").is_in(list(vc.OFFENSE))).then(c("off_n") - c("off")).otherwise(-(c("de_n") - c("de"))),
    d_grp=pl.when(c("group") == "OL").then(-(c("pa_n") - c("pa"))).when(c("group") == "DL").then(c("pm_n") - c("pm")).otherwise(None))
# the stayers' summed share gain at the group
nx2 = ps.select("gsis_id", "team", season=c("season") - 1, share_n="share")
stg = ps.join(nx2, on=["gsis_id", "team", "season"]).group_by("team", "season", "group").agg(st_gain=(c("share_n") - c("share")).sum())
h = h.join(stg, on=["team", "season", "group"], how="left").with_columns(c("st_gain").fill_null(0.0))
print(f"rows (team-season-groups with a departure, 2016-2023): {h.height}; brought in a top player {h['new_top'].sum()} ({h['new_top'].mean():.0%})")
print("  by group, share that brought one in:", h.group_by("group").agg(n=pl.len(), intake=c("new_top").mean().round(2)).sort("group").to_dicts())


def diff(df, col):
    x = df[col].to_numpy().astype(float)
    it = df["new_top"].to_numpy()
    ti = np.array([TIX[t] for t in df["team"].to_list()])
    W = WB[:, ti]
    m1 = (W * x * it).sum(1) / (W * it).sum(1)
    m0 = (W * x * ~it).sum(1) / (W * ~it).sum(1)
    d = x[it].mean() - x[~it].mean()
    lo, hi = np.percentile(m1 - m0, [5, 95])

    def wsd(m, msk):
        mu = (W * x * msk).sum(1) / (W * msk).sum(1)
        return np.sqrt((W * msk * (x[None, :] - mu[:, None]) ** 2).sum(1) / (W * msk).sum(1))
    ratio = wsd(None, it) / wsd(None, ~it)
    rlo, rhi = np.percentile(ratio, [5, 95])
    return d, lo, hi, x[it].std() / x[~it].std(), rlo, rhi, x[it].mean(), x[~it].mean()


d, lo, hi, r, rlo, rhi, a1, a0 = diff(h, "d_eff")
print(f"  efficiency change s to s+1 (EPA per play, up = better): brought in {a1:+.4f}, left empty {a0:+.4f}; difference {d:+.4f} (90% {lo:+.4f} to {hi:+.4f})")
print(f"  -> H112: {'HELD' if lo > 0 else 'FAILED'}")
print(f"  side bet, the spread differs (20%): SD ratio, brought in over left empty {r:.2f} (90% {rlo:.2f} to {rhi:.2f}) -> {rlo > 1 or rhi < 1}")
d2, lo2, hi2, *_ , b1, b0 = diff(h, "st_gain")
print(f"  side bet, stayers grow less where a top player came in (90%): stayers' summed share gain {b1:+.3f} against {b0:+.3f}; difference {d2:+.3f} (90% {lo2:+.3f} to {hi2:+.3f}) -> {hi2 < 0}")
for g in G:
    s_ = h.filter(c("group") == g)
    dd, l_, h_, *_ = diff(s_, "d_eff")
    print(f"    {g}: n {s_.height} (brought in {s_['new_top'].sum()}); efficiency difference {dd:+.4f} (90% {l_:+.4f} to {h_:+.4f})")
ln = h.filter(c("group").is_in(["OL", "DL"]))
dd, l_, h_, *_ = diff(ln, "d_grp")
print(f"  the lines' own outcome (pressure, up = better; reported): difference {dd:+.4f} (90% {l_:+.4f} to {h_:+.4f})")
# a fairer comparison: teams that bring in a top player may differ before; control for last season's efficiency
x0 = np.where(h["group"].is_in(list(vc.OFFENSE)).to_numpy(), h["off"].to_numpy(), -h["de"].to_numpy())
X = np.column_stack([np.ones(h.height), h["new_top"].cast(pl.Float64).to_numpy(), x0, h["n_left"].to_numpy()])
y = h["d_eff"].to_numpy()
ti = np.array([TIX[t] for t in h["team"].to_list()])
bb = wls(y, X, np.ones(len(y)))
bs = np.array([wls(y, X, WB[k, ti])[1] for k in range(B)])
print(f"  reported: the difference controlling for last season's efficiency and departures {bb[1]:+.4f} (90% {np.percentile(bs, 5):+.4f} to {np.percentile(bs, 95):+.4f})")

# reported after the pre-registration: H110's "he left" side bet overlaps the count of departures (he left means
# the count is 1 or more), so the side bet again without the count
print("\nreported (added after the pre-registration): H110's side bet without the count of departures")
reg(cp, "n_new", ["z_eff", "left", "age"], "newcomers at the group (count), without n_left")
