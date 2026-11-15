"""snap-leverage build check (2026-11-14): how much the morning-after map costs (the brief: "True
participation (2016-2024) is kept only as a check of how much the map costs").

For each regular-season player-game 2019-2024, the usage measures from participation-live's map
(each snap by its on-field chance) against the same measures from nflverse's true participation:
correlation, mean absolute gap, and for the role gap and trust over expected also how well each
repeats week to week (odd against even weeks, player-seasons with 8+ games at 10-90% snap share).
Writes map_cost.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/map_cost.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import polars as pl

from pcf.config import get_config
from pcf.data.gateway import history_run
from pcf.data.tables.store import read_part
from pcf.experts.snap_leverage import usage as U

c = pl.col
HERE = Path(__file__).parent
SEASONS = range(2019, 2025)


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    run = history_run("participation-live", 1)
    hist = get_config().zone("outputs") / "participation-live" / run / "history.parquet"
    both = []
    for s in SEASONS:
        reg = read_part("game", "schedule", [s]).filter(c("game_type") == "REG").select("game_id")
        plays = U.plays(
            read_part("play", "leverage", [s]).join(
                read_part("play", "pace", [s]).select("game_id", "play_id", "pcf_xpass"),
                on=["game_id", "play_id"], how="left",
            ).join(reg, on="game_id").collect()
        )  # fmt: skip
        mp = (
            pl.scan_parquet(hist)
            .filter(c("season") == s)
            .select("game_id", "play_id", "gsis_id", "side", "team", p="mean")
            .collect()
        )
        tr = (
            read_part("player_play", "on_field", [s])
            .select("game_id", "play_id", "gsis_id", "side", "team", p=pl.lit(1.0))
            .collect()
            .unique(["game_id", "play_id", "gsis_id"])
        )
        a, b = U.usage(mp, plays), U.usage(tr, plays)
        j = b.join(a, on=["game_id", "gsis_id", "side"], how="left", suffix="_map").with_columns(
            season=pl.lit(s), week=c("game_id").str.slice(5, 2).cast(pl.Int32)
        )
        # a true player-game the map missed: shares 0, role and trust empty
        j = j.with_columns(c(f"{m}_map").fill_null(0.0) for m in ("snap_share", "lev_share"))
        both.append(j)
        say(f"{s}: {b.height:,} true player-games; the map has {a.height:,}")
    d = pl.concat(both)
    say("")
    say("Map against truth, player-games he was truly on the field for (n, correlation, mean |gap|):")
    for m in U.MEASURES:
        x = d.filter(c(m).is_not_null() & c(f"{m}_map").is_not_null())
        r = x.select(pl.corr(m, f"{m}_map")).item()
        gap = x.select((c(m) - c(f"{m}_map")).abs().mean()).item()
        say(f"  {m:10s} {x.height:9,}  r {r:.3f}  |gap| {gap:.4f}")
    say("")
    say("Week-to-week repeat (odd vs even weeks), player-seasons with 8+ games at 10-90% snap share:")
    part = d.filter(c("snap_share").is_between(0.1, 0.9))
    for m in ("role_gap", "trust_oe"):
        for src in (m, f"{m}_map"):
            g = (
                part.filter(c(src).is_not_null())
                .with_columns(half=c("week") % 2)
                .group_by("gsis_id", "season", "half")
                .agg(v=c(src).mean(), n=pl.len())
                .filter(c("n") >= 4)
                .pivot(on="half", index=["gsis_id", "season"], values="v")
                .drop_nulls()
            )
            r = g.select(pl.corr("0", "1")).item()
            say(f"  {src:14s} {g.height:6,} player-seasons  odd-even r {r:.2f}")
    (HERE / "map_cost.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
