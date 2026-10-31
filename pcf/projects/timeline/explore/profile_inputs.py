"""Light exploration for `timeline`: what the raw nflverse copy says about when things happen.

1. Schedules: games per season, game types, missing kickoff times, days of the week.
2. Is `gametime` Eastern time? Scheduled kickoff vs the first play's UTC clock (`time_of_day`).
3. Week windows: the first and last game day of each week, and weeks that overlap.
4. Injuries: `date_modified` against the "noon ET the day before" known-at rule.
5. Daily depth charts (2025+): when snapshots are taken.
6. Offseason dates: which sources carry dates at all, and whether trades show the draft.

Run from pcf/:  uv run python projects/timeline/explore/profile_inputs.py
"""

import sys

import polars as pl

from pcf.data.sources.nflverse import scan

ET = "America/New_York"


def kickoffs() -> pl.DataFrame:
    s = scan("schedules").collect()
    return s.with_columns(
        kickoff=(pl.col("gameday") + " " + pl.col("gametime"))
        .str.to_datetime("%Y-%m-%d %H:%M", time_zone=ET, ambiguous="earliest")
        .dt.convert_time_zone("UTC")
    )


def schedules_profile(s: pl.DataFrame) -> None:
    print("\n## 1. Schedules")
    print(
        s.group_by("season")
        .agg(
            games=pl.len(),
            reg=(pl.col("game_type") == "REG").sum(),
            post=(pl.col("game_type") != "REG").sum(),
            weeks=pl.col("week").max(),
            no_time=pl.col("gametime").is_null().sum(),
            neutral=(pl.col("location") == "Neutral").sum(),
            unplayed=pl.col("result").is_null().sum(),
        )
        .sort("season")
    )
    print(s["game_type"].value_counts().sort("count", descending=True))
    print(s.filter(pl.col("season") >= 2016).group_by("weekday").len().sort("len", descending=True))
    played = s.filter(pl.col("season") < 2026)
    print(
        "past games with no result:",
        played.filter(pl.col("result").is_null()).select("game_id", "gameday").rows(),
    )


def gametime_is_eastern(s: pl.DataFrame) -> None:
    print("\n## 2. Scheduled kickoff (gametime as ET) vs the first play's UTC clock")
    out = []
    for season in range(2011, 2026):
        p = (
            scan("pbp", [season])
            .select("game_id", "time_of_day")
            .drop_nulls("time_of_day")
            .group_by("game_id")
            .agg(first_play=pl.col("time_of_day").min())
            .collect()
        )
        g = s.filter(pl.col("season") == season).join(p, on="game_id")
        # time_of_day is a full UTC timestamp (ISO, with Z).
        g = g.with_columns(
            minutes=(
                pl.col("first_play").str.to_datetime(time_zone="UTC") - pl.col("kickoff")
            ).dt.total_minutes()
        )
        out.append(g.select("season", "game_id", "location", "stadium", "minutes"))
    d = pl.concat(out)
    print(
        d.group_by("season")
        .agg(
            games=pl.len(),
            median=pl.col("minutes").median(),
            q01=pl.col("minutes").quantile(0.01),
            q99=pl.col("minutes").quantile(0.99),
            early=(pl.col("minutes") < -5).sum(),
            late_60=(pl.col("minutes") > 60).sum(),
        )
        .sort("season")
    )
    print("neutral-site games:")
    print(
        d.filter(pl.col("location") == "Neutral")
        .group_by("stadium")
        .agg(games=pl.len(), median=pl.col("minutes").median())
        .sort("games", descending=True)
        .head(10)
    )
    print("first play before the scheduled kickoff:")
    print(d.filter(pl.col("minutes") < -5).head(10))
    print("first play over 60 minutes late:")
    print(d.filter(pl.col("minutes") > 60).sort("minutes", descending=True).head(10))


def week_windows(s: pl.DataFrame) -> None:
    print("\n## 3. Week windows")
    w = (
        s.with_columns(day=pl.col("gameday").str.to_date())
        .group_by("season", "week")
        .agg(
            first=pl.col("day").min(),
            last=pl.col("day").max(),
            games=pl.len(),
            types=pl.col("game_type").unique().sort().str.join(","),
        )
        .sort("season", "week")
        .with_columns(
            span=(pl.col("last") - pl.col("first")).dt.total_days(),
            next_first=pl.col("first").shift(-1).over("season"),
        )
        .with_columns(gap=(pl.col("next_first") - pl.col("last")).dt.total_days())
    )
    print("weeks spanning more than 5 days:")
    print(w.filter(pl.col("span") > 5))
    print("weeks overlapping the next (gap <= 0):")
    print(w.filter(pl.col("gap") <= 0))
    print("gaps between weeks:", w["gap"].value_counts().sort("gap").rows())
    print("season start and end:")
    print(
        w.group_by("season")
        .agg(first=pl.col("first").min(), last=pl.col("last").max())
        .sort("season")
        .tail(8)
    )


def injuries_timing(s: pl.DataFrame) -> None:
    print("\n## 4. Injury reports: date_modified vs the known-at rule")
    games = pl.concat(
        [
            s.select("season", "week", "game_type", team=pl.col(t), kickoff="kickoff")
            for t in ("home_team", "away_team")
        ]
    )
    i = (
        scan("injuries", range(2009, 2026))
        .select("season", "week", "game_type", "team", "date_modified")
        .collect()
        .with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32))
    )
    print("null date_modified by season:")
    print(
        i.group_by("season")
        .agg(rows=pl.len(), null=pl.col("date_modified").is_null().mean())
        .sort("season")
    )
    j = i.drop_nulls("date_modified").join(
        games, on=["season", "week", "game_type", "team"], how="inner"
    )
    rule = (
        (pl.col("kickoff").dt.convert_time_zone(ET).dt.date() - pl.duration(days=1))
        .cast(pl.Datetime("us"))
        .dt.replace_time_zone(ET)
        + pl.duration(hours=12)
    ).dt.convert_time_zone("UTC")
    j = j.with_columns(
        modified=pl.col("date_modified").dt.replace_time_zone("UTC")
        if j["date_modified"].dtype == pl.Datetime("us")
        else pl.col("date_modified"),
        rule=rule,
    )
    print("date_modified dtype:", i["date_modified"].dtype)
    print(
        j.group_by("season")
        .agg(
            rows=pl.len(),
            after_rule=(pl.col("modified") > pl.col("rule")).mean(),
            after_kickoff=(pl.col("modified") > pl.col("kickoff")).mean(),
            after_kickoff_7d=(pl.col("modified") > pl.col("kickoff") + pl.duration(days=7)).mean(),
        )
        .sort("season")
    )


def depth_snapshots() -> None:
    print("\n## 5. Daily depth-chart snapshots (2025+)")
    d = (
        scan("depth_charts", [2025, 2026])
        .select("dt")
        .unique()
        .collect()
        .with_columns(taken=pl.col("dt").str.to_datetime(time_zone="UTC"))
        .sort("taken")
    )
    print("snapshots:", d.height, d["taken"].min(), "->", d["taken"].max())
    print("UTC hour:", d["taken"].dt.hour().value_counts().sort("taken").rows())
    gaps = d["taken"].diff().dt.total_hours().drop_nulls()
    print("hours between snapshots:", gaps.describe().rows())
    print(
        "longest gaps:",
        d.with_columns(gap=pl.col("taken").diff().dt.total_hours())
        .sort("gap", descending=True)
        .head(5)
        .rows(),
    )


def offseason_dates() -> None:
    print("\n## 6. Offseason dates")
    for name in ["draft_picks", "combine", "contracts", "players"]:
        cols = scan(name).collect_schema()
        dates = [c for c, t in cols.items() if t in (pl.Date, pl.Datetime) or "date" in c]
        print(f"{name}: date-like columns {dates}")
    t = scan("trades").collect()
    print(
        "trades:",
        t["trade_id"].n_unique(),
        "trades,",
        t["trade_date"].min(),
        "->",
        t["trade_date"].max(),
        "null:",
        t["trade_date"].is_null().sum(),
    )
    print(
        "trades by month:",
        t.unique("trade_id")
        .group_by(pl.col("trade_date").dt.month().alias("m"))
        .len()
        .sort("m")
        .rows(),
    )
    # Draft-day trades swap that year's picks. The busiest such day in April-May should be a
    # draft day.
    draft = (
        t.filter(
            (pl.col("pick_season") == pl.col("trade_date").dt.year())
            & pl.col("trade_date").dt.month().is_in([4, 5])
        )
        .unique("trade_id")
        .group_by(year=pl.col("trade_date").dt.year(), day=pl.col("trade_date"))
        .len()
        .sort("year", "len", descending=[False, True])
        .group_by("year", maintain_order=True)
        .agg(pl.col("day").head(3), pl.col("len").head(3))
    )
    print("busiest pick-trade days in April-May, by year:")
    print(draft.tail(12))
    w = scan("weekly_rosters", range(2002, 2027)).select("season", "week").unique().collect()
    print(
        "weekly roster weeks:",
        w.group_by("season")
        .agg(pl.col("week").min().alias("min"), pl.col("week").max().alias("max"), pl.len())
        .sort("season")
        .tail(6)
        .rows(),
    )
    e = scan("ecr_archive").select("scrape_date").unique().collect()
    print("ECR archive scrapes:", e.height, e["scrape_date"].min(), "->", e["scrape_date"].max())


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # polars tables don't fit cp1252
    pl.Config.set_tbl_width_chars(200)
    pl.Config.set_tbl_cols(16)
    pl.Config.set_tbl_rows(40)
    s = kickoffs()
    schedules_profile(s)
    gametime_is_eastern(s)
    week_windows(s)
    injuries_timing(s)
    depth_snapshots()
    offseason_dates()


if __name__ == "__main__":
    main()
