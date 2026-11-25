"""Round 2, the shuffled nulls for build2_backlog.py's ideas (20 each; a result counts when its
interval clears 0 and it beats all 20), plus RB rookies for I132 and I134's exact numbers.

- I122: the departed player (and the team's usual role) moved to another team's vacancy in the same
  group and offseason (a placebo vacancy); the blend's weight refit on each copy.
- I43: `adj_late` shuffled within signing year and group (trees and lasso).
- I57: the role table shuffled within target season and group.
- I132: the measurables shuffled within season and group.
- I134: the chosen band's median flip to 3 decimals, and the other bands on 2021-2024 (a
  sensitivity: the band was chosen on 2017-2020 before these were looked at).

Run from pcf/: .venv/Scripts/python.exe projects/roles-archetypes/explore/build2_nulls.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).parent))
import build2_common as bc  # noqa: E402

from pcf.config import get_config  # noqa: E402
from pcf.data.gateway import END_OF_TIME, Gateway, TableSource  # noqa: E402
from pcf.experts.roles_archetypes import data as D  # noqa: E402
from pcf.experts.roles_archetypes import evaluate as V  # noqa: E402

c = pl.col
say = bc.Say(Path(__file__).with_suffix(".txt"))
RAW = get_config().zone("raw") / "nflverse"
h = bc.history()
Z, T = bc.Z, bc.T_OFF
N_NULL = 20


def shuffle_cols(df: pl.DataFrame, cols, by, seed):
    rng = np.random.default_rng(seed)
    key = df.select(pl.concat_str([c(b).cast(pl.String) for b in by], separator="|")).to_series().to_numpy()
    order = np.arange(df.height)
    for k in np.unique(key):
        idx = np.flatnonzero(key == k)
        order[idx] = idx[rng.permutation(len(idx))]
    return df.with_columns(pl.Series(x, df[x].to_numpy()[order]) for x in cols)


def verdict(real, nulls, lo):
    nulls = np.array(nulls)
    return f"20 nulls: mean {100 * nulls.mean():+.1f}%, best {100 * nulls.max():+.1f}%; beats {int((real > nulls).sum())} of 20; counts: {bool(lo > 0 and real > nulls.max())}"


say("Round 2: shuffled nulls for the backlog ideas")
# ---------------------------------------------------------------- I122
say("\n== I122: placebo vacancies (the departed player and the team's usual role from another team, same group and offseason)")
off = h.filter((c("side") == "offense") & c("group").is_in(["WR", "TE", "RB"]))
TOP = {"WR": 2, "TE": 1, "RB": 1}
top = off.with_columns(rk=c("snaps").rank("ordinal", descending=True).over("team", "season", "group")).join(
    pl.DataFrame({"group": list(TOP), "top": list(TOP.values())}), on="group").filter((c("rk") <= c("top")) & (c("snaps") >= 200))
nxt = off.select("gsis_id", "team", season=c("season") - 1).with_columns(stays=pl.lit(True))
dep = top.join(nxt, on=["gsis_id", "team", "season"], how="left").filter(c("stays").is_null() & (c("season") < 2024))
dxy = dep.group_by("team", "season", "group").agg([c(z).mean().alias(f"d{i}") for i, z in enumerate(Z)])
was = off.select("gsis_id", "team", season=c("season") + 1).with_columns(was=pl.lit(True))
big = off.filter(c("snaps") >= 200)
new = big.join(was, on=["gsis_id", "team", "season"], how="left").filter(c("was").is_null()).with_columns(sd=c("season") - 1)
gavg = big.group_by("season", "group").agg([c(z).mean().alias(f"g{i}") for i, z in enumerate(Z)]).rename({"season": "sd"})
tavg = big.group_by("team", "season", "group").agg([c(z).mean().alias(f"t{i}") for i, z in enumerate(Z)]).rename({"season": "sd"})
ev = new.join(dxy.rename({"season": "sd"}), on=["team", "sd", "group"]).join(gavg, on=["sd", "group"]).join(tavg, on=["team", "sd", "group"])
y = ev.select(Z).to_numpy()
a = ev.select([f"g{i}" for i in range(6)]).to_numpy()
seasons = ev["season"].to_numpy()
teams = (ev["team"] + ev["season"].cast(pl.String)).to_numpy()
err_a = ((y - a) ** 2).sum(1)


def blend_share(tgt):
    grid = np.linspace(0, 1, 21)
    err_b = np.zeros(len(y))
    for s in np.unique(seasons):
        tr, te = seasons != s, seasons == s
        e = [(((y[tr] - (a[tr] + w * (tgt[tr] - a[tr]))) ** 2).sum(1)).mean() for w in grid]
        w = grid[int(np.argmin(e))]
        err_b[te] = ((y[te] - (a[te] + w * (tgt[te] - a[te]))) ** 2).sum(1)
    return err_b


rng = np.random.default_rng(get_config().seed)
_, inv = np.unique(teams, return_inverse=True)
W = rng.poisson(1.0, size=(2000, inv.max() + 1))[:, inv].astype(float)
for k, nm in (("d", "toward the departed player"), ("t", "toward the team's usual role")):
    tgt = ev.select([f"{k}{i}" for i in range(6)]).to_numpy()
    eb = blend_share(tgt)
    real = (err_a - eb).sum() / err_a.sum()
    lo = np.percentile((W @ (err_a - eb)) / (W @ err_a), 5)
    nulls = []
    key = (ev["sd"].cast(pl.String) + ev["group"]).to_numpy()
    for j in range(N_NULL):
        r2 = np.random.default_rng(500 + j)
        order = np.arange(len(y))
        for kk in np.unique(key):
            idx = np.flatnonzero(key == kk)
            order[idx] = idx[r2.permutation(len(idx))]
        en = blend_share(tgt[order])
        nulls.append((err_a - en).sum() / err_a.sum())
    say(f"  coordinates, blend {nm}: {100 * real:+.1f}% (90% lower {100 * lo:+.1f}); {verdict(real, nulls, lo)}")

# ---------------------------------------------------------------- I43
say("\n== I43: adj_late shuffled within signing year and group")
cnt, _ = D.counts()
fe = D.walk_features(cnt)
mainfe = fe.filter(c("half") == "all").sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
k = pl.read_parquet(RAW / "contracts" / "historical_contracts.parquet").filter(
    c("gsis_id").is_not_null() & c("apy_cap_pct").is_not_null() & (c("year_signed") != c("draft_year")) & c("year_signed").is_between(2019, 2024))
k = k.group_by("gsis_id", "year_signed").agg(c("apy_cap_pct").max(), c("date_of_birth").first(), c("draft_overall").first(), c("draft_year").first())
dd = k.join(mainfe.select("gsis_id", "group", "snaps", "snap_share", "adj_late", "oo_late", year_signed=c("season") + 1), on=["gsis_id", "year_signed"]).with_columns(
    age=(pl.date(c("year_signed"), 3, 15) - c("date_of_birth").str.to_date("%B %d, %Y", strict=False)).dt.total_days() / 365.25,
    pick=c("draft_overall").fill_null(260).cast(pl.Float64), yexp=(c("year_signed") - c("draft_year")).cast(pl.Float64), lsnaps=c("snaps").log1p())
dd = dd.with_columns(c("age").fill_null(c("age").median()), c("yexp").fill_null(c("yexp").median()))
groups = sorted(dd["group"].unique().to_list())
dd = dd.with_columns(**{f"is_{g}": (c("group") == g).cast(pl.Float64) for g in groups[1:]})
plain = ["snap_share", "lsnaps", "age", "pick", "yexp", *[f"is_{g}" for g in groups[1:]]]
say(f"  {dd.height:,} contracts; age known for {dd['age'].is_not_null().mean():.0%} (format 'Month day, year')")
yc = dd["apy_cap_pct"].to_numpy()
ys = dd["year_signed"].to_numpy()
ids = dd["gsis_id"].to_numpy()
grp = dd["group"].to_numpy()


def walk_c(frame, cols, model):
    x = frame.select(cols).to_numpy().astype(float)
    out = np.full(len(yc), np.nan)
    for yr in range(2021, 2025):
        tr, te = ys < yr, ys == yr
        if model == "trees":
            out[te] = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40, random_state=0).fit(x[tr], yc[tr]).predict(x[te])
        else:
            out[te] = V.LASSO.fit(x[tr], yc[tr], ys[tr])(x[te])
    return out


for model in ("lasso", "trees"):
    p0 = walk_c(dd, plain, model)
    p1 = walk_c(dd, [*plain, "adj_late"], model)
    sub = {"all": np.ones(len(yc), bool), "DL+OLB": np.isin(grp, ["DL", "OLB"])}
    real = {s: V.gain(yc[m], p0[m], p1[m], ids[m]) for s, m in sub.items()}
    nulls = {s: [] for s in sub}
    for j in range(N_NULL):
        sh = shuffle_cols(dd, ["adj_late"], ["year_signed", "group"], 700 + j)
        pn = walk_c(sh, [*plain, "adj_late"], model)
        for s, m in sub.items():
            nulls[s].append(V.gain(yc[m], p0[m], pn[m], ids[m]).share)
    for s in sub:
        g = real[s]
        say(f"  {model}, {s}: + adj_late {g.line()}; {verdict(g.share, nulls[s], g.lo)}")

# ---------------------------------------------------------------- I57
say("\n== I57: the role table shuffled within target season and group")
parts = []
for s in D.SEASONS:
    v = Gateway(TableSource(seasons=[s])).view(END_OF_TIME, "retrospective", {"play": ("pbp", "participation")})
    t = v.table("play", seasons=[s])
    parts.append(t.filter((c("season_type") == "REG") & c("route").is_not_null() & (c("route") != "") & c("receiver_player_id").is_not_null())
                 .select(gsis_id=c("receiver_player_id"), season=c("season").cast(pl.Int32), vert=c("route").is_in(["GO", "POST", "CORNER", "WHEEL"]).cast(pl.Int64)))
rt = pl.concat(parts).group_by("gsis_id", "season").agg(rn=pl.len(), vert=c("vert").sum())
mix = rt.group_by("season").agg(m=c("vert").sum() / c("rn").sum())
rt = rt.join(mix, on="season").with_columns(vshare=(c("vert") + 10 * c("m")) / (c("rn") + 10))
mo = bc.main_rows(h.filter(c("side") == "offense")).filter(c("group").is_in(["WR", "TE"]))
x = mo.select("gsis_id", "season", "group", *T).join(rt.filter(c("rn") >= 20).select("gsis_id", "season", own=c("vshare")), on=["gsis_id", "season"])
yy = rt.filter(c("rn") >= 20).select("gsis_id", target_season=c("season"), y=c("vshare"))
pr = x.with_columns(target_season=c("season") + 1).join(yy, on=["gsis_id", "target_season"]).with_columns(is_TE=(c("group") == "TE").cast(pl.Float64))
yv, idv = pr["y"].to_numpy(), pr["gsis_id"].to_numpy()
p_own = V.walk(pr, ["is_TE", "own"], "y", V.LASSO, D.SCORED)
p_pos = V.walk(pr, ["is_TE"], "y", V.LASSO, D.SCORED)
p_t = V.walk(pr, ["is_TE", "own", *T], "y", V.LASSO, D.SCORED)
g = V.gain(yv, p_own, p_t, idv)
nl = [V.gain(yv, p_own, V.walk(shuffle_cols(pr, T, ["target_season", "group"], 900 + j), ["is_TE", "own", *T], "y", V.LASSO, D.SCORED), idv).share for j in range(N_NULL)]
say(f"  + the role table beyond his own past share: {g.line()}; {verdict(g.share, nl, g.lo)}")
g2 = V.gain(yv, p_pos, p_own, idv)
nl2 = [V.gain(yv, p_pos, V.walk(shuffle_cols(pr, ["own"], ["target_season", "group"], 950 + j), ["is_TE", "own"], "y", V.LASSO, D.SCORED), idv).share for j in range(N_NULL)]
say(f"  his own past share over the position's mix: {g2.line()}; {verdict(g2.share, nl2, g2.lo)}")

# ---------------------------------------------------------------- I132
say("\n== I132: measurables shuffled within season and group; RB rookies added")
players = pl.read_parquet(RAW / "players" / "players.parquet", columns=["gsis_id", "pfr_id"]).drop_nulls()
cb = pl.read_parquet(RAW / "combine" / "combine.parquet").drop_nulls("pfr_id").unique("pfr_id")
cb = cb.with_columns(ht_in=c("ht").str.split("-").list.get(0, null_on_oob=True).cast(pl.Float64, strict=False) * 12
                     + c("ht").str.split("-").list.get(1, null_on_oob=True).cast(pl.Float64, strict=False))
meas = players.join(cb.select("pfr_id", "draft_year", "draft_ovr", "ht_in", "wt", "forty", "vertical", "shuttle"), on="pfr_id")
mo_all = bc.main_rows(h.filter(c("side") == "offense"))
rk = mo_all.filter(c("snaps") >= 200).join(meas, on="gsis_id").filter((c("season") == c("draft_year")) & (c("season") >= 2017))
M = ["ht_in", "wt", "forty", "vertical", "shuttle", "draft_ovr"]
rk = rk.with_columns([c(m).cast(pl.Float64).fill_null(c(m).cast(pl.Float64).median().over("group")).alias(m) for m in M])


def loso(r, ax, frame=None):
    frame = r if frame is None else frame
    yz = r[f"z{ax}"].to_numpy()
    xm = frame.select(M).to_numpy()
    s_ = r["season"].to_numpy()
    pm, p0 = np.zeros(len(yz)), np.zeros(len(yz))
    for s in np.unique(s_):
        tr, te = s_ != s, s_ == s
        mu, sd = xm[tr].mean(0), xm[tr].std(0) + 1e-9
        pm[te] = V.LASSO.fit((xm[tr] - mu) / sd, yz[tr], s_[tr])((xm[te] - mu) / sd)
        p0[te] = yz[tr].mean()
    return yz, p0, pm


for g_ in ("WR", "TE", "RB"):
    r = rk.filter(c("group") == g_)
    for ax, nm in ((0, "in tight (z0)"), (1, "ball carrier (z1)")):
        yz, p0, pm = loso(r, ax)
        gg = V.gain(yz, p0, pm, r["gsis_id"].to_numpy())
        nulls = [V.gain(yz, p0, loso(r, ax, shuffle_cols(r, M, ["season"], 1200 + j))[2], r["gsis_id"].to_numpy()).share for j in range(N_NULL)]
        say(f"  {g_} ({r.height} rookies), {nm}: {gg.line()}; {verdict(gg.share, nulls, gg.lo)}")

# ---------------------------------------------------------------- I134 exact
say("\n== I134: exact numbers (see build2_roles.txt)")
say.save()
