"""Why does team form beat the closing spread in new_inputs.py (2026-11-05)? Is it a leak, or is it
standing in for the week of the season? Also the last-week table in full.
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/new_inputs_week.py
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from new_inputs import CLOSE, FINAL, FORM, KEYS, SEASONS, Offered, option, with_close  # noqa: E402

from pcf.data.gateway import Gateway  # noqa: E402
from pcf.validation import backtest, leakage, scores  # noqa: E402
from pcf.validation.compare import compare  # noqa: E402

c = pl.col
OFFERS = {
    "as it is": [],
    "+ form": FORM,
    "+ week": ["week_no"],
    "+ week + form": ["week_no", *FORM],
    "+ week + close (can't ship)": ["week_no", *CLOSE],
    "+ form shuffled in week": ["form_mix", "form_mix_size"],
    "+ final week": FINAL,
    "+ week + final": ["week_no", *FINAL],
    "+ week + final + form": ["week_no", *FINAL, *FORM],
}


def main() -> None:
    gw = Gateway()
    bt = backtest.run(Offered(), gw, SEASONS, refit="season")

    # The checks that catch a leak, on the features with form and the final week in them
    leak_e = option([*FORM, *FINAL])()
    leak_bt = backtest.run(leak_e, gw, SEASONS, refit="season")
    seasons = sorted({s.season for s in leak_bt.steps if s.index in leak_bt.test})
    cuts = leakage.cutoffs(gw.calendar, seasons, leakage.CUTOFFS, 0)
    for mode in ("scramble", "delete"):
        r = leakage.future_check(leak_bt, gw, cuts, mode, 0)
        print(f"leak check {r.name if hasattr(r, 'name') else mode}: passed {r.passed}; {r.detail}")
    print(leakage.known_at_sanity(leak_e, gw), flush=True)

    feats = with_close(bt.features).with_columns(
        week_no=c("week").cast(pl.Float64),
        season_id=c("game_id").str.slice(0, 7),
    )
    rng = np.random.default_rng(20261105)
    mix = feats.select("season_id", "team", "form").unique(["season_id", "team"])
    mix = mix.with_columns(u=pl.Series(rng.random(mix.height))).with_columns(
        form_mix=c("form").sort_by("u").over("season_id")
    )
    feats = feats.join(mix.select("season_id", "team", "form_mix"), on=["season_id", "team"])
    feats = feats.with_columns(form_mix_size=c("form_mix").abs())
    print(f"Rows {feats.height:,}", flush=True)

    ctx = feats.select(*KEYS, "position", "depth1", "week_no", "final_week", "win_rate")
    runs = {}
    for name, extra in OFFERS.items():
        e = option(extra)()
        pred = backtest.walk(e, feats, bt.targets, bt.steps, bt.test, bt.refit, bt.half_life)
        h = backtest.standard(e, pred).join(bt.targets.select(*KEYS, "y"), on=KEYS, how="left")
        h = scores.row_losses(h, e.kind).filter(c("y").is_not_null())
        runs[name] = h.join(ctx, on=KEYS).with_columns(step=c("game_id").str.slice(0, 7))
        print(f"done: {name}", flush=True)

    groups = {
        "all": c("y").is_not_null(),
        "QB": c("position") == "QB",
        "WR": c("position") == "WR",
        "weeks 1-2": c("week_no") <= 2,
        "weeks 3-8": (c("week_no") > 2) & (c("week_no") <= 8),
        "weeks 9+": c("week_no") > 8,
        "not last week": c("final_week") == 0,
        "last week": c("final_week") == 1,
    }
    print("\nPaired by week against `as it is`, pinball x100 (90% interval)")
    base = runs["as it is"]
    for k, v in runs.items():
        if k == "as it is":
            continue
        print(k)
        for g, e in groups.items():
            r = compare(v.filter(e), base.filter(e), KEYS, "step", (k, "as it is"))
            print(f"  {g:<16} {r.diff * 100:+.3f} ({r.lo * 100:+.3f} to {r.hi * 100:+.3f}): "
                  f"{r.verdict}, {r.rows:,} rows")  # fmt: skip

    print("\nAgainst `+ week`: what does each add once the week is in?")
    wk = runs["+ week"]
    for k in ("+ week + form", "+ week + close (can't ship)", "+ week + final"):
        for g in ("all", "QB", "WR", "last week"):
            e = groups[g]
            r = compare(runs[k].filter(e), wk.filter(e), KEYS, "step", (k, "+ week"))
            print(f"  {k:<30} {g:<10} {r.diff * 100:+.3f} ({r.lo * 100:+.3f} to {r.hi * 100:+.3f}): "
                  f"{r.verdict}")  # fmt: skip

    b = base.filter((c("depth1") == 1)).with_columns(
        wins=pl.when(c("win_rate") >= 0.65).then(pl.lit("65%+ wins"))
        .when(c("win_rate") >= 0.4).then(pl.lit("40-65%")).otherwise(pl.lit("under 40%"))
    )  # fmt: skip
    t = b.group_by("position", "final_week", "wins").agg(
        n=pl.len(),
        was=c("y").mean() * 100,
        said=c("mean").mean() * 100,
        zero=(c("y") == 0).mean() * 100,
        said_zero=(1 - c("p_nonzero")).mean() * 100,
    )
    with pl.Config(float_precision=1, tbl_rows=30, tbl_cols=10, tbl_width_chars=120):
        print("\nStarters by week type and team wins")
        print(t.sort("position", "final_week", "wins"))


if __name__ == "__main__":
    main()
