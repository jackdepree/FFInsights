"""Schemes-v2 build, anti-traits (2026-11-09): does the anti-trait keep F18's sign on held-out
seasons? The brief's draft test: "the anti-trait term (avoidance × the play's usual choice) keeps
F18's sign on held-out seasons; the shuffled-team version shows nothing".

For each option (CEO: pass and shotgun on offense; man, two-high and blitz on defense), every
team-game in the test seasons with the option's features known before kickoff (exactly the
expert's, `pcf.experts.schemes_v2.anti_features`) and its gain in that game:
- the slope of the game's gain on the team's use (per sd of use), weighted by the gain's effective
  plays; positive means avoiders gain less (the anti-trait, F17-F18's sign);
- a 90% interval from 1,000 bootstrap resamples of team-seasons;
- each test season's own slope, and how many are positive;
- the null: use shuffled across teams within each prediction week, 200 times.
Nothing is fitted, so every season is held out: the use is known before the game, the gain after.
Also the same with `<o>_use_raw` (offense: without the opponents' part), to see whether the CEO's
"against that opponent" part matters.

Then the second test for the new per-game measures (`pcf.validation.consistency`): the gains and,
for defenses, the use over expected, regular season 2006-2024 (participation 2016+).

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/anti_sign.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.experts.schemes_v2 import anti_features as A
from pcf.experts.schemes_v2.anti_model import VARIANTS
from pcf.validation.backtest import test_seasons
from pcf.validation.consistency import consistency
from pcf.validation.splits import steps

c = pl.col
RNG = np.random.default_rng(20261109)
BOOT, SHUFFLES = 1000, 200


def rows(option: str, gw: Gateway) -> pl.DataFrame:
    ex = VARIANTS[f"{option}_gain_avoid"]()
    first = ex.first_train or 2015
    seasons = [s for s in test_seasons() if s > first]
    every = steps(gw.calendar, ex.cadence, seasons, ex.run)
    moments = pl.concat([s.games.with_columns(step=pl.lit(s.index)) for s in every])
    view = gw.view(END_OF_TIME, ex.cadence, ex.inputs)
    feats = A.history(view, moments.drop("step"), option).join(moments.select("game_id", "step"), on="game_id")
    tg = view.table("team_game").select(*A.F.KEYS, y=c(f"{option}_gain"), n=c(f"{option}_gain_n"))
    return feats.join(tg, on=A.F.KEYS).filter(c("y").is_not_null() & (c("n") > 0))


def slope(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    xm, ym = np.average(x, weights=w), np.average(y, weights=w)
    return float(np.sum(w * (x - xm) * (y - ym)) / np.sum(w * (x - xm) ** 2))


def test(df: pl.DataFrame, col: str) -> dict:
    x = df[col].to_numpy()
    x = (x - x.mean()) / x.std()
    y, w = df["y"].to_numpy(), df["n"].to_numpy()
    est = slope(x, y, w)
    cluster = (df["team"] + "_" + df["season"].cast(pl.String)).to_numpy()
    ids, inv = np.unique(cluster, return_inverse=True)
    members = [np.flatnonzero(inv == i) for i in range(len(ids))]
    boot = []
    for _ in range(BOOT):
        pick = np.concatenate([members[i] for i in RNG.integers(0, len(ids), len(ids))])
        boot.append(slope(x[pick], y[pick], w[pick]))
    step = df["step"].to_numpy()
    order = np.argsort(step, kind="stable")
    bounds = np.flatnonzero(np.diff(step[order])) + 1
    null = []
    for _ in range(SHUFFLES):
        xs = x.copy()
        for g in np.split(order, bounds):
            xs[g] = x[RNG.permutation(g)]
        null.append(slope(xs, y, w))
    null = np.abs(null)
    by_season = {}
    for s in sorted(df["season"].unique()):
        m = df["season"].to_numpy() == s
        by_season[s] = slope(x[m], y[m], w[m])
    return {
        "slope": est, "lo": float(np.quantile(boot, 0.05)), "hi": float(np.quantile(boot, 0.95)),
        "null95": float(np.quantile(null, 0.95)), "beats": int((null < abs(est)).sum()),
        "positive": sum(v > 0 for v in by_season.values()), "seasons": len(by_season), "by_season": by_season,
        "n": df.height, "sd_y": float(df["y"].std()),
    }  # fmt: skip


def main() -> None:
    gw = Gateway()
    for option in (*A.OFFENSE, *A.DEFENSE):
        df = rows(option, gw)
        cols = [f"{option}_use", f"{option}_use_raw"] if option in A.OFFENSE else [f"{option}_use"]
        for col in cols:
            r = test(df, col)
            seasons = " ".join(f"{s % 100:02d}:{v:+.3f}" for s, v in r["by_season"].items())
            print(
                f"{col:18s} n={r['n']:5d} slope {r['slope']:+.4f} per sd [{r['lo']:+.4f}, {r['hi']:+.4f}] "
                f"(gain sd {r['sd_y']:.2f}); shuffled |slope| 95th {r['null95']:.4f}, beaten {r['beats']}/{SHUFFLES}; "
                f"positive in {r['positive']}/{r['seasons']} seasons",
                flush=True,
            )
            print(f"    {seasons}", flush=True)
    repeats(gw)


def repeats(gw: Gateway) -> None:
    view = gw.view(END_OF_TIME, "retrospective", {"team_game": ("schedule", "tendencies", "charted")})
    tg = view.table("team_game").filter((c("game_type") == "REG") & c("season").is_between(2006, 2024))
    measures = ["pass_gain", "shotgun_gain", *[f"{o}_{x}" for o in A.DEFENSE for x in ("gain", "oe")]]
    out = consistency(tg, measures)
    print(out, flush=True)


if __name__ == "__main__":
    main()
