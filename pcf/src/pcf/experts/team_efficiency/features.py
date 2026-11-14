"""The team-efficiency features at a moment, and the targets (brief:
projects/team-efficiency/BRIEF.md).

**Rows:** each regular-season team-game predicted at the moment (`game_id`, `team`).

**Features**, for every rung at once (so a variant's baselines reuse its features, and every
comparison is on identical rows):
- `<side>_change` is `ridge` with P3's weaker pull after a new QB or coach (`changes`,
  `ratings`); on defense it equals `ridge`;
- `<side>_<rung>`: the team's rating before this game's week, from `ratings.ratings`, for each rung
  in `RUNGS` and side (`off`: EPA per play it gains above the league; `def`: what it allows);
- `opp_<h>_<side>_<rung>`: its opponents' mean rating on the other side over the horizon's games
  (an offense row faces defenses; a defense row faces offenses), from the schedule as known at
  the moment;
- `home_<h>`: the share of the horizon's games at home; `left_<h>`: how many games it holds.
  Horizons (`HORIZONS`): the next 3 games and the rest of the regular season, from this game on.
- **Published** (`PUBLISHED`, for higher layers; decision 0021's mechanism): the champion's
  ratings under names that don't change with the champion, `off_rating` and `def_rating` with
  their sds (offense: `change`, every play counted equally with P3's weaker pull after a new QB
  or coach; defense: `ridge`; the CEO, 2026-11-13 and 2026-11-14), and pass, run and
  series-success ratings.

**Targets** (`targets`): the team's EPA per play over the horizon's games, relative to the
league's mean in each game's week: on offense what it gained, on defense what it allowed. Known
when the last of those weeks is (the week's league mean needs all its games). Only complete
windows: every game in it has its plays.
"""

from __future__ import annotations

import polars as pl

from pcf.experts.team_efficiency import changes as X
from pcf.experts.team_efficiency import ratings as R

c = pl.col
INPUTS = {
    "team_game": ("schedule", "efficiency", *X.INPUTS["team_game"][1:]),
    "player_game": X.INPUTS["player_game"],
}
KEYS = ["game_id", "team"]
MOMENT = pl.Datetime("us", "UTC")
RUNGS = ("usual", "ridge", "change", "dml", "combo")
SIDES = ("off", "def")
HORIZONS = {"next3": 3, "rest": None}
EXTRA = ("pass", "run", "ssr")  # published only
PUBLISHED = (
    "off_rating", "def_rating", "off_rating_sd", "def_rating_sd", "off_pass", "def_pass", "off_run",
    "def_run", "off_ssr", "def_ssr",
)  # fmt: skip


def _schedule(tg: pl.DataFrame) -> pl.DataFrame:
    """Regular-season team-games on the schedule: game_id, season, week, team, opponent, home,
    listed_at (when the schedule knew it)."""
    return tg.filter(c("game_type") == "REG").select(
        "game_id",
        c("season").cast(pl.Int32),
        c("week").cast(pl.Int32),
        "team",
        "opponent",
        home=c("home").cast(pl.Float64),
        listed_at="known_at",
    )


def _targets(tg: pl.DataFrame, games: pl.DataFrame) -> pl.DataFrame:
    """The team-games predicted: game_id, team, season, week, moment."""
    return (
        _schedule(tg)
        .join(games.select("game_id", "moment"), on="game_id", how="inner")
        .select(*KEYS, "season", "week", c("moment").cast(MOMENT))
    )


def _windows(sched: pl.DataFrame, targets: pl.DataFrame, horizon: int | None) -> pl.DataFrame:
    """Each target's horizon games, as the schedule knew them at its moment: one row per target
    and game, with the opponent and home."""
    games = sched.select(
        "team", "season", g_week="week", opp="opponent", g_home="home", listed_at="listed_at"
    )
    x = targets.join(games, on=["team", "season"]).filter(
        (c("g_week") >= c("week")) & (c("listed_at") <= c("moment"))
    )
    x = x.sort(*KEYS, "moment", "g_week")
    if horizon is not None:
        x = x.filter(c("g_week").rank("ordinal").over(*KEYS, "moment") <= horizon)
    return x


def _rows(tg: pl.DataFrame, targets: pl.DataFrame, pg: pl.DataFrame) -> pl.DataFrame:
    if targets.is_empty():
        return pl.DataFrame()
    sched = _schedule(tg)
    names = R.teams(sched)
    x = R.prepare(tg, names)
    requests = targets.select("season", "week", "moment").unique()
    ch = R.change_arrays(X.season_changes(tg, pg), names)
    rat = R.ratings(x, requests, [*RUNGS, *EXTRA], names, ch)
    at = ["season", "week", "moment"]
    own = rat.select(
        *at,
        "team",
        *[c(f"{r}_o").alias(f"off_{r}") for r in (*RUNGS, *EXTRA)],
        *[c(f"{r}_d").alias(f"def_{r}") for r in (*RUNGS, *EXTRA)],
        # the champion (decision 0032): offense P3's `change`, defense `ridge`
        off_rating="change_o",
        def_rating="ridge_d",
        off_rating_sd="change_o_sd",
        def_rating_sd="ridge_d_sd",
    )
    out = targets.join(own, on=[*at, "team"], how="left")
    for h, n in HORIZONS.items():
        w = _windows(sched, targets, n)
        # an offense row faces its opponents' defenses; a defense row their offenses
        opp = rat.select(
            *at,
            opp="team",
            **{f"o_{r}": c(f"{r}_d") for r in RUNGS},
            **{f"d_{r}": c(f"{r}_o") for r in RUNGS},
        )
        w = w.join(opp, on=[*at, "opp"], how="left")
        agg = w.group_by(*KEYS, "moment").agg(
            *[c(f"o_{r}").mean().alias(f"opp_{h}_off_{r}") for r in RUNGS],
            *[c(f"d_{r}").mean().alias(f"opp_{h}_def_{r}") for r in RUNGS],
            c("g_home").mean().alias(f"home_{h}"),
            pl.len().cast(pl.Int32).alias(f"left_{h}"),
        )
        out = out.join(agg, on=[*KEYS, "moment"], how="left")
    return out.drop("week", "moment").sort(KEYS)


def at_moment(view, games: pl.DataFrame) -> pl.DataFrame:
    """The moment's `games` (game_id, season, week, kickoff), from a view at `view.at`."""
    tg = view.table("team_game")
    moment = games.with_columns(moment=pl.lit(view.at).cast(MOMENT))
    return _rows(tg, _targets(tg, moment), view.table("player_game"))


def history(view, moments: pl.DataFrame) -> pl.DataFrame:
    """Every game in `moments` (game_id, …, moment) at its own moment, in one pass, from a view
    that sees everything (each moment's ratings use only rows known by it)."""
    tg = view.table("team_game")
    return _rows(tg, _targets(tg, moments), view.table("player_game"))


def targets(tg: pl.DataFrame, side: str, horizon: str) -> pl.DataFrame:
    """game_id, team, y (EPA per play over the horizon's games relative to each week's league
    mean; offense gained or defense allowed) and known_at. Complete windows only."""
    sched = _schedule(tg)
    played = tg.filter(
        (c("game_type") == "REG") & c("efficiency_known_at").is_not_null() & (c("eff_plays") > 0)
    ).select(
        "game_id", "team", c("season").cast(pl.Int32), c("week").cast(pl.Int32), "eff_plays",
        "eff_epa", known="efficiency_known_at",
    )  # fmt: skip
    league = played.group_by("season", "week").agg(
        mean=c("eff_epa").sum() / c("eff_plays").sum(), week_known=c("known").max()
    )
    # the value per team-game for this side: the team's own offense, or the opponent's
    games = played.join(league, on=["season", "week"]).select(
        "game_id", off_team="team", rel=c("eff_epa") - c("eff_plays") * c("mean"),
        n="eff_plays", week_known="week_known",
    )  # fmt: skip
    if side == "off":
        value = sched.join(games, left_on=["game_id", "team"], right_on=["game_id", "off_team"])
    else:
        value = sched.join(games, left_on=["game_id", "opponent"], right_on=["game_id", "off_team"])
    value = value.select("team", "season", g_week="week", rel="rel", n="n", wk="week_known")
    seq = (
        sched.select("game_id", "team", "season", "week")
        .join(sched.select("team", "season", g_week="week"), on=["team", "season"])
        .filter(c("g_week") >= c("week"))
    )
    if HORIZONS[horizon] is not None:
        seq = seq.filter(c("g_week").rank("ordinal").over(KEYS) <= HORIZONS[horizon])
    pairs = seq.join(value, on=["team", "season", "g_week"], how="left")
    return (
        pairs.group_by(KEYS)
        .agg(
            y=c("rel").sum() / c("n").sum(),
            missing=c("rel").null_count(),
            known_at=c("wk").max(),
        )
        .filter(c("missing") == 0)
        .select(*KEYS, "y", "known_at")
        .sort(KEYS)
    )
