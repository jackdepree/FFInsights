"""snap-leverage build (2026-11-14): why the build's leverage rung lost (+0.23%) where the
exploration's won (+0.14%). The map, or the setup?

The exploration's own test (playing_time.py: rows after each game, plain snap share from true
participation, the next 3 games' snap share, trees), with leverage share three ways:
- from true participation (the exploration's), trained from 2016 as it was;
- from true participation, trained from 2019 only (the build's training window);
- from the morning-after map (the build's source), trained from 2019.
Scored 2021-2024 (every version has at least 2 training seasons). Gain = share of the plain
model's squared error removed (+ = better), 90% interval by week. Writes map_or_setup.txt.
Run from pcf/: PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/map_or_setup.py
"""

# ruff: noqa: E501
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.gateway import history_run
from pcf.data.tables.store import read_part
from pcf.experts.snap_leverage import usage as U

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import playing_time as PT  # noqa: E402

c = pl.col
SCORED = [2021, 2022, 2023, 2024]


def map_lev() -> pl.DataFrame:
    """The map's leverage share per regular-season player-game, 2019-2024."""
    hist = get_config().zone("outputs") / "participation-live" / history_run("participation-live", 1) / "history.parquet"
    out = []
    for s in range(2019, 2025):
        plays = U.plays(
            read_part("play", "leverage", [s]).join(read_part("play", "pace", [s]).select("game_id", "play_id", "pcf_xpass"), on=["game_id", "play_id"], how="left").collect()
        )
        mp = pl.scan_parquet(hist).filter(c("season") == s).select("game_id", "play_id", "gsis_id", "side", "team", p="mean").collect()
        out.append(U.usage(mp, plays).select("gsis_id", "game_id", "side", lev_map="lev_share"))
    return pl.concat(out)


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    x = PT.rows().join(map_lev(), on=["gsis_id", "game_id", "side"], how="left")
    k = ["gsis_id", "season"]
    x = x.with_columns(c("lev_map").fill_null(0.0)).with_columns(
        lev_map_last=c("lev_map"),
        lev_map_l3=c("lev_map").rolling_mean(3, min_samples=1).over(k),
        lev_map_std=c("lev_map").cum_sum().over(k) / c("lev_map").cum_count().over(k),
    )
    d = x.filter(c("y3").is_not_null())
    sets = {
        "plain": PT.PLAIN,
        "+ true leverage share": PT.PLAIN + ["lev_share_last", "lev_share_l3", "lev_share_std"],
        "+ map leverage share": PT.PLAIN + ["lev_map_last", "lev_map_l3", "lev_map_std"],
    }
    say("Next 3 games' snap share, the exploration's rows and trees, scored 2021-2024 (+ = better than plain)")
    for first, names in ((2016, ["plain", "+ true leverage share"]), (2019, list(sets))):
        preds = {n: [] for n in names}
        parts = []
        for s in SCORED:
            tr, te = d.filter(c("season").is_between(first, s - 1)), d.filter(c("season") == s)
            for n in names:
                preds[n].append(PT.fit_predict(tr, te, sets[n], "y3", "trees"))
            parts.append(te.select("season", "week", "gsis_id", "y3", "first_year"))
        sc = pl.concat(parts).with_columns(**{n: pl.Series(np.concatenate(v)) for n, v in preds.items()}).with_columns(
            blk=pl.concat_str("season", "week", separator="-")
        )
        say(f"  trained from {first} ({sc.height:,} rows):")
        for n in names[1:]:
            say(f"    {n:24s} everyone {PT.gain(sc, 'plain', n, 'y3', 'blk')} | first-year {PT.gain(sc.filter(c('first_year')), 'plain', n, 'y3', 'blk')}")
    (HERE / "map_or_setup.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
