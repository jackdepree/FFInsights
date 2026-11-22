"""context-retro's miss report: each shipped rung's average miss (actual minus expected) by play
lens, with a 90% interval from the week blocks (context-live's lenses, `context_live.report`).

    python -m pcf.experts.context_retro.report --tag backtest      # build/misses_backtest.txt
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import polars as pl

from pcf.experts.context_live.report import play_lenses
from pcf.experts.context_retro import plays
from pcf.experts.context_retro.outcomes import OUTCOMES
from pcf.experts.context_retro.run import cache_dir, report_dir

c = pl.col
LENS_COLUMNS = ["game_id", "play_id", "down", "qtr", "score_differential", "yardline_100",
                "is_screen_pass", "is_play_action", "is_trick_play"]  # fmt: skip


def lens_table(f: pl.DataFrame, mean: str, min_rows: int) -> list[str]:
    """One line per lens: each group's average miss, starred where its 90% interval misses 0."""
    f = f.with_columns(miss=c("y") - c(mean))
    cut = f[mean].quantile(0.9)
    lenses = {**play_lenses(f), "top tenth": (c(mean) >= cut).cast(pl.String),
              "pressure": c("pressure_y").cast(pl.String)}  # fmt: skip
    out = []
    for lens, expr in lenses.items():
        g = (f.with_columns(group=expr).drop_nulls("group")
             .group_by("group", "block").agg(m=c("miss").mean(), n=pl.len())
             .group_by("group").agg(rows=c("n").sum(), miss=(c("m") * c("n")).sum()
                                    / c("n").sum(), sd=c("m").std(), blocks=pl.len())
             .filter(c("rows") >= min_rows).sort("group"))  # fmt: skip
        parts = []
        for grp, rows, miss, sd, blocks in g.iter_rows():
            half = 1.645 * (sd or 0) / max(blocks, 1) ** 0.5
            parts.append(f"{grp} {miss:+.3f}{'*' if abs(miss) > half else ''} ({rows:,})")
        out.append(f"  {lens}: " + "; ".join(parts))
    return out


def misses(tag: str = "backtest", min_rows: int = 300) -> list[str]:
    work = cache_dir() / tag
    res = json.loads((work / "results.json").read_text())
    seasons = None
    out = [f"context-retro {tag}: average miss (actual - expected) by play lens, groups of "
           f"{min_rows}+ plays; * where the 90% interval (by week) misses zero", ""]  # fmt: skip
    for o in OUTCOMES:
        if o.name not in res:
            continue
        f = pl.read_parquet(work / f"{o.name}.parquet")
        if seasons is None:
            seasons = sorted(f["season"].unique().to_list())
            data = plays.load(seasons).select(LENS_COLUMNS)
        f = f.join(data, on=plays.KEYS, how="left")
        for mode in ("e0", "e1"):
            if mode not in res[o.name]:
                continue
            top = res[o.name][mode]["shipped"]
            rows = f.filter(c(f"{top}:mean").is_not_null())
            out.append(f"== {o.name} {mode} ({top})")
            out += lens_table(rows, f"{top}:mean", min_rows)
            out.append("")
    return out


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m pcf.experts.context_retro.report")
    ap.add_argument("--tag", default="backtest")
    a = ap.parse_args(argv)
    report_dir().mkdir(parents=True, exist_ok=True)
    (report_dir() / f"misses_{a.tag}.txt").write_text("\n".join(misses(a.tag)), encoding="utf-8")


if __name__ == "__main__":
    main()
