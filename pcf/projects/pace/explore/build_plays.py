"""pace exploration (2026-11-10), step 1: one compact play table for every hunch test.

Regular-season scrimmage snaps 2006-2024 (never the 2025 vault) from nflverse play-by-play, with:
- the gap: game seconds from the previous snap of the same drive and quarter to this one (the
  pace measure; nflverse has no play clock, its `play_clock` is 0 on every play);
- what happened on the previous snap that stops or slows the clock (Claude's addition to H22);
- in-game injuries from the descriptions ("was injured during the play"), by side;
- teams standardised as PCF's tables do.

Writes `<interim>/pace/plays.parquet` (gitignored). Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/pace/explore/build_plays.py
"""

# ruff: noqa: E501
from __future__ import annotations

import polars as pl

from pcf.config import get_config
from pcf.data.clean import standard

c = pl.col
SEASONS = range(2006, 2025)
COLS = [
    "game_id", "play_id", "season", "week", "season_type", "posteam", "defteam", "home_team",
    "down", "ydstogo", "yardline_100", "qtr", "half_seconds_remaining", "game_seconds_remaining",
    "score_differential", "wp", "vegas_wp", "ep", "epa", "success", "pass", "rush", "xpass",
    "qb_dropback", "qb_scramble", "qb_kneel", "qb_spike", "sack", "no_huddle", "shotgun",
    "incomplete_pass", "out_of_bounds", "penalty", "timeout", "touchdown", "interception",
    "fumble_lost", "play_type", "fixed_drive", "desc",
]  # fmt: skip
INJURED = r"([A-Z]{2,3})-\d+-[^ ]+ was injured during the play"


def season(s: int) -> pl.DataFrame:
    raw = get_config().zone("raw") / "nflverse" / "pbp" / f"season={s}"
    d = pl.read_parquet(next(raw.glob("*.parquet")), columns=COLS).filter(c("season_type") == "REG")
    # Injuries are counted on every play (special teams too), by the side the player was on.
    inj = d.select(
        "game_id", "play_id", "posteam", "defteam",
        team=c("desc").str.extract_all(INJURED),
    ).explode("team").drop_nulls("team").with_columns(team=c("team").str.extract(r"^([A-Z]{2,3})"))
    inj = inj.group_by("game_id", "play_id").agg(
        inj_off=(c("team") == c("posteam")).sum(),
        inj_def=(c("team") == c("defteam")).sum(),
        inj_any=pl.len(),
    )
    d = d.join(inj, on=["game_id", "play_id"], how="left").with_columns(
        c("inj_off", "inj_def", "inj_any").fill_null(0)
    )
    # A timeout row sits between two snaps: carry it onto the next snap.
    d = d.sort("game_id", "play_id").with_columns(
        timeout_before=(c("timeout") == 1).cast(pl.Int8)
    )
    snaps = d.filter(
        c("play_type").is_in(["pass", "run", "no_play", "qb_kneel", "qb_spike"])
        & c("down").is_not_null()
        & c("posteam").is_not_null()
    )
    # Timeouts called since the previous snap
    to = (
        d.with_columns(snap=c("play_id").is_in(snaps["play_id"].implode()).over("game_id"))
        .with_columns(grp=c("snap").cum_sum().over("game_id"))
    )
    to_before = (
        to.group_by("game_id", "grp").agg(t=(c("timeout") == 1).sum())
        .with_columns(grp=c("grp") + 1)
    )
    first = to.filter(c("snap")).select("game_id", "play_id", "grp")
    snaps = snaps.join(first, on=["game_id", "play_id"]).join(to_before, on=["game_id", "grp"], how="left")
    prev = lambda x: c(x).shift(1).over("game_id")  # noqa: E731
    snaps = snaps.sort("game_id", "play_id").with_columns(
        gap=prev("game_seconds_remaining") - c("game_seconds_remaining"),
        same=(prev("fixed_drive") == c("fixed_drive")) & (prev("qtr") == c("qtr")) & (prev("posteam") == c("posteam")),
        prev_incomplete=prev("incomplete_pass").fill_null(0),
        prev_oob=prev("out_of_bounds").fill_null(0),
        prev_penalty=prev("penalty").fill_null(0),
        prev_spike=prev("qb_spike").fill_null(0),
        prev_rush=prev("rush").fill_null(0),
        prev_sack=prev("sack").fill_null(0),
        prev_noplay=(prev("play_type") == "no_play").fill_null(False).cast(pl.Int8),
        timeouts_before=c("t").fill_null(0),
    ).drop("t", "grp", "timeout_before", "desc")
    snaps = standard.standard_teams(snaps, "posteam", "defteam")
    return snaps.with_columns(
        scrimmage=((c("pass") == 1) | (c("rush") == 1)) & (c("qb_kneel") == 0) & (c("qb_spike") == 0),
        gap=pl.when(c("same") & c("gap").is_between(0, 60)).then(c("gap")),
    )


def main() -> None:
    out = get_config().zone("interim") / "pace"
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    for s in SEASONS:
        f = season(s)
        frames.append(f)
        print(s, f.height, "snaps,", f["gap"].is_not_null().sum(), "with a gap,", int(f["inj_any"].sum()), "injuries", flush=True)
    plays = pl.concat(frames, how="diagonal_relaxed")
    plays.write_parquet(out / "plays.parquet")
    print("written", out / "plays.parquet", plays.height, "rows,", plays.estimated_size("mb"), "MB")


if __name__ == "__main__":
    main()
