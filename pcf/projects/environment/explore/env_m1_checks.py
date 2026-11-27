"""Environment, checks written AFTER method 1's results (2026-11-27). They explain what went against the frame and
don't change any pre-registered verdict.

1. H127's ranking: is yards a play's lead over game totals more than noise? Seasons resampled together.
2. Field goals kick by kick: how much the conditions add beyond distance (the share of the Brier score removed,
   a season held out at a time), and 50+ yard makes in 15+ mph wind against calm.
3. Wind beyond the closing total, by era, and with the forecast in place of the observed weather (2022-2024).

Run from pcf/:  python projects/environment/explore/env_m1_checks.py   (writes env_m1_checks.txt)
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
import env_m1 as M  # noqa: E402
from env_common import Say, games, kicks, team_games, weather  # noqa: E402

c = pl.col
RNG = np.random.default_rng(17)
say = Say(Path(__file__).with_suffix(".txt"))


def oof(x: pl.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X, y, seas = M.X_of(x), x["y"].to_numpy(), x["season"].to_numpy()
    p = np.zeros(len(y))
    for s in np.unique(seas):
        tr, te = seas != s, seas == s
        b, _ = M.ols(X[tr], y[tr])
        p[te] = np.column_stack([np.ones(te.sum()), X[te]]) @ b
    return y, p, seas


def main() -> None:
    g, t = games(), team_games()
    say("# Environment: checks after method 1 (2026-11-27; they don't change the pre-registered verdicts)", "")

    # 1. H127's top two
    ya, pa, sa = oof(M.rows_for("yards_per_play", t, g))
    yb, pb, sb = oof(M.rows_for("game_total", t, g))
    seasons = np.unique(sa)
    diffs = []
    for _ in range(1000):
        pick = RNG.choice(seasons, len(seasons))
        ia = np.concatenate([np.nonzero(sa == s)[0] for s in pick])
        ib = np.concatenate([np.nonzero(sb == s)[0] for s in pick])
        ra = 1 - np.sum((ya[ia] - pa[ia]) ** 2) / np.sum((ya[ia] - ya[ia].mean()) ** 2)
        rb = 1 - np.sum((yb[ib] - pb[ib]) ** 2) / np.sum((yb[ib] - yb[ib].mean()) ** 2)
        diffs.append(ra - rb)
    d = np.array(diffs)
    say("## 1. H127's top two", "", f"Yards a play's share less game totals': {np.mean(d):+.2%} (90%: {np.quantile(d, 0.05):+.2%} to {np.quantile(d, 0.95):+.2%}); yards a play ahead in {np.mean(d > 0):.0%} of resamples.", "")

    # 2. field goals, kick by kick
    k = kicks().join(g.select("game_id", "wind", "temp", "precip", "dome", "altitude"), on="game_id", how="inner").drop_nulls(["wind"])
    k = k.with_columns(cold=(50 - c("temp")).clip(0, None))
    dist = k["kick_distance"].to_numpy().astype(float)
    D = np.column_stack([dist, dist**2, dist**3 / 100])
    C = np.column_stack([k[x].cast(pl.Float64).to_numpy() for x in ("wind", "cold", "precip", "dome", "altitude")])
    C = np.column_stack([C, C[:, 0] * dist, C[:, 4] * dist])  # wind and altitude matter more on long kicks
    y, seas = k["made"].to_numpy(), k["season"].to_numpy()
    p0, p1 = np.zeros(len(y)), np.zeros(len(y))
    for s in np.unique(seas):
        tr, te = seas != s, seas == s
        for X, p in ((D, p0), (np.column_stack([D, C]), p1)):
            m, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
            f = LogisticRegression(C=1.0, max_iter=2000).fit((X[tr] - m) / sd, y[tr])
            p[te] = f.predict_proba((X[te] - m) / sd)[:, 1]
    b0, b1 = np.sum((y - p0) ** 2), np.sum((y - p1) ** 2)
    var = np.sum((y - y.mean()) ** 2)
    long = k.filter((c("kick_distance") >= 50) & ~c("dome"))
    w, calm = long.filter(c("wind") >= 15), long.filter(c("wind") < 10)
    say("## 2. Field goals, kick by kick", "",
        f"{k.height:,} kicks 1999-2024. Distance alone explains {1 - b0 / var:.2%} of the make-or-miss variation; the conditions add {(b0 - b1) / var:+.2%} of it "
        f"({1 - b1 / b0:+.2%} of the distance model's Brier score).",
        f"50+ yard kicks outdoors: made {w['made'].mean():.1%} in 15+ mph wind ({w.height} kicks) against {calm['made'].mean():.1%} under 10 mph ({calm.height}).", "")

    # 3. wind beyond the closing total, by era, and with the forecast
    x = M.rows_for("game_total", t, g).join(t.filter(c("home")).select("game_id", "total_line"), on="game_id", how="left").drop_nulls("total_line")
    say("## 3. Wind beyond the closing total", "", "| Seasons | Games, 15+ mph | Total less the close, 15+ mph | Total less the close, under 10 mph | Gap |", "|---|---|---|---|---|")
    for lo, hi in ((1999, 2007), (2008, 2015), (2016, 2024)):
        z = x.filter(c("season").is_between(lo, hi) & ~c("dome"))
        a = z.filter(c("wind") >= 15).with_columns(r=c("y") - c("total_line"))["r"]
        b = z.filter(c("wind") < 10).with_columns(r=c("y") - c("total_line"))["r"]
        se = np.sqrt(a.var() / a.len() + b.var() / b.len())
        say(f"| {lo}-{hi} | {a.len()} | {a.mean():+.2f} | {b.mean():+.2f} | {a.mean() - b.mean():+.2f} (±{1.645 * se:.2f}) |")
    f = weather("forecast").select("game_id", wind_f="wind")
    z = x.filter((c("season") >= 2022) & ~c("dome")).join(f, on="game_id", how="inner").with_columns(r=c("y") - c("total_line"))
    for lab, col in (("observed", "wind"), ("forecast", "wind_f")):
        a, b = z.filter(c(col) >= 15)["r"], z.filter(c(col) < 10)["r"]
        say(f"- 2022-2024, by the {lab} wind: total less the close {a.mean():+.2f} at 15+ mph ({a.len()} games) against {b.mean():+.2f} under 10 ({b.len()}); per mph, robust slope "
            f"{np.polyfit(z[col].to_numpy(), z['r'].to_numpy(), 1)[0]:+.3f}")
    say.save()


if __name__ == "__main__":
    main()
