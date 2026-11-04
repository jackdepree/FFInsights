"""The ladder, from the saved walk-forward histories: every variant on the rows they share, overall,
for players who played recently (D7), per position, and for players back from an absence (F9).
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/compare_rungs.py
"""

import polars as pl
from pcf.config import get_config
from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.experts.participation.common import SHARE
from pcf.validation.backtest import targets
from pcf.validation.compare import compare
from pcf.validation.scores import row_losses

c = pl.col
KEYS = ["gsis_id", "game_id"]
NEXT = ["last_game", "last3", "lasso", "trees", "trees_career"]
H3 = ["season_h3", "lasso_h3", "trees_h3"]
REST = ["season_rest", "lasso_rest", "trees_rest"]
SEASONS = list(range(2013, 2025))


def history(variant: str, gw: Gateway) -> pl.DataFrame:
    folder = get_config().zone("outputs") / "participation" / variant
    run = max(folder.iterdir(), key=lambda p: (p / "history.parquet").stat().st_mtime
              if (p / "history.parquet").exists() else 0)  # fmt: skip
    e = find("participation", variant)()
    h = pl.read_parquet(run / "history.parquet")
    y = targets(e, gw).select(*KEYS, "y")
    # Saved histories have no step: the week, from the game id, is the block
    return row_losses(h.join(y, on=KEYS), e.kind).with_columns(step=c("game_id").str.slice(0, 7))


def context() -> pl.DataFrame:
    """Position, and the player's recent games, for grouping only: never a model input."""
    pg = load("player_game", parts=["snaps", "game_status"], seasons=SEASONS)
    sched = load("game", parts=["schedule"], seasons=SEASONS).select("game_id", "kickoff")
    d = pg.join(sched, on="game_id").sort("gsis_id", "kickoff").with_columns(
        share=SHARE, off=(c("status") == "INA").fill_null(False)
        | (c("status").is_null() & c("offense_snaps").is_null()),
    )  # fmt: skip
    g = ["gsis_id"]
    d = d.with_columns(run=(~c("off")).cum_sum().over(g)).with_columns(
        streak=c("off").cast(pl.Int32).cum_sum().over([*g, "run"])
    )
    return d.with_columns(
        recent=c("share").shift(1).rolling_sum(8, min_samples=1).over(g).fill_null(0) > 0,
        missed=c("streak").shift(1).over(g).fill_null(0),
        was_on=~c("off"),
    ).select(*KEYS, "position", "season", "recent", "missed", "was_on")


def line(d: pl.DataFrame, name: str, group: str) -> dict:
    return {
        "group": group, "variant": name, "rows": d.height,
        "pinball": d["loss"].mean() * 100,
        "MAE": (d["y"] - d["mean"]).abs().mean() * 100,
        "R2": 1 - ((d["y"] - d["mean"]) ** 2).mean() / d["y"].var(),
        "bias": (d["mean"] - d["y"]).mean() * 100,
        "cover": d.select(((c("y") >= c("q10")) & (c("y") <= c("q90"))).mean()).item(),
        "width": (d["q90"] - d["q10"]).mean() * 100,
    }  # fmt: skip


def ladder(variants: list[str], gw: Gateway, ctx: pl.DataFrame, title: str) -> None:
    hist = {v: history(v, gw).join(ctx, on=KEYS) for v in variants}
    shared = None
    for h in hist.values():
        k = h.select(KEYS)
        shared = k if shared is None else shared.join(k, on=KEYS)
    hist = {v: h.join(shared, on=KEYS) for v, h in hist.items()}
    groups = {
        "all": lambda d: d,
        "played in last 8": lambda d: d.filter(c("recent")),
        **{p: lambda d, p=p: d.filter((c("position") == p) & c("recent"))
           for p in ("QB", "RB", "WR", "TE")},
        "2021-2024": lambda d: d.filter(c("season") >= 2021),
        "back, missed 1-3": lambda d: d.filter(c("was_on") & c("missed").is_between(1, 3)),
        "back, missed 4+": lambda d: d.filter(c("was_on") & (c("missed") >= 4)),
    }  # fmt: skip
    print(f"\n== {title} ({shared.height:,} shared rows; scores in points of share)")
    rows = [line(f(h), v, g) for g, f in groups.items() for v, h in hist.items()]
    with pl.Config(float_precision=3, tbl_width_chars=200, tbl_rows=80, fmt_str_lengths=30):
        print(pl.DataFrame(rows))
    print("\n   Paired, by week (a - b, pinball x100; 90% interval)")
    for a, b in zip(variants[1:], variants, strict=False):
        cmp = compare(hist[a], hist[b], KEYS, "step", (a, b))
        print(f"   {a:<14} vs {b:<12} {cmp.diff * 100:+.3f} ({cmp.lo * 100:+.3f} to "
              f"{cmp.hi * 100:+.3f}): {cmp.verdict}")  # fmt: skip


def active(gw: Gateway, ctx: pl.DataFrame) -> None:
    h = history("active", gw).join(ctx, on=KEYS)
    print("\n== The chance of being active, 2016-2024")
    bins = h.with_columns(b=(c("mean") * 10).floor().clip(0, 9)).group_by("b").agg(
        n=pl.len(), said=c("mean").mean(), was=c("y").mean()
    ).sort("b")  # fmt: skip
    with pl.Config(float_precision=3, tbl_rows=12):
        print(bins)
    print("   error (rows-weighted):", round(((bins["said"] - bins["was"]).abs() * bins["n"]).sum() / bins["n"].sum(), 4))
    from sklearn.metrics import roc_auc_score

    print("   AUC", round(roc_auc_score(h["y"], h["mean"]), 3), "Brier", round(h["readable"].mean(), 4))
    r = h.filter(c("recent"))
    print("   played in last 8: AUC", round(roc_auc_score(r["y"], r["mean"]), 3), "rows", r.height)


if __name__ == "__main__":
    gw = Gateway()
    ctx = context()
    ladder(NEXT, gw, ctx, "Next game")
    active(gw, ctx)
    ladder(H3, gw, ctx, "Next 3 games")
    ladder(REST, gw, ctx, "Rest of the season")
