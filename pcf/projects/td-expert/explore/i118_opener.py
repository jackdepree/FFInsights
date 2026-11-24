"""I118 (the CEO, 2026-11-24: "the open total market data can be used for the touchdown expert"):
the opening line beside B's inputs for team touchdowns next game, and beside the trees champion's
inputs for players', walked on the saved features (2013 on), scored 2023-2024 on the games with
an ESPN opener only (decision 0042 call 13's method: earlier seasons train on the kickoff line,
all known long before any later fit; the forecast rows use the opener). The kickoff line is the
ceiling. Odds written before (IDEAS.md I118): 75% it adds 3%+ of the squared error, interval clear.

The vault (2025) is spent for td-expert; the live 2026 ledger is this input's only clean test.
"""
from pathlib import Path

import polars as pl

from pcf.baselines.crude.inputs import espn_openers, lines, opener_rows
from pcf.experts.td_expert import features as F
from pcf.experts.td_expert import model as M
from pcf.experts.td_expert.checks import _shuffled, calibration_line, gain, gain_line, removed_line, walk_saved
from pcf.experts.td_expert.run import saved_dir
from pcf.validation import backtest

c = pl.col
OUT = Path(__file__).with_suffix(".txt")
SEASONS = [2023, 2024]
LINE = ["ln_total", "ln_margin", "ln_implied"]
SHUFFLES = 20

op = espn_openers()
out = [__doc__.strip().split("\n")[0], f"tested {SEASONS}; {op.height} games with an opener in our data", ""]


def with_lines(feats: pl.DataFrame, kind: str) -> pl.DataFrame:
    rows = feats.with_columns(season=c("game_id").str.slice(0, 4).cast(pl.Int32))
    keys = [k for k in ("gsis_id", "game_id", "team") if k in feats.columns]
    ln = lines(rows.select(*keys, "season").unique(keys), kind=kind, openers=op)
    jk = [k for k in ("gsis_id", "game_id", "team") if k in ln.columns]
    return feats.join(ln.unique(jk), on=jk, how="left").with_columns(
        [c(x).fill_null(c(x).mean()) for x in LINE])


for family, base_rung, cols, extra in (
    ("team", "volume", F.TEAM_VOLUME, {}),
    ("skill", "volume_trees", F.VOLUME, {"method": "trees"}),
):
    feats, outs = backtest.load_features(saved_dir(family, "next", ""))
    first = int(feats["step_season"].min())
    base = M.VARIANTS[f"{family}_next_{base_rung}"]()
    rate = M.VARIANTS[f"{family}_next_rate"]()
    name = f"{base_rung}+open"
    if f"{family}_next_{name}" not in M.VARIANTS:
        M._make(family, "next", name, columns=[*cols, *LINE], **extra)
    var = M.VARIANTS[f"{family}_next_{name}"]()
    keys = base.keys()
    f_open, f_kick = with_lines(feats, "open"), with_lines(feats, "kickoff")
    honest = opener_rows(feats.select(*keys, *(["team"] if "team" not in keys else []))).select(keys)

    def scored(p):
        return p.join(honest, on=keys, how="semi")

    p_base = scored(walk_saved(base, feats, outs, SEASONS, first))
    p_rate = scored(walk_saved(rate, feats, outs, SEASONS, first))
    p_open = scored(walk_saved(var, f_open, outs, SEASONS, first))
    p_kick = scored(walk_saved(var, f_kick, outs, SEASONS, first))
    by = "position" if family == "skill" else None
    out += [f"== {family}, next game ({p_base.height:,} rows with an opener)"]
    for n, p in (("rate", p_rate), (base_rung, p_base), (name, p_open), (f"{name} (kickoff: ceiling)", p_kick)):
        out.append(removed_line(n, p, by))
    for n, p in ((base_rung, p_base), (name, p_open)):
        out.append(calibration_line(n, p))
    out.append(gain_line(f"the opener beside {base_rung} (I118)", gain(p_open, p_base, keys)))
    out.append(gain_line("the kickoff line beside it (ceiling)", gain(p_kick, p_base, keys)))
    out.append(gain_line(f"{name} against rung 0", gain(p_open, p_rate, keys)))
    if by:
        for pos in ("QB", "RB", "WR", "TE"):
            s = c("position") == pos
            out.append(gain_line(f"  the opener, {pos}", gain(p_open.filter(s), p_base.filter(s), keys)))
    for s in SEASONS:
        sel = c("season") == s
        out.append(gain_line(f"  the opener, {s}", gain(p_open.filter(sel), p_base.filter(sel), keys)))
    if family == "team":
        real = p_open["loss"].mean()
        nulls = [scored(walk_saved(var, f_open, outs, SEASONS, first, _shuffled(s)))["loss"].mean()
                 for s in range(SHUFFLES)]
        out.append(f"  shuffled copies of {name}: log loss {real:.4f} against {min(nulls):.4f} to "
                   f"{max(nulls):.4f}; beats {sum(real < x for x in nulls)} of {SHUFFLES}")
    out.append("")
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[-14:]), flush=True)
