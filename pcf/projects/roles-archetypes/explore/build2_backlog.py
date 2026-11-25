"""Round 2, the backlog ideas that need other data beside the build's history (odds in BUILD.md,
round 2, and IDEAS.md, written before this ran):

- I122: a shrunk vacancy forecast. A newcomer's role (200+ snaps with a team he wasn't on, in the
  group a top player left) forecast as last season's group average moved part-way toward the
  departed player's role (or the team's usual role); the weight chosen leave-one-season-out.
  On the build's walk-forward coordinates and on the standardized role table.
- I43: the market pays for the passing-down role. Veteran contracts signed 2019-2024 (2025 left
  alone), each player's largest that year as a share of the cap; features from the season before
  (his main side's row). Plain: snap share, snaps, age, draft pick, years since the draft, position
  group. Added: the team-adjusted 3rd-and-4th-down share (`adj_late`, the passing-down role beyond
  his snap share), and its on/off tilt. Walk-forward by signing year (2021-2024 scored).
- I57: forecast a receiver's route mix. Next season's vertical share of his targeted routes (GO,
  POST, CORNER, WHEEL; shrunk with 10 routes of the season's mix) from his position's mix, his
  own past share, and his own share plus the role table. WR and TE with 20+ targeted routes both
  seasons; walk-forward by target season, scored 2021-2024.
- I132: the combine beside the space. A rookie's first-season coordinates (200+ snaps) from his
  measurables (40, height, weight, vertical, shuttle; draft slot) against his position's mean,
  leave-one-season-out (2017-2024 rookies), lasso.

Contracts and the combine are read from their raw nflverse files, as the snap-leverage and roles
explorations did (both sources are listed in DATA_SOURCES; neither is a table part yet). Routes
come through the gateway (participation, retrospective).

Run from pcf/: .venv/Scripts/python.exe projects/roles-archetypes/explore/build2_backlog.py
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
RNG = np.random.default_rng(get_config().seed)
RAW = get_config().zone("raw") / "nflverse"
h = bc.history()
Z, T = bc.Z, bc.T_OFF


def boot_teams(diff: np.ndarray, base: np.ndarray, teams: np.ndarray) -> tuple[float, float, float]:
    _, inv = np.unique(teams, return_inverse=True)
    w = RNG.poisson(1.0, size=(2000, inv.max() + 1))[:, inv].astype(float)
    bs = (w @ diff) / (w @ base)
    lo, hi = np.percentile(bs, [5, 95])
    return float(diff.sum() / base.sum()), float(lo), float(hi)


say("Round 2, backlog ideas on the build's history (run 696a3f0b)")
# ---------------------------------------------------------------- I122
say("\n== I122: a shrunk vacancy forecast (newcomers in a group a top player left)")
off = h.filter(c("side") == "offense")
ref = off.filter(c("snaps") >= 200)
tab_std = {x: (ref[x].mean(), ref[x].std()) for x in T}
off = off.with_columns(**{f"s_{x}": (c(x) - m) / s for x, (m, s) in tab_std.items()})
TOP = {"WR": 2, "TE": 1, "RB": 1}
for space_name, cols in (("coordinates", Z), ("role table (standardized)", [f"s_{x}" for x in T])):
    o = off.filter(c("group").is_in(list(TOP)))
    top = o.with_columns(rk=c("snaps").rank("ordinal", descending=True).over("team", "season", "group")).join(
        pl.DataFrame({"group": list(TOP), "top": list(TOP.values())}), on="group").filter((c("rk") <= c("top")) & (c("snaps") >= 200))
    nxt = o.select("gsis_id", "team", season=c("season") - 1).with_columns(stays=pl.lit(True))
    dep = top.join(nxt, on=["gsis_id", "team", "season"], how="left").filter(c("stays").is_null() & (c("season") < 2024))
    dxy = dep.group_by("team", "season", "group").agg([c(z).mean().alias(f"d{i}") for i, z in enumerate(cols)])
    was = o.select("gsis_id", "team", season=c("season") + 1).with_columns(was=pl.lit(True))
    new = o.filter(c("snaps") >= 200).join(was, on=["gsis_id", "team", "season"], how="left").filter(c("was").is_null()).with_columns(sd=c("season") - 1)
    big = o.filter(c("snaps") >= 200)
    gavg = big.group_by("season", "group").agg([c(z).mean().alias(f"g{i}") for i, z in enumerate(cols)]).rename({"season": "sd"})
    tavg = big.group_by("team", "season", "group").agg([c(z).mean().alias(f"t{i}") for i, z in enumerate(cols)]).rename({"season": "sd"})
    ev = new.join(dxy.rename({"season": "sd"}), on=["team", "sd", "group"]).join(gavg, on=["sd", "group"]).join(tavg, on=["team", "sd", "group"])
    y = ev.select(cols).to_numpy()
    a = ev.select([f"g{i}" for i in range(6)]).to_numpy()
    seasons = ev["season"].to_numpy()
    teams = (ev["team"] + ev["season"].cast(pl.String)).to_numpy()
    err_a = ((y - a) ** 2).sum(1)
    say(f"  {space_name}: {ev.height} newcomers; the group average (last season's) {err_a.mean():.3f}")
    for k, nm in (("d", "toward the departed player"), ("t", "toward the team's usual role")):
        tgt = ev.select([f"{k}{i}" for i in range(6)]).to_numpy()
        grid = np.linspace(0, 1, 21)
        err_b = np.zeros(len(y))
        ws = []
        for s in np.unique(seasons):
            tr, te = seasons != s, seasons == s
            e = [(((y[tr] - (a[tr] + w * (tgt[tr] - a[tr]))) ** 2).sum(1)).mean() for w in grid]
            w = grid[int(np.argmin(e))]
            ws.append(w)
            err_b[te] = ((y[te] - (a[te] + w * (tgt[te] - a[te]))) ** 2).sum(1)
        share, lo, hi = boot_teams(err_a - err_b, err_a, teams)
        say(f"    blend {nm}: weight {np.median(ws):.2f} (range {min(ws):.2f}-{max(ws):.2f} over folds); squared distance {err_b.mean():.3f}; "
            f"beats the average by {100 * share:+.1f}% (90% {100 * lo:+.1f} to {100 * hi:+.1f}) -> {'HOLDS' if lo > 0 else 'tie' if hi > 0 else 'worse'}")

# ---------------------------------------------------------------- I43
say("\n== I43: the market pays for the passing-down role (veteran contracts, share of the cap)")
cnt, _ = D.counts()
fe = D.walk_features(cnt)
mainfe = fe.filter(c("half") == "all").sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
k = pl.read_parquet(RAW / "contracts" / "historical_contracts.parquet").filter(
    c("gsis_id").is_not_null() & c("apy_cap_pct").is_not_null() & (c("year_signed") != c("draft_year")) & c("year_signed").is_between(2019, 2024))
k = k.group_by("gsis_id", "year_signed").agg(c("apy_cap_pct").max(), c("date_of_birth").first(), c("draft_overall").first(), c("draft_year").first())
dd = k.join(mainfe.select("gsis_id", "group", "snaps", "snap_share", "adj_late", "oo_late", year_signed=c("season") + 1), on=["gsis_id", "year_signed"]).with_columns(
    age=(pl.date(c("year_signed"), 3, 15) - c("date_of_birth").str.to_date("%Y-%m-%d", strict=False)).dt.total_days() / 365.25,
    pick=c("draft_overall").fill_null(260).cast(pl.Float64), yexp=(c("year_signed") - c("draft_year")).cast(pl.Float64), lsnaps=c("snaps").log1p())
if dd["age"].is_null().mean() > 0.5:  # the other date format
    dd = dd.with_columns(age=(pl.date(c("year_signed"), 3, 15) - c("date_of_birth").str.to_date("%B %d, %Y", strict=False)).dt.total_days() / 365.25)
dd = dd.with_columns(c("age").fill_null(c("age").median()), c("yexp").fill_null(c("yexp").median()))
groups = sorted(dd["group"].unique().to_list())
dd = dd.with_columns(**{f"is_{g}": (c("group") == g).cast(pl.Float64) for g in groups[1:]})
plain = ["snap_share", "lsnaps", "age", "pick", "yexp", *[f"is_{g}" for g in groups[1:]]]
say(f"  {dd.height:,} contracts signed 2019-2024 by WR, TE, RB and defenders with last season's row; mean {dd['apy_cap_pct'].mean():.2%} of the cap; groups {groups}")
y = dd["apy_cap_pct"].to_numpy()
ys = dd["year_signed"].to_numpy()
ids = dd["gsis_id"].to_numpy()


def walk_c(cols, model):
    x = dd.select(cols).to_numpy().astype(float)
    out = np.full(len(y), np.nan)
    for yr in range(2021, 2025):
        tr, te = ys < yr, ys == yr
        if model == "trees":
            m = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=40, random_state=0).fit(x[tr], y[tr])
            out[te] = m.predict(x[te])
        else:
            out[te] = V.LASSO.fit(x[tr], y[tr], ys[tr])(x[te])
    return out


for model in ("lasso", "trees"):
    p0 = walk_c(plain, model)
    say(f"  {model}: plain model's r with pay {np.corrcoef(y[~np.isnan(p0)], p0[~np.isnan(p0)])[0, 1]:.2f}")
    for nm, extra in (("+ passing-down share (adj_late)", ["adj_late"]), ("+ adj_late and its on/off tilt", ["adj_late", "oo_late"])):
        p1 = walk_c([*plain, *extra], model)
        say(f"    {nm}: {V.gain(y, p0, p1, ids).line()}")
        if extra == ["adj_late"]:
            parts = []
            for g in groups:
                ig = (dd["group"] == g).to_numpy()
                gg = V.gain(y[ig], p0[ig], p1[ig], ids[ig])
                parts.append(f"{g} {100 * gg.share:+.1f}% ({100 * gg.lo:+.1f} to {100 * gg.hi:+.1f})")
            say("      by group: " + "; ".join(parts))

# ---------------------------------------------------------------- I57
say("\n== I57: a receiver's vertical route share next season")
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
say(f"  {pr.height} receiver pairs (WR, TE; 20+ targeted routes both seasons), {pr.filter(c('target_season') >= 2021).height} scored 2021-2024")
yv = pr["y"].to_numpy()
idv = pr["gsis_id"].to_numpy()
L = lambda cols: V.walk(pr, cols, "y", V.LASSO, D.SCORED)  # noqa: E731
pp = {"pos": L(["is_TE"]), "own": L(["is_TE", "own"]), "own+T": L(["is_TE", "own", *T]), "T": L(["is_TE", *T])}
say(f"    his own past share over the position's mix: {V.gain(yv, pp['pos'], pp['own'], idv).line()}")
say(f"    the role table over the position's mix: {V.gain(yv, pp['pos'], pp['T'], idv).line()}")
say(f"    + the role table beyond his own past share: {V.gain(yv, pp['own'], pp['own+T'], idv).line()}")
ok = ~np.isnan(pp["own"])
say(f"    season-to-season r of the share (scored pairs): {np.corrcoef(yv[ok], pr['own'].to_numpy()[ok])[0, 1]:.2f}")

# ---------------------------------------------------------------- I132
say("\n== I132: the combine beside the space (rookies' first-season coordinates)")
players = pl.read_parquet(RAW / "players" / "players.parquet", columns=["gsis_id", "pfr_id"]).drop_nulls()
cb = pl.read_parquet(RAW / "combine" / "combine.parquet").drop_nulls("pfr_id").unique("pfr_id")
cb = cb.with_columns(ht_in=c("ht").str.split("-").list.get(0, null_on_oob=True).cast(pl.Float64, strict=False) * 12
                     + c("ht").str.split("-").list.get(1, null_on_oob=True).cast(pl.Float64, strict=False))
meas = players.join(cb.select("pfr_id", "draft_year", "draft_ovr", "ht_in", "wt", "forty", "vertical", "shuttle"), on="pfr_id")
rk = mo.filter(c("snaps") >= 200).join(meas, on="gsis_id").filter(c("season") == c("draft_year"))
rk = rk.filter(c("season") >= 2017)
M = ["ht_in", "wt", "forty", "vertical", "shuttle", "draft_ovr"]
say(f"  {rk.height} rookie WR, TE (and RB in the history's offense) seasons with 200+ snaps and a combine row, 2017-2024; measured share: "
    + ", ".join(f"{m} {rk[m].is_not_null().mean():.0%}" for m in M))
rk = rk.with_columns([c(m).cast(pl.Float64).fill_null(c(m).cast(pl.Float64).median().over("group")).alias(m) for m in M]).with_columns(c("draft_ovr").fill_null(260.0))
for g in ("WR", "TE"):
    r = rk.filter(c("group") == g)
    if r.height < 40:
        continue
    s_ = r["season"].to_numpy()
    out = []
    for ax, nm in ((0, "in tight (z0)"), (1, "ball carrier (z1)"), (3, "12 personnel (z3)"), (4, "featured target (z4)")):
        yz = r[f"z{ax}"].to_numpy()
        xm = r.select(M).to_numpy()
        pm, p0 = np.zeros(len(yz)), np.zeros(len(yz))
        for s in np.unique(s_):
            tr, te = s_ != s, s_ == s
            mu, sd = xm[tr].mean(0), xm[tr].std(0) + 1e-9
            pm[te] = V.LASSO.fit((xm[tr] - mu) / sd, yz[tr], s_[tr])((xm[te] - mu) / sd)
            p0[te] = yz[tr].mean()
        gg = V.gain(yz, p0, pm, r["gsis_id"].to_numpy())
        out.append(f"{nm} {gg.line()}")
    say(f"  {g} ({r.height} rookies): measurables against the position mean, leave-one-season-out: " + "; ".join(out))
say.save()
