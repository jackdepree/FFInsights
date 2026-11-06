"""Why does the plain week help (2026-11-05, F29)? `trees_week` against `trees_top`, from their
saved harness runs: where the gain falls in the season, who it moves, and how top teams' starters
fare in the last week.
Run from pcf/: .venv/Scripts/python.exe projects/participation/explore/why_week.py
"""

import polars as pl

from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.validation.backtest import targets
from pcf.validation.compare import compare
from pcf.validation.scores import row_losses

c = pl.col
KEYS = ["gsis_id", "game_id"]
SEASONS = list(range(2016, 2025))
TOP_RUN = "0c2a1ac624954337bf11257efc0a7001"
WEEK_RUN = "5a1155eaf7a94883a265e6d62b407e00"


def history(variant: str, run: str, y: pl.DataFrame, kind: str) -> pl.DataFrame:
    h = pl.read_parquet(f"data/outputs/participation/{variant}/{run}/history.parquet")
    return row_losses(h.join(y, on=KEYS), kind).filter(c("y").is_not_null())


def win_rates(sched: pl.DataFrame, last: pl.DataFrame) -> pl.DataFrame:
    """Each team's win rate before the last regular-season week, for grouping only."""
    res = load("game", parts=["result"], seasons=SEASONS).select(
        "game_id", "home_score", "away_score"
    )
    g = sched.filter(c("game_type") == "REG").join(res, on="game_id")
    margin = (c("home_score") - c("away_score")).cast(pl.Float64)
    sides = pl.concat(
        [
            g.select("season", "week", team="home_team", m=margin),
            g.select("season", "week", team="away_team", m=-margin),
        ]
    ).with_columns(w=c("m").gt(0).cast(pl.Float64) + 0.5 * c("m").eq(0).cast(pl.Float64))
    return (
        sides.join(last, on="season")
        .filter(c("week") < c("last"))
        .group_by("season", "team")
        .agg(win_rate=c("w").mean())
    )


def table(frame: pl.DataFrame, by: list[str]) -> pl.DataFrame:
    return (
        frame.group_by(by)
        .agg(
            n=pl.len(),
            was=c("y").mean() * 100,
            top=c("top").mean() * 100,
            week=c("week_f").mean() * 100,
            zero=(c("y") == 0).mean() * 100,
            top_zero=(1 - c("p_top")).mean() * 100,
            week_zero=(1 - c("p_week")).mean() * 100,
            top_mae=(c("y") - c("top")).abs().mean() * 100,
            week_mae=(c("y") - c("week_f")).abs().mean() * 100,
        )
        .sort(by)
    )


def main() -> None:
    e = find("participation", "trees_week")()
    y = targets(e, Gateway()).select(*KEYS, "y")
    sched = load("game", parts=["schedule"], seasons=SEASONS).select(
        "game_id", "season", "week", "game_type", "home_team", "away_team"
    )
    last = sched.filter(c("game_type") == "REG").group_by("season").agg(last=c("week").max())
    pg = load("player_game", parts=["depth"], seasons=SEASONS).select(
        *KEYS, "position", "team", "depth"
    )
    context = (
        sched.join(last, on="season")
        .with_columns(
            period=pl.when(c("game_type") != "REG").then(pl.lit("e playoffs"))
            .when(c("week") == c("last")).then(pl.lit("d last week"))
            .when(c("week") <= 2).then(pl.lit("a weeks 1-2"))
            .when(c("week") <= 8).then(pl.lit("b weeks 3-8"))
            .otherwise(pl.lit("c weeks 9 to next to last")),
        )
        .select("game_id", "season", "period")
    )  # fmt: skip
    new, old = (
        history(v, r, y, e.kind)
        .join(context, on="game_id")
        .join(pg, on=KEYS, how="left")
        .with_columns(step=c("game_id").str.slice(0, 7), starter=(c("depth") == 1).fill_null(False))
        for v, r in (("trees_week", WEEK_RUN), ("trees_top", TOP_RUN))
    )

    print("Paired by week, trees_week - trees_top, pinball x100 (90% interval)")
    groups = {p: c("period") == p for p in sorted(context["period"].unique())}
    groups |= {
        "regular season": c("period") != "e playoffs",
        "regular, not last week": ~c("period").is_in(["d last week", "e playoffs"]),
        "playoffs, starters": (c("period") == "e playoffs") & c("starter"),
        "playoffs, not starters": (c("period") == "e playoffs") & ~c("starter"),
    }
    for g, f in groups.items():
        x = compare(new.filter(f), old.filter(f), KEYS, "step", ("week", "top"))
        print(f"  {g:<28} {x.diff * 100:+.3f} ({x.lo * 100:+.3f} to {x.hi * 100:+.3f}) "
              f"{x.verdict}, {x.rows:,} rows")  # fmt: skip

    d = (
        old.select(*KEYS, "y", "period", "season", "team", "position", "starter", top="mean",
                   p_top="p_nonzero")
        .join(new.select(*KEYS, week_f="mean", p_week="p_nonzero"), on=KEYS)
    )  # fmt: skip
    with pl.Config(float_precision=2, tbl_rows=40, tbl_cols=12, tbl_width_chars=130):
        print("\nAll players")
        print(table(d, ["period"]))
        print("Starters")
        print(table(d.filter(c("starter")), ["period"]))
        print("Not starters")
        print(table(d.filter(~c("starter")), ["period"]))
        rates = win_rates(sched, last)
        top_teams = (
            d.filter((c("period") == "d last week") & c("starter"))
            .join(rates, on=["season", "team"])
            .filter(c("win_rate") >= 0.65)
        )
        print("Last week, starters on teams with 65%+ wins")
        print(table(top_teams, ["position"]))


if __name__ == "__main__":
    main()
