"""The CEO, 2026-11-24: "Yes, where calibrated". The players' rest-of-season champion with its
spread fit inside the model (the latest 20% of each training window, per position x window),
judged on its own harness run (2016-2024): every cell, and the published chances only."""
import sys
from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.experts.td_expert import model as M
from pcf.experts.td_expert.run import saved_dir
from pcf.validation import backtest, calibration

c = pl.col
run = sys.argv[1]
hist = pl.read_parquet(get_config().zone("outputs") / "td-expert" / "skill_rest_volume+qb_rz" / run / "history.parquet")
feats, outs = backtest.load_features(saved_dir("skill", "rest", "spread"))
keys = ["gsis_id", "game_id"]
p = (hist.join(outs.select(*keys, "y"), on=keys, how="inner")
     .join(feats.select(*keys, "position", "games_left").unique(keys), on=keys, how="left"))
p = p.with_columns(window=pl.Series(M.window_of(p["games_left"].to_numpy())))
out = [__doc__.strip().split("\n")[0], f"run {run}; {p.height:,} windows", ""]


def judge(q: pl.DataFrame, col: str, k: int) -> str:
    q = q.filter(c(col).is_not_null())
    if q.is_empty():
        return "-"
    rep = calibration.probability_report(q.select(mean=col, y=(c("y") >= k).cast(pl.Float64)))
    return f"{rep['error']:.2f} points, slope {rep['slope']:.2f} ({'passes' if rep['passed'] else 'fails'}; {q.height:,})"


rep = calibration.count_report(p)
out.append(f"every row under its spread: 1+ error {rep['one']['error']:.2f}, slope {rep['one']['slope']:.2f}; "
           f"2+ error {rep['two']['error']:.2f}, slope {rep['two']['slope']:.2f}")
out.append(f"published chances: 1+ {judge(p, 'p_one', 1)}; 2+ {judge(p, 'p_two', 2)}")
out.append(f"share of windows with a published 1+: {p['p_one'].is_not_null().mean():.1%}; 2+: {p['p_two'].is_not_null().mean():.1%}")
out += ["", "every cell, the chance under the model's own spread (1+; 2+):"]
for pos in ("QB", "RB", "WR", "TE"):
    for w in ("1-5", "6-11", "12+"):
        q = p.filter((c("position") == pos) & (c("window") == w))
        from pcf.validation.scores import negbin_at_least
        mu, a, pw = q["mean"].to_numpy(), q["alpha"].to_numpy(), q["power"].to_numpy()
        q = q.with_columns(c1=pl.Series(negbin_at_least(mu, a, 1, pw)), c2=pl.Series(negbin_at_least(mu, a, 2, pw)))
        shown = M.PUBLISHED.get((pos, w), ())
        out.append(f"  {pos} {w:<5} published {list(shown) or 'none'}: 1+ {judge(q, 'c1', 1)}; 2+ {judge(q, 'c2', 2)}")
Path(__file__).with_suffix(".txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
