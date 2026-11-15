"""snap-leverage spot-check (the CEO's pick, 2026-11-14: "R2: the seeds"). Does the no-noise verdict
(leverage share adds noise to plain snap share, next 3 games' snap share) depend on the trees'
random seed?

The retired variants are loaded from commit 892d39c (decision 0034). One pass of the build's
features and targets (2019-2024), then the build's own walk-forward (refit each season, scored
2020-2024):
1. What the seed changes: the trees stop early on a random tenth of each training window, so the
   number of trees each fit keeps, per season, rung and seed.
2. Each seed's difference by season (squared error, % of plain's; + = worse).
3. The seed-free alternative: no early stopping (all 250 trees), the same every run.
4. The five seeds' forecasts averaged per rung (most of the seed noise cancels).
5. An interval with both kinds of luck: each draw picks a random seed and resamples weeks.
Writes spot_check_seeds.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/spot_check_seeds.py
"""

# ruff: noqa: E501
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import polars as pl

from pcf.data.gateway import for_expert
from pcf.validation import backtest as B
from pcf.validation.splits import steps

c = pl.col
HERE = Path(__file__).parent
COMMIT = "892d39c"
SEEDS = (0, 1, 2, 3, 4)
K = ["gsis_id", "game_id"]
RUNGS = ("plain", "lev", "full")


def retired():
    """The retired features and model modules, from git, with their imports pointed at
    `pcf.data.usage` and each other."""
    tmp = Path(tempfile.mkdtemp())
    for name in ("features", "model"):
        src = subprocess.run(["git", "show", f"{COMMIT}:pcf/src/pcf/experts/snap_leverage/{name}.py"],
                             capture_output=True, text=True, encoding="utf-8", check=True).stdout
        src = src.replace("from pcf.experts.snap_leverage import usage as U", "from pcf.data import usage as U")
        src = src.replace("from pcf.experts.snap_leverage import features as F", "import snaplev_features as F")
        (tmp / f"snaplev_{name}.py").write_text(src, encoding="utf-8")
    sys.path.insert(0, str(tmp))
    mods = {}
    for name in ("features", "model"):
        spec = importlib.util.spec_from_file_location(f"snaplev_{name}", tmp / f"snaplev_{name}.py")
        mods[name] = importlib.util.module_from_spec(spec)
        sys.modules[f"snaplev_{name}"] = mods[name]
        spec.loader.exec_module(mods[name])
    return mods["model"]


def errors(p: pl.DataFrame, y: pl.DataFrame) -> pl.DataFrame:
    return p.join(y.select(*K, "y"), on=K).select(*K, "as_of", "mean", se=(c("y") - c("mean")) ** 2)


def pct(a: pl.DataFrame, b: pl.DataFrame) -> float:
    j = a.select(*K, "se").join(b.select(*K, sb="se"), on=K)
    return 100 * (j["sb"].sum() / j["se"].sum() - 1)


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    M = retired()
    plain = M.VARIANTS["snap_next3_plain"]()
    gw = for_expert(plain)
    every = steps(gw.calendar, plain.cadence, range(2019, 2025), plain.run, None)
    test = [s.index for s in every if s.season >= 2020]
    first_step = {}
    for s in every:
        if s.season >= 2020 and s.season not in first_step:
            first_step[s.season] = s
    feats = B.feature_history(plain, gw, every)
    y = B.targets(plain, gw)
    pool = feats.join(y, on=K, how="inner")
    say(f"Snap share, next 3 games: {feats.height:,} feature rows, scored 2020-2024")

    # 1. trees kept per fit
    say("")
    say("1. Trees kept by early stopping (of 250), the season's fit, per seed:")
    say("   season | rung  | seeds 0-4")
    for season, st in first_step.items():
        for r in ("plain", "lev"):
            e = M.VARIANTS[f"snap_next3_{r}"]()
            kept = []
            for seed in SEEDS:
                M.TREES["random_state"] = seed
                model, _ = B.fit_at(e, pool, st.at, season)
                kept.append(model["trees"].n_iter_)
            say(f"   {season}   | {r:5s} | {kept}")
    M.TREES["random_state"] = 0

    # 2. per seed and season
    runs: dict[tuple[str, object], pl.DataFrame] = {}
    for seed in SEEDS:
        M.TREES["random_state"] = seed
        for r in RUNGS:
            runs[(r, seed)] = errors(B.walk(M.VARIANTS[f"snap_next3_{r}"](), feats, y, every, test, refit="season"), y)
    M.TREES["random_state"] = 0
    say("")
    say("2. Leverage share against plain, squared error, % of plain's (+ = worse), by seed and season:")
    say("   seed | all     | 2020    | 2021    | 2022    | 2023    | 2024")
    season_of = c("game_id").str.slice(0, 4)
    for seed in SEEDS:
        a, b = runs[("plain", seed)], runs[("lev", seed)]
        row = [f"{pct(a, b):+.3f}%"]
        for s in ("2020", "2021", "2022", "2023", "2024"):
            row.append(f"{pct(a.filter(season_of == s), b.filter(season_of == s)):+.3f}%")
        say(f"   {seed:4d} | " + " | ".join(row))

    # 3. seed-free: no early stopping
    say("")
    say("3. No early stopping (all 250 trees; no seed in the fit at all):")
    M.TREES["early_stopping"] = False
    free = {r: errors(B.walk(M.VARIANTS[f"snap_next3_{r}"](), feats, y, every, test, refit="season"), y) for r in RUNGS}
    again = errors(B.walk(M.VARIANTS["snap_next3_lev"](), feats, y, every, test, refit="season"), y)
    del M.TREES["early_stopping"]
    same = free["lev"].select(*K, "mean").join(again.select(*K, m2="mean"), on=K)
    say(f"   repeat run identical: {bool((same['mean'] == same['m2']).all())}")
    for r in ("lev", "full"):
        say(f"   {r:4s} vs plain: squared error {pct(free['plain'], free[r]):+.3f}%")
    say(f"   plain without early stopping vs with it (seed 0): {pct(runs[('plain', 0)], free['plain']):+.3f}%")

    # 4. the five seeds averaged
    say("")
    say("4. The five seeds' forecasts averaged, per rung:")
    avg = {}
    for r in RUNGS:
        m = pl.concat([runs[(r, s)].select(*K, "as_of", "mean") for s in SEEDS]).group_by(K).agg(c("as_of").first(), c("mean").mean())
        avg[r] = errors(m, y)
    for r in ("lev", "full"):
        say(f"   {r:4s} vs plain: squared error {pct(avg['plain'], avg[r]):+.3f}%")

    # 5. an interval with both kinds of luck
    say("")
    say("5. Leverage share against plain, squared error, 90% interval resampling weeks and the seed together:")
    wk = {s: runs[("plain", s)].select(*K, "as_of", "se").join(runs[("lev", s)].select(*K, sb="se"), on=K)
          .with_columns(wk=c("as_of").dt.strftime("%Y-%m-%d")).group_by("wk").agg(c("se").sum(), c("sb").sum()).sort("wk")
          for s in SEEDS}
    weeks = wk[0]["wk"].to_list()
    arr = {s: (wk[s]["se"].to_numpy(), wk[s]["sb"].to_numpy()) for s in SEEDS}
    rng = np.random.default_rng(0)
    draws = []
    for _ in range(4000):
        s = SEEDS[rng.integers(len(SEEDS))]
        i = rng.integers(0, len(weeks), len(weeks))
        a, b = arr[s]
        draws.append(100 * (b[i].sum() / a[i].sum() - 1))
    lo, hi = np.percentile(draws, [5, 95])
    say(f"   {np.mean(draws):+.3f}% (90% {lo:+.3f} to {hi:+.3f}); share of draws where leverage share helps: {np.mean(np.array(draws) < 0):.1%}")
    (HERE / "spot_check_seeds.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
