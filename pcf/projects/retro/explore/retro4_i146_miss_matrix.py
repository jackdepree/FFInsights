"""IDEAS I146 (retro 4's dream, 2026-11-25): the experts' miss matrix.

Discovery only. Saved walk-forward histories, 2016-2024 (the 2025 vault is left out). For every
pair of forecasts on the same rows (player-game or team-game), A's miss (result minus forecast)
is corrected walk-forward by season, once from A's own forecast alone (a recalibration) and once
with B's forecast beside it. The cell's gain is the share of A's squared error that B removes
beyond the recalibration. B's value is used only where B was made no later than A.

- Interval: whole weeks resampled (1,000 draws). p: the share of draws at or below zero.
- Copies: B shuffled within each week, 19 times; a cell must beat the largest copy.
- A false-discovery control over every cell (Benjamini-Hochberg at 10%).

Claude's odds, written before the run (IDEAS.md, I146): 60% at least one cell passes; 35% one
adds 0.3%+ to its expert once built (not testable here: this run gives the cell's size only).

Run from pcf/:  python projects/retro/explore/retro4_i146_miss_matrix.py > projects/retro/explore/retro4_i146_miss_matrix.txt
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.validation.backtest import targets

c = pl.col
LAST = "2025"
DRAWS = 1000
COPIES = 19
MIN_TRAIN = 2
FDR = 0.10
RNG = np.random.default_rng(146)

PLAYER = [
    ("participation", "trees_week"),
    ("availability", "next_logit"),
    ("crude-forecaster", "receiving_next_lasso"),
    ("crude-forecaster", "rushing_next_lasso"),
    ("crude-forecaster", "passing_next_lasso"),
    ("crude-forecaster", "qb_rushing_next_lasso"),
    ("opportunity-quality", "eff_trees"),
    ("baselines", "lasso"),
    ("baselines", "ecr"),
]
TEAM = [
    ("team-efficiency", "off_next3_ridge"),
    ("team-efficiency", "def_next3_ridge"),
    ("pace", "plays_full"),
    ("pace", "dropbacks_full"),
    ("pace", "runs_full"),
    ("pace", "proe_shrunk"),
    ("pace", "pace_oe_shrunk"),
    ("schemes-v2", "shotgun_shrunk"),
    ("schemes-v2", "tempo_shrunk"),
    ("schemes-v2", "depth_shrunk"),
    ("player-pace", "proe_lineup"),
    ("crude-forecaster", "team_next_lasso"),
    ("elo", "wins_next3"),
]


def history(project: str, variant: str, gateway: Gateway):
    """The latest saved backtest run with its outcomes, or None (with the reason)."""
    try:
        cls = find(project, variant)
        expert = cls()
        folder = get_config().zone("outputs") / project / variant
        runs = sorted(
            (p for p in folder.iterdir() if (p / "history.parquet").exists()),
            key=lambda p: p.stat().st_mtime,
        )
        h = None
        for run in reversed(runs):
            try:
                x = pl.read_parquet(run / "history.parquet")
            except Exception:
                continue
            if x["game_id"].min() < "2024":
                h = x
                break
        if h is None:
            return None, "no backtest run"
        if h["quantity"].n_unique() > 1:
            return None, f"{h['quantity'].n_unique()} quantities"
        keys = list(expert.keys())
        y = targets(expert, gateway).select(*keys, "y")
        h = h.filter(c("game_id") < LAST).join(y, on=keys)
        return h.select(*keys, "as_of", "mean", "y"), keys
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"[:90]


def cell(a: pl.DataFrame, b: pl.DataFrame, keys: list[str]):
    d = a.join(b.select(*keys, c("as_of").alias("as_of_b"), c("mean").alias("mb")), on=keys)
    d = d.filter(c("as_of_b") <= c("as_of")).drop_nulls(["mean", "y", "mb"])
    if d.height < 2000:
        return None
    d = d.with_columns(
        season=c("game_id").str.slice(0, 4).cast(pl.Int32),
        week=c("game_id").str.slice(0, 7),
        z=c("y") - c("mean"),
    )
    season = d["season"].to_numpy()
    week = d["week"].to_numpy()
    z = d["z"].to_numpy().astype(float)
    ma = d["mean"].to_numpy().astype(float)
    mb = d["mb"].to_numpy().astype(float)
    seasons = np.unique(season)
    test = np.isin(season, seasons[MIN_TRAIN:])
    _, wk = np.unique(week, return_inverse=True)

    def walk(xb):
        e0 = np.zeros_like(z)
        e1 = np.zeros_like(z)
        x0 = np.column_stack([np.ones_like(z), ma])
        x1 = np.column_stack([x0, xb])
        for s in seasons[MIN_TRAIN:]:
            tr, te = season < s, season == s
            b0 = np.linalg.lstsq(x0[tr], z[tr], rcond=None)[0]
            b1 = np.linalg.lstsq(x1[tr], z[tr], rcond=None)[0]
            e0[te] = z[te] - x0[te] @ b0
            e1[te] = z[te] - x1[te] @ b1
        return e0, e1

    e0, e1 = walk(mb)
    nw = wk.max() + 1
    base = np.bincount(wk[test], z[test] ** 2, nw)
    gain_w = np.bincount(wk[test], e0[test] ** 2 - e1[test] ** 2, nw)
    used = np.flatnonzero(np.bincount(wk[test], minlength=nw))
    share = gain_w[used].sum() / base[used].sum()
    recal = 1 - np.bincount(wk[test], e0[test] ** 2, nw)[used].sum() / base[used].sum()
    draws = RNG.choice(used, (DRAWS, used.size))
    boot = gain_w[draws].sum(1) / base[draws].sum(1)
    copies = []
    order = np.argsort(wk, kind="stable")
    bounds = np.flatnonzero(np.diff(wk[order])) + 1
    for _ in range(COPIES):
        xb = mb.copy()
        for g in np.split(order, bounds):
            xb[g] = mb[RNG.permutation(g)]
        f0, f1 = walk(xb)
        copies.append((f0[test] ** 2 - f1[test] ** 2).sum() / (z[test] ** 2).sum())
    copies = np.array(copies)
    return dict(
        rows=int(test.sum()),
        share=share,
        lo=np.quantile(boot, 0.05),
        hi=np.quantile(boot, 0.95),
        p=(boot <= 0).mean() + 1 / DRAWS,
        copy_max=copies.max(),
        copy_mean=copies.mean(),
        recal=recal,
        r=np.corrcoef(z[test], mb[test])[0, 1],
    )


def main() -> None:
    gateway = Gateway()
    out = []
    for level, specs in (("player", PLAYER), ("team", TEAM)):
        hs = {}
        for proj, var in specs:
            h, keys = history(proj, var, gateway)
            name = f"{proj}/{var}"
            if h is None:
                print(f"skipped {name}: {keys}")
                continue
            hs[name] = (h, keys)
            print(f"loaded {name}: {h.height:,} rows, keys {keys}")
        for an, (ha, ka) in hs.items():
            for bn, (hb, kb) in hs.items():
                if an == bn or ka != kb:
                    continue
                r = cell(ha, hb, ka)
                if r is None:
                    continue
                out.append(dict(level=level, a=an, b=bn, **r))
                print(f"  {an} <- {bn}: {r['share']:+.3%} ({r['lo']:+.3%} to {r['hi']:+.3%}), copies max {r['copy_max']:+.3%}, rows {r['rows']:,}", flush=True)
    t = pl.DataFrame(out).sort("p")
    m = t.height
    t = t.with_row_index("rank", 1).with_columns(bh=c("p") <= FDR * c("rank") / m)
    # Benjamini-Hochberg: every cell up to the largest rank that passes
    k = t.filter(c("bh"))["rank"].max() or 0
    t = t.with_columns(fdr=c("rank") <= k, beats_copies=c("share") > c("copy_max"))
    t = t.with_columns(passes=c("fdr") & c("beats_copies") & (c("lo") > 0))
    print(f"\n{m} cells; {t['passes'].sum()} pass (false-discovery control at 10%, beats all 19 copies, 90% interval above 0)\n")
    print("Passing cells, largest first (share of A's squared error removed by B, beyond A's own recalibration):")
    for r in t.filter(c("passes")).sort("share", descending=True).iter_rows(named=True):
        print(f"  [{r['level']}] {r['a']}  <-  {r['b']}: {r['share']:+.3%} ({r['lo']:+.3%} to {r['hi']:+.3%}); copies {r['copy_mean']:+.3%} mean, {r['copy_max']:+.3%} max; recalibration alone {r['recal']:+.3%}; r {r['r']:+.3f}; {r['rows']:,} rows")
    print("\nThe largest cells that don't pass:")
    for r in t.filter(~c("passes")).sort("share", descending=True).head(8).iter_rows(named=True):
        print(f"  [{r['level']}] {r['a']}  <-  {r['b']}: {r['share']:+.3%} ({r['lo']:+.3%} to {r['hi']:+.3%}); copies max {r['copy_max']:+.3%}; fdr {r['fdr']}")
    print("\nRecalibration alone, per forecast (share of its squared error removed by a walk-forward a + b x its own forecast):")
    for a, g in t.group_by("a"):
        print(f"  {a[0]}: {g['recal'].median():+.3%}")
    t.write_csv("projects/retro/explore/retro4_i146_miss_matrix.csv")


if __name__ == "__main__":
    main()
