"""The CEO's H15, a little further (2026-11-09, discovery only). Reads the option tables that
`restricted.py` caches in interim/schemes_v2/h15/ (each play's usual choice from the league model,
and EPA residuals; defenses' EPA is flipped to EPA prevented).

1. **The anti-cluster (the CEO's framing).** Per regime, use over expected of each option, offense
   (pass, shotgun, no-huddle, heavy personnel; 2016+) and defense (man, two-high, blitz, 8+ box;
   2018+). Do avoidances go together? Correlations, principal components, and whether regime-level
   profiles form clusters at all (k-means silhouette against columns shuffled independently).
   Then the test: a regime's score on each component in one half of its games against its
   combined gap along the same component in the other half (the gaps weighted by the loadings),
   beside the best single option, with shuffled teams as the null.
2. **The box-count lead, in football units.** Against offenses that usually draw stacked boxes
   (the top fifth by the opponent's part of the expected 8+ box rate), defenses that avoid stacking
   (the bottom fifth of use over expected, other half) against the rest: EPA allowed per run and
   per dropback, beyond the situation, as a difference in differences, bootstrapped over defenses.
3. **Before kickoff (point in time).** Avoidance from the regime's earlier games only (3+), as a
   feature would see it: does it predict the gap in this game (within team-game), and the loss on
   plays where the option is favored? Null: prior avoidance shuffled across teams in the same week.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/anticlusters.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from restricted import OUT, option_table, perm_within, plays, unit_halves
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

c = pl.col
RNG = np.random.default_rng(202611092)
SHUFFLES = 200
CACHE = OUT / "h15"
GROUPS = {"offense": ["pass", "shotgun", "no_huddle", "heavy"], "defense": ["man", "two_high", "blitz", "box8"]}


def load(name: str) -> pl.DataFrame:
    f = CACHE / f"{name}.parquet"
    t = pl.read_parquet(f)
    if "rush" not in t.columns and name == "box8":   # older cache: rebuild with play ids and the run flag
        t = option_table(plays(), name)
        t.write_parquet(f)
    return t


def r_stack(xa, yb, xb, ya, season):
    x = np.concatenate([xa, xb])
    y = np.concatenate([yb, ya])
    g = np.concatenate([season, season])
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y, g = x[ok], y[ok], g[ok]
    r = float(np.corrcoef(x, y)[0, 1])
    null = np.array([np.corrcoef(x[perm_within(g)], y)[0, 1] for _ in range(SHUFFLES)])
    return r, float(np.mean(null >= r)), int(ok.sum() // 2)


def part1() -> None:
    print("== 1. The anti-cluster: do avoidances go together?")
    for side, opts in GROUPS.items():
        u = None
        for o in opts:
            h = unit_halves(load(o)).select("unit", "season", *[c(k).alias(f"{k}_{o}") for k in ("use_oe", "use_oe_b", "gap", "gap_b")])
            u = h if u is None else u.join(h.drop("season"), on="unit", how="inner")
        whole = np.column_stack([(u[f"use_oe_{o}"].to_numpy() + u[f"use_oe_b_{o}"].to_numpy()) / 2 for o in opts])
        mu, sd = whole.mean(0), whole.std(0)
        Z = (whole - mu) / sd
        print(f"\n{side}: {u.height} regimes with every option; correlations of use over expected (whole regime):")
        cm = np.corrcoef(Z.T)
        print("            " + " ".join(f"{o:>9}" for o in opts))
        for i, o in enumerate(opts):
            print(f"  {o:<9} " + " ".join(f"{cm[i, j]:>+9.2f}" for j in range(len(opts))))
        _, s, vt = np.linalg.svd(Z, full_matrices=False)
        share = s**2 / (s**2).sum()
        for k in range(2):
            load_k = vt[k] * np.sign(vt[k][np.argmax(np.abs(vt[k]))])
            print(f"  component {k + 1}: {share[k]:.0%} of the spread; loadings " + ", ".join(f"{o} {w:+.2f}" for o, w in zip(opts, load_k, strict=True)))
            za = ((np.column_stack([u[f"use_oe_{o}"].to_numpy() for o in opts]) - mu) / sd) @ load_k
            zb = ((np.column_stack([u[f"use_oe_b_{o}"].to_numpy() for o in opts]) - mu) / sd) @ load_k
            ga = np.column_stack([u[f"gap_{o}"].to_numpy() for o in opts]) @ load_k
            gb = np.column_stack([u[f"gap_b_{o}"].to_numpy() for o in opts]) @ load_k
            r, p, n = r_stack(za, gb, zb, ga, u["season"].to_numpy())
            print(f"    score (one half) against combined gap along it (other half): r {r:+.3f}, shuffled at or above {p:.0%}, regimes {n}")
        for o in opts:
            r, p, n = r_stack(u[f"use_oe_{o}"].to_numpy(), u[f"gap_b_{o}"].to_numpy(), u[f"use_oe_b_{o}"].to_numpy(), u[f"gap_{o}"].to_numpy(), u["season"].to_numpy())
            print(f"    single option {o:<9}: r {r:+.3f}, shuffled at or above {p:.0%} (same regimes, {n})")
        sil = {k: silhouette_score(Z, KMeans(k, n_init=10, random_state=0).fit_predict(Z)) for k in (3, 4, 5, 6)}
        null = []
        for _ in range(30):
            Zs = np.column_stack([RNG.permutation(Z[:, j]) for j in range(Z.shape[1])])
            null.append(silhouette_score(Zs, KMeans(5, n_init=10, random_state=0).fit_predict(Zs)))
        print("  regime-level clusters, silhouette: " + ", ".join(f"k={k} {v:.3f}" for k, v in sil.items())
              + f"; columns shuffled independently (k=5): {np.mean(null):.3f} (95th {np.quantile(null, 0.95):.3f})")


def part2() -> None:
    print("\n== 2. The box-count lead: defenses that avoid 8+ boxes, against offenses that usually draw them")
    t = load("box8")
    u = unit_halves(t)
    av = pl.concat([u.select("unit", half=pl.lit(1, pl.Int64), use=c("use_oe")), u.select("unit", half=pl.lit(0, pl.Int64), use=c("use_oe_b"))])
    d = t.with_columns(c("half").cast(pl.Int64)).join(av, on=["unit", "half"], how="inner")
    d = d.with_columns(draw=c("exp_opp").mean().over("game_id", "posteam"))
    gd = d.group_by("game_id", "posteam").agg(c("draw").first())
    cut = gd["draw"].quantile(0.8)
    lo_use = d.group_by("unit", "half").agg(c("use").first())["use"].quantile(0.2)
    d = d.with_columns(drawer=c("draw") >= cut, avoider=c("use") <= lo_use, allowed=-c("r0"))
    for lab, rows in (("runs", c("rush") == 1), ("dropbacks", c("rush") == 0)):
        s = d.filter(rows)
        tab = s.group_by("avoider", "drawer").agg(epa=c("allowed").mean(), n=pl.len(), box8=c("choice").mean()).sort("avoider", "drawer")
        cell = {(r["avoider"], r["drawer"]): r for r in tab.iter_rows(named=True)}

        def did(frame: pl.DataFrame) -> float:
            m = frame.group_by("avoider", "drawer").agg(c("allowed").mean())
            v = {(r["avoider"], r["drawer"]): r["allowed"] for r in m.iter_rows(named=True)}
            return (v[(True, True)] - v[(True, False)]) - (v[(False, True)] - v[(False, False)])

        est = did(s)
        units = s["unit"].unique().to_numpy()
        parts = s.partition_by("unit", as_dict=True)
        bs = []
        for _ in range(300):
            pick = RNG.choice(units, len(units))
            bs.append(did(pl.concat([parts[(k,)] for k in pick])))
        print(f"  {lab}: EPA allowed per play beyond the situation (8+ box rate)")
        for a in (True, False):
            who = "avoiders" if a else "the rest"
            print(f"    {who:<9} vs box-drawing offenses {cell[(a, True)]['epa']:+.3f} ({cell[(a, True)]['box8']:.0%} stacked, {cell[(a, True)]['n']:,} plays); "
                  f"vs others {cell[(a, False)]['epa']:+.3f} ({cell[(a, False)]['box8']:.0%}, {cell[(a, False)]['n']:,})")
        print(f"    difference in differences: {est:+.3f} EPA per play (90% {np.quantile(bs, 0.05):+.3f} to {np.quantile(bs, 0.95):+.3f})")


def part3() -> None:
    print("\n== 3. Before kickoff: avoidance from the regime's earlier games only (3+)")
    print(f"{'option':<10} {'gap per sd prior use':>21} {'shuf>=':>7} {'favored loss per sd':>20} {'shuf<=':>7} {'team-games':>11}")
    for o in [*GROUPS["offense"], "deep", *GROUPS["defense"]]:
        t = load(o).with_columns(tg=pl.concat_str(c("game_id"), c("team")))
        g = (t.group_by("unit", "game_id", "tg", "season").agg(s=(c("choice") - c("exp")).sum(), n=pl.len())
             .with_columns(wk=c("game_id").str.slice(5, 2).cast(pl.Int32)).sort("unit", "game_id")
             .with_columns(k=pl.int_range(pl.len()).over("unit"), cs=c("s").cum_sum().over("unit") - c("s"), cn=c("n").cum_sum().over("unit") - c("n"))
             .filter(c("k") >= 3).with_columns(prior=c("cs") / c("cn")))
        g = g.with_columns(z=(c("prior") - c("prior").mean().over("season")) / c("prior").std().over("season")).with_row_index("gi")
        d = t.join(g.select("tg", "gi", "z"), on="tg", how="inner").with_columns(
            y1=c("r1") - c("r1").mean().over("tg"), ch=c("choice") - c("choice").mean().over("tg"),
            y0=c("r0") - c("r0").mean().over("tg"), f=c("exp") - c("exp").mean().over("tg"))
        y1, ch, y0, f, gi = (d[k].to_numpy() for k in ("y1", "ch", "y0", "f", "gi"))
        z = g["z"].to_numpy()

        def coefs(zg, gi=gi, ch=ch, y1=y1, f=f, y0=y0):
            zp = zg[gi]
            b1 = np.linalg.lstsq(np.column_stack([ch, ch * zp]), y1, rcond=None)[0][1]
            b0 = np.linalg.lstsq(np.column_stack([f, f * zp]), y0, rcond=None)[0][1]
            return b1, b0

        b1, b0 = coefs(z)
        keys = (g["season"] * 100 + g["wk"]).to_numpy()
        null = np.array([coefs(z[perm_within(keys)]) for _ in range(SHUFFLES)])
        loss = -b0 * f.std()   # per sd of avoidance (= minus use)
        print(f"{o:<10} {b1:>+21.4f} {np.mean(null[:, 0] >= b1):>7.0%} {loss:>+20.4f} {np.mean(null[:, 1] >= b0):>7.0%} {g.height:>11,}")
    print("  gap per sd prior use: EPA per play, choosing less not choosing, within the team-game (H15: positive).")
    print("  favored loss per sd: EPA per play per sd of avoidance (prior) per sd of the expected choice, all plays (H15: negative).")


def main() -> None:
    part1()
    part2()
    part3()


if __name__ == "__main__":
    main()
