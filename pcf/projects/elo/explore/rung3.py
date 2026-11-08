"""Rung 3: rung 1 plus what held, then win chances, ranges and the long horizon.

1. The combined margin rating: rung 1 (margin Elo, half pull) learning from a blend of the margin
   and average win probability (weight w on the margin, H3), with H1's pre-game adjustments
   (c_q per usual QB missing, c_s per unit of same-team share) and finishing (F19: c_f times the
   gap in each team's running finishing average). The settings are re-chosen before every
   season from 2016 on, by the mean miss on all seasons from 2013 up to it (H1's data starts in
   2013). Scored on 2016-2024 against rung 1 and the close.
2. Win chances: the forecast margin through a normal curve whose spread is the misses' standard
   deviation on all earlier seasons. Log loss and Brier score against the no-vig closing line;
   calibration by tenths.
3. Ranges: q10 and q90 from the earlier seasons' misses; coverage on margins and totals (totals
   from rung 1's offense and defense ratings).
4. Long horizon: before each week, wins over the next 3 games and the rest of the regular season,
   from the ratings as they stood (no future results, no future injuries). Against the
   yardstick: the current win rate pulled toward .500 by k games, k picked on 2002-2015.

The vault (2025) isn't read. Run from pcf/:
.venv/Scripts/python.exe projects/elo/explore/rung3.py
"""

# ruff: noqa: E501
from __future__ import annotations

import itertools
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
import h2_h1_same_team as H1  # noqa: E402
import h3_winprob as H3  # noqa: E402
import ladder as L  # noqa: E402

from pcf.baselines.market import no_vig_home  # noqa: E402
from pcf.data.tables.store import load  # noqa: E402

c = pl.col
FIRST_H1 = 2013
GRID = {
    "w": (1.0, 0.75),
    "cq": (0, 2, 3, 4),
    "cs": (0, 5, 10, 20),
    "cf": (0, 2, 4),
}
KF = 0.05  # finishing's running-average step


def phi(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1 + np.vectorize(math.erf)(x / math.sqrt(2)))


def with_inputs(g: pl.DataFrame) -> pl.DataFrame:
    """Add same-team share, QB missing, the win-probability blend inputs and finishing."""
    st = H1.same_team(H1.player_games())
    for side in ("home", "away"):
        g = g.join(
            st.rename(
                {"team": f"{side}_team", "share": f"{side[0]}_share", "qb_out": f"{side[0]}_qb"}
            ),
            on=["game_id", f"{side}_team"],
            how="left",
        )
    g = g.with_columns(c("h_share", "a_share").fill_null(1.0), c("h_qb", "a_qb").fill_null(0.0))
    g = g.join(H3.avg_wp().with_columns(c("wp").round(6)), on="game_id", how="left")
    tune = g.filter(c("season").is_between(L.TUNE_FROM, L.REPORT_FROM - 1))
    x, y = (tune["wp"] - 0.5).to_numpy(), tune["margin"].to_numpy()
    b = float((x * y).sum() / (x * x).sum())
    g = g.with_columns(wp_pts=((c("wp") - 0.5) * b).fill_null(c("margin")))
    # finishing: each team's running average of (result - its average win probability), frozen
    # before each week, half pull between seasons
    fin: dict[str, float] = defaultdict(float)
    season, rows = None, []
    for (s, _w), wk in g.sort("order").group_by(["season", "week"], maintain_order=True):
        if s != season:
            for t in list(fin):
                fin[t] *= 0.5
            season = s
        games = wk.to_dicts()
        for z in games:
            rows.append(
                {
                    "game_id": z["game_id"],
                    "h_fin": fin[z["home_team"]],
                    "a_fin": fin[z["away_team"]],
                }
            )
        for z in games:
            if z["wp"] is None:
                continue
            res = 1.0 if z["margin"] > 0 else 0.0 if z["margin"] < 0 else 0.5
            fin[z["home_team"]] += KF * ((res - z["wp"]) - fin[z["home_team"]])
            fin[z["away_team"]] += KF * (((1 - res) - (1 - z["wp"])) - fin[z["away_team"]])
    return g.join(pl.DataFrame(rows), on="game_id")


def combined(g: pl.DataFrame, priors) -> pl.DataFrame:
    """Every grid point's forecasts, then each season's from the point that did best before it."""
    preds = {}
    for w in GRID["w"]:
        g = g.with_columns((w * c("margin") + (1 - w) * c("wp_pts")).alias(f"sig_{w}"))
    for w, cq, cs, cf in itertools.product(*GRID.values()):

        def adj(x, cq=cq, cs=cs, cf=cf):
            return (
                cq * (x["a_qb"] - x["h_qb"])
                + cs * (x["h_share"] - x["a_share"])
                + cf * (x["h_fin"] - x["a_fin"])
            )

        p = {"k": L.RUNG1["k"], "pull": L.RUNG1["pull"], "signal": f"sig_{w}", "adj_fn": adj}
        preds[(w, cq, cs, cf)] = L.run(g, priors, "margin_pull", **p).select("game_id", "pred")
    keyed = g.select("game_id", "season", "margin")
    miss = {
        k: keyed.join(v, on="game_id").with_columns(e=(c("margin") - c("pred")).abs())
        for k, v in preds.items()
    }
    out, chosen = [], {}
    for s in range(L.REPORT_FROM, L.LAST + 1):
        # rounded so float noise can't flip near-ties; ties go to the earlier (simpler) setting
        best = min(
            miss,
            key=lambda k: round(
                float(miss[k].filter(c("season").is_between(FIRST_H1, s - 1))["e"].mean()), 3
            ),
        )
        chosen[s] = best
        out.append(miss[best].filter(c("season") == s).select("game_id", r3=c("pred")))
    print("settings chosen before each season (w, c_q, c_s, c_f):")
    for s, k in chosen.items():
        print(f"  {s}: {k}")
    fixed = {k: float(v.filter(c("season") >= L.REPORT_FROM)["e"].mean()) for k, v in miss.items()}
    top = sorted(fixed.items(), key=lambda kv: kv[1])[:3]
    print(
        "best fixed settings on 2016-2024 with hindsight (not a result):",
        [(k, round(v, 3)) for k, v in top],
    )
    return pl.concat(out)


def walk_sd(df: pl.DataFrame, pred: str, y: str) -> pl.DataFrame:
    """Per season: the misses' sd, q10 and q90 on all earlier seasons (from 2002)."""
    rows = []
    for s in range(L.REPORT_FROM, L.LAST + 1):
        e = df.filter(c("season").is_between(L.TUNE_FROM, s - 1)).select(e=c(y) - c(pred))["e"]
        rows.append(
            {
                "season": s,
                "sd": float(e.std()),
                "q10": float(e.quantile(0.1)),
                "q90": float(e.quantile(0.9)),
            }
        )
    return pl.DataFrame(rows)


def main() -> None:
    lines = load("game").select("game_id", "home_moneyline", "away_moneyline")
    g = with_inputs(L.games()).join(lines, on="game_id", how="left")
    priors = L.season_priors(g)
    r3 = combined(g, priors)
    snap: dict = {}
    r1 = (
        L.run(g, priors, "margin_pull", **L.RUNG1, snap=snap)
        .rename({"pred": "r1"})
        .drop("pred_total")
    )
    od = L.run(g, priors, "off_def", **L.RUNG1_OD).select("game_id", r1_t="pred_total")
    j = g.join(r1, on="game_id").join(od, on="game_id").join(r3, on="game_id", how="left")

    rep = j.filter(c("season") >= L.REPORT_FROM)
    e = rep.select(
        "season",
        "week",
        r3=c("margin") - c("r3"),
        r1=c("margin") - c("r1"),
        close=c("margin") - c("spread"),
    )
    gap = L.interval(e, "r3", "r1")
    print(
        f"\nMARGIN 2016-2024: rung 3 {float(e['r3'].abs().mean()):.3f}, rung 1 {float(e['r1'].abs().mean()):.3f}, "
        f"close {float(e['close'].abs().mean()):.3f}; rung 3 - rung 1 {gap[0]:+.3f} [{gap[1]:+.3f}, {gap[2]:+.3f}]"
    )
    e20 = e.filter(c("season") >= 2020)
    gap20 = L.interval(e20, "r3", "r1")
    print(
        f"  2020-2024: rung 3 {float(e20['r3'].abs().mean()):.3f}, rung 1 {float(e20['r1'].abs().mean()):.3f}, "
        f"close {float(e20['close'].abs().mean()):.3f}; gap {gap20[0]:+.3f} [{gap20[1]:+.3f}, {gap20[2]:+.3f}]"
    )

    # ------------------------------------------------------------------ win chances and ranges
    sd_m = walk_sd(j.with_columns(r3=c("r3").fill_null(c("r1"))), "r3", "margin")
    sd_t = walk_sd(j, "r1_t", "total")
    rep = rep.join(sd_m, on="season").join(
        sd_t.rename({"sd": "sd_t", "q10": "q10_t", "q90": "q90_t"}), on="season"
    )
    rep = rep.filter(c("margin") != 0).with_columns(
        win=(c("margin") > 0).cast(pl.Float64),
        market=no_vig_home(c("home_moneyline"), c("away_moneyline")),
    )
    p = phi((rep["r3"] / rep["sd"]).to_numpy())
    y = rep["win"].to_numpy()
    m = rep["market"].to_numpy()
    ok = ~np.isnan(m)
    ll = lambda q: float(-np.mean(y[ok] * np.log(q[ok]) + (1 - y[ok]) * np.log(1 - q[ok])))  # noqa: E731
    br = lambda q: float(np.mean((q[ok] - y[ok]) ** 2))  # noqa: E731
    print(
        f"\nWIN CHANCES 2016-2024 ({ok.sum()} games, ties out): log loss rung 3 {ll(p):.4f}, close {ll(m):.4f}; "
        f"Brier {br(p):.4f}, close {br(m):.4f}"
    )
    bins = np.clip((p * 10).astype(int), 0, 9)
    print("  calibration (forecast tenth: mean forecast / home win rate / games):")
    for b_ in range(10):
        sel = bins == b_
        if sel.sum() >= 20:
            print(
                f"    {b_ / 10:.1f}-{(b_ + 1) / 10:.1f}: {p[sel].mean():.3f} / {y[sel].mean():.3f} / {sel.sum()}"
            )

    full = (
        j.filter(c("season") >= L.REPORT_FROM)
        .join(sd_m, on="season")
        .join(sd_t.rename({"sd": "sd_t", "q10": "q10_t", "q90": "q90_t"}), on="season")
    )
    cov = full.select(
        m=((c("margin") >= c("r3") + c("q10")) & (c("margin") <= c("r3") + c("q90"))).mean(),
        t=((c("total") >= c("r1_t") + c("q10_t")) & (c("total") <= c("r1_t") + c("q90_t"))).mean(),
        width_m=(c("q90") - c("q10")).mean(),
        width_t=(c("q90_t") - c("q10_t")).mean(),
    )
    print(
        f"\nRANGES q10-q90 2016-2024: margin coverage {cov['m'][0]:.1%} (width {cov['width_m'][0]:.1f} points), "
        f"total coverage {cov['t'][0]:.1%} (width {cov['width_t'][0]:.1f})"
    )

    # ------------------------------------------------------------------------ long horizon
    reg = g.filter(c("game_type") == "REG").select(
        "game_id", "season", "week", "home_team", "away_team", "neutral", "margin"
    )
    sides = pl.concat(
        [
            reg.select(
                "season",
                "week",
                team="home_team",
                opp="away_team",
                home=~c("neutral"),
                away=pl.lit(False),
                neutral="neutral",
                res=pl.when(c("margin") > 0)
                .then(1.0)
                .when(c("margin") < 0)
                .then(0.0)
                .otherwise(0.5),
            ),
            reg.select(
                "season",
                "week",
                team="away_team",
                opp="home_team",
                home=pl.lit(False),
                away=~c("neutral"),
                neutral="neutral",
                res=pl.when(c("margin") < 0)
                .then(1.0)
                .when(c("margin") > 0)
                .then(0.0)
                .otherwise(0.5),
            ),
        ]
    ).sort("season", "team", "week")
    sd_all = {r["season"]: r["sd"] for r in sd_m.iter_rows(named=True)}
    rows = []
    for (s, t), sg in sides.group_by("season", "team"):
        if s < L.TUNE_FROM:
            continue
        sg = sg.sort("week").to_dicts()
        sd = sd_all.get(s, 13.5)
        hfa = priors[s]["hfa"]
        for i, now in enumerate(sg):
            r = snap.get((s, now["week"]))
            if r is None:
                continue
            rest = sg[i:]
            pr = []
            for z in rest:
                edge = (
                    r.get(t, 0.0)
                    - r.get(z["opp"], 0.0)
                    + (hfa if z["home"] else -hfa if z["away"] else 0.0)
                )
                pr.append(0.5 * (1 + math.erf(edge / sd / math.sqrt(2))))
            done = sg[:i]
            rows.append(
                {
                    "season": s,
                    "week": now["week"],
                    "n_done": len(done),
                    "w_done": sum(z["res"] for z in done),
                    "elo3": sum(pr[:3]),
                    "act3": sum(z["res"] for z in rest[:3]),
                    "n3": len(rest[:3]),
                    "elo_rest": sum(pr),
                    "act_rest": sum(z["res"] for z in rest),
                    "n_rest": len(rest),
                }
            )
    lh = pl.DataFrame(rows)

    def yard(k):
        rate = (c("w_done") + 0.5 * k) / (c("n_done") + k)
        return rate

    best_k = min(
        (2, 4, 8, 16),
        key=lambda k: float(
            lh.filter(c("season") < L.REPORT_FROM)
            .select(((yard(k) * c("n_rest")) - c("act_rest")).abs().mean())
            .item()
        ),
    )
    lh = lh.with_columns(y3=yard(best_k) * c("n3"), y_rest=yard(best_k) * c("n_rest"))
    out = lh.filter(c("season") >= L.REPORT_FROM)
    print(
        f"\nLONG HORIZON 2016-2024 (yardstick pulls the win rate toward .500 by {best_k} games), mean miss in wins:"
    )
    for label, f in (
        ("all weeks", pl.lit(True)),
        ("before week 1", c("n_done") == 0),
        ("after 4 games", c("n_done") == 4),
        ("after 8 games", c("n_done") == 8),
        ("after 12 games", c("n_done") == 12),
    ):
        o = out.filter(f)
        print(
            f"  {label:15s} next 3: Elo {float((o['elo3'] - o['act3']).abs().mean()):.3f}, yardstick "
            f"{float((o['y3'] - o['act3']).abs().mean()):.3f} | rest of season: Elo "
            f"{float((o['elo_rest'] - o['act_rest']).abs().mean()):.3f}, yardstick "
            f"{float((o['y_rest'] - o['act_rest']).abs().mean()):.3f}  ({o.height} team-weeks)"
        )


if __name__ == "__main__":
    main()
