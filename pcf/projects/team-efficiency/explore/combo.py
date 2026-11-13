"""team-efficiency exploration, step 7: do the two small gains add up? DML with game state (H42)
with each play counted by the H41+H44a representativeness weights (offense weights for the offense
ratings, defense weights for the defense ratings). Scored like every step; writes combo.txt.
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/combo.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402
import h42_dml as D  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"


def main() -> None:
    p = C.plays()
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    eq = {h: pl.read_parquet(CACHE / f"equal_{h}.parquet") for h in ("next3", "rest")}
    w = pl.read_parquet(CACHE / "weights_h44a.parquet").select("game_id", "play_id", "w_off", "w_def")
    p = p.join(w, on=["game_id", "play_id"])
    g = D.outcome_model(p, D.X_STATE)
    p = p.with_columns(yt0=pl.Series(p["epa"].to_numpy() - g))
    wpband = pl.when(c("wp") < 0.1).then(0).when(c("wp") < 0.25).then(1).when(c("wp") < 0.4).then(2).when(c("wp") < 0.6).then(3).when(c("wp") < 0.75).then(4).when(c("wp") < 0.9).then(5).otherwise(6)
    bins = (wpband * 2 + (c("qtr") > 2).cast(pl.Int32)).cast(pl.Int32)
    rats = {}
    for side, wc in (("off", "w_off"), ("def", "w_def")):
        q = p.with_columns(yt=c("yt0") * c(wc))  # weighted sum per play: n stays the play count
        cl = D.cells(q, bins)
        best, bv = None, np.inf
        for prm in C.GRID:
            r = D.walk_dml(cl, prm, 14)
            v = C.mse(C.fit_score(C.predict_frame(r, ufs["next3"]), ["own", "opp", "home"]).filter(c("side") == side), C.TUNE)
            if v < bv:
                best, bv, br = prm, v, r
        rats[side] = br
        print(side, best, flush=True)
    r = C.combine(rats["off"], rats["def"])
    r.write_parquet(CACHE / "ratings_combo.parquet")
    out = C.score_ratings(r, ufs)
    lines = ["DML with game state + H41+H44a weights, against all plays equal:"]
    for h in ("next3", "rest"):
        lines.append(f"  {h:5s} 2016-2024 {C.fmt(C.skill(out[h], eq[h]))} | off {C.fmt(C.skill(out[h], eq[h], side='off'))} def {C.fmt(C.skill(out[h], eq[h], side='def'))} | 2020-2024 {C.fmt(C.skill(out[h], eq[h], seasons=list(range(2020, 2025))))}")
    print("\n".join(lines))
    (HERE / "combo.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
