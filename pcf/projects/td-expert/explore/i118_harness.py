"""I118 in the harness (run e26a1d97, `team_next_volume+line`, 2023-2024, all 10 checks, 20 of 20
shuffles): the line against B on that run's saved features, all rows and the opener rows, by season."""
from pathlib import Path

import polars as pl

from pcf.experts.td_expert import model as M
from pcf.experts.td_expert.checks import calibration_line, gain, gain_line, removed_line, walk_saved
from pcf.experts.td_expert.run import saved_dir
from pcf.validation import backtest

c = pl.col
feats, outs = backtest.load_features(saved_dir("team", "next", "line"))
first = int(feats["step_season"].min())
keys = ["game_id", "team"]
p = {r: walk_saved(M.VARIANTS[f"team_next_{r}"](), feats, outs, [2023, 2024], first)
     for r in ("rate", "volume", "volume+line")}
has = feats.filter(c("has_line") == 1).select(keys)
lines = [__doc__.strip().split("\n")[0], ""]
for label, rows in (("every row", None), ("rows with an opener", has)):
    q = {k: (v if rows is None else v.join(rows, on=keys, how="semi")) for k, v in p.items()}
    lines.append(f"== {label}")
    for k, v in q.items():
        lines.append(removed_line(k, v))
    lines.append(calibration_line("volume+line", q["volume+line"]))
    lines.append(gain_line("the opener beside B (I118)", gain(q["volume+line"], q["volume"], keys)))
    lines.append(gain_line("B+line against rung 0", gain(q["volume+line"], q["rate"], keys)))
    for s in (2023, 2024):
        sel = c("season") == s
        lines.append(gain_line(f"  {s}", gain(q["volume+line"].filter(sel), q["volume"].filter(sel), keys)))
    lines.append("")
Path(__file__).with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
