"""Roles exploration: H102, an in-season chance his role is unchanged (pre-registered in EXPLORATION.md).

The label: M1's cluster (the role table, no measurables) for his season, against last season's, same group,
200+ snaps both seasons. In-season inputs through week 4 and week 8, with no participation: snap counts
(player_game.snaps), box-score usage (player_game.stats), middle targets and tackle depth (play-by-play),
each against his own last season; a team-change flag; his team's pass rate over expected and plays a game
(team_game.pace) against last season; last season's label and the mixture's certainty. Logistic regression
with group dummies, walk-forward by season (2018-2024 scored), against each group's training change rate.

Run from pcf/projects/roles-archetypes/explore: PYTHONIOENCODING=utf-8 <venv python> h102_role_change.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
import roles_common as rc
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

c = pl.col
T = rc.CFG.zone("tables")
RNG = np.random.default_rng(rc.CFG.seed)
B = 2000
SEASONS = range(2016, 2025)
EPS = 1e-6

# --- the labels and their changes
lat = pl.read_parquet(rc.O / "latent.parquet").filter(c("half") == "all")
cnt = pl.read_parquet(rc.O / "counts.parquet").filter(c("half") == "all").select("gsis_id", "team", "season", "snaps")
lab = (lat.join(cnt, on=["gsis_id", "team", "season"]).sort("snaps", descending=True).unique(["gsis_id", "season"], keep="first")
       .with_columns(side=pl.when(c("group").is_in(list(rc.OFFENSE))).then(pl.lit("offense")).otherwise(pl.lit("defense")))
       .select("gsis_id", "season", "team", "side", "group", "m1_lab", "m1_prob"))
prev = lab.select("gsis_id", "group", season=c("season") + 1, team_prev=c("team"), lab_prev=c("m1_lab"), prob_prev=c("m1_prob"))
rows = lab.join(prev, on=["gsis_id", "season", "group"], how="inner").with_columns(
    changed=(c("m1_lab") != c("lab_prev")).cast(pl.Int8), team_change=(c("team") != c("team_prev")).cast(pl.Float64))
print(f"player-season pairs (same group, 200+ snaps both): {rows.height:,}; changed label {rows['changed'].mean():.1%}")
print(rows.group_by("group").agg(n=pl.len(), changed=c("changed").mean()).sort("group"))

# --- per player-game in-season inputs (all known after each game, before the next)
pbp_cols = ["game_id", "season_type", "play_type", "receiver_player_id", "pass_location", "yards_gained", "two_point_attempt",
            "solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id", "assist_tackle_2_player_id",
            "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id"]
pg = []
for s in SEASONS:
    sn = pl.read_parquet(T / "player_game" / "snaps" / f"season={s}" / "data.parquet")
    st = pl.read_parquet(T / "player_game" / "stats" / f"season={s}" / "data.parquet", columns=[
        "gsis_id", "game_id", "targets", "carries", "receiving_air_yards", "def_tackles_solo", "def_tackle_assists", "def_tackles_with_assist",
        "def_sacks", "def_qb_hits", "def_pass_defended"])
    p = pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=pbp_cols).filter(
        (c("season_type") == "REG") & c("play_type").is_in(["pass", "run"]) & (c("two_point_attempt") != 1))
    mid = p.filter(c("receiver_player_id").is_not_null()).group_by("game_id", gsis_id=c("receiver_player_id")).agg(
        middle=(c("pass_location") == "middle").sum(), loc_n=c("pass_location").is_not_null().sum())
    tk = pl.concat([p.select("game_id", "yards_gained", gsis_id=c(k)) for k in pbp_cols[7:]]).drop_nulls("gsis_id")
    tk = tk.group_by("game_id", "gsis_id").agg(tkl_yds=c("yards_gained").sum(), tkl_n=pl.len())
    d = (sn.join(st, on=["gsis_id", "game_id"], how="left").join(mid, on=["game_id", "gsis_id"], how="left").join(tk, on=["game_id", "gsis_id"], how="left")
         .with_columns(week=c("game_id").str.slice(5, 2).cast(pl.Int32), season=pl.lit(s)).fill_null(0))
    pg.append(d.filter(c("week") <= 18))
pg = pl.concat(pg, how="diagonal_relaxed")

NUM = dict(  # name: (numerator, denominator expression, prior weight)
    tgt_snap=(c("targets"), "off", 100), car_snap=(c("carries"), "off", 100), adot=(c("receiving_air_yards"), c("targets"), 10),
    middle=(c("middle"), c("loc_n"), 10), tkl_snap=(c("def_tackles_solo") + c("def_tackle_assists") + c("def_tackles_with_assist"), "def", 100),
    solo=(c("def_tackles_solo"), c("def_tackles_solo") + c("def_tackle_assists") + c("def_tackles_with_assist"), 10),
    tkl_depth=(c("tkl_yds"), c("tkl_n"), 10), rush_snap=(c("def_sacks") + c("def_qb_hits"), "def", 100), pd_snap=(c("def_pass_defended"), "def", 100),
)


def summarize(d: pl.DataFrame, by: list[str]) -> pl.DataFrame:
    agg = [c("offense_snaps").sum().alias("off"), c("defense_snaps").sum().alias("def"), c("offense_pct").mean().alias("off_pct"),
           c("defense_pct").mean().alias("def_pct"), pl.len().alias("gp")]
    for n, (num, den, _) in NUM.items():
        agg.append(num.sum().alias(f"{n}_num"))
        agg.append((c("offense_snaps") if isinstance(den, str) and den == "off" else c("defense_snaps") if isinstance(den, str) else den).sum().alias(f"{n}_den"))
    return d.group_by(by).agg(agg)


def rates(d: pl.DataFrame, ref: pl.DataFrame, tag: str) -> pl.DataFrame:
    """Shrunk rates (toward the group's pooled rate in `ref`) and the snap share, suffixed by tag."""
    out = d.with_columns(snap=pl.when(c("side") == "offense").then(c("off_pct")).otherwise(c("def_pct")))
    for n, (_, _, k) in NUM.items():
        pooled = ref.group_by("group").agg(m=c(f"{n}_num").sum() / c(f"{n}_den").sum().clip(1))
        out = out.join(pooled, on="group", how="left").with_columns(((c(f"{n}_num") + k * c("m")) / (c(f"{n}_den") + k)).alias(n)).drop("m")
    return out.select("gsis_id", "season", "snap", "gp", *NUM).rename({x: f"{x}_{tag}" for x in ["snap", "gp", *NUM]})


meta = rows.select("gsis_id", "season", "side", "group")
last = summarize(pg, ["gsis_id", "season"]).with_columns(season=c("season") + 1).join(meta, on=["gsis_id", "season"], how="inner")
last_r = rates(last, last, "last")

pace = pl.concat([pl.read_parquet(T / "team_game" / "pace" / f"season={s}" / "data.parquet", columns=["game_id", "team", "season", "proe", "plays"]) for s in SEASONS])
pace = pace.with_columns(week=c("game_id").str.slice(5, 2).cast(pl.Int32)).filter(c("week") <= 18)
pace_last = pace.group_by("team", "season").agg(proe_last=c("proe").mean(), plays_last=c("plays").mean()).with_columns(season=c("season") + 1)


def frame(k: int) -> pl.DataFrame:
    cur = summarize(pg.filter(c("week") <= k), ["gsis_id", "season"]).join(meta, on=["gsis_id", "season"], how="inner")
    cur_r = rates(cur, last, "now")
    tp = pace.filter(c("week") <= k).group_by("team", "season").agg(proe_now=c("proe").mean(), plays_now=c("plays").mean())
    f = (rows.join(last_r, on=["gsis_id", "season"], how="left").join(cur_r, on=["gsis_id", "season"], how="left")
         .join(tp, on=["team", "season"], how="left").join(pace_last.rename({"team": "team_prev"}), on=["team_prev", "season"], how="left"))
    f = f.with_columns(no_games=c("gp_now").is_null().cast(pl.Float64))
    for x in ["snap", *NUM]:  # no games yet: his last season stands in, flagged
        f = f.with_columns(c(f"{x}_now").fill_null(c(f"{x}_last")))
    f = f.with_columns(c("gp_now").fill_null(0)).with_columns(
        [(c(f"{x}_now") - c(f"{x}_last")).alias(f"{x}_d") for x in ["snap", *NUM]]
        + [(c("proe_now") - c("proe_last")).alias("proe_d"), (c("plays_now") - c("plays_last")).alias("plays_d")])
    return f.fill_null(0).fill_nan(0)


def design(f: pl.DataFrame) -> tuple[np.ndarray, list[str]]:
    num = ["team_change", "prob_prev", "no_games", "gp_now", "proe_d", "plays_d"] + [f"{x}_{t}" for x in ["snap", *NUM] for t in ("now", "d")]
    X = f.select(num).to_numpy().astype(float)
    dums = []
    for gg in rc.GROUPS:
        ig = (f["group"] == gg).to_numpy()
        dums.append(ig.astype(float))
        for L in sorted(rows.filter(c("group") == gg)["lab_prev"].unique().to_list())[1:]:
            dums.append((ig & (f["lab_prev"] == L).to_numpy()).astype(float))
        # usage inputs act within a group: interact the snap-share delta with the group
        dums.append(ig * f["snap_d"].to_numpy())
    return np.column_stack([X, *dums]), num


def ll(y, p):
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


res = {}
for k in (4, 8):
    f = frame(k)
    X, _ = design(f)
    y = f["changed"].to_numpy()
    seas = f["season"].to_numpy()
    grp = f["group"].to_numpy()
    ts = (f["team"] + f["season"].cast(pl.Utf8)).to_numpy()
    pm, pb, keep = np.zeros(len(y)), np.zeros(len(y)), np.zeros(len(y), bool)
    for s in range(2018, 2025):
        tr, te = seas < s, seas == s
        sc = StandardScaler().fit(X[tr])
        m = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(X[tr]), y[tr])
        pm[te] = m.predict_proba(sc.transform(X[te]))[:, 1]
        for gg in rc.GROUPS:
            ig = grp == gg
            pb[te & ig] = y[tr & ig].mean()
        keep |= te
    yk, gain = y[keep], (ll(y, pb) - ll(y, pm))[keep]
    u, inv = np.unique(ts[keep], return_inverse=True)
    W = RNG.poisson(1.0, size=(B, len(u)))[:, inv].astype(float)
    bs = (W @ gain) / W.sum(1)
    lo, hi = np.percentile(bs, [5, 95])
    lg = np.log(np.clip(pm[keep], EPS, 1 - EPS) / (1 - np.clip(pm[keep], EPS, 1 - EPS)))
    slope = LogisticRegression(C=1e6, max_iter=5000).fit(lg.reshape(-1, 1), yk).coef_[0, 0]
    base_ll = ll(y, pb)[keep].mean()
    print(f"\nthrough week {k}: scored {keep.sum():,} pairs (2018-2024); change rate {yk.mean():.1%}")
    print(f"  log loss: baseline {base_ll:.4f}, model {ll(y, pm)[keep].mean():.4f}; gain {gain.mean():.4f} ({gain.mean() / base_ll:.1%} of the baseline; 90% {lo:.4f} to {hi:.4f}); calibration slope {slope:.2f}")
    # how sharp: the changed rate in the model's top fifth against its bottom fifth
    q = np.quantile(pm[keep], [0.2, 0.8])
    print(f"  changed in the model's bottom fifth {yk[pm[keep] <= q[0]].mean():.1%}, top fifth {yk[pm[keep] >= q[1]].mean():.1%}")
    for gg in rc.GROUPS:
        ig = grp[keep] == gg
        print(f"  {gg:4} n {ig.sum():4d}  change {yk[ig].mean():.1%}  gain {gain[ig].mean():+.4f}")
    res[k] = (gain.mean(), lo, hi, slope)

    # what drives it: the univariate gain of the snap-share delta alone
    if k == 8:
        Xs = np.column_stack([f["snap_d"].to_numpy(), np.abs(f["snap_d"].to_numpy()), *[(grp == gg).astype(float) for gg in rc.GROUPS]])
        ps = np.zeros(len(y))
        for s in range(2018, 2025):
            tr, te = seas < s, seas == s
            sc = StandardScaler().fit(Xs[tr])
            ps[te] = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(Xs[tr]), y[tr]).predict_proba(sc.transform(Xs[te]))[:, 1]
        g2 = (ll(y, pb) - ll(y, ps))[keep]
        print(f"  the obvious input: the snap-share change alone (with group dummies) gains {g2.mean():.4f}, {g2.mean() / gain.mean():.0%} of the full model's gain")

g8, lo8, hi8, sl8 = res[8]
held = lo8 > 0
print("\n-> H102 (week 8):", "HELD" if held and 0.8 <= sl8 <= 1.2 else "HELD IN PART" if held else "FAILED")
print("   week 4 (Claude's side bet, 50%):", "gain clear" if res[4][1] > 0 else "gain not clear")
