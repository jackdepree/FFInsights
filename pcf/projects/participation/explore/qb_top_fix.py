"""Which fix closes QBs' collapsed ranges (2026-11-05, spot-check on F26)? Each option against
`trees_spikes` on the same QB rows: keep games that aren't every snap below 100% (truncate), and
recalibrate the chance of every snap on the latest 20% of each training window (Platt or isotonic).
Ranges are scored on QB games played; pinball on every QB row.
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/qb_top_fix.py
"""

import polars as pl

from pcf.data.gateway import Gateway
from pcf.experts.participation.twopart import FULL, TreesSpikes, calibrated
from pcf.validation import backtest, calibration, scores
from pcf.validation.compare import compare

c = pl.col
KEYS = ["gsis_id", "game_id"]
SEASONS = list(range(2016, 2025))
OPTIONS = {
    "as it is": (False, None),
    "truncate": (True, None),
    "platt": (False, "platt"),
    "isotonic": (False, "isotonic"),
    "truncate + platt": (True, "platt"),
    "truncate + isotonic": (True, "isotonic"),
}


def option(cut: bool, how: str | None):
    """`TreesSpikes` with the fix's switches, keeping the chance of every snap it predicted."""

    class Option(TreesSpikes):
        truncate = cut
        recalibrate = how
        said: list[pl.DataFrame] = []

        def predict(self, model, rows):
            if "QB" in model["parts"]:
                x = rows.select(self.columns).to_numpy().astype(float)
                full = model["parts"]["QB"][1]
                t = calibrated(model["calibrators"].get("QB"), full.predict_proba(x)[:, 1])
                self.said.append(rows.select(*KEYS, "depth1").with_columns(t=pl.Series(t)))
            return super().predict(model, rows)

    return Option


def slope(d: pl.DataFrame) -> tuple[float, float]:
    r = calibration.probability_report(d.select(y=(c("y") >= FULL).cast(pl.Float64), mean="t"))
    return r["error"], r["slope"]


def line(name: str, d: pl.DataFrame) -> dict:
    on = d.filter(c("y") > 0)
    q10, q90 = c("if_nonzero_q10"), c("if_nonzero_q90")
    top = on.filter(q10 >= 0.9)
    err, sl = slope(on)
    _, starter = slope(on.filter(c("depth1") == 1))
    return {
        "option": name,
        "pinball": d["loss"].mean() * 100,
        "MAE": (d["y"] - d["mean"]).abs().mean() * 100,
        "error": err,
        "slope": sl,
        "starter slope": starter,
        "inside": on.select(((c("y") >= q10) & (c("y") <= q90)).mean()).item() * 100,
        "below": on.select((c("y") < q10).mean()).item() * 100,
        "above q50": on.select((c("y") > c("if_nonzero_q50")).mean()).item() * 100,
        "at 100": on.select((q10 >= FULL).sum()).item(),
        "q10 90+": top.height,
        "its below": top.select((c("y") < q10).mean()).item() * 100,
    }


def main() -> None:
    bt = backtest.run(TreesSpikes(), Gateway(), SEASONS, refit="season")
    qb = bt.features.filter(c("position") == "QB")
    runs = {}
    for name, (cut, how) in OPTIONS.items():
        e = option(cut, how)()
        pred = backtest.walk(e, qb, bt.targets, bt.steps, bt.test, bt.refit, bt.half_life)
        h = backtest.standard(e, pred).join(bt.targets.select(*KEYS, "y"), on=KEYS, how="left")
        h = scores.row_losses(h, e.kind).filter(c("y").is_not_null())
        runs[name] = h.join(pl.concat(e.said), on=KEYS)
        print(f"done: {name}", flush=True)
    with pl.Config(float_precision=3, tbl_width_chars=220, tbl_cols=20):
        print(pl.DataFrame([line(k, v) for k, v in runs.items()]))

    print("\nPaired by week against `as it is`, pinball x100, QB rows (90% interval)")
    base = runs["as it is"].with_columns(step=c("game_id").str.slice(0, 7))
    for k, v in runs.items():
        if k != "as it is":
            a = v.with_columns(step=c("game_id").str.slice(0, 7))
            r = compare(a, base, KEYS, "step", (k, "as it is"))
            print(f"  {k:<22} {r.diff * 100:+.3f} ({r.lo * 100:+.3f} to {r.hi * 100:+.3f}): "
                  f"{r.verdict}")  # fmt: skip

    print("\nChance of every snap, said -> was (games), by what it said")
    for k, v in runs.items():
        on = v.filter(c("y") > 0).with_columns(
            b=(c("t") * 10).floor().clip(0, 9), every=(c("y") >= FULL).cast(pl.Float64)
        )
        t = on.group_by("b").agg(n=pl.len(), said=c("t").mean(), was=c("every").mean()).sort("b")
        print(f"  {k:<22} " + "  ".join(
            f"{a:.0%}->{b:.0%} ({n})" for a, b, n in t.select("said", "was", "n").iter_rows()
        ))  # fmt: skip


if __name__ == "__main__":
    main()
