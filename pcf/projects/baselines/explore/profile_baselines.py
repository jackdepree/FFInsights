"""Light exploration for baselines: is there a yardstick in each candidate, and when is it known?

1. The FantasyPros weekly ECR archive: which seasons and weeks, when each snapshot is known, which
   games it can honestly rank (the Friday snapshot is after Thursday's kickoff), and the id match.
2. Rank skill on 2021-2024 player-games: ECR against the 4-game and season-so-far averages and
   last season's per-game average, by rank correlation within each position-week.
3. Points skill: ECR turned into points by a rank-to-points curve fit on 2021-2022, scored on
   2023-2024 against the averages (mean absolute error), on the same rows.
4. Game lines: how close the nflverse closing spread and total come to results, 2016-2024.

The vault (2025) is not read. Run from pcf/:
.venv/Scripts/python.exe projects/baselines/explore/profile_baselines.py
"""

from datetime import timedelta

import numpy as np
import polars as pl

from pcf.config import get_config
from pcf.data.tables.store import load
from pcf.data.timeline.calendar import day_start

c = pl.col
SEASONS = [2020, 2021, 2022, 2023, 2024]
POSITIONS = ["QB", "RB", "WR", "TE"]
POINTS = "fantasy_points_ppr"


def ecr_weekly() -> pl.DataFrame:
    """Weekly positional ECR (PPR pages), with `known_at` (the start of the day after the scrape,
    Eastern) and `gsis_id`."""
    raw = get_config().zone("raw") / "nflverse"
    ecr = pl.read_parquet(raw / "ecr_archive" / "db_fpecr.parquet").filter(
        (c("ecr_type") == "wp") & c("pos").is_in(POSITIONS)
    )
    ids = (
        pl.read_csv(raw / "player_ids" / "db_playerids.csv", infer_schema_length=0)
        .filter(c("fantasypros_id").is_not_null() & c("gsis_id").is_not_null())
        .select(id="fantasypros_id", gsis_id="gsis_id")
        .unique("id")
    )
    return (
        ecr.join(ids, on="id", how="left")
        .with_columns(day=c("scrape_date").str.to_date())
        .with_columns(known_at=day_start(c("day") + timedelta(days=1)))
        .select("gsis_id", "player", "pos", "team", "ecr", "sd", "day", "known_at")
    )


def player_games() -> pl.DataFrame:
    kick = load("game", parts=["schedule"], seasons=SEASONS).select(
        "game_id", "kickoff", "game_type", "weekday"
    )
    return (
        load("player_game", parts=["stats"], seasons=SEASONS)
        .filter(c("position").is_in(POSITIONS) & c(POINTS).is_not_null())
        .join(kick, on="game_id")
        .select("gsis_id", "game_id", "season", "week", "position", "kickoff", "weekday", POINTS)
        .sort("gsis_id", "kickoff")
    )


def snapshots(ecr: pl.DataFrame) -> pl.DataFrame:
    return ecr.group_by("day", "known_at").agg(rows=pl.len()).sort("day")


def coverage(ecr: pl.DataFrame, pg: pl.DataFrame) -> None:
    """Which games each snapshot can rank: kickoffs after it is known and within 4 days."""
    snaps = snapshots(ecr)
    print("Snapshots by season (Sep-Feb) and weekday:")
    s = snaps.with_columns(
        season=pl.when(c("day").dt.month() <= 2).then(c("day").dt.year() - 1).otherwise(c("day").dt.year()),
        weekday=c("day").dt.strftime("%a"),
    ).filter(c("day").dt.month().is_in([9, 10, 11, 12, 1, 2]))
    print(s.group_by("season").agg(snapshots=pl.len(), weekdays=c("weekday").unique().sort(),
                                   first=c("day").min(), last=c("day").max()).sort("season"))  # fmt: skip
    games = pg.select("game_id", "season", "week", "kickoff", "weekday").unique().sort("kickoff")
    games = games.join_asof(
        snaps.select("known_at").sort("known_at"),
        left_on="kickoff", right_on="known_at", strategy="backward",
    ).with_columns(age_days=(c("kickoff") - c("known_at")).dt.total_hours() / 24)  # fmt: skip
    games = games.with_columns(fresh=c("age_days") <= 4)
    print("Games by whether a snapshot from the last 4 days ranks them (2021-2024):")
    print(
        games.filter(c("season") >= 2021)
        .group_by("season", "weekday").agg(games=pl.len(), fresh=c("fresh").mean().round(3))
        .sort("season", "games", descending=[False, True])
    )  # fmt: skip


def features(ecr: pl.DataFrame, pg: pl.DataFrame) -> pl.DataFrame:
    """Each fresh (snapshot, player-game) with ECR and the averages known at the snapshot."""
    snaps = snapshots(ecr).select("known_at").sort("known_at")
    target = pg.sort("kickoff").join_asof(snaps, left_on="kickoff", right_on="known_at", strategy="backward")
    target = target.filter((c("kickoff") - c("known_at")) <= timedelta(days=4))
    rows = target.join(ecr.select("gsis_id", "known_at", "ecr", "sd"), on=["gsis_id", "known_at"])
    # Stats are known 24 hours after kickoff (DATA_SOURCES.md).
    known = pg.with_columns(stats_known=c("kickoff") + timedelta(hours=24)).select(
        "gsis_id", "season", "stats_known", p=c(POINTS)
    )
    out = []
    for at, frame in rows.group_by("known_at"):
        (at,) = at
        season = int(frame["season"].max())
        k = known.filter((c("stats_known") <= at) & c("season").is_between(season - 1, season))
        avg = k.sort("stats_known").group_by("gsis_id").agg(
            last4=c("p").tail(4).mean(),
            season_avg=c("p").filter(c("season") == season).mean(),
            last_season=c("p").filter(c("season") == season - 1).mean(),
        )
        out.append(frame.join(avg, on="gsis_id", how="left"))
    return pl.concat(out)


def rank_skill(rows: pl.DataFrame) -> None:
    """Rank correlation with the result, inside each position-week, on rows every method ranks."""
    both = rows.drop_nulls(["last4", "season_avg", "last_season"]).filter(c("season") >= 2021)
    score = both.with_columns(neg_ecr=-c("ecr"))
    agg = []
    for (pos, at), g in score.group_by("position", "known_at"):
        if g.height < 10:
            continue
        r = g.select(
            [pl.corr(m, POINTS, method="spearman").alias(m) for m in ["neg_ecr", "last4", "season_avg", "last_season"]]
        )  # fmt: skip
        agg.append(r.with_columns(position=pl.lit(pos), n=pl.lit(g.height)))
    res = pl.concat(agg)
    print("Mean Spearman correlation with PPR points inside each position-week, 2021-2024 (ECR = -rank):")
    print(res.group_by("position").agg(pl.col("neg_ecr", "last4", "season_avg", "last_season").mean().round(3),
                                       weeks=pl.len(), rows=c("n").sum()).sort("position"))  # fmt: skip


def points_skill(rows: pl.DataFrame) -> None:
    """ECR as points: mean PPR points by ECR rank, per position, fit on 2021-2022 (a smoothed
    step curve); scored on 2023-2024 with the averages on the same rows."""
    both = rows.drop_nulls(["last4", "season_avg"]).filter(c("season") >= 2021)
    train, test = both.filter(c("season") <= 2022), both.filter(c("season") >= 2023)
    out = []
    for pos in POSITIONS:
        tr, te = train.filter(c("position") == pos), test.filter(c("position") == pos)
        order = np.argsort(tr["ecr"].to_numpy())
        x, y = tr["ecr"].to_numpy()[order], tr[POINTS].to_numpy()[order]
        smooth = np.convolve(y, np.ones(51) / 51, mode="same")  # a running mean over 51 rows
        pred = np.interp(te["ecr"].to_numpy(), x, smooth)
        truth = te[POINTS].to_numpy()
        out.append({
            "position": pos, "rows": te.height,
            "ecr_curve": np.abs(pred - truth).mean(),
            "last4": np.abs(te["last4"].to_numpy() - truth).mean(),
            "season_avg": np.abs(te["season_avg"].to_numpy() - truth).mean(),
        })  # fmt: skip
    print("Mean absolute error, PPR points, 2023-2024 (curve fit on 2021-2022):")
    print(pl.DataFrame(out).with_columns(pl.col("ecr_curve", "last4", "season_avg").round(2)))


def game_lines() -> None:
    """nflverse's (closing) spread and total against results, 2016-2024."""
    g = load("game", parts=["schedule", "pregame", "result"], seasons=list(range(2016, 2025)))
    g = g.drop_nulls(["spread_line", "total_line", "result", "total"])
    print("Closing lines vs results, 2016-2024:")
    print(
        g.select(
            games=pl.len(),
            spread_mae=(c("result") - c("spread_line")).abs().mean().round(2),
            total_mae=(c("total") - c("total_line")).abs().mean().round(2),
            fav_won=((c("result") > 0) == (c("spread_line") > 0)).filter(c("spread_line") != 0).mean().round(3),
            home_moneyline=c("home_moneyline").is_not_null().mean(),
        )
    )  # fmt: skip


def main() -> None:
    pl.Config.set_tbl_rows(60)
    pl.Config.set_tbl_width_chars(160)
    ecr = ecr_weekly()
    print(f"ECR weekly positional rows: {ecr.height:,}; matched to gsis_id: {ecr['gsis_id'].is_not_null().mean():.3%}")
    pg = player_games()
    coverage(ecr, pg)
    rows = features(ecr.drop_nulls("gsis_id"), pg)
    print(f"Fresh ECR player-games (2020-2024): {rows.height:,}")
    rank_skill(rows)
    points_skill(rows)
    game_lines()


if __name__ == "__main__":
    main()
