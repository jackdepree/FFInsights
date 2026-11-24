"""I118 for players, the harness's way (a preview on the trees champion's saved features): each
row's opener only where it was known at its own moment (2023 on), 0 and a flag elsewhere, so the
line's weight is learned on opener rows only; the team's total and expected margin beside the
trees' inputs. Players next game, scored 2023-2024 on games with an opener."""
from pathlib import Path

import polars as pl

from pcf.baselines.crude.inputs import espn_openers
from pcf.experts.td_expert import features as F
from pcf.experts.td_expert import model as M
from pcf.experts.td_expert.checks import gain, gain_line, removed_line, walk_saved
from pcf.experts.td_expert.run import saved_dir
from pcf.validation import backtest

c = pl.col
op = espn_openers()
feats, outs = backtest.load_features(saved_dir("skill", "next", ""))
first = int(feats["step_season"].min())
g = feats.select("game_id", "team").unique().with_columns(
    home=c("game_id").str.split("_").list.get(3) == c("team"))
ln = g.join(op, on="game_id", how="inner").select(
    "game_id", "team", line_total=c("open_total") - F.LINE_CENTER,
    line_margin=pl.when("home").then(-c("open_home_spread")).otherwise(c("open_home_spread")))
f = feats.join(ln, on=["game_id", "team"], how="left").with_columns(
    has_line=c("line_total").is_not_null().cast(pl.Float64),
    line_total=c("line_total").fill_null(0.0), line_margin=c("line_margin").fill_null(0.0))
if "skill_next_volume_trees+line" not in M.VARIANTS:
    M._make("skill", "next", "volume_trees+line", columns=[*F.VOLUME, *F.LINE], method="trees")
var, base = M.VARIANTS["skill_next_volume_trees+line"](), M.VARIANTS["skill_next_volume_trees"]()
keys = base.keys()
has = f.filter(c("has_line") == 1).select(keys)
pb = walk_saved(base, feats, outs, [2023, 2024], first).join(has, on=keys, how="semi")
pl_ = walk_saved(var, f, outs, [2023, 2024], first).join(has, on=keys, how="semi")
out = [__doc__.strip().split("\n")[0], ""]
out += [removed_line("volume_trees", pb, "position"), removed_line("volume_trees+line", pl_, "position")]
out.append(gain_line("the opener beside the trees", gain(pl_, pb, keys)))
for pos in ("QB", "RB", "WR", "TE"):
    s = c("position") == pos
    out.append(gain_line(f"  {pos}", gain(pl_.filter(s), pb.filter(s), keys)))
for yr in (2023, 2024):
    s = c("season") == yr
    out.append(gain_line(f"  {yr}", gain(pl_.filter(s), pb.filter(s), keys)))
Path(__file__).with_suffix(".txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
