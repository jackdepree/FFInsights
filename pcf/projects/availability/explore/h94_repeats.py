"""Availability exploration: H94, some injuries repeat and others don't (pre-registered in
EXPLORATION.md).

Episodes from the injury report, 2009-2024: a body part starts an episode when it appears on a
player's report (game status or practice line) after 4+ weeks without it; the episode ends at its
last listing before a 4-week gap. Weeks run on one calendar across seasons (18 per season).

For each of the 10 most common parts:
- R_same: new episodes of the same part in the 17 weeks after the episode ends, over what the
  base rate of that part says (rostered player-weeks of his position with no listing of it in
  the past 4 weeks);
- R_other: the same for a new episode of any other part, measuring general proneness;
- a part repeats specifically if R_same / R_other's 90% interval (resampling players) is above 1.
Held if at least 2 parts repeat specifically and at least 2 don't; failed if all or none.

Run from pcf/: PYTHONIOENCODING=utf-8 <venv python> <this file>
"""

# ruff: noqa: E501
from __future__ import annotations

from collections import defaultdict

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
CFG = get_config()
T = CFG.zone("tables")
RNG = np.random.default_rng(CFG.seed)
SEASONS = list(range(2009, 2025))
GAP, WIN = 4, 17
B = 1000


def part(table, name, cols):
    out = []
    for s in SEASONS:
        f = T / table / name / f"season={s}" / "data.parquet"
        if f.exists():
            out.append(pl.read_parquet(f, columns=cols))
    return pl.concat(out, how="diagonal_relaxed")


ro = part("player_game", "roster", ["gsis_id", "game_id", "season", "week", "position"])
ro = ro.filter(c("position").is_in(["QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB"])).with_columns(t=(c("season") - 2009) * 18 + c("week"))
inj = part("player_game", "injury", ["gsis_id", "game_id", "report_primary_injury", "practice_primary_injury"])
inj = inj.join(ro.select("gsis_id", "game_id", "t", "position"), on=["gsis_id", "game_id"])
inj = inj.with_columns(part_=pl.coalesce(c("report_primary_injury"), c("practice_primary_injury")))
NORM = {"Rib": "Ribs", "Quadricep": "Quadriceps", "Hamstrings": "Hamstring", "Head": "Concussion"}
inj = inj.filter(c("part_").is_not_null()).with_columns(part_=c("part_").str.strip_chars().replace(NORM))
top = inj["part_"].value_counts().sort("count", descending=True)
NOT_INJ = ("not injury", "illness", "rest", "personal", "coach", "suspen")
TOP = [p for p in top["part_"].to_list() if not any(k in p.lower() for k in NOT_INJ)][:10]
print("excluded as not injuries:", [p for p in top["part_"].to_list()[:30] if any(k in p.lower() for k in NOT_INJ)])
print("listings 2009-2024:", inj.height, "| the 10 parts:", TOP)
TMAX = int(ro["t"].max())

# episodes per player and part
lst = inj.select("gsis_id", "position", "t", "part_").unique().sort("gsis_id", "part_", "t")
eps = []  # (player, position, part, start, end)
for (pid, prt), g in lst.group_by(["gsis_id", "part_"]):
    ts = g["t"].to_numpy()
    pos = g["position"][0]
    s0 = e0 = ts[0]
    for x in ts[1:]:
        if x - e0 > GAP:
            eps.append((pid, pos, prt, s0, e0))
            s0 = x
        e0 = x
    eps.append((pid, pos, prt, s0, e0))
E = pl.DataFrame(eps, schema=["gsis_id", "position", "part_", "start", "end"], orient="row")
print("episodes:", E.height)
starts = defaultdict(list)  # player -> list of (start, part)
for pid, _, prt, s0, _ in E.iter_rows():
    starts[pid].append((s0, prt))
for k in starts:
    starts[k].sort()

# base rates by position: from rostered player-weeks, the chance a new episode of part P starts in the next 17 weeks
# (no listing of P in the past 4 weeks), and of any part other than P
listed = defaultdict(set)
for pid, t_, prt in lst.select("gsis_id", "t", "part_").iter_rows():
    listed[(pid, prt)].add(t_)
pw = ro.select("gsis_id", "position", "t").unique()
pw = pw.filter(c("t") <= TMAX - WIN).sample(n=min(200_000, pw.height), seed=CFG.seed)
base = {}
for P in TOP:
    num = defaultdict(float)
    den = defaultdict(float)
    numo = defaultdict(float)
    for pid, pos, t_ in pw.iter_rows():
        if any((t_ - k) in listed.get((pid, P), ()) for k in range(0, GAP + 1)):
            continue
        den[pos] += 1
        ss = starts.get(pid, [])
        num[pos] += any(t_ < s0 <= t_ + WIN and prt == P for s0, prt in ss)
        numo[pos] += any(t_ < s0 <= t_ + WIN and prt != P for s0, prt in ss)
    base[P] = {pos: (num[pos] / den[pos], numo[pos] / den[pos]) for pos in den}

rows = []
for P in TOP:
    e = E.filter((c("part_") == P) & (c("end") <= TMAX - WIN))
    rec = []
    for pid, pos, _, s0, e0 in e.iter_rows():
        ss = starts.get(pid, [])
        same = any(e0 < x <= e0 + WIN and prt == P for x, prt in ss)
        other = any(e0 < x <= e0 + WIN and prt != P for x, prt in ss)
        bs, bo = base[P].get(pos, (np.nan, np.nan))
        rec.append((pid, same, other, bs, bo))
    r = pl.DataFrame(rec, schema=["gsis_id", "same", "other", "bs", "bo"], orient="row").drop_nulls()
    pids = r["gsis_id"].unique().to_list()
    pi = {p: i for i, p in enumerate(pids)}
    idx = np.array([pi[p] for p in r["gsis_id"].to_list()])
    sm, ot, bsv, bov = (r[k].to_numpy().astype(float) for k in ("same", "other", "bs", "bo"))
    Rs, Ro = sm.sum() / bsv.sum(), ot.sum() / bov.sum()
    W = RNG.poisson(1.0, size=(B, len(pids))).astype(float)[:, idx]
    rs_b = (W @ sm) / (W @ bsv)
    ro_b = (W @ ot) / (W @ bov)
    ratio_b = rs_b / ro_b
    lo, hi = np.percentile(ratio_b, [5, 95])
    rows.append((P, len(r), Rs, Ro, Rs / Ro, lo, hi))

print(f"\n{'part':12} {'episodes':>8} {'R_same':>7} {'R_other':>8} {'same/other':>10}  90% interval     repeats specifically?")
n_yes = n_no = 0
for P, n, Rs, Ro, rat, lo, hi in rows:
    yes = lo > 1
    no = lo <= 1 <= hi
    n_yes += yes
    n_no += no
    print(f"{P:12} {n:8d} {Rs:7.2f} {Ro:8.2f} {rat:10.2f}  ({lo:4.2f} to {hi:4.2f})   {'yes' if yes else 'no (covers 1)' if no else 'no (below 1)'}")
verdict = "HELD" if (n_yes >= 2 and n_no >= 2) else "FAILED" if (n_yes == len(rows) or n_yes == 0) else "UNCLEAR"
print(f"-> parts repeating specifically: {n_yes}; covering 1: {n_no}; H94: {verdict}")
