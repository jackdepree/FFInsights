"""The anti-trait features at a moment (CEO, 2026-11-09: pass and shotgun on offense, live; man
coverage, two-high shells and blitzes on defense, from finished seasons), one option at a time.

The anti-trait claim: a team that avoids an option gains less from it when it does take it (H15).
So every option has two kinds of features, known before kickoff:
- **use** (`<o>_use`): how much the team takes the option beyond what's usual. Below zero is
  avoidance, the anti-trait.
- **past gains** (`<o>_gain_<part>`): how much better its plays went with the option than without,
  the league's level and the team's own history.

**Offense (live, from `team_game.tendencies`).** Use is the team's shrunk season level of the
option (pass rate over expected, shotgun rate) less the league's, less what its opponents so far
usually allow: the CEO's "what teams usually do against that opponent" (brief, 2026-11-09), with
nflfastR's `xpass` as "standard strategy" for passing. The schedule part is each opponent's level
allowed (its defense's games this season and the last, known by the moment), less the league's,
averaged over the team's games this season with `PRIOR_GAMES` games of zero. Past gains are the
same parts as the traits (`features.PARTS`: league, last 4, season, shrunk, last season, coach).

**Defense (from `team_game.charted`, a post-season part).** Use is the team's last season's use
over expected (the league's usual choice for the down, distance and offense look: `charted.py`).
Past gains are the league's over the last two finished seasons and the team's last season. Before
a season is over, nothing of it is known: an in-season view hides it (rule m), and `history` keeps
only rows known by each moment.

A missing team average falls back to the league's (use: to zero).
"""

from __future__ import annotations

import polars as pl

from pcf.experts.schemes_v2 import features as F

c = pl.col
OFFENSE: dict[str, tuple[str, str]] = {  # option → (its use, the level opponents allow)
    "pass": ("neutral_pass_oe", "def_pass_oe"),
    "shotgun": ("shotgun_rate", "def_shotgun_rate"),
}
DEFENSE = ("man", "two_high", "blitz")
OFFENSE_INPUTS = {"team_game": ("schedule", "pregame", "opening_coach", "tendencies")}
DEFENSE_INPUTS = {"team_game": ("schedule", "charted")}
DEFENSE_SEASONS = 2  # the league's gain: the last two finished seasons


def _measures(option: str) -> dict[str, tuple[str, str]]:
    use, _ = OFFENSE[option]
    return {"use": (use, "neutral_plays"), "gain": (f"{option}_gain", f"{option}_gain_n")}


def _schedule(tg: pl.DataFrame, targets: pl.DataFrame, option: str) -> pl.DataFrame:
    """Per target: the sum over the team's games this season (known by the moment) of the
    opponent's level allowed then, and how many there were."""
    _, allowed = OFFENSE[option]
    played = tg.filter(c("tendencies_known_at").is_not_null()).select(
        "team", "opponent", allowed, "def_neutral_plays", h_season="season",
        known="tendencies_known_at",
    )  # fmt: skip
    pairs = targets.select("season", "moment").unique()
    level = (
        pairs.join(played, how="cross")
        .filter(
            (c("known") <= c("moment")) & c("h_season").is_between(c("season") - 1, c("season"))
        )
        .group_by("season", "moment", opponent="team")
        .agg(F._wmean(allowed, "def_neutral_plays").fill_nan(None).alias("allowed"))
    )
    return (
        targets.join(played.select("team", "opponent", "h_season", "known"), on="team")
        .filter((c("known") <= c("moment")) & (c("h_season") == c("season")))
        .join(level, on=["season", "moment", "opponent"], how="inner")
        .drop_nulls("allowed")
        .group_by(F.KEYS)
        .agg(sched_sum=c("allowed").sum(), sched_n=pl.len().cast(pl.Float64))
    )


def _league_allowed(tg: pl.DataFrame, targets: pl.DataFrame, option: str) -> pl.DataFrame:
    _, allowed = OFFENSE[option]
    played = tg.filter(c("tendencies_known_at").is_not_null()).select(
        allowed, "def_neutral_plays", h_season="season", known="tendencies_known_at"
    )
    return (
        targets.select("season", "moment")
        .unique()
        .join(played, how="cross")
        .filter(
            (c("known") <= c("moment")) & c("h_season").is_between(c("season") - 1, c("season"))
        )
        .group_by("season", "moment")
        .agg(F._wmean(allowed, "def_neutral_plays").alias("allowed_league"))
    )


def offense_features(tg: pl.DataFrame, targets: pl.DataFrame, option: str) -> pl.DataFrame:
    """`targets`: game_id, team, season, moment. Columns: keys, season, games, `<o>_use`,
    `<o>_use_raw` (without the opponents' part) and `<o>_gain_<part>`."""
    base = F._features(tg, targets, _measures(option))
    sched = _schedule(tg, targets, option)
    league = _league_allowed(tg, targets, option)
    out = (
        base.join(targets.select(*F.KEYS, "moment"), on=F.KEYS)
        .join(sched, on=F.KEYS, how="left")
        .join(league, on=["season", "moment"], how="left")
    )
    n = c("sched_n").fill_null(0.0)
    opponents = (c("sched_sum").fill_null(0.0) - n * c("allowed_league")) / (n + F.PRIOR_GAMES)
    raw = c("use_shrunk") - c("use_league")
    return (
        out.with_columns(
            raw.alias(f"{option}_use_raw"),
            (raw - opponents.fill_null(0.0)).alias(f"{option}_use"),
            *[c(f"gain_{p}").alias(f"{option}_gain_{p}") for p in F.PARTS],
        )
        .select(
            *F.KEYS,
            "season",
            "games",
            f"{option}_use",
            f"{option}_use_raw",
            *[f"{option}_gain_{p}" for p in F.PARTS],
        )  # fmt: skip
        .sort(F.KEYS)
    )


def defense_features(tg: pl.DataFrame, targets: pl.DataFrame, option: str) -> pl.DataFrame:
    """`targets`: game_id, team, season, moment. Columns: keys, season, `<o>_use`,
    `<o>_gain_league`, `<o>_gain_last_season`."""
    o = option
    charted = tg.filter(c("charted_known_at").is_not_null()).select(
        "team", f"{o}_oe", f"{o}_plays", f"{o}_gain", f"{o}_gain_n",
        h_season="season", known="charted_known_at",
    )  # fmt: skip
    targets = targets.select(*F.KEYS, "season", "moment")
    team = (
        targets.join(charted, on="team")
        .filter((c("known") <= c("moment")) & (c("h_season") == c("season") - 1))
        .group_by(F.KEYS)
        .agg(
            F._wmean(f"{o}_oe", f"{o}_plays").alias("use"),
            F._wmean(f"{o}_gain", f"{o}_gain_n").alias("gain_last"),
        )
    )
    league = (
        targets.select("season", "moment")
        .unique()
        .join(charted.drop("team"), how="cross")
        .filter(
            (c("known") <= c("moment"))
            & c("h_season").is_between(c("season") - DEFENSE_SEASONS, c("season") - 1)
        )
        .group_by("season", "moment")
        .agg(F._wmean(f"{o}_gain", f"{o}_gain_n").alias("league"))
    )
    lg = c("league").fill_nan(None)
    return (
        targets.join(team, on=F.KEYS, how="left")
        .join(league, on=["season", "moment"], how="left")
        .select(
            *F.KEYS,
            "season",
            c("use").fill_nan(None).fill_null(0.0).alias(f"{o}_use"),
            lg.alias(f"{o}_gain_league"),
            pl.coalesce(c("gain_last").fill_nan(None), lg).alias(f"{o}_gain_last_season"),
        )
        .drop_nulls(f"{o}_gain_league")  # no finished season with the option charted yet
        .sort(F.KEYS)
    )


def at_moment(view, games: pl.DataFrame, option: str) -> pl.DataFrame:
    """The moment's `games` (game_id, season, week, kickoff), from a view at `view.at`."""
    season = int(games["season"].max())
    back = F.COACH_SEASONS if option in OFFENSE else DEFENSE_SEASONS
    tg = view.table("team_game", seasons=list(range(season - back, season + 1)))
    moment = games.with_columns(moment=pl.lit(view.at).cast(F.MOMENT))
    return _route(tg, F._targets(tg, moment), option)


def history(view, moments: pl.DataFrame, option: str) -> pl.DataFrame:
    """Every game in `moments` (game_id, …, moment) at its own moment, in one pass."""
    tg = view.table("team_game")
    return _route(tg, F._targets(tg, moments), option)


def _route(tg: pl.DataFrame, targets: pl.DataFrame, option: str) -> pl.DataFrame:
    if option in OFFENSE:
        return offense_features(tg, targets, option)
    return defense_features(tg, targets, option)
