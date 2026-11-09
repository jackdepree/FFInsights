"""The CEO's H11, first look (2026-11-09, discovery only, diagnosis): do schemes predict how a team
does from a game state?

"we can predict performance based on conditions, like if a team is losing at halftime then they
will most likely not be able to come back."

Each row is one team in one game, 2006-2024 regular season, weeks 4+.
- **The state:** the score at halftime, from the team's side: trailing by 9+, by 1-8, tied, leading
  by 1-8, by 9+.
- **Two outcomes beyond what's already known at halftime:**
  - *win beyond the win chance:* result (win 1, tie 0.5, loss 0) less the closing line's win
    chance at the start of the second half (nflfastR `vegas_home_wp`, which knows the score, the
    clock, the ball and both teams' strength through the spread);
  - *second-half margin beyond the close:* the team's second-half points less the opponent's, less
    half the closing spread's expected margin. Far more information per game than win or loss.
- **Schemes, known before the game:** each tendency's mean over the regime's earlier games (3+),
  standardized by season (as in `conditions.py`); offense and defense tendencies of the team, and
  the opponent's.
1. The usual way: comeback rates by state, and whether the win chance is calibrated in each.
2. Each tendency's slope on both outcomes, among trailing teams and among leading teams, and the
   difference. Null: tendencies shuffled across teams within the same week (200); the largest |t|.
3. Held out: all tendencies × state, fitted on even seasons, predicting odd seasons, and the reverse,
   against the same with shuffled tendencies.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/states.py
"""

# ruff: noqa: E501
from __future__ import annotations

import numpy as np
import polars as pl
from conditions import DEF, OFF, prior

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
RNG = np.random.default_rng(202611093)
SHUFFLES = 200
SEASONS = range(2006, 2025)
STATES = ["down 9+", "down 1-8", "tied", "up 1-8", "up 9+"]
TEND = OFF + DEF


def halftime() -> pl.DataFrame:
    cols = ["game_id", "season", "season_type", "week", "home_team", "away_team", "qtr", "total_home_score", "total_away_score",
            "vegas_home_wp", "result", "spread_line", "play_id"]
    rows = []
    for s in SEASONS:
        p = read_part("play", "pbp", [s]).select(cols).collect().filter(c("season_type") == "REG").sort("game_id", "play_id")
        h1 = p.filter(c("qtr") <= 2).group_by("game_id").agg(h_home=c("total_home_score").max(), h_away=c("total_away_score").max())
        q3 = p.filter((c("qtr") == 3) & c("vegas_home_wp").is_not_null()).group_by("game_id").agg(c("vegas_home_wp").first().alias("wp_half"))
        g = p.group_by("game_id").agg(c("season", "week", "home_team", "away_team", "result", "spread_line").first())
        rows.append(g.join(h1, on="game_id").join(q3, on="game_id"))
    g = pl.concat(rows)
    home = g.select("game_id", "season", "week", team=c("home_team"), opp=c("away_team"), ht=c("h_home") - c("h_away"),
                    final=c("result").cast(pl.Float64), exp=c("spread_line"), wp=c("wp_half"))
    away = g.select("game_id", "season", "week", team=c("away_team"), opp=c("home_team"), ht=c("h_away") - c("h_home"),
                    final=-c("result").cast(pl.Float64), exp=-c("spread_line"), wp=1 - c("wp_half"))
    t = pl.concat([home, away]).with_columns(
        win=pl.when(c("final") > 0).then(1.0).when(c("final") < 0).then(0.0).otherwise(0.5),
        state=pl.when(c("ht") <= -9).then(pl.lit(STATES[0])).when(c("ht") < 0).then(pl.lit(STATES[1])).when(c("ht") == 0).then(pl.lit(STATES[2]))
        .when(c("ht") <= 8).then(pl.lit(STATES[3])).otherwise(pl.lit(STATES[4])),
    ).with_columns(r_win=c("win") - c("wp"), r_2h=(c("final") - c("ht")) - 0.5 * c("exp"))
    return t


def table() -> pl.DataFrame:
    tg = pl.read_parquet(get_config().zone("interim") / "schemes_v2" / "team_game.parquet")
    z = prior(tg, TEND, "regime", "z_")
    t = halftime().join(z, on=["game_id", "team"], how="inner")
    oz = z.select("game_id", c("team").alias("opp"), *[c(f"z_{m}").alias(f"oz_{m}") for m in TEND])
    t = t.join(oz, on=["game_id", "opp"], how="left").filter(c("week") >= 4)
    cols = [f"z_{m}" for m in TEND] + [f"oz_{m}" for m in TEND]
    return t.with_columns(*[((c(k) - c(k).mean().over("season")) / c(k).std().over("season")) for k in cols])


def week_perm(t: pl.DataFrame) -> np.ndarray:
    keys = (t["season"] * 100 + t["week"]).to_numpy()
    idx = np.arange(t.height)
    out = idx.copy()
    for k in np.unique(keys):
        w = idx[keys == k]
        out[w] = RNG.permutation(w)
    return out


def slope_t(x: np.ndarray, y: np.ndarray) -> tuple[float, float, int]:
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    if len(x) < 200:
        return np.nan, np.nan, len(x)
    X = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    se = np.sqrt((e @ e) / (len(y) - 2) / ((x - x.mean()) ** 2).sum())
    return float(b[1]), float(b[1] / se), len(x)


def slopes(t: pl.DataFrame, perm: np.ndarray | None = None) -> dict:
    trail = (t["ht"] < 0).to_numpy()
    lead = (t["ht"] > 0).to_numpy()
    out = {}
    for pre in ("z_", "oz_"):
        for m in TEND:
            x = t[f"{pre}{m}"].to_numpy()
            if perm is not None:
                x = x[perm]
            for oc in ("r_win", "r_2h"):
                y = t[oc].to_numpy()
                out[(pre + m, oc, "trailing")] = slope_t(x[trail], y[trail])
                out[(pre + m, oc, "leading")] = slope_t(x[lead], y[lead])
                out[(pre + m, oc, "all")] = slope_t(x, y)
    return out


def held_out(t: pl.DataFrame, oc: str, perm: np.ndarray | None = None) -> float:
    cols = [f"z_{m}" for m in TEND] + [f"oz_{m}" for m in TEND]
    Z = np.nan_to_num(t.select(cols).to_numpy())
    if perm is not None:
        Z = Z[perm]
    st = np.column_stack([(t["state"] == s).to_numpy().astype(float) for s in STATES])
    X = np.column_stack([st] + [Z * st[:, [k]] for k in range(len(STATES))])
    y = t[oc].to_numpy()
    even = (t["season"] % 2 == 0).to_numpy()
    pred = np.empty(len(y))
    for tr in (even, ~even):
        lam = 50.0 * np.eye(X.shape[1])
        lam[: len(STATES), : len(STATES)] = 0
        b = np.linalg.solve(X[tr].T @ X[tr] + lam, X[tr].T @ y[tr])
        pred[~tr] = X[~tr] @ b
    return float(np.corrcoef(pred, y)[0, 1])


def main() -> None:
    t = table().drop_nulls(["wp", "exp", "final"])
    print(f"team-games {t.height:,} (weeks 4+, 2006-2024, regimes with 3+ earlier games)")

    print("\n== 1. The usual way: comebacks by halftime state")
    s = t.group_by("state").agg(n=pl.len(), won=c("win").mean(), wp=c("wp").mean(), r_win=c("r_win").mean(), r_2h=c("r_2h").mean(),
                                sd_win=c("r_win").std(), sd_2h=c("r_2h").std())
    for row in sorted(s.iter_rows(named=True), key=lambda r: STATES.index(r["state"])):
        print(f"  {row['state']:<9} {row['n']:>5} games: won {row['won']:.1%}, win chance at half {row['wp']:.1%} "
              f"(beyond: {row['r_win']:+.3f} ± {1.645 * row['sd_win'] / np.sqrt(row['n']):.3f}); second-half margin beyond the close {row['r_2h']:+.2f} ± {1.645 * row['sd_2h'] / np.sqrt(row['n']):.2f} points")

    print("\n== 2. Each tendency (per sd), among trailing and leading teams")
    real = slopes(t)
    null_max = {k: [] for k in ("r_win", "r_2h")}
    for _ in range(SHUFFLES):
        sh = slopes(t, week_perm(t))
        for oc in null_max:
            null_max[oc].append(max(abs(v[1]) for k, v in sh.items() if k[1] == oc and not np.isnan(v[1])))
    for oc, unit, lab in (("r_win", "win chance", "win beyond the win chance"), ("r_2h", "points", "second-half margin beyond the close")):
        q = np.quantile(null_max[oc], 0.95)
        print(f"\n  {lab} ({unit} per sd); shuffled tendencies' largest |t| 95th: {q:.2f}")
        print(f"  {'tendency':<18} {'trailing':>16} {'leading':>16} {'all':>16}")
        for pre in ("z_", "oz_"):
            for m in TEND:
                k = pre + m
                cells = []
                for st in ("trailing", "leading", "all"):
                    b, tt, n = real[(k, oc, st)]
                    mark = "*" if abs(tt) > q else ("~" if abs(tt) > 2.5 else " ")
                    cells.append(f"{b:+.3f} (t{tt:+.1f}){mark}" if oc == "r_win" else f"{b:+.2f} (t{tt:+.1f}){mark}")
                print(f"  {('opp ' if pre == 'oz_' else '') + m:<18} " + " ".join(f"{x:>16}" for x in cells))
    print("  * beyond the shuffled 95th of the largest |t|; ~ |t| > 2.5")

    print("\n== 3. Held out: all tendencies × halftime state (ridge), even seasons predict odd and the reverse")
    for oc in ("r_win", "r_2h"):
        r = held_out(t, oc)
        null = np.array([held_out(t, oc, week_perm(t)) for _ in range(SHUFFLES)])
        print(f"  {oc}: r {r:+.3f}; shuffled tendencies 95th {np.quantile(null, 0.95):+.3f}, at or above {np.mean(null >= r):.0%}")


if __name__ == "__main__":
    main()
