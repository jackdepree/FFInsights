"""Moving the Wednesday 16:00 run to Thursday noon (CEO, 2026-11-06): what changes?
Run from pcf/: .venv/Scripts/python.exe projects/prediction-ledger/explore/thursday_run.py

Which games move, how many reports the moved rows see at each time, how much of the final report
was really out by then, and how the rows look in live seasons. Nothing is scored here, so the 2025
vault stays closed. The scores, on 2016-2024 only, are in `thursday_scores.py`.
"""

from datetime import UTC, datetime

import polars as pl

from pcf.core.contract import find
from pcf.data.gateway import Gateway
from pcf.data.tables.store import load
from pcf.data.timeline import moments
from pcf.data.timeline.calendar import ET
from pcf.validation import backtest
from pcf.validation.splits import steps

c = pl.col
NOW = datetime.now(UTC)
NEW = dict(moments.RUNS)
OLD = {"tuesday": (2, 10), "wednesday": (3, 16), "saturday": (6, 12)}
DAY = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def use_runs(which: dict) -> None:
    moments.RUNS.clear()
    moments.RUNS.update(which)


def games_moved(gw: Gateway) -> None:
    """Which games get a different moment, for a Saturday model, by kickoff day."""
    frames = {}
    for name, which, run in (("old", OLD, "saturday"), ("new", NEW, "saturday")):
        use_runs(which)
        frames[name] = moments.game_moments(gw.calendar, run)
    use_runs(NEW)
    d = frames["new"].join(
        frames["old"].select("game_id", old="moment", old_fallback="fallback"), on="game_id"
    )
    et = c("kickoff").dt.convert_time_zone(ET)
    hours = (c("kickoff") - c("moment")).dt.total_minutes() / 60
    d = d.with_columns(
        day=et.dt.weekday().map_elements(lambda i: DAY[i], return_dtype=pl.String),
        moved=c("moment") != c("old"),
        hours=hours,
        old_hours=(c("kickoff") - c("old")).dt.total_minutes() / 60,
        at_day=c("moment").dt.convert_time_zone(ET).dt.weekday(),
    )
    with pl.Config(tbl_rows=12, float_precision=1, tbl_width_chars=120):
        print("Games since 2016 by kickoff day: moved, and hours from moment to kickoff")
        print(
            d.filter(c("season") >= 2016)
            .group_by("day")
            .agg(
                games=pl.len(),
                moved=c("moved").sum(),
                old_lo=c("old_hours").min(),
                old_mid=c("old_hours").median(),
                new_lo=c("hours").min(),
                new_mid=c("hours").median(),
                new_hi=c("hours").max(),
            )
            .sort("games", descending=True)
        )
        print("Games that now go back to an earlier moment, since 2016 (the Wednesday games)")
        print(
            d.filter((c("season") >= 2016) & (c("moment") < c("old")))
            .select("game_id", "day", "old_hours", "hours")
            .sort("game_id")
        )
        print("Still to come in 2026, not on Sunday, Monday or at Thursday noon")
        print(
            d.filter(
                (c("season") == 2026) & (c("kickoff") > NOW) & c("day").is_in(["Wed", "Fri", "Sat"])
            )
            .select("game_id", "day", "hours")
            .sort("game_id")
        )
    for run in ("tuesday", "thursday", "saturday"):
        m = moments.game_moments(gw.calendar, run)
        print(f"Fallback games since 1999, {run}: {m['fallback'].sum()}")


def real_times() -> None:
    """2021-2024, Thursday games: was each final report out by each moment, in real times?"""
    inj = load("player_game", parts=["injury"], seasons=[2021, 2022, 2023, 2024]).filter(
        c("report_status").is_not_null()
    )
    sched = load("game", parts=["schedule"], seasons=[2021, 2022, 2023, 2024]).select(
        "game_id", "kickoff"
    )
    et = c("kickoff").dt.convert_time_zone(ET)

    def at(days: int, hour: int) -> pl.Expr:
        day = et.dt.date().cast(pl.Datetime("us")) - pl.duration(days=days)
        return (day + pl.duration(hours=hour)).dt.replace_time_zone(ET).dt.convert_time_zone("UTC")

    d = (
        inj.join(sched, on="game_id")
        .with_columns(day=et.dt.weekday())
        .filter(c("day") == 4)
        .with_columns(
            wed_16=c("injury_known_at") <= at(1, 16),
            thu_12=c("injury_known_at") <= at(0, 12),
        )
    )
    print(
        f"\nThursday games 2021-2024, {d.height} reports with a status, known by: "
        f"Wed 16:00 {d['wed_16'].mean() * 100:.1f}%, Thu 12:00 {d['thu_12'].mean() * 100:.1f}%"
    )


def reports_at_moment(gw: Gateway, variant: str = "trees_week") -> None:
    """Thursday games' rows with a report, at the old and new moment. Rows are only counted."""
    e = find("participation", variant)()
    thursday = gw.calendar.games.filter(
        (c("kickoff").dt.convert_time_zone(ET).dt.weekday() == 4) & (c("kickoff") <= NOW)
    ).select("game_id")
    out = {}
    for name, which in (("wed_16", OLD), ("thu_12", NEW)):
        use_runs(which)
        every = steps(gw.calendar, e.cadence, range(2022, 2027), e.run, e.event)
        feats = backtest.feature_history(e, gw, [s for s in every if s.at <= NOW])
        out[name] = feats.join(thursday, on="game_id").select(
            *e.keys(), "report", "practice", "mates_out"
        )
    use_runs(NEW)
    keys = e.keys()
    both = out["thu_12"].join(out["wed_16"], on=keys, suffix="_old", how="full", coalesce=True)
    with pl.Config(tbl_rows=8, float_precision=1, tbl_width_chars=120):
        print("\nThursday games' rows: share with a report, practice status or teammate out")
        print(
            both.with_columns(season=c("game_id").str.slice(0, 4))
            .group_by("season")
            .agg(
                rows=pl.len(),
                report_wed=(c("report_old") > 0).mean() * 100,
                report_thu=(c("report") > 0).mean() * 100,
                practice_wed=(c("practice_old") > 0).mean() * 100,
                practice_thu=(c("practice") > 0).mean() * 100,
                mates_wed=(c("mates_out_old") > 0).mean() * 100,
                mates_thu=(c("mates_out") > 0).mean() * 100,
            )
            .sort("season")
        )


def main() -> None:
    gw = Gateway()
    games_moved(gw)
    real_times()
    reports_at_moment(gw)


if __name__ == "__main__":
    main()
