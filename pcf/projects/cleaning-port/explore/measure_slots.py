"""Measure the improved slot labels on every season, against the old functions where they run.

For each season 2016-2025: where each label came from (week, earlier week, roster, none), how
often `special` is used, how often one play-side has two players with the same label, the share
of offense plays with exactly one QB1, and (2016-2024) how often the improved label equals the
old one. Also checks 2026 depth labels build from the daily snapshots.

Run from pcf/:  uv run python projects/cleaning-port/explore/measure_slots.py
"""

import sys
import time

import polars as pl

from pcf.data.clean import legacy
from pcf.data.clean.depth_charts import (
    daily_depth_rows,
    depth_labels,
    game_day_cutoffs,
    weekly_depth_rows,
)
from pcf.data.clean.players import plays_with_players, players_on_play
from pcf.data.clean import standard
from pcf.data.clean.slots import slot_labels
from pcf.data.sources.nflverse import scan

PBP = ["game_id", "play_id", "play_type", "season", "week", "season_type", "posteam", "defteam"]
OLD_PLAYS = ["offense_players", "defense_players", "game_id", "play_id", "play_type", "season", "week"]
ROSTER = ["season", "week", "team", "gsis_id", "position", "depth_chart_position"]


def all_depth_rows() -> pl.DataFrame:
    weekly = weekly_depth_rows(scan("depth_charts", range(2001, 2025)).collect())
    cutoffs = game_day_cutoffs(
        scan("schedules").filter(pl.col("season") >= 2025).collect()
    )
    daily = daily_depth_rows(scan("depth_charts", [2025, 2026]).collect(), cutoffs)
    return pl.concat([weekly, daily])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # polars tables don't fit cp1252
    t = time.time()
    labels = depth_labels(all_depth_rows())
    print(f"depth labels 2001-2026: {labels.height:,} rows in {time.time() - t:.0f}s")
    l26 = labels.filter(pl.col("season") == 2026)
    print(f"2026: {l26.select('week', 'team').n_unique()} team-weeks, weeks {sorted(l26['week'].unique())}")

    rows = []
    for season in range(2016, 2026):
        t = time.time()
        plays = plays_with_players(
            scan("pbp", [season]).select(PBP).collect(),
            scan("participation", [season])
            .select("nflverse_game_id", "play_id", "offense_players", "defense_players")
            .collect(),
        )
        players = players_on_play(plays)
        rosters = standard.weekly_rosters(
            scan("weekly_rosters", [season]).select(*ROSTER, "status").collect()
        )
        out = slot_labels(players, labels, rosters)
        took = time.time() - t
        src = out["label_source"].value_counts()
        share = {s: c / out.height for s, c in src.iter_rows()}
        offense = out.filter(pl.col("side") == "offense")
        qb1 = offense.group_by("game_id", "play_id").agg(
            n=(pl.col("position_label") == "QB1").sum()
        )
        clash = out.group_by("game_id", "play_id", "side", "position_label").len()
        row = {
            "season": season,
            "player_plays": out.height,
            "week": share.get("week", 0),
            "earlier": share.get("earlier_week", 0),
            "roster": share.get("roster", 0),
            "none": share.get("none", 0),
            "special": (out["position"] == "special").mean(),
            "one_qb1": (qb1["n"] == 1).mean(),
            "label_clash_plays": clash.filter(pl.col("len") > 1)
            .select("game_id", "play_id")
            .n_unique()
            / out.select("game_id", "play_id").n_unique(),
            "seconds": round(took, 1),
        }
        if season <= 2024:
            old = legacy.pivot_long_both_sides(
                legacy.pivot_wide_both_sides(plays.select(OLD_PLAYS).to_pandas()),
                scan("depth_charts", [season]).collect().to_pandas(),
            )
            old = pl.from_pandas(old[["game_id", "play_id", "player_id", "position_label"]])
            both = out.join(
                old.rename({"player_id": "gsis_id", "position_label": "old_label"}),
                on=["game_id", "play_id", "gsis_id"],
                how="left",
            )
            week = both.filter(pl.col("label_source") == "week")
            row["old_special"] = (old["position_label"] == "special").mean()
            row["same_label"] = (both["position_label"] == both["old_label"]).mean()
            row["same_label_week"] = (week["position_label"] == week["old_label"]).mean()
            row["same_position_week"] = (
                week["position"] == week["old_label"].str.replace(r"\d+$", "")
            ).mean()
            row["old_rows"] = old.height
        rows.append(row)
        print(row, flush=True)
    pl.Config.set_tbl_cols(20)
    pl.Config.set_tbl_width_chars(250)
    print(pl.DataFrame(rows).with_columns(pl.selectors.float().round(4)))


if __name__ == "__main__":
    main()
