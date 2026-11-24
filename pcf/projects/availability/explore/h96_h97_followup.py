"""Availability exploration: the follow-up of H96 against H97 (pre-registered in EXPLORATION.md,
"Follow-up: H96 against H97"). Why can plays differ in risk (H97) while risk-weighted snaps don't
forecast better than counts (H96)? Six checks, A to F.

Rows, scoring and intervals are H96's: player-games played 2017-2024, an in-game injury, walk-forward
by season (2017 fits on itself), position dummies, logistic, held-out log loss, 2,000 Poisson-bootstrap
draws over team-weeks. Each play's risk is H97's play model fitted on earlier seasons only.

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from pcf.config import get_config

c = pl.col
CFG = get_config()
O = CFG.zone("interim") / "availability"
T = CFG.zone("tables")
RNG = np.random.default_rng(CFG.seed)
B = 2000
NSIM = 10
GROUPS = ["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"]
H98_HL = [1, 1, 4, 4, 8, 2, 4, 2]  # H98's half-life chosen per season 2017-2024 (h96_h98_workload.txt)

# --- personal contacts per player-game (check D) ---
ids = ["rusher_player_id", "receiver_player_id", "passer_player_id", "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id",
       "qb_hit_1_player_id", "qb_hit_2_player_id", "solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id",
       "assist_tackle_2_player_id", "assist_tackle_3_player_id", "assist_tackle_4_player_id", "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id"]
cols = ["game_id", "play_id", "season_type", "play_type", "complete_pass", "sack", "qb_hit", *ids]
p = pl.concat([pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=cols) for s in range(2016, 2025)], how="diagonal_relaxed")
p = p.filter((c("season_type") == "REG") & c("play_type").is_in(["run", "pass"]))
roles = [
    p.filter(c("play_type") == "run").select("game_id", "play_id", gsis_id=c("rusher_player_id")),
    p.filter((c("play_type") == "pass") & (c("complete_pass") == 1)).select("game_id", "play_id", gsis_id=c("receiver_player_id")),
    p.filter((c("sack") == 1) | (c("qb_hit") == 1)).select("game_id", "play_id", gsis_id=c("passer_player_id")),
    *[p.select("game_id", "play_id", gsis_id=c(k)) for k in ids[3:]],
]
con = pl.concat(roles).drop_nulls().unique().group_by("gsis_id", "game_id").agg(con=pl.len())

# --- player-games, as H96 ---
pr = pl.read_parquet(O / "player_play_risk.parquet")
risk = pr.with_columns(l1=(1 - c("risk")).log()).group_by("gsis_id", "game_id").agg(plays=pl.len(), wsum=c("risk").sum(), p_game=1 - c("l1").sum().exp())
pg = pl.read_parquet(O / "player_games.parquet").filter((c("season") >= 2016) & c("position").is_in(GROUPS))
pg = (pg.join(risk, on=["gsis_id", "game_id"], how="left").join(con, on=["gsis_id", "game_id"], how="left")
      .with_columns(c("plays").fill_null(0), c("wsum").fill_null(0.0), c("p_game").fill_null(0.0), c("con").fill_null(0)).sort("gsis_id", "season", "week"))


def win(col, name):
    return {
        f"{name}_last": c(col).shift(1).over("gsis_id", "season").fill_null(0),
        f"{name}4": c(col).shift(1).rolling_sum(4, min_samples=1).over("gsis_id", "season").fill_null(0),
        f"{name}S": (c(col).cum_sum() - c(col)).over("gsis_id", "season"),
    }


pg = pg.with_columns(
    **win("plays", "cnt"), **win("wsum", "w"), **win("con", "con"),
    **{f"ew{h}": c("wsum").shift(1).ewm_mean(half_life=h, adjust=True).over("gsis_id").fill_null(0) for h in set(H98_HL)},
    **{f"ec{h}": c("plays").shift(1).ewm_mean(half_life=h, adjust=True).over("gsis_id").fill_null(0) for h in set(H98_HL)},
    inj_car=(c("hurt").cum_sum() - c("hurt")).over("gsis_id"),
    cpg=((c("plays").cum_sum() - c("plays")) / (c("plays").cum_count() - 1).clip(1)).over("gsis_id"),
    crisk_raw=pl.when((c("plays").cum_sum() - c("plays")).over("gsis_id") > 0).then(((c("wsum").cum_sum() - c("wsum")) / (c("plays").cum_sum() - c("plays"))).over("gsis_id")),
)
# no history yet: his position's average risk per play, with a flag
pg = pg.with_columns(no_hist=c("crisk_raw").is_null().cast(pl.Int8),
                     crisk=c("crisk_raw").fill_null(c("crisk_raw").mean().over("position")))
EPS = float(pr["risk"].mean())  # one average play's risk, so log(w + EPS) mirrors log(1 + snaps)
pg = pg.with_columns(
    **{f"l{k}": (c(k) + 1).log() for k in ["plays", "cnt_last", "cnt4", "cntS"]},
    **{f"l{k}": (c(k) + EPS).log() for k in ["wsum", "w4", "wS"]},
)
d = pg.filter((c("played") == 1) & (c("season") >= 2017)).with_columns(
    gw=pl.concat_str([c("season").cast(pl.Utf8), c("week").cast(pl.Utf8), c("team")], separator="-"))
print(f"rows (played, 2017-2024): {d.height:,}; injuries {int(d['hurt'].sum()):,}")
G = np.column_stack([(d["position"] == g).to_numpy() for g in GROUPS[1:]]).astype(float)
y = d["hurt"].to_numpy().astype(float)
season = d["season"].to_numpy()
hl_of = dict(zip(range(2017, 2025), H98_HL, strict=True))


def X(cols_, s=None):
    cs = [k.replace("{h}", str(hl_of[s])) if s else k for k in cols_]
    return np.column_stack([G] + [d[k].to_numpy().astype(float)[:, None] for k in cs])


def wf(cols_, yy):
    L = np.zeros(len(yy))
    for s in range(2017, 2025):
        tr, te = season < s, season == s
        if tr.sum() == 0:
            tr = season == 2017
        Xa = X(cols_, s)
        sc = StandardScaler().fit(Xa[tr])
        m = LogisticRegression(C=1.0, max_iter=3000).fit(sc.transform(Xa[tr]), yy[tr])
        q = np.clip(m.predict_proba(sc.transform(Xa[te]))[:, 1], 1e-7, 1 - 1e-7)
        L[te] = -(yy[te] * np.log(q) + (1 - yy[te]) * np.log(1 - q))
    return L


u, inv = np.unique(d["gw"].to_numpy(), return_inverse=True)
W = RNG.poisson(1.0, size=(B, len(u))).astype(np.float32)


def gain(La, Lb, Lref, label="", show=True):
    dd, base = np.bincount(inv, weights=La - Lb), np.bincount(inv, weights=Lref)
    est = dd.sum() / base.sum()
    lo, hi = np.percentile((W @ dd) / (W @ base), [5, 95])
    if show:
        tag = "clear" if lo > 0 else "clear, worse" if hi < 0 else "covers 0"
        print(f"  {label:66} {100 * est:+.3f}% ({100 * lo:+.3f} to {100 * hi:+.3f})  {tag}")
    return est, lo, hi


COUNTS = ["cnt_last", "cnt4", "cntS"]
WEIGHTED = ["cnt_last", "w4", "wS"]  # H96's weighted set (last game's snaps as the base in both)

print("=" * 100)
print("A. Averaging: within position, how close is the risk-weighted sum to a count?")
A = d.filter(c("cnt4") > 0)
rows = []
for g in GROUPS:
    x = A.filter(c("position") == g)
    r4 = np.corrcoef(x["cnt4"].to_numpy(), x["w4"].to_numpy())[0, 1]
    rS = np.corrcoef(x["cntS"].to_numpy(), x["wS"].to_numpy())[0, 1] if (x["cntS"] > 0).sum() > 10 else np.nan
    gm = x.filter(c("plays") >= 20).with_columns(m=c("wsum") / c("plays"))["m"]
    pp_g = pr.join(pg.filter(c("position") == g).select("gsis_id", "game_id"), on=["gsis_id", "game_id"])["risk"]
    rows.append(r4)
    print(f"  {g}: corr(last-4 weighted, last-4 count) {r4:.3f}; season to date {rS:.3f}; a game's average risk per play varies by {gm.std() / gm.mean():.1%} of its mean (single plays: {pp_g.std() / pp_g.mean():.0%})")
med = float(np.median(rows))
print(f"  -> median group correlation {med:.3f}: {'averaging explains most of it (0.95+)' if med >= 0.95 else 'below 0.95'}")

print("\nB. Acute, not cumulative: the same game, after the fact (not a forecast)")
Lc_same = wf(["plays"], y)
Lw_same = wf(["wsum"], y)
Lb_same = wf(["plays", "wsum"], y)
gain(Lc_same, Lw_same, Lc_same, "B: this game's weighted sum against its count (pre-registered)")
gain(Lc_same, Lb_same, Lc_same, "   both, against the count alone")
Lcon_same = wf(["plays", "con"], y)
gain(Lc_same, Lcon_same, Lc_same, "   (D's description) this game's personal contacts beside its count")

print("\nC. The ceiling: a simulated world where the play model is exactly true and risk is acute")
pgame = d["p_game"].to_numpy()
print(f"  real injuries per game {y.mean():.4f}; the model's expected per game {pgame.mean():.4f} (scrimmage plays only; real ones include special teams)")
c1, c2, c2_cover = [], [], 0
for _ in range(NSIM):
    ys = (RNG.random(len(pgame)) < pgame).astype(float)
    a, b = wf(["plays"], ys), wf(["wsum"], ys)
    c1.append(gain(a, b, a, show=False)[0])
    a, b = wf(COUNTS, ys), wf(WEIGHTED, ys)
    e, lo, hi = gain(a, b, a, show=False)
    c2.append(e)
    c2_cover += int(lo <= 0 <= hi)
print(f"  C1, same game, weighted against count: mean {100 * np.mean(c1):+.3f}% over {NSIM} draws (range {100 * min(c1):+.3f} to {100 * max(c1):+.3f})")
print(f"  C2, H96's forward test on the drawn injuries: mean {100 * np.mean(c2):+.3f}% (range {100 * min(c2):+.3f} to {100 * max(c2):+.3f}); intervals covering 0: {c2_cover} of {NSIM}")

print("\nD. Personal contacts (carries, catches, hit or sacked as passer, tackles made), a forecast like H96")
Lcnt = wf(COUNTS, y)
Lcon = wf([*COUNTS, "con_last", "con4", "conS"], y)
gain(Lcnt, Lcon, Lcnt, "D: contacts (last game, last 4, season) beside the counts (pre-registered)")
Lw = wf(WEIGHTED, y)
gain(Lcnt, Lw, Lcnt, "   (H96 again, for scale) risk-weighted against counts")
for g in ["RB", "WR", "TE", "LB", "DB", "QB"]:
    x = d.filter((c("position") == g) & (c("con4") > 0))
    print(f"    {g}: contacts per snap over the last 4 games, mean {(x['con4'] / x['cnt4']).mean():.3f}; corr with the count {np.corrcoef(x['cnt4'].to_numpy(), x['con4'].to_numpy())[0, 1]:.2f}")

print("\nE. Is H98's gain recency or the risk weights? (each beside the counts set, H98's half-lives)")
Le_c = wf([*COUNTS, "ec{h}"], y)
Le_w = wf([*COUNTS, "ew{h}"], y)
ec = gain(Lcnt, Le_c, Lcnt, "   recency on plain counts, beside the counts")[0]
ew = gain(Lcnt, Le_w, Lcnt, "   recency on risk-weighted plays (H98's), beside the counts")[0]
gain(Le_c, Le_w, Lcnt, "E: weighted against plain counts, both with recency")
print(f"  -> recency on plain counts gets {ec / ew:.0%} of the weighted version's gain" if ew > 0 else "  -> the weighted version gains nothing here")

print("\nF. A trait, not a load: his career-long average risk per play")
Lf0 = wf([*COUNTS, "inj_car", "cpg", "no_hist"], y)
Lf1 = wf([*COUNTS, "inj_car", "cpg", "no_hist", "crisk"], y)
gain(Lf0, Lf1, Lf0, "F: career risk per play beside career injuries and snaps per game")

print("\nG (addendum, after A-D's first run): the same tests with log exposure, log(1 + snaps) and log(weighted + one play's risk)")
LCOUNTS = ["lcnt_last", "lcnt4", "lcntS"]
LWEIGHTED = ["lcnt_last", "lw4", "lwS"]
La, Lb_ = wf(["lplays"], y), wf(["lwsum"], y)
gain(La, Lb_, La, "G-B: this game's log weighted sum against its log count (real injuries)")
La, Lb_ = wf(LCOUNTS, y), wf(LWEIGHTED, y)
gain(La, Lb_, La, "G-H96: last 4 and season, log weighted against log counts (real)")
g1, g2, g2_cover = [], [], 0
for _ in range(NSIM):
    ys = (RNG.random(len(pgame)) < pgame).astype(float)
    a, b = wf(["lplays"], ys), wf(["lwsum"], ys)
    g1.append(gain(a, b, a, show=False)[0])
    a, b = wf(LCOUNTS, ys), wf(LWEIGHTED, ys)
    e, lo, hi = gain(a, b, a, show=False)
    g2.append(e)
    g2_cover += int(lo <= 0 <= hi)
print(f"  G-C1, same game on drawn injuries: mean {100 * np.mean(g1):+.3f}% (range {100 * min(g1):+.3f} to {100 * max(g1):+.3f})")
print(f"  G-C2, H96's forward test on drawn injuries: mean {100 * np.mean(g2):+.3f}% (range {100 * min(g2):+.3f} to {100 * max(g2):+.3f}); intervals covering 0: {g2_cover} of {NSIM}")

