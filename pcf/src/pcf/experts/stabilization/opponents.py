"""I155: a defense's faced rates read through its opponents (decision 0052).

For each defensive team rate, every game's rate is taken less **what the opponent's offense
usually does**, known before kickoff: the opponent's offensive rate this season in its earlier
games, with last season's (pulled by its reliability) as the prior worth k plays. Both versions
are centred by the season's league rate (the whole season's: a description, as CONSISTENCY's
test 2 centres; the opponent's own part reads only its earlier games). Reported, raw against
adjusted:
- the game split (odd against even games of a team-season, as the exploration's);
- k (the 50% point, in plays) from the shared `components`;
- the season r (this season's against next season's, team-seasons).

A description of consistency (CONSISTENCY.md's test 2), fit on 2006-2024; not a forecast.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.experts.stabilization import common as K
from pcf.validation import stabilize as S

c = pl.col


def _league(g: pl.DataFrame) -> pl.DataFrame:
    lm = g.group_by("season").agg(lm=c("num").sum() / c("den").sum())
    return g.join(lm, on="season")


def opponent_usual(tg: pl.DataFrame, measure: str, k: float | None = None) -> pl.DataFrame:
    """Per offense-game: the offense's usual centred rate before that game (this season's earlier
    games plus last season's pulled rate worth k plays). k is fit once on every season (a
    description) unless given."""
    off = _league(tg.filter((c("side") == "off") & (c("measure") == measure)))
    off = off.with_columns(dev=c("num") - c("lm") * c("den")).sort("team", "season", "week")
    ts = off.group_by("team", "season").agg(dv=c("dev").sum(), n=c("den").sum())
    rows = ts.with_columns(x=c("dv") / c("n"), den="n")
    gm = off.join(ts.select("team", "season", rate=c("dv") / c("n")), on=["team", "season"])
    gm = gm.with_columns(num=c("dev"), n_games=pl.len().over("team", "season"))
    if k is None:
        sigma2, tau2 = S.components(rows, gm, key=("team", "season"))
        k = S.k_of(sigma2, tau2)
    prior = ts.select("team", season=c("season") + 1,
                      prior=c("dv") / c("n") * c("n") / (c("n") + k))  # fmt: skip
    off = off.with_columns(
        cdv=c("dev").cum_sum().over("team", "season") - c("dev"),
        cn=c("den").cum_sum().over("team", "season") - c("den"),
    ).join(prior, on=["team", "season"], how="left").with_columns(c("prior").fill_null(0.0))
    return off.select("team", "game_id", usual=(c("cdv") + k * c("prior")) / (c("cn") + k))


def split_r(g: pl.DataFrame, col: str) -> float:
    h = g.sort("week").with_columns(h=c("week").rank("ordinal").over("team", "season") % 2)
    a = h.group_by("team", "season", "h").agg(num=c(col).sum(), den=c("den").sum())
    j = a.filter(c("h") == 1).join(a.filter(c("h") == 0), on=["team", "season"], suffix="_e")
    return float(np.corrcoef(j["num"] / j["den"], j["num_e"] / j["den_e"])[0, 1])


def describe(g: pl.DataFrame, col: str) -> dict:
    ts = g.group_by("team", "season").agg(dv=c(col).sum(), den=c("den").sum())
    rows = ts.with_columns(x=c("dv") / c("den"))
    gm = g.join(rows.select("team", "season", rate="x"), on=["team", "season"]).with_columns(
        num=c(col), n_games=pl.len().over("team", "season"))
    sigma2, tau2 = S.components(rows, gm, key=("team", "season"))
    nxt = rows.select("team", season=c("season") - 1, x2="x")
    p = rows.join(nxt, on=["team", "season"])
    return {"split": split_r(g, col), "k": S.k_of(sigma2, tau2),
            "season_r": float(np.corrcoef(p["x"], p["x2"])[0, 1]), "tau2": tau2}  # fmt: skip


def report(tg: pl.DataFrame, out) -> dict:
    out("", "== I155: a defense's faced rates less its opponents' usual (2006-2024; the opponent's "
        "usual from its earlier games, the league rate the season's)", "", "| Defensive rate | Game split: raw, adjusted | k (plays): "
        "raw, adjusted | Season r: raw, adjusted |", "|---|---|---|---|")  # fmt: skip
    res = {}
    for m in K.TEAM_MEASURES:
        d = _league(tg.filter((c("side") == "def") & (c("measure") == m)))
        d = d.join(opponent_usual(tg, m).rename({"team": "opponent"}), on=["opponent", "game_id"],
                   how="left").with_columns(c("usual").fill_null(0.0))  # fmt: skip
        d = d.with_columns(raw=c("num") - c("lm") * c("den"),
                           adj=c("num") - (c("lm") + c("usual")) * c("den"))  # fmt: skip
        a, b = describe(d, "raw"), describe(d, "adj")
        out(f"| {m} | {a['split']:.2f}, {b['split']:.2f} | {a['k']:.0f}, {b['k']:.0f} | "
            f"{a['season_r']:.2f}, {b['season_r']:.2f} |")
        res[m] = {"raw": a, "adj": b}
    return res
