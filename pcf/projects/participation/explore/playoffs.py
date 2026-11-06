"""Spot-check on F34 (2026-11-05): is the playoff gap football or a data quirk, and could a plain
playoff flag replace the week?
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/playoffs.py

The rows compare each playoff game with the same teams' late regular-season games, so better teams
and their rosters are on both sides. The flags are refit on the same rows as `trees_week`.
"""

import polars as pl

from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.experts.participation.features import FEATURES
from pcf.experts.participation.twopart import TreesWeek
from pcf.validation import backtest, scores
from pcf.validation.backtest import targets
from pcf.validation.compare import compare

c = pl.col
KEYS = ["gsis_id", "game_id"]
SEASONS = list(range(2016, 2025))
TOP_RUN = "0c2a1ac624954337bf11257efc0a7001"
WEEK_RUN = "5a1155eaf7a94883a265e6d62b407e00"
OPTIONS = {
    "trees_week": ["week_no", "final_week", "final_wins"],
    "playoff flag": ["playoff"],
    "playoff flag + last week": ["playoff", "final_week", "final_wins"],
    "last week only": ["final_week", "final_wins"],
}


def saved(variant: str, run: str, y: pl.DataFrame) -> pl.DataFrame:
    h = pl.read_parquet(f"data/outputs/participation/{variant}/{run}/history.parquet")
    return scores.row_losses(h.join(y, on=KEYS), "amount").filter(c("y").is_not_null())


def rates(frame: pl.DataFrame) -> dict:
    """What happened to a group of rows, in points of share."""
    played = c("y") > 0
    return dict(
        rows=pl.len(),
        per_team_game=pl.len() / c("game_team").n_unique(),
        was=c("y").mean() * 100,
        no_snap=(~played).mean() * 100,
        inactive=(c("status") == "INA").mean() * 100,
        active_no_snap=((~played) & (c("status") == "ACT")).mean() * 100,
        no_status=c("status").is_null().mean() * 100,
        if_played=c("y").filter(played).mean() * 100,
    )


def rows_check(top: pl.DataFrame, wk: pl.DataFrame) -> None:
    sched = load("game", parts=["schedule"], seasons=SEASONS).select(
        "game_id", "season", "week", "game_type"
    )
    print("Week numbers by type and era:")
    print(sched.group_by("game_type", era=c("season") >= 2021)
          .agg(lo=c("week").min(), hi=c("week").max(), games=pl.len())
          .sort("era", "lo").rows())  # fmt: skip
    pg = load("player_game", parts=["game_status", "depth"], seasons=SEASONS).select(
        *KEYS, "team", "position", "full_name", "status", "depth"
    )
    last = sched.filter(c("game_type") == "REG").group_by("season").agg(last=c("week").max())
    d = (
        top.select(*KEYS, "y", said="mean", p_said="p_nonzero", loss_top="loss")
        .join(wk.select(*KEYS, week_said="mean", p_week="p_nonzero", loss_week="loss"), on=KEYS)
        .join(sched, on="game_id")
        .join(last, on="season")
        .join(pg, on=KEYS, how="left")
        .with_columns(
            starter=(c("depth") == 1).fill_null(False),
            game_team=c("game_id") + c("team"),
        )
    )
    # The same playoff teams: the 4 regular-season weeks before the last one, against their playoffs
    teams = d.filter(c("game_type") != "REG").select("season", "team").unique()
    both = d.join(teams, on=["season", "team"]).with_columns(
        period=pl.when(c("game_type") != "REG").then(pl.lit("b playoffs"))
        .when((c("week") < c("last")) & (c("week") >= c("last") - 4)).then(pl.lit("a late regular"))
    ).filter(c("period").is_not_null())  # fmt: skip
    with pl.Config(float_precision=1, tbl_rows=40, tbl_cols=16, tbl_width_chars=190):
        print("\nThe same teams, late regular season against playoffs")
        print(both.group_by("period").agg(**rates(both)).sort("period"))
        print("Starters and not")
        print(both.group_by("starter", "period").agg(**rates(both)).sort("starter", "period"))
        print("By position")
        print(both.group_by("position", "period").agg(**rates(both)).sort("position", "period"))
        print("\nSince 2019, when `status` marks game-day inactives")
        since = both.filter(c("season") >= 2019)
        print(since.group_by("starter", "period").agg(**rates(since)).sort("starter", "period"))

        po = d.filter(c("game_type") != "REG")
        by = dict(
            rows=pl.len(),
            was=c("y").mean() * 100,
            top=c("said").mean() * 100,
            week=c("week_said").mean() * 100,
            no_snap=(c("y") == 0).mean() * 100,
            top_no_snap=(1 - c("p_said")).mean() * 100,
            week_no_snap=(1 - c("p_week")).mean() * 100,
            gain=(c("loss_week") - c("loss_top")).mean() * 100,
        )
        print("\nBy round")
        print(po.group_by("game_type").agg(**by).sort("rows", descending=True))
        # Did a final week of resting starters mislead the playoff forecast? A player's final-week
        # share against their average before it: filled in, rested, or neither.
        reg = d.filter(c("game_type") == "REG")
        before = (
            reg.filter(c("week") < c("last")).group_by("season", "gsis_id").agg(usual=c("y").mean())
        )
        final = reg.filter(c("week") == c("last")).select("season", "gsis_id", final="y")
        change = (c("final") - c("usual")) * 100
        split = po.join(before.join(final, on=["season", "gsis_id"]), on=["season", "gsis_id"],
                        how="left").with_columns(
            final_week=pl.when(change >= 20).then(pl.lit("filled in, +20 or more"))
            .when(change <= -20).then(pl.lit("rested, -20 or more"))
            .when(change.is_null()).then(pl.lit("no final-week game"))
            .otherwise(pl.lit("neither"))
        )  # fmt: skip
        more = dict(
            **by,
            top_mae=(c("y") - c("said")).abs().mean() * 100,
            week_mae=(c("y") - c("week_said")).abs().mean() * 100,
            top_miss=(c("said") - c("y")).mean() * 100,
            week_miss=(c("week_said") - c("y")).mean() * 100,
        )
        print("\nPlayoffs, by what the player did in the final regular-season week")
        print(split.group_by("final_week").agg(**more).sort("final_week"))
        print("Wild card round only: the final week is their last game")
        wild = split.filter(c("game_type") == "WC")
        print(wild.group_by("final_week").agg(**more).sort("final_week"))
        print("Later rounds")
        later = split.filter(c("game_type") != "WC")
        print(later.group_by("final_week").agg(**more).sort("final_week"))
        # The control: any game far from a player's usual share is followed by a fall back to it.
        # Is that as large in ordinary regular-season weeks, from week 6 to the next to last?
        ordered = reg.sort("gsis_id", "season", "week").with_columns(
            prior=c("y").shift(1).over("gsis_id", "season"),
            usual=c("y").shift(2).cum_sum().over("gsis_id", "season")
            / c("y").shift(2).cum_count().over("gsis_id", "season"),
        )
        move = (c("prior") - c("usual")) * 100
        ordinary = ordered.filter((c("week") >= 6) & (c("week") < c("last"))).with_columns(
            final_week=pl.when(move >= 20).then(pl.lit("last game +20 or more"))
            .when(move <= -20).then(pl.lit("last game -20 or more"))
            .when(move.is_null()).then(pl.lit("no earlier games"))
            .otherwise(pl.lit("neither"))
        )  # fmt: skip
        print("\nThe control: ordinary weeks, by the player's last game against their usual")
        print(ordinary.group_by("final_week").agg(**more).sort("final_week"))
        print("By season, for steadiness")
        print(po.group_by("season").agg(**by).sort("season"))
        print("Largest over-forecasts by `trees_top` among non-starters who took no snap")
        out = po.filter(~c("starter") & (c("y") == 0)).sort("said", descending=True).head(10)
        print(out.select("full_name", "position", "game_id", "status", "depth",
                         top=c("said") * 100, week=c("week_said") * 100))  # fmt: skip
        print("Largest under-forecasts by `trees_top` among starters")
        print(po.filter(c("starter")).with_columns(miss=(c("y") - c("said")) * 100)
              .sort("miss", descending=True).head(6)
              .select("full_name", "position", "game_id", y=c("y") * 100, top=c("said") * 100,
                      week=c("week_said") * 100))  # fmt: skip


def flags() -> None:
    gw = Gateway()
    bt = backtest.run(TreesWeek(), gw, SEASONS, refit="season")
    # Every season, because training starts before the seasons scored
    types = load("game", parts=["schedule"]).select("game_id", "game_type")
    feats = bt.features.join(types, on="game_id", how="left").with_columns(
        playoff=(c("game_type") != "REG").cast(pl.Float64)
    )
    runs = {}
    for name, extra in OPTIONS.items():

        class Option(TreesWeek):
            columns = [*FEATURES, *extra]

        e = Option()
        pred = backtest.walk(e, feats, bt.targets, bt.steps, bt.test, bt.refit, bt.half_life)
        h = backtest.standard(e, pred).join(bt.targets.select(*KEYS, "y"), on=KEYS, how="left")
        runs[name] = (
            scores.row_losses(h, e.kind)
            .filter(c("y").is_not_null())
            .join(feats.select(*KEYS, "position", "playoff", "final_week"), on=KEYS)
            .with_columns(step=c("game_id").str.slice(0, 7))
        )
        print(f"done: {name}", flush=True)
    y = targets(find("participation", "trees_week")(), gw).select(*KEYS, "y")
    base = (
        saved("trees_top", TOP_RUN, y)
        .join(feats.select(*KEYS, "position", "playoff", "final_week"), on=KEYS)
        .with_columns(step=c("game_id").str.slice(0, 7))
    )
    groups = {
        "all": c("y").is_not_null(),
        "playoffs": c("playoff") == 1,
        "last week": c("final_week") == 1,
        "other regular weeks": (c("playoff") == 0) & (c("final_week") == 0),
        "QB": c("position") == "QB",
    }
    print("\nAgainst `trees_top`, pinball x100 (90% interval); MAE of the mean, x100")
    for k, v in runs.items():
        print(k, f"MAE {(v['y'] - v['mean']).abs().mean() * 100:.3f}")
        for g, f in groups.items():
            r = compare(v.filter(f), base.filter(f), KEYS, "step", (k, "trees_top"))
            print(f"  {g:<22} {r.diff * 100:+.3f} ({r.lo * 100:+.3f} to {r.hi * 100:+.3f}): "
                  f"{r.verdict}, {r.rows:,} rows")  # fmt: skip
    print("\nAgainst `trees_week`")
    for k, v in runs.items():
        if k != "trees_week":
            for g, f in groups.items():
                r = compare(v.filter(f), runs["trees_week"].filter(f), KEYS, "step", (k, "week"))
                print(f"  {k:<26} {g:<22} {r.diff * 100:+.3f} ({r.lo * 100:+.3f} to "
                      f"{r.hi * 100:+.3f}): {r.verdict}")  # fmt: skip


def main() -> None:
    e = find("participation", "trees_week")()
    y = targets(e, Gateway()).select(*KEYS, "y")
    rows_check(saved("trees_top", TOP_RUN, y), saved("trees_week", WEEK_RUN, y))
    flags()


if __name__ == "__main__":
    main()
