"""snap-leverage exploration (2026-11-14): football sanity. Who tops trust over expected, and the
raw trust gap, in 2024 (part-timers: 8+ games at 10-90% of his side's snaps).
Writes sanity.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/sanity.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.data.tables.store import read_part

c = pl.col
HERE = Path(__file__).parent


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    pg = pl.read_parquet(get_config().zone("interim") / "snap-leverage" / "player_game.parquet").filter(c("season") == 2024)
    names = read_part("player_game", "roster", seasons=[2024]).select("gsis_id", "full_name").collect().unique("gsis_id")
    ps = (
        pg.filter(c("snap_share").is_between(0.1, 0.9) & (c("t_hi") >= 5) & c("group").is_not_null())
        .group_by("gsis_id", "group").agg(c("team").mode().first(), n=pl.len(), snap=c("snap_share").mean(), hi=c("hi_share").mean(), gap=c("trust_gap").mean(), oe=c("trust_oe").mean())
        .filter(c("n") >= 8).join(names, on="gsis_id", how="left")
    )
    for m, nm in (("oe", "trust over expected"), ("gap", "raw trust gap")):
        say(f"2024, top and bottom 3 by {nm} (snap share, high-stakes share, games):")
        for g in ["RB", "WR", "TE", "DL", "LB", "CB", "S"]:
            a = ps.filter(c("group") == g).sort(m, descending=True)
            top = ", ".join(f"{r['full_name']} {r['team']} {r[m]:+.3f} ({r['snap']:.0%}, {r['hi']:.0%}, {r['n']})" for r in a.head(3).iter_rows(named=True))
            bot = ", ".join(f"{r['full_name']} {r['team']} {r[m]:+.3f} ({r['snap']:.0%}, {r['hi']:.0%})" for r in a.tail(3).iter_rows(named=True))
            say(f"  {g:2s} top: {top}")
            say(f"     bottom: {bot}")
        say("")
    (HERE / "sanity.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
