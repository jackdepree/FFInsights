"""The `team_game` part `charted`: how each defense chose to play on dropbacks, from participation.

One row per defense and game, **known when participation is: after the season** (a post-season
part, so an in-season model sees it only for finished seasons, rule m). For each defensive option
(`OPTIONS`: man coverage, a two-high shell, a blitz of 5+ rushers), on neutral-situation dropbacks
(as in `tendencies`) where the option is charted:
- `<o>_plays`: dropbacks charted, `<o>_rate`: share with the option;
- `<o>_oe`: use over expected, the mean of (choice - the league's usual choice). The usual choice
  is the league's rate that season for the same down, distance, offense formation (shotgun or not)
  and personnel (heavy or not): what defenses usually do against that look (the CEO's "clearly
  favorable", schemes-v2 brief, 2026-11-09). A whole finished season sets it, which is fine: the
  part isn't known before that season ends;
- `<o>_gain`: EPA prevented when taking the option less when not (higher is better for the
  defense), and `<o>_gain_n`, its effective plays (n_yes * n_no / (n_yes + n_no); null when one
  side has none).

The builder is pure: play-by-play and participation rows in, the part's rows out.
"""

import polars as pl

from pcf.data.clean import personnel
from pcf.data.tables.tendencies import scrimmage

c = pl.col
DISTANCE_BUCKETS = [3, 6, 10]  # yards to go: 1-3, 4-6, 7-10, 11+
PBP_COLUMNS = [
    "game_id", "play_id", "season", "posteam", "defteam", "down", "ydstogo", "qtr", "wp",
    "half_seconds_remaining", "pass", "rush", "shotgun", "qb_dropback", "qb_kneel", "qb_spike",
    "air_yards", "pass_attempt", "sack", "epa",
]  # fmt: skip
PARTICIPATION_COLUMNS = [
    "nflverse_game_id", "play_id", "offense_personnel", "number_of_pass_rushers",
    "defense_man_zone_type", "defense_coverage_type",
]  # fmt: skip
SHELLS = ["COVER_0", "COVER_1", "COVER_2", "COVER_3", "COVER_4", "COVER_6", "2_MAN"]
TWO_HIGH = ["COVER_2", "COVER_4", "COVER_6", "2_MAN"]
OPTIONS = ("man", "two_high", "blitz")
COLUMNS = [f"{o}_{x}" for o in OPTIONS for x in ("plays", "rate", "oe", "gain", "gain_n")]


def rushers() -> pl.Expr:
    """Pass rushers where charted: 1-11 (0 is a dropback left uncharted, 0.1-0.4% a season)."""
    r = c("number_of_pass_rushers")
    return pl.when(r.is_between(1, 11)).then(r)


def choices() -> list[pl.Expr]:
    """Each option as 1.0 / 0.0 where it's charted, else null. For dropbacks only."""
    mz, cov = c("defense_man_zone_type"), c("defense_coverage_type")
    return [
        pl.when(mz.is_in(["MAN_COVERAGE", "ZONE_COVERAGE"]))
        .then((mz == "MAN_COVERAGE").cast(pl.Float64))
        .alias("man"),
        pl.when(cov.is_in(SHELLS)).then(cov.is_in(TWO_HIGH).cast(pl.Float64)).alias("two_high"),
        (rushers() >= 5).cast(pl.Float64).alias("blitz"),
    ]


def _gain(o: str) -> list[pl.Expr]:
    yes, no = c(o) == 1.0, c(o) == 0.0
    n1, n0 = yes.sum(), no.sum()
    # EPA prevented: the defense gains when the offense's EPA is lower
    gain = c("epa").filter(no).mean() - c("epa").filter(yes).mean()
    ok = (n1 > 0) & (n0 > 0)
    return [
        pl.when(ok).then(gain).alias(f"{o}_gain"),
        pl.when(ok).then(n1 * n0 / (n1 + n0)).cast(pl.Float64).alias(f"{o}_gain_n"),
    ]


def charted_rows(pbp: pl.DataFrame, participation: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play (`PBP_COLUMNS`) and raw participation (`PARTICIPATION_COLUMNS`) for one or
    more seasons → one row per defense and game: game_id, team, season and `COLUMNS`. Raises if
    participation lists a play twice."""
    part = participation.select(PARTICIPATION_COLUMNS).rename({"nflverse_game_id": "game_id"})
    part = part.with_columns(c("play_id").cast(pl.Int64))
    if part.select(pl.struct("game_id", "play_id").is_duplicated().any()).item():
        raise ValueError("participation lists a play twice")
    plays = (
        scrimmage(pbp.select(PBP_COLUMNS).with_columns(c("play_id").cast(pl.Int64)))
        .filter(c("neutral") & (c("qb_dropback") == 1) & c("epa").is_not_null())
        .join(part, on=["game_id", "play_id"], how="inner")
        .with_columns(
            *choices(),
            # 0: 1-3 yards to go, 1: 4-6, 2: 7-10, 3: 11+
            dist=pl.sum_horizontal(c("ydstogo") > b for b in DISTANCE_BUCKETS),
            # backs (fullbacks too, 2023 on) and tight ends
            heavy=personnel.heavy(c("offense_personnel")),
        )
    )
    cell = ["season", "down", "dist", "shotgun", "heavy"]
    plays = plays.with_columns((c(o) - c(o).mean().over(cell)).alias(f"{o}_resid") for o in OPTIONS)
    aggs = []
    for o in OPTIONS:
        aggs += [
            c(o).count().cast(pl.Int32).alias(f"{o}_plays"),
            c(o).mean().alias(f"{o}_rate"),
            c(f"{o}_resid").mean().alias(f"{o}_oe"),
            *_gain(o),
        ]
    return (
        plays.group_by("game_id", "season", team="defteam")
        .agg(aggs)
        .with_columns(c("season").cast(pl.Int32))
        .select("game_id", "team", "season", *COLUMNS)
        .sort("game_id", "team")
    )
