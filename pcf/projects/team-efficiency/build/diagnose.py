"""team-efficiency build: why did the combination's gain over all plays equal shrink from the
exploration (+0.6% next 3, +1.4% rest; explore/combo.txt) to the build (-0.1%, +0.5%)?

The build's ratings are fed through the exploration's own scoring (explore/common.py: ratings
before week w from earlier weeks only, a forecast map fit once on 2007-2015, skill on
2016-2024), so the scoring is held fixed and one build difference is switched at a time:

- **A, the exploration's own ratings** (cached): must reproduce combo.txt.
- **B, the build's ratings** as built.
- **B + the polars fold**: the cross-fitting halves from `hash(7) % 2`, as the exploration.
- **B + the 2006-2024 scale**: the prior's unit is the mean plays per team-game over every season.
- **B + fixed models**: the gap and outcome models and the weights fit once on 2006-2015 and used
  for every season, as the exploration (the build refits them each season on the 10 before).
- **Split luck** (`folds`): the combination under 8 other cross-fitting halves (CRC-32 of the game
  id with a salt). They all agree, because CRC-32 is linear: its last bit is a parity of the
  id's bits, so a salt only flips the halves. `seeds`: four real random splits (polars hashes).
- **The fix** (`fix`): halves from blake2b; then also the 2006-2015 models for 2017-2024 only, so
  the fixed models are tested out of sample (the exploration's were in sample for 2006-2015).

Stages: `main models folds` by default; `seeds` and `fix` on request (each run appends).
- **Scoring, the harness's way**: the build's ratings with the map refit each season on the
  seasons before it (recency half-life 4 seasons), instead of once on 2007-2015.

Writes diagnose.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/team-efficiency/build/diagnose.py
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import sys
import zlib
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.tables import efficiency as E
from pcf.data.tables.store import load
from pcf.experts.team_efficiency import ratings as R

HERE = Path(__file__).parent
B = importlib.import_module("pcf.data.tables.build")  # the package also exports a function `build`
sys.path.insert(0, str(HERE.parent / "explore"))
import common as C  # noqa: E402

c = pl.col
CACHE = get_config().zone("interim") / "team-efficiency"
FAR = datetime(2100, 1, 1)
NAMES = ("ridge", "combo")


def build_ratings(tg: pl.DataFrame, measures: dict[str, R.Measure]) -> dict[str, pl.DataFrame]:
    """The build's walk, at the exploration's moments: before week w, from earlier weeks only
    (reference week w), every season 2006-2024. One frame per measure: season, week, team, o, d."""
    R._FINALS.clear()  # its key holds the settings and rows, not the scale
    names = R.teams(tg)
    x = R.prepare(tg, names)
    out = {}
    for n, m in measures.items():
        frames = []
        walks = {s: R.Walk(x, m, s, len(names)) for s in ("off", "def")}
        for season in C.SEASONS:
            rows_s = {s: w.by_season[season][1] for s, w in walks.items()}
            priors = {s: w.prior(season, FAR) for s, w in walks.items()}
            last = int(rows_s["off"][:, 0].max())
            for wk in range(1, last + 1):
                o = R._fit(m, rows_s["off"][rows_s["off"][:, 0] < wk], float(wk), *priors["off"],
                           walks["off"].s)[0]  # fmt: skip
                d = R._fit(m, rows_s["def"][rows_s["def"][:, 0] < wk], float(wk), *priors["def"],
                           walks["def"].s)[1]  # fmt: skip
                frames.append(pl.DataFrame({"season": season, "week": wk, "team": names, "o": o, "d": d}))
        out[n] = pl.concat(frames).with_columns(c("season").cast(pl.Int32), c("week").cast(pl.Int32))
    return out


def fixed_models_part(tg: pl.DataFrame, seasons=None) -> pl.DataFrame:
    """tg with `seasons`' efficiency columns (default: every season in the part) rebuilt from the
    models fit on 2006-2015; other seasons keep their walk-forward models."""
    have = B.local_seasons("pbp")
    models = E.models_for(2016, have, B._efficiency_plays, CACHE / "models")
    if seasons is None:
        seasons = sorted(tg.filter(c("efficiency_known_at").is_not_null())["season"].unique())
    seasons = list(seasons)
    rows = pl.concat(
        E.efficiency_rows(E.apply_models(B._efficiency_plays(s), models)) for s in seasons
    )
    cols = [k for k in rows.columns if k.startswith("eff_")]
    swap = tg.filter(c("season").is_in(seasons)).drop(cols)
    swap = swap.join(rows.select("game_id", "team", *cols), on=["game_id", "team"], how="left")
    return pl.concat([tg.filter(~c("season").is_in(seasons)), swap.select(tg.columns)])


def map_by_season(pf: pl.DataFrame, half_life: float = 4.0) -> pl.DataFrame:
    """The forecast map refit each scored season on every earlier season from 2007, recency
    weighted, as the harness does (a season-level stand-in for its weekly refit)."""
    outs = []
    for side in ("off", "def"):
        x = pf.filter(c("side") == side)
        for s in C.SCORE:
            tr = x.filter((c("season") >= 2007) & (c("season") < s)).drop_nulls(["own", "opp"])
            te = x.filter(c("season") == s)
            w = 0.5 ** ((s - 1 - tr["season"].to_numpy()) / half_life)
            X = np.column_stack([np.ones(tr.height), tr["own"], tr["opp"], tr["home"]])
            sw = np.sqrt(w)
            b = np.linalg.lstsq(X * sw[:, None], tr["y"].to_numpy() * sw, rcond=None)[0]
            Xt = np.column_stack([np.ones(te.height), te["own"], te["opp"], te["home"]])
            outs.append(te.with_columns(pred=pl.Series(Xt @ b)))
    return pl.concat(outs)


def main() -> None:
    lines = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    p = C.plays()
    sched = C.schedule()
    ufs = {h: C.unit_frame(C.team_games(p, sched), h) for h in ("next3", "rest")}
    del p

    def compare(label: str, combo: pl.DataFrame, ridge: pl.DataFrame, scorer=None) -> None:
        if scorer is None:
            a, b = C.score_ratings(combo, ufs), C.score_ratings(ridge, ufs)
        else:
            a = {h: scorer(C.predict_frame(combo, ufs[h])) for h in ufs}
            b = {h: scorer(C.predict_frame(ridge, ufs[h])) for h in ufs}
        parts = []
        for h in ("next3", "rest"):
            sk = C.skill(a[h], b[h])
            parts.append(f"{h} {C.fmt(sk)} (off {100 * C.skill(a[h], b[h], side='off')[0]:+.1f}%, "
                         f"def {100 * C.skill(a[h], b[h], side='def')[0]:+.1f}%)")  # fmt: skip
        say(f"{label:44s} | " + " | ".join(parts))

    stages = set(sys.argv[1:]) or {"main", "models", "folds"}
    tg = load("team_game", parts=["schedule", "efficiency"])
    ms = {n: R.MEASURES[n] for n in NAMES}
    say("The combination against all plays equal, on the exploration's scoring (2016-2024):")
    if "main" in stages:
        main_stages(tg, ms, compare, say)
    if "models" in stages:
        tgm = fixed_models_part(tg)
        bm = build_ratings(tgm, ms)
        compare("B + models fit once on 2006-2015", bm["combo"], bm["ridge"])
        old_fold = R.fold
        R.fold = lambda g: (g.hash(7) % 2).cast(pl.Int8)
        bm = build_ratings(tgm, ms)
        R.fold = old_fold
        compare("B + fixed models + the polars fold", bm["combo"], bm["ridge"])
    if "folds" in stages:
        ridge = build_ratings(tg, {"ridge": ms["ridge"]})["ridge"]
        old_fold = R.fold
        for salt in range(1, 9):
            R.fold = lambda g, k=salt: g.map_elements(
                lambda v: zlib.crc32(f"{v}#{k}".encode()) % 2, return_dtype=pl.Int8
            )
            bc = build_ratings(tg, {"combo": ms["combo"]})["combo"]
            compare(f"B, cross-fitting halves #{salt}", bc, ridge)
        R.fold = old_fold
    if "seeds" in stages:  # CRC-32 is linear, so its salted halves are one split; try real ones
        ridge = build_ratings(tg, {"ridge": ms["ridge"]})["ridge"]
        old_fold = R.fold
        for seed in (7, 1, 2, 3):
            R.fold = lambda g, s=seed: (g.hash(s) % 2).cast(pl.Int8)
            bc = build_ratings(tg, {"combo": ms["combo"]})["combo"]
            compare(f"B, polars hash({seed}) halves", bc, ridge)
        R.fold = old_fold
    if "fix" in stages:  # a proper hash; then the 2006-2015 models out of sample only
        old_fold = R.fold
        R.fold = lambda g: g.map_elements(
            lambda v: hashlib.blake2b(v.encode(), digest_size=8).digest()[0] % 2,
            return_dtype=pl.Int8,
        )
        b = build_ratings(tg, ms)
        compare("B, blake2b halves (the proposed fix)", b["combo"], b["ridge"])
        late = fixed_models_part(tg, range(2017, 2025))
        b = build_ratings(late, ms)
        compare("B, blake2b + 2006-2015 models for 2017-2024", b["combo"], b["ridge"])
        R.fold = old_fold
    out = HERE / "diagnose.txt"
    keep = [] if "main" in stages or not out.exists() else out.read_text("utf-8").splitlines()
    out.write_text("\n".join(keep + [ln for ln in lines if ln not in keep]), encoding="utf-8")


def main_stages(tg: pl.DataFrame, ms: dict, compare, say) -> None:
    ex = {"combo": pl.read_parquet(CACHE / "ratings_combo.parquet"),
          "ridge": pl.read_parquet(CACHE / "equal_ratings.parquet")}  # fmt: skip
    compare("A  the exploration's ratings", ex["combo"], ex["ridge"])
    b = build_ratings(tg, ms)
    compare("B  the build's ratings", b["combo"], b["ridge"])
    for n in NAMES:
        j = b[n].join(ex[n], on=["season", "week", "team"], suffix="_x").filter(c("season") >= 2016)
        say(f"   {n}: r with the exploration's, offense {j.select(pl.corr('o', 'o_x')).item():.3f}, "
            f"defense {j.select(pl.corr('d', 'd_x')).item():.3f}")  # fmt: skip
    compare("B, scored the harness's way (map per season)", b["combo"], b["ridge"], map_by_season)

    old_fold = R.fold  # prepare sets the fold; swap the exploration's in for one run
    R.fold = lambda g: (g.hash(7) % 2).cast(pl.Int8)
    bf = build_ratings(tg, ms)
    R.fold = old_fold
    compare("B + the polars fold", bf["combo"], bf["ridge"])

    sizes = load("team_game", parts=["schedule", "efficiency"]).filter(
        (c("game_type") == "REG") & c("season").is_between(2006, 2024)
    )
    full = float(sizes["eff_plays"].mean())
    say(f"   scale: 2006-2015 {ms['ridge'].scale}, 2006-2024 {full:.1f}")
    bs = build_ratings(tg, {n: dataclasses.replace(m, scale=full) for n, m in ms.items()})
    compare("B + the 2006-2024 scale", bs["combo"], bs["ridge"])


if __name__ == "__main__":
    main()
