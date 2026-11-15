"""snap-leverage: a football sanity look at what ships (rule h), 2024 (not the vault).
A. `play.leverage`: is it high where football says the stakes are (late and close), low in blowouts?
B. `player_game.leverage_usage`: over the season, who has the largest and smallest passing-down role
   gap and trust over expected, and how each position averages. Players with 300+ snaps on their
   main side; season values are snap-weighted means of the per-game ones.
Writes sanity_part.txt. Run from pcf/:
PYTHONUTF8=1 .venv/Scripts/python.exe projects/snap-leverage/explore/sanity_part.py
"""

# ruff: noqa: E501
from __future__ import annotations

from pathlib import Path

import polars as pl

from pcf.data.tables.store import read_part

c = pl.col
HERE = Path(__file__).parent
SEASON = 2024
MIN_SNAPS = 300


def main() -> None:
    lines: list[str] = []

    def say(t: str = "") -> None:
        print(t, flush=True)
        lines.append(t)

    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_width_chars(140)
    pl.Config.set_fmt_str_lengths(60)
    pl.Config.set_tbl_hide_dataframe_shape(True)

    # A. the leverage of a play
    lev = read_part("play", "leverage", [SEASON]).select("game_id", "play_id", "leverage", "high_stakes")
    pbp = read_part("play", "pbp", [SEASON]).select(
        "game_id", "play_id", "season_type", "qtr", "down", "game_seconds_remaining", "score_differential", "desc"
    )
    p = lev.join(pbp, on=["game_id", "play_id"]).filter(c("season_type") == "REG", c("down").is_not_null()).collect()
    diff = c("score_differential").abs()
    late = (c("game_seconds_remaining") <= 300) & (c("qtr") >= 4)
    situ = (
        pl.when(late & (diff <= 8)).then(pl.lit("4th qtr, last 5 min, within 8"))
        .when(diff >= 21).then(pl.lit("blowout, 21+ points"))
        .when(c("qtr") == 1).then(pl.lit("1st quarter"))
        .otherwise(pl.lit("everything else"))
    )  # fmt: skip
    say(f"A. play.leverage, {SEASON} regular season ({p.height:,} plays with a down). Leverage is the spread")
    say("   of the play's win-chance swing, over the training mean (1 = an average play)")
    say(str(p.group_by(situ.alias("situation")).agg(plays=pl.len(), leverage=c("leverage").mean().round(2),
                                                     high_stakes=c("high_stakes").mean().round(3)).sort("leverage")))  # fmt: skip
    say("")
    say("   By down (high-stakes share):")
    say(str(p.group_by("down").agg(leverage=c("leverage").mean().round(2), high_stakes=c("high_stakes").mean().round(3)).sort("down")))
    say("")
    say("   The five highest-leverage plays:")
    top = p.sort("leverage", descending=True).head(5).select(
        "game_id", "qtr", "down", "score_differential", c("leverage").round(2), c("desc").str.slice(0, 60)
    )
    say(str(top))

    # B. the usage part
    u = read_part("player_game", "leverage_usage", [SEASON]).collect()
    ros = read_part("player_game", "roster", [SEASON]).select("gsis_id", "game_id", "full_name", "position", "team").collect()
    g = u.join(ros, on=["gsis_id", "game_id"], how="left")
    w = c("lev_snaps")
    season = (
        g.group_by("gsis_id")
        .agg(
            c("full_name").drop_nulls().first(), c("position").drop_nulls().mode().first(),
            c("team").drop_nulls().mode().first(), c("lev_side").mode().first(),
            snaps=w.sum(), snap_share=(c("lev_snap_share") * w).sum() / w.sum(),
            role_gap=(c("lev_role_gap") * w).sum() / w.sum(), trust_oe=(c("lev_trust_oe") * w).sum() / w.sum(),
        )
        .filter(c("snaps") >= MIN_SNAPS)
        .with_columns(c("snap_share", "role_gap", "trust_oe").round(3))
    )  # fmt: skip
    cols = ["full_name", "position", "team", "snaps", "snap_share", "role_gap", "trust_oe"]
    say("")
    say(f"B. player_game.leverage_usage, {SEASON}, {season.height:,} players with {MIN_SNAPS}+ snaps on their main side")
    say("   role_gap: high-stakes share minus snap share (+ = on the field more when it matters)")
    say("   trust_oe: role gap beyond what the kind of situation predicts (pass-likely snaps)")
    say("")
    say("   By position (players' mean):")
    say(str(season.group_by("position").agg(players=pl.len(), role_gap=c("role_gap").mean().round(3),
                                             trust_oe=c("trust_oe").mean().round(3)).filter(c("players") >= 10).sort("role_gap")))  # fmt: skip
    for col in ("role_gap", "trust_oe"):
        for side in ("offense", "defense"):
            s = season.filter(c("lev_side") == side)
            say("")
            say(f"   {side}, largest {col}:")
            say(str(s.sort(col, descending=True).head(8).select(cols)))
            say(f"   {side}, smallest {col}:")
            say(str(s.sort(col).head(8).select(cols)))
    (HERE / "sanity_part.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
