"""Finishing schemes-v2 (2026-11-10): what the opening-coach rule changed, and rung 2 against the blend.

From the saved walk-forward histories (2016-2024, the harness's runs):
1. **The coach rule:** each trait's blend after decision 0025 against the same blend before it (R1's
   runs), on every row and on teams' first game of a season with a new head coach (the rows it can
   change).
2. **Rung 2 against the blend** (both after the rule): all rows, a team's first 4 games of a season,
   and the rest.
3. **Where the final models miss:** average miss (actual less predicted) by lens: a team's first 4
   games, first games with a new head coach, playoffs, and the rest; with a 90% interval by week.
Scores are the harness's range score (pinball) and typical miss; intervals resample whole weeks.
The vault (2025) isn't read.

Run from pcf/: .venv/Scripts/python.exe projects/schemes-v2/explore/rung2_check.py
"""

# ruff: noqa: E501
from __future__ import annotations

import glob
import os

import polars as pl

from pcf.config import get_config
from pcf.data.tables import load
from pcf.validation.compare import compare
from pcf.validation.scores import row_losses

c = pl.col
OUT = get_config().zone("outputs") / "schemes-v2"
BEFORE = {
    "pass_oe": "ce050b08",
    "shotgun": "d200bcfa",
    "tempo": "44a58bad",
    "depth": "51396e30",
    "pass_gain": "9633e3c8",
}
KEYS = ["game_id", "team"]


def history(variant: str, prefix: str | None = None, vault: bool = False) -> pl.DataFrame:
    """A saved run's history: the one whose id starts with `prefix`, else the latest development
    run (2016-2024), or with `vault` the latest vault run (2025 only)."""
    runs = glob.glob(str(OUT / variant / "*" / "history.parquet"))
    if prefix:
        return pl.read_parquet(
            next(r for r in runs if os.path.basename(os.path.dirname(r)).startswith(prefix))
        )
    for f in sorted(runs, key=os.path.getmtime, reverse=True):
        h = pl.read_parquet(f)
        if h["game_id"].str.starts_with("2025").all() == vault:
            return h
    raise FileNotFoundError(f"no {'vault' if vault else 'development'} run for {variant}")


def scored(h: pl.DataFrame, tg: pl.DataFrame) -> pl.DataFrame:
    q = h["quantity"][0]
    t = tg.select(*KEYS, y=c(q).cast(pl.Float64))
    return row_losses(h.join(t, on=KEYS).drop_nulls("y"), "amount").with_columns(step=c("as_of"))


def line(lab: str, a: pl.DataFrame, b: pl.DataFrame) -> str:
    comp = compare(a, b, KEYS, "step")
    j = a.select(*KEYS, "readable").join(b.select(*KEYS, rb="readable"), on=KEYS)
    return (
        f"   {lab}: {comp.n if hasattr(comp, 'n') else j.height:,} rows; range score change {comp.diff:+.5f} ({comp.lo:+.5f} to {comp.hi:+.5f}) -> {comp.verdict}; "
        f"typical miss {j['rb'].mean():.4f} to {j['readable'].mean():.4f}"
    )


def main() -> None:
    tg = load("team_game", parts=["pregame", "tendencies"])
    # a team's game number in its season, and whether its first game had a new head coach
    order = tg.filter(c("game_id").str.slice(5, 2).cast(pl.Int32) <= 18).sort(
        "team", "kickoff" if "kickoff" in tg.columns else "game_id"
    )
    order = order.with_columns(n=pl.int_range(1, pl.len() + 1).over("team", "season"))
    last = (
        order.group_by("team", "season")
        .agg(c("coach").drop_nulls().last().alias("last_coach"))
        .with_columns(season=c("season") + 1)
    )
    first = (
        order.filter(c("n") == 1)
        .join(last, on=["team", "season"], how="left")
        .filter(c("coach") != c("last_coach"))
        .select(KEYS)
    )
    order = order.select(*KEYS, "n")
    print(
        f"teams' first games with a new head coach, 2016-2024: {first.filter(c('game_id').str.slice(0, 4).cast(pl.Int32) >= 2016).height}"
    )

    print("\n== 1. The opening-coach rule: the blend after it against before (lower is better)")
    for t, prefix in BEFORE.items():
        v = "pass_gain_blend" if t == "pass_gain" else f"{t}_shrunk"
        new, old = scored(history(v), tg), scored(history(v, prefix), tg)
        print(f"  {v}")
        print(line("all rows", new, old))
        print(
            line(
                "first games with a new coach",
                new.join(first, on=KEYS, how="semi"),
                old.join(first, on=KEYS, how="semi"),
            )
        )

    print("\n== 2. Rung 2 against the blend (both after the rule)")
    for t in ("pass_oe", "shotgun", "tempo", "depth"):
        r2, bl = (
            scored(history(f"{t}_rung2"), tg).join(order, on=KEYS),
            scored(history(f"{t}_shrunk"), tg).join(order, on=KEYS),
        )
        print(f"  {t}")
        print(line("all rows", r2, bl))
        print(line("games 1-4", r2.filter(c("n") <= 4), bl.filter(c("n") <= 4)))
        print(line("games 5+", r2.filter(c("n") > 4), bl.filter(c("n") > 4)))

    print("\n== 3. Where the final models miss (actual less predicted, 2016-2024)")
    full = (
        tg.select(*KEYS)
        .with_columns(wk=c("game_id").str.slice(5, 2).cast(pl.Int32))
        .join(order, on=KEYS, how="left")
    )
    full = full.join(first.with_columns(newc=pl.lit(True)), on=KEYS, how="left")
    lenses = {"games 1-4": (c("n") <= 4), "first game, new coach": c("newc").fill_null(False),
              "playoffs": c("wk") > 18, "everything else": (c("n") > 4) & (c("wk") <= 18)}  # fmt: skip
    for v in ("pass_oe_rung2", "shotgun_rung2", "depth_rung2", "tempo_shrunk"):
        s = (
            scored(history(v), tg)
            .join(full, on=KEYS, how="left")
            .with_columns(miss=c("y") - c("mean"))
        )
        parts = []
        for lab, f in lenses.items():
            x = s.filter(f)
            wk = x.group_by("step").agg(m=c("miss").mean(), n=pl.len())
            boots = [
                wk.sample(fraction=1.0, with_replacement=True, seed=i)
                .select((c("m") * c("n")).sum() / c("n").sum())
                .item()
                for i in range(500)
            ]
            lo, hi = sorted(boots)[25], sorted(boots)[475]
            parts.append(f"{lab} {x.height}: {x['miss'].mean():+.4f} ({lo:+.4f} to {hi:+.4f})")
        print(f"  {v}: " + "; ".join(parts))


if __name__ == "__main__":
    main()
