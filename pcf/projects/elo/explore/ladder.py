"""Elo exploration, rungs 0-1: how near the closing line does a simple rating get?

Rungs, each predicting the home margin (and the total where it can) before every game:
- `home`: home field only (the mean home margin of the last 3 seasons); the total is last
  season's mean total.
- `last_season`: home field plus last season's point differential per game, scaled.
- `chess`: chess Elo on win, loss or tie only; margin = rating gap / 25 (FiveThirtyEight's rate).
- `mov`: the CEO's base. Ratings in points; after each game both teams move by k times the
  miss on the margin.
- `mov_pull`: `mov` plus the usual one-third pull toward average between seasons.
- `fte`: FiveThirtyEight-style: win/loss Elo with their margin-of-victory multiplier, K=20, a
  one-third pull, margin = gap / 25.
- `off_def`: points Elo with an offense and a defense rating per team, so it predicts the total.

Ratings are frozen for a week: every game in week w uses ratings after week w-1 (the Tuesday
moment), so no game sees a result from its own week. Home field is the mean home margin of the
previous 3 seasons, known before each season. Settings (k, scale) are tuned on 2002-2015 and
reported on 2016-2024 with the same games for every rung. The vault (2025) isn't read.

Run from pcf/:
.venv/Scripts/python.exe projects/elo/explore/ladder.py
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
import polars as pl

from pcf.data.tables.store import load

c = pl.col
FIRST, TUNE_FROM, REPORT_FROM, LAST = 1999, 2002, 2016, 2024
DRAWS = 2000
RNG = np.random.default_rng(20261107)


def games() -> pl.DataFrame:
    g = load("game").filter(c("season").is_between(FIRST, LAST) & c("result").is_not_null())
    return (
        g.sort("kickoff", "game_id")
        .with_row_index("order")
        .select(
            "order",
            "game_id",
            "season",
            "week",
            "game_type",
            "home_team",
            "away_team",
            neutral=c("location") == "Neutral",
            margin=c("result").cast(pl.Float64),
            total=c("total").cast(pl.Float64),
            home_pts=c("home_score").cast(pl.Float64),
            away_pts=c("away_score").cast(pl.Float64),
            spread="spread_line",
            total_line="total_line",
        )
    )


def season_priors(g: pl.DataFrame) -> dict[int, dict[str, float]]:
    """Known before each season: home field (mean home margin, previous 3 seasons, non-neutral),
    last season's mean total, and each team's point differential per game last season."""
    out: dict[int, dict[str, float]] = {}
    for s in range(FIRST, LAST + 1):
        past = g.filter(c("season").is_between(s - 3, s - 1) & ~c("neutral"))
        last = g.filter(c("season") == s - 1)
        hfa = float(past["margin"].mean()) if past.height else 2.5
        tot = float(last["total"].mean()) if last.height else 41.0
        pd = defaultdict(float)
        if last.height:
            both = (
                pl.concat(
                    [
                        last.select(team="home_team", d="margin"),
                        last.select(team="away_team", d=-c("margin")),
                    ]
                )
                .group_by("team")
                .agg(c("d").mean())
            )
            pd.update(dict(zip(both["team"], both["d"], strict=True)))
        out[s] = {"hfa": hfa, "total": tot, "pd": pd}
    return out


def weekly(g: pl.DataFrame):
    """Games grouped by (season, week), in order."""
    for (s, w), wk in g.group_by(["season", "week"], maintain_order=True):
        yield s, w, wk.to_dicts()


def run(g: pl.DataFrame, priors, kind: str, **p) -> pl.DataFrame:
    """Walk the games week by week; return each game's pre-game home margin (and total).

    Hooks for the hunch variants: `signal` (the column the margin ratings learn from, default
    `margin`), `signals` (the home and away points the offense/defense ratings learn from),
    `pull_fn(season, team)` (a team's own pull toward average), `step_fn(game, team)` (a
    multiplier on a team's step size for one game), `adj_fn(game)` (points added to the home
    margin before the game, for the margin ratings)."""
    sig = p.get("signal", "margin")
    sh, sa = p.get("signals", ("home_pts", "away_pts"))
    pull_fn = p.get("pull_fn")
    step_fn = p.get("step_fn") or (lambda _x, _t: 1.0)
    adj_fn = p.get("adj_fn") or (lambda _x: 0.0)
    r: dict[str, float] = defaultdict(float)  # overall rating (points or Elo points)
    o: dict[str, float] = defaultdict(float)  # offense (off_def)
    d: dict[str, float] = defaultdict(float)  # defense (off_def)
    season = None
    mu = None
    rows = []
    for s, _w, wk in weekly(g.sort("order")):  # joins may reorder rows; the walk mustn't
        pr = priors[s]
        if s != season:
            pull = p.get("pull", 0.0)
            for t in list(r):
                r[t] *= 1 - (pull_fn(s, t) if pull_fn else pull)
            for t in list(o):
                o[t] *= 1 - (pull_fn(s, t) if pull_fn else pull)
                d[t] *= 1 - (pull_fn(s, t) if pull_fn else pull)
            mu = pr["total"] / 2
            season = s
        if "snap" in p:  # ratings as they stood before this week (for the long horizon)
            p["snap"][(s, _w)] = dict(r)
        preds = []
        for x in wk:
            h, a = x["home_team"], x["away_team"]
            hfa = 0.0 if x["neutral"] else pr["hfa"]
            tot = None
            if kind == "home":
                m = hfa
                tot = pr["total"]
            elif kind == "last_season":
                m = hfa + p["b"] * (pr["pd"][h] - pr["pd"][a])
            elif kind in ("chess", "fte"):
                m = (r[h] - r[a]) / 25 + hfa
            elif kind in ("margin", "margin_pull"):
                m = r[h] - r[a] + hfa + adj_fn(x)
            elif kind == "off_def":
                ph = mu + o[h] - d[a] + hfa / 2
                pa = mu + o[a] - d[h] - hfa / 2
                m, tot = ph - pa, ph + pa
            preds.append((x, m, tot))
            rows.append({"game_id": x["game_id"], "pred": m, "pred_total": tot})
        # update after the week
        for x, m, _tot in preds:
            h, a = x["home_team"], x["away_team"]
            hfa = 0.0 if x["neutral"] else pr["hfa"]
            if kind in ("margin", "margin_pull"):
                e = x[sig] - m
                r[h] += p["k"] * step_fn(x, h) * e
                r[a] -= p["k"] * step_fn(x, a) * e
            elif kind in ("chess", "fte"):
                gap = r[h] - r[a] + hfa * 25
                exp = 1 / (1 + 10 ** (-gap / 400))
                res = 1.0 if x["margin"] > 0 else 0.0 if x["margin"] < 0 else 0.5
                mult = 1.0
                if kind == "fte":
                    win_gap = gap if x["margin"] > 0 else -gap
                    mult = math.log(abs(x["margin"]) + 1) * 2.2 / (win_gap * 0.001 + 2.2)
                step = p["K"] * mult * (res - exp)
                r[h] += step
                r[a] -= step
            elif kind == "off_def":
                ph = mu + o[h] - d[a] + hfa / 2
                pa = mu + o[a] - d[h] - hfa / 2
                eh, ea = x[sh] - ph, x[sa] - pa
                kh, ka = p["k"] * step_fn(x, h), p["k"] * step_fn(x, a)
                o[h] += kh * eh
                d[a] -= ka * eh
                o[a] += ka * ea
                d[h] -= kh * ea
                mu += p["k_mu"] * (eh + ea) / 2
    return pl.DataFrame(rows)


def mae(g: pl.DataFrame, pred: pl.DataFrame, lo: int, hi: int, col="pred", y="margin") -> float:
    j = g.join(pred, on="game_id").filter(c("season").is_between(lo, hi))
    return float((j[y] - j[col]).abs().mean())


def tune(g, priors, kind, grid: list[dict]) -> dict:
    best = min(grid, key=lambda p: mae(g, run(g, priors, kind, **p), TUNE_FROM, REPORT_FROM - 1))
    return best


def interval(errs: pl.DataFrame, a: str, b: str) -> tuple[float, float, float]:
    """Mean of (|miss a| - |miss b|) by whole weeks, with a 90% week-block interval."""
    wk = errs.group_by("season", "week").agg(n=pl.len(), diff=(c(a).abs() - c(b).abs()).sum())
    n, diff = wk["n"].to_numpy(), wk["diff"].to_numpy()
    idx = RNG.integers(0, len(n), size=(DRAWS, len(n)))
    boot = diff[idx].sum(1) / n[idx].sum(1)
    return float(diff.sum() / n.sum()), *np.quantile(boot, [0.05, 0.95])


def main() -> None:
    g = games()
    priors = season_priors(g)
    print(f"games {g.height}, report {g.filter(c('season') >= REPORT_FROM).height}")
    hfa = {s: round(priors[s]["hfa"], 2) for s in range(REPORT_FROM, LAST + 1)}
    print("home field by season (prev 3 seasons):", hfa)

    specs = {
        "home": ("home", [{}]),
        "last_season": ("last_season", [{"b": b} for b in np.arange(0.1, 0.81, 0.05)]),
        "chess": ("chess", [{"K": k} for k in (10, 15, 20, 25, 30, 40, 50)]),
        "mov": ("margin", [{"k": k} for k in np.arange(0.02, 0.161, 0.01)]),
        "mov_pull": (
            "margin_pull",
            [
                {"k": k, "pull": pu}
                for k in np.arange(0.03, 0.131, 0.01)
                for pu in (0.2, 1 / 3, 0.5)
            ],
        ),
        "fte": ("fte", [{"K": 20, "pull": 1 / 3}]),
        "off_def": (
            "off_def",
            [
                {"k": k, "k_mu": km, "pull": pu}
                for k in (0.03, 0.05, 0.07, 0.09)
                for km in (0.0, 0.005, 0.01)
                for pu in (0.0, 1 / 3)
            ],
        ),
    }
    preds, chosen = {}, {}
    for name, (kind, grid) in specs.items():
        p = tune(g, priors, kind, grid)
        chosen[name] = {k: round(float(v), 3) for k, v in p.items()}
        preds[name] = run(g, priors, kind, **p).rename(
            {"pred": f"{name}", "pred_total": f"{name}_total"}
        )

    rep = g.filter(c("season") >= REPORT_FROM)
    for pr in preds.values():
        rep = rep.join(pr, on="game_id")
    errs = rep.select(
        "season",
        "week",
        close=c("margin") - c("spread"),
        **{n: c("margin") - c(n) for n in preds},
        close_t=c("total") - c("total_line"),
        **{f"{n}_t": c("total") - c(f"{n}_total") for n in ("home", "off_def")},
    )
    close = float(errs["close"].abs().mean())
    close_t = float(errs["close_t"].abs().mean())
    print(
        f"\nreport games {rep.height}; the close misses margin by {close:.2f}, total {close_t:.2f}"
    )
    print("\nMARGIN  (mean miss, points; gap to close; gap to `mov` with 90% interval)")
    for n in preds:
        m = float(errs[n].abs().mean())
        gap = interval(errs, n, "mov")
        band = f"{gap[0]:+.3f} [{gap[1]:+.3f}, {gap[2]:+.3f}]"
        print(f"  {n:12s} {m:6.2f}  close+{m - close:5.2f}  vs mov {band}  {chosen[n]}")
    print("\nTOTAL")
    for n in ("home", "off_def"):
        m = float(errs[f"{n}_t"].abs().mean())
        print(f"  {n:12s} {m:6.2f}  close+{m - close_t:5.2f}")
    gap = interval(errs, "off_def_t", "home_t")
    print(f"  off_def vs home on totals {gap[0]:+.3f} [{gap[1]:+.3f}, {gap[2]:+.3f}]")

    # early season (weeks 1-4) vs rest, margin
    print("\nWEEKS 1-4 vs 5+ (margin)")
    for part, f in (("1-4", c("week") <= 4), ("5+", c("week") > 4)):
        e = errs.filter(f)
        line = "  ".join(f"{n} {float(e[n].abs().mean()):.2f}" for n in ("close", *preds))
        print(f"  {part}: {line}")

    # by season
    print("\nBY SEASON (margin): close / mov_pull / off_def")
    for s, e in errs.group_by("season", maintain_order=True):
        line = " ".join(f"{float(e[n].abs().mean()):.2f}" for n in ("close", "mov_pull", "off_def"))
        print(f"  {s[0]}: {line}")


if __name__ == "__main__":
    main()


# ------------------------------------------------------------------ shared by the hunch scripts
RUNG1 = {"k": 0.06, "pull": 0.5}  # margin Elo with a half pull (F3)
RUNG1_OD = {"k": 0.05, "k_mu": 0.0, "pull": 1 / 3}  # offense and defense ratings (F4)


def versus_rung1(
    g: pl.DataFrame,
    priors,
    kind: str,
    grid: list[dict],
    lo: int = REPORT_FROM,
    tune_lo: int = TUNE_FROM,
) -> dict:
    """Tune a variant on the tuning seasons, then score it against rung 1 on `lo`-2024: mean miss
    on the margin (and the total for off_def), and the gap to rung 1 with a 90% week-block
    interval. Negative gaps mean the variant misses by less."""
    base_kind, base = ("off_def", RUNG1_OD) if kind == "off_def" else ("margin_pull", RUNG1)
    best = min(grid, key=lambda p: mae(g, run(g, priors, kind, **p), tune_lo, lo - 1))
    a = run(g, priors, kind, **best).rename({"pred": "v", "pred_total": "v_t"})
    b = run(g, priors, base_kind, **base).rename({"pred": "b", "pred_total": "b_t"})
    j = g.filter(c("season").is_between(lo, LAST)).join(a, on="game_id").join(b, on="game_id")
    e = j.select(
        "season",
        "week",
        v=c("margin") - c("v"),
        b=c("margin") - c("b"),
        close=c("margin") - c("spread"),
    )
    out = {
        "chosen": {k: v for k, v in best.items() if not callable(v)},
        "games": j.height,
        "close": float(e["close"].abs().mean()),
        "rung1": float(e["b"].abs().mean()),
        "variant": float(e["v"].abs().mean()),
        "gap": interval(e, "v", "b"),
    }
    if kind == "off_def":
        et = j.select(
            "season",
            "week",
            v=c("total") - c("v_t"),
            b=c("total") - c("b_t"),
            close=c("total") - c("total_line"),
        )
        out |= {
            "close_t": float(et["close"].abs().mean()),
            "rung1_t": float(et["b"].abs().mean()),
            "variant_t": float(et["v"].abs().mean()),
            "gap_t": interval(et, "v", "b"),
        }
    return out


def show(name: str, r: dict) -> None:
    g = r["gap"]
    print(
        f"  {name:28s} margin {r['variant']:.3f} (rung 1 {r['rung1']:.3f}, close {r['close']:.3f})"
        f"  gap {g[0]:+.3f} [{g[1]:+.3f}, {g[2]:+.3f}]  {r['chosen']}"
    )
    if "gap_t" in r:
        t = r["gap_t"]
        print(
            f"  {'':28s} total  {r['variant_t']:.3f} (rung 1 {r['rung1_t']:.3f}, close"
            f" {r['close_t']:.3f})  gap {t[0]:+.3f} [{t[1]:+.3f}, {t[2]:+.3f}]"
        )
