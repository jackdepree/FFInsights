"""Scheme against scheme, option D (CEO, 2026-11-09): the wide scan, run as the tempting-but-bad option.

It looks thorough: try every pairing in every shape and keep what lights up. The expectation
(stated before running): the more terms tried, the bigger a real effect must be to stand out, so
the scan finds "winners" in-sample that vanish on held-out seasons. Run as a test, not argued.

Rows: F7's sides (offense against defense, weeks 4+, 2006-2024; each tendency from the regime's
earlier games; the residual is EPA per play beyond both units' season-to-date strength).
1. **Wide pair scan:** each of F7's 77 offense × defense tendency pairs in 4 shapes: the product, and
   three corner indicators (both high, offense high and defense low, offense low and defense high;
   high = above +0.5 sd, low = below -0.5 sd). 308 terms, each with both main effects. The largest |t|
   against the same with defenses shuffled within the week (100 times).
2. **The selection trap:** on even seasons, keep the 20 terms with the largest |t|, fit them together;
   r on even seasons (in-sample) and on odd seasons (held out), and the reverse.
3. **More clusters:** k = 3 to 10 offense and defense clusters (2016-2024, every tendency); the
   offense × defense cell means beyond both mains, from even seasons predicting odd and the reverse.
4. **Throw everything in trees:** gradient-boosted trees on every tendency of both sides; r
   in-sample and held out (even/odd seasons), and with shuffled defenses.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/wide.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from conditions import DEF, OFF, ols_t, shuffled, sides
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingRegressor

c = pl.col
RNG = np.random.default_rng(20261114)
SHUFFLES = 100
TOP = 20


def terms(
    s: pl.DataFrame, dz: dict[str, np.ndarray]
) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    out = {}
    for a in OFF:
        za = s[f"z_{a}"].to_numpy()
        for d in DEF:
            zd = dz[d]
            out[f"{a}×{d}"] = (za, zd, za * zd)
            out[f"{a}↑{d}↑"] = (za, zd, ((za > 0.5) & (zd > 0.5)).astype(float))
            out[f"{a}↑{d}↓"] = (za, zd, ((za > 0.5) & (zd < -0.5)).astype(float))
            out[f"{a}↓{d}↑"] = (za, zd, ((za < -0.5) & (zd > 0.5)).astype(float))
    return out


def scan(y, tm, rows=None):
    res = {}
    for name, (za, zd, x) in tm.items():
        ok = ~(np.isnan(za) | np.isnan(zd) | np.isnan(y))
        if rows is not None:
            ok &= rows
        if ok.sum() < 500 or x[ok].std() == 0:
            continue
        b, t = ols_t(y[ok], [np.nan_to_num(za[ok]), np.nan_to_num(zd[ok]), x[ok]])
        res[name] = (b[3], t[3])
    return res


def selection_trap(y, tm, season, label):
    out = []
    for fold in (0, 1):
        tr, te = season % 2 == fold, season % 2 != fold
        sc = scan(y, tm, tr)
        top = sorted(sc, key=lambda k: -abs(sc[k][1]))[:TOP]
        X = np.column_stack(
            [np.ones(len(y))]
            + [np.nan_to_num(tm[k][2]) for k in top]
            + [np.nan_to_num(tm[k][0]) for k in top]
            + [np.nan_to_num(tm[k][1]) for k in top]
        )
        ok = ~np.isnan(y)
        b = np.linalg.lstsq(X[tr & ok], y[tr & ok], rcond=None)[0]
        inter = X[:, 1 : 1 + TOP] @ b[1 : 1 + TOP]
        out.append(
            (
                np.corrcoef(inter[tr & ok], y[tr & ok])[0, 1],
                np.corrcoef(inter[te & ok], y[te & ok])[0, 1],
                top[:5],
            )
        )
    if label:
        for k, (ins, held, top) in enumerate(out):
            print(
                f"   picked on {'even' if k == 0 else 'odd'} seasons: in-sample r {ins:+.3f} → held out r {held:+.3f}; top picks {', '.join(top)}"
            )
    return np.mean([o[0] for o in out]), np.mean([o[1] for o in out])


def main() -> None:
    s = sides()
    y = s["resid"].to_numpy()
    season = s["season"].to_numpy()
    real = {d: s[f"z_{d}"].to_numpy() for d in DEF}
    tm = terms(s, real)

    print(f"\n== 1. Wide pair scan: {len(tm)} terms (77 pairs × 4 shapes)")
    sc = scan(y, tm)
    null_max = []
    null_trap = []
    for _ in range(SHUFFLES):
        tz = terms(s, shuffled(s))
        ns = scan(y, tz)
        null_max.append(max(abs(v[1]) for v in ns.values()))
        null_trap.append(selection_trap(y, tz, season, False))
    null_max, null_trap = np.array(null_max), np.array(null_trap)
    top = sorted(sc.items(), key=lambda kv: -abs(kv[1][1]))
    cut = np.quantile(null_max, 0.95)
    print(
        f"   tested {len(sc)}; largest |t| {abs(top[0][1][1]):.2f} ({top[0][0]}); shuffled defenses: 95th percentile of the largest |t| {cut:.2f}"
    )
    print(
        f"   real terms above that bar: {sum(abs(v[1]) > cut for v in sc.values())}; above |t| 2: {sum(abs(v[1]) > 2 for v in sc.values())} (chance ≈ {0.0455 * len(sc):.0f})"
    )
    for name, (b, t) in top[:8]:
        print(f"      {name:<30} {b:+.4f}  t {t:+.1f}")

    print(
        f"\n== 2. The selection trap: keep the top {TOP} terms on one half of the seasons, test on the other"
    )
    ins, held = selection_trap(y, tm, season, True)
    print(
        f"   average: in-sample r {ins:+.3f}, held out {held:+.3f}; shuffled defenses: in-sample {null_trap[:, 0].mean():+.3f}, held out {null_trap[:, 1].mean():+.3f} "
        f"(held out at or above the real: {np.mean(null_trap[:, 1] >= held):.0%})"
    )

    print(
        "\n== 3. More clusters (2016-2024, every tendency): offense × defense cells beyond both mains, even seasons predicting odd and the reverse"
    )
    q = (
        s.filter(c("season") >= 2016)
        .drop_nulls([f"z_{m}" for m in OFF + DEF])
        .drop_nans([f"z_{m}" for m in OFF + DEF])
    )
    yq = q["resid"].to_numpy()
    sq = q["season"].to_numpy()
    XO = q.select([f"z_{m}" for m in OFF]).to_numpy()
    XD = q.select([f"z_{m}" for m in DEF]).to_numpy()

    def cell_r(oc, dc, k):
        pred = np.zeros(len(yq))
        for fold in (0, 1):
            tr, te = sq % 2 == fold, sq % 2 != fold
            X = np.column_stack(
                [np.ones(len(yq))]
                + [(oc == i) * 1.0 for i in range(1, k)]
                + [(dc == j) * 1.0 for j in range(1, k)]
            )
            e = yq - X @ np.linalg.lstsq(X[tr], yq[tr], rcond=None)[0]
            for i in range(k):
                for j in range(k):
                    w = (oc == i) & (dc == j)
                    if (w & tr).sum() >= 10:
                        pred[w & te] = e[w & tr].mean()
        return float(np.corrcoef(pred, yq)[0, 1])

    for k in range(3, 11):
        oc = KMeans(k, n_init=10, random_state=0).fit_predict(XO)
        dc = KMeans(k, n_init=10, random_state=0).fit_predict(XD)
        rr = cell_r(oc, dc, k)
        nul = np.array([cell_r(oc, RNG.permutation(dc), k) for _ in range(SHUFFLES)])
        print(
            f"   k {k:>2} ({k * k} cells, about {len(yq) // (k * k)} sides each): held-out r {rr:+.3f}; shuffled clusters at or above {np.mean(nul >= rr):.0%}"
        )

    print("\n== 4. Throw everything in trees: boosted trees on all 18 tendencies of both sides")

    def trees(dz):
        X = np.column_stack([s[f"z_{a}"].to_numpy() for a in OFF] + [dz[d] for d in DEF])
        ok = ~np.isnan(y)
        ins, held = [], []
        for fold in (0, 1):
            tr, te = (season % 2 == fold) & ok, (season % 2 != fold) & ok
            m = HistGradientBoostingRegressor(
                max_iter=300, learning_rate=0.05, max_depth=4, random_state=0
            ).fit(X[tr], y[tr])
            ins.append(np.corrcoef(m.predict(X[tr]), y[tr])[0, 1])
            held.append(np.corrcoef(m.predict(X[te]), y[te])[0, 1])
        return np.mean(ins), np.mean(held)

    ins, held = trees(real)
    nt = np.array([trees(shuffled(s)) for _ in range(20)])
    print(
        f"   in-sample r {ins:+.3f} → held out {held:+.3f}; shuffled defenses (20): in-sample {nt[:, 0].mean():+.3f}, held out {nt[:, 1].mean():+.3f}, held out at or above the real: {np.mean(nt[:, 1] >= held):.0%}"
    )
    print(
        "   (the trees also see each side's main effects, which F6 found near zero beyond strength except shotgun)"
    )


if __name__ == "__main__":
    main()
