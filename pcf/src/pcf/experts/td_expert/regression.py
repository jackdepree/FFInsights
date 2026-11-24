"""The regression measure (decision 0043; the brief's Q3): a player's touchdowns over expected
so far, and the share of it he keeps the next season.

- **Over expected, per chance:** (touchdowns - expected touchdowns) / chances in a regular season
  (rushing and receiving: carries and targets; thrown: a quarterback's throws).
- **What he keeps:** next season's touchdowns over expected = k x this season's rate x next
  season's chances. `k` is one number per position, fitted by least squares on the 6 season pairs
  before the tested one (nothing from the tested season or later).
- **Scored** on the tested season's touchdowns over expected (squared error), against keeping all
  of it (k = 1) and keeping none (k = 0), with 90% intervals from whole players resampled.

The answer feeds the forecasts as a prior (`tdoe_ch` in `features.py` is shrunk toward 0 with a
prior of 100 chances, the same idea); this module measures it on its own.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway
from pcf.validation.compare import block_interval

c = pl.col
PAIRS = 6  # earlier season pairs the kept share is fitted on
MIN_CHANCES = {"skill": 30, "thrown": 150}  # this season's, for a rate worth carrying
POSITIONS = {"skill": ("QB", "RB", "WR", "TE"), "thrown": ("QB",)}


def last_week(season: pl.Expr) -> pl.Expr:
    return pl.when(season >= 2021).then(18).otherwise(17)


def player_seasons(seasons: Sequence[int]) -> pl.DataFrame:
    """Regular-season totals per player-season: chances, touchdowns and expected, both kinds."""
    view = Gateway().view(END_OF_TIME, "in_season", {"player_game": ("touchdowns",)})
    pg = view.table("player_game", seasons=list(seasons)).filter(
        c("touchdowns_known_at").is_not_null() & (c("week") <= last_week(c("season"))))  # fmt: skip
    return pg.group_by("gsis_id", "season").agg(
        position=c("position").drop_nulls().mode().first(),
        skill_n=(c("tdx_carries") + c("tdx_targets")).sum(), skill_td=c("tdx_td").sum(),
        skill_x=c("tdx_xtd").sum(), thrown_n=c("tdx_throws").sum(),
        thrown_td=c("tdx_thrown_td").sum(), thrown_x=c("tdx_thrown_xtd").sum(),
    )  # fmt: skip


def pairs(ps: pl.DataFrame, kind: str) -> pl.DataFrame:
    """Each player-season with enough chances, beside his next season (with at least one)."""
    rate = (c(f"{kind}_td") - c(f"{kind}_x")) / c(f"{kind}_n")
    now = ps.filter((c(f"{kind}_n") >= MIN_CHANCES[kind]) & c("position").is_in(POSITIONS[kind]))
    now = now.select("gsis_id", "position", "season", rate=rate, n=c(f"{kind}_n"))
    nxt = ps.filter(c(f"{kind}_n") > 0).select(
        "gsis_id", season=c("season") - 1, n_next=c(f"{kind}_n"),
        y=c(f"{kind}_td") - c(f"{kind}_x"))  # fmt: skip
    return now.join(nxt, on=["gsis_id", "season"], how="inner").with_columns(
        x=c("rate") * c("n_next"), tested=c("season") + 1)  # fmt: skip


def kept(train: pl.DataFrame) -> dict[str, float]:
    """The least-squares share kept, per position (k in y = k x)."""
    out = {}
    for (pos,), d in train.group_by("position"):
        x, y = d["x"].to_numpy(), d["y"].to_numpy()
        out[pos] = float((x * y).sum() / (x * x).sum()) if (x * x).sum() > 0 else 0.0
    return out


def walk(p: pl.DataFrame, tested: Sequence[int]) -> pl.DataFrame:
    """Each tested season scored with the share fitted on the `PAIRS` pairs before it."""
    out = []
    for t in tested:
        train = p.filter(c("tested").is_between(t - PAIRS, t - 1))
        k = kept(train)
        rows = p.filter(c("tested") == t).with_columns(
            k=c("position").replace_strict(k, default=0.0))  # fmt: skip
        out.append(rows.with_columns(fit=c("k") * c("x")))
    return pl.concat(out)


def _gain(rows: pl.DataFrame, base: pl.Expr) -> tuple[float, float, float]:
    per = rows.with_columns(d=(base - c("y")) ** 2 - (c("fit") - c("y")) ** 2,
                            b=(base - c("y")) ** 2).group_by("gsis_id").agg(
        c("d").sum(), c("b").sum())  # fmt: skip
    d, b = per["d"].to_numpy(), per["b"].to_numpy()
    lo, hi = block_interval(d, b)
    return float(d.sum() / b.sum()), lo, hi


def report(seasons: Sequence[int]) -> list[str]:
    """`seasons` are the tested (next) seasons."""
    first = min(seasons) - PAIRS - 1
    ps = player_seasons(range(max(first, 2012), max(seasons) + 1))
    lines = [f"td-expert regression measure: tested seasons {seasons[0]}-{seasons[-1]}; the share "
             f"kept fitted on the {PAIRS} season pairs before each; regular season only", ""]  # fmt: skip
    for kind, label in (("skill", "rushing and receiving"), ("thrown", "thrown, QBs")):
        p = pairs(ps, kind)
        rows = walk(p, seasons)
        lines.append(f"{label} ({rows.height:,} player-seasons with {MIN_CHANCES[kind]}+ chances "
                     f"before them):")  # fmt: skip
        last = kept(p.filter(c("tested").is_between(max(seasons) - PAIRS, max(seasons) - 1)))
        lines.append("  share kept (fit for the last tested season): " + ", ".join(
            f"{k} {v:.2f}" for k, v in sorted(last.items())))  # fmt: skip
        for (pos,), d in sorted(rows.group_by("position"), key=lambda t: t[0]):
            r_ = np.corrcoef(d["rate"], d["y"] / d["n_next"])[0, 1] if d.height > 3 else np.nan
            g0, g1 = _gain(d, pl.lit(0.0)), _gain(d, c("x"))
            lines.append(f"  {pos}: {d.height:,} pairs; this season's rate against next's r = "
                         f"{r_:.2f}; against keep-none {100 * g0[0]:+.2f}% ({100 * g0[1]:+.2f} to "
                         f"{100 * g0[2]:+.2f}); against keep-all {100 * g1[0]:+.1f}% "
                         f"({100 * g1[1]:+.1f} to {100 * g1[2]:+.1f})")  # fmt: skip
        g0, g1 = _gain(rows, pl.lit(0.0)), _gain(rows, c("x"))
        beats = g0[1] > 0 and g1[1] > 0
        lines.append(f"  everyone: against keep-none {100 * g0[0]:+.2f}% ({100 * g0[1]:+.2f} to "
                     f"{100 * g0[2]:+.2f}); against keep-all {100 * g1[0]:+.1f}% ({100 * g1[1]:+.1f}"
                     f" to {100 * g1[2]:+.1f}); beats both, intervals clear: {beats}")  # fmt: skip
        by = rows.group_by("tested").agg(
            k=c("k").mean(), g=1 - ((c("fit") - c("y")) ** 2).sum() / (c("y") ** 2).sum()).sort(
            "tested")  # fmt: skip
        lines.append("  by season (gain on keep-none): " + ", ".join(
            f"{r['tested']} {100 * r['g']:+.1f}%" for r in by.iter_rows(named=True)))  # fmt: skip
        lines.append("")
    return lines
