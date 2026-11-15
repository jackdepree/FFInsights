"""snap-leverage build (2026-11-14): the ladder, exactly. The scorecards round to 3 decimals; this
compares each rung's saved walk-forward history with the rung below on the same rows.

For each target (snap share next 3 games, the no-noise target; leverage share next 3 games and
rest of season): `lev` against `plain`, `full` against `plain`, `full` against `lev`. Range score
(mean pinball over q10, q50, q90) and squared error of the mean, as % of the lower rung's
(+ = worse), with a 90% interval resampled by week (the harness's way). Then the no-noise target
by season, position group, first-year players and weeks 1-4 (where the exploration's gain was).
Reads each variant's latest run under outputs/snap-leverage/. Writes ladder.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/ladder.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import END_OF_TIME, for_expert
from pcf.data.tables.store import read_part
from pcf.experts.snap_leverage import features as F
from pcf.experts.snap_leverage.model import TARGETS, VARIANTS
from pcf.validation.scores import mean_pinball

c = pl.col
HERE = Path(__file__).parent
K = ["gsis_id", "game_id"]
PAIRS = [("lev", "plain"), ("full", "plain"), ("full", "lev")]


def latest(variant: str) -> Path:
    folder = get_config().zone("outputs") / "snap-leverage" / variant
    runs = [p for p in folder.iterdir() if (p / "history.parquet").exists()]
    return max(runs, key=lambda p: p.stat().st_mtime) / "history.parquet"


def scored(variant: str, y: pl.DataFrame) -> pl.DataFrame:
    h = pl.read_parquet(latest(variant)).join(y.select(*K, "y"), on=K)
    return h.with_columns(loss=mean_pinball(), se=(c("y") - c("mean")) ** 2).select(
        *K, "as_of", "loss", "se"
    )


def gain(d: pl.DataFrame, n: int = 2000) -> tuple[str, str]:
    """(range score, squared error): B against A as % of A, with the 90% interval by week."""
    g = d.group_by("wk").agg(c("loss_a", "loss_b", "se_a", "se_b").sum())
    rng = np.random.default_rng(0)
    i = rng.integers(0, g.height, (n, g.height))
    out = []
    for m in ("loss", "se"):
        a, b = g[f"{m}_a"].to_numpy(), g[f"{m}_b"].to_numpy()
        boot = 100 * (b[i].sum(1) / a[i].sum(1) - 1)
        lo, hi = np.percentile(boot, [5, 95])
        out.append(f"{100 * (b.sum() / a.sum() - 1):+.3f}% ({lo:+.3f} to {hi:+.3f})")
    return out[0], out[1]


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    e = VARIANTS["snap_next3_plain"]()
    view = for_expert(e).view(END_OF_TIME, e.cadence, e.inputs)
    roster = (
        read_part("player_game", "roster", seasons=range(2020, 2025))
        .select(*K, "position", first_year=c("season") == c("rookie_year"))
        .collect()
        .unique(K)
    )
    say("Each rung against the one below, same rows, 2020-2024 (+ = worse; 90% interval by week)")
    say("target      | rung vs below | rows    | range score           | squared error")
    keep = {}
    for target, (measure, horizon) in TARGETS.items():
        y = F.targets(view, measure, horizon)
        runs = {r: scored(f"{target}_{r}", y) for r in ("plain", "lev", "full")}
        for b, a in PAIRS:
            d = (
                runs[a]
                .rename({"loss": "loss_a", "se": "se_a"})
                .join(runs[b].select(*K, loss_b="loss", se_b="se"), on=K)
                .with_columns(wk=c("as_of").dt.strftime("%Y-%m-%d"))
            )
            r, s = gain(d)
            say(f"{target:11s} | {b:4s} vs {a:5s} | {d.height:7,} | {r:21s} | {s}")
            if target == "snap_next3":
                keep[(b, a)] = d
    say("")
    say("The no-noise target (snap share, next 3 games), by group: range score | squared error")
    for (b, a), d in keep.items():
        if a != "plain":
            continue
        say(f"  {b} vs plain:")
        d = d.join(roster, on=K, how="left").with_columns(
            season=c("game_id").str.slice(0, 4), week=c("game_id").str.slice(5, 2).cast(pl.Int32)
        )
        groups = [(f"season {s}", c("season") == s) for s in ("2020", "2021", "2022", "2023", "2024")]
        groups += [(f"{p}", c("position") == p) for p in ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB")]
        groups += [("first-year players", c("first_year").fill_null(False)), ("weeks 1-4", c("week") <= 4)]
        for name, cond in groups:
            sub = d.filter(cond)
            r, s = gain(sub)
            say(f"    {name:20s} {sub.height:7,}  {r:22s} | {s}")
    (HERE / "ladder.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
