"""The pace features at a moment, from `team_game` only (brief: projects/pace/BRIEF.md).

**Habits** (`HABITS`, from the `pace` part, measured on every play against PCF's own expected
values): pace over expected, pass rate over expected on every play and on 1st, 2nd and 3rd down
apart, and the no-huddle rate. Per habit `<h>`, the same history averages as schemes-v2's traits
(`pcf.experts.schemes_v2.features`, reused): `<h>_league`, `_last4`, `_season`, `_shrunk`,
`_last_season`, `_coach`, each weighted by the plays it was measured on.

**Volume** (`VOLUME`): plays, dropbacks and runs, each game weighted alike. For a volume forecast
each row also has `CONTEXT` (what the team's defense allows, its offense's and defense's EPA per
play and plays per drive), the usual neutral habits (`NEUTRAL`, from `tendencies`: the yardstick
the full-sample habits must beat), the opponent's version of all of them (`opp_<name>`), and the
game's line (`spread` for this team, `total_line`), each only once it is known by the moment
(otherwise a pick'em and `TOTAL_FALLBACK`).

`at_moment` is the per-moment version the contract defines; `history` computes every game's in one
pass and must give the same rows (the leakage checks compare them).
"""

from __future__ import annotations

import polars as pl

from pcf.experts.schemes_v2 import features as S

c = pl.col
INPUTS = {"team_game": ("schedule", "pregame", "opening_coach", "tendencies", "pace")}
KEYS = S.KEYS
KNOWN = "pace_known_at"
MOMENT = S.MOMENT
PARTS = S.PARTS
COACH_SEASONS = S.COACH_SEASONS
# measure → (the pace column, what it's weighted by)
HABITS: dict[str, tuple[str, str]] = {
    "pace_oe": ("pace_oe", "pace_snaps"),
    "proe": ("proe", "plays"),
    "proe_1st": ("proe_1st", "downs_1st"),
    "proe_2nd": ("proe_2nd", "downs_2nd"),
    "proe_3rd": ("proe_3rd", "downs_3rd"),
    "no_huddle": ("no_huddle", "plays"),
}
VOLUME: dict[str, tuple[str, str]] = {
    "plays": ("plays", "one"),
    "dropbacks": ("dropbacks", "one"),
    "runs": ("runs", "one"),
}
CONTEXT: dict[str, tuple[str, str]] = {
    "def_plays": ("def_plays", "one"),
    "def_dropbacks": ("def_dropbacks_all", "one"),
    "def_runs": ("def_runs", "one"),
    "epa": ("epa_per_play", "plays"),
    "def_epa": ("def_epa_per_play", "def_plays"),
    "ppd": ("plays_per_drive", "drives"),
    "def_ppd": ("def_plays_per_drive", "def_drives"),
}
# the usual measures, in neutral situations only (team_game.tendencies)
NEUTRAL: dict[str, tuple[str, str]] = {
    "tempo": ("tempo_seconds", "tempo_plays"),
    "neutral_pass_oe": ("neutral_pass_oe", "neutral_plays"),
}
FULL_HABITS = ("pace_oe", "proe", "no_huddle")  # the habits a volume forecast reads
TOTAL_FALLBACK = 44.0  # points: a typical total, for a game whose line isn't known yet


def _played(tg: pl.DataFrame) -> pl.DataFrame:
    return tg.with_columns(one=pl.lit(1.0))


def habit_features(tg: pl.DataFrame, targets: pl.DataFrame) -> pl.DataFrame:
    """Every habit's history averages for `targets` (game_id, team, season, moment)."""
    return S._features(_played(tg), targets, HABITS, KNOWN)


def _line(tg: pl.DataFrame, targets: pl.DataFrame) -> pl.DataFrame:
    """The game's line for each target, if known by its moment."""
    lines = tg.select(*KEYS, "spread", "total_line", known="pregame_known_at")
    known = c("known").is_not_null() & (c("known") <= c("moment"))
    return (
        targets.select(*KEYS, "moment")
        .join(lines, on=KEYS, how="left")
        .select(
            *KEYS,
            spread=pl.when(known).then(c("spread")).fill_null(0.0).cast(pl.Float64),
            total_line=pl.when(known)
            .then(c("total_line"))
            .fill_null(TOTAL_FALLBACK)
            .cast(pl.Float64),
        )
    )


def volume_features(tg: pl.DataFrame, targets: pl.DataFrame) -> pl.DataFrame:
    """Volume, context and habit averages for each target and its opponent, plus the line."""
    played = _played(tg)
    own = S._features(
        played, targets, {**VOLUME, **CONTEXT, **{h: HABITS[h] for h in FULL_HABITS}}, KNOWN
    )
    neutral = S._features(tg, targets, NEUTRAL).drop("season", "games")
    rows = own.join(neutral, on=KEYS, how="inner")
    measures = [x for x in rows.columns if x not in (*KEYS, "season", "games")]
    other = rows.select(
        "game_id", c("team").alias("opp_team"), *[c(x).alias(f"opp_{x}") for x in measures]
    )
    opp = (
        rows.select(KEYS)
        .join(other, on="game_id")
        .filter(c("opp_team") != c("team"))
        .drop("opp_team")
    )
    # both teams' histories are needed: a game whose opponent has none yet is left out
    return rows.join(opp, on=KEYS, how="inner").join(_line(tg, targets), on=KEYS).sort(KEYS)


def _targets(tg: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    return tg.select(*KEYS, "season").join(games.select("game_id", "moment"), on="game_id")


def at_moment(view, games: pl.DataFrame, kind: str) -> pl.DataFrame:
    """The moment's `games` (game_id, season, week, kickoff), from a view at `view.at`. `kind`:
    "habit" or "volume"."""
    season = int(games["season"].max())
    tg = view.table("team_game", seasons=list(range(season - COACH_SEASONS, season + 1)))
    moment = games.with_columns(moment=pl.lit(view.at).cast(MOMENT))
    targets = _targets(tg, moment)
    return habit_features(tg, targets) if kind == "habit" else volume_features(tg, targets)


def history(view, moments: pl.DataFrame, kind: str) -> pl.DataFrame:
    """Every game in `moments` (game_id, …, moment) at its own moment, in one pass, from a view
    that sees everything."""
    tg = view.table("team_game")
    targets = _targets(tg, moments)
    return habit_features(tg, targets) if kind == "habit" else volume_features(tg, targets)
