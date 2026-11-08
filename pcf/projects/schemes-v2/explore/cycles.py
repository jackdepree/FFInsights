"""The CEO's rock-paper-scissors hunch, first look (2026-11-08, discovery only).

A circle: A beat B, B beat C, C beat A in the same season. Two explanations (the CEO's): flukes in
close games, or schemes that give each team an edge over the next. Before any scheme data, the
question is whether circles are more common than team strength plus luck produce on their own.

1. Every triangle of teams that played each other in a season (each pair's games counted
   equally): the share that are circles, actual against two nulls, each simulated 1,000 times
   from per-game win chances: Elo's (team strength only) and the closing line's (strength plus
   anything the market knows, injuries and matchups included). Pure coin flips give 25%.
   Independent games understate how ordered a season is: a team's true strength is shared by all
   its games (elo#F13). So a third null adds a hidden season strength per team, sized so the
   simulated spread of wins around Elo's expected wins matches the real one.
2. The flukes test: how close are the games inside circles, against games inside ordinary
   (transitive) triangles?

Elo's chances are the validated `win` history (pull 0.4, seed lock), 2016-2024. Ties are dropped.
The vault (2025) isn't read.
Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/cycles.py
"""

# ruff: noqa: E501
from __future__ import annotations

from collections import defaultdict
from itertools import product

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import Gateway

c = pl.col
WIN_RUN = "b811be4301f54f1491bfce1ef29e06d5"
SIMS = 1000
RNG = np.random.default_rng(20261108)


def games() -> pl.DataFrame:
    s = Gateway().source
    res = s.part("game", "result").select("game_id", "home_score", "away_score")
    pre = s.part("game", "pregame").select("game_id", "home_moneyline", "away_moneyline")
    elo = pl.read_parquet(get_config().zone("outputs") / "elo" / "win" / WIN_RUN / "history.parquet").select("game_id", p_elo="mean")
    odds = lambda m: pl.when(m > 0).then(100 / (m + 100)).otherwise(-m / (-m + 100))  # noqa: E731
    return (
        s.part("game", "schedule").filter(c("season").is_between(2016, 2024))
        .select("game_id", "season", "home_team", "away_team")
        .join(res, on="game_id").join(pre, on="game_id", how="left").join(elo, on="game_id")
        .filter(c("home_score") != c("away_score"))
        .with_columns(
            hw=c("home_score") > c("away_score"),
            margin=(c("home_score") - c("away_score")).abs(),
            p_close=odds(c("home_moneyline")) / (odds(c("home_moneyline")) + odds(c("away_moneyline"))),
        )
        .with_columns(c("p_close").fill_null(c("p_elo")))
        .sort("game_id")
    )  # fmt: skip


def triangles(g: pl.DataFrame):
    """Each combination of one game per pair inside each triangle: the three game indices, whether
    the first-named team of each edge was at home, and a weight (1 / combinations) so every
    triangle counts once."""
    home, away = g["home_team"].to_list(), g["away_team"].to_list()
    rows = []
    for season in g["season"].unique().sort().to_list():
        idx = [i for i, s in enumerate(g["season"].to_list()) if s == season]
        pair = defaultdict(list)
        for i in idx:
            pair[frozenset((home[i], away[i]))].append(i)
        teams = sorted({home[i] for i in idx} | {away[i] for i in idx})
        for ai, a in enumerate(teams):
            for bi in range(ai + 1, len(teams)):
                b = teams[bi]
                ab = pair.get(frozenset((a, b)))
                if not ab:
                    continue
                for cc in teams[bi + 1:]:
                    bc, ca = pair.get(frozenset((b, cc))), pair.get(frozenset((cc, a)))
                    if not bc or not ca:
                        continue
                    combos = list(product(ab, bc, ca))
                    for g1, g2, g3 in combos:
                        rows.append((season, g1, g2, g3, home[g1] == a, home[g2] == b, home[g3] == cc, 1 / len(combos)))
    return np.array(rows, dtype=float)


def cyclic(t: np.ndarray, hw: np.ndarray) -> np.ndarray:
    """1 where the combination is a circle: A beat B, B beat C, C beat A (or all reversed)."""
    g1, g2, g3 = t[:, 1].astype(int), t[:, 2].astype(int), t[:, 3].astype(int)
    x = hw[..., g1] == t[:, 4].astype(bool)
    y = hw[..., g2] == t[:, 5].astype(bool)
    z = hw[..., g3] == t[:, 6].astype(bool)
    return ((x & y & z) | (~x & ~y & ~z)).astype(float)


def main() -> None:
    g = games()
    t = triangles(g)
    w = t[:, 7]
    n = w.sum()
    hw = g["hw"].to_numpy()
    actual = (cyclic(t, hw) * w).sum() / n
    print(f"== 1. Circles among triangles, 2016-2024 ({g.height} games, {n:.0f} triangles of teams that all met)")
    print(f"   actual: {actual:.1%}")
    for name in ("p_elo", "p_close"):
        p = g[name].to_numpy()
        sims = RNG.random((SIMS, len(p))) < p
        rates = (cyclic(t, sims) * w).sum(axis=1) / n
        lo, hi = np.quantile(rates, [0.05, 0.95])
        print(f"   null from {name[2:]:<6} win chances: {rates.mean():.1%} (90% of simulated seasons {lo:.1%} to {hi:.1%}); "
              f"actual above {np.mean(rates < actual):.0%} of them")
    print("   coin flips: 25.0%")

    # The fair null: Elo's chances plus a hidden season strength per team (logit units)
    seasons_g = g["season"].to_numpy()
    teams = sorted(set(g["home_team"]) | set(g["away_team"]))
    code = {(s_, t_): k for k, (s_, t_) in enumerate((s_, t_) for s_ in np.unique(seasons_g) for t_ in teams)}
    hi_ = np.array([code[(s_, t_)] for s_, t_ in zip(seasons_g, g["home_team"])])
    ai_ = np.array([code[(s_, t_)] for s_, t_ in zip(seasons_g, g["away_team"])])
    pe = g["p_elo"].to_numpy().clip(1e-6, 1 - 1e-6)
    logit = np.log(pe / (1 - pe))

    def spread(outcome: np.ndarray, p: np.ndarray) -> float:
        """Variance of a team-season's wins minus its expected wins."""
        r = np.zeros((outcome.shape[0], len(code)))
        for side, sign in ((hi_, 1), (ai_, -1)):
            np.add.at(r.T, side, (np.where(sign == 1, outcome, ~outcome) - np.where(sign == 1, p, 1 - p)).T)
        return float(r.var(axis=1).mean())

    real = spread(hw[None, :], pe[None, :])
    print(f"   real spread of team-season wins around Elo's expectation: variance {real:.2f}")
    for sd in (0.0, 0.2, 0.3, 0.4, 0.5):
        u = RNG.normal(0, sd, (SIMS, len(code)))
        prob = 1 / (1 + np.exp(-(logit + u[:, hi_] - u[:, ai_])))
        sims = RNG.random(prob.shape) < prob
        rates = (cyclic(t, sims) * w).sum(axis=1) / n
        lo, hi = np.quantile(rates, [0.05, 0.95])
        print(f"   hidden strength sd {sd:.1f}: win spread {spread(sims, pe[None, :].repeat(SIMS, 0)):.2f}, circles {rates.mean():.1%} ({lo:.1%} to {hi:.1%}), actual above {np.mean(rates < actual):.0%}")

    seasons = t[:, 0]
    cyc = cyclic(t, hw)
    print("   by season:", ", ".join(f"{int(s)} {(cyc * w)[seasons == s].sum() / w[seasons == s].sum():.0%}" for s in np.unique(seasons)))

    print("\n== 2. Flukes? How close the games are (points), in circles against ordinary triangles")
    m = g["margin"].to_numpy()
    for label, mask in (("circles", cyc == 1), ("ordinary", cyc == 0)):
        ww = np.repeat(w[mask], 3)
        mm = m[t[mask][:, 1:4].astype(int)].ravel()
        print(f"   {label:<9} mean margin {np.average(mm, weights=ww):.1f}, within 3 points {np.average(mm <= 3, weights=ww):.0%}, "
              f"within 7 {np.average(mm <= 7, weights=ww):.0%}")
    one = (m[t[:, 1:4].astype(int)] <= 3).any(axis=1)
    print(f"   circles with at least one game decided by 3 or fewer: {np.average(one[cyc == 1], weights=w[cyc == 1]):.0%} "
          f"(ordinary triangles: {np.average(one[cyc == 0], weights=w[cyc == 0]):.0%})")
    print(f"   all games: mean margin {m.mean():.1f}, within 3 points {np.mean(m <= 3):.0%}")


if __name__ == "__main__":
    main()
