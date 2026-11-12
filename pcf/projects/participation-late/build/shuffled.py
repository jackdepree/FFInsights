"""The no-noise check for the late edition: the same model with FTN's counts shuffled across plays
within each season (signal-free FTN). It should score like the morning-after map; the real FTN
should beat it. Writes shuffled.txt here.

    python projects/participation-late/build/shuffled.py
"""

# ruff: noqa: E501
import json
from pathlib import Path

import numpy as np
import polars as pl

from pcf.experts.participation_late import ftn, reconstruct
from pcf.experts.participation_live import chain, grid, model, score

c = pl.col
HERE = Path(__file__).parent
base = json.loads((HERE / "backtest.json").read_text(encoding="utf-8"))

feats = reconstruct.ftn_features(range(ftn.FIRST_SEASON, 2025))
rng = np.random.default_rng(0)
parts = []
for s in feats["game_id"].str.slice(0, 4).unique().sort().to_list():
    f = feats.filter(c("game_id").str.starts_with(s))
    perm = rng.permutation(f.height)
    parts.append(f.select("game_id", "play_id").hstack(f.select(ftn.COLUMNS[:-1])[perm]))
shuf = pl.concat(parts)

lines = ["Shuffled FTN (counts permuted across plays within each season), log loss on open spots:", "season side      live    late(real FTN)  late(shuffled FTN)"]
for s in reconstruct.TEST_SEASONS:
    train = reconstruct.train_frame(s, shuf)
    test = reconstruct.load(s, shuf)
    m = model.fit(train, "sequence", seed=s, extra=ftn.COLUMNS)
    inf = chain.infer(test, m)
    test = test.join(inf.select(*grid.CELL_KEYS, c("p").alias("p_shuf")), on=grid.CELL_KEYS, how="left")
    r = score.per_play(test, "shuf")
    b = base["seasons"][str(s)]
    for side in ("offense", "defense"):
        k = f"{side}_log_loss"
        lines.append(f"{s}   {side:8s} {b['live'][k]:.4f}  {b['late'][k]:.4f}          {r[k]:.4f}")
text = "\n".join(lines)
(HERE / "shuffled.txt").write_text(text, encoding="utf-8")
print(text)
