"""Do the range fixes earn their place (2026-11-04)? The next-game trees against `trees_status`
(residuals per injury-report status) and `trees_spikes` (plus a third part for every snap), on the
same rows, each judged part by part. Also checks that adding the parts left `trees` unchanged.
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/parts_ladder.py
"""

import sys
from pathlib import Path

import polars as pl

from pcf.data.gateway import Gateway
from pcf.experts.participation.twopart import Trees, TreesSpikes, TreesStatus
from pcf.validation import backtest, calibration, scores
from pcf.validation.compare import compare

sys.path.insert(0, str(Path(__file__).parent))
from compare_rungs import KEYS, history  # noqa: E402

c = pl.col
SEASONS = list(range(2016, 2025))
GROUPS = ["position", "report", "played_recently", "season"]


def line(name: str, d: pl.DataFrame) -> dict:
    r = calibration.spike_report(d)
    ch, sh, bl = r["chance"], r["share"], r["blend"]
    return {
        "variant": name,
        "rows": d.height,
        "pinball": d["loss"].mean() * 100,
        "MAE": (d["y"] - d["mean"]).abs().mean() * 100,
        "R2": 1 - ((d["y"] - d["mean"]) ** 2).mean() / d["y"].var(),
        "chance err": ch["error"],
        "slope": ch["slope"],
        "played rows": sh["rows"],
        "covered": sh["inside"] * 100,
        "above q50": sh["above"] * 100,
        "width": sh["width"] * 100,
        "blend cover": bl["inside"] * 100,
        "blend width": bl["width"] * 100,
    }


def main() -> None:
    gw = Gateway()
    bt = backtest.run(Trees(), gw, SEASONS, refit="season")
    saved = history("trees", gw).select(*KEYS, m="mean", a="q10", b="q90")
    same = bt.scored.join(saved, on=KEYS)
    print(
        f"Trees against the saved history, {same.height:,} rows: largest gap, mean "
        f"{(same['mean'] - same['m']).abs().max():.2e}, q10 {(same['q10'] - same['a']).abs().max():.2e}"
        f", q90 {(same['q90'] - same['b']).abs().max():.2e}"
    )
    runs = {"trees": bt.history}
    for cls in (TreesStatus, TreesSpikes):
        e = cls()
        pred = backtest.walk(e, bt.features, bt.targets, bt.steps, bt.test, bt.refit, bt.half_life)
        h = backtest.standard(e, pred).join(bt.targets.select(*KEYS, "y"), on=KEYS, how="left")
        runs[e.variant] = scores.row_losses(h, e.kind)
    extra = bt.features.select(*KEYS, "position", "report", "played_recently", "step_season")
    runs = {
        k: v.filter(c("y").is_not_null()).join(extra, on=KEYS, how="left") for k, v in runs.items()
    }
    groups = {
        "all": c("position").is_not_null(),
        **{p: c("position") == p for p in ("QB", "RB", "WR", "TE")},
        "Questionable": c("report") == 1,
        "Doubtful or Out": c("report") >= 2,
        "not on the report": c("report") == 0,
        "2019-2024": c("step_season") >= 2019,
    }
    with pl.Config(float_precision=3, tbl_width_chars=240, tbl_rows=60, tbl_cols=20,
                   fmt_str_lengths=30):  # fmt: skip
        for name, e in groups.items():
            print(f"\n{name}")
            print(pl.DataFrame([line(k, v.filter(e)) for k, v in runs.items()]))
    print("\nPaired, by week, pinball x100 (a - trees; 90% interval)")
    base = runs["trees"].with_columns(step=c("game_id").str.slice(0, 7))
    for k in ("trees_status", "trees_spikes"):
        a = runs[k].with_columns(step=c("game_id").str.slice(0, 7))
        for name, e in groups.items():
            cmp = compare(a.filter(e), base.filter(e), KEYS, "step", (k, "trees"))
            print(f"  {k:<13} {name:<18} {cmp.diff * 100:+.3f} ({cmp.lo * 100:+.3f} to "
                  f"{cmp.hi * 100:+.3f}): {cmp.verdict}, {cmp.rows:,} rows")  # fmt: skip
    print("\nThe harness's verdict, with its groups")
    with pl.Config(float_precision=3, tbl_width_chars=160, tbl_rows=60):
        for k, v in runs.items():
            r = calibration.spike_report(v.rename({"step_season": "season"}), GROUPS)
            s = r["share"]["groups"].filter(c("judged") & ~c("ok"))
            print(f"  {k}: passed {r['passed']}; chance {r['chance']['passed']}, share "
                  f"{r['share']['passed']}; groups failing: {s.height}")  # fmt: skip
            print(r["share"]["groups"].filter(c("group") != "season"))


if __name__ == "__main__":
    main()
