"""team-efficiency exploration, round two (2026-11-13), idea 3: combine the steady measures, with a
gate that changes by week.

A mixture of experts in miniature. Each measure is its own rating (the same ridge, settings tuned
on 2007-2015):
- EPA per play: the best EPA rating so far (F8's combination by default; `--epa <cache name>`);
- series success rate, success rate per play;
- EPA on passes only, EPA on runs only;
- this season only (no prior: pull 0) and the prior alone (last season's, as week 1 sees it).

The forecast is a ridge regression on each measure's own rating and its opponents' mean, per side.
**The gate**: every coefficient may differ by the part of the season (weeks 1-4, 5-9, 10+), so the
model can trust the prior early and the season's data late. The ridge strength is picked by leaving
one season out within 2007-2015; scored on 2016-2024.

**Compression**: principal components of the measures (fitted on 2007-2015): how many underlying
traits are there, and do the first one or two forecast as well as all of them?
Writes r2_stack.txt (or r2_stack_<epa>.txt).
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/explore/r2_stack.py [--epa ratings_combo_lf]
"""

# ruff: noqa: E501
from __future__ import annotations

import argparse
import itertools
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import common as C  # noqa: E402

c = pl.col
HERE = Path(__file__).parent
CACHE = C.get_config().zone("interim") / "team-efficiency"
LAMS = (0.0, 1.0, 10.0, 100.0, 300.0, 1000.0, 3000.0, 1e4, 3e4)
BUCKETS = ((1, 4), (5, 9), (10, 99))


def tuned(s: pl.DataFrame, sched, ufs, grid=C.GRID) -> pl.DataFrame:
    return C.tune(s, sched, ufs, grid)[1]["_ratings"]


def design(pf: pl.DataFrame, feats: list[str], gate: bool) -> np.ndarray:
    X = pf.select(feats).to_numpy().astype(float)
    if not gate:
        return X
    w = pf["w"].to_numpy()
    blocks = []
    for lo, hi in BUCKETS:
        m = ((w >= lo) & (w <= hi)).astype(float)[:, None]
        blocks += [m, X * m]
    return np.column_stack(blocks)


def ridge_fit(X, y, lam):
    """Ridge with an unpenalized intercept (X standardized beforehand)."""
    Xa = np.column_stack([np.ones(len(y)), X])
    pen = np.full(Xa.shape[1], lam)
    pen[0] = 0.0
    return np.linalg.solve(Xa.T @ Xa + np.diag(pen) + 1e-9 * np.eye(Xa.shape[1]), Xa.T @ y)


def stack_score(pf: pl.DataFrame, feats: list[str], gate: bool, pcs: int | None = None) -> tuple[pl.DataFrame, dict]:
    """Per side: standardize on TUNE, optional principal components per block (own, opp), ridge
    with lambda by leave-one-season-out on TUNE. Returns pf with pred, and the chosen lambdas."""
    outs, info = [], {}
    for side in ("off", "def"):
        x = pf.filter(c("side") == side).drop_nulls(feats)
        tr = x["season"].is_in(C.TUNE).to_numpy()
        Z = x.select(feats).to_numpy().astype(float)
        mu, sd = Z[tr].mean(0), Z[tr].std(0)
        Z = (Z - mu) / np.where(sd > 0, sd, 1)
        if pcs:
            cols = []
            for blk in ("own", "opp"):
                idx = [i for i, f in enumerate(feats) if f.startswith(blk)]
                B = Z[:, idx]
                _, sv, Vt = np.linalg.svd(B[tr] - B[tr].mean(0), full_matrices=False)
                cols.append(B @ Vt[:pcs].T)
                info[f"{side}_{blk}_var"] = np.round((sv**2 / (sv**2).sum())[:4], 2).tolist()
                info[f"{side}_{blk}_pc1"] = dict(zip([feats[i] for i in idx], np.round(Vt[0], 2)))
            hi = [i for i, f in enumerate(feats) if f == "home"]
            Z = np.column_stack(cols + [Z[:, hi]])
        xx = x.with_columns(*[pl.Series(f"z{i}", Z[:, i]) for i in range(Z.shape[1])])
        zf = [f"z{i}" for i in range(Z.shape[1])]
        X = design(xx, zf, gate)
        y = x["y"].to_numpy()
        seasons = x["season"].to_numpy()
        cv = {}
        for lam in LAMS:
            err = 0.0
            for s in C.TUNE:
                fit, te = tr & (seasons != s), seasons == s
                b = ridge_fit(X[fit], y[fit], lam)
                err += float(((y[te] - np.column_stack([np.ones(te.sum()), X[te]]) @ b) ** 2).sum())
            cv[lam] = err
        lam = min(cv, key=cv.get)
        info[f"{side}_lambda"] = lam
        b = ridge_fit(X[tr], y[tr], lam)
        Xa = np.column_stack([np.ones(len(y)), X])
        # Leave-one-season-out predictions on TUNE, for choices made on TUNE without in-sample
        # optimism (r2_gate.py); outside TUNE the same as pred.
        cvp = Xa @ b
        for s in C.TUNE:
            fit, te = tr & (seasons != s), seasons == s
            cvp[te] = Xa[te] @ ridge_fit(X[fit], y[fit], lam)
        outs.append(x.with_columns(pred=pl.Series(Xa @ b), pred_cv=pl.Series(cvp)))
    return pl.concat(outs), info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epa", default="ratings_combo")
    args = ap.parse_args()
    t0 = time.time()
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    p = C.plays()
    sched = C.schedule()
    tg = C.team_games(p, sched)
    ufs = {h: C.unit_frame(tg, h) for h in ("next3", "rest")}
    eq = {h: pl.read_parquet(CACHE / f"equal_{h}.parquet") for h in ("next3", "rest")}
    r_epa = pl.read_parquet(CACHE / f"{args.epa}.parquet")
    ref = C.score_ratings(r_epa, ufs)

    ser = p.group_by("game_id", "posteam", "series_key").agg(succ=c("series_success").first().cast(pl.Float64))
    rats = {
        "ssr": tuned(C.sides(ser, "succ"), sched, ufs),
        "sr": tuned(C.sides(p.with_columns(sv=c("success").cast(pl.Float64)), "sv"), sched, ufs),
        "pass": tuned(C.sides(p.filter(c("is_pass") == 1), "epa"), sched, ufs),
        "run": tuned(C.sides(p.filter(c("is_pass") == 0), "epa"), sched, ufs),
        "season": tuned(C.sides(p, "epa"), sched, ufs, [C.Params(h, l, 0.0) for h, l in itertools.product((4.0, 8.0, 16.0, 1000.0), (0.5, 1.0, 2.0, 5.0, 10.0))]),
    }
    er = pl.read_parquet(CACHE / "equal_ratings.parquet")
    rats["prior"] = er.filter(c("week") == 1).select("season", "team", "o", "d").join(er.select("season", "week", "team"), on=["season", "team"])
    say(f"Ratings walked ({time.time() - t0:.0f}s). EPA input: {args.epa}")

    names = list(rats)
    feats_all = ["own"] + [f"own_{n}" for n in names] + ["opp"] + [f"opp_{n}" for n in names] + ["home"]
    feats_epa = ["own", "opp", "home"]
    versions = {}
    for h in ("next3", "rest"):
        pf = C.predict_frame(r_epa, ufs[h], rats)
        versions[("gate only (EPA alone, by week)", h)] = stack_score(pf, feats_epa, True)
        versions[("stack, no gate", h)] = stack_score(pf, feats_all, False)
        versions[("stack + gate", h)] = stack_score(pf, feats_all, True)
        for k in (1, 2, 3):
            versions[(f"{k} principal component(s) per block + gate", h)] = stack_score(pf, feats_all, True, pcs=k)
    say("")
    say(f"The main test, 2016-2024: skill against the EPA rating alone ({args.epa}), then against all plays equal")
    for (nm, h), (out, info) in versions.items():
        say(f"  {h:5s} {nm:44s} {C.fmt(C.skill(out, ref[h]))} | vs all plays {C.fmt(C.skill(out, eq[h]))} | weeks 1-4 {C.fmt(C.skill(out.filter(c('w') <= 4), ref[h]))} | off {C.fmt(C.skill(out, ref[h], side='off'))} def {C.fmt(C.skill(out, ref[h], side='def'))} | lambda off {info['off_lambda']:g} def {info['def_lambda']:g}")
    say("")
    say("2020-2024 only, against the EPA rating alone:")
    for (nm, h), (out, _) in versions.items():
        say(f"  {h:5s} {nm:44s} {C.fmt(C.skill(out, ref[h], seasons=list(range(2020, 2025))))}")
    say("")
    say("Compression: share of the measures' spread per principal component (own block), and the first component's loadings (2007-2015):")
    _, info = versions[("1 principal component(s) per block + gate", "next3")]
    for side in ("off", "def"):
        say(f"  {side}: variance {info[f'{side}_own_var']}; first component {info[f'{side}_own_pc1']}")
    # Coefficients of the gated stack (next 3), to see what the gate learned.
    say("")
    say("Correlation of the measures' ratings with the EPA rating, offense, 2016-2024 end of week 9:")
    pf = C.predict_frame(r_epa, ufs["next3"], rats).filter((c("side") == "off") & (c("w") == 9) & c("season").is_in(C.SCORE))
    say("  " + "; ".join(f"{n} {np.corrcoef(pf['own'].to_numpy(), pf[f'own_{n}'].to_numpy())[0, 1]:.2f}" for n in names))
    say("")
    say(f"Versions tried in this step: {len(versions) // 2} stacks x 2 horizons")
    sfx = "" if args.epa == "ratings_combo" else f"_{args.epa.replace('ratings_', '')}"
    (HERE / f"r2_stack{sfx}.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
