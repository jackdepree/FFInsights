# ruff: noqa: E501
"""voe, first look (2026-11-19). Discovery only: 2016-2024 (participation's years before the
2025 vault). The noise ceiling first, then the CEO's ask (the old VOE, recreated and fixed) and
hunches H69 (plus-minus with shrinkage), H70 (a player against whoever else plays his spot),
H72 (in-game injuries) and H73 (extending the injury measurement to everyone).

- A play = a regular-season run or pass snap (two-point tries out) with true participation.
- The leftover ("EPA over expected") = the play's EPA less what the situation alone expects
  (boosted trees on down, distance, field position, clock, score and win chance, fit only on the
  six seasons before). Signed for the side: a defender's leftover is minus the offense's.
- Player groups: QB, RB (FB in), WR, TE, OL, DL, LB, DB.
- The roster-change test ("does it travel?"): a team's EPA over expected per play in season s+1,
  from last season's own rate, then plus the sum over the players it actually used in s+1 of
  (his share of its s+1 plays x his season-s value). Fit walk-forward on earlier target seasons,
  scored 2019-2024; teams resampled for the interval.

Run from pcf/:  python projects/voe/explore/first_look.py > projects/voe/explore/first_look.txt
"""

from __future__ import annotations

import math
import re
import sys
import time

import numpy as np
import polars as pl
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

from pcf.config import get_config
from pcf.data.clean import standard

c = pl.col
TABLES = get_config().zone("tables")
SEASONS = list(range(2016, 2025))
RNG = np.random.default_rng(get_config().seed)
T0 = time.time()
GROUPS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]
G = {"QB": "QB", "RB": "RB", "FB": "RB", "HB": "RB", "WR": "WR", "TE": "TE",
     "T": "OL", "G": "OL", "C": "OL", "OL": "OL", "OT": "OL", "OG": "OL", "LT": "OL", "RT": "OL", "LG": "OL", "RG": "OL",
     "DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "OLB": "LB", "ILB": "LB", "MLB": "LB", "LB": "LB",
     "CB": "DB", "SS": "DB", "FS": "DB", "S": "DB", "DB": "DB"}  # fmt: skip
SIT = [
    "yardline_100",
    "down",
    "ydstogo",
    "goal_to_go",
    "qtr",
    "half_seconds_remaining",
    "score_differential",
    "wp",
    "pass",
]


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, file=sys.stderr, flush=True)


def part(table, name, seasons, cols):
    files = [TABLES / table / name / f"season={s}" / "data.parquet" for s in seasons]
    dfs = [pl.scan_parquet(str(f)).select(cols).collect() for f in files if f.exists()]
    return pl.concat(dfs, how="vertical_relaxed")


def fz(r, n):
    if n < 6 or math.isnan(r):
        return f"{r:+.2f} (n {n})"
    z, se = math.atanh(max(min(r, 0.9999), -0.9999)), 1 / math.sqrt(n - 3)
    return f"{r:+.2f} ({math.tanh(z - 1.645 * se):+.2f} to {math.tanh(z + 1.645 * se):+.2f}, n {n})"


def r_of(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~np.isnan(a) & ~np.isnan(b)
    if ok.sum() < 6:
        return float("nan"), int(ok.sum())
    return float(np.corrcoef(a[ok], b[ok])[0, 1]), int(ok.sum())


def rr(a, b):
    return fz(*r_of(a, b))


# ---------------------------------------------------------------- plays and the leftover
def plays() -> pl.DataFrame:
    cols = ["game_id", "play_id", "season", "season_type", "week", "posteam", "defteam", "play_type", "two_point_attempt",
            "yardline_100", "down", "ydstogo", "goal_to_go", "qtr", "half_seconds_remaining", "score_differential", "wp", "epa", "desc"]  # fmt: skip
    p = part("play", "pbp", range(2010, 2025), cols)
    p = p.filter((c("season_type") == "REG") & c("play_type").is_in(["run", "pass"]) & (c("two_point_attempt") == 0)
                 & c("posteam").is_not_null() & c("epa").is_not_null()).with_columns(
        c("play_id").cast(pl.Int64), pass_=(c("play_type") == "pass").cast(pl.Float64)).rename({"pass_": "pass"})  # fmt: skip
    p = standard.standard_teams(p, "posteam").pipe(standard.standard_teams, "defteam")
    out = []
    for s in SEASONS:
        tr = p.filter(c("season").is_between(s - 6, s - 1))
        m = HistGradientBoostingRegressor(
            max_iter=200,
            learning_rate=0.08,
            max_leaf_nodes=31,
            min_samples_leaf=200,
            random_state=0,
        )
        m.fit(tr.select(SIT).to_numpy(), tr["epa"].to_numpy())
        te = p.filter(c("season") == s)
        out.append(te.with_columns(xepa=pl.Series(m.predict(te.select(SIT).to_numpy()))))
    p = pl.concat(out).with_columns(resid=c("epa") - c("xepa"))
    return p.drop("season_type", "two_point_attempt")


def on_field(p: pl.DataFrame) -> pl.DataFrame:
    on = part(
        "player_play",
        "on_field",
        SEASONS,
        ["game_id", "play_id", "side", "gsis_id", "position", "position_label"],
    )
    on = on.unique(["game_id", "play_id", "gsis_id"]).with_columns(
        group=c("position").replace_strict(G, default=None)
    )
    on = on.join(
        p.select(
            "game_id", "play_id", "season", "week", "posteam", "defteam", "resid", "play_type"
        ),
        on=["game_id", "play_id"],
    )
    return on.with_columns(
        team=pl.when(c("side") == "offense").then(c("posteam")).otherwise(c("defteam")),
        y=pl.when(c("side") == "offense").then(c("resid")).otherwise(-c("resid")),
    ).filter(c("group").is_not_null())


def player_info(on: pl.DataFrame) -> pl.DataFrame:
    return on.group_by("gsis_id", "season").agg(
        group=c("group").mode().first(), side=c("side").mode().first(), n=pl.len()
    )


# ---------------------------------------------------------------- consistency helpers
def split_and_season(
    vals: pl.DataFrame, value: str, n_min_half: int, n_min_season: int, label: str
):
    """vals: gsis_id, season, half ('odd'/'even'/'all'), value, n, group."""
    print(f"  {label}")
    h = vals.filter(c("half") != "all")
    a = vals.filter(c("half") == "all")
    w = h.pivot(on="half", index=["gsis_id", "season"], values=[value, "n"]).join(
        a.select("gsis_id", "season", "group"), on=["gsis_id", "season"]
    )
    nxt = a.join(a.with_columns(season=c("season") - 1), on=["gsis_id", "season"], suffix="_next")
    rows = []
    for g in ["all", *GROUPS]:
        wg = w if g == "all" else w.filter(c("group") == g)
        wg = wg.filter((c("n_odd") >= n_min_half) & (c("n_even") >= n_min_half))
        ng = nxt if g == "all" else nxt.filter(c("group") == g)
        ng = ng.filter((c("n") >= n_min_season) & (c("n_next") >= n_min_season))
        r1, n1 = r_of(wg[f"{value}_odd"], wg[f"{value}_even"])
        r2, n2 = r_of(ng[value], ng[f"{value}_next"])
        rows.append((g, r1, n1, r2, n2))
        print(f"    {g:>3}: halves {fz(r1, n1)}; season to season {fz(r2, n2)}")
    return rows


# ---------------------------------------------------------------- the roster-change test
def team_rates(p: pl.DataFrame) -> pl.DataFrame:
    off = (
        p.group_by(team=c("posteam"), season=c("season"))
        .agg(rate=c("resid").mean(), n=pl.len())
        .with_columns(side=pl.lit("offense"))
    )
    de = (
        p.group_by(team=c("defteam"), season=c("season"))
        .agg(rate=-c("resid").mean(), n=pl.len())
        .with_columns(side=pl.lit("defense"))
    )
    return pl.concat([off, de])


def roster_sum(on: pl.DataFrame, vals: pl.DataFrame, value: str) -> pl.DataFrame:
    """For each team-season-side s+1: sum over its players of (share of its s+1 plays) x value in s."""
    used = on.group_by("team", "season", "side", "gsis_id").agg(n_on=pl.len())
    tot = on.group_by("team", "season", "side").agg(n_team=c("play_id").n_unique())
    v = vals.select("gsis_id", season=c("season") + 1, v=c(value))
    x = used.join(tot, on=["team", "season", "side"]).join(v, on=["gsis_id", "season"], how="left")
    return x.group_by("team", "season", "side").agg(
        roster=(c("n_on") / c("n_team") * c("v").fill_null(0)).sum(),
        known=(c("n_on") * c("v").is_not_null()).sum() / c("n_on").sum(),
    )


def travel(tr: pl.DataFrame, rs: pl.DataFrame, label: str):
    d = tr.join(
        tr.select("team", "side", season=c("season") + 1, last=c("rate")),
        on=["team", "season", "side"],
    ).join(rs, on=["team", "season", "side"])
    out = {}
    for side in ["offense", "defense"]:
        ds = d.filter(c("side") == side).sort("season")
        se0, se1, keys = [], [], []
        for t in range(2019, 2025):
            a, b = ds.filter(c("season") < t), ds.filter(c("season") == t)
            if b.height == 0:
                continue
            for cols, store in ((["last"], se0), (["last", "roster"], se1)):
                m = Ridge(alpha=1e-6).fit(a.select(cols).to_numpy(), a["rate"].to_numpy())
                store.append((b["rate"].to_numpy() - m.predict(b.select(cols).to_numpy())) ** 2)
            keys.append(b["team"].to_numpy())
        se0, se1, keys = np.concatenate(se0), np.concatenate(se1), np.concatenate(keys)
        gain = 1 - se1.sum() / se0.sum()
        teams = np.unique(keys)
        idx = [np.flatnonzero(keys == k) for k in teams]
        bs = []
        for _ in range(1000):
            pick = np.concatenate([idx[k] for k in RNG.integers(0, len(teams), len(teams))])
            bs.append(1 - se1[pick].sum() / se0[pick].sum())
        lo, hi = np.percentile(bs, [5, 95])
        r_raw, n = r_of(ds["roster"], ds["rate"])
        out[side] = gain
        print(
            f"    {label}, {side}: adds {100 * gain:+.2f}% to last season's rate (90% {100 * lo:+.2f} to {100 * hi:+.2f}); roster sum against the season {fz(r_raw, n)}; plays by players with a value {ds['known'].mean():.0%}"
        )
    return out


# ---------------------------------------------------------------- H69: plus-minus with shrinkage
def rapm_fit(rows: pl.DataFrame, alpha: float, prior: dict | None = None):
    """rows: one per player-play with game_id, play_id, gsis_id, side, resid. Returns {gsis_id: value} (good = +)."""
    keys = (
        rows.select("game_id", "play_id", "resid")
        .unique(["game_id", "play_id"])
        .with_row_index("r")
    )
    r = rows.join(keys.select("game_id", "play_id", "r"), on=["game_id", "play_id"])
    ids = r["gsis_id"].unique().sort().to_list()
    col = {g: i for i, g in enumerate(ids)}
    ci = np.array([col[g] for g in r["gsis_id"].to_list()])
    sign = np.where(r["side"].to_numpy() == "offense", 1.0, -1.0)
    X = sp.csr_matrix((sign, (r["r"].to_numpy(), ci)), shape=(keys.height, len(ids)))
    y = keys["resid"].to_numpy()
    y = y - y.mean()
    b0 = np.zeros(len(ids))
    if prior:
        b0 = np.array([prior.get(g, 0.0) for g in ids])
        y = y - X @ b0
    b = lsqr(X, y, damp=math.sqrt(alpha), atol=1e-8, btol=1e-8, iter_lim=3000)[0] + b0
    return dict(zip(ids, b, strict=True))


def rapm_all(
    on: pl.DataFrame, info: pl.DataFrame, alpha: float, use_prior: bool, shrink_prior: float = 0.5
) -> pl.DataFrame:
    out, prev = [], None
    for s in sorted(on["season"].unique().to_list()):
        rows = on.filter(c("season") == s).select(
            "game_id", "play_id", "gsis_id", "side", "resid", "week"
        )
        prior = {k: shrink_prior * v for k, v in prev.items()} if (use_prior and prev) else None
        for half, f in (("all", None), ("odd", 1), ("even", 0)):
            rs = rows if f is None else rows.filter(c("week") % 2 == f)
            v = rapm_fit(rs, alpha, prior)
            n = rs.group_by("gsis_id").len()
            out.append(
                pl.DataFrame({"gsis_id": list(v), "pm": list(v.values())})
                .with_columns(season=pl.lit(s), half=pl.lit(half))
                .join(n.rename({"len": "n"}), on="gsis_id")
            )
            if half == "all":
                prev = v
        log("rapm", s, "prior" if use_prior else "")
    return pl.concat(out).join(info.select("gsis_id", "season", "group"), on=["gsis_id", "season"])


def pick_alpha(on: pl.DataFrame):
    rows = on.filter(c("season") == 2017)
    tr, te = rows.filter(c("week") % 2 == 1), rows.filter(c("week") % 2 == 0)
    tk = te.select("game_id", "play_id", "resid").unique(["game_id", "play_id"])
    base = float(((tk["resid"] - tr["resid"].mean()) ** 2).mean())
    best = None
    print("  The shrinkage, chosen on 2017 (fit on odd weeks, scored on even weeks' plays):")
    for alpha in (100, 300, 1000, 3000, 10000, 30000):
        v = rapm_fit(tr, alpha)
        pred = (
            te.with_columns(
                b=c("gsis_id").replace_strict(v, default=0.0)
                * pl.when(c("side") == "offense").then(1.0).otherwise(-1.0)
            )
            .group_by("game_id", "play_id")
            .agg(c("b").sum(), c("resid").first())
        )
        mse = float(((pred["resid"] - tr["resid"].mean() - pred["b"]) ** 2).mean())
        print(
            f"    alpha {alpha:>6}: the 22 players explain {100 * (1 - mse / base):+.3f}% of a held-out play's leftover"
        )
        if best is None or mse < best[1]:
            best = (alpha, mse)
    return best[0]


# ---------------------------------------------------------------- H70: whoever else plays his spot
def spot_pm(on: pl.DataFrame) -> pl.DataFrame:
    """On minus off, inside the team-game, against the team's plays where he was off but someone of his group was on."""
    grp_plays = on.group_by("game_id", "play_id", "team", "group").agg(c("y").first())
    tg = grp_plays.group_by("game_id", "team", "group").agg(n_g=pl.len(), s_g=c("y").sum())
    pg = on.group_by("gsis_id", "game_id", "team", "group", "season", "week").agg(
        n_on=pl.len(), s_on=c("y").sum()
    )
    x = pg.join(tg, on=["game_id", "team", "group"]).with_columns(
        n_off=c("n_g") - c("n_on"), s_off=c("s_g") - c("s_on")
    )
    x = x.filter(c("n_off") > 0).with_columns(
        d=c("s_on") / c("n_on") - c("s_off") / c("n_off"), w=c("n_on") * c("n_off") / c("n_g")
    )
    out = []
    for half, f in (("all", None), ("odd", 1), ("even", 0)):
        xs = x if f is None else x.filter(c("week") % 2 == f)
        # shrunk toward 0 by a prior worth k weighted plays
        out.append(
            xs.group_by("gsis_id", "season")
            .agg(
                group=c("group").mode().first(),
                sw=c("w").sum(),
                swd=(c("w") * c("d")).sum(),
                n=c("n_on").sum(),
            )
            .with_columns(spot=c("swd") / (c("sw") + 60.0), half=pl.lit(half))
        )
    return pl.concat(out)


# ---------------------------------------------------------------- the recreation
def recreation(on: pl.DataFrame) -> pl.DataFrame:
    """The old design, fixed: ratings from each player's last 50 snaps of the (signed) leftover,
    a tree model for his next 6 snaps (fit on earlier seasons), slots from the depth-chart label,
    ridge from the 22 slot ratings to the play's leftover (pass and run apart, earlier seasons),
    and the knockout to the slot's average rating."""
    o = on.sort("season", "week", "game_id", "play_id").with_columns(one=pl.lit(1.0))
    o = o.with_columns(
        roll=c("y").shift(1).rolling_mean(50, min_samples=1).over("gsis_id"),
        roll_sd=c("y").shift(1).rolling_std(50, min_samples=2).over("gsis_id"),
        cum_n=c("one").cum_sum().over("gsis_id") - 1,
        cum_s=c("y").cum_sum().over("gsis_id") - c("y"),
        cs=c("y").cum_sum().over("gsis_id"),
    ).with_columns(
        career=pl.when(c("cum_n") > 0).then(c("cum_s") / c("cum_n")),
        nxt=(c("cs").shift(-6).over("gsis_id") - c("cs")),
        gi=c("group").replace_strict({g: i for i, g in enumerate(GROUPS)}, return_dtype=pl.Int64),
    )
    feats = ["roll", "roll_sd", "career", "cum_n", "gi"]
    rated = []
    for s in SEASONS[1:]:
        tr = o.filter((c("season") < s) & c("nxt").is_not_null() & c("roll").is_not_null())
        tr = tr.sample(min(tr.height, 1_200_000), seed=s)
        m = HistGradientBoostingRegressor(
            max_iter=150, learning_rate=0.1, max_depth=3, min_samples_leaf=500, random_state=s
        )
        m.fit(tr.select(feats).to_numpy(), tr["nxt"].to_numpy())
        te = o.filter(c("season") == s)
        rated.append(te.with_columns(rating=pl.Series(m.predict(te.select(feats).to_numpy()))))
        log("rating", s)
    r = (
        pl.concat(rated)
        .unique(["game_id", "play_id", "position_label"])
        .with_columns(slot=c("side").str.slice(0, 1) + "_" + c("position_label"))
    )
    slots = r["slot"].unique().sort().to_list()
    sidx = {k: i for i, k in enumerate(slots)}
    keys = (
        r.select("game_id", "play_id", "season", "resid", "play_type")
        .unique(["game_id", "play_id"])
        .sort("season", "game_id", "play_id")
        .with_row_index("ri")
    )
    r = r.join(keys.select("game_id", "play_id", "ri"), on=["game_id", "play_id"])
    X = sp.csr_matrix(
        (
            r["rating"].to_numpy(),
            (r["ri"].to_numpy(), np.array([sidx[k] for k in r["slot"].to_list()])),
        ),
        shape=(keys.height, len(slots)),
    )
    filled = sp.csr_matrix(
        (np.ones(r.height), (r["ri"].to_numpy(), np.array([sidx[k] for k in r["slot"].to_list()]))),
        shape=X.shape,
    )
    yall, seas, ptype = (
        keys["resid"].to_numpy(),
        keys["season"].to_numpy(),
        keys["play_type"].to_numpy(),
    )
    coef = {}
    r2 = []
    for s in SEASONS[2:]:
        for pt in ("pass", "run"):
            trm, tem = (seas < s) & (ptype == pt), (seas == s) & (ptype == pt)
            m = Ridge(alpha=10.0).fit(X[trm], yall[trm])
            mean = np.asarray(X[trm].sum(axis=0)).ravel() / np.maximum(
                np.asarray(filled[trm].sum(axis=0)).ravel(), 1
            )
            pred = m.predict(X[tem])
            r2.append(
                (
                    s,
                    pt,
                    1
                    - ((yall[tem] - pred) ** 2).sum() / ((yall[tem] - yall[trm].mean()) ** 2).sum(),
                )
            )
            coef[(s, pt)] = (m.coef_, mean, m.intercept_)
    print(
        "  The VOE model on held-out seasons (how much of a play's leftover the 22 slot ratings explain):"
    )
    for pt in ("pass", "run"):
        print(f"    {pt}: " + ", ".join(f"{s} {100 * v:+.2f}%" for s, p_, v in r2 if p_ == pt))
    r = r.filter(c("season") >= SEASONS[2])
    cs, ms = np.zeros(r.height), np.zeros(r.height)
    sl = np.array([sidx[k] for k in r["slot"].to_list()])
    for (s, pt), (cf, mean, _) in coef.items():
        mk = (r["season"].to_numpy() == s) & (r["play_type"].to_numpy() == pt)
        cs[mk], ms[mk] = cf[sl[mk]], mean[sl[mk]]
    ev = cs * (r["rating"].to_numpy() - ms)  # effect on the offense's leftover
    side_sign = np.where(r["side"].to_numpy() == "offense", 1.0, -1.0)
    # y1 per play
    y1 = np.zeros(keys.height)
    for (s, pt), (cf, _, b) in coef.items():
        mk = (seas == s) & (ptype == pt)
        y1[mk] = X[mk] @ cf + b
    r = r.with_columns(exp_voe=pl.Series(side_sign * ev), y1=pl.Series(y1[r["ri"].to_numpy()]))
    r = r.with_columns(real_voe=pl.Series(side_sign) * (c("resid") - (c("y1") - pl.Series(ev))))
    return r


def per_snap(r: pl.DataFrame, col: str) -> pl.DataFrame:
    out = []
    for half, f in (("all", None), ("odd", 1), ("even", 0)):
        rs = r if f is None else r.filter(c("week") % 2 == f)
        out.append(
            rs.group_by("gsis_id", "season")
            .agg(group=c("group").mode().first(), v=c(col).mean(), n=pl.len())
            .with_columns(half=pl.lit(half))
        )
    return pl.concat(out)


# ---------------------------------------------------------------- H72, H73: in-game injuries
INJ = re.compile(r"([A-Z]{2,3})-(\d+)-([A-Za-z\.'\- ]+?) was injured during the play")


def injuries(p: pl.DataFrame, on: pl.DataFrame, pm: pl.DataFrame):
    ev = p.filter(
        c("season").is_in(SEASONS) & c("desc").str.contains("was injured during the play")
    ).select("game_id", "play_id", "season", "desc")
    recs = []
    for g, pid, s, d in ev.iter_rows():
        for m in INJ.finditer(d):
            last = m.group(3).split(".")[-1].strip().lower()
            recs.append((g, pid, s, int(m.group(2)), last))
    ev = pl.DataFrame(
        recs, schema=["game_id", "inj_play", "season", "jersey", "last"], orient="row"
    ).unique(["game_id", "jersey", "last"], keep="first")
    ro = part(
        "player_game", "roster", SEASONS, ["gsis_id", "game_id", "jersey_number", "full_name"]
    ).with_columns(
        jersey=c("jersey_number").cast(pl.Int64, strict=False),
        last=c("full_name")
        .str.split(" ")
        .list.last()
        .str.to_lowercase()
        .str.replace_all(r"[^a-z\-']", ""),
    )
    ev = ev.with_columns(c("last").str.replace_all(r"[^a-z\-']", "")).join(
        ro.select("gsis_id", "game_id", "jersey", "last"), on=["game_id", "jersey", "last"]
    )
    o = on.select("game_id", "play_id", "gsis_id", "team", "side", "group", "y", "season")
    # each team-game-side's plays in order
    tg = (
        on.select("game_id", "play_id", "team", "side", "y", "season")
        .unique(["game_id", "play_id", "side"])
        .sort("game_id", "play_id")
    )
    arr = {
        k: (g["play_id"].to_numpy(), g["y"].to_numpy())
        for k, g in tg.group_by(["game_id", "team", "side"])
    }
    me = ev.join(
        o, left_on=["game_id", "inj_play", "gsis_id"], right_on=["game_id", "play_id", "gsis_id"]
    ).select("game_id", "inj_play", "gsis_id", "team", "side", "group", season=c("season"))
    mine_rows = o.join(me.select("gsis_id", "game_id").unique(), on=["gsis_id", "game_id"])
    pp = {
        (k[0], k[1]): set(v["play_id"].to_list())
        for k, v in mine_rows.group_by(["gsis_id", "game_id"])
    }
    rows = []
    for g, ip, pid, team, side, grp, s in me.iter_rows():
        key = (g, team, side)
        if key not in arr:
            continue
        ids, ys = arr[key]
        k = int(np.searchsorted(ids, ip, side="right"))
        nb, na = k - 1, len(ids) - k
        if nb < 10 or na < 10:
            continue
        mine = pp.get((pid, g), set())
        on_before = sum(1 for x in ids[: k - 1] if x in mine)
        on_after = sum(1 for x in ids[k:] if x in mine)
        if on_after > 2 or on_before < 0.6 * nb:
            continue
        # who took his plays: the group-mate with the most plays after, relative to before
        rows.append(
            (
                g,
                ip,
                pid,
                team,
                side,
                grp,
                s,
                ys[: k - 1].mean(),
                ys[k:].mean(),
                nb,
                na,
                k / len(ids),
            )
        )
    E = pl.DataFrame(
        rows,
        schema=[
            "game_id",
            "inj_play",
            "gsis_id",
            "team",
            "side",
            "group",
            "season",
            "before",
            "after",
            "nb",
            "na",
            "frac",
        ],
        orient="row",
    )
    E = E.unique(["game_id", "team", "side", "gsis_id"])
    # the control: the same team-season-side's other games, split at the same point in the game
    hit = set(zip(E["game_id"].to_list(), E["team"].to_list(), E["side"].to_list(), strict=True))
    by_ts = {}
    for (g, team, side), (_, ys) in arr.items():
        if (g, team, side) in hit:
            continue
        by_ts.setdefault((g[:4], team, side), []).append(np.cumsum(ys))
    ctrl = []
    for g, team, side, frac in E.select("game_id", "team", "side", "frac").iter_rows():
        vals = []
        for cs in by_ts.get((g[:4], team, side), []):
            n = len(cs)
            k = min(max(int(round(frac * n)), 5), n - 5)
            vals.append((cs[-1] - cs[k - 1]) / (n - k) - cs[k - 1] / k)
        ctrl.append(np.mean(vals) if vals else np.nan)
    E = E.with_columns(ctrl=pl.Series(ctrl)).with_columns(
        change=c("after") - c("before"),
        did=c("after") - c("before") - c("ctrl"),
        w=1 / (1 / c("nb") + 1 / c("na")),
    )
    E = E.filter(c("did").is_not_nan())
    # the backup: the group-mate with the largest rise in share after the injury
    gm = on.select("game_id", "play_id", "gsis_id", "team", "side", "group").join(
        E.select("game_id").unique(), on="game_id"
    )
    gm = {k: v for k, v in gm.group_by(["game_id", "team", "side", "group"])}
    bk = []
    for g, ip, pid, team, side, grp in E.select(
        "game_id", "inj_play", "gsis_id", "team", "side", "group"
    ).iter_rows():
        x = gm.get((g, team, side, grp))
        if x is None:
            bk.append(None)
            continue
        x = x.filter(c("gsis_id") != pid)
        a = x.group_by("gsis_id").agg(b=(c("play_id") < ip).sum(), a=(c("play_id") > ip).sum())
        a = a.with_columns(rise=c("a") - c("b")).sort("rise", descending=True)
        bk.append(a["gsis_id"][0] if a.height and a["rise"][0] > 0 else None)
    E = E.with_columns(backup=pl.Series(bk, dtype=pl.Utf8))
    prior = pm.filter(c("half") == "all").select(
        "gsis_id", season=c("season") + 1, prior=c("pm"), prior_n=c("n")
    )
    E = E.join(prior, on=["gsis_id", "season"], how="left").join(
        prior.rename({"gsis_id": "backup", "prior": "bk_prior", "prior_n": "bk_n"}),
        on=["backup", "season"],
        how="left",
    )
    return E


def wmean_ci(x, w, n=2000):
    x, w = np.asarray(x, float), np.asarray(w, float)
    est = float((x * w).sum() / w.sum())
    bs = []
    for _ in range(n):
        i = RNG.integers(0, len(x), len(x))
        bs.append((x[i] * w[i]).sum() / w[i].sum())
    lo, hi = np.percentile(bs, [5, 95])
    return est, float(lo), float(hi)


def main():
    p = plays()
    log("plays", p.height)
    on = on_field(p)
    info = player_info(on)
    pp = p.filter(c("season").is_in(SEASONS))
    print("== DATA ==")
    print(
        f"Plays with participation, 2016-2024: {on.select('game_id', 'play_id').unique().height:,} of {pp.height:,} run and pass snaps; player-plays {on.height:,}; players {on['gsis_id'].n_unique():,}"
    )
    print(
        f"The leftover (EPA less the situation's expectation): mean {pp['resid'].mean():+.3f}, sd {pp['resid'].std():.3f} a play; the situation model's expectation has sd {pp['xepa'].std():.3f}"
    )
    print(
        "Players a season by group: "
        + ", ".join(
            f"{g} {info.filter((c('group') == g) & (c('n') >= 100)).height / len(SEASONS):.0f}"
            for g in GROUPS
        )
        + " (100+ plays)"
    )

    print("\n== NOISE CEILING ==")
    tr = team_rates(pp)
    halves = pp.with_columns(
        h=pl.when(c("week") % 2 == 1).then(pl.lit("odd")).otherwise(pl.lit("even"))
    )
    for side, tcol, sgn in (("offense", "posteam", 1), ("defense", "defteam", -1)):
        t = (
            halves.group_by(team=c(tcol), season=c("season"), h=c("h"))
            .agg(v=sgn * c("resid").mean())
            .pivot(on="h", index=["team", "season"], values="v")
        )
        r, n = r_of(t["odd"], t["even"])
        t2 = tr.filter(c("side") == side)
        t2 = t2.join(t2.with_columns(season=c("season") - 1), on=["team", "season"], suffix="_n")
        print(
            f"  A team's {side} EPA over expected a play: halves of a season {fz(r, n)} (a full season's reliability {2 * r / (1 + r):.2f}); season to season {rr(t2['rate'], t2['rate_n'])}"
        )
    raw = []
    for half, f in (("all", None), ("odd", 1), ("even", 0)):
        x = on if f is None else on.filter(c("week") % 2 == f)
        raw.append(
            x.group_by("gsis_id", "season")
            .agg(group=c("group").mode().first(), raw=c("y").mean(), n=pl.len())
            .with_columns(half=pl.lit(half))
        )
    raw = pl.concat(raw)
    print(
        "  A player's raw on-field average (his team's leftover while he was on; no split from teammates):"
    )
    split_and_season(
        raw, "raw", 150, 300, "raw on-field average, 150+ plays each half, 300+ each season"
    )
    dice = on.group_by("gsis_id", "season").agg(n=pl.len()).filter(c("n") >= 300)
    print(
        f"  Pure dice on a player-season of 300+ plays: the leftover's sd {pp['resid'].std():.3f} / sqrt(n) = {pp['resid'].std() / math.sqrt(dice['n'].median()):.3f} at the median ({dice['n'].median():.0f} plays); teams' spread of the full-season rate {tr['rate'].std():.3f}"
    )

    print("\n== H69: PLUS-MINUS WITH SHRINKAGE ==")
    alpha = pick_alpha(on)
    print(f"  chosen alpha {alpha}")
    pm = rapm_all(on, info, alpha, use_prior=False)
    split_and_season(
        pm,
        "pm",
        150,
        300,
        "plain ridge, a season at a time (150+ plays each half, 300+ each season)",
    )
    # fitting noise: two shrinkages either side
    for a2 in (alpha / 3, alpha * 3):
        alt = rapm_all(
            on.filter(c("season").is_in([2020, 2021])), info, a2, use_prior=False
        ).filter(c("half") == "all")
        base = pm.filter((c("half") == "all") & c("season").is_in([2020, 2021]))
        j = base.join(alt, on=["gsis_id", "season"]).filter(c("n") >= 300)
        print(
            f"  fitting noise: alpha {a2:.0f} against {alpha} (2020-2021, 300+ plays): values agree {rr(j['pm'], j['pm_right'])}"
        )
    pmp = rapm_all(on, info, alpha, use_prior=True)
    print(
        "  with last season's value as the prior (half of it): the halves share the prior, so only the roster-change test reads it fairly"
    )
    top = pm.filter((c("half") == "all") & (c("n") >= 500)).join(
        part("player_game", "roster", SEASONS, ["gsis_id", "full_name"]).unique("gsis_id"),
        on="gsis_id",
        how="left",
    )
    for g in ["QB", "OL", "DL", "DB"]:
        tg = top.filter(c("group") == g).sort("pm", descending=True)
        print(
            f"    top {g} seasons: "
            + "; ".join(
                f"{n} {s} {v:+.3f}"
                for n, s, v in tg.select("full_name", "season", "pm").head(5).iter_rows()
            )
        )
    pos_sd = (
        pm.filter((c("half") == "all") & (c("n") >= 300))
        .group_by("group")
        .agg(sd=c("pm").std(), mean=c("pm").mean(), n=pl.len())
        .sort("group")
    )
    print(
        "    spread of values by group (300+ plays): "
        + "; ".join(f"{g} sd {s:.4f}" for g, s, _, _ in pos_sd.iter_rows())
    )

    print("\n== THE RECREATION (the old VOE, fixed: walk-forward, defense's sign, per snap) ==")
    rec = recreation(on)
    ev = per_snap(rec, "exp_voe")
    rv = per_snap(rec, "real_voe")
    split_and_season(
        ev.rename({"v": "ev"}), "ev", 150, 300, "expected VOE per snap (the play's result not used)"
    )
    split_and_season(
        rv.rename({"v": "rv"}),
        "rv",
        150,
        300,
        "realized VOE per snap (the play's leftover less the prediction without him)",
    )
    rt = (
        rec.with_columns(w=c("week"))
        .group_by("gsis_id", "season", "week")
        .agg(c("rating").mean(), c("exp_voe").sum())
    )
    rt = rt.sort("gsis_id", "season", "week").with_columns(
        nxt=c("exp_voe").shift(-1).over("gsis_id", "season")
    )
    print(
        f"  expected VOE summed per game, week to the next week (the old measure): {rr(rt['exp_voe'], rt['nxt'])}"
    )

    print("\n== H70: A PLAYER AGAINST WHOEVER ELSE PLAYS HIS SPOT (same team-game) ==")
    sp_ = spot_pm(on)
    split_and_season(
        sp_,
        "spot",
        100,
        200,
        "on minus off at his group, shrunk (100+ plays each half, 200+ each season)",
    )
    ov = on.group_by("gsis_id", "season").agg(group=c("group").mode().first(), n=pl.len())
    sh = sp_.filter(c("half") == "all").select("gsis_id", "season", "sw")
    print(
        "  how many plays without him at his spot (weight on x off / team, a season, 300+ plays): "
        + "; ".join(
            f"{g} {v:.0f}"
            for g, v in ov.join(sh, on=["gsis_id", "season"])
            .filter(c("n") >= 300)
            .group_by("group")
            .agg(c("sw").median())
            .sort("group")
            .iter_rows()
        )
    )

    print("\n== AGREEMENT (player-seasons with 300+ plays) ==")
    A = (
        pm.filter(c("half") == "all")
        .select("gsis_id", "season", "group", "n", "pm")
        .join(
            ev.filter(c("half") == "all").select("gsis_id", "season", ev=c("v")),
            on=["gsis_id", "season"],
            how="left",
        )
        .join(
            sp_.filter(c("half") == "all").select("gsis_id", "season", "spot"),
            on=["gsis_id", "season"],
            how="left",
        )
        .join(
            raw.filter(c("half") == "all").select("gsis_id", "season", "raw"),
            on=["gsis_id", "season"],
            how="left",
        )
        .filter(c("n") >= 300)
    )
    for g in ["all", *GROUPS]:
        a = A if g == "all" else A.filter(c("group") == g)
        print(
            f"  {g:>3}: plus-minus vs recreation {rr(a['pm'], a['ev'])}; vs spot {rr(a['pm'], a['spot'])}; vs raw on-field {rr(a['pm'], a['raw'])}"
        )

    print("\n== DOES IT TRAVEL? (the roster-change test, 2019-2024) ==")
    trs = tr.filter(c("season").is_in(SEASONS))
    res = {}
    res["raw"] = travel(
        trs, roster_sum(on, raw.filter(c("half") == "all"), "raw"), "raw on-field average"
    )
    res["pm"] = travel(trs, roster_sum(on, pm.filter(c("half") == "all"), "pm"), "plus-minus")
    res["pmp"] = travel(
        trs,
        roster_sum(on, pmp.filter(c("half") == "all"), "pm"),
        "plus-minus with last season's prior",
    )
    res["ev"] = travel(
        trs,
        roster_sum(on, ev.filter(c("half") == "all"), "v"),
        "recreation (expected VOE per snap)",
    )
    res["spot"] = travel(
        trs, roster_sum(on, sp_.filter(c("half") == "all"), "spot"), "spot plus-minus"
    )

    print("\n== H72: IN-GAME INJURIES ==")
    E = injuries(p, on, pmp)
    print(
        f"  Injury notes matched to a regular who left (on 60%+ of his side's plays before, 2 or fewer after, 10+ plays each side of it): {E.height:,}"
    )
    for g in ["all", *GROUPS]:
        e = E if g == "all" else E.filter(c("group") == g)
        if e.height < 10:
            continue
        a = wmean_ci(e["did"], e["w"])
        b = wmean_ci(e["change"], e["w"], 300)
        print(
            f"    {g:>3} (n {e.height}): after less before, less the same team's other games at that point: {a[0]:+.3f} EPA a play (90% {a[1]:+.3f} to {a[2]:+.3f}); raw change {b[0]:+.3f}"
        )
    k = E.filter(c("prior").is_not_null() & (c("prior_n") >= 200))
    print(
        "  Credited to him? The change against his value last season (plus-minus with prior, 200+ plays):"
    )
    for g in ["all", "QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]:
        e = k if g == "all" else k.filter(c("group") == g)
        if e.height < 15:
            continue
        gap = e.filter(c("bk_prior").is_not_null())
        print(
            f"    {g:>3}: with his value {rr(-e['prior'], e['did'])}; with his value less his backup's {rr(-(gap['prior'] - gap['bk_prior']), gap['did'])}"
        )

    print("\n== H73: EXTENDING THE INJURY MEASUREMENT FROM WHAT WAS KNOWN BEFORE ==")
    F = E.with_columns(
        c("prior").fill_null(0),
        c("bk_prior").fill_null(0),
        lp=(c("prior_n").fill_null(0) + 1).log(),
    )
    for g in GROUPS:
        F = F.with_columns(pl.Series(f"g_{g}", (F["group"] == g).cast(pl.Float64)))
    cols = [f"g_{g}" for g in GROUPS] + ["prior", "bk_prior", "lp"]
    se = {"zero": [], "mean": [], "group": [], "model": []}
    for t in range(2019, 2025):
        a, b = F.filter(c("season") < t), F.filter(c("season") == t)
        if b.height == 0:
            continue
        w, y = b["w"].to_numpy(), b["did"].to_numpy()
        se["zero"].append(w * y**2)
        se["mean"].append(w * (y - np.average(a["did"], weights=a["w"])) ** 2)
        gm = a.group_by("group").agg(m=(c("did") * c("w")).sum() / c("w").sum())
        bg = b.join(gm, on="group", how="left")["m"].fill_null(0).to_numpy()
        se["group"].append(w * (y - bg) ** 2)
        m = Ridge(alpha=10.0).fit(
            a.select(cols).to_numpy(), a["did"].to_numpy(), sample_weight=a["w"].to_numpy()
        )
        se["model"].append(w * (y - m.predict(b.select(cols).to_numpy())) ** 2)
    tot = {k: np.concatenate(v).sum() for k, v in se.items()}
    print(
        f"  held-out events 2019-2024 (n {sum(len(x) for x in se['zero'])}): against predicting the average change, the group's average {100 * (1 - tot['group'] / tot['mean']):+.2f}%; the model (group, his value, his backup's, his plays) {100 * (1 - tot['model'] / tot['mean']):+.2f}%"
    )
    log("done")


if __name__ == "__main__":
    main()
