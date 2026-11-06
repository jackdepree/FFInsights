"""When do injury reports really appear? (2026-11-06) Measured on 2021-2024, the seasons whose files
still carry `date_modified`, to choose the known-at rule for files without it (2009, 2025 on).
Run from pcf/: .venv/Scripts/python.exe projects/prediction-ledger/explore/injury_timing.py

The table keeps one row per player and week, its last version, so `date_modified` here is when the
final version appeared. Nothing is scored.
"""

import polars as pl

from pcf.data.clean.standard import injuries as clean_injuries
from pcf.data.sources.nflverse import scan
from pcf.data.tables.build import _schedules
from pcf.data.timeline.calendar import ET, calendar

c = pl.col
SEASONS = [2021, 2022, 2023, 2024]
DAY = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def reports() -> pl.DataFrame:
    cal = calendar(_schedules())
    kick = pl.concat(
        [
            cal.games.select("season", "week", "game_type", team=c(t), kickoff="kickoff")
            for t in ("home_team", "away_team")
        ]
    ).with_columns(c("season").cast(pl.Int32), c("week").cast(pl.Int32))
    d = clean_injuries(scan("injuries", SEASONS).collect()).with_columns(
        c("season").cast(pl.Int32), c("week").cast(pl.Int32)
    )
    print("Rows, with date_modified:", d.height, d["date_modified"].is_not_null().sum())
    et_kick, et_mod = (
        c("kickoff").dt.convert_time_zone(ET),
        c("date_modified").dt.convert_time_zone(ET),
    )
    return (
        d.drop_nulls("date_modified")
        .join(kick, on=["season", "week", "game_type", "team"])
        .with_columns(
            kick_day=et_kick.dt.weekday().map_elements(lambda x: DAY[x], return_dtype=pl.String),
            mod_day=et_mod.dt.weekday().map_elements(lambda x: DAY[x], return_dtype=pl.String),
            mod_hour=et_mod.dt.hour() + et_mod.dt.minute() / 60,
            days_before=(et_kick.dt.date() - et_mod.dt.date()).dt.total_days(),
            hours_before=(c("kickoff") - c("date_modified")).dt.total_minutes() / 60,
            has_status=c("report_status").is_not_null(),
        )
    )


def main() -> None:
    d = reports()
    with pl.Config(tbl_rows=60, tbl_cols=14, tbl_width_chars=170, float_precision=1):
        print("\nHours from the final version to kickoff, by kickoff day")
        print(
            d.group_by("kick_day")
            .agg(
                rows=pl.len(),
                games=(
                    c("season").cast(pl.String) + "_" + c("week").cast(pl.String) + c("team")
                ).n_unique()
                / 2,
                p01=c("hours_before").quantile(0.01),
                p10=c("hours_before").quantile(0.10),
                p50=c("hours_before").quantile(0.50),
                p90=c("hours_before").quantile(0.90),
            )
            .sort("rows", descending=True)
        )
        print("\nDays before kickoff the final version appeared, by kickoff day (share of rows)")
        print(
            d.group_by("kick_day", "days_before").agg(rows=pl.len(), hour_p50=c("mod_hour").median(),
                hour_p90=c("mod_hour").quantile(0.9), hour_p99=c("mod_hour").quantile(0.99))
            .with_columns(share=c("rows") / c("rows").sum().over("kick_day") * 100)
            .filter(c("share") >= 1).sort("kick_day", "days_before")
        )  # fmt: skip
        print("\nDifferent seasons: Sunday games, final version's day and median hour")
        print(
            d.filter(c("kick_day") == "Sun").group_by("season", "days_before")
            .agg(rows=pl.len(), hour_p50=c("mod_hour").median(), hour_p90=c("mod_hour").quantile(.9))
            .with_columns(share=c("rows") / c("rows").sum().over("season") * 100)
            .filter(c("share") >= 3).sort("season", "days_before")
        )  # fmt: skip


def rule(kick: pl.Expr) -> pl.Expr:
    """Candidate: nflverse's file updates once a day, around 9 to 12 Eastern, so a final report is
    in the file by noon the day after it's issued. Saturday, Sunday and Monday games have their
    final report two days before; other days, the day before."""
    et = kick.dt.convert_time_zone(ET)
    two_days = et.dt.weekday().is_in([6, 7, 1])
    day = et.dt.date() - pl.when(two_days).then(pl.duration(days=1)).otherwise(pl.duration(days=0))
    noon = (day.cast(pl.Datetime("us")) + pl.duration(hours=12)).dt.replace_time_zone(ET)
    return pl.min_horizontal(noon.dt.convert_time_zone("UTC"), kick - pl.duration(hours=1))


def check_rule(d: pl.DataFrame) -> None:
    """How often is the rule too early, and does it show the same rows at each moment?"""
    et = c("kickoff").dt.convert_time_zone(ET)
    r = d.with_columns(
        known=rule(c("kickoff")),
        # The moment a Saturday model predicts each game: Saturday noon, or Wednesday 16:00 for
        # games before it
        moment=pl.when(et.dt.weekday().is_in([6, 7, 1]) & (c("hours_before").is_not_null()))
        .then(pl.lit("Sat 12:00"))
        .when(et.dt.weekday() >= 4)
        .then(pl.lit("Wed 16:00"))
        .otherwise(pl.lit("Tue 10:00")),
    ).with_columns(
        too_early=c("date_modified") > c("known"),
        at_kick=c("known") >= c("kickoff"),
    )
    with pl.Config(tbl_rows=40, tbl_cols=14, tbl_width_chars=170, float_precision=2):
        print("\nThe rule against the real times, by kickoff day")
        print(
            r.group_by("kick_day").agg(
                rows=pl.len(), too_early=c("too_early").mean() * 100,
                status_too_early=(c("too_early") & c("has_status")).sum() / c("has_status").sum() * 100,
                late_hours_p50=((c("known") - c("date_modified")).dt.total_minutes() / 60).median(),
                after_kick=c("at_kick").sum(),
            ).sort("rows", descending=True)
        )  # fmt: skip
        print("By season")
        print(
            r.group_by("season")
            .agg(rows=pl.len(), too_early=c("too_early").mean() * 100)
            .sort("season")
        )
        print("All seasons, all rows:", round(r["too_early"].mean() * 100, 2), "% too early")
        # Thursday games at Wednesday 16:00: how much of the final report was out by then?
        thu = r.filter(c("kick_day") == "Thu").with_columns(
            wed16=(et.dt.date().cast(pl.Datetime("us")) - pl.duration(hours=8))
            .dt.replace_time_zone(ET).dt.convert_time_zone("UTC")
        ).with_columns(seen=c("date_modified") <= c("wed16"))  # fmt: skip
        print("\nThursday games: seen by Wednesday 16:00 in the real times")
        print(thu.group_by("has_status").agg(rows=pl.len(), seen=c("seen").mean() * 100))
        sun = r.filter(c("kick_day") == "Sun").with_columns(
            sat12=((et.dt.date() - pl.duration(days=1)).cast(pl.Datetime("us")) + pl.duration(hours=12))
            .dt.replace_time_zone(ET).dt.convert_time_zone("UTC")
        ).with_columns(seen=c("date_modified") <= c("sat12"))  # fmt: skip
        print("Sunday games: seen by Saturday 12:00 in the real times")
        print(sun.group_by("has_status").agg(rows=pl.len(), seen=c("seen").mean() * 100))


if __name__ == "__main__":
    main()
    check_rule(reports())
