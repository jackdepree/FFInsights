# ruff: noqa: E501
"""voe, checks on the first look (2026-11-19). Discovery only, 2016-2024.

1. Player or team? Season-to-season repeat of each value for players who stayed on their team
   against players who moved (the team effect can't move with him).
2. The roster-change test for offense, split: QBs only, and everyone but QBs.
3. The injury design: a placebo (players with an injury note who came back for most of the
   remaining plays), win chance 10-90% only, and the QB events listed.

Run from pcf/:  python projects/voe/explore/checks.py > projects/voe/explore/checks.txt
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import first_look as fl  # noqa: E402

c = pl.col


def movers(vals: pl.DataFrame, value: str, team_of: pl.DataFrame, label: str, n_min: int = 300):
    a = vals.filter(c("half") == "all").join(team_of, on=["gsis_id", "season"])
    j = a.join(
        a.with_columns(season=c("season") - 1), on=["gsis_id", "season"], suffix="_n"
    ).filter((c("n") >= n_min) & (c("n_n") >= n_min))
    st, mv = j.filter(c("team") == c("team_n")), j.filter(c("team") != c("team_n"))
    # the value net of his team-side's average that season (within-team rank)
    print(
        f"  {label}: stayed {fl.rr(st[value], st[f'{value}_n'])}; moved {fl.rr(mv[value], mv[f'{value}_n'])}"
    )
    for g in ["QB", "WR", "OL", "DL", "DB"]:
        s2, m2 = st.filter(c("group") == g), mv.filter(c("group") == g)
        print(
            f"      {g}: stayed {fl.rr(s2[value], s2[f'{value}_n'])}; moved {fl.rr(m2[value], m2[f'{value}_n'])}"
        )


def main():
    p = fl.plays()
    on = fl.on_field(p)
    info = fl.player_info(on)
    team_of = on.group_by("gsis_id", "season").agg(team=c("team").mode().first())
    pm = fl.rapm_all(on, info, 10000, use_prior=False)
    pmp = fl.rapm_all(on, info, 10000, use_prior=True)
    raw = (
        on.group_by("gsis_id", "season")
        .agg(group=c("group").mode().first(), raw=c("y").mean(), n=pl.len())
        .with_columns(half=pl.lit("all"))
    )

    print(
        "== 1. PLAYER OR TEAM? Season to season, players who stayed against players who moved (300+ plays both seasons) =="
    )
    movers(raw, "raw", team_of, "raw on-field average")
    movers(pm, "pm", team_of, "plus-minus")
    rec = fl.recreation(on)
    ev = fl.per_snap(rec, "exp_voe").rename({"v": "ev"})
    movers(ev, "ev", team_of, "recreation, expected VOE per snap")

    print("\n== 2. THE ROSTER-CHANGE TEST FOR OFFENSE, SPLIT ==")
    pp = p.filter(c("season").is_in(fl.SEASONS))
    tr = fl.team_rates(pp)
    for lab, keep in (("QBs only", ["QB"]), ("everyone but QBs", ["RB", "WR", "TE", "OL"])):
        o2 = on.filter(c("group").is_in(keep) | (c("side") == "defense"))
        fl.travel(
            tr,
            fl.roster_sum(o2, pmp.filter(c("half") == "all"), "pm"),
            f"plus-minus with prior, {lab}",
        )

    print("\n== 3. THE INJURY DESIGN ==")
    E = fl.injuries(p, on, pmp)
    print(f"  events {E.height}")
    qb = E.filter(c("group") == "QB").join(
        fl.part("player_game", "roster", fl.SEASONS, ["gsis_id", "full_name"]).unique("gsis_id"),
        on="gsis_id",
        how="left",
    )
    print(
        "  QB events, largest weight first (before, after, change less control, plays before/after):"
    )
    for r in (
        qb.sort("w", descending=True)
        .head(15)
        .select("full_name", "game_id", "before", "after", "did", "nb", "na")
        .iter_rows()
    ):
        print(f"    {r[0]}, {r[1]}: {r[2]:+.3f} -> {r[3]:+.3f}, {r[4]:+.3f} ({r[5]}/{r[6]})")
    # placebo: same matching, but the player came back (on most plays after)
    import re

    INJ = fl.INJ
    ev = p.filter(
        c("season").is_in(fl.SEASONS) & c("desc").str.contains("was injured during the play")
    ).select("game_id", "play_id", "season", "desc")
    recs = [
        (g, pid, s, int(m.group(2)), m.group(3).split(".")[-1].strip().lower())
        for g, pid, s, d in ev.iter_rows()
        for m in INJ.finditer(d)
    ]
    del re
    evd = pl.DataFrame(
        recs, schema=["game_id", "inj_play", "season", "jersey", "last"], orient="row"
    ).with_columns(c("last").str.replace_all(r"[^a-z\-']", ""))
    ro = fl.part(
        "player_game", "roster", fl.SEASONS, ["gsis_id", "game_id", "jersey_number", "full_name"]
    ).with_columns(
        jersey=c("jersey_number").cast(pl.Int64, strict=False),
        last=c("full_name")
        .str.split(" ")
        .list.last()
        .str.to_lowercase()
        .str.replace_all(r"[^a-z\-']", ""),
    )
    evd = evd.join(
        ro.select("gsis_id", "game_id", "jersey", "last"), on=["game_id", "jersey", "last"]
    ).unique(["game_id", "gsis_id"])
    o = on.select("game_id", "play_id", "gsis_id", "team", "side", "group", "y")
    me = evd.join(
        o, left_on=["game_id", "inj_play", "gsis_id"], right_on=["game_id", "play_id", "gsis_id"]
    )
    tg = (
        on.select("game_id", "play_id", "team", "side", "y")
        .unique(["game_id", "play_id", "side"])
        .sort("game_id", "play_id")
    )
    arr = {
        k: (g["play_id"].to_numpy(), g["y"].to_numpy())
        for k, g in tg.group_by(["game_id", "team", "side"])
    }
    mine = o.join(me.select("gsis_id", "game_id").unique(), on=["gsis_id", "game_id"])
    pp_ = {
        (k[0], k[1]): set(v["play_id"].to_list()) for k, v in mine.group_by(["gsis_id", "game_id"])
    }
    stay, left = [], []
    for g, ip, _s, _j, _l, pid, team, side, grp, _y in me.select(
        "game_id", "inj_play", "season", "jersey", "last", "gsis_id", "team", "side", "group", "y"
    ).iter_rows():
        if (g, team, side) not in arr:
            continue
        ids, ys = arr[(g, team, side)]
        k = int(np.searchsorted(ids, ip, side="right"))
        nb, na = k - 1, len(ids) - k
        if nb < 10 or na < 10:
            continue
        m_ = pp_.get((pid, g), set())
        ob = sum(1 for x in ids[: k - 1] if x in m_)
        oa = sum(1 for x in ids[k:] if x in m_)
        if ob < 0.6 * nb:
            continue
        rec_ = (
            grp,
            ys[k:].mean() - ys[: k - 1].mean(),
            1 / (1 / nb + 1 / na),
            ys[: k - 1].mean(),
            ys[k:].mean(),
            ys[max(0, k - 6) : k - 1].mean(),
        )
        if oa >= 0.6 * na:
            stay.append(rec_)
        elif oa <= 2:
            left.append(rec_)
    for lab, rows in (("came back (placebo)", stay), ("left", left)):
        a = np.array([r[1:] for r in rows], float)
        est = fl.wmean_ci(a[:, 0], a[:, 1])
        print(
            f"  {lab} (n {len(rows)}): after less before {est[0]:+.3f} (90% {est[1]:+.3f} to {est[2]:+.3f}); before {np.average(a[:, 2], weights=a[:, 1]):+.3f}, the 5 plays before the injury {np.nanmean(a[:, 4]):+.3f}, after {np.average(a[:, 3], weights=a[:, 1]):+.3f}"
        )
        for g in ["QB", "WR", "OL", "DB"]:
            b = np.array([r[1:] for r in rows if r[0] == g], float)
            if len(b) > 10:
                e2 = fl.wmean_ci(b[:, 0], b[:, 1], 500)
                print(f"      {g} (n {len(b)}): {e2[0]:+.3f} (90% {e2[1]:+.3f} to {e2[2]:+.3f})")
    # the QB's own team: whole-game view, games where the starting QB left early against his other games
    fl.log("done")


if __name__ == "__main__":
    main()
