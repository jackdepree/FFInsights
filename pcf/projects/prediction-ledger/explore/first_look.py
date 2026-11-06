"""First look for the prediction ledger (2026-11-06): can today's code forecast games that haven't
been played, how long does it take, and are the rows right?
Run from pcf/: .venv/Scripts/python.exe projects/prediction-ledger/explore/first_look.py

The harness refuses live seasons (`check_seasons`), so this walks the steps itself. Nothing is
saved: it only reports. Training uses every season, because a live model should.
"""

import time
from datetime import UTC, datetime

import polars as pl

from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.validation import backtest, scores
from pcf.validation.splits import steps

c = pl.col
NOW = datetime.now(UTC)
SEASON = 2026


def freshness() -> None:
    sched = load("game", parts=["schedule"], seasons=[SEASON])
    print("Now:", NOW.isoformat(timespec="minutes"))
    print(
        "Schedule rows and kickoff column:", sched.height, [x for x in sched.columns if "kick" in x]
    )
    pg = load("player_game", parts=["snaps", "depth", "injury", "game_status"], seasons=[SEASON])
    games = pg.select("game_id").unique().height
    print("player_game rows, games:", pg.height, games)
    with pl.Config(tbl_rows=30, tbl_cols=10, tbl_width_chars=150):
        print(
            pg.with_columns(week=c("game_id").str.slice(5, 2).cast(pl.Int32))
            .group_by("week")
            .agg(
                rows=pl.len(),
                games=c("game_id").n_unique(),
                snaps=c("offense_pct").is_not_null().sum(),
                depth=c("depth").is_not_null().sum(),
                report=c("report_status").is_not_null().sum(),
                status=c("status").is_not_null().sum(),
            )
            .sort("week")
        )


def forecast(variant: str) -> pl.DataFrame:
    e = find("participation", variant)()
    gw = Gateway()
    t0 = time.perf_counter()
    first = e.first_train
    every = steps(gw.calendar, e.cadence, range(first, SEASON + 1), e.run, e.event)
    # The last step that has started is this week: most of its games are still to come
    use = [s for s in every if s.at <= NOW]
    print(f"{variant}: {len(use)} steps used of {len(every)}; last: {use[-1].season, use[-1].week}")
    feats = backtest.feature_history(e, gw, use)
    t1 = time.perf_counter()
    outcomes = backtest.targets(e, gw)
    t2 = time.perf_counter()
    pred = backtest.walk(e, feats, outcomes, use, [use[-1].index], refit="season")
    t3 = time.perf_counter()
    print(
        f"seconds: features {t1 - t0:.0f}, outcomes {t2 - t1:.0f}, fit and predict {t3 - t2:.0f}, "
        f"rows {pred.height}, train_end {pred['train_end'].max()}, "
        f"as_of {pred['as_of'].unique().to_list()}"
    )
    return pred.join(feats.select(*e.keys(), "position", "team", "depth"), on=e.keys(), how="left")


def check_rows(pred: pl.DataFrame) -> None:
    names = load("player_game", parts=["roster"], seasons=[SEASON]).select(
        "gsis_id", "game_id", "full_name"
    )
    d = pred.join(names, on=["gsis_id", "game_id"], how="left")
    with pl.Config(tbl_rows=40, tbl_cols=12, tbl_width_chars=170, float_precision=1):
        print("Games:", d["game_id"].unique().sort().to_list())
        print(
            d.group_by("position").agg(
                rows=pl.len(),
                per_team_game=pl.len() / (c("game_id") + c("team")).n_unique(),
                mean=c("mean").mean() * 100,
                low=c("q10").mean() * 100,
                high=c("q90").mean() * 100,
                null_mean=c("mean").is_null().sum(),
            )
        )
        print("Top QBs and WRs by forecast")
        for pos in ("QB", "WR"):
            print(
                d.filter(c("position") == pos)
                .sort("mean", descending=True)
                .head(6)
                .select(
                    "full_name", "game_id", "depth",
                    mean=c("mean") * 100, q10=c("q10") * 100, q50=c("q50") * 100,
                    q90=c("q90") * 100, p_snap=c("p_nonzero") * 100,
                )
            )  # fmt: skip


def report_gap(variant: str = "trees_week") -> None:
    """Does the Saturday forecast see the injury report, in the backtest and in live seasons?
    Files from 2025 have no `date_modified`. On 2026-11-06 their rule was kickoff - 12 hours, which
    these numbers exposed; `injury_fix_check.py` is the same count after the fix."""
    e = find("participation", variant)()
    gw = Gateway()
    every = steps(gw.calendar, e.cadence, range(2022, SEASON + 1), e.run, e.event)
    use = [s for s in every if s.week in (6, 7, 8) and s.at <= NOW]
    feats = backtest.feature_history(e, gw, use)
    print("\nRows with an injury-report status in the features, weeks 6-8")
    with pl.Config(tbl_rows=20, float_precision=1):
        print(
            feats.with_columns(season=c("game_id").str.slice(0, 4))
            .group_by("season")
            .agg(
                rows=pl.len(),
                with_report=(c("report") > 0).sum(),
                per_100=(c("report") > 0).mean() * 100,
                practice=c("practice").is_not_null().mean() * 100,
            )
            .sort("season")
        )
    inj = load("player_game", parts=["injury"], seasons=[2024, SEASON]).filter(
        c("report_status").is_not_null() & c("game_id").str.slice(5, 2).is_in(["07", "08"])
    )
    sched = load("game", parts=["schedule"], seasons=[2024, SEASON]).select("game_id", "kickoff")
    print("Hours from the report being known to kickoff")
    print(
        inj.join(sched, on="game_id")
        .with_columns(
            season=c("game_id").str.slice(0, 4),
            hours=(c("kickoff") - c("injury_known_at")).dt.total_minutes() / 60,
        )
        .group_by("season")
        .agg(rows=pl.len(), lo=c("hours").min(), mid=c("hours").median(), hi=c("hours").max())
        .sort("season")
    )


def roster_lag() -> None:
    """If this week's roster rows haven't landed, how well does last week's list stand in?"""
    pg = load("player_game", parts=["roster"], seasons=[2024, 2025, SEASON]).filter(
        c("position").is_in(["QB", "RB", "WR", "TE"])
    )
    sched = load("game", parts=["schedule"], seasons=[2024, 2025, SEASON]).select(
        "game_id", "season", "week"
    )
    d = pg.select("gsis_id", "game_id", "team").join(sched, on="game_id")
    prior = d.select("gsis_id", "team", "season", week=c("week") + 1).unique()
    both = d.join(
        prior.with_columns(had=pl.lit(1)), on=["gsis_id", "team", "season", "week"], how="left"
    ).filter(c("week") > 1)
    print(
        "\nOf each week's rows, the share where the player was on that team's list the week before"
    )
    print(both.group_by("season").agg(rows=pl.len(), share=c("had").is_not_null().mean() * 100))


def report_arrival(base_file: str) -> None:
    """Our first snapshot, Saturday 2026-10-31 13:31 Eastern: was Friday's report for Sunday's
    games in nflverse's file by then? Pass a copy of the injuries base file from pcf-data."""
    d = pl.read_parquet(base_file).filter(c("week") == 8)
    print("\nWeek 8 injury rows in the Saturday snapshot:", d.height)
    print(d.group_by("report_status").agg(pl.len()).sort("report_status"))


def report_cost(season: int = 2024) -> None:
    """What losing the report costs: score one backtest season with and without it."""
    e = find("participation", "trees_week")()
    gw = Gateway()
    every = steps(gw.calendar, e.cadence, range(e.first_train, season + 1), e.run, e.event)
    test = [s.index for s in every if s.season == season]
    feats = backtest.feature_history(e, gw, every)
    print("\nPractice feature by season:")
    print(
        feats.with_columns(season=c("game_id").str.slice(0, 4))
        .filter(c("season").is_in(["2023", "2024"]))
        .group_by("season")
        .agg(report=(c("report") > 0).mean() * 100, practice=(c("practice") > 0).mean() * 100)
    )
    y = backtest.targets(e, gw)
    keys = e.keys()
    # Blanked only in the rows predicted, as live: training still has the reports
    blank = feats.with_columns(
        report=pl.when(c("step").is_in(test)).then(0.0).otherwise(c("report")),
        practice=pl.when(c("step").is_in(test)).then(0.0).otherwise(c("practice")),
    )
    groups = {"all": c("y").is_not_null(), "on the report": c("on_report")}
    scored = {}
    for name, f in (("with report", feats), ("report hidden", blank)):
        p = backtest.walk(e, f, y, every, test, refit="season")
        h = backtest.standard(e, p).join(y.select(*keys, "y"), on=keys, how="left")
        scored[name] = (
            scores.row_losses(h, e.kind)
            .filter(c("y").is_not_null())
            .join(feats.select(*keys, on_report=c("report") > 0), on=keys)
        )
    for g, f in groups.items():
        a, b = (scored[n].filter(f) for n in scored)
        print(
            f"{g:<14} rows {a.height:>6}: range score x100 {a['loss'].mean() * 100:.3f} with, "
            f"{b['loss'].mean() * 100:.3f} hidden; average miss x100 "
            f"{(a['y'] - a['mean']).abs().mean() * 100:.2f} with, "
            f"{(b['y'] - b['mean']).abs().mean() * 100:.2f} hidden; said "
            f"{a['mean'].mean() * 100:.1f} with, {b['mean'].mean() * 100:.1f} hidden; "
            f"was {a['y'].mean() * 100:.1f}"
        )


def fill_rates(variant: str = "trees_week") -> None:
    """Which inputs look different live than in the backtest? Weeks 6-8, Saturday forecasts."""
    e = find("participation", variant)()
    gw = Gateway()
    every = steps(gw.calendar, e.cadence, range(2024, SEASON + 1), e.run, e.event)
    use = [s for s in every if s.week in (6, 7, 8) and s.season in (2024, SEASON)]
    feats = backtest.feature_history(e, gw, use).with_columns(season=c("game_id").str.slice(0, 4))
    rows = []
    for col in e.columns:
        if feats.schema[col].is_numeric():
            a, b = (feats.filter(c("season") == s)[col] for s in ("2024", str(SEASON)))
            rows.append(
                dict(
                    input=col,
                    used_2024=(a.fill_null(0) != 0).mean() * 100,
                    used_2026=(b.fill_null(0) != 0).mean() * 100,
                    missing_2024=a.is_null().mean() * 100,
                    missing_2026=b.is_null().mean() * 100,
                )
            )
    d = pl.DataFrame(rows).with_columns(gap=(c("used_2024") - c("used_2026")).abs())
    print(f"\nInputs compared: {d.height}; rows {feats.group_by('season').len().rows()}")
    with pl.Config(tbl_rows=15, float_precision=1, tbl_width_chars=120):
        print(d.sort("gap", descending=True).head(12))


def main() -> None:
    freshness()
    check_rows(forecast("trees_week"))
    report_gap()
    roster_lag()
    fill_rates()
    report_cost()
    # report_arrival(path) needs a copy of the injuries base file from pcf-data


if __name__ == "__main__":
    main()
