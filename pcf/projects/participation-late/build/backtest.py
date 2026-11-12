"""The participation-late backtest, 2023-2024 (FTN starts in 2022; the 2025 vault stays closed):
the late edition against the morning-after map on the same plays. Writes backtest.txt and
backtest.json here, the late edition's walk-forward history to outputs/, and one MLflow attempt.

    python projects/participation-late/build/backtest.py
"""

# ruff: noqa: E501
import json
import time
from pathlib import Path

import polars as pl

from pcf.experts.participation_late import reconstruct
from pcf.experts.participation_live import reconstruct as live

HERE = Path(__file__).parent

t0 = time.time()
out = reconstruct.backtest()
lines = [
    f"participation-late backtest 2023-2024, run {out['run_id']}, {time.time() - t0:.0f} s",
    f"history: {out['history_path']}",
    f"point-in-time gap (0 = none): {out['point_in_time_gap']}; FTN rows a morning-after view already holds (0 = none): {out['ftn_rows_at_morning']}",
    "",
    "live = the morning-after map (refitted); late = with FTN's counts (champion); late_ftn_seasons = with FTN, trained on FTN's seasons only. Open spots and of 11 from the likeliest lineup unless snap_matched.",
]
with pl.Config(tbl_cols=40, tbl_rows=60, float_precision=4, tbl_width_chars=400):
    pooled = pl.DataFrame([{"version": k, **v} for k, v in out["pooled"].items()], infer_schema_length=None)
    lines += ["Pooled:", str(pooled.transpose(include_header=True, column_names="version"))]
    for s, res in out["seasons"].items():
        df = pl.DataFrame([{"version": k, **v} for k, v in res.items()], infer_schema_length=None)
        lines += ["", f"Season {s}:", str(df.transpose(include_header=True, column_names="version"))]
    for k, df in out["by_group"].items():
        lines += ["", f"By group, {k} (likeliest):", str(df)]
    for k, df in out["certainty"].items():
        lines += ["", f"Certainty, {k} (tenths of plays):", str(df)]
    lines += ["", "Late model's weights on FTN's columns (last season's fit):"]
    for g, w in out["models"][max(out["models"])].explain().items():
        lines.append(f"{g}: " + ", ".join(f"{a} {w[a]:+.3f}" for a in ("bf", "box", "rush", "blitz", "motion", "pa", "screen", "fmiss") if a in w))
text = "\n".join(lines)
(HERE / "backtest.txt").write_text(text, encoding="utf-8")
(HERE / "backtest.json").write_text(json.dumps({"run_id": out["run_id"], "pooled": out["pooled"], "seasons": {str(k): v for k, v in out["seasons"].items()}, "point_in_time_gap": out["point_in_time_gap"], "ftn_rows_at_morning": out["ftn_rows_at_morning"]}, indent=1), encoding="utf-8")
out["scored"].write_parquet(live.cache_dir() / "scored_late_2023_2024.parquet")
print(text[:4000])
