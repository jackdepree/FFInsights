# ruff: noqa: E501
"""Retro 5, group A: I192, bodies, not teams: travel and body clock beside Elo (from P13, bodies hold, and H5, where
no team-specific condition repeated).

Elo's saved walk-forward home margins (the pinned run 21082e26), 2016-2024; the 2025 vault is never read. Elo has one
league-wide home edge and no travel or rest terms. Three league-wide terms, each the away side's value less the home
side's (so a positive slope favours the home team):
- hours crossed: the gap between the game site's UTC offset and the team's home base's, at kickoff (DST-aware);
- the body-clock early game: the team's base is 2+ hours west of the site and the site's kickoff is before 2 pm local;
- short rest after travel: rest of 6 days or fewer and 1+ hour crossed.
A team's home base is the stadium of most of its home games that season (relocations follow); the site is the game's
stadium (London, Mexico City, Germany and Sao Paulo included). Slopes are fit by OLS (no intercept: the home edge is
Elo's) on earlier seasons, walk-forward from 2017. Gain: the share of Elo's squared error removed, 90% interval from
2,000 resamples of weeks; and 19 shuffled copies (the three terms shuffled together across games within a season).

Odds, written before any test (Claude, 2026-11-26, IDEAS.md I192): 30% clear beside Elo (interval above 0); 0.1-0.3%
if so. Pass rule (written now, before the run): the gain's interval is above 0 and it beats all 19 copies.
Run from pcf/:  PCF_DATA_DIR=... python projects/retro/explore/retro5_i192_travel.py > projects/retro/explore/retro5_i192_travel.txt
"""

import os
from datetime import UTC
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

c = pl.col
D = Path(os.environ["PCF_DATA_DIR"])
T = D / "tables"
S = range(2016, 2025)
rng = np.random.default_rng(192)
TZ = {
    "ATL": "America/New_York", "BAL": "America/New_York", "BOS": "America/New_York", "BUF": "America/New_York", "CAR": "America/New_York",
    "CIN": "America/New_York", "CLE": "America/New_York", "DET": "America/Detroit", "IND": "America/Indiana/Indianapolis", "JAX": "America/New_York",
    "MIA": "America/New_York", "NYC": "America/New_York", "PHI": "America/New_York", "PIT": "America/New_York", "TAM": "America/New_York",
    "WAS": "America/New_York", "CHI": "America/Chicago", "DAL": "America/Chicago", "GNB": "America/Chicago", "HOU": "America/Chicago",
    "KAN": "America/Chicago", "MIN": "America/Chicago", "NAS": "America/Chicago", "NOR": "America/Chicago", "STL": "America/Chicago",
    "DEN": "America/Denver", "PHO": "America/Phoenix", "LAX": "America/Los_Angeles", "OAK": "America/Los_Angeles", "SDG": "America/Los_Angeles",
    "SEA": "America/Los_Angeles", "SFO": "America/Los_Angeles", "VEG": "America/Los_Angeles", "LON": "Europe/London", "MEX": "America/Mexico_City",
    "GER": "Europe/Berlin", "FRA": "Europe/Berlin", "SAO": "America/Sao_Paulo",
}

gm = pl.concat([pl.read_parquet(T / "game/schedule" / f"season={s}" / "data.parquet", columns=["game_id", "season", "week", "home_team", "away_team", "location", "stadium_id", "kickoff", "home_rest", "away_rest"]) for s in S])
res = pl.concat([pl.read_parquet(T / "team_game/result" / f"season={s}" / "data.parquet", columns=["game_id", "team", "margin"]) for s in S])
elo = pl.read_parquet(D / "outputs/elo/margin/21082e26cec94ea1920081554197d201/history.parquet", columns=["game_id", "mean"])
gm = gm.with_columns(site=c("stadium_id").str.slice(0, 3))
assert set(gm["site"].unique().to_list()) <= set(TZ), set(gm["site"].unique().to_list()) - set(TZ)
base = gm.filter(c("location") == "Home").group_by("home_team", "season").agg(base=c("site").mode().first()).rename({"home_team": "team"})
g = (
    gm.join(base.rename({"team": "home_team", "base": "h_base"}), on=["home_team", "season"], how="left")
    .join(base.rename({"team": "away_team", "base": "a_base"}), on=["away_team", "season"], how="left")
    .join(res.rename({"team": "home_team"}), on=["game_id", "home_team"])
    .join(elo, on="game_id")
)


def off(zone, t):
    return t.astimezone(ZoneInfo(TZ[zone])).utcoffset().total_seconds() / 3600


rows = []
for r in g.iter_rows(named=True):
    t = r["kickoff"].astimezone(UTC)
    so = off(r["site"], t)
    local_h = t.astimezone(ZoneInfo(TZ[r["site"]])).hour
    out = {"game_id": r["game_id"]}
    for side, b, rest in (("h", r["h_base"], r["home_rest"]), ("a", r["a_base"], r["away_rest"])):
        bo = off(b, t)
        hrs = abs(so - bo)
        out[f"{side}_hrs"] = hrs
        out[f"{side}_early"] = float(so - bo >= 2 and local_h < 14)
        out[f"{side}_short"] = float(rest is not None and rest <= 6 and hrs >= 1)
    rows.append(out)
f = g.join(pl.DataFrame(rows), on="game_id").with_columns(
    x_hrs=c("a_hrs") - c("h_hrs"), x_early=c("a_early") - c("h_early"), x_short=c("a_short") - c("h_short"),
    y=c("margin") - c("mean"), blk=c("season") * 100 + c("week"),
).sort("season", "week")
X = ["x_hrs", "x_early", "x_short"]
print(f"games {f.height} ({f['season'].min()}-{f['season'].max()}); Elo's root squared error {np.sqrt((f['y'] ** 2).mean()):.2f} points")
print("how often (away side): " + ", ".join(f"{k} {float((f[k.replace('x_', 'a_')] > 0).mean()):.1%}" for k in X) + f"; away crossed 3 hours {float((f['a_hrs'] >= 3).mean()):.1%}")
xa, ya = f.select(X).to_numpy(), f["y"].to_numpy()
b_all = np.linalg.lstsq(xa, ya, rcond=None)[0]
print("in-sample slopes, points of home margin per unit (all seasons, for reading only): " + ", ".join(f"{k} {v:+.2f}" for k, v in zip(X, b_all, strict=True)))
for k in X:
    m = f[k].to_numpy() != 0
    print(f"  Elo's mean residual when {k} > 0: {ya[f[k].to_numpy() > 0].mean():+.2f} ({(f[k].to_numpy() > 0).sum()} games); < 0: {ya[f[k].to_numpy() < 0].mean() if (f[k].to_numpy() < 0).any() else float('nan'):+.2f}; 0: {ya[~m].mean():+.2f}")


def walk(frame):
    out = []
    for s in range(2017, 2025):
        tr, te = frame.filter(c("season") < s), frame.filter(c("season") == s)
        b = np.linalg.lstsq(tr.select(X).to_numpy(), tr["y"].to_numpy(), rcond=None)[0]
        out.append(te.with_columns(p=pl.Series(te.select(X).to_numpy() @ b)))
    o = pl.concat(out)
    return o["y"].to_numpy(), o["p"].to_numpy(), o["blk"].to_numpy()


def gain(y, p):
    return 1 - ((y - p) ** 2).sum() / (y ** 2).sum()


y, p, blk = walk(f)
ub = np.unique(blk)
idx = {b: np.where(blk == b)[0] for b in ub}
v = []
for _ in range(2000):
    pick = np.concatenate([idx[b] for b in rng.choice(ub, len(ub))])
    v.append(gain(y[pick], p[pick]))
est, lo, hi = gain(y, p), *np.percentile(v, [5, 95])
copies = []
for i in range(19):
    perm = pl.concat([t.with_columns(pl.DataFrame(t.select(X).to_numpy()[np.random.default_rng(1000 + i).permutation(t.height)], schema=X, orient="row")) for (_,), t in f.group_by("season", maintain_order=True)]).sort("season", "week")
    yy, pp, _ = walk(perm)
    copies.append(gain(yy, pp))
print(f"\n== the three terms beside Elo, walk-forward 2017-2024: {100 * est:+.3f}% of Elo's squared error ({100 * lo:+.3f}% to {100 * hi:+.3f}%); the copies' largest {100 * max(copies):+.3f}%, beaten by {sum(est > x for x in copies)} of 19")
for k in X:
    one = [k]
    out = []
    for s in range(2017, 2025):
        tr, te = f.filter(c("season") < s), f.filter(c("season") == s)
        b = np.linalg.lstsq(tr.select(one).to_numpy(), tr["y"].to_numpy(), rcond=None)[0]
        out.append(te.with_columns(p=pl.Series(te.select(one).to_numpy() @ b)))
    o = pl.concat(out)
    print(f"  {k} alone: {100 * gain(o['y'].to_numpy(), o['p'].to_numpy()):+.3f}%")
print(f"\n== verdict (interval above 0 and beats all 19 copies): {'held' if lo > 0 and est > max(copies) else 'failed'}")
