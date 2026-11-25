"""Availability build: the ladder's comparisons on the saved walks (BUILD.md A1-A12).

Every variant was walked 2017-2024 (refit each season, trained from 2016) by
`checks.walk` and saved in the build cache as hist_<variant>.parquet (walk_all in the build log).
This reads them and writes projects/availability/build/compare.txt.

Run from pcf/: <venv python> projects/availability/build/compare_run.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.experts.availability import checks as K

c = pl.col
OUT = Path(__file__).with_name("compare.txt")
lines: list[str] = []
KEYS = K.KEYS


def log(*parts) -> None:
    s = " ".join(str(p) for p in parts)
    print(s, flush=True)
    lines.append(s)


def h(v: str) -> pl.DataFrame:
    return pl.read_parquet(K.cache_dir() / f"hist_{v}.parquet").filter(c("y").is_not_null())


def vs(a: str, b: str, A: pl.DataFrame, B: pl.DataFrame, rows=None, loss="loss") -> None:
    if loss != "loss":
        A, B = A.with_columns(loss=c(loss)), B.with_columns(loss=c(loss))
    cmp = K.versus(A, B, (a, b), rows)
    base = B.join(A.select(KEYS), on=KEYS, how="semi")
    if rows is not None:
        base = base.join(rows.select(KEYS), on=KEYS, how="semi")
    log(f"  {a:>18} vs {b:<18} {K.pct(cmp, base['loss'].mean())}")


feats = pl.read_parquet(K.cache_dir() / "features.parquet").select(*KEYS, "status", "practice", "listed17", "proneness")

# ---------------------------------------------------------------- next game
log("NEXT GAME: the chance of a health absence (rows: the 53, not on a reserve list), 2017-2024")
log("Scores: log loss (decides); a positive % is the share of the second model's log loss the first removes, 90% interval by whole weeks")
N = {v: h(v) for v in ("next_table", "next_logit", "next_lasso", "next_trees")}
for v, d in N.items():
    p, y = d["mean"].to_numpy(), d["y"].to_numpy()
    log(f"  {v:<12} rows {d.height}  log loss {d['loss'].mean():.5f}  Brier {d['readable'].mean():.5f}  base rate {y.mean():.4f}  calibration error {K.calibration_error(p, y):.2f} pts  slope {K.calibration_slope(p, y):.3f}")
listed = N["next_table"].join(feats, on=KEYS).filter((c("status") > 0) | (c("practice") >= 1))
log(f"  listed rows: {listed.height} (absence rate {listed['y'].mean():.3f}); unlisted rows' absence rate {N['next_table'].join(listed.select(KEYS), on=KEYS, how='anti')['y'].mean():.5f}")
log("A1: method 1 against rung 0 (the status-by-body-part table)")
vs("next_logit", "next_table", N["next_logit"], N["next_table"])
vs("next_lasso", "next_table", N["next_lasso"], N["next_table"])
vs("next_lasso", "next_table", N["next_lasso"], N["next_table"], rows=listed)
log("the lasso against the plain logistic, and A2: trees against the lasso")
vs("next_lasso", "next_logit", N["next_lasso"], N["next_logit"])
vs("next_trees", "next_lasso", N["next_trees"], N["next_lasso"])
vs("next_trees", "next_lasso", N["next_trees"], N["next_lasso"], rows=listed)
for v in ("next_table", "next_lasso", "next_trees"):
    d = N[v].join(listed.select(KEYS), on=KEYS, how="semi")
    p, y = d["mean"].to_numpy(), d["y"].to_numpy()
    log(f"  listed rows, {v}: calibration error {K.calibration_error(p, y):.2f} pts, slope {K.calibration_slope(p, y):.3f}")
st = N["next_lasso"].join(feats, on=KEYS).filter(c("status") > 0).group_by("status").agg(
    n=pl.len(), predicted=c("mean").mean(), actual=c("y").mean()).sort("status")
log("  next_lasso by game status (1 Questionable, 2 Doubtful, 3 Out):")
for r in st.iter_rows(named=True):
    log(f"    status {r['status']}: rows {r['n']}, predicted {r['predicted']:.3f}, actual {r['actual']:.3f}")

# ---------------------------------------------------------------- active (test 1)
log("\nTEST 1: the chance he's active next game (QB/RB/WR/TE on the 53, participation's rows), 2017-2024")
A = {v: h(v) for v in ("active_part", "active_recal", "active_stack", "active_gated")}
for v, d in A.items():
    p, y = d["mean"].to_numpy(), d["y"].to_numpy()
    log(f"  {v:<13} rows {d.height}  log loss {d['loss'].mean():.5f}  Brier {d['readable'].mean():.5f}  calibration error {K.calibration_error(p, y):.2f} pts  slope {K.calibration_slope(p, y):.3f}")
log("A3: beside participation's active, against active alone; A4: against active recalibrated")
vs("active_stack", "active_part", A["active_stack"], A["active_part"])
vs("active_stack", "active_recal", A["active_stack"], A["active_recal"])
vs("active_recal", "active_part", A["active_recal"], A["active_part"])
vs("active_gated", "active_part", A["active_gated"], A["active_part"])
log("A5 (Questionable slope 0.85-1.15) and A6 (Out and Doubtful: predicted over actual active rate under 1.3)")
for v, d in A.items():
    j = d.join(feats, on=KEYS)
    q = j.filter(c("status") == 1)
    od = j.filter(c("status") >= 2)
    lst = j.filter((c("status") > 0) | (c("practice") >= 1))
    log(f"  {v:<13} Questionable rows {q.height}: slope {K.calibration_slope(q['mean'].to_numpy(), q['y'].to_numpy()):.3f}, predicted {q['mean'].mean():.3f} vs actual {q['y'].mean():.3f}"
        f" | Out/Doubtful rows {od.height}: predicted {od['mean'].mean():.3f} vs actual {od['y'].mean():.3f}, ratio {od['mean'].mean() / max(od['y'].mean(), 1e-9):.2f}"
        f" | listed rows {lst.height}: log loss {lst['loss'].mean():.4f}")
lst = A["active_part"].join(feats, on=KEYS).filter((c("status") > 0) | (c("practice") >= 1))
vs("active_stack", "active_part", A["active_stack"], A["active_part"], rows=lst)
vs("active_recal", "active_part", A["active_recal"], A["active_part"], rows=lst)

# ---------------------------------------------------------------- horizons
for hz in ("next3", "rest"):
    log(f"\n{hz.upper()}: games of health absence over {'the next 3 games' if hz == 'next3' else 'the rest of the season'} (rows: the 53 and the reserve lists), 2017-2024")
    log("Scores: the range score (average pinball loss over q10, q50, q90, in games; decides), the mean's squared error (readable), q10-q90 coverage and the share below q10")
    names = [f"{hz}_{m}" for m in ("table", "two", "chain", "chain_trees", "hmm")]
    H = {v: h(v) for v in names if (K.cache_dir() / f"hist_{v}.parquet").exists()}
    for v, d in H.items():
        d = d.with_columns(se=(c("mean") - c("y")) ** 2)
        cover = ((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()
        below = (c("y") < c("q10")).mean()
        above = (c("y") > c("q90")).mean()
        s = d.select(loss=c("loss").mean(), se=c("se").mean(), cover=cover, below=below, above=above, mean=c("mean").mean(), y=c("y").mean())
        r = s.row(0, named=True)
        log(f"  {v:<18} rows {d.height}  range score {r['loss']:.4f}  sq error {r['se']:.4f}  coverage {100 * r['cover']:.1f}%  below q10 {100 * r['below']:.1f}%  above q90 {100 * r['above']:.1f}%  mean {r['mean']:.3f} vs actual {r['y']:.3f}")
    log("A10/A11 and the ladder (range score)")
    pairs = [(f"{hz}_two", f"{hz}_table"), (f"{hz}_chain", f"{hz}_table"), (f"{hz}_chain", f"{hz}_two"),
             (f"{hz}_chain_trees", f"{hz}_chain"), (f"{hz}_hmm", f"{hz}_chain"), (f"{hz}_hmm", f"{hz}_two")]
    for a, b in pairs:
        if a in H and b in H:
            vs(a, b, H[a], H[b])
    log("  on the mean's squared error (readable):")
    for a, b in pairs:
        if a in H and b in H:
            vs(a, b, H[a].with_columns(se=(c("mean") - c("y")) ** 2), H[b].with_columns(se=(c("mean") - c("y")) ** 2), loss="se")
    if f"{hz}_chain" in H:
        d = H[f"{hz}_chain"].with_columns(se=(c("mean") - c("y")) ** 2)
        log("  the chain by state at the run (h healthy, l listed, o out/doubtful, r reserve):")
        for r in d.group_by("state").agg(n=pl.len(), loss=c("loss").mean(), mean=c("mean").mean(), y=c("y").mean(),
                                          cover=((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()).sort("state").iter_rows(named=True):
            log(f"    {r['state']}: rows {r['n']}, range score {r['loss']:.4f}, mean {r['mean']:.3f} vs actual {r['y']:.3f}, coverage {100 * r['cover']:.1f}%")

# ---------------------------------------------------------------- kept share (test 3)
log("\nTEST 3: kept share, his offensive snap share when he plays while listed (QB/RB/WR/TE), 2017-2024")
P = {v: h(v) for v in ("kept_part", "kept_model")}
for v, d in P.items():
    d = d.with_columns(se=(c("mean") - c("y")) ** 2)
    log(f"  {v:<11} rows {d.height}  squared error {d['se'].mean():.5f}  range score {d['loss'].mean():.5f}  mean {d['mean'].mean():.3f} vs actual {d['y'].mean():.3f}"
        f"  coverage {100 * d.select(((c('y') >= c('q10')) & (c('y') <= c('q90'))).mean()).item():.1f}%")
vs("kept_model", "kept_part", P["kept_model"].with_columns(se=(c("mean") - c("y")) ** 2), P["kept_part"].with_columns(se=(c("mean") - c("y")) ** 2), loss="se")
vs("kept_model", "kept_part", P["kept_model"], P["kept_part"])

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
