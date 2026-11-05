"""CEO spot-check (2026-11-04): is next-game coverage of 85.3% really fine, and what if each part of
the forecast is judged on its own: the chance of exactly 0 snaps, then the share if they play?
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/coverage_deep_dive.py

Saved histories hold only the blended mean and ranges, so this refits the `trees` walk-forward to
capture the two parts. It first checks that the refit matches the saved history.

Tests:
1. The self-test: if each row's forecast were exactly true, what would coverage be? Draw results
   from each row's own forecast, then compare. This replaces the blend in F13 with a measurement.
2. The randomized PIT: the place a result lands within its own forecast, with results of exactly 0
   spread across the spike. It's uniform only if the whole forecast, spike included, is right.
3. Part 1: is the chance of exactly 0 calibrated? Part 2: on rows where they played, does the
   conditional range hold 80%?
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from pcf.config import get_config
from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.experts.participation.twopart import BINS, LEVELS, Trees
from pcf.validation import backtest

sys.path.insert(0, str(Path(__file__).parent))
from compare_rungs import KEYS, context, history  # noqa: E402

c = pl.col
SEASONS = list(range(2016, 2025))
DRAWS = 40
RNG = 20261104


class Capture(Trees):
    """The trees, keeping the parts behind each prediction."""

    rows: list[pl.DataFrame] = []
    grids: list[np.ndarray] = []

    def predict(self, model, rows):
        for pos, g in rows.partition_by("position", as_dict=True).items():
            if pos[0] not in model["parts"]:
                continue
            x = g.select(self.columns).to_numpy().astype(float)
            on_field, share = model["parts"][pos[0]]
            p = on_field.predict_proba(x)[:, 1]
            s = self.predict_share(share, x).clip(0, 1)
            grid = model["grid"][pos[0]][np.digitize(s, BINS)]
            self.rows.append(g.select(self.keys()).with_columns(p=pl.Series(p), s=pl.Series(s)))
            self.grids.append(grid)
        return super().predict(model, rows)


def parts(gw: Gateway) -> tuple[pl.DataFrame, np.ndarray]:
    """Each row's two parts and residual quantiles, in a cache: the refit takes minutes."""
    folder = get_config().zone("interim") / "participation_parts"
    if not (folder / "rows.parquet").exists():
        backtest.run(Capture(), gw, SEASONS, refit="season")
        folder.mkdir(parents=True, exist_ok=True)
        pl.concat(Capture.rows).write_parquet(folder / "rows.parquet")
        np.save(folder / "grids.npy", np.vstack(Capture.grids))
    return pl.read_parquet(folder / "rows.parquet"), np.load(folder / "grids.npy")


def quantile_of(u: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Each row's residual at its own level u, interpolating its row of the grid."""
    at = np.clip((u - LEVELS[0]) / (LEVELS[1] - LEVELS[0]), 0, len(LEVELS) - 1)
    lo = at.astype(int)
    hi = np.minimum(lo + 1, len(LEVELS) - 1)
    i = np.arange(len(u))
    return grid[i, lo] + (at - lo) * (grid[i, hi] - grid[i, lo])


def level_of(resid: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Where each row's residual falls in its own grid, 0 to 1."""
    below = (grid <= resid[:, None]).sum(1)
    return np.clip(below / grid.shape[1], 0, 1)


def draw(d: pl.DataFrame, grid: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One result per row from its own forecast."""
    p, s = d["p"].to_numpy(), d["s"].to_numpy()
    u = rng.random(len(p))
    on = u >= 1 - p
    y = np.zeros(len(p))
    level = (u[on] - (1 - p[on])) / p[on]
    y[on] = (s[on] + quantile_of(level, grid[on])).clip(0, 1)
    return y


def week_interval(d: pl.DataFrame, value: str) -> tuple[float, float]:
    """A 90% interval on a mean, resampling whole weeks."""
    g = d.group_by("step").agg(s=c(value).sum(), n=pl.len()).sort("step")
    s, n = g["s"].to_numpy(), g["n"].to_numpy()
    draws = np.random.default_rng(RNG).integers(0, len(s), (2000, len(s)))
    return tuple(np.quantile(s[draws].sum(1) / n[draws].sum(1), [0.05, 0.95]))


def show(rows: list[dict], title: str, precision: int = 1) -> None:
    print(f"\n{title}")
    with pl.Config(float_precision=precision, tbl_width_chars=220, tbl_rows=60, tbl_cols=24,
                   fmt_str_lengths=40):  # fmt: skip
        print(pl.DataFrame(rows))


def against_self(d: pl.DataFrame, groups: dict[str, pl.Expr], title: str) -> None:
    rows = []
    for name, e in groups.items():
        g = d.filter(e)
        lo, hi = week_interval(g, "gap")
        rows.append({
            "group": name, "rows": g.height, "covered": g["inside"].mean() * 100,
            "if exactly true": g["self_inside"].mean() * 100, "gap": g["gap"].mean() * 100,
            "lo": lo * 100, "hi": hi * 100,
            "below": g["below"].mean() * 100, "self below": g["self_below"].mean() * 100,
            "above": g["above"].mean() * 100, "self above": g["self_above"].mean() * 100,
        })  # fmt: skip
    show(rows, title)


def pit_table(d: pl.DataFrame, groups: dict[str, pl.Expr]) -> None:
    rows = []
    for name, e in groups.items():
        g = d.filter(e)
        share = g.group_by((c("pit") * 10).floor().clip(0, 9).alias("b")).agg(n=pl.len()).sort("b")
        row = {"group": name, "rows": g.height}
        row |= {f"{int(b) * 10}s": n / g.height * 100 for b, n in share.iter_rows()}
        rows.append(row)
    show(rows, "Where results land within their own forecast (each decile should hold 10%)")


def part_one(d: pl.DataFrame) -> None:
    edges = [0, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95, 1.0001]
    bins = d.with_columns(
        b=pl.col("p0").cut(edges[1:-1], labels=[f"{a:.0%}-{b:.0%}" for a, b in
                                                zip(edges, edges[1:], strict=False)])
    ).group_by("b").agg(rows=pl.len(), said=c("p0").mean() * 100, was=c("zero").mean() * 100).sort(
        "said"
    )  # fmt: skip
    print("\nPart 1: the chance of exactly 0 snaps")
    with pl.Config(float_precision=1, tbl_rows=12):
        print(bins)
    rows = []
    groups = {
        "all": c("season") > 0, **{p: c("position") == p for p in ("QB", "RB", "WR", "TE")},
        "2016-2018": c("season") <= 2018, "2019-2024": c("season") >= 2019,
        "played in last 8": c("recent"), "not played in last 8": ~c("recent"),
    }  # fmt: skip
    for name, e in groups.items():
        g = d.filter(e)
        p0, z = g["p0"].to_numpy().clip(1e-5, 1 - 1e-5), g["zero"].to_numpy().astype(int)
        logit = np.log(p0 / (1 - p0)).reshape(-1, 1)
        slope = LogisticRegression(C=1e6).fit(logit, z).coef_[0][0]
        b = g.with_columns(b=(c("p0") * 20).floor()).group_by("b").agg(
            n=pl.len(), a=c("p0").mean(), z=c("zero").mean()
        )  # fmt: skip
        err = ((b["a"] - b["z"]).abs() * b["n"]).sum() / b["n"].sum()
        rows.append({
            "group": name, "rows": g.height, "said": p0.mean() * 100, "was": z.mean() * 100,
            "AUC": roc_auc_score(z, p0), "error": err * 100, "slope": slope,
        })  # fmt: skip
    show(rows, "Part 1, by group", 3)


def part_two(d: pl.DataFrame) -> None:
    on = d.filter(~c("zero"))
    groups = {
        "all": c("season") > 0, **{p: c("position") == p for p in ("QB", "RB", "WR", "TE")},
        **{n: c("s").is_between(a, b, closed="left") for n, a, b in
           [("said under 25", 0, 0.25), ("said 25-50", 0.25, 0.5), ("said 50-75", 0.5, 0.75),
            ("said 75+", 0.75, 1.01)]},
        "2016-2018": c("season") <= 2018, "2019-2024": c("season") >= 2019,
        "listed Questionable": c("report_status") == "Questionable",
    }  # fmt: skip
    rows = []
    on = on.with_columns(held=((c("y") >= c("c10")) & (c("y") <= c("c90"))).cast(pl.Float64))
    for name, e in groups.items():
        g = on.filter(e)
        lo, hi = week_interval(g, "held")
        rows.append({
            "group": name, "rows": g.height, "covered": g["held"].mean() * 100,
            "lo": lo * 100, "hi": hi * 100,
            "below": (g["y"] < g["c10"]).mean() * 100, "above": (g["y"] > g["c90"]).mean() * 100,
            "above q50": (g["y"] > g["c50"]).mean() * 100,
            "width": (g["c90"] - g["c10"]).mean() * 100,
            "bias": (g["s"] - g["y"]).mean() * 100, "MAE": (g["s"] - g["y"]).abs().mean() * 100,
            "at 100": (g["y"] >= 0.999).mean() * 100,
            "R2 x100": (1 - ((g["y"] - g["s"]) ** 2).mean() / g["y"].var()) * 100,
        })  # fmt: skip
    show(rows, "Part 2: the share if they play, on the rows where they did (range should hold 80%)")
    rows = []
    for pos in ("QB", "RB", "WR", "TE"):
        g = on.filter(c("position") == pos)
        up = g.filter(c("y") > c("c90"))
        rows.append({
            "position": pos, "above q90": up.height, "of those, exactly 100": (up["y"] >= 0.999).mean() * 100,  # noqa: E501
            "said 90+": (g["s"] >= 0.9).mean() * 100,
            "q90 is 100": (g["c90"] >= 0.999).mean() * 100,
        })  # fmt: skip
    show(rows, "A second spike at 100%? Rows above the range, by position")


def examples(d: pl.DataFrame) -> None:
    names = load(
        "player_game", parts=["injury"], seasons=[2024]
    ).select(*KEYS, "full_name", "week")  # fmt: skip
    one = d.filter(c("season") == 2024).join(names, on=KEYS).filter(c("full_name") == "A.J. Brown")
    print()
    print("One player's 2024, every game: the forms a forecast takes")
    for x in one.sort("week").iter_rows(named=True):
        print(f"  wk {x['week']:>2} {x['report_status'] or '-':<13} chance of 0 {x['p0']:>4.0%}  "
              f"if plays {x['s']:>4.0%}  range {x['q10']:>4.0%} to {x['q90']:>4.0%}  "
              f"result {x['y']:>4.0%}  {'inside' if x['inside'] else 'OUTSIDE'}")  # fmt: skip


def horizons(gw: Gateway) -> None:
    rows = []
    for v in ("lasso_h3", "lasso_rest"):
        h = history(v, gw)
        low = h.filter(c("q10") > 0)
        out = low.filter(c("y") < c("q10"))
        rows.append({
            "variant": v, "rows": h.height, "exactly 0": (h["y"] == 0).mean() * 100,
            "q10>0 rows": low.height,
            "covered": low.select(((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()).item() * 100,  # noqa: E501
            "below q10": out.height / low.height * 100,
            "of those, exactly 0": (out["y"] == 0).mean() * 100,
            "of those, under half of q10": (out["y"] < out["q10"] / 2).mean() * 100,
        })  # fmt: skip
    show(rows, "Longer horizons: would a spike at exactly 0 explain the rows below q10?")


def main() -> None:
    gw = Gateway()
    got, grid = parts(gw)
    got = got.with_row_index("i")
    h = history("trees", gw)
    ctx = context().select(*KEYS, "position", "season", "recent")
    status = load("player_game", parts=["injury"], seasons=SEASONS).select(*KEYS, "report_status")
    d = h.join(got, on=KEYS).join(ctx, on=KEYS).join(status, on=KEYS, how="left").sort("i")
    print(f"Rows: history {h.height:,}, matched {d.height:,}. Largest gap between the refit and the "  # noqa: E501
          f"saved mean: {(d['mean'] - d['p'] * d['s']).abs().max():.2e}")  # fmt: skip
    g = grid[d["i"].to_numpy()]
    y = d["y"].to_numpy()
    p, s = d["p"].to_numpy(), d["s"].to_numpy()
    q = {k: d[k].to_numpy() for k in ("q10", "q50", "q90")}
    rng = np.random.default_rng(RNG)

    # The self-test: many draws per row, against that row's own range
    sims = np.stack([draw(d, g, rng) for _ in range(DRAWS)])
    # The whole forecast: 0s spread across the spike; other results at their place above it
    u = rng.random(len(y))
    resid_level = level_of(y - s, g)
    pit = np.where(y == 0, u * (1 - p), (1 - p) + p * resid_level)

    d = d.with_columns(
        p0=pl.Series(1 - p), zero=c("y") == 0, pit=pl.Series(pit),
        inside=(c("y") >= c("q10")) & (c("y") <= c("q90")),
        below=c("y") < c("q10"), above=c("y") > c("q90"),
        self_inside=pl.Series(((sims >= q["q10"]) & (sims <= q["q90"])).mean(0)),
        self_below=pl.Series((sims < q["q10"]).mean(0)),
        self_above=pl.Series((sims > q["q90"]).mean(0)),
        c10=pl.Series((s + g[:, 9]).clip(0, 1)), c50=pl.Series((s + g[:, 49]).clip(0, 1)),
        c90=pl.Series((s + g[:, 89]).clip(0, 1)),
    ).with_columns(gap=c("inside").cast(pl.Float64) - c("self_inside"))  # fmt: skip

    show([{
        "cell": n, "rows": x.height, "share of all": x.height / d.height * 100,
        "inside": x["inside"].mean() * 100,
    } for n, x in [
        ("range is 0 to 0, result 0", d.filter((c("q90") == 0) & c("zero"))),
        ("range is 0 to 0, result above", d.filter((c("q90") == 0) & ~c("zero"))),
        ("q10 = 0, q90 > 0, result 0", d.filter((c("q10") == 0) & (c("q90") > 0) & c("zero"))),
        ("q10 = 0, q90 > 0, result above 0", d.filter((c("q10") == 0) & (c("q90") > 0) & ~c("zero"))),  # noqa: E501
        ("q10 > 0, result 0", d.filter((c("q10") > 0) & c("zero"))),
        ("q10 > 0, result above 0", d.filter((c("q10") > 0) & ~c("zero"))),
    ]], "Every row, by where it falls")  # fmt: skip

    against_self(d, {
        "all": c("season") > 0,
        "q10 above 0": c("q10") > 0, "q10 = 0, q90 above 0": (c("q10") == 0) & (c("q90") > 0),
        "range is 0 to 0": c("q90") == 0,
        "without the 0-to-0 rows": c("q90") > 0,
        **{f"chance of 0 {a:.0%}-{b:.0%}": c("p0").is_between(a, b, closed="left") for a, b in
           [(0, 0.02), (0.02, 0.05), (0.05, 0.1), (0.1, 0.2), (0.2, 0.5), (0.5, 0.9), (0.9, 1.01)]},
        **{p: c("position") == p for p in ("QB", "RB", "WR", "TE")},
        **{str(x): c("season") == x for x in SEASONS},
        "played in last 8": c("recent"), "not played in last 8": ~c("recent"),
    }, "Coverage against the forecast's own promise")  # fmt: skip

    pit_table(d, {
        "all": c("season") > 0, **{p: c("position") == p for p in ("QB", "RB", "WR", "TE")},
        "played in last 8": c("recent"), "2019-2024": c("season") >= 2019,
    })  # fmt: skip
    part_one(d)
    part_two(d)
    examples(d)
    horizons(gw)


if __name__ == "__main__":
    main()
