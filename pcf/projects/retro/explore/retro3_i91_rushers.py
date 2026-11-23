# ruff: noqa: E501
"""IDEAS I91 (retro 3's quick group, 2026-11-23): how much of skill-over-expected's +15.1% (an outside
linebacker's pressure rate added to his sack rate, forecasting next season's sacks per dropback) is
only knowing who rushes?

Claude's odds, written 2026-11-20 before this run: 65% that within rushers the gain is under half of
+15.1%; 75% that it stays above zero.

The second look's frame and scoring (weighted least squares, one target season left out at a time,
90% from resampling players), with the third look's role: rush share = pressures / (pressures +
coverage targets) in the first season. Arms: all outside linebackers (the +15.1%); rushers only
(rush share over 2/3); all, with rush share added to the base. Defensive linemen beside it.

Run from pcf/:  python projects/retro/explore/retro3_i91_rushers.py > projects/retro/explore/retro3_i91_rushers.txt
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import polars as pl

from pcf.data.gateway import Gateway

c = pl.col
SOE = Path(__file__).parents[2] / "skill-over-expected" / "explore"
spec = importlib.util.spec_from_file_location("sl", SOE / "second_look.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)
fl = sl.fl


def main() -> None:
    src = Gateway().source
    teams = fl.main_team(src)
    wk = src.part("game", "schedule").select("game_id", "week", "season", "game_type")
    reg = wk.filter((c("game_type") == "REG") & c("season").is_between(sl.FIRST, sl.LAST)).select("game_id", "week", "season")
    pb = fl.plays(src)
    of = src.part("player_play", "on_field").filter((c("side") == "defense") & c("season").is_between(2018, sl.LAST))
    drop = pb.filter(c("qb_dropback") == 1).select("game_id", "play_id")
    on = of.join(drop, on=["game_id", "play_id"]).group_by(pid="gsis_id", game_id="game_id").agg(nd=pl.len())
    pr = src.part("player_game", "pfr").select(
        pid="gsis_id", game_id="game_id", press=c("pfr_def_def_pressures"), sacks=c("pfr_def_def_sacks"), tgt=c("pfr_def_def_targets"),
    )
    dr = on.join(reg, on="game_id").join(pr, on=["pid", "game_id"], how="left").with_columns(c("press", "sacks", "tgt").fill_null(0))
    rows = []
    for label, pos in (("OLB", ["OLB"]), ("DE, DT, NT", ["DE", "DT", "NT"])):
        d = dr.join(teams.filter(c("position").is_in(pos)).select("pid", "season"), on=["pid", "season"])
        s = (
            sl.seasons_frame(d, ["sacks", "press", "nd", "tgt"], "nd", 150)
            .with_columns(
                srate=c("sacks") / c("nd"), prate=c("press") / c("nd"),
                rush=c("press") / (c("press") + c("tgt")),
                y=c("sacks_next") / c("nd_next"), w=c("nd_next"),
            )
            .filter(c("nd_next") >= 150)
        )  # fmt: skip
        arms = [("all (the second look)", s, ["srate"])]
        if label == "OLB":
            arms += [
                ("rushers only (rush share over 2/3)", s.filter(c("rush") > 2 / 3), ["srate"]),
                ("droppers only (rush share under 1/3)", s.filter(c("rush") < 1 / 3), ["srate"]),
                ("all, rush share added to the base", s, ["srate", "rush"]),
            ]
        for name, f, base in arms:
            rows.append({"group": label, "arm": name, **sl.score(f, base, ["prate"], "y", "w")})
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(240)
    pl.Config.set_fmt_str_lengths(60)
    pl.Config.set_float_precision(4)
    print("== next season's sacks per dropback: the gain from adding the pressure rate (share of the base's weighted squared error removed)")
    print(pl.DataFrame(rows))


if __name__ == "__main__":
    main()
