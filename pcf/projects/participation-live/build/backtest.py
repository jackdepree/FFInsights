"""The participation-live backtest, 2019-2024 (2025, the vault, stays closed): every rung,
walk-forward by season, scored on the brief's tests. Writes backtest.txt and backtest.json here,
the champion's walk-forward history to outputs/, and one MLflow attempt.

    python projects/participation-live/build/backtest.py
"""

# ruff: noqa: E501
import json
import time
from pathlib import Path

import polars as pl

from pcf.experts.participation_live import reconstruct, score

HERE = Path(__file__).parent

t0 = time.time()
out = reconstruct.backtest()
lines = [f"participation-live backtest 2019-2024, run {out['run_id']}, {time.time() - t0:.0f} s",
         f"history: {out['history_path']}", f"point-in-time gap (0 = none): {out['point_in_time_gap']}", ""]  # fmt: skip
pooled = pl.DataFrame([{"rung": k, **v} for k, v in out["pooled"].items()], infer_schema_length=None)
with pl.Config(tbl_cols=40, tbl_rows=40, float_precision=4, tbl_width_chars=400):
    lines.append("Pooled 2019-2024 (open cells: not named, not on every snap):")
    lines.append(str(pooled.transpose(include_header=True, column_names="rung")))
    for s, res in out["seasons"].items():
        df = pl.DataFrame([{"rung": k, **v} for k, v in res.items()], infer_schema_length=None)
        lines += ["", f"Season {s}:", str(df.transpose(include_header=True, column_names="rung"))]
    for k, df in out["by_group"].items():
        lines += ["", f"By group, {k}:", str(df)]
    lines += ["", "Per-play certainty of the likeliest lineup (tenths of plays by certainty):"]
    lines.append(str(score.certainty(out["scored"], "sequence")))
    lines += ["", "Champion's weights (last season's fit):"]
    for g, w in out["models"][max(out["models"])].explain().items():
        lines.append(f"{g}: " + ", ".join(f"{a} {b:+.3f}" for a, b in w.items() if abs(b) > 1e-9))
text = "\n".join(lines)
(HERE / "backtest.txt").write_text(text, encoding="utf-8")
(HERE / "backtest.json").write_text(json.dumps({"run_id": out["run_id"], "pooled": out["pooled"], "seasons": {str(k): v for k, v in out["seasons"].items()}, "point_in_time_gap": out["point_in_time_gap"]}, indent=1), encoding="utf-8")  # fmt: skip
out["scored"].write_parquet(reconstruct.cache_dir() / "scored_2019_2024.parquet")
print(text[:3000])
