# ruff: noqa: E501
"""The CEO's spot-check (2026-11-19): why participation-late's on-field map can't be a call field.

Three parts, on 2023-2024 scrimmage plays, against the truth (the after-the-season participation data, which lists
every player on the field and can't know how the play ended):

A. Where the map's position counts are off, split by whether a player of that group was named on the play (the
   target or ball carrier, a tackler, the sacker, a pass defender, a QB hitter). If the map's count rises on the
   plays where a group was named, more than the truth does, the map is reading the result.
B. What each kind of personnel adds to the live model, 2024 fit on 2023: the truth's counts (the honest value of
   personnel, if we knew it) against the map's counts. The map's gain beyond the truth's is the leak.
C. The sizes behind A: how often each group is named, and how certain the map is about named and unnamed players.

Run: .venv/Scripts/python.exe projects/context-live/explore/spotcheck_map_leak.py > projects/context-live/explore/spotcheck_map_leak.txt
"""

import polars as pl

from pcf.data.gateway import END_OF_TIME, Gateway, TableSource
from pcf.experts.context_live import context, plays, run

c = pl.col
SEASONS = [2023, 2024]
NAMED = ["receiver_player_id", "rusher_player_id", "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id",
         "solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id", "assist_tackle_2_player_id",
         "tackle_with_assist_1_player_id", "pass_defense_1_player_id", "pass_defense_2_player_id",
         "qb_hit_1_player_id", "qb_hit_2_player_id", "tackle_for_loss_1_player_id", "interception_player_id"]
OUTCOME_NAMES = ["air_yards_exp", "completion_prob", "sack_prob", "pressure_prob", "rush_yards_exp", "run_success_prob", "dropback_success_prob"]


def truth_and_named() -> tuple[pl.DataFrame, pl.DataFrame]:
    gw = Gateway(TableSource(seasons=SEASONS))
    t = gw.view(END_OF_TIME, "retrospective", {"play": ("participation",)}).table("play")
    t = (t.collect() if hasattr(t, "collect") else t).filter(c("season").is_in(SEASONS))
    on = (t.select(*plays.KEYS, ids=pl.concat_str([c("offense_players"), c("defense_players")], separator=";"))
          .filter(c("ids").is_not_null())
          .with_columns(c("ids").str.split(";")).explode("ids").rename({"ids": "gsis_id"})
          .filter(c("gsis_id").str.len_chars() > 0).unique())
    named = (t.select(*plays.KEYS, *NAMED).unpivot(index=plays.KEYS, value_name="gsis_id")
             .drop_nulls("gsis_id").select(*plays.KEYS, "gsis_id").unique())
    return on, named


def main():
    field = context.on_field(SEASONS)  # the map: game_id, play_id, gsis_id, side, chance, position
    pos = field.select("game_id", "gsis_id", "position").unique(["game_id", "gsis_id"])
    on, named = truth_and_named()
    groups = pl.DataFrame({"position": list(context.GROUPS), "group": list(context.GROUPS.values())})
    scored = run.load(SEASONS).filter(c("is_run") | c("is_dropback")).select(*plays.KEYS, "is_dropback", "sack_y", "complete_y")
    charted = on.select(*plays.KEYS).unique().join(scored.select(plays.KEYS), on=plays.KEYS)  # plays with truth
    true_rows = on.join(charted, on=plays.KEYS).join(pos, on=["game_id", "gsis_id"], how="left").with_columns(chance=pl.lit(1.0))
    map_rows = field.join(charted, on=plays.KEYS)

    def counts(rows: pl.DataFrame, label: str) -> pl.DataFrame:
        return (rows.join(groups, on="position").group_by(*plays.KEYS, "group").agg(c("chance").sum().alias(label)))

    named_groups = named.join(charted, on=plays.KEYS).join(pos, on=["game_id", "gsis_id"], how="left").join(groups, on="position").select(*plays.KEYS, "group").unique().with_columns(named=pl.lit(True))
    grid = charted.join(groups.select("group").unique(), how="cross")
    cmp = (grid.join(counts(map_rows, "map"), on=[*plays.KEYS, "group"], how="left")
           .join(counts(true_rows, "truth"), on=[*plays.KEYS, "group"], how="left")
           .join(named_groups, on=[*plays.KEYS, "group"], how="left")
           .with_columns(c("map").fill_null(0.0), c("truth").fill_null(0.0), c("named").fill_null(False)))
    print(f"plays with the truth and the map: {charted.height:,} (2023-2024 runs and dropbacks)\n")
    print("A. The map's count of each group minus the truth's, by whether a player of that group was named on the play")
    a = (cmp.group_by("group", "named").agg(plays=pl.len(), truth=c("truth").mean(), map=c("map").mean(), gap=(c("map") - c("truth")).mean(),
                                             abs_gap=(c("map") - c("truth")).abs().mean()).sort("group", "named"))
    for g, nm, n, tr, mp, gap, ag in a.iter_rows():
        print(f"  {g:9} named={str(nm):5} plays {n:7,}  truth {tr:5.2f}  map {mp:5.2f}  map-truth {gap:+.3f}  typical miss {ag:.3f}")

    print("\n   the same on sacks against other dropbacks (who made the sack is named):")
    s = cmp.join(scored, on=plays.KEYS).filter(c("is_dropback"), c("group").is_in(["n_dl_map", "n_lb_map", "n_db_map"]))
    for row in s.group_by("group", "sack_y").agg(plays=pl.len(), truth=c("truth").mean(), map=c("map").mean(), gap=(c("map") - c("truth")).mean()).sort("group", "sack_y").iter_rows():
        print(f"  {row[0]:9} sack={int(row[1])}  plays {row[2]:6,}  truth {row[3]:5.2f}  map {row[4]:5.2f}  map-truth {row[5]:+.3f}")

    print("\nC. How sure the map is: its average chance for players who really were on the field, named or not")
    tr = on.join(charted, on=plays.KEYS).join(field.select(*plays.KEYS, "gsis_id", "chance"), on=[*plays.KEYS, "gsis_id"], how="left").with_columns(c("chance").fill_null(0.0))
    tr = tr.join(named.with_columns(named=pl.lit(True)), on=[*plays.KEYS, "gsis_id"], how="left").with_columns(c("named").fill_null(False))
    for nm, n, ch, one in tr.group_by("named").agg(n=pl.len(), ch=c("chance").mean(), one=(c("chance") >= 0.999).mean()).sort("named").iter_rows():
        print(f"  named={str(nm):5} player-plays {n:9,}  average chance {ch:.3f}  share at 1.0: {one:.1%}")

    print("\nB. What personnel adds to the live model (2024, fit on 2023): the truth's counts against the map's")
    truth_wide = cmp.pivot(on="group", index=plays.KEYS, values="truth").rename({g: g.replace("_map", "_true") for g in context.PERSONNEL})
    map_wide = cmp.pivot(on="group", index=plays.KEYS, values="map")
    data = run.load(SEASONS).join(map_wide, on=plays.KEYS, how="inner").join(truth_wide, on=plays.KEYS, how="inner")
    true_cols = [g.replace("_map", "_true") for g in context.PERSONNEL]
    plays.FIELD_SETS["map_personnel"] = plays.FIELD_SETS["live"] + context.PERSONNEL
    plays.FIELD_SETS["true_personnel"] = plays.FIELD_SETS["live"] + true_cols
    r_map = run.Rung("6-map-personnel", "map_personnel", "trees")
    r_true = run.Rung("7-true-personnel", "true_personnel", "trees")
    for name in OUTCOME_NAMES:
        o = next(x for x in run.OUTCOMES if x.name == name)
        frame, _ = run.walk(data, o, [2024], [run.BY_RUNG["0-base"], run.BY_RUNG["4-live-trees"], r_map, r_true])
        live = run.share_removed(frame, "4-live-trees")
        print(f"  {o.label:<26} live {live:6.2f}  + true personnel {run.share_removed(frame, r_true.name):6.2f} ({run.loss_gain(frame, r_true.name, '4-live-trees'):+.2f}% of the loss)"
              f"  + map personnel {run.share_removed(frame, r_map.name):6.2f} ({run.loss_gain(frame, r_map.name, '4-live-trees'):+.2f}%)", flush=True)


if __name__ == "__main__":
    main()
