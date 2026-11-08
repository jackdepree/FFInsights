"""H7: parts of a team. Do passing and running ratings add to the points rating?

Each team gets offense and defense ratings of expected points per play (EPA), for passing and
for running (and one for all plays, to test whether the split helps). They're tracked like
rung 1: before each week, a team's expected edge is its offense rating minus the opponent's
defense rating; after the week, both move by k times the miss; a half pull between seasons.

The margin forecast is rung 1's plus beta x (home edge - away edge) for each part; the total
forecast is the offense/defense ratings' plus gamma x (home edge + away edge). beta and gamma
are fit by least squares on 2002-2015 (the miss of rung 1), k is picked on the same seasons.
Reported on 2016-2024 and on 2020-2024, the seasons expected points weren't fit on
(tag-tables#F4). The vault (2025) isn't read. Run from pcf/:
.venv/Scripts/python.exe projects/elo/explore/h7_parts.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import ladder as L  # noqa: E402

from pcf.data.tables.store import read_part  # noqa: E402

c = pl.col
PARTS = ("pass", "rush", "all")


def team_epa() -> pl.DataFrame:
    """Per (game, offense team): EPA per play for passes, runs and both."""
    p = (
        read_part("play", "pbp", seasons=list(range(L.FIRST, L.LAST + 1)))
        .select("game_id", "posteam", "play_type", "epa")
        .filter(c("play_type").is_in(["pass", "run"]) & c("epa").is_not_null())
        .filter(~c("epa").is_nan())
        .collect()
    )
    return (
        p.group_by("game_id", "posteam")
        .agg(
            pass_=c("epa").filter(c("play_type") == "pass").mean(),
            rush=c("epa").filter(c("play_type") == "run").mean(),
            all=c("epa").mean(),
        )
        .rename({"pass_": "pass"})
    )


def edges(g: pl.DataFrame, te: pl.DataFrame, k: float) -> pl.DataFrame:
    """Each game's pre-game expected EPA-per-play edge for home and away offense, per part."""
    h = te.rename({"posteam": "home_team"} | {x: f"h_{x}" for x in PARTS})
    a = te.rename({"posteam": "away_team"} | {x: f"a_{x}" for x in PARTS})
    gg = g.join(h, on=["game_id", "home_team"], how="left").join(
        a, on=["game_id", "away_team"], how="left"
    )
    o = {x: defaultdict(float) for x in PARTS}
    d = {x: defaultdict(float) for x in PARTS}
    mu = {x: 0.0 for x in PARTS}
    season, rows = None, []
    for (s, _w), wk in gg.sort("order").group_by(["season", "week"], maintain_order=True):
        if s != season:
            for x in PARTS:
                for t in list(o[x]):
                    o[x][t] *= 0.5
                    d[x][t] *= 0.5
            season = s
        games = wk.to_dicts()
        for z in games:
            hh, aa = z["home_team"], z["away_team"]
            row = {"game_id": z["game_id"]}
            for x in PARTS:
                row[f"eh_{x}"] = o[x][hh] - d[x][aa]
                row[f"ea_{x}"] = o[x][aa] - d[x][hh]
            rows.append(row)
        for z in games:
            hh, aa = z["home_team"], z["away_team"]
            for x in PARTS:
                for off, de, obs in ((hh, aa, z[f"h_{x}"]), (aa, hh, z[f"a_{x}"])):
                    if obs is None:
                        continue
                    miss = obs - (mu[x] + o[x][off] - d[x][de])
                    o[x][off] += k * miss
                    d[x][de] -= k * miss
                    mu[x] += 0.01 * miss
    return pl.DataFrame(rows)


def fit(df: pl.DataFrame, y: str, xs: list[str]) -> np.ndarray:
    X = df.select(xs).to_numpy()
    return np.linalg.lstsq(X, df[y].to_numpy(), rcond=None)[0]


def main() -> None:
    g = L.games()
    priors = L.season_priors(g)
    te = team_epa()
    base = L.run(g, priors, "margin_pull", **L.RUNG1).rename({"pred": "b"}).drop("pred_total")
    od = L.run(g, priors, "off_def", **L.RUNG1_OD).select("game_id", b_t="pred_total")
    sets = {"pass": ["pass"], "rush": ["rush"], "pass+rush": ["pass", "rush"], "all": ["all"]}

    best = None
    for k in (0.05, 0.1, 0.15, 0.2):
        e = edges(g, te, k)
        j = g.join(base, on="game_id").join(od, on="game_id").join(e, on="game_id")
        j = j.with_columns(
            [(c(f"eh_{x}") - c(f"ea_{x}")).alias(f"m_{x}") for x in PARTS]
            + [(c(f"eh_{x}") + c(f"ea_{x}")).alias(f"t_{x}") for x in PARTS]
            + [(c("margin") - c("b")).alias("res"), (c("total") - c("b_t")).alias("res_t")]
        )
        tune = j.filter(c("season").is_between(L.TUNE_FROM, L.REPORT_FROM - 1))
        beta = fit(tune, "res", ["m_pass", "m_rush"])
        miss = float(
            (tune["res"] - tune.select(["m_pass", "m_rush"]).to_numpy() @ beta).abs().mean()
        )
        if best is None or miss < best[0]:
            best = (miss, k, j)
    _, k, j = best
    print(f"chosen k = {k}")
    tune = j.filter(c("season").is_between(L.TUNE_FROM, L.REPORT_FROM - 1))

    for lo in (L.REPORT_FROM, 2020):
        rep = j.filter(c("season").is_between(lo, L.LAST))
        print(
            f"\nreported {lo}-{L.LAST} ({rep.height} games); rung 1 margin "
            f"{float(rep['res'].abs().mean()):.3f}, total {float(rep['res_t'].abs().mean()):.3f}"
        )
        for name, xs in sets.items():
            beta = fit(tune, "res", [f"m_{x}" for x in xs])
            gamma = fit(tune, "res_t", [f"t_{x}" for x in xs])
            e = rep.with_columns(
                v=c("res") - sum(b * c(f"m_{x}") for b, x in zip(beta, xs, strict=True)),
                v_t=c("res_t") - sum(gm * c(f"t_{x}") for gm, x in zip(gamma, xs, strict=True)),
            ).select("season", "week", "v", "v_t", b="res", b_t="res_t")
            gm_ = L.interval(e, "v", "b")
            gt_ = L.interval(e, "v_t", "b_t")
            coef = ", ".join(f"{x} {b:.1f}" for x, b in zip(xs, beta, strict=True))
            print(
                f"  {name:10s} margin {float(e['v'].abs().mean()):.3f} gap {gm_[0]:+.3f} "
                f"[{gm_[1]:+.3f}, {gm_[2]:+.3f}]  total {float(e['v_t'].abs().mean()):.3f} "
                f"gap {gt_[0]:+.3f} [{gt_[1]:+.3f}, {gt_[2]:+.3f}]  (points per EPA/play: {coef})"
            )


if __name__ == "__main__":
    main()
