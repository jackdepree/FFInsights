"""The `team_game` part `tendencies`: how each team chose to play in a game, from play-by-play.

One row per team and game, known when play-by-play is (kickoff + 1 day). Offense columns describe
the team with the ball, `def_` columns what the team's defense faced and did. Everything is
measured in **neutral situations** (schemes-v2 exploration, "Data and definitions"): run and pass
plays on downs 1-3, win chance 20-80%, outside the last two minutes of a half, no kneels or
spikes. Outside them, the score and the clock choose the plays, not the team.

A play-level table is ~2.7 GB in memory, so models read these game totals instead (decision 0023).
The builder is pure: play-by-play rows in, the part's rows out.
"""

import polars as pl

from pcf.data.clean import standard

c = pl.col
NEUTRAL_WIN_CHANCE = (0.2, 0.8)
END_OF_HALF_SECONDS = 120
DEEP_AIR_YARDS = 20  # the usual "deep" cut
# Seconds between snaps that count as tempo: shorter is a no-play, longer a stoppage.
TEMPO_SECONDS = (5, 60)
PBP_COLUMNS = [
    "game_id", "play_id", "season", "posteam", "defteam", "down", "qtr", "wp",
    "half_seconds_remaining", "game_seconds_remaining", "pass", "rush", "xpass", "shotgun",
    "no_huddle", "qb_dropback", "qb_scramble", "qb_kneel", "qb_spike", "air_yards",
    "pass_attempt", "sack", "qb_hit", "penalty", "out_of_bounds", "fixed_drive", "epa",
]  # fmt: skip
OFFENSE = [
    "neutral_plays", "neutral_pass_oe", "shotgun_rate", "no_huddle_rate", "scramble_rate",
    "air_attempts", "air_yards_per_att", "deep_rate", "tempo_plays", "tempo_seconds",
    "pass_gain", "pass_gain_n", "shotgun_gain", "shotgun_gain_n",
]  # fmt: skip
DEFENSE = [
    "def_neutral_plays", "def_pass_oe", "def_dropbacks", "def_pressure_rate",
    "def_air_attempts", "def_air_yards_per_att", "def_shotgun_rate",
]  # fmt: skip


def scrimmage(pbp: pl.DataFrame) -> pl.DataFrame:
    """Run and pass plays with both teams named, with the neutral-situation flag."""
    lo, hi = NEUTRAL_WIN_CHANCE
    plays = pbp.filter(
        ((c("pass") == 1) | (c("rush") == 1))
        & (c("qb_kneel") == 0)
        & (c("qb_spike") == 0)
        & c("posteam").is_not_null()
        & c("defteam").is_not_null()
    )
    return standard.standard_teams(plays, "posteam", "defteam").with_columns(
        neutral=(
            c("wp").is_between(lo, hi)
            & c("down").is_between(1, 3)
            & (c("half_seconds_remaining") > END_OF_HALF_SECONDS)
            & (c("qtr") <= 4)
        ).fill_null(False),
        # A thrown ball with a charted depth (sacks and throwaways without one are left out)
        air=(c("pass_attempt") == 1) & (c("sack") == 0) & c("air_yards").is_not_null(),
    )


def _tempo(plays: pl.DataFrame) -> pl.DataFrame:
    """Seconds of game clock from an in-bounds run to the next snap of the same drive: the clock
    was running, so the gap is the offense's pace. Per offense and game."""
    prev = [c(x).shift(1).over("game_id") for x in ("rush", "out_of_bounds", "penalty")]
    lo, hi = TEMPO_SECONDS
    return (
        plays.sort("game_id", "play_id")
        .with_columns(
            gap=c("game_seconds_remaining").shift(1).over("game_id") - c("game_seconds_remaining"),
            running=(prev[0] == 1)
            & (prev[1] == 0)
            & (prev[2] == 0)
            & (c("fixed_drive").shift(1).over("game_id") == c("fixed_drive")),
        )
        .filter(c("neutral") & c("running") & c("gap").is_between(lo, hi))
        .group_by("game_id", team="posteam")
        .agg(tempo_plays=pl.len().cast(pl.Int32), tempo_seconds=c("gap").mean())
    )


def _effective(n1: pl.Expr, n0: pl.Expr) -> pl.Expr:
    """The effective plays behind a difference of two means: n1 * n0 / (n1 + n0)."""
    return (n1 * n0 / (n1 + n0)).cast(pl.Float64)


def _gains(n: pl.DataFrame) -> pl.DataFrame:
    """Each offense's gain from passing and from the shotgun, per game (the anti-traits' target,
    schemes-v2 brief, CEO 2026-11-09): mean EPA when taking the option less when not.
    - `pass_gain`: dropbacks (sacks and scrambles included) against runs;
    - `shotgun_gain`: shotgun against under center, within passes and within runs, then averaged
      with the effective plays as weights, so it isn't passing's gain over again.
    `<o>_gain_n` is the effective plays; both are null when one side has no plays."""
    e = n.filter(c("epa").is_not_null())
    cells = e.group_by("game_id", "posteam", "pass").agg(
        g=c("epa").filter(c("shotgun") == 1).mean() - c("epa").filter(c("shotgun") == 0).mean(),
        w=_effective((c("shotgun") == 1).sum(), (c("shotgun") == 0).sum()),
    )
    shotgun = (
        cells.filter(c("w") > 0)
        .group_by("game_id", team="posteam")
        .agg(shotgun_gain=(c("g") * c("w")).sum() / c("w").sum(), shotgun_gain_n=c("w").sum())
    )
    passing = e.group_by("game_id", team="posteam").agg(
        pass_gain=c("epa").filter(c("pass") == 1).mean() - c("epa").filter(c("pass") == 0).mean(),
        pass_gain_n=_effective((c("pass") == 1).sum(), (c("pass") == 0).sum()),
    )
    return passing.join(shotgun, on=["game_id", "team"], how="full", coalesce=True).with_columns(
        pass_gain_n=pl.when(c("pass_gain").is_not_null()).then(c("pass_gain_n"))
    )


def tendency_rows(pbp: pl.DataFrame) -> pl.DataFrame:
    """Play-by-play (`PBP_COLUMNS`) → one row per team and game: game_id, team, season, and the
    `OFFENSE` and `DEFENSE` columns. Rates are 0-1; a rate with nothing to count is null."""
    plays = scrimmage(pbp.select(PBP_COLUMNS))
    n = plays.filter(c("neutral"))
    dropback = c("qb_dropback") == 1
    offense = n.group_by("game_id", "season", team="posteam").agg(
        neutral_plays=pl.len().cast(pl.Int32),
        neutral_pass_oe=(c("pass") - c("xpass")).mean(),
        shotgun_rate=c("shotgun").mean(),
        no_huddle_rate=c("no_huddle").mean(),
        scramble_rate=c("qb_scramble").filter(dropback).mean(),
        air_attempts=c("air").sum().cast(pl.Int32),
        air_yards_per_att=c("air_yards").filter(c("air")).mean(),
        deep_rate=(c("air_yards") >= DEEP_AIR_YARDS).filter(c("air")).mean(),
    )
    defense = n.group_by("game_id", "season", team="defteam").agg(
        def_neutral_plays=pl.len().cast(pl.Int32),
        def_pass_oe=(c("pass") - c("xpass")).mean(),
        def_dropbacks=dropback.sum().cast(pl.Int32),
        def_pressure_rate=((c("sack") == 1) | (c("qb_hit") == 1)).filter(dropback).mean(),
        def_air_attempts=c("air").sum().cast(pl.Int32),
        def_air_yards_per_att=c("air_yards").filter(c("air")).mean(),
        def_shotgun_rate=c("shotgun").mean(),
    )
    keys = ["game_id", "team", "season"]
    return (
        offense.join(defense, on=keys, how="full", coalesce=True)
        .join(_tempo(plays), on=["game_id", "team"], how="left")
        .join(_gains(n), on=["game_id", "team"], how="left")
        .with_columns(c("season").cast(pl.Int32))
        .select(*keys, *OFFENSE, *DEFENSE)
        .sort("game_id", "team")
    )
