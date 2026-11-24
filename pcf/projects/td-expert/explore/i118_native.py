"""I118, the harness's way (a preview before the table part is built): each row's line is only
what was known at its own moment, so training rows carry an opener only from 2023 (ESPN's
history); other rows get the mean and a flag, so the line's weight is learned on opener rows only.
Teams next game, scored 2023-2024 on the games with an opener. Compare i118_opener.txt, where the
earlier seasons trained on kickoff lines.
"""
from pathlib import Path

import polars as pl

from pcf.baselines.crude.inputs import espn_openers
from pcf.experts.td_expert import features as F
from pcf.experts.td_expert import model as M
from pcf.experts.td_expert.checks import _shuffled, gain, gain_line, removed_line, walk_saved
from pcf.experts.td_expert.run import saved_dir
from pcf.validation import backtest

c = pl.col
OUT = Path(__file__).with_suffix(".txt")
SEASONS = [2023, 2024]
LINE = ["ln_total", "ln_margin", "has_line"]

op = espn_openers()
feats, outs = backtest.load_features(saved_dir("team", "next", ""))
first = int(feats["step_season"].min())
home = feats.select("game_id", "team", "home")
ln = (home.join(op, on="game_id", how="inner")
      .select("game_id", "team", ln_total="open_total",
              ln_margin=pl.when(c("home").cast(pl.Float64) == 1).then(-c("open_home_spread")).otherwise(c("open_home_spread"))))
f = feats.join(ln.unique(["game_id", "team"]), on=["game_id", "team"], how="left").with_columns(
    has_line=c("ln_total").is_not_null().cast(pl.Float64),
    ln_total=c("ln_total").fill_null(44.0), ln_margin=c("ln_margin").fill_null(0.0))
if "team_next_volume+line" not in M.VARIANTS:
    M._make("team", "next", "volume+line", columns=[*F.TEAM_VOLUME, *LINE])
var, base = M.VARIANTS["team_next_volume+line"](), M.VARIANTS["team_next_volume"]()
keys = base.keys()
honest = f.filter(c("has_line") == 1).select(keys)


def scored(p):
    return p.join(honest, on=keys, how="semi")


p_base = scored(walk_saved(base, feats, outs, SEASONS, first))
p_line = scored(walk_saved(var, f, outs, SEASONS, first))
out = [__doc__.strip().split("\n")[0], ""]
out.append(removed_line("volume", p_base))
out.append(removed_line("volume+line (opener rows only)", p_line))
out.append(gain_line("the opener beside volume, harness's way", gain(p_line, p_base, keys)))
for s in SEASONS:
    sel = c("season") == s
    out.append(gain_line(f"  {s}", gain(p_line.filter(sel), p_base.filter(sel), keys)))
real = p_line["loss"].mean()
nulls = [scored(walk_saved(var, f, outs, SEASONS, first, _shuffled(s)))["loss"].mean() for s in range(20)]
out.append(f"  shuffled copies: {real:.4f} against {min(nulls):.4f} to {max(nulls):.4f}; beats "
           f"{sum(real < x for x in nulls)} of 20")
OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
