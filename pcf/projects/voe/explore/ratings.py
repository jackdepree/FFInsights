# ruff: noqa: E501
"""voe, second look (2026-11-19): the CEO's directions (a) and (b) together, and H75 ("the VOE model
holds if we incorporate the plus-minus sum"), with a small MLP beside the lasso. Discovery only,
2016-2024 (the 2025 vault not read).

Each player gets two ratings from information his teammates don't share, made only from seasons
before the play's season:
- (a) plus-minus that starts from his own stats: each season's plus-minus with, as its prior, what
  his own stats and last season's plain plus-minus say about this season (a lasso per position
  group, fit only on earlier pairs of seasons). New players start at their group's new-player value.
- (b) the own-stats rating: his season's own stats (nflverse player stats, NGS, PFR) mapped to next
  season's plain plus-minus, per position group, earlier pairs only. No on-field team outcome in it.

Then the old VOE design on top: each play's slots carry the ratings of who played there, plus the
play's offense-minus-defense sum of ratings ("the plus-minus sum"); models from those to the play's
EPA over expected, pass and run apart, fit on 2018 to T-1 and scored on season T (2019-2024).
The knockout: a side's players replaced by the slot's average gives that side's value per play.

Run from pcf/:  python projects/voe/explore/ratings.py > projects/voe/explore/ratings.txt
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LassoCV, LinearRegression
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402

c = pl.col
ALPHA = 10000.0  # the plus-minus shrinkage chosen in the first look (2017, odd weeks -> even weeks)
SEASONS = fl.SEASONS
PLAY_SEASONS = list(range(2018, 2025))  # seasons whose plays have both ratings
TEST = list(range(2019, 2025))
GROUPS = fl.GROUPS
log = fl.log
RNG = np.random.default_rng(11)
MLP_SEEDS = (0, 1, 2)

FEATS = ["log_n", "pass_epa", "cpoe", "ngs_cpoe", "int_rate", "sack_rate", "bad_throw", "db_rate",
         "carry_rate", "rush_epa", "ryoe", "tgt_rate", "rec_epa", "yds_play", "sep", "yacoe", "drop", "btk",
         "sack", "hit", "tfl", "pd", "int", "ff", "solo", "press", "tgt_allowed", "ypt_allowed", "missed",
         "pen", "pfr"]  # fmt: skip


# ---------------------------------------------------------------- own stats, a player-season
def season_stats(p: pl.DataFrame, on: pl.DataFrame) -> pl.DataFrame:
    reg = p.select("game_id").unique()
    n_on = on.group_by("gsis_id", "season").agg(n_on=pl.len())
    sc = ["attempts", "sacks_suffered", "passing_epa", "passing_interceptions", "carries", "rushing_epa",
          "targets", "receptions", "receiving_yards", "receiving_epa", "def_sacks", "def_qb_hits",
          "def_tackles_for_loss", "def_pass_defended", "def_interceptions", "def_fumbles_forced",
          "def_tackles_solo", "penalties"]  # fmt: skip
    st = fl.part(
        "player_game", "stats", SEASONS, ["gsis_id", "season", "game_id", "passing_cpoe", *sc]
    ).join(reg, on="game_id")
    s1 = st.group_by("gsis_id", "season").agg(
        *(c(k).cast(pl.Float64).fill_null(0).sum() for k in sc),
        cp_x=(c("passing_cpoe") * c("attempts")).fill_null(0).sum(),
        cp_w=pl.when(c("passing_cpoe").is_not_null())
        .then(c("attempts"))
        .otherwise(0)
        .fill_null(0)
        .sum(),
    )
    ng = fl.part("player_game", "ngs", SEASONS, ["gsis_id", "season", "game_id",
                 "ngs_pass_completion_percentage_above_expectation", "ngs_pass_attempts",
                 "ngs_rush_rush_yards_over_expected", "ngs_rush_rush_attempts", "ngs_rec_avg_separation",
                 "ngs_rec_targets", "ngs_rec_avg_yac_above_expectation", "ngs_rec_receptions"]).join(reg, on="game_id")  # fmt: skip

    def wsum(v, n):
        return (c(v) * c(n)).fill_null(0).sum()

    def wn(v, n):
        return pl.when(c(v).is_not_null()).then(c(n)).otherwise(0).fill_null(0).sum()

    s2 = ng.group_by("gsis_id", "season").agg(
        cpoe_x=wsum("ngs_pass_completion_percentage_above_expectation", "ngs_pass_attempts"),
        cpoe_n=wn("ngs_pass_completion_percentage_above_expectation", "ngs_pass_attempts"),
        ryoe_x=c("ngs_rush_rush_yards_over_expected").fill_null(0).sum(),
        ryoe_n=wn("ngs_rush_rush_yards_over_expected", "ngs_rush_rush_attempts"),
        sep_x=wsum("ngs_rec_avg_separation", "ngs_rec_targets"),
        sep_n=wn("ngs_rec_avg_separation", "ngs_rec_targets"),
        yac_x=wsum("ngs_rec_avg_yac_above_expectation", "ngs_rec_receptions"),
        yac_n=wn("ngs_rec_avg_yac_above_expectation", "ngs_rec_receptions"),
    )
    pc = ["pfr_rec_receiving_drop", "pfr_rush_rushing_broken_tackles", "pfr_rec_receiving_broken_tackles",
          "pfr_def_def_pressures", "pfr_def_def_targets", "pfr_def_def_yards_allowed", "pfr_def_def_missed_tackles",
          "pfr_def_def_tackles_combined", "pfr_pass_passing_bad_throws"]  # fmt: skip
    pf = fl.part(
        "player_game",
        "pfr",
        [s for s in SEASONS if s >= 2018],
        ["gsis_id", "season", "game_id", *pc],
    ).join(reg, on="game_id")
    s3 = pf.group_by("gsis_id", "season").agg(
        *(c(k).cast(pl.Float64, strict=False).fill_null(0).sum() for k in pc)
    )
    f = (
        n_on.join(s1, on=["gsis_id", "season"], how="left")
        .join(s2, on=["gsis_id", "season"], how="left")
        .join(s3, on=["gsis_id", "season"], how="left")
        .fill_null(0)
    )
    lm = f.group_by("season").agg(
        lm_sep=c("sep_x").sum() / c("sep_n").sum(),
        lm_ypt=c("pfr_def_def_yards_allowed").sum() / c("pfr_def_def_targets").sum().clip(1),
    )
    f = f.join(
        lm.with_columns(c("lm_sep").fill_nan(0), c("lm_ypt").fill_nan(0)), on="season"
    ).fill_null(0)
    db = c("attempts") + c("sacks_suffered")
    n = c("n_on")
    return f.select(
        "gsis_id", "season", "n_on",
        log_n=(n + 1).log(),
        pass_epa=c("passing_epa") / (db + 50),
        cpoe=c("cp_x") / (c("cp_w") + 50),
        ngs_cpoe=c("cpoe_x") / (c("cpoe_n") + 50),
        int_rate=c("passing_interceptions") / (c("attempts") + 50),
        sack_rate=c("sacks_suffered") / (db + 50),
        bad_throw=c("pfr_pass_passing_bad_throws") / (c("attempts") + 50),
        db_rate=db / n,
        carry_rate=c("carries") / n,
        rush_epa=c("rushing_epa") / (c("carries") + 30),
        ryoe=c("ryoe_x") / (c("ryoe_n") + 30),
        tgt_rate=c("targets") / n,
        rec_epa=c("receiving_epa") / (c("targets") + 20),
        yds_play=c("receiving_yards") / n,
        sep=(c("sep_x") - c("lm_sep") * c("sep_n")) / (c("sep_n") + 20),
        yacoe=c("yac_x") / (c("yac_n") + 20),
        drop=c("pfr_rec_receiving_drop") / (c("targets") + 20),
        btk=(c("pfr_rush_rushing_broken_tackles") + c("pfr_rec_receiving_broken_tackles")) / (c("carries") + c("receptions") + 20),
        sack=c("def_sacks") / n,
        hit=c("def_qb_hits") / n,
        tfl=c("def_tackles_for_loss") / n,
        pd=c("def_pass_defended") / n,
        int=c("def_interceptions") / n,
        ff=c("def_fumbles_forced") / n,
        solo=c("def_tackles_solo") / n,
        press=c("pfr_def_def_pressures") / n,
        tgt_allowed=c("pfr_def_def_targets") / n,
        ypt_allowed=(c("pfr_def_def_yards_allowed") - c("lm_ypt") * c("pfr_def_def_targets")) / (c("pfr_def_def_targets") + 20),
        missed=c("pfr_def_def_missed_tackles") / (c("pfr_def_def_tackles_combined") + c("pfr_def_def_missed_tackles") + 20),
        pen=c("penalties") / n,
        pfr=(c("season") >= 2018).cast(pl.Float64),
    )  # fmt: skip


# ---------------------------------------------------------------- the stats model (b), and the prior for (a)
def design(F, info, pmdf, target, with_pm):
    """Players in season `target`, with features from target-1 (zeros and new=1 if he didn't play)."""
    base = info.filter(c("season") == target).select("gsis_id", "group", "n")
    prev = F.filter(c("season") == target - 1).drop("season", "n_on")
    x = base.join(prev, on="gsis_id", how="left").with_columns(
        new=c("log_n").is_null().cast(pl.Float64)
    )
    if with_pm:
        x = x.join(
            pmdf.filter(c("season") == target - 1).select("gsis_id", pm_last=c("pm")),
            on="gsis_id",
            how="left",
        )
    return x.fill_null(0)


def stats_ratings(F, info, pmdf, T, with_pm):
    """Ratings for season T's players from season T-1's stats; the model is fit on pairs (t-1 -> t), t <= T-1."""
    cols = FEATS + (["pm_last"] if with_pm else []) + ["new"]
    tr = pl.concat(
        [
            design(F, info, pmdf, t, with_pm).join(
                pmdf.filter(c("season") == t).select("gsis_id", y=c("pm")), on="gsis_id"
            )
            for t in range(2017, T)
        ]
    )
    te = design(F, info, pmdf, T, with_pm)
    out = []
    for g in GROUPS:
        a, b = tr.filter(c("group") == g), te.filter(c("group") == g)
        if b.height == 0:
            continue
        w = a["n"].clip(upper_bound=1000).cast(pl.Float64).to_numpy()
        X, y = a.select(cols).to_numpy(), a["y"].to_numpy()
        splits = list(GroupKFold(5).split(X, y, a["gsis_id"].to_numpy()))
        m = make_pipeline(StandardScaler(), LassoCV(alphas=20, cv=splits, max_iter=20000))
        m.fit(X, y, lassocv__sample_weight=w)
        out.append(
            b.select("gsis_id", "new").with_columns(
                rating=pl.Series(m.predict(b.select(cols).to_numpy()))
            )
        )
    return pl.concat(out).with_columns(season=pl.lit(T))


# ---------------------------------------------------------------- plays to slot matrices
def build(on, R):
    o = on.filter(c("season").is_in(PLAY_SEASONS)).join(R, on=["gsis_id", "season"], how="left")
    o = o.with_columns(c("rp").fill_null(0.0), c("ra").fill_null(0.0), c("rs").fill_null(0.0))
    keys = (
        o.select("game_id", "play_id", "season", "week", "posteam", "defteam", "resid", "play_type")
        .unique(["game_id", "play_id"])
        .sort("season", "game_id", "play_id")
        .with_row_index("ri")
    )
    o = o.join(keys.select("game_id", "play_id", "ri"), on=["game_id", "play_id"])
    o = o.with_columns(k0=c("side").str.slice(0, 1) + "_" + c("position_label").fill_null("x"))
    share = o.group_by("k0").agg(s=pl.len() / keys.height)
    keep = set(share.filter(c("s") >= 0.005)["k0"].to_list())
    o = o.with_columns(
        key=pl.when(c("k0").is_in(list(keep)))
        .then(c("k0"))
        .otherwise(c("side").str.slice(0, 1) + "_" + c("group") + "_x")
    )
    slots = sorted(o["key"].unique().to_list())
    sidx = {k: i for i, k in enumerate(slots)}
    P, S = keys.height, len(slots)
    ri = o["ri"].to_numpy()
    si = np.array([sidx[k] for k in o["key"].to_list()])
    off = o["side"].to_numpy() == "offense"
    sd = {k: float(o[k].std()) for k in ("ra", "rs", "rp")}
    Xa, Xs, Fm = (np.zeros((P, S), np.float32) for _ in range(3))
    np.add.at(Xa, (ri, si), (o["ra"].to_numpy() / sd["ra"]).astype(np.float32))
    np.add.at(Xs, (ri, si), (o["rs"].to_numpy() / sd["rs"]).astype(np.float32))
    np.add.at(Fm, (ri, si), 1.0)
    sums = {}
    for k in ("ra", "rs", "rp"):
        v = o[k].to_numpy() / sd[k]
        sums[k] = (np.bincount(ri[off], v[off], P), np.bincount(ri[~off], v[~off], P))
    X = np.hstack(
        [
            Xa,
            Xs,
            np.column_stack([sums[k][0] - sums[k][1] for k in ("ra", "rs", "rp")]).astype(
                np.float32
            ),
        ]
    )
    side_o = np.array([k.startswith("o_") for k in slots])
    log("matrices", P, "plays", S, "slots")
    return keys, X, Fm, sums, slots, side_o


def knock(Xte, Fte, te, side_o, sums, smean, msl, side, S):
    """Held-out plays with one side's players replaced by the slot's training average, and that side's part of the sums by its training average."""
    Xk = Xte.copy()
    cols = np.flatnonzero(side_o if side == "o" else ~side_o)
    filled = Fte[:, cols] > 0
    for part_ in (0, 1):
        j = cols + part_ * S
        Xk[:, j] = np.where(filled, msl[j], 0.0)
    for i, k in enumerate(("ra", "rs", "rp")):
        so, sdf = sums[k]
        if side == "o":
            Xk[:, 2 * S + i] = smean[k][0] - sdf[te]
        else:
            Xk[:, 2 * S + i] = so[te] - smean[k][1]
    return Xk


def fit_all(keys, X, Fm, sums, slots, side_o):
    S = len(slots)
    seas, ptype = keys["season"].to_numpy(), keys["play_type"].to_numpy()
    y, games = keys["resid"].to_numpy(), keys["game_id"].to_numpy()
    full = list(range(2 * S + 2))
    models = {
        "sum_pm": [2 * S + 2],
        "sum_a": [2 * S],
        "sums": [2 * S, 2 * S + 1],
        "lasso_slots": list(range(2 * S)),
        "lasso": full,
        "mlp": full,
    }
    se = {m: np.zeros(len(y)) for m in [*models, "base", "null", *(f"mlp{s}" for s in MLP_SEEDS)]}
    vo = {m: np.zeros(len(y)) for m in models}
    vd = {m: np.zeros(len(y)) for m in models}
    test = np.zeros(len(y), bool)
    diag = []
    for T in TEST:
        for pt in ("pass", "run"):
            tr = np.flatnonzero((seas < T) & (ptype == pt))
            te = np.flatnonzero((seas == T) & (ptype == pt))
            test[te] = True
            se["base"][te] = (y[te] - y[tr].mean()) ** 2
            Xtr, Xte, Ftr, Fte = X[tr], X[te], Fm[tr], Fm[te]
            cnt = np.maximum((Ftr > 0).sum(axis=0), 1)
            msl = np.concatenate(
                [Xtr[:, :S].sum(axis=0) / cnt, Xtr[:, S : 2 * S].sum(axis=0) / cnt]
            )
            smean = {k: (sums[k][0][tr].mean(), sums[k][1][tr].mean()) for k in sums}
            Xo = knock(Xte, Fte, te, side_o, sums, smean, msl, "o", S)
            Xd = knock(Xte, Fte, te, side_o, sums, smean, msl, "d", S)
            gcode = np.unique(games[tr], return_inverse=True)[1]
            splits = list(GroupKFold(3).split(tr, groups=gcode))
            for name, cols in models.items():
                if name == "mlp":
                    preds = []
                    for s in MLP_SEEDS:
                        m = make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(32,), alpha=1e-3, batch_size=512,
                                          learning_rate_init=1e-3, early_stopping=True, validation_fraction=0.15,
                                          n_iter_no_change=10, max_iter=200, random_state=s))  # fmt: skip
                        m.fit(Xtr[:, cols], y[tr])
                        pr = (
                            m.predict(Xte[:, cols]),
                            m.predict(Xo[:, cols]),
                            m.predict(Xd[:, cols]),
                        )
                        se[f"mlp{s}"][te] = (y[te] - pr[0]) ** 2
                        preds.append(pr)
                    pa, po, pdd = (np.mean([p_[i] for p_ in preds], axis=0) for i in range(3))
                elif name.startswith("lasso"):
                    m = make_pipeline(
                        StandardScaler(), LassoCV(alphas=20, cv=splits, max_iter=5000)
                    )
                    m.fit(Xtr[:, cols], y[tr])
                    pa, po, pdd = (
                        m.predict(Xte[:, cols]),
                        m.predict(Xo[:, cols]),
                        m.predict(Xd[:, cols]),
                    )
                    if name == "lasso":
                        coef = m[-1].coef_
                        diag.append(
                            (
                                T,
                                pt,
                                int((coef[: 2 * S] != 0).sum()),
                                2 * S,
                                coef[2 * S],
                                coef[2 * S + 1],
                                m[-1].alpha_,
                            )
                        )
                        yn = y[tr].copy()
                        RNG.shuffle(yn)
                        mn = make_pipeline(
                            StandardScaler(), LassoCV(alphas=20, cv=splits, max_iter=5000)
                        ).fit(Xtr[:, cols], yn)
                        se["null"][te] = (y[te] - mn.predict(Xte[:, cols])) ** 2
                else:
                    m = LinearRegression().fit(Xtr[:, cols], y[tr])
                    pa, po, pdd = (
                        m.predict(Xte[:, cols]),
                        m.predict(Xo[:, cols]),
                        m.predict(Xd[:, cols]),
                    )
                se[name][te] = (y[te] - pa) ** 2
                vo[name][te] = pa - po
                vd[name][te] = pdd - pa
            log("fit", T, pt)
    return se, vo, vd, test, diag, list(models)


# ---------------------------------------------------------------- scoring
def r2_ci(se_m, se_b, games, n=1000):
    gi, g = np.unique(games, return_inverse=True)
    a, b = np.bincount(g, se_m, len(gi)), np.bincount(g, se_b, len(gi))
    est = 1 - a.sum() / b.sum()
    bs = []
    for _ in range(n):
        i = RNG.integers(0, len(gi), len(gi))
        bs.append(1 - a[i].sum() / b[i].sum())
    lo, hi = np.percentile(bs, [5, 95])
    return 100 * est, 100 * lo, 100 * hi


def travel2(tr, rs, label, start=2020):
    d = tr.join(
        tr.select("team", "side", season=c("season") + 1, last=c("rate")),
        on=["team", "season", "side"],
    ).join(rs, on=["team", "season", "side"])
    out = {}
    for side in ["offense", "defense"]:
        ds = d.filter(c("side") == side).sort("season")
        se0, se1, keys = [], [], []
        for t in range(start, 2025):
            a, b = ds.filter(c("season") < t), ds.filter(c("season") == t)
            if b.height == 0 or a.height == 0:
                continue
            for cols, store in ((["last"], se0), (["last", "roster"], se1)):
                m = LinearRegression().fit(a.select(cols).to_numpy(), a["rate"].to_numpy())
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
        out[side] = (gain, lo, hi)
        print(
            f"    {label:<44} {side}: {100 * gain:+.2f}% (90% {100 * lo:+.2f} to {100 * hi:+.2f})"
        )
    return out


def qb_games(on, V, names):
    qb = on.filter((c("side") == "offense") & (c("group") == "QB") & c("season").is_in(TEST))
    qbp = qb.group_by("gsis_id", "team", "season", "game_id").agg(k=pl.len())
    main_qb = (
        qbp.group_by("team", "season", "gsis_id")
        .agg(tot=c("k").sum())
        .sort("tot", descending=True)
        .unique(["team", "season"], keep="first")
    )
    g = V.group_by("game_id", team=c("posteam"), season=c("season")).agg(
        *(c(f"vo_{m}").mean() for m in names), rate=c("resid").mean(), n=pl.len()
    )
    g = (
        g.join(main_qb.select("team", "season", "gsis_id"), on=["team", "season"])
        .join(qbp.select("gsis_id", "game_id", "k"), on=["gsis_id", "game_id"], how="left")
        .with_columns(share=c("k").fill_null(0) / c("n"))
        .with_columns(
            kind=pl.when(c("share") >= 0.95)
            .then(pl.lit("played"))
            .when(c("share") == 0)
            .then(pl.lit("missed"))
            .otherwise(pl.lit("part"))
        )
    )
    vals = ["rate", *(f"vo_{m}" for m in names)]
    w = g.group_by("team", "season", "kind").agg(
        *((c(v) * c("n")).sum() / c("n").sum() for v in vals), n=c("n").sum(), games=pl.len()
    )
    mi = w.filter(c("kind") == "missed").drop("kind")
    pl_ = w.filter(c("kind") == "played").drop("kind")
    j = mi.join(pl_, on=["team", "season"], suffix="_p")
    wt = (1 / (1 / j["n"] + 1 / j["n_p"])).to_numpy()
    print(
        f"  Team-seasons 2019-2024 where the main QB missed whole games: {j.height}; games missed {int(j['games'].sum())}"
    )
    res = {}
    for v in vals:
        est = fl.wmean_ci((j[v] - j[f"{v}_p"]).to_numpy(), wt)
        res[v] = est
        lab = "actual offense EPA over expected a play" if v == "rate" else f"predicted by {v[3:]}"
        print(
            f"    missed less played, {lab:<44} {est[0]:+.4f} (90% {est[1]:+.4f} to {est[2]:+.4f})"
        )
    return res


# ---------------------------------------------------------------- main
def make_ratings(p, on, info):
    """The two ratings (a, b) and the first look's plus-minus with prior, per player and play season."""

    def rows_of(s):
        return on.filter(c("season") == s).select("game_id", "play_id", "gsis_id", "side", "resid")

    pm_plain = {s: fl.rapm_fit(rows_of(s), ALPHA) for s in SEASONS}
    log("plain plus-minus")
    pmdf = pl.concat(
        [
            pl.DataFrame({"gsis_id": list(v), "pm": list(v.values())}).with_columns(
                season=pl.lit(s)
            )
            for s, v in pm_plain.items()
        ]
    )
    pmp, prev = {}, None
    for s in SEASONS:
        pmp[s] = fl.rapm_fit(
            rows_of(s), ALPHA, {k: 0.5 * v for k, v in prev.items()} if prev else None
        )
        prev = pmp[s]
    log("plus-minus with last season's prior")
    F = season_stats(p, on)
    log("stats", F.height)

    SMS = {T: stats_ratings(F, info, pmdf, T, with_pm=False) for T in PLAY_SEASONS}
    log("stats ratings")
    SMP = {T: stats_ratings(F, info, pmdf, T, with_pm=True) for T in PLAY_SEASONS}
    log("stats+pm priors")
    ra_end = {2017: pmp[2017]}
    for s in range(2018, 2024):
        pr = dict(zip(SMP[s]["gsis_id"].to_list(), SMP[s]["rating"].to_list(), strict=True))
        ra_end[s] = fl.rapm_fit(rows_of(s), ALPHA, pr)
        log("plus-minus from his own stats", s)

    R = []
    for T in PLAY_SEASONS:
        base = info.filter(c("season") == T).select("gsis_id", "season", "group")
        d_a = pl.DataFrame({"gsis_id": list(ra_end[T - 1]), "ra0": list(ra_end[T - 1].values())})
        d_p = pl.DataFrame({"gsis_id": list(pmp[T - 1]), "rp": list(pmp[T - 1].values())})
        x = (
            base.join(d_a, on="gsis_id", how="left")
            .join(d_p, on="gsis_id", how="left")
            .join(SMP[T].select("gsis_id", ra_new=c("rating")), on="gsis_id", how="left")
            .join(SMS[T].select("gsis_id", rs=c("rating"), new=c("new")), on="gsis_id", how="left")
        )
        R.append(
            x.with_columns(ra=c("ra0").fill_null(c("ra_new")), rp=c("rp").fill_null(0.0)).select(
                "gsis_id", "season", "ra", "rs", "rp", "new"
            )
        )
    R = pl.concat(R)
    return R, pmdf, pmp


def main():
    p = fl.plays()
    on = fl.on_field(p)
    info = fl.player_info(on)
    pp = p.filter(c("season").is_in(SEASONS))
    log("plays", p.height)

    R, pmdf, pmp = make_ratings(p, on, info)

    print("== DATA ==")
    print(
        f"Plays with both ratings: seasons {PLAY_SEASONS[0]}-{PLAY_SEASONS[-1]}; held-out seasons {TEST[0]}-{TEST[-1]}"
    )
    oo = on.filter(c("season").is_in(PLAY_SEASONS)).join(R, on=["gsis_id", "season"])
    print(
        f"  share of player-plays by a player new that season (no rating from the season before): {oo['new'].mean():.1%}"
    )
    print(
        "  spread of the ratings by group (player-plays): "
        + "; ".join(
            f"{g} a {oo.filter(c('group') == g)['ra'].std():.4f} b {oo.filter(c('group') == g)['rs'].std():.4f}"
            for g in GROUPS
        )
    )

    print("\n== THE RATINGS ON THEIR OWN (player-seasons, 300+ plays in both seasons) ==")
    team = on.group_by("gsis_id", "season").agg(team=c("team").mode().first())
    Q = (
        R.join(info.select("gsis_id", "season", "group", "n"), on=["gsis_id", "season"])
        .join(pmdf.rename({"pm": "pm_now"}), on=["gsis_id", "season"])
        .join(
            pmdf.select("gsis_id", season=c("season") + 1, pm_last=c("pm")),
            on=["gsis_id", "season"],
        )
        .join(team, on=["gsis_id", "season"])
        .join(
            team.select("gsis_id", season=c("season") + 1, team_last=c("team")),
            on=["gsis_id", "season"],
        )
        .join(
            info.select("gsis_id", season=c("season") + 1, n_last=c("n")), on=["gsis_id", "season"]
        )
        .join(
            R.select("gsis_id", season=c("season") - 1, rs_next=c("rs")),
            on=["gsis_id", "season"],
            how="left",
        )
        .filter((c("n") >= 300) & (c("n_last") >= 300))
        .with_columns(moved=c("team") != c("team_last"))
    )
    for lab, q in (("stayed", Q.filter(~c("moved"))), ("moved", Q.filter(c("moved")))):
        print(f"  {lab}:")
        print(
            f"    this season's plain plus-minus, from last season's plain plus-minus: {fl.rr(q['pm_last'], q['pm_now'])}"
        )
        print(
            f"    ... from the own-stats rating (b, last season's stats only):        {fl.rr(q['rs'], q['pm_now'])}"
        )
        print(
            f"    ... from plus-minus that starts from his own stats (a):             {fl.rr(q['ra'], q['pm_now'])}"
        )
        print(
            f"    the own-stats rating, season to season (separate seasons' stats):   {fl.rr(q['rs'], q['rs_next'])}"
        )
    mv = Q.filter(c("moved"))
    print(
        "  moved, by group: own-stats rating -> plain plus-minus on the new team (and last plain plus-minus -> it): "
        + "; ".join(
            f"{g} {fl.r_of(mv.filter(c('group') == g)['rs'], mv.filter(c('group') == g)['pm_now'])[0]:+.2f} ({fl.r_of(mv.filter(c('group') == g)['pm_last'], mv.filter(c('group') == g)['pm_now'])[0]:+.2f}, n {mv.filter(c('group') == g).height})"
            for g in GROUPS
        )
    )

    keys, X, Fm, sums, slots, side_o = build(on, R)
    cache = fl.get_config().zone("interim") / "voe_second_look_fits.pkl"
    if cache.exists():
        se, vo, vd, test, diag, names = pickle.loads(cache.read_bytes())
        log("fits read from the cache", cache)
    else:
        se, vo, vd, test, diag, names = fit_all(keys, X, Fm, sums, slots, side_o)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps((se, vo, vd, test, diag, names)))
    games = keys["game_id"].to_numpy()

    print(
        "\n== HELD-OUT PLAYS, 2019-2024 (share of a play's EPA over expected explained, against predicting the training average; 90% by resampling games) =="
    )
    label = {"sum_pm": "plain sum: plus-minus with last season's prior (first look)", "sum_a": "plain sum: plus-minus from his own stats (a)",
             "sums": "plain sums: (a) and the own-stats rating (b)", "lasso_slots": "VOE lasso, slot ratings only (no sums)",
             "lasso": "VOE lasso, slot ratings and the sums (H75)", "mlp": "VOE small MLP (32 units), 3 seeds averaged",
             "null": "VOE lasso fit on shuffled plays (the null)"}  # fmt: skip
    for m in [*names, "null", *(f"mlp{s}" for s in MLP_SEEDS)]:
        for pt in ("all", "pass", "run"):
            mk = test if pt == "all" else test & (keys["play_type"].to_numpy() == pt)
            est = r2_ci(se[m][mk], se["base"][mk], games[mk])
            if pt == "all":
                line = f"  {label.get(m, f'MLP seed {m[3:]}'):<62} {est[0]:+.3f}% (90% {est[1]:+.3f} to {est[2]:+.3f})"
            else:
                line += f"; {pt} {est[0]:+.3f}%"
        print(line)
    print(
        "  by season (lasso | MLP): "
        + "; ".join(
            f"{T} {100 * (1 - se['lasso'][test & (keys['season'].to_numpy() == T)].sum() / se['base'][test & (keys['season'].to_numpy() == T)].sum()):+.2f} | {100 * (1 - se['mlp'][test & (keys['season'].to_numpy() == T)].sum() / se['base'][test & (keys['season'].to_numpy() == T)].sum()):+.2f}"
            for T in TEST
        )
    )
    d = (se["lasso"] - se["mlp"])[test]
    print(
        f"  the lasso less the MLP, per play: MLP better by {100 * d.sum() / se['base'][test].sum():+.3f} points of the explained share"
    )
    print(
        "  the lasso's choices (standardized coefficients): "
        + "; ".join(
            f"{T} {pt}: {k}/{tot} slot inputs kept, sum (a) {a_:+.4f}, sum (b) {b_:+.4f}"
            for T, pt, k, tot, a_, b_, _ in diag
            if T in (2019, 2024)
        )
    )

    print(
        "\n== DOES IT TRAVEL? (the roster-change test, a team's next season; 2020-2024, fit on earlier seasons) =="
    )
    tr = fl.team_rates(pp)
    V = keys.with_columns(
        *(pl.Series(f"vo_{m}", vo[m]) for m in names), *(pl.Series(f"vd_{m}", vd[m]) for m in names)
    ).filter(pl.Series(test))
    res = {}
    for m in names:
        rs = pl.concat(
            [
                V.group_by(team=c("posteam"), season=c("season"))
                .agg(roster=c(f"vo_{m}").mean())
                .with_columns(side=pl.lit("offense")),
                V.group_by(team=c("defteam"), season=c("season"))
                .agg(roster=c(f"vd_{m}").mean())
                .with_columns(side=pl.lit("defense")),
            ]
        )
        res[m] = travel2(tr, rs, label[m])
    pmpdf = pl.concat(
        [
            pl.DataFrame({"gsis_id": list(v), "pm": list(v.values())}).with_columns(
                season=pl.lit(s)
            )
            for s, v in pmp.items()
        ]
    )
    res["pmp_roster"] = travel2(
        tr, fl.roster_sum(on, pmpdf, "pm"), "check: first look's plus-minus with prior"
    )
    res["pm_roster"] = travel2(tr, fl.roster_sum(on, pmdf, "pm"), "plain plus-minus (first look)")
    rec = fl.recreation(on)
    ev = fl.per_snap(rec, "exp_voe").filter(c("half") == "all")
    res["rec"] = travel2(tr, fl.roster_sum(on, ev, "v"), "the recreation (old VOE, fixed)")

    print("\n== H75 REAL? GAMES THE MAIN QB MISSED (2019-2024) ==")
    qb = qb_games(on, V, names)

    print("\n== H75 VERDICT CHECKS ==")
    a = qb["vo_lasso"]
    real = (a[2] < 0) and (a[0] <= qb["rate"][0] / 3)
    g, lo, hi = res["lasso"]["offense"]
    pays = (lo > 0) and (g > res["rec"]["offense"][0])
    print(
        f"  Real? the lasso's predicted QB-miss change {a[0]:+.4f} (upper {a[2]:+.4f}) against actual {qb['rate'][0]:+.4f}: {'pass' if real else 'fail'}"
    )
    print(
        f"  Pays? the lasso's roster-change gain on offense {100 * g:+.2f}% (lower {100 * lo:+.2f}) against the recreation {100 * res['rec']['offense'][0]:+.2f}%: {'pass' if pays else 'fail'}"
    )
    log("done")


if __name__ == "__main__":
    main()
