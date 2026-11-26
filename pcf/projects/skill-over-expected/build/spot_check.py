# ruff: noqa: E501
"""The CEO's spot-check (2026-11-26): inside linebackers' movers (I171, RESULTS R6), after
off-ball outside linebackers count as inside linebackers (decision 0051 call 31). Odds are in
SPOT_CHECK.md, written before this ran.

Run from pcf/:  python projects/skill-over-expected/build/spot_check.py > projects/skill-over-expected/build/spot_check.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.experts.skill_over_expected import data as D
from pcf.experts.skill_over_expected import evaluate as E
from pcf.experts.skill_over_expected import run as R
from pcf.experts.skill_over_expected import traits as T

c = pl.col
SEED = get_config().seed


def err(q: pl.DataFrame, f: str) -> pl.Expr:
    return (q["w"] * (q["y"] - q[f]) ** 2).sum()


def one(trait: str, d: dict, before: dict) -> None:
    t = T.BY_NAME[trait]
    rows = T.season_rows(d["games"], d["teams"], t)
    ilb = rows.filter(c("group") == "ILB")
    pr = T.pairs(ilb, d["games"], rows)
    q = E.scored(T.rungs(pr))
    mv = q.filter(c("moved"))
    was = d["teams"].filter(c("roster_position") == "OLB").select(gsis_id="pid", season="season")
    mv = mv.with_columns(from_olb=pl.struct("gsis_id", "season").is_in(was.select(pl.struct("gsis_id", "season")).to_series().implode()))
    print(f"\n== {trait}, inside linebackers: {q.height} scored pairs, {mv.height} movers ({mv['gsis_id'].n_unique()} players; {int(mv['from_olb'].sum())} of them OLB-labelled off-ball in the input season); before the reclassification {before[trait]}")
    g0 = E.gain(mv, "split0", "m1", SEED)
    g1 = E.gain(mv, "split", "m1", SEED)
    print(f"  the movers' gain, as pre-registered (his M1 and his new team's part, against M1): {E.fmt(g0)}; the shipped rung 3 (the team change): {E.fmt(g1)}")
    print(f"  all rows (movers and stayers): split0 against M1 {E.fmt(E.gain(q, 'split0', 'm1', SEED))}")
    print(f"  is it only a harder pull? the second pull (one slope on M1, no team) against M1, movers: {E.fmt(E.gain(mv, 'pull', 'm1', SEED))}; the split against the second pull, movers: {E.fmt(E.gain(mv, 'split0', 'pull', SEED))}")
    w, y, m1, s_ = (mv[k].to_numpy() for k in ("w", "y", "m1", "season"))
    mp = np.full(mv.height, np.nan)  # a movers-only pull: one slope on M1 fit on earlier movers
    for t in np.unique(s_):
        tr = s_ < t
        if tr.sum() >= 15:
            mp[s_ == t] = m1[s_ == t] * np.sum(w[tr] * m1[tr] * y[tr]) / np.sum(w[tr] * m1[tr] ** 2)
    mvp = mv.with_columns(mpull=pl.Series(mp).fill_nan(None)).drop_nulls("mpull")
    print(f"  a movers' own pull (fit on earlier movers only), {mvp.height} movers: against M1 {E.fmt(E.gain(mvp, 'mpull', 'm1', SEED))}; the split against it {E.fmt(E.gain(mvp, 'split0', 'mpull', SEED))}")
    keep = mv.select("gsis_id", "season")
    cp = []
    for i in range(20):
        qi = E.scored(T.rungs(pr, ("team_new",), SEED + 500 + i)).filter(c("moved")).join(keep, on=["gsis_id", "season"], how="semi")
        cp.append(E.gain(qi, "split0", "m1", draws=10).share)
    print(f"  20 copies with the new team's part moved to another inside linebacker that season: best {100 * max(cp):+.1f}%, median {100 * float(np.median(cp)):+.1f}%; beats all 20: {g0.share > max(cp)}")
    tot = float(err(mv, "m1") - err(mv, "split0"))
    print("  by target season (movers, the gain, its share of the total gain):")
    for s in sorted(mv["season"].unique().to_list()):
        m = mv.filter(c("season") == s)
        gs = float(err(m, "m1") - err(m, "split0"))
        loo = E.gain(mv.filter(c("season") != s), "split0", "m1", SEED, draws=500)
        print(f"    {s + 1}: {m.height} movers, {100 * (1 - float(err(m, 'split0')) / float(err(m, 'm1'))):+.1f}%, {100 * gs / tot:.0f}% of the total; without it {E.fmt(loo)}")
    print("  dropping each new team in turn (movers to it):")
    res = []
    for tm in sorted(mv["team_next"].unique().to_list()):
        m = mv.filter(c("team_next") != tm)
        res.append((E.gain(m, "split0", "m1", SEED, draws=500), tm, mv.filter(c("team_next") == tm).height))
    res.sort(key=lambda r: r[0].share)
    for g, tm, n in res[:3]:
        print(f"    without {tm} ({n} movers): {E.fmt(g)}")
    print(f"    the lowest lower bound over all {len(res)} teams: {100 * min(r[0].lo for r in res):+.1f}%; clear without every team: {all(r[0].clear() for r in res)}")
    mv = mv.with_columns(change=c("team_new") - c("team_old"), own=c("y") - c("m1"))
    w = mv["w"].to_numpy()
    a, b = mv["change"].to_numpy(), mv["own"].to_numpy()
    r = float(np.sum(w * (a - np.average(a, weights=w)) * (b - np.average(b, weights=w))) / np.sqrt(np.sum(w * (a - np.average(a, weights=w)) ** 2) * np.sum(w * (b - np.average(b, weights=w)) ** 2)))
    print(f"  role or scheme: the team change (new team's part less the old) against his miss from M1, weighted r {r:.2f}")
    med = float(mv["change"].abs().median())
    for label, m in (("big team change (above the median)", mv.filter(c("change").abs() > med)), ("small team change", mv.filter(c("change").abs() <= med))):
        print(f"    {label}: {m.height} movers, {E.fmt(E.gain(m, 'split0', 'm1', SEED, draws=1000))}")
    for label, m in (("OLB-labelled off-ball movers", mv.filter(c("from_olb"))), ("ILB-labelled movers", mv.filter(~c("from_olb")))):
        if m.height >= 15:
            print(f"    {label}: {m.height}, {E.fmt(E.gain(m, 'split0', 'm1', SEED, draws=1000))}")
    nm = R.names()
    top = mv.with_columns(helped=c("w") * ((c("y") - c("m1")) ** 2 - (c("y") - c("split0")) ** 2)).join(nm, on="gsis_id", how="left").sort("helped", descending=True)
    print("  the movers it helps most (season in, team, new team, his centred rate in and out, M1, with the new team):")
    for row in top.head(6).iter_rows(named=True):
        print(f"    {row['name']} {row['season']} {row['team']}->{row['team_next']}: {row['x']:+.3f} -> {row['y']:+.3f}; M1 {row['m1']:+.3f}, split0 {row['split0']:+.3f}")


def main() -> None:
    d = D.load()
    d["teams"] = T.regroup(d["teams"], R.roles())
    before = {"press_rate": "66 movers, +20.7% (+10.1 to +29.8)", "rush_share": "66 movers, +27.9% (+17.4 to +37.9)"}
    for trait in ("press_rate", "rush_share"):
        one(trait, d, before)


if __name__ == "__main__":
    main()


def others() -> None:
    """The same question for the other movers results I171 reported (RESULTS R6)."""
    d = D.load()
    d["teams"] = T.regroup(d["teams"], R.roles())
    print("\n== The other movers results: the first split against M1 and against the second pull (movers only)")
    for trait, grp in (("catch_rate", "WR"), ("depth_against", "DB"), ("ol_press_rate", "OL"), ("ol_sack_rate", "OL")):
        rows = T.season_rows(d["games"], d["teams"], T.BY_NAME[trait])
        q = E.scored(T.rungs(T.pairs(rows.filter(c("group") == grp), d["games"], rows)))
        mv = q.filter(c("moved"))
        print(f"  {trait} {grp} ({mv.height} movers): split0 against M1 {E.fmt(E.gain(mv, 'split0', 'm1', SEED))}; the second pull against M1 {E.fmt(E.gain(mv, 'pull', 'm1', SEED))}; split0 against the second pull {E.fmt(E.gain(mv, 'split0', 'pull', SEED))}")


if __name__ == "__main__":
    others()


def olb() -> None:
    """After the reclassification OLB pressures' shipped split clears (the rerun's ladder): is it,
    too, only a harder pull? The split against the second pull, with 20 copies of the team change."""
    d = D.load()
    d["teams"] = T.regroup(d["teams"], R.roles())
    print("
== Outside linebackers (edge players after the reclassification): the shipped split against the second pull")
    for trait in ("press_rate", "rush_share"):
        rows = T.season_rows(d["games"], d["teams"], T.BY_NAME[trait])
        pr = T.pairs(rows.filter(c("group") == "OLB"), d["games"], rows)
        q = E.scored(T.rungs(pr))
        mv = q.filter(c("moved"))
        cp = [E.gain(E.scored(T.rungs(pr, ("team_change",), SEED + 700 + i)), "split", "pull", draws=10).share for i in range(20)]
        print(f"  {trait} OLB ({q.height} pairs, {mv.height} movers): the second pull against M1 {E.fmt(E.gain(q, 'pull', 'm1', SEED))}; split against M1 {E.fmt(E.gain(q, 'split', 'm1', SEED))}; split against the second pull {E.fmt(E.gain(q, 'split', 'pull', SEED))}, copies' best {100 * max(cp):+.1f}%; movers: split against the second pull {E.fmt(E.gain(mv, 'split', 'pull', SEED))}")


if __name__ == "__main__":
    olb()
