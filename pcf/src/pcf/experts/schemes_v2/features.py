"""The trait features at a moment, from `team_game` only: for each team in the moment's games and
each trait, the league's level and the team's own history known by then.

Per trait `<t>` (see `TRAITS`), every average weighted by the plays it was measured on:
- `<t>_league`: every team's games in this season and the last;
- `<t>_last4`: the team's last 4 games (this season and the last);
- `<t>_season`: the team's season to date, and `<t>_shrunk`, the same shrunk toward the league
  with `PRIOR_GAMES` games' weight (0 games played → the league);
- `<t>_last_season`: the team's last season;
- `<t>_coach`: every game the team's head coach has coached in the last three seasons, for any
  team (schemes follow the coach: exploration F4). The coach is the one from the team's latest
  known game this season; before its first, the coach it opens the season with (`opening_coach`,
  known from the start of week 1: decision 0025), else last season's last. A later game's own
  coach is known only at its kickoff, so a mid-season change counts from the new coach's first
  game.
A missing average falls back to the league's, so every feature is filled; `games` is the team's
games this season.

For rung 2 (`<t>_opp`, decision 0025): the opponent's bend, the shrunk season gap from the league
of what offenses do against the opposing defense (`DEF_TRAITS`; 0 where unknown). Tempo has none.

`at_moment` is the per-moment version the contract defines; `history` computes every game's in one
pass and must give the same rows (the leakage checks compare them).
"""

from __future__ import annotations

import polars as pl

c = pl.col
INPUTS = {"team_game": ("schedule", "pregame", "opening_coach", "tendencies")}
KEYS = ["game_id", "team"]
# trait → (the tendency column, the plays it's measured on)
TRAITS: dict[str, tuple[str, str]] = {
    "pass_oe": ("neutral_pass_oe", "neutral_plays"),
    "shotgun": ("shotgun_rate", "neutral_plays"),
    "tempo": ("tempo_seconds", "tempo_plays"),
    "depth": ("air_yards_per_att", "air_attempts"),
}
# trait → what offenses do against a team's defense, and the plays it's measured on (rung 2)
DEF_TRAITS: dict[str, tuple[str, str]] = {
    "pass_oe": ("def_pass_oe", "def_neutral_plays"),
    "shotgun": ("def_shotgun_rate", "def_neutral_plays"),
    "depth": ("def_air_yards_per_att", "def_air_attempts"),
}
PRIOR_GAMES = 4.0  # the league's weight in the shrunk season average, in games
LAST_N = 4
COACH_SEASONS = 3
PARTS = ("league", "last4", "season", "shrunk", "last_season", "coach")
MOMENT = pl.Datetime("us", "UTC")


def _wmean(value: str, weight: str, where: pl.Expr | None = None) -> pl.Expr:
    """The play-weighted mean of `value` over the rows where it's measured (and `where`)."""
    ok = c(value).is_not_null() & (c(weight) > 0)
    if where is not None:
        ok = ok & where
    return (c(value) * c(weight)).filter(ok).sum() / c(weight).filter(ok).sum()


def _team_aggs(traits: dict[str, tuple[str, str]]) -> list[pl.Expr]:
    this, last = c("h_season") == c("season"), c("h_season") == c("season") - 1
    aggs = [
        c("coach").drop_nulls().last().alias("coach_now"),
        this.sum().cast(pl.Float64).alias("games"),
    ]
    for t, (v, w) in traits.items():
        measured = c(v).is_not_null() & (c(w) > 0)
        aggs += [
            _wmean(v, w, this).alias(f"{t}_season"),
            _wmean(v, w, last).alias(f"{t}_last_season"),
            (c(v) * c(w)).filter(measured & this).sum().alias(f"{t}_sum"),
            c(w).filter(measured & this).sum().cast(pl.Float64).alias(f"{t}_n"),
            c(w).filter(measured).mean().alias(f"{t}_per_game"),
            (
                (c(v) * c(w)).filter(measured).tail(LAST_N).sum()
                / c(w).filter(measured).tail(LAST_N).sum()
            ).alias(f"{t}_last4"),
        ]
    return aggs


def _features(
    tg: pl.DataFrame,
    targets: pl.DataFrame,
    traits: dict[str, tuple[str, str]] = TRAITS,
    known: str = "tendencies_known_at",
) -> pl.DataFrame:
    """`targets`: game_id, team, season, moment. `tg`: team-games with their tendencies.
    `traits`: the measures to average (default `TRAITS`; the anti-traits add their own).
    `known`: the known-at column of the part the measures come from (pace reads its own part)."""
    columns = sorted({col for pair in traits.values() for col in pair})
    played = tg.filter(c(known).is_not_null()).select(
        "team", "kickoff", "coach", *columns, h_season="season", known=known
    )
    targets = targets.select(*KEYS, "season", "moment")
    # The team's own games known by the moment, oldest first
    own = (
        targets.join(played, on="team", how="left")
        .filter((c("known") <= c("moment")) & (c("h_season") >= c("season") - 1))
        .sort(*KEYS, "kickoff")
    )
    team = own.group_by(KEYS, maintain_order=True).agg(_team_aggs(traits))
    # The league: every game known by the moment in this season and the last
    pairs = targets.select("season", "moment").unique()
    league = (
        pairs.join(played, how="cross")
        .filter(
            (c("known") <= c("moment")) & c("h_season").is_between(c("season") - 1, c("season"))
        )
        .group_by("season", "moment")
        .agg(_wmean(v, w).alias(f"{t}_league") for t, (v, w) in traits.items())
    )
    out = targets.join(team, on=KEYS, how="left").join(league, on=["season", "moment"], how="left")
    # Before the team's first game of the season, the coach it opens with, if known by then
    if "opening_coach" in tg.columns:
        opening = tg.filter(c("opening_coach").is_not_null()).select(
            "team", "season", "opening_coach", oc_known="opening_coach_known_at"
        )
        out = (
            out.join(opening, on=["team", "season"], how="left")
            .with_columns(
                coach_now=pl.when((c("games").fill_null(0) == 0) & (c("oc_known") <= c("moment")))
                .then(c("opening_coach"))
                .otherwise(c("coach_now"))
            )
            .drop("opening_coach", "oc_known")
        )
    # The head coach's games for any team, known by the moment
    coached = (
        out.select(*KEYS, "season", "moment", "coach_now")
        .drop_nulls("coach_now")
        .join(played.drop_nulls("coach"), left_on="coach_now", right_on="coach", how="inner")
        .filter((c("known") <= c("moment")) & (c("h_season") > c("season") - COACH_SEASONS))
        .group_by(KEYS)
        .agg(_wmean(v, w).alias(f"{t}_coach") for t, (v, w) in traits.items())
    )
    out = out.join(coached, on=KEYS, how="left").with_columns(c("games").fill_null(0.0))
    for t in traits:
        lg = c(f"{t}_league")
        # the league's level, worth the plays of PRIOR_GAMES typical games
        prior = PRIOR_GAMES * c(f"{t}_per_game").fill_null(0.0)
        shrunk = (c(f"{t}_sum").fill_null(0.0) + prior * lg) / (c(f"{t}_n").fill_null(0.0) + prior)
        out = out.with_columns(
            pl.when(prior > 0).then(shrunk).otherwise(lg).alias(f"{t}_shrunk"),
            # before a team's first game of the season, its season is last season's
            pl.coalesce(c(f"{t}_season").fill_nan(None), c(f"{t}_last_season").fill_nan(None), lg)
            .alias(f"{t}_season"),
            *[
                pl.coalesce(c(f"{t}_{p}").fill_nan(None), lg).alias(f"{t}_{p}")
                for p in ("last4", "last_season", "coach")
            ],
        )  # fmt: skip
    cols = [f"{t}_{p}" for t in traits for p in PARTS]
    return (
        out.select(*KEYS, "season", "games", *[c(x).fill_nan(None) for x in cols])
        .drop_nulls(cols)  # no league level yet: nothing known at all
        .sort(KEYS)
    )


def _with_opponent(tg: pl.DataFrame, targets: pl.DataFrame, out: pl.DataFrame) -> pl.DataFrame:
    """`out` plus `<t>_opp`: the opposing defense's shrunk gap from the league, known by then."""
    d = _features(tg, targets, {f"opp_{t}": v for t, v in DEF_TRAITS.items()})
    gaps = [(c(f"opp_{t}_shrunk") - c(f"opp_{t}_league")).alias(f"{t}_opp") for t in DEF_TRAITS]
    other = d.select("game_id", c("team").alias("opp_team"), *gaps)
    opp = (
        targets.select(KEYS)
        .join(other, on="game_id")
        .filter(c("opp_team") != c("team"))
        .drop("opp_team")
    )
    return (
        out.join(opp, on=KEYS, how="left")
        .with_columns(c(f"{t}_opp").fill_null(0.0) for t in DEF_TRAITS)
        .sort(KEYS)
    )


def _targets(tg: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    return tg.select(*KEYS, "season").join(games.select("game_id", "moment"), on="game_id")


def at_moment(view, games: pl.DataFrame) -> pl.DataFrame:
    """The moment's `games` (game_id, season, week, kickoff), from a view at `view.at`."""
    season = int(games["season"].max())
    tg = view.table("team_game", seasons=list(range(season - COACH_SEASONS, season + 1)))
    moment = games.with_columns(moment=pl.lit(view.at).cast(MOMENT))
    targets = _targets(tg, moment)
    return _with_opponent(tg, targets, _features(tg, targets))


def history(view, moments: pl.DataFrame) -> pl.DataFrame:
    """Every game in `moments` (game_id, …, moment) at its own moment, in one pass, from a view
    that sees everything."""
    tg = view.table("team_game")
    targets = _targets(tg, moments)
    return _with_opponent(tg, targets, _features(tg, targets))
