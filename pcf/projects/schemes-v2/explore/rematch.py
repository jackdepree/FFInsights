"""Scheme against scheme, option A (CEO, 2026-11-09): the rematch ceiling, at unit level.

Division rivals meet twice a season. When offense A beats its expectation against defense B in the
first meeting, does it again in the second? Whatever repeats is specific to the pairing (schemes,
one player against another, anything), so it is the ceiling on what any matchup term can add.

Each row is one side: an offense against a defense in one game, 2006-2024 regular season.
- **Outcome:** the offense's EPA per play beyond both units' strength. Strength is each unit's
  season mean (offense EPA per play, defense EPA allowed) leaving out the games being compared, so
  neither game is in the other's expectation.
- **The decomposition.** A side's residual = offense form + defense form + matchup + noise. Form
  drifts within a season, so two games of one offense a few weeks apart share some of it.
  - *real*: cov(residual in meeting 1, residual in meeting 2), same offense and defense;
  - *offense null*: cov(meeting 1, the same offense against another defense at the same gap);
  - *defense null*: cov(meeting 1, another offense against the same defense at the same gap);
  - **matchup variance = real − offense null − defense null.** Its share of the residual's variance
    is the ceiling; its square root is the largest r any matchup predictor could reach on one game.
- 90% intervals resample team-season pairs (2,000 draws).
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/rematch.py
"""

# ruff: noqa: E501
from __future__ import annotations

from collections import defaultdict

import numpy as np
import polars as pl

from pcf.config import get_config

c = pl.col
RNG = np.random.default_rng(20261109)
DRAWS = 2000


def load() -> pl.DataFrame:
    tg = pl.read_parquet(get_config().zone("interim") / "schemes_v2" / "team_game.parquet")
    return (
        tg.select("game_id", "season", "week", off="team", dfn="opp", y="off_epa")
        .drop_nulls("y")
        .filter(c("y").is_not_nan())
    )


class Strength:
    """Season sums per unit, so a unit's mean leaving out any set of games is cheap."""

    def __init__(self, s: pl.DataFrame):
        self.y = {(r["game_id"], r["off"]): r["y"] for r in s.iter_rows(named=True)}
        self.off = defaultdict(list)
        self.dfn = defaultdict(list)
        for r in s.iter_rows(named=True):
            self.off[(r["season"], r["off"])].append((r["game_id"], r["y"]))
            self.dfn[(r["season"], r["dfn"])].append((r["game_id"], r["y"]))

    @staticmethod
    def _mean(rows, skip):
        v = [y for g, y in rows if g not in skip]
        return float(np.mean(v)) if v else np.nan

    def pair(self, season, off, dfn, skip):
        return self._mean(self.off[(season, off)], skip), self._mean(self.dfn[(season, dfn)], skip)


K = 3  # null games per comparison: the K nearest in week to the second game


def nearest(cands, week):
    return sorted(cands, key=lambda r: (abs(r["week"] - week), RNG.random()))[:K]


def comparisons(s: pl.DataFrame, next_season: bool = False):
    """Each first meeting with a second one (the rematch that season, or a meeting the next
    season), and the null games nearest the second meeting's week:
    - offense null: the same offense against other defenses;
    - defense null: other offenses against the same defense;
    - placebo: neither unit (other offenses against other defenses that week)."""
    rows = s.sort("season", "week").to_dicts()
    by_off = defaultdict(list)
    by_dfn = defaultdict(list)
    by_week = defaultdict(list)
    for r in rows:
        by_off[(r["season"], r["off"])].append(r)
        by_dfn[(r["season"], r["dfn"])].append(r)
        by_week[(r["season"], r["week"])].append(r)
    out = []
    for (season, off), games in by_off.items():
        seen = defaultdict(list)
        for r in games:
            seen[r["dfn"]].append(r)
        for dfn, meet in seen.items():
            if next_season:
                later = [r for r in by_off.get((season + 1, off), []) if r["dfn"] == dfn]
                if not later:
                    continue
                pairs = [(meet[-1], later[0])]
            else:
                if len(meet) != 2:
                    continue
                pairs = [tuple(meet)]
            for g1, g2 in pairs:
                s2 = g2["season"]
                o_c = [
                    r
                    for r in by_off[(s2, off)]
                    if r["dfn"] != dfn and r["game_id"] != g1["game_id"]
                ]
                d_c = [
                    r
                    for r in by_dfn[(s2, dfn)]
                    if r["off"] != off and r["game_id"] != g1["game_id"]
                ]
                p_c = [
                    r
                    for r in by_week[(s2, g2["week"])]
                    if r["off"] not in (off, dfn) and r["dfn"] not in (off, dfn)
                ]
                if not o_c or not d_c or not p_c:
                    continue
                out.append(
                    (
                        season,
                        off,
                        dfn,
                        g1,
                        g2,
                        nearest(o_c, g2["week"]),
                        nearest(d_c, g2["week"]),
                        list(RNG.choice(p_c, min(K, len(p_c)), replace=False)),
                    )
                )
    return out


def resid(st: Strength, b, r, skip):
    so, sd = st.pair(r["season"], r["off"], r["dfn"], skip)
    return r["y"] - (b[0] + b[1] * so + b[2] * sd)


def fit(s: pl.DataFrame, st: Strength):
    """Expected EPA per play from the two strengths (each leaving out the game itself)."""
    X, y = [], []
    for r in s.iter_rows(named=True):
        so, sd = st.pair(r["season"], r["off"], r["dfn"], {r["game_id"]})
        if np.isfinite(so) and np.isfinite(sd):
            X.append((1.0, so, sd))
            y.append(r["y"])
    X, y = np.array(X), np.array(y)
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    return b, float(e.var()), float(y.var())


def decompose(a, real, onull, dnull, plac, clusters, label, unit):
    """Covariances, the matchup variance and its interval, by resampling clusters."""

    def stats(i):
        cr = np.cov(a[i], real[i])[0, 1]
        co = np.cov(a[i], onull[i])[0, 1]
        cd = np.cov(a[i], dnull[i])[0, 1]
        v = 0.5 * (a[i].var() + real[i].var())
        return cr, co, cd, cr - co - cd, v, np.cov(a[i], plac[i])[0, 1]

    allidx = np.arange(len(a))
    cr, co, cd, m, v, cp = stats(allidx)
    groups = defaultdict(list)
    for k, g in enumerate(clusters):
        groups[g].append(k)
    keys = list(groups)
    boots = []
    for _ in range(DRAWS):
        pick = RNG.choice(len(keys), len(keys))
        i = np.concatenate([groups[keys[p]] for p in pick])
        boots.append(stats(i))
    boots = np.array(boots)
    lo, hi = np.quantile(boots[:, 3], [0.05, 0.95])
    share = m / v
    slo, shi = np.quantile(boots[:, 3] / boots[:, 4], [0.05, 0.95])
    print(f"\n== {label}: {len(a):,} rematches; residual sd {np.sqrt(v):.3f} {unit}")
    q = np.quantile(boots[:, :3] / boots[:, 4:5], [0.05, 0.95], axis=0)
    print(
        f"   r with the second meeting {cr / v:+.3f} ({q[0, 0]:+.3f} to {q[1, 0]:+.3f}); offense null {co / v:+.3f} ({q[0, 1]:+.3f} to {q[1, 1]:+.3f}); "
        f"defense null {cd / v:+.3f} ({q[0, 2]:+.3f} to {q[1, 2]:+.3f}); placebo (neither unit) {cp / v:+.3f}"
    )
    print(
        f"   matchup variance {m:+.5f} (90% {lo:+.5f} to {hi:+.5f}); share of the residual {share:+.2%} (90% {slo:+.2%} to {shi:+.2%})"
    )
    rmax = np.sqrt(max(share, 0))
    print(
        f"   so the largest r any matchup term could reach on one game: {rmax:.3f} (upper end of the interval: {np.sqrt(max(shi, 0)):.3f})"
    )
    print(f"   resampled draws with matchup variance above zero: {np.mean(boots[:, 3] > 0):.1%}")
    return share, slo, shi


def build(s, st, b, next_season):
    """Residuals for each comparison; each null is the mean residual of its K games."""
    a, real, on, dn, pl_, cl, gaps, seasons = [], [], [], [], [], [], [], []

    def mean_res(games, g1):
        return float(np.nanmean([resid(st, b, r, {g1["game_id"], r["game_id"]}) for r in games]))

    for season, off, dfn, g1, g2, onr, dnr, plr in comparisons(s, next_season):
        skip = {g1["game_id"], g2["game_id"]}
        a.append(resid(st, b, g1, skip))
        real.append(resid(st, b, g2, skip))
        on.append(mean_res(onr, g1))
        dn.append(mean_res(dnr, g1))
        pl_.append(mean_res(plr, g1))
        cl.append((season, *sorted((off, dfn))))
        gaps.append((g2["season"] - g1["season"]) * 18 + g2["week"] - g1["week"])
        seasons.append(season)
    arr = [np.array(x) for x in (a, real, on, dn, pl_)]
    ok = np.logical_and.reduce([np.isfinite(x) for x in arr])
    arr = [x[ok] for x in arr]
    cl = [x for x, k in zip(cl, ok, strict=True) if k]
    return arr, cl, np.array(gaps)[ok], np.array(seasons)[ok]


def unit_level(s: pl.DataFrame):
    st = Strength(s)
    b, ev, yv = fit(s, st)
    print(
        f"sides {s.height:,} (2006-2024 regular season); strength explains r² {1 - ev / yv:.3f} of game EPA per play; weights offense {b[1]:.2f}, defense {b[2]:.2f}"
    )
    (a, real, on, dn, plc), cl, gaps, seasons = build(s, st, b, next_season=False)
    print(
        f"   weeks between meetings: median {np.median(gaps):.0f}, 10th-90th {np.quantile(gaps, 0.1):.0f}-{np.quantile(gaps, 0.9):.0f}; null games per comparison: {K}"
    )
    decompose(a, real, on, dn, plc, cl, "1. The rematch, same season, 2006-2024", "EPA per play")
    for lo, hi in ((2006, 2015), (2016, 2024)):
        w = (seasons >= lo) & (seasons <= hi)
        decompose(
            a[w],
            real[w],
            on[w],
            dn[w],
            plc[w],
            [x for x, k in zip(cl, w, strict=True) if k],
            f"   by era: {lo}-{hi}",
            "EPA per play",
        )
    for lo, hi in ((1, 5), (6, 9), (10, 17)):
        w = (gaps >= lo) & (gaps <= hi)
        decompose(
            a[w],
            real[w],
            on[w],
            dn[w],
            plc[w],
            [x for x, k in zip(cl, w, strict=True) if k],
            f"   by weeks apart: {lo}-{hi}",
            "EPA per play",
        )
    (a, real, on, dn, plc), cl, gaps, seasons = build(s, st, b, next_season=True)
    decompose(
        a,
        real,
        on,
        dn,
        plc,
        cl,
        "2. The last meeting of one season against the first of the next (same two teams)",
        "EPA per play",
    )


def market(s: pl.DataFrame) -> None:
    """3. Does the first meeting's matchup residual predict the rematch's margin beyond the close?
    Known before the rematch: strengths use only that season's games before the rematch's week
    (and leave the first meeting out). The game's term is the home offense's first-meeting
    residual less the away offense's."""
    from pcf.data.tables.store import read_part

    rows = s.to_dicts()
    by_unit = defaultdict(list)
    for r in rows:
        by_unit[("o", r["season"], r["off"])].append(r)
        by_unit[("d", r["season"], r["dfn"])].append(r)

    def before(kind, season, team, week, skip):
        v = [
            r["y"]
            for r in by_unit[(kind, season, team)]
            if r["week"] < week and r["game_id"] not in skip
        ]
        return float(np.mean(v)) if len(v) >= 3 else np.nan

    st = Strength(s)
    b, _, _ = fit(s, st)
    term = {}
    for season, off, dfn, g1, g2, *_ in comparisons(s):
        so = before("o", season, off, g2["week"], {g1["game_id"]})
        sd = before("d", season, dfn, g2["week"], {g1["game_id"]})
        term[(g2["game_id"], off)] = g1["y"] - (b[0] + b[1] * so + b[2] * sd)
    sch = (
        read_part("game", "schedule")
        .select("game_id", "season", "week", "home_team", "away_team")
        .collect()
    )
    res = read_part("game", "result").select("game_id", "home_score", "away_score").collect()
    pre = read_part("game", "pregame").select("game_id", "spread_line").collect()
    g = (
        sch.join(res, on="game_id")
        .join(pre, on="game_id")
        .filter(c("season") <= 2024)
        .with_columns(miss=c("home_score") - c("away_score") - c("spread_line"))
        .to_dicts()
    )
    x, y, wk = [], [], []
    for r in g:
        h, a = term.get((r["game_id"], r["home_team"])), term.get((r["game_id"], r["away_team"]))
        if h is None or a is None or not (np.isfinite(h) and np.isfinite(a)) or r["miss"] is None:
            continue
        x.append(h - a)
        y.append(r["miss"])
        wk.append(r["season"] * 100 + r["week"])
    x, y, wk = np.array(x), np.array(y), np.array(wk)
    rr = float(np.corrcoef(x, y)[0, 1])
    null = []
    for _ in range(DRAWS):
        p = x.copy()
        for k in np.unique(wk):
            i = np.where(wk == k)[0]
            p[i] = RNG.permutation(p[i])
        null.append(np.corrcoef(p, y)[0, 1])
    null = np.array(null)
    slope = np.polyfit(x / x.std(), y, 1)[0]
    q = np.quantile(x, [0.2, 0.8])
    top, bot = y[x >= q[1]], y[x <= q[0]]
    print(f"\n== 3. Against the betting market: {len(x):,} rematch games (2006-2024)")
    print(
        f"   r between the first meeting's matchup term and the rematch's margin beyond the close: {rr:+.3f}; shuffled within week: {np.mean(null >= rr):.1%} at or above"
    )
    print(
        f"   {slope:+.2f} points per sd of the term; top fifth (favours home) home beats the close by {top.mean():+.2f}, covers {np.mean(top > 0):.1%}; "
        f"bottom fifth {bot.mean():+.2f}, home covers {np.mean(bot > 0):.1%}"
    )


def main() -> None:
    s = load()
    unit_level(s)
    market(s)


if __name__ == "__main__":
    main()
