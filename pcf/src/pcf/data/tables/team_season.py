"""The `team_season` table: each team's charted traits in a season, from participation.

One row per team and season, in one part, `charted` (the spine). It's **retrospective** (rule
m): participation is published after the season, so the row is known the day after that season's
Super Bowl (the participation rule), and an in-season view sees it only for finished seasons
(post-season part, leakage check 5). Its timing columns, so later models can use it without
leaking:
- `known_at`: when PCF could first have had the row; the gateway's column;
- `first_kickoff`, `last_kickoff`: the first and last regular-season kickoffs it sums up;
- `prior_for`: the first season whose in-season models may use the row (season + 1), as a prior.

Measured over the regular season, in neutral situations (`tendencies.scrimmage`), on plays that
participation charts. Every measure comes raw and over expected (`<m>_oe`): the mean of the
team's choice less the league's usual choice that season in the same cell.
- **The offense's choices** (`off_`): personnel 11, 12 and 21, heavy (3+ backs and tight ends),
  the pistol, and time to throw. Cell: down and distance.
- **What the offense faced** (`off_faced_`) **and what the defense chose** (`def_`): box count,
  man coverage, a two-high shell, a blitz of 5+, and (defense only) pass rushers, nickel (5
  defensive backs) and dime (6+). Cell: down, distance, shotgun and the offense's personnel group:
  what defenses usually do against that look.
- Pass-play measures are on dropbacks; box and personnel on every play. Coverage and shells are
  charted from 2018 (null before). Counts: `games`, `off_plays`, `off_dropbacks`, `def_plays`,
  `def_dropbacks`.

The builder is pure: play-by-play, participation and the calendar in, the part's rows out.
"""

import polars as pl

from pcf.data.clean import personnel
from pcf.data.tables.charted import DISTANCE_BUCKETS, PBP_COLUMNS, choices, rushers
from pcf.data.tables.tendencies import scrimmage
from pcf.data.timeline import Calendar
from pcf.data.timeline.known_at import known_at

c = pl.col
PARTICIPATION_COLUMNS = [
    "nflverse_game_id", "play_id", "offense_personnel", "defense_personnel", "offense_formation",
    "defenders_in_box", "number_of_pass_rushers", "defense_man_zone_type",
    "defense_coverage_type", "time_to_throw",
]  # fmt: skip
# (output column, play-level choice)
OFFENSE = [
    ("off_11_rate", "p11"), ("off_12_rate", "p12"), ("off_21_rate", "p21"),
    ("off_heavy_rate", "heavy"), ("off_pistol_rate", "pistol"), ("off_time_to_throw", "ttt"),
]  # fmt: skip
FACED = [
    ("off_faced_box", "box"), ("off_faced_man_rate", "man"),
    ("off_faced_two_high_rate", "two_high"), ("off_faced_blitz_rate", "blitz"),
]  # fmt: skip
DEFENSE = [
    ("def_box", "box"), ("def_man_rate", "man"), ("def_two_high_rate", "two_high"),
    ("def_blitz_rate", "blitz"), ("def_rushers", "rushers"), ("def_nickel_rate", "nickel"),
    ("def_dime_rate", "dime"),
]  # fmt: skip
OFFENSE_CELL = ["season", "down", "dist"]
LOOK_CELL = ["season", "down", "dist", "shotgun", "group"]
TIMING = ["first_kickoff", "last_kickoff", "prior_for"]
COUNTS = ["games", "off_plays", "off_dropbacks", "def_plays", "def_dropbacks"]
MEASURES = [m for col, _ in (*OFFENSE, *FACED, *DEFENSE) for m in (col, f"{col}_oe")]
COLUMNS = [*TIMING, *COUNTS, *MEASURES]


def _flag(when: pl.Expr, value: pl.Expr) -> pl.Expr:
    return pl.when(when).then(value.cast(pl.Float64))


def charted_plays(pbp: pl.DataFrame, participation: pl.DataFrame) -> pl.DataFrame:
    """Neutral run and pass plays that participation charts, with each choice as a play-level
    column (1.0 / 0.0, or a count; null where it isn't charted) and the two cells' residuals:
    `<choice>_ro` against the offense cell, `<choice>_rl` against the look cell."""
    part = participation.select(PARTICIPATION_COLUMNS).rename({"nflverse_game_id": "game_id"})
    part = part.with_columns(c("play_id").cast(pl.Int64))
    if part.select(pl.struct("game_id", "play_id").is_duplicated().any()).item():
        raise ValueError("participation lists a play twice")
    drop = c("qb_dropback") == 1
    off_p, def_p = c("offense_personnel"), c("defense_personnel")
    rb, te = personnel.count(off_p, personnel.BACKS), personnel.count(off_p, personnel.TIGHT_ENDS)
    dbs = personnel.count(def_p, personnel.DEFENSIVE_BACKS)
    known = rb.is_not_null() & te.is_not_null()
    dbs_ok = dbs.is_between(1, 11)
    form = c("offense_formation")
    plays = (
        scrimmage(pbp.select(PBP_COLUMNS).with_columns(c("play_id").cast(pl.Int64)))
        .filter(c("neutral"))
        .join(part, on=["game_id", "play_id"], how="inner")
        .with_columns(
            # 0: 1-3 yards to go, 1: 4-6, 2: 7-10, 3: 11+
            dist=pl.sum_horizontal(c("ydstogo") > b for b in DISTANCE_BUCKETS),
            group=personnel.offense_group(off_p),
            p11=_flag(known, (rb == 1) & (te == 1)),
            p12=_flag(known, (rb == 1) & (te == 2)),
            p21=_flag(known, (rb == 2) & (te == 1)),
            heavy=_flag(known, rb + te >= 3),
            pistol=_flag(form.is_not_null() & (form != ""), form == "PISTOL"),
            ttt=pl.when(drop & (c("time_to_throw") > 0)).then(c("time_to_throw")),
            box=_flag(c("defenders_in_box").is_between(1, 11), c("defenders_in_box")),
            rushers=_flag(drop, rushers()),
            nickel=_flag(dbs_ok, dbs == 5),
            dime=_flag(dbs_ok, dbs >= 6),
        )
        .with_columns(pl.when(drop).then(x).alias(x.meta.output_name()) for x in choices())
    )
    off = {x for _, x in OFFENSE}
    look = {x for _, x in (*FACED, *DEFENSE)}
    return plays.with_columns(
        *((c(x) - c(x).mean().over(OFFENSE_CELL)).alias(f"{x}_ro") for x in off),
        *((c(x) - c(x).mean().over(LOOK_CELL)).alias(f"{x}_rl") for x in look),
    )


def _side(plays: pl.DataFrame, team: str, prefix: str, measures, resid: str) -> pl.DataFrame:
    aggs = [
        pl.len().cast(pl.Int32).alias(f"{prefix}_plays"),
        (c("qb_dropback") == 1).sum().cast(pl.Int32).alias(f"{prefix}_dropbacks"),
    ]
    for col, x in measures:
        aggs += [c(x).mean().alias(col), c(f"{x}_{resid}").mean().alias(f"{col}_oe")]
    return plays.group_by("season", team=team).agg(aggs)


def team_season_rows(pbp: pl.DataFrame, participation: pl.DataFrame, cal: Calendar) -> pl.DataFrame:
    """Play-by-play (`charted.PBP_COLUMNS`), raw participation (`PARTICIPATION_COLUMNS`) and the
    calendar, for one or more seasons → the `charted` part: one row per team and season with
    team, season, `known_at` and `COLUMNS`. Regular-season games only."""
    reg = cal.games.filter(c("game_type") == "REG")
    plays = charted_plays(pbp, participation).join(reg.select("game_id"), on="game_id", how="semi")
    plays = plays.with_columns(c("season").cast(pl.Int32))
    offense = _side(plays, "posteam", "off", OFFENSE, "ro")
    faced = _side(plays, "posteam", "off", FACED, "rl").drop("off_plays", "off_dropbacks")
    defense = _side(plays, "defteam", "def", DEFENSE, "rl")
    games = (
        pl.concat([plays.select("season", "game_id", team=c(t)) for t in ("posteam", "defteam")])
        .group_by("season", "team")
        .agg(games=c("game_id").n_unique().cast(pl.Int32))
    )
    kickoffs = (
        pl.concat(
            [
                reg.select("season", team=c(side), kickoff="kickoff")
                for side in ("home_team", "away_team")
            ]
        )
        .group_by("season", "team")
        .agg(first_kickoff=c("kickoff").min(), last_kickoff=c("kickoff").max())
    )
    # Participation's rule: the day after the season's Super Bowl
    ids = plays.select(nflverse_game_id="game_id").unique()
    season_known = (
        known_at("participation", ids, cal)
        .join(
            reg.select(nflverse_game_id="game_id", season=c("season").cast(pl.Int32)),
            on="nflverse_game_id",
        )
        .group_by("season")
        .agg(c("known_at").max())
    )
    keys = ["season", "team"]
    return (
        offense.join(faced, on=keys, how="full", coalesce=True)
        .join(defense, on=keys, how="full", coalesce=True)
        .join(games, on=keys, how="left")
        .join(kickoffs.with_columns(c("season").cast(pl.Int32)), on=keys, how="left")
        .join(season_known, on="season", how="left")
        .with_columns(prior_for=(c("season") + 1).cast(pl.Int32))
        .select("team", "season", "known_at", *COLUMNS)
        .sort("season", "team")
    )


def team_season_parts(
    pbp: pl.DataFrame, participation: pl.DataFrame, cal: Calendar
) -> dict[str, pl.DataFrame]:
    """The `team_season` parts: `charted` (the spine, and so far the only part)."""
    return {"charted": team_season_rows(pbp, participation, cal)}
