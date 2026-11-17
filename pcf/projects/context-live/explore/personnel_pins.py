# ruff: noqa: E501
"""Is the map's personnel gain a leak? (discovery, 2026-11-17; decision 0036, RESULTS F-personnel)

participation-late's map pins every player the play-by-play names on a play (passer, rusher, target, tackler,
sacker, pass defender). Those names come from what happened. Here the pins are undone roughly: a chance of
exactly 1 for a player whose median chance in that game is under 0.9 is replaced by his average chance on his
other plays of the game. If the gain shrinks a lot, it came from the names, not the personnel.

Result (personnel_pins.txt): the gain grew instead (sack 1.1% -> 15.3%). The map balances each play to 11, so a
pinned name lowers the other players' chances on that play; undoing the pin breaks the sum and marks the named
plays even more clearly. Either way the saved chances carry who was named on the play, i.e. part of its result.
The map's personnel isn't used as a call field (decision 0036, call 14; idea I63: an edition without the play's
own names).

Run: .venv/Scripts/python.exe projects/context-live/explore/personnel_pins.py > projects/context-live/explore/personnel_pins.txt
"""

import polars as pl

from pcf.experts.context_live import context, plays, run

c = pl.col
NAMES = ["air_yards_exp", "completion_prob", "sack_prob", "pressure_prob", "rush_yards_exp", "run_success_prob", "dropback_success_prob"]


def unpinned(field: pl.DataFrame) -> pl.DataFrame:
    g = field.group_by("game_id", "gsis_id").agg(med=c("chance").median(), other=c("chance").filter(c("chance") < 1).mean())
    f = field.join(g, on=["game_id", "gsis_id"], how="left")
    pinned = (c("chance") == 1) & (c("med") < 0.9)
    print(f"pinned by name (rough): {f.filter(pinned).height:,} of {f.filter(c('chance') == 1).height:,} chances of 1")
    return f.with_columns(chance=pl.when(pinned).then(c("other").fill_null(c("med"))).otherwise(c("chance"))).drop("med", "other")


def main():
    field = context.on_field([2023, 2024])
    for label, fld in [("map as saved", field), ("pins undone", unpinned(field))]:
        crew = context.personnel(fld)
        data = run.load([2023, 2024]).join(crew, on=plays.KEYS, how="left")
        plays.FIELD_SETS["personnel"] = plays.FIELD_SETS["live"] + context.PERSONNEL
        r6 = run.Rung("6-personnel-trees", "personnel", "trees")
        print(f"\n-- {label}: 2024, fit on 2023 --")
        for name in NAMES:
            o = next(x for x in run.OUTCOMES if x.name == name)
            frame, _ = run.walk(data, o, [2024], [run.BY_RUNG["0-base"], run.BY_RUNG["4-live-trees"], r6])
            comp = run.paired(frame, r6.name, "4-live-trees")
            print(f"  {o.label:<26} live {run.share_removed(frame, '4-live-trees'):6.2f}  +personnel {run.share_removed(frame, r6.name):6.2f}  "
                  f"loss {run.loss_gain(frame, r6.name, '4-live-trees'):+.2f}% ({comp.lo:+.5f} to {comp.hi:+.5f})")


if __name__ == "__main__":
    main()
