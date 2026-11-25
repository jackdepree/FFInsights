"""What every availability model shares: a player's game-by-game health record, as known at a
moment (decision 0047).

**The record** (`timeline`) has one row per player and team-game he was on a roster or a reserve
list for, from 2013 (the 53-man roster) and 2016 (reserve lists, `roster_week`), with:
- `played` (any snap), his scrimmage snaps and his share on his side;
- `listed` (on that game's injury report with a game status, or limited or out of practice),
  the report's status and the body part;
- `reserve` (on a reserve list for injury, illness or non-football injury);
- `absent`: **a health absence**, no snap while listed or on a reserve list (the brief's term);
- `named`: an in-game injury named in the play-by-play that game;
- touches and tackles made (exposure).

A past game's outcome (snaps, stats, named injuries) is known the day after it. A game's report
is known when it's posted, and `reserve` at the start of its week. A player with a roster row and
no snap row in a game whose snaps are known took no snap (participation's exploration F1).

**The state** of a game (the chain's): `h` healthy (not listed), `l` listed (Questionable, or no
game status), `o` Out or Doubtful, `r` reserve, and `f`, off every roster (released or unsigned).
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

c = pl.col
FIRST_HISTORY = 2013  # snap counts and named injuries (the exploration)
FIRST_TRAIN = 2016  # weekly reserve statuses (roster_week)
GROUPS = ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB")
SKILL = ("QB", "RB", "WR", "TE")
STATES = ("h", "l", "o", "r")  # with "f", off every roster, in the roll-forward
OFF = "f"
STATUS = {"Out": 3, "Doubtful": 2, "Questionable": 1}
CREDIBILITY = 2.0  # expected injuries for half weight (the exploration's noise ceiling)
RECOVERY_K = 2.0  # absence spells for half weight on his own recovery length
REPEATERS = ("calf", "back", "foot", "groin", "hip", "hamstring", "knee")  # H94
PARTS = {  # body-part groups, first match wins
    "not_injury": r"not injury|illness|rest|personal|coach|suspen|covid|non-football",
    "concussion": r"concussion|head",
    "hamstring": r"hamstring",
    "knee": r"knee|acl|mcl|patella|meniscus",
    "ankle": r"ankle",
    "soft": r"calf|back|foot|groin|hip|quad|thigh|achilles|toe|heel|pectoral|oblique|abdom",
    "shoulder": r"shoulder|arm|elbow|wrist|hand|finger|thumb|collarbone|clavicle",
}
INPUTS = {
    "player_game": ("roster", "snaps", "injury", "stats", "injured", "game_status"),
    "roster_week": ("status",),
    "team_game": ("schedule",),
    "participation/active": 1,
}
HISTORY_COLS = ["offense_snaps", "defense_snaps", "st_snaps", "offense_pct", "defense_pct"]


def part_group(e: pl.Expr) -> pl.Expr:
    """A report's body part → its group (PARTS), "other" if listed with no match."""
    low = e.str.to_lowercase()
    out = pl.when(low.is_null() | (low.str.strip_chars() == "")).then(pl.lit(None, pl.String))
    for name, pattern in PARTS.items():
        out = out.when(low.str.contains(pattern)).then(pl.lit(name))
    return out.otherwise(pl.lit("other"))


def practice_code(e: pl.Expr) -> pl.Expr:
    """The final practice status: 2 did not, 1 limited, 0 full, null not on the practice report."""
    return (
        pl.when(e.str.starts_with("Did Not")).then(2)
        .when(e.str.starts_with("Limited")).then(1)
        .when(e.str.starts_with("Full")).then(0)
        .otherwise(None).cast(pl.Int8)
    )  # fmt: skip


def schedule(view, seasons: Sequence[int]) -> pl.DataFrame:
    """Each team's regular-season games in order: game_id, team, season, week, kickoff, gi (its
    index in the team's season), n_games (the team's games that season)."""
    tg = view.table("team_game", seasons=list(seasons)).filter(c("game_type") == "REG")
    return (
        tg.select("game_id", "team", "season", "week", "kickoff")
        .sort("team", "season", "week")
        .with_columns(
            gi=pl.int_range(pl.len()).over("team", "season").cast(pl.Int32),
            n_games=pl.len().over("team", "season").cast(pl.Int32),
        )
    )


def report(pg: pl.DataFrame) -> pl.DataFrame:
    """A player-game's report columns: status (0 none, 1 Q, 2 D, 3 O), practice code, the body
    part's group and `listed`."""
    practice = practice_code(c("practice_status"))
    return pg.with_columns(
        status=c("report_status").replace_strict(STATUS, default=0, return_dtype=pl.Int8),
        practice=practice,
        part=part_group(pl.coalesce("report_primary_injury", "practice_primary_injury")),
    ).with_columns(listed=(c("status") > 0) | (c("practice") >= 1).fill_null(False))


def timeline(view, season: int, sched: pl.DataFrame) -> pl.DataFrame:
    """Every player-game of a regular season from FIRST_HISTORY to `season` whose outcome is known
    at the view's moment (see the module's doc), oldest first. `sched` is `schedule` over the
    same seasons."""
    seasons = list(range(FIRST_HISTORY, season + 1))
    pg = view.table("player_game", seasons=seasons)
    pg = pg.join(sched.select("game_id", "team", "gi"), on=["game_id", "team"], how="inner")
    known_games = pg.group_by("game_id").agg(c("snaps_known_at").max().is_not_null().alias("k"))
    pg = pg.join(known_games.filter(c("k")).select("game_id"), on="game_id", how="semi")
    pg = report(pg)
    tackles = ["def_tackles_solo", "def_tackle_assists", "def_tackles_with_assist", "def_sacks"]
    pg = pg.select(
        "gsis_id", "game_id", "season", "week", "team", "position", "gi",
        *[c(x).fill_null(0.0).alias(x) for x in HISTORY_COLS],
        "status", "practice", "part", "listed",
        touches=(c("carries").fill_null(0) + c("receptions").fill_null(0)).cast(pl.Float64),
        tackles=pl.sum_horizontal(c(x).fill_null(0) for x in tackles).cast(pl.Float64),
        named=c("injured_play").is_not_null(),
        reserve=pl.lit(False),
    )  # fmt: skip
    # reserve-list games (2016 on): no player_game row, so they're added from roster_week
    rw = view.table("roster_week", seasons=seasons).filter(c("reserve"))
    rw = rw.join(sched.select("game_id", "team", "gi", "kickoff"), on=["game_id", "team"])
    played_games = pg.select("game_id").unique()
    rw = rw.join(played_games, on="game_id", how="semi")  # outcomes known
    res = rw.join(pg.select("gsis_id", "game_id"), on=["gsis_id", "game_id"], how="anti").select(
        "gsis_id", "game_id", "season", "week", "team", "position", "gi",
        *[pl.lit(0.0).alias(x) for x in HISTORY_COLS],
        status=pl.lit(0, pl.Int8), practice=pl.lit(None, pl.Int8), part=pl.lit(None, pl.String),
        listed=pl.lit(False), touches=pl.lit(0.0), tackles=pl.lit(0.0), named=pl.lit(False),
        reserve=pl.lit(True),
    )  # fmt: skip
    out = pl.concat([pg, res], how="vertical_relaxed")
    scrim = c("offense_snaps") + c("defense_snaps")
    return out.with_columns(
        played=(scrim + c("st_snaps")) > 0,
        snaps=scrim,
        share=pl.max_horizontal("offense_pct", "defense_pct"),
    ).with_columns(
        absent=~c("played") & (c("listed") | c("reserve")),
        state=pl.when(c("reserve")).then(pl.lit("r"))
        .when(c("status") >= 2).then(pl.lit("o"))
        .when(c("listed")).then(pl.lit("l"))
        .otherwise(pl.lit("h")),
    ).sort("gsis_id", "season", "week")  # fmt: skip


def position_rates(tl: pl.DataFrame) -> pl.DataFrame:
    """Named in-game injuries per scrimmage snap by position, from the record (a description of
    the league as known at the moment, used as proneness's expected rate)."""
    return (
        tl.filter(c("position").is_in(list(GROUPS)))
        .group_by("position")
        .agg(rate=c("named").sum() / c("snaps").sum().clip(1.0))
    )
