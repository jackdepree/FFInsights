"""The published trait table (decision 0051, calls 1 and 19-21): one row per player-season,
trait and group, every number made from seasons up to that row's season only.

Columns: gsis_id, season, team, group, trait, chances (`den`), rate, mu (the group's mean that
season), rate_c (centred), k, reliability n / (n + k), shrunk (rate scale) with shrunk_lo and
shrunk_hi (90% for his true rate this season: sd = sqrt(sigma2 / (n + k))), shrunk_c (centred),
rung (the trait's champion), next_c (the champion's forecast for next season, centred) with
next_q10 and next_q90 (80%, at this season's chances), owner (player or team, from the share
kept) and share_kept, as_of, train_end, cadence.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from pcf.experts.skill_over_expected import traits as T

c = pl.col
Z90, Z80 = 1.6448536269514722, 1.2815515655446004


def rows_for(rows: pl.DataFrame, games: pl.DataFrame, p: pl.DataFrame, rung: str,
             owner: str, share: float, known: pl.DataFrame,
             k_rows: pl.DataFrame | None = None) -> pl.DataFrame:  # fmt: skip
    """`rows`: one trait and group's season rows; `p`: its walk (`traits.walk`), whose pairs
    give the slope and the left-over spread for each season's forecast; `rung`: raw, m1, flat or
    pull (the trait's champion; split's forecast needs next season's team, so its rows publish
    the rung below and the split's slopes are in the report); `k_rows`: all the trait's groups,
    for its one k (`traits.pairs`)."""
    trait = T.BY_NAME[rows["trait"][0]]
    out = []
    pr = p.drop_nulls(["m1"])
    for s in sorted(rows["season"].unique().to_list()):
        tr = (rows if k_rows is None else k_rows).filter(c("season") <= s)
        sigma2, tau2 = T.components(tr, T.game_rows(games, tr, trait))
        k = sigma2 / tau2
        a = rows.filter(c("season") == s).with_columns(
            k=pl.lit(k), reliability=c("den") / (c("den") + k),
        ).with_columns(shrunk_c=c("reliability") * c("x"),
                       sd=(sigma2 / (c("den") + k)).sqrt())  # fmt: skip
        fit = pr.filter(c("season") < s)  # pairs whose target season is s or earlier
        slope, v, scale = 1.0, float("nan"), float("nan")
        if fit.height >= 30:
            y, w = fit["y"].to_numpy(), fit["w"].to_numpy()
            m = fit["x" if rung in ("raw", "flat") else "m1"].to_numpy()
            if rung in ("pull", "flat"):
                slope = float(np.sum(w * m * y) / np.sum(w * m * m))
            s2 = fit["sigma2"].to_numpy()
            resid = (y - slope * m) ** 2 - s2 / w
            v = max(float(np.average(resid, weights=w)), 1e-12)
            z = np.abs(y - slope * m) / np.sqrt(v + s2 / w)
            scale = float(np.quantile(z, 0.8)) / Z80  # the conformal scale (evaluate.ranges)
        spread = scale * (pl.lit(v) + sigma2 / c("den")).sqrt()
        if rung == "flat":  # one pull for everyone: no per-player interval (call 30)
            a = a.with_columns(shrunk_c=slope * c("x"), sd=pl.lit(None, dtype=pl.Float64))
            slope = 1.0
        base = c("x") if rung == "raw" else c("shrunk_c")
        a = (
            a.with_columns(next_c=slope * base)
            .with_columns(next_q10=c("next_c") - Z80 * spread, next_q90=c("next_c") + Z80 * spread)
            .with_columns(c("next_q10", "next_q90").fill_nan(None))
        )  # no earlier pairs: no range
        out.append(a)
    h = pl.concat(out).join(known.select("season", as_of="known_at"), on="season", how="left")
    return h.select(
        "gsis_id", "season", "team", "group", "trait", chances="den", rate="rate", mu="mu",
        rate_c="x", k="k", reliability="reliability",
        shrunk=c("mu") + c("shrunk_c"), shrunk_lo=c("mu") + c("shrunk_c") - Z90 * c("sd"),
        shrunk_hi=c("mu") + c("shrunk_c") + Z90 * c("sd"), shrunk_c="shrunk_c",
        rung=pl.lit(rung), next_c="next_c", next_q10="next_q10", next_q90="next_q90",
        owner=pl.lit(owner), share_kept=pl.lit(share), as_of="as_of", train_end="as_of",
        cadence=pl.lit("retrospective"),
    )  # fmt: skip
