# ruff: noqa: E501
"""voe, fifth look: checks after the result (2026-11-22), from fifth_look.py's cache.

1. The movers' repeat with each season's and each position group's mean taken out. Against replacement
   level every slot gets its own constant, so values can repeat just because a QB always rates above a
   guard; within the group that can't happen.
2. Season by season: the net's held-out play fit, and the spread of the stratified arm's team values.

Run from pcf/ after fifth_look.py:  python projects/voe/explore/fifth_check.py > projects/voe/explore/fifth_check.txt
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import fifth_look as fv  # noqa: E402
import first_look as fl  # noqa: E402
import ratings as rt  # noqa: E402
import success_look as sl  # noqa: E402

c = pl.col
RNG = np.random.default_rng(23)


def pairs_group(pv, info, team):
    q = sl.pairs({"pmdf": pv, "info": info, "team": team})
    return q.with_columns(
        c("pm") - c("pm").mean().over("season", "group"),
        c("pm_next") - c("pm_next").mean().over("season", "group"),
    )


def main() -> None:
    p = sl.plays()
    on = fl.on_field(p.with_columns(resid=c("r_epa")))
    info = fl.player_info(on)
    team = on.group_by("gsis_id", "season").agg(team=c("team").mode().first())
    keys = (on.filter(c("season").is_in(rt.PLAY_SEASONS)).select("game_id", "play_id", "season", "posteam", "defteam", "play_type")
            .unique(["game_id", "play_id"]).sort("season", "game_id", "play_id"))  # fmt: skip
    vo, vd, se, PV, test, diag = pickle.loads(
        (fl.get_config().zone("interim") / "voe_fifth_look" / "fits.pkl").read_bytes()
    )
    assert len(test) == keys.height

    print(
        "== CHECK 1: THE MOVERS' REPEAT WITH EACH SEASON'S AND EACH POSITION GROUP'S MEAN OUT (300+ plays in both) =="
    )
    P = {k: pairs_group(v, info, team) for k, v in PV.items()}
    base = P["ref"].select("gsis_id", "season", "moved", e=c("pm"), e_n=c("pm_next"))
    for k in ("ref", "ref_repl", "named", "pairs", "mlp", "mlp_w"):
        j = base.join(
            P[k].select("gsis_id", "season", s=c("pm"), s_n=c("pm_next")), on=["gsis_id", "season"]
        )
        mv = j.filter(c("moved"))
        ids = mv["gsis_id"].unique().to_list()
        gid = mv["gsis_id"].to_numpy()
        idx = {g: np.flatnonzero(gid == g) for g in ids}
        E, En, Sx, Sn = (mv[x].to_numpy() for x in ("e", "e_n", "s", "s_n"))
        bs = []
        for _ in range(1000):
            pick = np.concatenate([idx[ids[i]] for i in RNG.integers(0, len(ids), len(ids))])
            bs.append(fv.r(Sx[pick], Sn[pick]) - fv.r(E[pick], En[pick]))
        lo, hi = np.percentile(bs, [5, 95])
        st = j.filter(~c("moved"))
        print(
            f"  {fv.LABEL[k]:<72} stayed {fv.r(st['s'], st['s_n']):+.3f}; moved {fv.r(Sx, Sn):+.3f} ({mv.height}); movers less the reference {fv.r(Sx, Sn) - fv.r(E, En):+.3f} (90% {lo:+.3f} to {hi:+.3f})"
        )
    print(
        "  the same for H90's plus-minus arms is not needed: the plain plus-minus carries no position constant"
    )

    print("\n== CHECK 2: SEASON BY SEASON ==")
    seas = keys["season"].to_numpy()
    print(
        "  held-out play fit (% of squared error removed against the training mean; only the lasso and the nets)"
    )
    for T in rt.TEST:
        m = test & (seas == T)
        print(
            f"    {T}: mean squared error, reference {se['ref'][m].mean():.4f}; net {se['mlp'][m].mean():.4f}; weighted net {se['mlp_w'][m].mean():.4f}; largest net error {se['mlp'][m].max():.1f} against the reference's {se['ref'][m].max():.1f}"
        )
    V = (
        keys.select("season", "posteam", "defteam")
        .with_columns(
            *(pl.Series(f"vd_{k}", vd[k]) for k in ("ref", "strat")),
            *(pl.Series(f"vo_{k}", vo[k]) for k in ("ref", "strat")),
        )
        .filter(pl.Series(test))
    )
    print("  the spread of team values (sd across teams of a season's mean value a play)")
    for side, tcol, pre in (("offense", "posteam", "vo"), ("defense", "defteam", "vd")):
        g = (
            V.group_by("season", tcol)
            .agg(c(f"{pre}_ref").mean(), c(f"{pre}_strat").mean())
            .group_by("season")
            .agg(c(f"{pre}_ref").std(), c(f"{pre}_strat").std())
            .sort("season")
        )
        print(
            f"    {side}: "
            + "; ".join(
                f"{d['season']} reference {d[f'{pre}_ref']:.4f}, stratified {d[f'{pre}_strat']:.4f}"
                for d in g.to_dicts()
            )
        )


if __name__ == "__main__":
    main()
