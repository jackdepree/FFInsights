"""Is the third part right for QBs (2026-11-04)? `trees_spikes` adds the chance of every snap,
which moved QBs' range coverage from 75.7% to 88.5% and put only 12.0% of results above q50. Are
those new misses, or the same arithmetic as the spike at 0 (F13), now at the top?
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/qb_every_snap.py

Scored on QB games they played: is the chance of every snap calibrated, does the range hold 80% on
games that were neither 0 nor every snap, and what would coverage be if each forecast were exactly
true (results drawn from each row's own forecast, as in coverage_deep_dive.py)?
"""

import numpy as np
import polars as pl

from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.experts.participation.twopart import BINS, FULL, LEVELS, TreesSpikes
from pcf.validation import backtest, calibration

c = pl.col
KEYS = ["gsis_id", "game_id"]
SEASONS = list(range(2016, 2025))
RNG = 20261104
DRAWS = 40


class Capture(TreesSpikes):
    rows: list[pl.DataFrame] = []
    grids: list[np.ndarray] = []

    def predict(self, model, rows):
        g = rows.filter(c("position") == "QB")
        if g.height and "QB" in model["parts"]:
            x = g.select(self.columns).to_numpy().astype(float)
            _, full, share = model["parts"]["QB"]
            s = self.predict_share(share, x).clip(0, 1)
            t = full.predict_proba(x)[:, 1]
            listed = self._listed(x)
            grid = model["grid"]["QB"][listed, np.digitize(s, BINS)]
            self.rows.append(g.select(*KEYS, "depth1").with_columns(t=pl.Series(t), s=pl.Series(s)))
            self.grids.append(grid)
        return super().predict(model, rows)


def main() -> None:
    bt = backtest.run(Capture(), Gateway(), SEASONS, refit="season")
    d = pl.concat(Capture.rows).with_row_index("i")
    grid = np.vstack(Capture.grids)
    d = d.join(bt.scored, on=KEYS)
    g = grid[d["i"].to_numpy()]
    d = d.with_columns(
        rest10=pl.Series((d["s"].to_numpy() + g[:, 9]).clip(0, 1)),
        rest90=pl.Series((d["s"].to_numpy() + g[:, 89]).clip(0, 1)),
    )
    keep = (d["y"] > 0).to_numpy()
    on, go = d.filter(c("y") > 0), g[keep]

    every = on.select(y=(c("y") >= FULL).cast(pl.Float64), mean="t")
    r = calibration.probability_report(every)
    print(f"QB games played: {on.height:,}; every snap in {every['y'].mean():.1%}, "
          f"said {every['mean'].mean():.1%}")  # fmt: skip
    print(f"Chance of every snap: error {r['error']:.2f} points, slope {r['slope']:.3f}, "
          f"passed {r['passed']}")  # fmt: skip
    with pl.Config(float_precision=3, tbl_rows=12):
        print(r["table"])

    # Spot-check (2026-11-04): who is it right for, is it steady, does it beat knowing the starter?
    tagged = on.with_columns(
        every=(c("y") >= FULL).cast(pl.Float64),
        season=c("game_id").str.slice(0, 4).cast(pl.Int32),
    )
    rows = []
    groups = {"starter": c("depth1") == 1, "not starter": c("depth1") == 0}
    groups |= {str(s): c("season") == s for s in SEASONS}
    for name, e in groups.items():
        g = tagged.filter(e)
        x = g.select(y="every", mean="t")
        one = calibration.probability_report(x)
        rows.append({"group": name, "rows": g.height, "said": x["mean"].mean(),
                     "was": x["y"].mean(), "error": one["error"],
                     "slope": one["slope"]})  # fmt: skip
    with pl.Config(float_precision=3, tbl_rows=20):
        print(pl.DataFrame(rows))
    # The simple rival: each season, last seasons' every-snap rate for starters and non-starters
    rival = []
    for s in SEASONS:
        past = tagged.filter(c("season") < s).group_by("depth1").agg(r=c("every").mean())
        rival.append(tagged.filter(c("season") == s).join(past, on="depth1", how="inner"))
    rival = pl.concat(rival)
    base = rival.select(((c("every") - c("r")) ** 2).mean()).item()
    model = rival.select(((c("every") - c("t")) ** 2).mean()).item()
    print(f"Brier on {rival.height:,} games: logistic {model:.4f}, starter rate only {base:.4f}")
    st = tagged.filter(c("depth1") == 1)["t"]
    print(f"Starters' chance of every snap: 5th to 95th percentile {st.quantile(0.05):.1%} to "
          f"{st.quantile(0.95):.1%}; 25th to 75th {st.quantile(0.25):.1%} to "
          f"{st.quantile(0.75):.1%}")  # fmt: skip

    # Ranges that collapse to 100% to 100%: how often below, and which part put them there?
    ranges = on.with_columns(
        flat=c("if_nonzero_q10") >= FULL,
        below=c("y") < c("if_nonzero_q10"),
        inside=(c("y") >= c("if_nonzero_q10")) & (c("y") <= c("if_nonzero_q90")),
        every=c("y") >= FULL,
        t90=c("t") >= 0.9,
        s_full=c("s") >= FULL,
        rest_full=c("rest10") >= FULL,
    )
    for name, e in {"100 to 100": c("flat"), "other": ~c("flat"), "all": c("y") > 0,
                    "q10 at 90%+": c("if_nonzero_q10") >= 0.9}.items():  # fmt: skip
        x = ranges.filter(e)
        print(f"{name}: {x.height:,} games; every snap {x['every'].mean():.1%}, said "
              f"{x['t'].mean():.1%}; below q10 {x['below'].mean():.1%}, inside "
              f"{x['inside'].mean():.1%}; mean said {x['if_nonzero_mean'].mean():.1%}, was "
              f"{x['y'].mean():.1%}")  # fmt: skip
    flat = ranges.filter(c("flat"))
    print(f"Why 100 to 100 ({flat.height:,}): chance of every snap at 90%+ on "
          f"{flat['t90'].mean():.1%}; otherwise share at 100% on {flat['s_full'].mean():.1%}; "
          f"otherwise share's low end at 100% on {flat['rest_full'].mean():.1%}; mean otherwise "
          f"share {flat['s'].mean():.1%}")  # fmt: skip
    for name, e in {"t at 90%+": c("t90"), "t under 90%": ~c("t90")}.items():
        x = flat.filter(e)
        if x.height:
            print(f"  {name}: {x.height:,} games, every snap {x['every'].mean():.1%}, said "
                  f"{x['t'].mean():.1%}")  # fmt: skip
    off = flat.filter(~c("every"))
    print(f"  Below-range games ({off.height:,}): said otherwise {off['s'].mean():.1%}, "
          f"was {off['y'].mean():.1%}")  # fmt: skip

    rest = on.filter(c("y") < FULL)
    held = rest.select(((c("y") >= c("rest10")) & (c("y") <= c("rest90"))).mean()).item()
    print(f"Games neither 0 nor every snap: {rest.height:,}; range holds {held:.1%}, "
          f"{rest.select((c('y') < c('rest10')).mean()).item():.1%} below, "
          f"{rest.select((c('y') > c('rest90')).mean()).item():.1%} above")  # fmt: skip

    # If each forecast were exactly true
    rng = np.random.default_rng(RNG)
    t, s = on["t"].to_numpy(), on["s"].to_numpy()
    q10, q50, q90 = (on[f"if_nonzero_{q}"].to_numpy() for q in ("q10", "q50", "q90"))
    inside, above = [], []
    for _ in range(DRAWS):
        u = rng.random(len(t))
        every_snap = u >= 1 - t
        v = np.clip(u / np.maximum(1 - t, 1e-6), 0, 1)
        at = np.clip((v - LEVELS[0]) / (LEVELS[1] - LEVELS[0]), 0, len(LEVELS) - 1)
        lo = at.astype(int)
        hi = np.minimum(lo + 1, len(LEVELS) - 1)
        i = np.arange(len(t))
        y = (s + go[i, lo] + (at - lo) * (go[i, hi] - go[i, lo])).clip(0, 1)
        y[every_snap] = 1.0
        inside.append(((y >= q10) & (y <= q90)).mean())
        above.append((y > q50).mean())
    y = on["y"].to_numpy()
    print(f"\nRange, QB games played: actual {((y >= q10) & (y <= q90)).mean():.1%}; "
          f"if exactly true {np.mean(inside):.1%}")  # fmt: skip
    print(f"Above q50: actual {(y > q50).mean():.1%}; if exactly true {np.mean(above):.1%}")
    free = on.filter(c("if_nonzero_q50") < FULL)
    print(f"Where q50 is below 100% ({free.height:,} of {on.height:,}): "
          f"{free.select((c('y') > c('if_nonzero_q50')).mean()).item():.1%} above q50")  # fmt: skip

    names = load("player_game", parts=["injury"], seasons=[2024]).select(*KEYS, "full_name", "week")
    show = d.join(names, on=KEYS).filter(c("full_name") == "Josh Allen").sort("week")
    print("\nOne starter's 2024")
    for x in show.iter_rows(named=True):
        print(f"  wk {x['week']:>2} chance of 0 {1 - x['p_nonzero']:>4.0%}  "
              f"every snap {x['t']:>4.0%}  otherwise {x['s']:>4.0%}  "
              f"range {x['if_nonzero_q10']:>4.0%} to {x['if_nonzero_q90']:>4.0%}  "
              f"result {x['y']:>4.0%}")  # fmt: skip


if __name__ == "__main__":
    main()
