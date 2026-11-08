"""Cheap checks of the long horizon's assumptions (CEO, 2026-11-07), regular seasons 2002-2024.

The long horizon scores each game left with today's ratings (frozen), turns the edge into a win
chance with a normal curve 13.5 points wide, sums the chances (games treated as independent), and
refits wins = b1 x the sum + b2 x games left.

1. The curve's width: the spread of margins around the rating-only forecast.
2. Frozen ratings: are win chances for games k weeks ahead still calibrated? (a logistic slope of
   the result on the chance's log-odds: 1 = right, below 1 = too confident). Expect the slope to
   fall the further ahead, since ratings drift; that's what b1 < 1 would correct.
3. Independence: is the spread of (wins - expected wins) wider than the sum of p(1 - p) says?
   Games of one team share its unknown true strength, so expect wider, more with more games left.
4. The refit on 2002-2015: b1 and b2.

Run from pcf/: .venv/Scripts/python.exe projects/elo/explore/horizon_checks.py
"""

# ruff: noqa: E501
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
import carryover as C  # noqa: E402

from pcf.experts.elo.features import results  # noqa: E402
from pcf.experts.elo.horizons import SPREAD  # noqa: E402
from pcf.experts.elo.ratings import DEFAULT, Walk, season_priors  # noqa: E402

c = pl.col


def chance(edge: float) -> float:
    return 0.5 * (1 + math.erf(edge / SPREAD / math.sqrt(2)))


def rows() -> pl.DataFrame:
    """For each team, each regular-season week w (ratings as they stood before week w), and each of
    its games in week w or later: the frozen win chance and the result."""
    g = C.games()
    reg = g.filter(
        (c("game_type") == "REG")
        & c("season").is_between(2002, C.LAST)
        & c("home_score").is_not_null()
    )
    res = results(g)
    w = Walk(season_priors(res, DEFAULT), DEFAULT)
    res_rows = res.to_dicts()
    starts = reg.group_by("season", "week").agg(start=c("kickoff").min()).sort("season", "week")
    games = reg.select(
        "season", "week", "home_team", "away_team", "location", m=c("home_score") - c("away_score")
    ).to_dicts()
    by_season: dict[int, list[dict]] = {}
    for x in games:
        by_season.setdefault(x["season"], []).append(x)
    i, out = 0, []
    for s in starts.iter_rows(named=True):
        while i < len(res_rows) and res_rows[i]["known_at"] <= s["start"]:
            w.add(res_rows[i])
            i += 1
        w.roll_to(s["season"])
        hfa = w.hfa(s["season"], False)
        for x in by_season[s["season"]]:
            if x["week"] < s["week"]:
                continue
            side = 0.0 if x["location"] == "Neutral" else hfa
            p = chance(w.r[x["home_team"]] - w.r[x["away_team"]] + side)
            win = 1.0 if x["m"] > 0 else 0.0 if x["m"] < 0 else 0.5
            out += [
                {
                    "season": s["season"],
                    "at": s["week"],
                    "week": x["week"],
                    "team": x["home_team"],
                    "p": p,
                    "win": win,
                },
                {
                    "season": s["season"],
                    "at": s["week"],
                    "week": x["week"],
                    "team": x["away_team"],
                    "p": 1 - p,
                    "win": 1 - win,
                },
            ]
    return pl.DataFrame(out).with_columns(ahead=c("week") - c("at"))


def main() -> None:
    g = C.games()
    pre, _ = C.walk_all(g)
    e = pre.filter((c("game_type") == "REG") & c("season").is_between(2002, C.LAST))
    print(
        f"== 1. Spread of margins around the rating-only forecast: sd {(e['margin'] - e['fc']).std():.1f} points (the curve uses {SPREAD})"
    )

    d = rows()
    print(
        "\n== 2. Frozen ratings: calibration of win chances by weeks ahead (slope 1 = right, below 1 = too confident)"
    )
    print(f"   {'weeks ahead':<14}{'team-games':>11}{'slope':>8}{'mean chance':>13}{'won':>7}")
    for lo, hi in ((0, 0), (1, 3), (4, 8), (9, 20)):
        x = d.filter(c("ahead").is_between(lo, hi) & (c("win") != 0.5))
        logit = np.log(x["p"] / (1 - x["p"])).to_numpy().reshape(-1, 1)
        slope = LogisticRegression(C=1e6).fit(logit, x["win"].to_numpy()).coef_[0, 0]
        print(
            f"   {f'{lo}-{hi}':<14}{x.height:>11,}{slope:>8.2f}{x['p'].mean():>13.3f}{x['win'].mean():>7.3f}"
        )

    print(
        "\n== 3. Independence: spread of (wins - expected wins) against what independent games give"
    )
    print(
        f"   {'games left':<12}{'team-weeks':>11}{'actual sd':>11}{'independent sd':>16}{'ratio':>7}"
    )
    tw = d.group_by("season", "at", "team").agg(
        left=pl.len(), exp=c("p").sum(), var=(c("p") * (1 - c("p"))).sum(), won=c("win").sum()
    )
    for lo, hi in ((1, 3), (4, 8), (9, 12), (13, 17)):
        x = tw.filter(c("left").is_between(lo, hi))
        act = (x["won"] - x["exp"]).std()
        ind = math.sqrt(x["var"].mean())
        print(f"   {f'{lo}-{hi}':<12}{x.height:>11,}{act:>11.2f}{ind:>16.2f}{act / ind:>7.2f}")

    print("\n== 4. The refit, wins = b1 x expected wins + b2 x games left, on 2002-2015")
    x = tw.filter(c("season") <= 2015)
    b = np.linalg.lstsq(x.select("exp", "left").to_numpy(), x["won"].to_numpy(), rcond=None)[0]
    print(
        f"   b1 = {b[0]:.2f}, b2 = {b[1]:.2f}: a game at 80% counts {0.8 * b[0] + b[1]:.2f}, at 50% {0.5 * b[0] + b[1]:.2f}, at 20% {0.2 * b[0] + b[1]:.2f}"
    )


if __name__ == "__main__":
    main()
