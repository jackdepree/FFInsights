"""Matchup types learned from results, the forecast version (I26; the CEO, 2026-11-09: "after the
merge we can push more into a forecast version using earlier games").

F24 learned hidden offense and defense numbers within a season from the season's *other* games
(including later ones). Here only earlier games are used, as a live model would:
- for each season and each week w from 6 on, fit strengths + k hidden numbers on that season's
  games before week w; predict week w's sides;
- the matchup part (u · v) against what the strength-only fit (same earlier games) misses;
- settings fixed at F24's (k 2, λ 1, chosen on 2006-2014 there): nothing is tuned here;
- eras reported separately (2006-2014, 2015-2024), and pairs that already met this season
  against pairs that haven't;
- null: each season's defenses swapped among sides within the week (training and test alike),
  30 times, 2015-2024;
- the market: each game's term (home offense's matchup part less the away offense's) against the
  margin's miss against the closing line, with the same null.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/walkforward.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from latent import als
from rematch import load

from pcf.data.tables.store import read_part

c = pl.col
RNG = np.random.default_rng(20261117)
K, LAM = 2, 1.0
FIRST_WEEK = 6
SHUFFLES = 30


def season_forecasts(t: pl.DataFrame, dfn: list[str], rng) -> pl.DataFrame:
    teams = sorted(set(t["off"].to_list()) | set(dfn))
    ix = {x: i for i, x in enumerate(teams)}
    o = np.array([ix[x] for x in t["off"].to_list()])
    d = np.array([ix[x] for x in dfn])
    y = t["y"].to_numpy()
    wk = t["week"].to_numpy()
    miss = np.full(len(y), np.nan)
    part = np.full(len(y), np.nan)
    met = np.zeros(len(y), bool)
    pair = o * 100 + d
    for w in np.unique(wk):
        if w < FIRST_WEEK:
            continue
        tr, te = wk < w, wk == w
        mu, a, b, _, _ = als(o[tr], d[tr], y[tr], len(teams), len(teams), 0, 0, rng)
        miss[te] = y[te] - (mu + a[o[te]] + b[d[te]])
        *_, U, V = als(o[tr], d[tr], y[tr], len(teams), len(teams), K, LAM, rng)
        part[te] = (U[o[te]] * V[d[te]]).sum(1)
        met[te] = np.isin(pair[te], pair[tr])
    return t.select("game_id", "season", "week", "off").with_columns(
        miss=pl.Series(miss), part=pl.Series(part), met=pl.Series(met)
    )


def run(s: pl.DataFrame, seasons, rng, shuffle=False) -> pl.DataFrame:
    out = []
    for yr in seasons:
        t = s.filter(c("season") == yr).sort("week", "game_id", "off")
        dfn = t["dfn"].to_list()
        if shuffle:
            wk = t["week"].to_numpy()
            for w in np.unique(wk):
                i = np.flatnonzero(wk == w)
                p = rng.permutation(i)
                vals = [t["dfn"][int(j)] for j in p]
                for a_, v in zip(i, vals, strict=True):
                    dfn[a_] = v
        out.append(season_forecasts(t, dfn, rng))
    return pl.concat(out).filter(c("part").is_not_nan() & c("miss").is_not_nan())


def r(df: pl.DataFrame) -> float:
    return float(np.corrcoef(df["part"].to_numpy(), df["miss"].to_numpy())[0, 1])


def market(f: pl.DataFrame) -> tuple[float, int, np.ndarray, np.ndarray]:
    sch = read_part("game", "schedule").select("game_id", "home_team", "away_team").collect()
    res = read_part("game", "result").select("game_id", "home_score", "away_score").collect()
    pre = read_part("game", "pregame").select("game_id", "spread_line").collect()
    g = (
        sch.join(res, on="game_id")
        .join(pre, on="game_id")
        .with_columns(close_miss=c("home_score") - c("away_score") - c("spread_line"))
        .join(
            f.select("game_id", c("off").alias("home_team"), c("part").alias("ph")),
            on=["game_id", "home_team"],
        )
        .join(
            f.select("game_id", c("off").alias("away_team"), c("part").alias("pa")),
            on=["game_id", "away_team"],
        )
        .with_columns(term=c("ph") - c("pa"))
        .drop_nulls(["term", "close_miss"])
    )
    x, y = g["term"].to_numpy(), g["close_miss"].to_numpy()
    return float(np.corrcoef(x, y)[0, 1]), g.height, x, y


def main() -> None:
    s = load()
    print(
        f"sides {s.height:,}; forecasts from week {FIRST_WEEK}, each from the season's earlier games only (k {K}, λ {LAM})"
    )
    old = run(s, range(2006, 2015), RNG)
    new = run(s, range(2015, 2025), RNG)
    nulls = [run(s, range(2015, 2025), RNG, shuffle=True) for _ in range(SHUFFLES)]
    nr = np.array([r(n) for n in nulls])
    print("\n== 1. The matchup part against what strength (from the same earlier games) misses")
    print(f"   2006-2014: {old.height:,} sides, r {r(old):+.4f}")
    print(
        f"   2015-2024: {new.height:,} sides, r {r(new):+.4f}; shuffled pairings: mean {nr.mean():+.4f}, 95th {np.quantile(nr, 0.95):+.4f}, at or above {np.mean(nr >= r(new)):.0%}"
    )
    for lab, m in (("already met this season", True), ("not yet met", False)):
        sub = new.filter(c("met") == m)
        ns = np.array([r(n.filter(c("met") == m)) for n in nulls])
        print(
            f"      {lab}: {sub.height:,} sides, r {r(sub):+.4f}; shuffled at or above {np.mean(ns >= r(sub)):.0%}"
        )
    for lo, hi in ((6, 9), (10, 13), (14, 18)):
        sub = new.filter(c("week").is_between(lo, hi))
        print(f"      weeks {lo}-{hi}: {sub.height:,} sides, r {r(sub):+.4f}")
    by = " ".join(
        f"{yr % 100:02d}:{r(new.filter(c('season') == yr)):+.3f}" for yr in range(2015, 2025)
    )
    print(f"      by season: {by}")
    slope = np.polyfit(new["part"].to_numpy() / new["part"].std(), new["miss"].to_numpy(), 1)[0]
    print(f"   size: {slope:+.4f} EPA per play per sd of the matchup part")

    print(
        "\n== 2. Against the closing line (2015-2024): the home offense's matchup part less the away offense's, against margin less the spread"
    )
    mr, n, x, y = market(new)
    mn = np.array([market(nl)[0] for nl in nulls])
    pts = np.polyfit(x / x.std(), y, 1)[0]
    q = np.quantile(x, [0.2, 0.8])
    print(
        f"   {n:,} games: r {mr:+.4f} ({pts:+.2f} points per sd); shuffled: mean {mn.mean():+.4f}, at or above {np.mean(mn >= mr):.0%}"
    )
    print(
        f"   top fifth (favours home): home beats the close by {y[x >= q[1]].mean():+.2f}, covers {np.mean(y[x >= q[1]] > 0):.1%}; bottom fifth {y[x <= q[0]].mean():+.2f}, covers {np.mean(y[x <= q[0]] > 0):.1%}"
    )


if __name__ == "__main__":
    main()
