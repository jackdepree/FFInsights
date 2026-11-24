"""Availability exploration: addendum H of the H96-against-H97 follow-up (EXPLORATION.md): touches
against the other personal contacts. Prep and scoring copied from h96_h97_followup.py.

Originally: the follow-up of H96 against H97 (pre-registered in EXPLORATION.md,
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

ids_def = ["sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id", "qb_hit_1_player_id", "qb_hit_2_player_id",
           "solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id", "assist_tackle_2_player_id",
           "assist_tackle_3_player_id", "assist_tackle_4_player_id", "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id"]
cols = ["game_id", "play_id", "season_type", "play_type", "complete_pass", "sack", "qb_hit", "rusher_player_id", "receiver_player_id", "passer_player_id", *ids_def]
p = pl.concat([pl.read_parquet(T / "play" / "pbp" / f"season={s}" / "data.parquet", columns=cols) for s in range(2016, 2025)], how="diagonal_relaxed")
p = p.filter((c("season_type") == "REG") & c("play_type").is_in(["run", "pass"]))
touch = pl.concat([
    p.filter(c("play_type") == "run").select("game_id", "play_id", gsis_id=c("rusher_player_id")),
    p.filter((c("play_type") == "pass") & (c("complete_pass") == 1)).select("game_id", "play_id", gsis_id=c("receiver_player_id")),
]).drop_nulls().unique()
other = pl.concat([
    p.filter((c("sack") == 1) | (c("qb_hit") == 1)).select("game_id", "play_id", gsis_id=c("passer_player_id")),
    *[p.select("game_id", "play_id", gsis_id=c(k)) for k in ids_def],
]).drop_nulls().unique().join(touch, on=["game_id", "play_id", "gsis_id"], how="anti")
tch = touch.group_by("gsis_id", "game_id").agg(tch=pl.len())
oth = other.group_by("gsis_id", "game_id").agg(oth=pl.len())
pr = pl.read_parquet(O / "player_play_risk.parquet", columns=["gsis_id", "game_id"])
risk = pr.group_by("gsis_id", "game_id").agg(plays=pl.len())
pg = pl.read_parquet(O / "player_games.parquet").filter((c("season") >= 2016) & c("position").is_in(GROUPS))
pg = (pg.join(risk, on=["gsis_id", "game_id"], how="left").join(tch, on=["gsis_id", "game_id"], how="left").join(oth, on=["gsis_id", "game_id"], how="left")
      .with_columns(c("plays").fill_null(0), c("tch").fill_null(0), c("oth").fill_null(0)).sort("gsis_id", "season", "week"))


def win(col, name):
    return {
        f"{name}_last": c(col).shift(1).over("gsis_id", "season").fill_null(0),
        f"{name}4": c(col).shift(1).rolling_sum(4, min_samples=1).over("gsis_id", "season").fill_null(0),
        f"{name}S": (c(col).cum_sum() - c(col)).over("gsis_id", "season"),
    }


pg = pg.with_columns(**win("plays", "cnt"), **win("tch", "tch"), **win("oth", "oth"))
d = pg.filter((c("played") == 1) & (c("season") >= 2017)).with_columns(
    gw=pl.concat_str([c("season").cast(pl.Utf8), c("week").cast(pl.Utf8), c("team")], separator="-"))
print(f"rows (played, 2017-2024): {d.height:,}; injuries {int(d['hurt'].sum()):,}")
G = np.column_stack([(d["position"] == g).to_numpy() for g in GROUPS[1:]]).astype(float)
y = d["hurt"].to_numpy().astype(float)
season = d["season"].to_numpy()


def X(cols_):
    return np.column_stack([G] + [d[k].to_numpy().astype(float)[:, None] for k in cols_])


def wf(cols_, yy, rows=None):
    L = np.zeros(len(yy))
    for s in range(2017, 2025):
        tr, te = season < s, season == s
        if tr.sum() == 0:
            tr = season == 2017
        Xa = X(cols_)
        sc = StandardScaler().fit(Xa[tr])
        m = LogisticRegression(C=1.0, max_iter=3000).fit(sc.transform(Xa[tr]), yy[tr])
        q = np.clip(m.predict_proba(sc.transform(Xa[te]))[:, 1], 1e-7, 1 - 1e-7)
        L[te] = -(yy[te] * np.log(q) + (1 - yy[te]) * np.log(1 - q))
    return L


u, inv = np.unique(d["gw"].to_numpy(), return_inverse=True)
W = RNG.poisson(1.0, size=(B, len(u))).astype(np.float32)


def gain(La, Lb, Lref, label, mask=None):
    m = np.ones(len(La), bool) if mask is None else mask
    dd, base = np.bincount(inv[m], weights=(La - Lb)[m], minlength=len(u)), np.bincount(inv[m], weights=Lref[m], minlength=len(u))
    est = dd.sum() / base.sum()
    lo, hi = np.percentile((W @ dd) / (W @ base), [5, 95])
    tag = "clear" if lo > 0 else "clear, worse" if hi < 0 else "covers 0"
    print(f"  {label:66} {100 * est:+.3f}% ({100 * lo:+.3f} to {100 * hi:+.3f})  {tag}")


COUNTS = ["cnt_last", "cnt4", "cntS"]
TCH = ["tch_last", "tch4", "tchS"]
OTH = ["oth_last", "oth4", "othS"]
L0, L1, L2 = wf(COUNTS, y), wf([*COUNTS, *TCH], y), wf([*COUNTS, *TCH, *OTH], y)
gain(L0, L1, L0, "H1: touches beside the counts (the usual way)")
gain(L1, L2, L0, "H2: tackles made and hits taken beside counts and touches")
off = d["position"].is_in(["QB", "RB", "WR", "TE", "OL"]).to_numpy()
gain(L1, L2, L0, "   H2 on defensive players' rows (tackles, sacks, hits made)", ~off)
gain(L1, L2, L0, "   H2 on offensive players' rows (a passer's sacks and hits taken)", off)

# the consistency test for the new measure (CLAUDE.md, two tests): a defender's tackles made per snap,
# per player, demeaned within position and season so position differences don't count as a trait
from pcf.validation.consistency import consistency  # noqa: E402

cd_ = (d.filter(c("position").is_in(["DL", "LB", "DB"]) & (c("plays") >= 10))
       .with_columns(tps=c("oth") / c("plays"))
       .with_columns(tps_w=c("tps") - c("tps").mean().over("position", "season")))
print("\nConsistency, defenders' tackles made per snap (player-games with 10+ snaps), within position and season:")
r_ = consistency(cd_, ["tps_w"], unit="gsis_id").row(0, named=True)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r_.items()})
